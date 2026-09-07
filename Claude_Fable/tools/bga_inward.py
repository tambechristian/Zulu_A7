# -*- coding: utf-8 -*-
"""Escape the SDRAM balls of U1 INWARD: a lane along a gap between ball
rows or columns to a through via in the empty annulus (rings 4-6), so the
bus drops straight down to U3 under the part and never touches U1's
perimeter.

    python tools/bga_inward.py in.brd out.brd --nets A0,A1,...

WHY. With U3 under U1 the bus is short only if it goes down inside the
footprint. Run c4b (2026-09-06) let the SDRAM nets take their outward
stubs instead: 22 of their through vias landed outside U1 and their L2
traces wrapped around the east edge, walling in the CHAN, JA and UART
balls behind them (48 nets open). Rings 4-6 carry no balls, so a via
there blocks nothing, and every gap between two ball rows fits one 3 mil
trace per layer.

WHAT IT DOES, per listed ball in rings 1-3: tries, in order, a lane along
the two gap rows beside it (east-west, on L1 from the pad) and the two gap
columns beside it (north-south, on L2 from the ball's 1-2 microvia, so it
can cross the L1 lanes), each ending on a 0.20/0.30 through via in the
annulus nearest that side; a via spot that fails is retried one pitch
further in. Every leg and land is checked against foreign copper and the
lanes already placed, so lanes never cross on one layer. A ball on an L1
lane loses its 1-2 microvia (the router keeps an L1 stub only from a bare
pad). Ring-1 balls go first: they have the longest way in. Writes
out.brd.nets.
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
import gnd_stitch as GS   # noqa: E402

SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)
W = 0.0762
VIA_D, VIA_L = 0.2, 0.3
PITCH = 0.5


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def main():
    args = sys.argv[1:]
    i = args.index("--nets")
    only = set(args[i + 1].split(","))
    del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    balls = [(n, x, y) for n, x, y, hx, hy, side in E.board_copper(board, skip=())
             if side == 1 and abs(hx - 0.1125) < 0.01 and 41 < x < 52 and 7 < y < 17 and n]
    xs = sorted(set(round(x, 2) for n, x, y in balls))
    ys = sorted(set(round(y, 2) for n, x, y in balls))
    ng = len(xs)
    x_lo, x_hi, y_lo, y_hi = xs[0], xs[-1], ys[0], ys[-1]
    cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
    r4 = 3 * PITCH          # ring 4 is three pitches in from ring 1
    placed = []
    adds, drops, done, skipped = {}, {}, [], []

    def wire_obj(a, b, L):
        return {"kind": "wire", "a": a, "b": b, "radius": W / 2, "layers": frozenset((L,))}

    def via_obj(x, y):
        return {"kind": "via", "at": (x, y), "radius": VIA_L / 2, "layers": C.COPPER_LAYERS}

    def via_ok(local, x, y):
        for o in local:
            if o["kind"] == "via" and math.hypot(o["at"][0] - x, o["at"][1] - y) < max(PM.DRILL_CC, o["radius"] + VIA_L / 2 + PM.CLR):
                return False
            if o["kind"] == "wire" and E.seg_pt(o["a"], o["b"], (x, y)) < o["radius"] + VIA_L / 2 + PM.CLR:
                return False
            if o["kind"] == "pad":
                if o["through"]:
                    if math.hypot(o["at"][0] - x, o["at"][1] - y) < o["hx"] + VIA_L / 2 + PM.CLR:
                        return False
                elif max(abs(x - o["at"][0]) - o["hx"], abs(y - o["at"][1]) - o["hy"]) < VIA_L / 2 + PM.CLR:
                    return False
        return True

    def candidates(x, y):
        """(layer, legs, via) options for a ball, nearest gap first"""
        out = []
        sx = 1 if x < cx else -1          # inward direction in x
        sy = 1 if y < cy else -1
        # east-west lanes on L1: along the gap rows y +/- 0.25 to the annulus column on this ball's side
        for gy in (y + sy * 0.25, y - sy * 0.25):
            if not (y_lo - 0.3 < gy < y_hi + 0.3):
                continue
            for k in (0, 1):
                col = (x_lo + r4 + 0.25 + k * 0.5) if sx > 0 else (x_hi - r4 - 0.25 - k * 0.5)
                knee = (x + sx * 0.25, gy)
                out.append((1, [((x, y), knee), (knee, (col, gy))], (col, gy)))
        # north-south lanes on L2: along the gap columns x +/- 0.25 to the annulus row on this ball's side
        for gx in (x + sx * 0.25, x - sx * 0.25):
            if not (x_lo - 0.3 < gx < x_hi + 0.3):
                continue
            for k in (0, 1):
                row = (y_lo + r4 + 0.25 + k * 0.5) if sy > 0 else (y_hi - r4 - 0.25 - k * 0.5)
                knee = (gx, y + sy * 0.25)
                out.append((2, [((x, y), knee), (knee, (gx, row))], (gx, row)))
        return out

    order = []
    for n, x, y in balls:
        if n not in only:
            continue
        i, j = xs.index(round(x, 2)), ys.index(round(y, 2))
        ring = min(i, j, ng - 1 - i, ng - 1 - j) + 1
        if ring <= 3:
            order.append((ring, n, x, y))
    for ring, n, x, y in sorted(order):
        objs = parsed[n][0]
        v12 = [o for o in objs if o["kind"] == "via" and o["layers"] == frozenset((1, 2)) and math.hypot(o["at"][0] - x, o["at"][1] - y) < 0.05]
        foreign = [o for o in PM.foreign_copper(board, parsed, n)
                   if (o["kind"] == "wire" and min(o["a"][0], o["b"][0]) - 4 <= x <= max(o["a"][0], o["b"][0]) + 4
                       and min(o["a"][1], o["b"][1]) - 4 <= y <= max(o["a"][1], o["b"][1]) + 4)
                   or (o["kind"] != "wire" and abs(o["at"][0] - x) <= 5 and abs(o["at"][1] - y) <= 5)] + placed
        plan = None
        for L, legs, via in candidates(x, y):
            if L == 2 and not v12:
                continue
            if all(GS.wire_ok(foreign, a, b, W, L) for a, b in legs) and via_ok(foreign, *via):
                plan = (L, legs, via)
                break
        if plan is None:
            skipped.append(n)
            print("  ****  %-10s ball (%.2f,%.2f) ring %d: no inward lane" % (n, x, y, ring))
            continue
        L, legs, via = plan
        add = ""
        for a, b in legs:
            add += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (g(a[0]), g(a[1]), g(b[0]), g(b[1]), g(W), L)
            placed.append(wire_obj(a, b, L))
        add += '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (g(via[0]), g(via[1]), g(VIA_D), g(VIA_L))
        placed.append(via_obj(*via))
        if L == 1 and v12:
            drops.setdefault(n, []).extend(v12)
        adds[n] = adds.get(n, "") + add
        done.append(n)
        print("  %-10s ball (%.2f,%.2f) ring %d: L%d lane to a via at (%.2f,%.2f)" % (n, x, y, ring, L, via[0], via[1]))
    print("inward lanes for %d ball(s); skipped %d: %s" % (len(done), len(skipped), ",".join(skipped) or "-"))

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
