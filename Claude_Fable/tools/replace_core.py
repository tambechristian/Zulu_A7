# -*- coding: utf-8 -*-
"""Core re-placement: move the SDRAM under U1, the flash beside it, and the
small parts out of their way; cut the copper that has to be routed again.

    python tools/replace_core.py in.brd out.brd --moves moves.txt [--keep-copper]

moves.txt: one part per line, "NAME x y [ROT]"; a line starting with # is
a comment. ROT, when given, replaces the element's rotation (MR90 puts a
part on the bottom, rotated).

WHY (2026-09-06). Four routing branches on the old floorplan stalled at 26
to 49 airwires because the SDRAM (U3, bottom, west of U1) sent its 39
nets through the same 3 mm strip as the FT2232, flash, SD and LED nets,
and each of the 39 had to cross the core inside that strip. With U3 on
the bottom directly under U1, the bus goes down through vias in U1's
empty annulus (rings 4-6, 120 sites) and along L16 under U3's body to its
pads; the strip west of U1 carries only the other traffic.

WHAT IT DOES. Moves the elements. Then, unless --keep-copper, deletes the
routed copper that the new floorplan invalidates: every wire and via of a
re-routable net with a point at x >= CUT_X (the U2/U1 half of the board),
plus any wire or via of any net that would touch a moved part's new pads.
Kept whatever happens: the USB pair, the supply nets (they have no plane
and their bulk caps stay), and every via inside a U1 ball (the plane
balls' via-in-pad). Writes out.brd.nets: the nets that lost copper.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E   # noqa: E402
import geom as G     # noqa: E402

CUT_X = 27.0
KEEP_NETS = set(("USB_D_P", "USB_D_N", "USB5V0", "VU", "VEXT", "VBUS", "VCC1V0", "VCC1V8",
                 "VCCADC", "GNDADC", "GND", "VCC3V3", "SW1_NET", "SW2_NET", "SW3_NET"))
CLR = 0.0762
BIG_POWER = set(("VCC1V0", "VCC1V8", "VU", "VEXT", "USB5V0"))
VIA_ROOM = 0.15 + 0.0762 + 0.05     # a 0.30 mm land plus the 3 mil rule plus margin
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)


def rp(x, y, rot):
    r = rot[1:] if rot.startswith("M") else rot
    ang = int(r[1:]) % 360 if len(r) > 1 else 0
    x, y = {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[ang]
    return (-x, y) if rot.startswith("M") else (x, y)


def main():
    args = sys.argv[1:]
    keep_copper = "--keep-copper" in args
    args = [a for a in args if a != "--keep-copper"]
    i = args.index("--moves")
    moves = {}
    for line in io.open(args[i + 1]).read().splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        f = line.split()
        moves[f[0]] = (float(f[1]), float(f[2]), f[3] if len(f) > 3 else None)
    del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', board, re.S):
        for pm in re.finditer(r'<package name="([^"]+)"[^>]*>(.*?)</package>', lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)
    sm = re.search(r"<signals>(.*)</signals>", board, re.S).group(1)
    padnet = {}
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sm, re.S):
        for c in re.finditer(r'<contactref element="([^"]+)" pad="([^"]+)"', m.group(2)):
            padnet[(c.group(1), c.group(2))] = m.group(1)
    u1 = re.search(r'<element name="U1"[^>]*x="([-\d.]+)" y="([-\d.]+)"', board)
    u1x, u1y = float(u1.group(1)), float(u1.group(2))

    new_text = board
    new_pads = []   # (net, x, y, hx, hy, layers, element)
    for name, (nx, ny, nrot) in moves.items():
        m = re.search(r'<element name="%s" library="([^"]+)" package="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?' % re.escape(name), board)
        if not m:
            print("  ****  %s: no such element" % name)
            continue
        lib, pk, ox, oy, rot = m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), m.group(5) or "R0"
        rot2 = nrot or rot
        side = 16 if rot2.startswith("M") else 1
        swap = rot2.lstrip("M") in ("R90", "R270")
        for pn, px, py, dx, dy in re.findall(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', pkg.get((lib, pk), "")):
            a = rp(float(px), float(py), rot2)
            hx, hy = (float(dy) / 2, float(dx) / 2) if swap else (float(dx) / 2, float(dy) / 2)
            new_pads.append((padnet.get((name, pn)), nx + a[0], ny + a[1], hx, hy, frozenset((side,)), name))
        for pn, px, py, d in re.findall(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"', pkg.get((lib, pk), "")):
            a = rp(float(px), float(py), rot2)
            new_pads.append((padnet.get((name, pn)), nx + a[0], ny + a[1], float(d), float(d), C.COPPER_LAYERS, name))
        tag = m.group(0)
        tag2 = tag.replace('x="%s"' % m.group(3), 'x="%s"' % ("%.4f" % nx).rstrip("0").rstrip("."), 1)
        tag2 = tag2.replace('y="%s"' % m.group(4), 'y="%s"' % ("%.4f" % ny).rstrip("0").rstrip("."), 1)
        if nrot:
            if m.group(5):
                tag2 = tag2.replace('rot="%s"' % m.group(5), 'rot="%s"' % nrot, 1)
            else:
                tag2 = tag2[:-1] + ' rot="%s">' % nrot if tag2.endswith(">") else tag2 + ' rot="%s"' % nrot
        new_text = new_text.replace(tag, tag2, 1)
        print("  %-5s (%.2f,%.2f) %s -> (%.2f,%.2f) %s" % (name, ox, oy, rot, nx, ny, rot2))

    to_delete = {}
    if not keep_copper:
        for net, (objs, terms, planes) in parsed.items():
            victims = []
            for o in objs:
                if o["kind"] not in ("wire", "via"):
                    continue
                pts = [o["a"], o["b"]] if o["kind"] == "wire" else [o["at"]]
                # a via inside a U1 ball stays: the plane balls' via-in-pad
                if o["kind"] == "via" and 41.5 <= o["at"][0] <= 51.5 and 7.2 <= o["at"][1] <= 17.3 \
                        and abs((o["at"][0] - u1x) / 0.5 - round((o["at"][0] - u1x) / 0.5)) < 0.05 \
                        and abs((o["at"][1] - u1y) / 0.5 - round((o["at"][1] - u1y) / 0.5)) < 0.05:
                    continue
                hit = False
                if net not in KEEP_NETS and any(p[0] >= CUT_X for p in pts):
                    hit = True
                elif net not in BIG_POWER and any(pn != net and el == "U3" and (
                        (o["kind"] == "wire" and E.seg_pt(o["a"], o["b"], (px, py)) - o["radius"] < VIA_ROOM)
                        or (o["kind"] == "via" and math.hypot(o["at"][0] - px, o["at"][1] - py) - o["radius"] < VIA_ROOM))
                        for pn, px, py, hx, hy, layers, el in new_pads):
                    # room for a through via in every U3 pad: the plane nets'
                    # top-side stubs and stitches near the rows go, the pours
                    # reconnect them; the supply traces stay (BIG_POWER)
                    hit = True
                else:
                    for pn, px, py, hx, hy, layers, el in new_pads:
                        if pn == net or not (o["layers"] & layers):
                            continue
                        if o["kind"] == "wire":
                            d = G.rect_seg((px, py, hx, hy, 0.0), o["a"], o["b"]) - o["radius"]
                        else:
                            d = G.rect_pt((px, py, hx, hy), o["at"][0], o["at"][1]) - o["radius"]
                        if d < CLR:
                            hit = True
                            break
                if hit:
                    victims.append(o)
            if victims:
                to_delete[net] = victims

    def sub(mm):
        net = mm.group(2)
        if net not in to_delete:
            return mm.group(0)
        body = mm.group(3)
        victims = to_delete[net]
        wires = [o for o in victims if o["kind"] == "wire"]
        vias = [o for o in victims if o["kind"] == "via"]

        def keep_w(w):
            a = (float(w.group(1)), float(w.group(2)))
            b = (float(w.group(3)), float(w.group(4)))
            L = int(w.group(6))
            for o in wires:
                if L in o["layers"] and abs(a[0] - o["a"][0]) < 1e-6 and abs(a[1] - o["a"][1]) < 1e-6 and abs(b[0] - o["b"][0]) < 1e-6 and abs(b[1] - o["b"][1]) < 1e-6:
                    return ""
            return w.group(0)

        def keep_v(v):
            at = dict(re.findall(r'(\w+)="([^"]*)"', v.group(0)))
            if "x" in at:
                for o in vias:
                    if abs(float(at["x"]) - o["at"][0]) < 1e-6 and abs(float(at["y"]) - o["at"][1]) < 1e-6:
                        return ""
            return v.group(0)
        body = re.sub(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"[^>]*/>', keep_w, body)
        body = re.sub(r"<via\s[^>]*?(?:/>|>\s*</via>)", keep_v, body, flags=re.S)
        return mm.group(1) + body + mm.group(4)

    out = SIG_RE.sub(sub, new_text)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    io.open(dst + ".nets", "w").write(",".join(sorted(to_delete)))
    print("moved %d part(s); copper cut from %d net(s) (%d wire(s), %d via(s))" % (
        len(moves), len(to_delete), sum(1 for v in to_delete.values() for o in v if o["kind"] == "wire"),
        sum(1 for v in to_delete.values() for o in v if o["kind"] == "via")))
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
