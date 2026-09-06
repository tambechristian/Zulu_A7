# -*- coding: utf-8 -*-
"""Ring 3 of U1 on the second build-up layer: a 1-2 microvia in the ball, a
staggered 2-3 microvia on the diagonal towards the centre, and the L2 hop
between them, so the net escapes on L3.

    python tools/bga_fanout3.py in.brd out.brd [--rip] [--nets A,B]

WHY. On the 2+4+2 build (tools/stackup_242.py) L3 is the second escape
layer. Rings 1 and 2 stop at L2, so L3 under the footprint holds nothing of
theirs; a ring-3 net that reaches L3 at the ball can run outward under rings
1 and 2 on L3 and cross the corridor west of U1 as a trace, needing no via
site there. Staggered rather than stacked: the 2-3 via sits 0.354 mm from
the 1-2 via, which keeps Fusion's Drill Distance rule (0.20 mm) and
PCBWay's cheaper option; it lands on the diagonal towards the empty
annulus, where L2 carries no ring-1/2 escapes.

WHAT IT DOES, per ring-3 signal ball: adds the 1-2 microvia if missing (the
L2 land must clear foreign copper; --rip takes foreign L2 wires under the
ball out), picks the inward diagonal spot for the 2-3 microvia whose land
clears foreign copper on L2 and L3 and whose drill keeps DRILL_CC from every
other drill (--rip clears L2/L3 wires there too), and writes the L2 hop.
Prints the converted nets and writes them to out.brd.nets for CLOSE_FORCE.
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
import gnd_stitch as GS   # noqa: E402

SIG_RE = re.compile(r'(<signal name="([^"]+)"[^>]*>)(.*?)(</signal>)', re.S)
HOP_W = 0.0762


def g(v):
    t = ("%.4f" % v).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def main():
    args = sys.argv[1:]
    rip = "--rip" in args
    only = None
    if "--nets" in args:
        i = args.index("--nets")
        only = set(args[i + 1].split(","))
        del args[i:i + 2]
    args = [a for a in args if a != "--rip"]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    owner = {}
    for net, (objects, terminals, planes) in parsed.items():
        for o in objects:
            owner[id(o)] = net
    balls = [(n, x, y) for n, x, y, hx, hy, side in E.board_copper(board, skip=())
             if side == 1 and abs(hx - 0.1125) < 0.01 and 41 < x < 52 and 7 < y < 17 and n]
    xs = sorted(set(round(x, 2) for n, x, y in balls))
    ys = sorted(set(round(y, 2) for n, x, y in balls))
    ci = dict((x, i) for i, x in enumerate(xs))
    ri = dict((y, j) for j, y in enumerate(ys))
    ng = len(xs)
    cx, cy = (xs[0] + xs[-1]) / 2.0, (ys[0] + ys[-1]) / 2.0
    adds, rips, converted, skipped = {}, {}, [], []
    placed = []   # vias added in this run, any net: two neighbouring balls must not pick the same diagonal

    def rippable(o):
        # never rip a plane or power net's copper for an escape: a ball whose
        # spot is under VU or VCC1V8 is skipped instead
        nm = owner[id(o)]
        return nm not in BM.PLANE and not nm.startswith("VCC")

    for n, x, y in sorted(balls, key=lambda t: (t[1], t[2])):
        if n in BM.PLANE or n.startswith("VCC") or (only and n not in only):
            continue
        i, j = ci[round(x, 2)], ri[round(y, 2)]
        if min(i, j, ng - 1 - i, ng - 1 - j) + 1 != 3:
            continue
        objects = parsed[n][0]
        # THE OLD ESCAPE GOES. The ball's dogbone through via sits 0.15 to
        # 0.35 mm from the ball and its L1 stub leads to it; both are what
        # the microvias replace, so they are deleted here (and ignored in the
        # drill check) rather than left to block the very via that replaces
        # them. The rest of the old route dangles until the router re-routes
        # the net from the 2-3 via.
        old_esc = [o for o in objects if (o["kind"] == "via" and len(o["layers"]) > 2 and math.hypot(o["at"][0] - x, o["at"][1] - y) < 0.6)
                   or (o["kind"] == "wire" and 1 in o["layers"] and min(math.hypot(o["a"][0] - x, o["a"][1] - y), math.hypot(o["b"][0] - x, o["b"][1] - y)) < 0.6)]
        for o in old_esc:
            rips[id(o)] = o
        pending = list(old_esc)   # taken back out of rips if this ball is skipped
        own_vias = [o for o in objects if o["kind"] == "via" and id(o) not in rips]
        foreign = PM.foreign_copper(board, parsed, n)
        local = [o for o in foreign if (o["kind"] == "wire" and min(o["a"][0], o["b"][0]) - 1 <= x <= max(o["a"][0], o["b"][0]) + 1
                                         and min(o["a"][1], o["b"][1]) - 1 <= y <= max(o["a"][1], o["b"][1]) + 1)
                 or (o["kind"] != "wire" and abs(o["at"][0] - x) <= 1.5 and abs(o["at"][1] - y) <= 1.5)]
        local = [o for o in local if id(o) not in rips]
        add = ""
        # 1-2 in the ball
        has12 = any(v["layers"] == frozenset((1, 2)) and math.hypot(v["at"][0] - x, v["at"][1] - y) < 0.12 for v in own_vias)
        if not has12:
            ok = PM.land_ok(local, x, y, frozenset((1, 2)), own_vias + placed)
            if not ok and rip:
                gone = [o for o in local if o["kind"] == "wire" and 2 in o["layers"] and rippable(o) and E.seg_pt(o["a"], o["b"], (x, y)) - o["radius"] < PM.RIP_R]
                for o in gone:
                    rips[id(o)] = o
                local = [o for o in local if id(o) not in rips]
                ok = PM.land_ok(local, x, y, frozenset((1, 2)), own_vias + placed)
            if not ok:
                skipped.append(n)
                for o in pending:
                    rips.pop(id(o), None)   # the old escape stays: the ball is not converted
                print("  ****  %-12s ball (%.2f,%.2f): no room for the 1-2 microvia; old escape kept" % (n, x, y))
                continue
            add += '<via x="%s" y="%s" extent="1-2" drill="%s" diameter="%s"/>' % (g(x), g(y), g(PM.MICRO_D), g(PM.MICRO_L))
            own_vias.append({"kind": "via", "at": (x, y), "radius": PM.MICRO_L / 2, "layers": frozenset((1, 2))})
            placed.append(own_vias[-1])
        # 2-3 on the inward diagonal
        sx = 1 if x < cx else -1
        sy = 1 if y < cy else -1
        cands = [(x + sx * 0.25, y + sy * 0.25), (x + sx * 0.25, y - sy * 0.25), (x - sx * 0.25, y + sy * 0.25)]
        spot = None
        for vx, vy in cands:
            vx, vy = round(vx, 4), round(vy, 4)
            vias_here = [v for v in own_vias if math.hypot(v["at"][0] - vx, v["at"][1] - vy) < 0.05]
            if vias_here:
                spot = (vx, vy, True)
                break
            others = [v for v in own_vias if math.hypot(v["at"][0] - vx, v["at"][1] - vy) >= 0.05] + placed   # another ball's new via at this spot must count
            ok = PM.land_ok(local, vx, vy, frozenset((2, 3)), others) and GS.wire_ok(local, (x, y), (vx, vy), HOP_W, 2)
            if not ok and rip:
                gone = [o for o in local if o["kind"] == "wire" and (o["layers"] & frozenset((2, 3))) and rippable(o)
                        and E.seg_pt(o["a"], o["b"], (vx, vy)) - o["radius"] < PM.RIP_R]
                if gone:
                    for o in gone:
                        rips[id(o)] = o
                    local = [o for o in local if id(o) not in rips]
                    ok = PM.land_ok(local, vx, vy, frozenset((2, 3)), others) and GS.wire_ok(local, (x, y), (vx, vy), HOP_W, 2)
                    print("  %-12s ball (%.2f,%.2f): ripped %d foreign L2/L3 segment(s) at (%.2f,%.2f) (%s)" % (
                        n, x, y, len(gone), vx, vy, ", ".join(sorted(set(owner[id(o)] for o in gone)))))
            if ok:
                spot = (vx, vy, False)
                break
        if spot is None:
            skipped.append(n)
            for o in pending:
                rips.pop(id(o), None)
            add = ""   # and no 1-2 microvia either: the old escape is what connects this ball
            print("  ****  %-12s ball (%.2f,%.2f): no room for the 2-3 microvia; old escape kept" % (n, x, y))
            continue
        vx, vy, existed = spot
        if not existed:
            add += '<via x="%s" y="%s" extent="2-3" drill="%s" diameter="%s"/>' % (g(vx), g(vy), g(PM.MICRO_D), g(PM.MICRO_L))
            add += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="2"/>' % (g(x), g(y), g(vx), g(vy), g(HOP_W))
            placed.append({"kind": "via", "at": (vx, vy), "radius": PM.MICRO_L / 2, "layers": frozenset((2, 3))})
        elif not any(o["kind"] == "wire" and 2 in o["layers"] and id(o) not in rips
                     and ((E.seg_pt(o["a"], o["b"], (x, y)) < 0.02 and E.seg_pt(o["a"], o["b"], (vx, vy)) < 0.02))
                     for o in objects):
            # the via is there but its L2 hop is gone (bga_microvias --rip on a
            # neighbouring ball takes foreign L2 wires within 0.45 mm, and the
            # hop's far end is 0.35 mm from the next ball): put it back
            add += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="2"/>' % (g(x), g(y), g(vx), g(vy), g(HOP_W))
            print("  %-12s ball (%.2f,%.2f): L2 hop to the 2-3 via restored" % (n, x, y))
        adds[n] = adds.get(n, "") + add
        converted.append(n)
        print("  %-12s ball (%.2f,%.2f) -> 1-2 in the ball, 2-3 at (%.2f,%.2f)" % (n, x, y, vx, vy))
    print("converted nets (%d): %s" % (len(set(converted)), ",".join(sorted(set(converted)))))
    if skipped:
        print("skipped (%d): %s" % (len(skipped), ",".join(skipped)))
    rip_by_net = {}
    for o in rips.values():
        rip_by_net.setdefault(owner[id(o)], []).append(o)

    def drop_wires(body, victims):
        wires = [o for o in victims if o["kind"] == "wire"]
        vias = [o for o in victims if o["kind"] == "via"]

        def keep(m):
            a = (float(m.group(1)), float(m.group(2)))
            b = (float(m.group(3)), float(m.group(4)))
            L = int(m.group(6))
            for o in wires:
                if L in o["layers"] and abs(a[0] - o["a"][0]) < 1e-6 and abs(a[1] - o["a"][1]) < 1e-6 and abs(b[0] - o["b"][0]) < 1e-6 and abs(b[1] - o["b"][1]) < 1e-6:
                    return ""
            return m.group(0)

        def keep_via(m):
            at = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
            if "x" in at:
                vx, vy = float(at["x"]), float(at["y"])
                for o in vias:
                    if abs(vx - o["at"][0]) < 1e-6 and abs(vy - o["at"][1]) < 1e-6:
                        return ""
            return m.group(0)
        body = re.sub(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"[^>]*/>', keep, body)
        return re.sub(r"<via\s[^>]*?(?:/>|>\s*</via>)", keep_via, body, flags=re.S)

    def sub(m):
        body = m.group(3)
        if m.group(2) in rip_by_net:
            body = drop_wires(body, rip_by_net[m.group(2)])
        return m.group(1) + body + adds.get(m.group(2), "") + m.group(4)

    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    victims = sorted(set(owner[id(o)] for o in rips.values()) - set(converted))
    io.open(dst + ".nets", "w").write(",".join(sorted(set(converted)) + victims))
    print("wrote %s (%d segment(s) ripped; nets whose copper was ripped and must be re-routed too: %s)" % (
        dst, len(rips), ",".join(victims) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
