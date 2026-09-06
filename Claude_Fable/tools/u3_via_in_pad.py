# -*- coding: utf-8 -*-
"""A 0.20 mm through via in every SDRAM pad of U3 whose land clears the
copper above it, so the bus changes layer AT the pad and never in the
corridor west of U1.

    python tools/u3_via_in_pad.py in.brd out.brd [--nets A,B]

WHY. U3 (TSOPII-54, bottom side) reaches U1's balls on the top build-up
layers; every one of its 39 signals has to cross the core once, and a laser
microvia cannot. Left to the router, the through via lands in the 3 mm
corridor between U3's east end and U1's west balls -- run t3 (2026-09-06)
rebuilt a column of 22 there, and the first six of them boxed the escape
stubs of the balls behind them. A through via in the pad itself (the pad is
1.20 x 0.45 mm, the land 0.30) needs no room anywhere else: the L2/L3
trace from U1 ends on the via, the pad is on L16, done. PCBWay fills and
caps via-in-pad already (see the FAB NOTE).

WHAT IT DOES, per U3 signal pad without a through via: checks a 0.30 mm
land at the pad centre against foreign copper on every copper layer (3 mil
rule) and its 0.20 drill against every other drill (DRILL_CC); a 7-16
microvia already in the pad is replaced. Pads that fail keep their old
escape. Writes out.brd.nets with the converted nets.
"""

import io
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_connectivity as C   # noqa: E402
import escape as E   # noqa: E402
import pad_microvias as PM   # noqa: E402
import bga_microvias as BM   # noqa: E402

SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)
VIA_D, VIA_L = 0.2, 0.3


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def main():
    args = sys.argv[1:]
    only = None
    if "--nets" in args:
        i = args.index("--nets")
        only = set(args[i + 1].split(","))
        del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    sm = re.search(r"<signals>(.*)</signals>", board, re.S).group(1)
    u3nets = set(m.group(1) for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sm, re.S) if 'element="U3"' in m.group(2))
    # U3's pad centres from the element itself, wherever it stands
    em = re.search(r'<element name="U3" library="([^"]+)" package="([^"]+)"[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', board)
    pm = re.search(r'<library name="%s">.*?<package name="%s"[^>]*>(.*?)</package>' % (re.escape(em.group(1)), re.escape(em.group(2))), board, re.S)
    rot = em.group(5) or "R0"

    def rp(x, y):
        r = rot[1:] if rot.startswith("M") else rot
        ang = int(r[1:]) % 360 if len(r) > 1 else 0
        x, y = {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[ang]
        return (-x, y) if rot.startswith("M") else (x, y)
    centres = []
    for s in re.finditer(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', pm.group(1)):
        a = rp(float(s.group(2)), float(s.group(3)))
        centres.append((float(em.group(3)) + a[0], float(em.group(4)) + a[1]))
    side_u3 = 16 if rot.startswith("M") else 1
    pads = [(n, x, y, hx, hy) for n, x, y, hx, hy, side in E.board_copper(board, skip=())
            if side == side_u3 and n in u3nets and any(abs(x - cx) < 0.05 and abs(y - cy) < 0.05 for cx, cy in centres)]
    adds, drops, done, skipped = {}, {}, [], []
    placed = []
    for n, x, y, hx, hy in sorted(pads, key=lambda t: (t[2], t[1])):
        if n in BM.PLANE or n.startswith("VCC") or (only and n not in only):
            continue
        objs = parsed[n][0]
        inpad = [o for o in objs if o["kind"] == "via" and abs(o["at"][0] - x) <= hx and abs(o["at"][1] - y) <= hy]
        if any(len(o["layers"]) > 2 for o in inpad):
            continue   # already a through via in the pad
        foreign = PM.foreign_copper(board, parsed, n)
        local = [o for o in foreign if (o["kind"] == "wire" and min(o["a"][0], o["b"][0]) - 1 <= x <= max(o["a"][0], o["b"][0]) + 1
                                         and min(o["a"][1], o["b"][1]) - 1 <= y <= max(o["a"][1], o["b"][1]) + 1)
                 or (o["kind"] != "wire" and abs(o["at"][0] - x) <= 1.5 and abs(o["at"][1] - y) <= 1.5)] + placed
        # own vias other than the microvia this replaces must keep their drill distance too
        own = [o for o in objs if o["kind"] == "via" and o not in inpad]
        ok = True
        for o in local + own:
            if o["kind"] == "via" and math.hypot(o["at"][0] - x, o["at"][1] - y) < PM.DRILL_CC:
                ok = False
                break
        if ok:
            for o in local:
                if o["kind"] == "wire":
                    if E.seg_pt(o["a"], o["b"], (x, y)) < o["radius"] + VIA_L / 2 + PM.CLR:
                        ok = False
                        break
                elif o["kind"] == "via":
                    if math.hypot(o["at"][0] - x, o["at"][1] - y) < o["radius"] + VIA_L / 2 + PM.CLR:
                        ok = False
                        break
                elif o["kind"] == "pad":
                    if o["through"]:
                        if math.hypot(o["at"][0] - x, o["at"][1] - y) < o["hx"] + VIA_L / 2 + PM.CLR:
                            ok = False
                            break
                    elif max(abs(x - o["at"][0]) - o["hx"], abs(y - o["at"][1]) - o["hy"]) < VIA_L / 2 + PM.CLR:
                        ok = False
                        break
        if not ok:
            skipped.append(n)
            print("  ****  %-10s pad (%.2f,%.2f): no room for a through via in the pad; old escape kept" % (n, x, y))
            continue
        adds[n] = adds.get(n, "") + '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (g(x), g(y), g(VIA_D), g(VIA_L))
        for o in inpad:
            drops.setdefault(n, []).append(o)
        placed.append({"kind": "via", "at": (x, y), "radius": VIA_L / 2, "layers": C.COPPER_LAYERS})
        done.append(n)
        print("  %-10s pad (%.2f,%.2f): through via in the pad%s" % (n, x, y, " (replaces the 7-16 microvia)" if inpad else ""))
    print("via-in-pad at %d U3 pad(s); skipped %d: %s" % (len(done), len(skipped), ",".join(skipped) or "-"))

    def sub(m):
        net = m.group(2)
        body = m.group(3)
        if net in drops:
            def keep_v(v):
                at = dict(re.findall(r'(\w+)="([^"]*)"', v.group(0)))
                if "x" in at:
                    for o in drops[net]:
                        if abs(float(at["x"]) - o["at"][0]) < 1e-6 and abs(float(at["y"]) - o["at"][1]) < 1e-6:
                            return ""
                return v.group(0)
            body = re.sub(r"<via\s[^>]*?(?:/>|>\s*</via>)", keep_v, body, flags=re.S)
        return m.group(1) + body + adds.get(net, "") + m.group(4)

    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    io.open(dst + ".nets", "w").write(",".join(sorted(set(done))))
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
