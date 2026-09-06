# -*- coding: utf-8 -*-
"""Move small parts to new positions and cut their pads loose, so the router
can re-attach their nets from where the pads now are.

    python tools/move_parts.py in.brd out.brd --moves "C109:53.5,9.6;R20:54.6,9.6;..."

WHY. The strip between U1's west dogbones and U3's east pads (x 39..42) is
the corridor every westbound net has to cross, and nine 0201 parts sit in
it on both sides -- four VCC3V3 decouplers and five pull-up/pull-down
resistors -- with their stubs and vias. The area east of U1 (x 52..58,
y 9..17) is empty on both outer layers (user, 2026-09-06). Moving the nine
there frees the strip for a second via column and lanes.

WHAT IT DOES, per part: rewrites the <element> position (rotation kept);
deletes every wire of the part's nets that ends inside one of its OLD pads,
and every via of those nets within VIA_R of an old pad (the dogbone); reports
foreign copper the NEW pads would touch on their layer, and refuses the move
if there is any. GND / VCC3V3 pads are then re-tied with gnd_stitch.py
(--net GND, --net VCC3V3); signal nets are re-routed with close_airwires.py
(CLOSE_FORCE on the nets printed at the end).
"""

import io
import math
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E   # noqa: E402
import geom as G     # noqa: E402

VIA_R = 1.2
CLR = 0.0762
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)


def main():
    args = sys.argv[1:]
    i = args.index("--moves")
    moves = {}
    for item in args[i + 1].split(";"):
        if not item.strip():
            continue
        name, xy = item.split(":")
        x, y = (float(v) for v in xy.split(","))
        moves[name.strip()] = (x, y)
    del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    pads_all = [(n, x, y, hx, hy, side) for n, x, y, hx, hy, side in E.board_copper(board, skip=())]
    # pads per element: nearest element origin is not reliable for a smashed
    # part, so take pad ownership from the package geometry via contactrefs
    sm = re.search(r"<signals>(.*)</signals>", board, re.S).group(1)
    padnet = {}
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sm, re.S):
        for c in re.finditer(r'<contactref element="([^"]+)" pad="([^"]+)"', m.group(2)):
            padnet[(c.group(1), c.group(2))] = m.group(1)
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', board, re.S):
        for pm in re.finditer(r'<package name="([^"]+)"[^>]*>(.*?)</package>', lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)

    def rp(x, y, rot):
        r = rot[1:] if rot.startswith("M") else rot
        ang = int(r[1:]) % 360 if len(r) > 1 else 0
        x, y = {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[ang]
        return (-x, y) if rot.startswith("M") else (x, y)

    to_delete = {}   # net -> list of (kind, key)
    signal_nets = set()
    new_text = board
    for name, (nx, ny) in moves.items():
        m = re.search(r'<element name="%s" library="([^"]+)" package="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?' % re.escape(name), board)
        if not m:
            print("  ****  %s: no such element" % name)
            continue
        lib, pk, ox, oy, rot = m.group(1), m.group(2), float(m.group(3)), float(m.group(4)), m.group(5) or "R0"
        side = 16 if rot.startswith("M") else 1
        swap = rot.lstrip("M") in ("R90", "R270")
        smds = re.findall(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', pkg.get((lib, pk), ""))
        old_pads, new_pads = [], []
        for pn, px, py, dx, dy in smds:
            a = rp(float(px), float(py), rot)
            hx, hy = (float(dy) / 2, float(dx) / 2) if swap else (float(dx) / 2, float(dy) / 2)
            net = padnet.get((name, pn))
            old_pads.append((net, ox + a[0], oy + a[1], hx, hy))
            new_pads.append((net, nx + a[0], ny + a[1], hx, hy))
        # clearance of the new pads on their layer
        clash = []
        for net, px, py, hx, hy in new_pads:
            for onet, (objs, t, pl) in parsed.items():
                if onet == net:
                    continue
                for o in objs:
                    if side not in o["layers"]:
                        continue
                    if o["kind"] == "wire":
                        d = G.rect_seg((px, py, hx, hy, 0.0), o["a"], o["b"]) - o["radius"]
                    elif o["kind"] == "via":
                        d = G.rect_pt((px, py, hx, hy), o["at"][0], o["at"][1]) - o["radius"]
                    else:
                        d = max(abs(px - o["at"][0]) - hx - o["hx"], abs(py - o["at"][1]) - hy - o["hy"])
                    if d < CLR:
                        clash.append((onet, o["kind"], round(d, 3)))
            for onet, x, y, hx2, hy2, s2 in pads_all:
                if onet == net or (s2 != 0 and s2 != side):
                    continue
                if max(abs(px - x) - hx - hx2, abs(py - y) - hy - hy2) < CLR and not (abs(px - x) < 1e-6 and abs(py - y) < 1e-6):
                    clash.append((onet, "pad", 0))
        if clash:
            print("  ****  %s at (%.2f,%.2f): new pads would touch %s -- not moved" % (name, nx, ny, sorted(set(clash))[:6]))
            continue
        # copper attached to the old pads
        for net, px, py, hx, hy in old_pads:
            if not net:
                continue
            objs = parsed[net][0]
            for o in objs:
                if o["kind"] == "wire" and side in o["layers"] and (
                        (abs(o["a"][0] - px) <= hx and abs(o["a"][1] - py) <= hy) or (abs(o["b"][0] - px) <= hx and abs(o["b"][1] - py) <= hy)):
                    to_delete.setdefault(net, []).append(("wire", o))
                if o["kind"] == "via" and math.hypot(o["at"][0] - px, o["at"][1] - py) <= VIA_R:
                    to_delete.setdefault(net, []).append(("via", o))
            if net not in ("GND", "VCC3V3"):
                signal_nets.add(net)
        new_text = new_text.replace(m.group(0), m.group(0).replace('x="%s"' % m.group(3), 'x="%s"' % ("%.4f" % nx).rstrip("0").rstrip("."), 1)
                                    .replace('y="%s"' % m.group(4), 'y="%s"' % ("%.4f" % ny).rstrip("0").rstrip("."), 1), 1)
        print("  %-5s (%.2f,%.2f) -> (%.2f,%.2f) %s; pads: %s" % (name, ox, oy, nx, ny, rot, ", ".join(str(p[0]) for p in old_pads)))

    def sub(mm):
        net = mm.group(2)
        if net not in to_delete:
            return mm.group(0)
        body = mm.group(3)
        victims = to_delete[net]

        def keep_w(w):
            a = (float(w.group(1)), float(w.group(2)))
            b = (float(w.group(3)), float(w.group(4)))
            L = int(w.group(6))
            for kind, o in victims:
                if kind == "wire" and L in o["layers"] and abs(a[0] - o["a"][0]) < 1e-6 and abs(a[1] - o["a"][1]) < 1e-6 and abs(b[0] - o["b"][0]) < 1e-6 and abs(b[1] - o["b"][1]) < 1e-6:
                    return ""
            return w.group(0)

        def keep_v(v):
            at = dict(re.findall(r'(\w+)="([^"]*)"', v.group(0)))
            if "x" in at:
                for kind, o in victims:
                    if kind == "via" and abs(float(at["x"]) - o["at"][0]) < 1e-6 and abs(float(at["y"]) - o["at"][1]) < 1e-6:
                        return ""
            return v.group(0)
        body = re.sub(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"[^>]*/>', keep_w, body)
        body = re.sub(r"<via\s[^>]*?(?:/>|>\s*</via>)", keep_v, body, flags=re.S)
        return mm.group(1) + body + mm.group(4)

    out = SIG_RE.sub(sub, new_text)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    print("deleted attached copper of %d net(s); signal nets to re-route: %s" % (len(to_delete), ",".join(sorted(signal_nets))))
    io.open(dst + ".nets", "w").write(",".join(sorted(signal_nets)))
    print("wrote", dst)


if __name__ == "__main__":
    main()
