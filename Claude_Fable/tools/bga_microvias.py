# -*- coding: utf-8 -*-
"""Put a 1-2 laser microvia into chosen signal balls of U1, so those nets
escape on L2 instead of on L1 to a through via in the corridor.

    python tools/bga_microvias.py in.brd out.brd --cols 42.0,42.5,43.0 [--rows y1,y2] [--rip]
    python tools/bga_microvias.py in.brd out.brd --all-signal [--rip]

WHY. U1 (0.5 mm pitch, rings 1-3 populated, power in the centre) escapes
every west ball on L1 to one column of through vias at x 39.2, and that
column plus the L1 stubs is the wall that boxes the SDRAM nets (see
board/STACKUP.md, 2026-09-06). The 1+6+1 build exists to do this instead:
a 0.10/0.20 microvia in the ball, an L2 escape, and a through via wherever
there is room -- 0.5 mm pitch leaves 0.30 mm between lands, one 3 mil trace
per gap. Plane balls keep their through vias to L3/L5.

WHAT IT DOES. For each selected ball whose net is a signal (not a plane or
power net), and which has no microvia yet, place a 1-2 microvia at the ball
centre when the L2 land clears foreign copper by the 3 mil rule and every
overlapping drill by DRILL_CC; with --rip, foreign L2 wires under the ball
are taken out first (their nets reroute). Prints the converted nets, which
the caller hands to close_airwires.py as CLOSE_FORCE: with a via in the pad
the router now keeps only that as the escape and drops the L1 stub and the
old through via, so the corridor empties as the nets re-route.
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

PLANE = set(("GND", "VCC3V3", "VCC1V0", "VCC1V8", "VCCADC", "GNDADC", "VU", "VEXT", "USB5V0"))
SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def main():
    args = sys.argv[1:]
    cols = rows = None
    if "--cols" in args:
        i = args.index("--cols")
        cols = set(round(float(v), 2) for v in args[i + 1].split(","))
        del args[i:i + 2]
    if "--rows" in args:
        i = args.index("--rows")
        rows = set(round(float(v), 2) for v in args[i + 1].split(","))
        del args[i:i + 2]
    all_signal = "--all-signal" in args
    rip = "--rip" in args
    args = [a for a in args if a not in ("--all-signal", "--rip")]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    owner = {}
    for net, (objects, terminals, planes) in parsed.items():
        for o in objects:
            owner[id(o)] = net
    balls = [(n, x, y) for n, x, y, hx, hy, side in E.board_copper(board, skip=())
             if side == 1 and abs(hx - 0.1125) < 0.01 and 41 < x < 52 and 7 < y < 17 and n]
    chosen = []
    for n, x, y in balls:
        if n in PLANE or n.startswith("VCC"):
            continue
        if not all_signal:
            if cols is not None and round(x, 2) not in cols:
                continue
            if rows is not None and round(y, 2) not in rows:
                continue
        chosen.append((n, x, y))
    print("%d signal ball(s) selected" % len(chosen))
    adds, rips, converted, skipped = {}, {}, [], []
    span = frozenset((1, 2))
    for n, x, y in sorted(chosen, key=lambda t: (t[1], t[2])):
        objects = parsed[n][0]
        own_vias = [o for o in objects if o["kind"] == "via"]
        if any(len(v["layers"]) <= 2 and math.hypot(v["at"][0] - x, v["at"][1] - y) < 0.12 for v in own_vias):
            converted.append(n)
            print("  %-12s ball (%.2f,%.2f): microvia already there" % (n, x, y))
            continue
        foreign = PM.foreign_copper(board, parsed, n)
        local = [o for o in foreign if (o["kind"] == "wire" and min(o["a"][0], o["b"][0]) - 1 <= x <= max(o["a"][0], o["b"][0]) + 1
                                         and min(o["a"][1], o["b"][1]) - 1 <= y <= max(o["a"][1], o["b"][1]) + 1)
                 or (o["kind"] != "wire" and abs(o["at"][0] - x) <= 1.5 and abs(o["at"][1] - y) <= 1.5)]
        ok = PM.land_ok(local, x, y, span, own_vias)
        if not ok and rip:
            gone = [o for o in local if o["kind"] == "wire" and 2 in o["layers"] and E.seg_pt(o["a"], o["b"], (x, y)) - o["radius"] < PM.RIP_R]
            for o in gone:
                rips[id(o)] = o
            local = [o for o in local if id(o) not in rips]
            ok = PM.land_ok(local, x, y, span, own_vias)
            if gone:
                print("  %-12s ball (%.2f,%.2f): ripped %d foreign L2 segment(s) (%s)" % (n, x, y, len(gone), ", ".join(sorted(set(owner[id(o)] for o in gone)))))
        if not ok:
            skipped.append(n)
            print("  ****  %-12s ball (%.2f,%.2f): no room for a 1-2 microvia" % (n, x, y))
            continue
        adds.setdefault(n, "")
        adds[n] += '<via x="%s" y="%s" extent="1-2" drill="%s" diameter="%s"/>' % (g(x), g(y), g(PM.MICRO_D), g(PM.MICRO_L))
        converted.append(n)
        print("  %-12s ball (%.2f,%.2f) -> 1-2 microvia" % (n, x, y))
    print("converted nets (%d): %s" % (len(set(converted)), ",".join(sorted(set(converted)))))
    if skipped:
        print("skipped (%d): %s" % (len(skipped), ",".join(skipped)))
    rip_by_net = {}
    for o in rips.values():
        rip_by_net.setdefault(owner[id(o)], []).append(o)

    def drop_wires(body, victims):
        def keep(m):
            a = (float(m.group(1)), float(m.group(2)))
            b = (float(m.group(3)), float(m.group(4)))
            L = int(m.group(6))
            for o in victims:
                if L in o["layers"] and abs(a[0] - o["a"][0]) < 1e-6 and abs(a[1] - o["a"][1]) < 1e-6 and abs(b[0] - o["b"][0]) < 1e-6 and abs(b[1] - o["b"][1]) < 1e-6:
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
    io.open(dst + ".nets", "w").write(",".join(sorted(set(converted))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
