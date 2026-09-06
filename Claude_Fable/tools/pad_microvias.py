# -*- coding: utf-8 -*-
"""Give every bare SMD pad of an open net a laser microvia, so the net can
leave the pad on the HDI escape layer instead of the walled outer layer.

    python tools/pad_microvias.py in.brd out.brd [--nets A,B] [--dry]

WHY. After the HDI swap the BGA balls and the SDRAM pads carry microvias, and
their nets flood the board from L2 and L7. What still shows as a bare pad
on 2026-09-05 is the OTHER end of eleven nets: 0201 resistor pads on the
bottom side directly under U1 (PUDC_B, CFG-M0, DONE, NODE_P0, PROG#,
AIN15_P), boxed in by the dogbone via field on L16, and 0201/0603 pads on
the top between x = 24 and 34 mm, boxed on L1 by the buses that pass them.
Each is the same problem the balls had, and gets the same answer: a
0.10/0.20 mm microvia in the pad (filled and capped, like the other 30) --
1-2 for a top pad, 7-16 for a bottom pad -- wherever the inner layer under
the pad is clear.

HOW. A piece of an open net that holds an SMD pad and nothing that reaches
another layer is a candidate. Inside the pad, on a 0.01 mm grid from the
centre outwards, the first spot where the 0.20 land clears every foreign
wire, via and pad on both layers of the span by the 3 mil rule, and every
drill whose span overlaps by DRILL_CC, gets the via. Nothing else changes;
close_airwires.py routes from there.
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

CLR = 0.0762
MICRO_D, MICRO_L = 0.1, 0.2
DRILL_CC = 0.35
RIP_R = 0.45
SPANS = {1: (1, 2), 16: (7, 16)}
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def foreign_copper(board, parsed, net):
    out = []
    for other, (objects, terminals, planes) in parsed.items():
        if other != net:
            out.extend(objects)
    for n, x, y, hx, hy, side in E.board_copper(board, skip=()):
        if n is None:
            out.append({"kind": "pad", "at": (x, y), "hx": hx, "hy": hy, "through": side == 0,
                        "layers": C.COPPER_LAYERS if side == 0 else frozenset((side,))})
    return out


def land_ok(local, x, y, span_layers, own_vias):
    for o in local:
        # DRILLS KEEP THEIR DISTANCE WHATEVER THEIR DEPTH: Fusion's Drill
        # Distance rule (0.2 mm) does not care that a 1-2 and a 7-16 laser via
        # never meet. A 1-2 in SDRAM-CS#'s ball 0.15 mm from the 7-16 in C36's
        # pad passed the old layer-filtered check (2026-09-06).
        if o["kind"] == "via" and math.hypot(o["at"][0] - x, o["at"][1] - y) < DRILL_CC:
            return False
        if not (o["layers"] & span_layers):
            continue
        if o["kind"] == "wire":
            if E.seg_pt(o["a"], o["b"], (x, y)) < o["radius"] + MICRO_L / 2 + CLR:
                return False
        elif o["kind"] == "via":
            d = math.hypot(o["at"][0] - x, o["at"][1] - y)
            if d < o["radius"] + MICRO_L / 2 + CLR or d < DRILL_CC:
                return False
        else:
            if o["through"]:
                d = math.hypot(o["at"][0] - x, o["at"][1] - y)
                if d < o["hx"] + MICRO_L / 2 + CLR or d < o["hx"] + 0.15:
                    return False
            elif G.rect_pt((o["at"][0], o["at"][1], o["hx"], o["hy"]), x, y) < MICRO_L / 2 + CLR:
                return False
    for o in own_vias:
        if math.hypot(o["at"][0] - x, o["at"][1] - y) < DRILL_CC:
            return False
    return True


def main():
    args = sys.argv[1:]
    only = None
    if "--nets" in args:
        i = args.index("--nets")
        only = set(args[i + 1].split(","))
        del args[i:i + 2]
    dry = "--dry" in args
    rip = "--rip" in args
    args = [a for a in args if a not in ("--dry", "--rip")]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    owner = {}
    for net, (objects, terminals, planes) in parsed.items():
        for o in objects:
            owner[id(o)] = net
    rips = {}
    adds = {}
    for net, (objects, terminals, planes) in sorted(parsed.items()):
        if terminals < 2 or (only and net not in only) or net in ("GND", "VCC3V3"):
            continue
        groups = C.components(objects, terminals, planes)
        if len(groups) < 2:
            continue
        foreign = None
        own_vias = [o for o in objects if o["kind"] == "via"]
        for grp in groups:
            pads = [objects[i] for i in grp if objects[i]["kind"] == "pad"]
            if not pads or any(objects[i]["kind"] == "via" or objects[i].get("through") for i in grp):
                continue
            pad = pads[0]
            if pad["through"]:
                continue
            side = min(pad["layers"])
            if side not in SPANS:
                continue
            lo, hi = SPANS[side]
            span_layers = frozenset((lo, hi))
            if foreign is None:
                foreign = foreign_copper(board, parsed, net)
            px, py = pad["at"]
            local = [o for o in foreign if (o["kind"] == "wire" and min(o["a"][0], o["b"][0]) - 1 <= px <= max(o["a"][0], o["b"][0]) + 1
                                             and min(o["a"][1], o["b"][1]) - 1 <= py <= max(o["a"][1], o["b"][1]) + 1)
                     or (o["kind"] != "wire" and abs(o["at"][0] - px) <= 1.5 and abs(o["at"][1] - py) <= 1.5)]
            hx, hy = max(pad["hx"] - MICRO_L / 2 + 0.05, 0.0), max(pad["hy"] - MICRO_L / 2 + 0.05, 0.0)
            cands = []
            m = int(max(hx, hy) / 0.01) + 1
            for i in range(-m, m + 1):
                for j in range(-m, m + 1):
                    x, y = round(px + i * 0.01, 4), round(py + j * 0.01, 4)
                    if abs(x - px) <= hx + 1e-9 and abs(y - py) <= hy + 1e-9:
                        cands.append((math.hypot(x - px, y - py), x, y))
            cands.sort()
            spot = next(((x, y) for d, x, y in cands if land_ok(local, x, y, span_layers, own_vias)), None)
            if spot is None and rip:
                # THE TRACE UNDER THE PAD MOVES. With --rip, the foreign wires
                # on the inner layer within RIP_R of the pad are taken out (the
                # router reroutes their nets; they keep the rest of their
                # copper) and the search runs again.
                inner = 2 if side == 1 else 7
                gone = [o for o in local if o["kind"] == "wire" and inner in o["layers"]
                        and E.seg_pt(o["a"], o["b"], (px, py)) - o["radius"] < RIP_R]
                if gone:
                    for o in gone:
                        rips.setdefault(id(o), o)
                    local = [o for o in local if id(o) not in rips]
                    spot = next(((x, y) for d, x, y in cands if land_ok(local, x, y, span_layers, own_vias)), None)
                    print("  %-12s pad L%d (%.3f,%.3f): ripped %d foreign L%d segment(s) under it (%s)" % (
                        net, side, px, py, len(gone), inner, ", ".join(sorted(set(owner[id(o)] for o in gone)))))
            if spot is None:
                print("  ****  %-12s pad L%d (%.3f,%.3f): no room for a %d-%d microvia" % (net, side, px, py, lo, hi))
                continue
            x, y = spot
            adds.setdefault(net, "")
            adds[net] += '<via x="%s" y="%s" extent="%d-%d" drill="%s" diameter="%s"/>' % (g(x), g(y), lo, hi, g(MICRO_D), g(MICRO_L))
            own_vias.append({"kind": "via", "at": (x, y), "radius": MICRO_L / 2, "layers": span_layers})
            print("  %-12s pad L%d (%.3f,%.3f) -> %d-%d microvia at (%.3f,%.3f)" % (net, side, px, py, lo, hi, x, y))
    print("%d microvia(s) in %d net(s); %d foreign segment(s) ripped" % (sum(v.count("<via") for v in adds.values()), len(adds), len(rips)))
    if dry or not (adds or rips):
        return 0
    rip_by_net = {}
    for o in rips.values():
        rip_by_net.setdefault(owner[id(o)], []).append(o)

    def drop_wires(body, victims):
        def keep(m):
            a = (float(m.group(1)), float(m.group(2)))
            b = (float(m.group(3)), float(m.group(4)))
            L = int(m.group(6))
            for o in victims:
                if L in o["layers"] and ((abs(a[0] - o["a"][0]) < 1e-6 and abs(a[1] - o["a"][1]) < 1e-6 and abs(b[0] - o["b"][0]) < 1e-6 and abs(b[1] - o["b"][1]) < 1e-6)):
                    return ""
            return m.group(0)
        return re.sub(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"[^>]*/>', keep, body)

    def sub(m):
        body = m.group(3)
        if m.group(2) in rip_by_net:
            body = drop_wires(body, rip_by_net[m.group(2)])
        return m.group(1) + body + adds.get(m.group(2), "") + m.group(4)

    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
