# -*- coding: utf-8 -*-
"""Plan U1's escapes instead of letting the router improvise them: every
ball with a microvia gets a stub on the microvia's layer that leaves the
ball field, so no net is boxed at its own ball by the nets routed before it.

    python tools/bga_escape.py in.brd out.brd [--nets A,B]

WHY. With rings 1-3 on microvias the L2 lands sit 0.30 mm apart and each
gap between two ring-1 lands fits exactly one 3 mil trace. Routed one net
at a time, the first nets through take whichever gap is nearest and the
last ones find their land walled in (RAS# had 63 free cells around its
ball after run t2, 2026-09-06). A fan-out pattern fixes the gaps up front,
like any BGA design: ring 1 straight out on L2, ring 2 through the gap on
its outward side (always the +y / +x neighbour gap, so no two balls share
one), ring 3 straight out on L3 from its staggered 2-3 via, where rings 1
and 2 have no copper at all.

WHAT IT DOES, per signal ball of U1 that has a 1-2 microvia and no copper
on the land yet: writes the stub (STUB_W wide) to END beyond the ring-1
line, checking every leg against all foreign copper and the stubs already
placed; a ring-3 ball uses its 2-3 via and L3. Balls whose stub does not
fit are reported and left as they are. Prints and writes out.brd.nets.
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
STUB_W = 0.0762
BEYOND = 0.55      # stub end this far outside the ring-1 centre line
PITCH = 0.5


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
    exclude = set()
    if "--exclude" in args:
        # balls that escape inward (tools/bga_inward.py) get no outward stub
        i = args.index("--exclude")
        exclude = set(args[i + 1].split(","))
        del args[i:i + 2]
    force = set()
    if "--force" in args:
        # nets the router will strip to their escapes: only their KEPT copper
        # is an obstacle here, the rest is gone before any stub matters
        i = args.index("--force")
        force = set(n for n in io.open(args[i + 1]).read().replace("\n", ",").split(",") if n.strip())
        del args[i:i + 2]
    src, dst = args[0], args[1]
    board = io.open(src, encoding="utf-8", errors="replace").read()
    parsed = C.parse_signal_objects(board)
    kept_keys = {}
    if force:
        os.environ.setdefault("CLOSE_BOARD", src)
        import close_airwires as CA
        pads, fields = CA.pad_index(board)
        zones = [(fields[el][0], fields[el][1], r) for el, r in CA.ZONE_R.items() if el in fields] + CA.EXTRA_ZONES
        padobjs = {}
        for key, p in pads.items():
            if p["net"]:
                padobjs.setdefault(p["net"], []).append(p)
        sig = dict((m.group(2), (m.group(1), m.group(3))) for m in CA.SIG_RE.finditer(board))
        for n in force:
            if n not in sig:
                continue
            net = CA.Net(n, sig[n][0], sig[n][1], padobjs.get(n, []), zones, force=True)
            keys = set()
            for o in net.kept:
                if o["kind"] == "wire":
                    keys.add(("wire", round(o["a"][0], 4), round(o["a"][1], 4), round(o["b"][0], 4), round(o["b"][1], 4)))
                elif o["kind"] == "via":
                    keys.add(("via", round(o["at"][0], 4), round(o["at"][1], 4)))
            kept_keys[n] = keys
        print("obstacles of %d forced net(s) reduced to their kept escapes" % len(kept_keys))

    def obstacle(o, net):
        """does this foreign object survive the router's strip?"""
        if net not in kept_keys or o["kind"] == "pad":
            return True
        if o["kind"] == "wire":
            return ("wire", round(o["a"][0], 4), round(o["a"][1], 4), round(o["b"][0], 4), round(o["b"][1], 4)) in kept_keys[net]
        return ("via", round(o["at"][0], 4), round(o["at"][1], 4)) in kept_keys[net]

    owner = {}
    for net, (objects, terminals, planes) in parsed.items():
        for o in objects:
            owner[id(o)] = net
    balls = [(n, x, y) for n, x, y, hx, hy, side in E.board_copper(board, skip=())
             if side == 1 and abs(hx - 0.1125) < 0.01 and 41 < x < 52 and 7 < y < 17 and n]
    xs = sorted(set(round(x, 2) for n, x, y in balls))
    ys = sorted(set(round(y, 2) for n, x, y in balls))
    ng = len(xs)
    x_lo, x_hi, y_lo, y_hi = xs[0], xs[-1], ys[0], ys[-1]
    placed = []      # stubs of every net placed in this run, as wire objects
    adds, done, skipped = {}, [], []

    def stub_obj(a, b, L):
        return {"kind": "wire", "a": a, "b": b, "radius": STUB_W / 2, "layers": frozenset((L,))}

    def side_of(i, j):
        """(dx, dy) outward unit step for a ball at grid (i, j): the nearer
        edge; ties go to the west/east edge"""
        d = {"w": i, "e": ng - 1 - i, "s": j, "n": ng - 1 - j}
        k = min(d, key=lambda s: (d[s], "wesn".index(s)))
        return {"w": (-1, 0), "e": (1, 0), "s": (0, -1), "n": (0, 1)}[k]

    for n, x, y in sorted(balls, key=lambda t: (t[1], t[2])):
        if n in BM.PLANE or n.startswith("VCC") or (only and n not in only) or n in exclude:
            continue
        i, j = xs.index(round(x, 2)), ys.index(round(y, 2))
        ring = min(i, j, ng - 1 - i, ng - 1 - j) + 1
        objs = parsed[n][0]
        v12 = [o for o in objs if o["kind"] == "via" and o["layers"] == frozenset((1, 2)) and math.hypot(o["at"][0] - x, o["at"][1] - y) < 0.05]
        if not v12:
            continue
        v23 = [o for o in objs if o["kind"] == "via" and o["layers"] == frozenset((2, 3)) and math.hypot(o["at"][0] - x, o["at"][1] - y) < 0.4]
        dx, dy = side_of(i, j)
        if v23:
            L = 3
            start = tuple(v23[0]["at"])
            # already escaped on L3?
            if any(o["kind"] == "wire" and 3 in o["layers"] and (E.seg_pt(o["a"], o["b"], start) < 0.05) for o in objs):
                continue
        else:
            L = 2
            start = (x, y)
            if any(o["kind"] == "wire" and 2 in o["layers"] and E.seg_pt(o["a"], o["b"], start) < 0.05 for o in objs):
                continue
        # the end line beyond ring 1
        if dx:
            end_x = (x_lo - BEYOND) if dx < 0 else (x_hi + BEYOND)
        else:
            end_y = (y_lo - BEYOND) if dy < 0 else (y_hi + BEYOND)
        legs = []
        if L == 3:
            # straight out along the 2-3 via's own line (already off the ball rows by 0.25)
            end = (end_x, start[1]) if dx else (start[0], end_y)
            legs = [(start, end)]
        elif ring == 1:
            end = (end_x, y) if dx else (x, end_y)
            legs = [(start, end)]
        else:
            # ring 2 and deeper: a diagonal to the gap on the +y (or +x) side of
            # the ring-1 neighbour, then straight out
            if dx:
                gap = (x + dx * PITCH, y + PITCH / 2)
                end = (end_x, gap[1])
            else:
                gap = (x + PITCH / 2, y + dy * PITCH)
                end = (gap[0], end_y)
            legs = [(start, gap), (gap, end)]
        foreign = [o for o in PM.foreign_copper(board, parsed, n) if obstacle(o, owner.get(id(o)))]
        local = [o for o in foreign if (o["kind"] == "wire" and min(o["a"][0], o["b"][0]) - 2 <= x <= max(o["a"][0], o["b"][0]) + 2
                                         and min(o["a"][1], o["b"][1]) - 2 <= y <= max(o["a"][1], o["b"][1]) + 2)
                 or (o["kind"] != "wire" and abs(o["at"][0] - x) <= 2.5 and abs(o["at"][1] - y) <= 2.5)] + placed
        ok = all(GS.wire_ok(local, a, b, STUB_W, L) for a, b in legs)
        if not ok and L == 3:
            # a plane ball's through via beside the line: jog one gap line
            # over (a 45-degree leg across the ball row) and run out from there
            for s in (1, -1):
                if dx:
                    knee = (start[0] + dx * PITCH, start[1] + s * PITCH)
                    end = (end_x, knee[1])
                else:
                    knee = (start[0] + s * PITCH, start[1] + dy * PITCH)
                    end = (knee[0], end_y)
                legs = [(start, knee), (knee, end)]
                ok = all(GS.wire_ok(local, a, b, STUB_W, L) for a, b in legs)
                if ok:
                    break
        if not ok and ring >= 2 and L == 2:
            # the other gap
            if dx:
                gap = (x + dx * PITCH, y - PITCH / 2)
                end = (end_x, gap[1])
            else:
                gap = (x - PITCH / 2, y + dy * PITCH)
                end = (gap[0], end_y)
            legs = [(start, gap), (gap, end)]
            ok = all(GS.wire_ok(local, a, b, STUB_W, L) for a, b in legs)
        if not ok:
            skipped.append(n)
            print("  ****  %-12s ball (%.2f,%.2f) ring %d: stub on L%d blocked" % (n, x, y, ring, L))
            continue
        add = ""
        for a, b in legs:
            add += '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%d"/>' % (g(a[0]), g(a[1]), g(b[0]), g(b[1]), g(STUB_W), L)
            placed.append(stub_obj(a, b, L))
        adds[n] = adds.get(n, "") + add
        done.append(n)
        print("  %-12s ball (%.2f,%.2f) ring %d: L%d stub to (%.2f,%.2f)" % (n, x, y, ring, L, end[0], end[1]))
    print("stubs placed for %d ball(s); skipped %d: %s" % (len(done), len(skipped), ",".join(skipped) or "-"))

    def sub(m):
        return m.group(1) + m.group(3) + adds.get(m.group(2), "") + m.group(4)

    out = SIG_RE.sub(sub, board)
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(dst, "w", encoding="utf-8", newline="").write(out)
    io.open(dst + ".nets", "w").write(",".join(sorted(set(done))))
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
