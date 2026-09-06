# -*- coding: utf-8 -*-
"""Route each stranded GND pad to a real via, on the pad's own layer.

WHY THIS AND NOT ANOTHER VIA. Three via-based passes converged on the same
tiny yield -- 15 of 58 pads for stitch_pads, 13 of 61 islands for stitch_pour --
and the measurement that explains it is this one:

    L16   38 big orphan islands:  2 have room for a through via
                                 36 have room if only L16 mattered
    L1    23 big orphan islands:  2 / 22

The room is there. It is the sixth layer of it that is missing. A through via
is copper on all six layers and has to clear 2027 wires on L1, 1287 on L3, 1724
on L4 and 1392 on L16 -- with 1774 mm2 of board that is not available. A TRACE
on the pad's own layer has to clear one of those numbers, not all four, which
is the whole of the difference.

WHAT IT CONNECTS TO. A GND via, chosen by breadth-first distance from the pad,
never the pour. The pour is what put us here: an island holding a pad and no via
ties the pad to the island and the island to the pad while nothing reaches the
L2/L4 planes, which is the circularity check_planes used to score as grounded.
A via spans 1-16 by construction, so a copper path from pad to via is a
connection that cannot be argued with.

WHAT THIS IS NOT. It is not a rip-up. Nothing already routed moves. It adds
copper on one layer and takes the room it finds, which is why it is worth
trying before tearing up 6416 wires to make space for vias that a trace does
not need.

AN AIRWIRE ENDPOINT IS NOT A DISCONNECTED PAD, which cost a round of redundant
copper before it was understood. Eagle draws ONE ratsnest line between the two
nearest unconnected groups, so one end of it is routinely a pad that is
perfectly well grounded and the other is the one with the problem. targets()
takes both ends because it cannot tell them apart, so the work list runs about
two to one against the real fault, and routing the good end lays a path that is
already there -- 12 segments written for 5 pads were 12 duplicates, and R11's
pad, one of them, reaches a via at 0.0000 mm.

reach() is the answer to that: it floods from vias and plated holes through the
net's own wires on one layer and returns what is genuinely grounded, so a pad
is skipped on the evidence of the copper rather than on the ratsnest's hint.
The writer refuses a duplicate segment as a second line of defence.

    python tools/stitch_traces.py            report
    python tools/stitch_traces.py --apply    write the traces

Layer 19 in the file is stale afterwards -- recompute the ratsnest in Fusion.
"""
import io
import math
import os
import re
import sys
import collections
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E
import geom as G
import power as P

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")
NET = os.environ.get("STITCH_NET", "GND")
# Narrow, because this is a stitch and not a rail: every 0.05 mm of width is
# room the maze does not have to find. 0.25 is what power.py runs its rails at.
W = float(os.environ.get("STITCH_W", "0.25"))
STEP = 0.1
SKIP = ("U1",)


def element_of(b):
    """(x, y) -> element name, for the report only"""
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for pm in re.finditer(r'<package name="([^"]+)">(.*?)</package>',
                              lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)

    def rp(x, y, rot):
        r = re.sub(r"^M", "", rot)
        x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
        return (-x, y) if rot.startswith("M") else (x, y)

    out = {}
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"'
                         r'[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', b):
        nm, lib, pk = m.group(1), m.group(2), m.group(3)
        ex, ey, rot = float(m.group(4)), float(m.group(5)), m.group(6) or "R0"
        for s in re.finditer(r'<(?:smd|pad) name="[^"]+" x="([-\d.]+)" y="([-\d.]+)"',
                             pkg.get((lib, pk), "")):
            a = rp(float(s.group(1)), float(s.group(2)), rot)
            out[(round(ex + a[0], 2), round(ey + a[1], 2))] = nm
    return out


def targets(b):
    """pads the ratsnest still wants, as (x, y, side) -- Eagle's own verdict"""
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(NET), sig, re.S)
    if not m:
        return []
    pads = {}
    for onet, x, y, _hx, _hy, side in E.board_copper(b, skip=()):
        if onet == NET:
            pads[(round(x, 2), round(y, 2))] = (x, y, side)
    seen, out = set(), []
    for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                         r' y2="([-\d.]+)"[^>]*layer="19"', m.group(1)):
        a, c, d, e = [float(q) for q in w.groups()]
        for p in ((round(a, 2), round(c, 2)), (round(d, 2), round(e, 2))):
            if p in pads and p not in seen:
                seen.add(p)
                out.append(pads[p])
    return out


def main():
    raw = io.open(BRD, "rb").read()
    b = raw.decode("utf-8")
    clr = G.rule_mm(b, "mdWireWire")
    plan_clr = clr + 0.005
    w20 = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                     r' y2="([-\d.]+)" width="[\d.]+" layer="20"/>', b)
    xs = [float(q) for v in w20 for q in (v[0], v[2])]
    ys = [float(q) for v in w20 for q in (v[1], v[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))

    own = element_of(b)
    tgt = targets(b)
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    gm = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(NET), sig, re.S)
    vias = [(x, y) for x, y, _d in G.vias(gm.group(1))]
    print("%s: %d pad(s) wanted, %d via(s) to aim at, %.2f mm trace, clearance %.3f"
          % (NET, len(tgt), len(vias), W, clr))

    # one maze per surface: a trace clears its OWN layer and nothing else
    mz = {}
    for sd in (1, 16):
        mz[sd] = P.Maze(G.obstacles(b, frozenset((NET,)), sd, ()),
                        bx, plan_clr, W, STEP)

    # WHAT COUNTS AS GROUND, PER LAYER. A via spans 1-16 and a plated hole is
    # copper on every layer, so both reach the planes from either surface. A
    # trace this pass has already laid reaches a via by construction, so it
    # joins the target set the moment it is laid -- which is why the loop runs
    # until it stops making progress. A pad with no via in its reachable region
    # very often has a neighbour that does, and one hop through that neighbour
    # is a real connection, not a shortcut.
    holes = [(rec[1], rec[2]) for rec in E.board_copper(b, skip=())
             if rec[0] == NET and rec[5] == 0]
    tset = {1: list(vias) + holes, 16: list(vias) + holes}

    ground = {sd: G.surface_reach(gm.group(1), sd, vias + holes)
              for sd in (1, 16)}
    print("   copper already reaching a via: L1 %d point(s), "
          "L16 %d point(s)" % (len(ground[1]), len(ground[16])))
    work, laid, miss, skipped = [], [], [], collections.Counter()
    for px, py, side in tgt:
        nm = own.get((round(px, 2), round(py, 2)), "?")
        if nm in SKIP:
            skipped["%s -- the escape owns its balls" % nm] += 1
            continue
        if side == 0:
            skipped["plated hole (spans every layer already)"] += 1
            continue
        # AN AIRWIRE ENDPOINT IS NOT A DISCONNECTED PAD. Eagle draws one
        # ratsnest line between the two nearest unconnected GROUPS, so one end
        # of it is routinely a pad that is perfectly well grounded and the other
        # is the one with the problem. Taking both ends as work over-collects by
        # about two to one, and routing the good end lays a path that already
        # exists: 12 segments written for 5 pads on 2026-08-29 were 12 duplicates
        # of copper already on the board. R11 was one of them, and its pad
        # reaches a via at 0.0000 mm.
        #
        # So ask the copper, not the ratsnest, whether this pad is already
        # grounded -- reach() floods from vias and plated holes through the
        # net's own wires on the pad's own layer.
        if (round(px, 2), round(py, 2)) in ground[16 if side == 16 else 1]:
            skipped["already reaches a via through its own copper"] += 1
            continue
        work.append((nm, px, py, 16 if side == 16 else 1))

    rnd = 0
    while work:
        rnd += 1
        again, got = [], 0
        for nm, px, py, sd in work:
            m = mz[sd]
            dist, prev = m.bfs((px, py))
            if dist is None:
                miss.append((nm, px, py, sd, "pad is walled in"))
                continue
            best = None
            for vx, vy in tset[sd]:
                i, j = m.i(vx), m.j(vy)
                if not (0 <= i < m.W and 0 <= j < m.H):
                    continue
                c = j * m.W + i
                if dist[c] < 0:
                    continue
                if best is None or dist[c] < best[0]:
                    best = (dist[c], c, (vx, vy))
            if best is None:
                again.append((nm, px, py, sd))
                continue
            pts = m.walk(prev, best[1], (px, py), best[2])
            if not pts or len(pts) < 2:
                again.append((nm, px, py, sd))
                continue
            laid.append((nm, sd, pts))
            tset[sd] += pts
            got += 1
        print("   pass %d: routed %d, %d still open" % (rnd, got, len(again)))
        if not got:
            for nm, px, py, sd in again:
                miss.append((nm, px, py, sd, "no ground reachable on L%d" % sd))
            break
        work = again

    for k, n in skipped.most_common():
        print("   skipped %2d: %s" % (n, k))
    tot = sum(sum(math.hypot(p[1][0] - p[0][0], p[1][1] - p[0][1])
                  for p in zip(q[2], q[2][1:])) for q in laid)
    top = sum(1 for q in laid if q[1] == 1)
    print("   routed %d of %d pad(s): %.1f mm of %.2f mm trace  (L1 %d, L16 %d)"
          % (len(laid), len(tgt) - sum(skipped.values()), tot, W, top, len(laid) - top))
    if miss:
        why = collections.Counter(q[4] for q in miss)
        print("   could not route %d:" % len(miss))
        for k, n in why.most_common():
            print("      %-28s %d" % (k, n))
    if not laid:
        print("\nnothing to route")
        return 0
    ln = sorted(sum(math.hypot(p[1][0] - p[0][0], p[1][1] - p[0][1])
                    for p in zip(q[2], q[2][1:])) for q in laid)
    print("   path length: min %.2f, median %.2f, max %.2f mm"
          % (ln[0], ln[len(ln) // 2], ln[-1]))

    if "--apply" not in sys.argv:
        print("\nreport only -- re-run with --apply to write %d trace(s)" % len(laid))
        return 0

    g = E.g
    have = set()
    for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)"'
                         r' x2="([-\d.]+)" y2="([-\d.]+)"'
                         r' width="([\d.]+)" layer="(\d+)"', gm.group(1)):
        a, c, d, e = [round(float(q), 3) for q in w.groups()[:4]]
        have.add((tuple(sorted([(a, c), (d, e)])), w.group(6)))
    add, dup = [], 0
    for _nm, sd, pts in laid:
        for a, c in zip(pts, pts[1:]):
            if math.hypot(c[0] - a[0], c[1] - a[1]) < 1e-9:
                continue
            k = (tuple(sorted([(round(a[0], 3), round(a[1], 3)),
                                  (round(c[0], 3), round(c[1], 3))])), str(sd))
            if k in have:          # already on the board; never lay it twice
                dup += 1
                continue
            have.add(k)
            add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                       % (g(round(a[0], 3)), g(round(a[1], 3)),
                          g(round(c[0], 3)), g(round(c[1], 3)), g(W), sd))
    m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(NET), b)
    out = b[:m.end()] + "".join(add) + b[m.end():]
    ET.fromstring(out)
    io.open(BRD, "wb").write(out.encode("utf-8"))
    print("\nwrote %d segment(s) for %d pad(s) into %s" % (len(add), len(laid), BRD))
    print("layer 19 is now STALE -- recompute the ratsnest in Fusion")
    return 0


if __name__ == "__main__":
    sys.exit(main())
