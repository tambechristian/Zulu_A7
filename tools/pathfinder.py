# -*- coding: utf-8 -*-
"""Negotiated-congestion routing (PathFinder) over two layers and the vias between.

WHY THIS EXISTS. signals.py routes greedily and then rips up whatever is in the
way, and it tops out at 21 of 39 SDRAM nets. That is not the board: the narrowest
vertical cut every bus net has to cross carries 108 lanes at 0.10 mm trace and
0.09 mm clearance, and each of the 18 failures routes perfectly well against an
empty board. It is the algorithm. Rip-up with no memory does not converge -- it
trades the same nets back and forth, and pushing it harder makes it worse rather
than better: rip limit 4 gave 21 nets, 8 gave 17, and 25 gave 19 after 789
rip-ups and twenty minutes.

WHAT PATHFINDER DOES DIFFERENTLY (Nair 1987; Betz and Rose's VPR popularised it).
Let the nets overlap. Route every one by shortest path, allowing them to share
cells, then make sharing progressively more expensive:

    cost(cell) = base + hfac * history[cell] + pfac * occupancy[cell]

`occupancy` is how many nets sit on the cell right now and `pfac` grows each
iteration, so a net with an alternative takes it while a net with none keeps the
cell. `history` accumulates over every iteration a cell was oversubscribed, and
it is the part that converges where plain rip-up does not: it is a memory of
contention, so the router stops re-making the same mistake next time round. When
no cell carries more than one net the routing is legal by construction.

THE VIA IS AN EDGE, NOT A DECISION. The graph is L3 and L16 stacked, with an
edge between them at every cell where a through via would be legal. The router
places the fan-out via while finding the path, at whatever a layer change is
worth in VIA_COST -- nothing to pre-place and nothing to guess. Same conclusion
attempt_split reached, generalised.

COSTS ARE INTEGERS in units of STEP_COST, so the priority queue stays cheap.
Nodes are layer_index * NN + cell, sharing power.Maze's cell indexing.
"""

import os, sys, math, heapq, collections
from array import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STEP_COST = 10
VIA_COST = int(os.environ.get("VIA_COST", "90"))
HFAC = int(os.environ.get("HFAC", "0"))          # 0 -> one step per history unit
PFAC0 = float(os.environ.get("PFAC0", "0.5"))
PGROW = float(os.environ.get("PGROW", "1.8"))
# Past a few thousand, pfac stops carrying information: every route is then
# dominated by congestion, the search thrashes and the residue oscillates
# instead of settling. Left uncapped it reached 1.3e7 and finished WORSE
# (28 of 39 over 40 iterations) than a capped run half the length (33).
PCAP = float(os.environ.get("PCAP", "4000"))


class Router(object):
    def __init__(self, mz, vfree, layers):
        self.layers = list(layers)
        self.mz = mz
        m0 = mz[self.layers[0]]
        self.W, self.H, self.step, self.bx = m0.W, m0.H, m0.step, m0.bx
        self.NN = self.W * self.H
        self.free = [bytearray(mz[L].free) for L in self.layers]
        self.vfree = vfree
        n = self.NN * len(self.layers)
        self.hist = array("i", [0]) * n
        self.occ = array("i", [0]) * n
        self.dist = array("i", [0]) * n
        self.prev = array("i", [-1]) * n
        self.stamp = array("i", [0]) * n
        self.gen = 0
        self.hfac = HFAC or STEP_COST

    def cell(self, p):
        m = self.mz[self.layers[0]]
        return m.j(p[1]) * self.W + m.i(p[0])

    def xy(self, c):
        return (self.bx[0] + (c % self.W) * self.step,
                self.bx[1] + (c // self.W) * self.step)

    def open_cells(self, li, cells, on):
        """temporarily free, or re-block, a net's own fixed copper.

        The base grids treat EVERY net's copper as an obstacle, including the
        group's own escape vias and U3 pads. That is right for all the other
        members and wrong for the one being routed, which has to start on its own
        ring via and end on its own pad -- so its cells are opened for the
        duration of its search and closed again afterwards. Excluding the whole
        group from the base instead is what put three holes in signals.py.
        """
        f = self.free[li]
        for c in cells:
            f[c] = 1 if on else 0

    def route(self, srcs, dsts, pfac, box):
        """cheapest path from any src node to any dst node under current congestion"""
        self.gen += 1
        gen = self.gen
        dist, prev, stamp, occ, hist = (self.dist, self.prev, self.stamp,
                                        self.occ, self.hist)
        NN, W = self.NN, self.W
        i0, j0, i1, j1 = box
        pf = int(round(pfac * STEP_COST))
        hf = self.hfac
        dset = set(li * NN + c for li, c in dsts)
        pq = []
        for li, c in srcs:
            if not self.free[li][c]:
                continue
            n = li * NN + c
            dist[n] = 0
            prev[n] = -1
            stamp[n] = gen
            heapq.heappush(pq, (0, n))
        if not pq:
            return None
        nl = len(self.layers)
        while pq:
            d, n = heapq.heappop(pq)
            if stamp[n] != gen or d > dist[n]:
                continue
            if n in dset:
                out = []
                while n >= 0:
                    out.append(n)
                    n = prev[n]
                out.reverse()
                return out
            li, c = divmod(n, NN)
            i, j = c % W, c // W
            fl = self.free[li]
            for step, ni, nj in ((-1, i - 1, j), (1, i + 1, j),
                                 (-W, i, j - 1), (W, i, j + 1)):
                if not (i0 <= ni <= i1 and j0 <= nj <= j1):
                    continue
                q = c + step
                if not fl[q]:
                    continue
                m = li * NN + q
                w = d + STEP_COST + hf * hist[m] + pf * occ[m]
                if stamp[m] != gen or w < dist[m]:
                    stamp[m] = gen
                    dist[m] = w
                    prev[m] = n
                    heapq.heappush(pq, (w, m))
            if nl > 1 and self.vfree[c]:
                for lo in range(nl):
                    if lo == li or not self.free[lo][c]:
                        continue
                    m = lo * NN + c
                    w = d + VIA_COST + hf * hist[m] + pf * occ[m]
                    if stamp[m] != gen or w < dist[m]:
                        stamp[m] = gen
                        dist[m] = w
                        prev[m] = n
                        heapq.heappush(pq, (w, m))
        return None

    def foot_sample_step(self, sample):
        return sample * self.step

    def set_footprint(self, w, clr, via_d=0.30, sample=1):
        # SAMPLE EVERY NODE, not every second one. Stamping alternate nodes and
        # inflating the radius to cover the gap between them is only sound if the
        # path is STRAIGHT. These paths are 4-connected staircases: skip a node
        # on a diagonal run and the nearest stamp to a point sits at a (3, 3)
        # cell offset instead of (3, 2), which is 0.2121 against a radius of
        # 0.1965 -- outside, so the cell is never marked. JA3 and JA4 came out
        # 0.1803 apart where 0.19 was required, and stayed there through a revert
        # of the straightening because the raw paths were already too close.
        """the disc a net's centreline projects onto its neighbours.

        OCCUPANCY HAS TO BE THE CLEARANCE ENVELOPE, NOT THE CELL. Two traces need
        their centrelines `w + clr` apart -- 0.19 mm here. Counting only the cell
        a path passes through would call two nets on ADJACENT cells legal, and
        they would be 0.05 mm apart. So a path marks every node within 0.19 mm of
        it, and "no node used twice" then means what it should.

        Sampled every `sample` cells rather than every cell, which is what keeps
        the bookkeeping affordable: the union of discs of radius r spaced d apart
        pinches to sqrt(r^2 - (d/2)^2), so at d = 0.10 mm the thinnest the
        envelope ever gets is 0.183 mm against the 0.19 it is standing in for.
        """
        # RADIUS CORRECTED FOR THE SAMPLING. The envelope stands for "no other
        # centreline within w + clr", but it is stamped every `sample` cells, and
        # the union of discs of radius r spaced d apart pinches to
        # sqrt(r^2 - (d/2)^2) between stamps. At r = 0.19 and d = 0.10 that is
        # 0.183, so the router could legally place two traces 0.183 apart and
        # check_board would call it 0.0803 against a 0.0900 rule -- which is
        # exactly the four violations this produced. Inflate r so the PINCH is
        # w + clr rather than the peak.
        r = math.hypot(w + clr, self.foot_sample_step(sample) / 2.0)
        rr = int(r / self.step) + 1
        self.foot_off = [dj * self.W + di
                         for di in range(-rr, rr + 1)
                         for dj in range(-rr, rr + 1)
                         if (di * self.step) ** 2 + (dj * self.step) ** 2 <= r * r]
        self.foot_sample = sample
        # A VIA IS NOT A TRACE. It is copper on every layer, so it has to be
        # marked on all of them, and it needs more room: via to via is
        # dia + clr = 0.39 mm centre to centre, against 0.19 for two traces.
        # Leaving vias out of the congestion model gave 33 via-on-via and 238
        # wire-on-via violations -- the router had no idea they were there.
        vr = via_d + clr
        vrr = int(vr / self.step) + 1
        self.via_off = [dj * self.W + di
                        for di in range(-vrr, vrr + 1)
                        for dj in range(-vrr, vrr + 1)
                        if (di * self.step) ** 2 + (dj * self.step) ** 2 <= vr * vr]

    def footprint(self, nodes):
        NN, W, H = self.NN, self.W, self.H
        out = set()
        for k in range(0, len(nodes), self.foot_sample):
            n = nodes[k]
            li, c = divmod(n, NN)
            i = c % W
            base = li * NN
            for off in self.foot_off:
                q = c + off
                if 0 <= q < NN and abs((q % W) - i) <= 40:
                    out.add(base + q)
        for n in nodes:                       # never miss the centreline itself
            out.add(n)
        nl = len(self.layers)
        for k in range(len(nodes) - 1):
            a, c2 = nodes[k], nodes[k + 1]
            if a % NN != c2 % NN or a // NN == c2 // NN:
                continue
            cc = a % NN                       # a layer change: there is a via here
            i = cc % W
            for li in range(nl):
                base = li * NN
                for off in self.via_off:
                    q = cc + off
                    if 0 <= q < NN and abs((q % W) - i) <= 12:
                        out.add(base + q)
        return out

    def add(self, nodes, k=1):
        for n in nodes:
            self.occ[n] += k

    def shared(self, routes):
        """centreline nodes that lie inside somebody else's clearance envelope.

        NOT footprint-against-footprint, which is what this did first and why it
        would not converge: envelopes of radius `w + clr` touch whenever two
        centrelines are within TWICE that, so two nets a comfortable 0.4 mm apart
        were being reported as sharing and the history cost kept punishing cells
        that were perfectly legal. Sharing plateaued near 15,000 cells with pfac
        over 1000, which is the shape of a test that cannot be satisfied rather
        than a routing that will not settle.

        The real rule is symmetric and one-sided at the same time: A is too close
        to B exactly when a node of A's CENTRELINE lies in B's envelope. occ[] is
        envelope coverage and includes the net's own, so a centreline node with
        occ >= 2 is covered by somebody else. That is the test.
        """
        occ = self.occ
        return set(n for nodes in routes.values() for n in nodes if occ[n] >= 2)

    def bump_history(self, over):
        for n in over:
            self.hist[n] += 1


def to_segments(rt, nodes, layers):
    """a node path back into (layer, polyline) runs, and the vias between them"""
    NN = rt.NN
    runs, vias, run, lay = [], [], [], None
    for n in nodes:
        li, c = divmod(n, NN)
        if lay is None:
            lay, run = li, [c]
        elif li == lay:
            run.append(c)
        else:
            vias.append(rt.xy(c))
            runs.append((lay, run))
            lay, run = li, [c]
    runs.append((lay, run))
    out = []
    for li, run in runs:
        pts = [rt.xy(c) for c in run]
        keep = [pts[0]]
        for k in range(1, len(pts) - 1):
            a, m, c2 = pts[k - 1], pts[k], pts[k + 1]
            if (a[0] == m[0] == c2[0]) or (a[1] == m[1] == c2[1]):
                continue
            keep.append(m)
        if len(pts) > 1:
            keep.append(pts[-1])
        out.append((layers[li], keep))
    return out, vias


# ---------------------------------------------------------------- driver
def cells_of(obst, mz, clr, w, margin=0.02):
    """the grid cells a set of obstacle circles blocks, for opening/closing"""
    out = []
    for ox, oy, r in obst:
        rad = r + clr + w / 2.0 + margin
        rr = int(rad / mz.step) + 2
        ci, cj = mz.i(ox), mz.j(oy)
        for i in range(max(0, ci - rr), min(mz.W, ci + rr + 1)):
            cx = mz.bx[0] + i * mz.step
            for j in range(max(0, cj - rr), min(mz.H, cj + rr + 1)):
                if (cx - ox) ** 2 + (mz.bx[1] + j * mz.step - oy) ** 2 <= rad * rad:
                    out.append(j * mz.W + i)
    return out


def route_group(b, nets, terms, own, bx, clr, w, layers=("3", "16"),
                maxit=None, box_mm=None, log=print, thru=False, slay=None):
    """PathFinder over `nets`.

    terms[net] = (src_point, dst_point) -- src is a through hole and so exists on
                 both layers; dst is a pad on layers[-1].
    own[net]   = the net's own fixed obstacle circles, opened while it routes.

    Returns {net: (vias, [(a, c, layer)])} for the nets that came out legal, and
    the list that did not.
    """
    import power as P
    import geom as G
    # 26 iterations: the residue falls to single figures around 18-20 and the
    # best state is usually found by 22. Fewer stops short (16 -> 33 nets);
    # many more is not better, because pfac is capped and the search then just
    # wanders (40 iterations at a gentler growth gave 28).
    maxit = maxit or int(os.environ.get("MAXIT", "26"))
    box_mm = box_mm if box_mm is not None else float(os.environ.get("BOX", "6.0"))

    log("   building grids: every net's copper is an obstacle, opened per net")
    mz = dict((L, P.Maze(G.obstacles(b, frozenset(), int(L)), bx, clr, w, 0.05))
              for L in layers)
    vmz = P.Maze(G.obstacles(b, frozenset(), None), bx, clr, P.VIA_L, 0.05)
    rt = Router(mz, vmz.free, layers)
    rt.set_footprint(w, clr)
    li_last = len(layers) - 1

    # OPEN ONLY WHAT THIS NET ITSELF BLOCKS. open_cells sets a cell free, and a
    # cell near a net's own pad is very often blocked by something else as well
    # -- a neighbouring pad, or one of the power rails passing by. Opening it
    # regardless punched real holes in the grid: 18 of 113 bus vias landed on
    # cells the via grid had marked blocked, several of them straight on top of
    # VCC1V0 and VCC1V8. So intersect with a grid built WITHOUT this net: a cell
    # is safe to open only if nothing but this net was blocking it.
    log("   working out what each net may open (%d nets, one grid each)" % len(nets))
    owncells = {}
    for net in nets:
        rows = []
        for L in layers:
            solo = P.Maze(G.obstacles(b, net, int(L)), bx, clr, w, 0.05)
            rows.append([c for c in cells_of(own[net], mz[L], clr, w) if solo.free[c]])
        solo = P.Maze(G.obstacles(b, net, None), bx, clr, P.VIA_L, 0.05)
        rows.append([c for c in cells_of(own[net], vmz, clr, P.VIA_L) if solo.free[c]])
        owncells[net] = rows

    def openings(net, on):
        for li in range(len(layers)):
            rt.open_cells(li, owncells[net][li], on)
        for c in owncells[net][-1]:
            rt.vfree[c] = 1 if on else 0

    def box_for(net, slack):
        (sx, sy), (dx, dy) = terms[net]
        m = mz[layers[0]]
        i0 = max(0, m.i(min(sx, dx) - slack)); i1 = min(m.W - 1, m.i(max(sx, dx) + slack))
        j0 = max(0, m.j(min(sy, dy) - slack)); j1 = min(m.H - 1, m.j(max(sy, dy) + slack))
        return (i0, j0, i1, j1)

    routes, foot, pfac = {}, {}, PFAC0
    # KEEP THE BEST ITERATION, not the last. The residue does not fall
    # monotonically -- it dips, wanders and can end above where it passed
    # through -- so the run is only as good as the best state it ever reached.
    best = (10 ** 9, None, None)
    order = list(nets)
    for it in range(maxit):
        for net in order:
            if net in routes:
                rt.add(foot[net], -1)
                del routes[net]
                del foot[net]
            (sp, dp) = terms[net]
            sc, dc = rt.cell(sp), rt.cell(dp)
            openings(net, True)
            # THE BOX HAS TO GROW WITH THE ITERATIONS. It is a speed trick --
            # search near the two terminals rather than the whole board -- but a
            # fixed box silently caps how far a net may detour, and detouring is
            # the entire mechanism here. The residue sat at ~460 contested nodes
            # with pfac over 1000, where sharing costs a hundred times a detour;
            # they were not choosing to share, they could not see the way round.
            # Expanding only on outright FAILURE never fires, because a congested
            # route is still a route.
            grow = box_mm + 4.0 * it
            nodes = None
            for slack in (grow, grow * 3, 1e9):
                # `thru`: a plated-hole far end exists on every layer, so the
                # search may finish on any of them, not one nominated layer
                dst = ([(li, dc) for li in range(len(layers))] if thru
                       else [(li_last, dc)])
                    # and the search may only START where the escape actually left
                # copper: every layer if it ended on a via, one layer if not
                ok = slay.get(net) if slay else None
                src = [(li, sc) for li in range(len(layers))
                       if ok is None or layers[li] in ok]
                nodes = rt.route(src, dst, pfac, box_for(net, slack))
                if nodes:
                    break
            openings(net, False)
            if nodes:
                fp = rt.footprint(nodes)
                routes[net] = nodes
                foot[net] = fp
                rt.add(fp, 1)
        over = rt.shared(routes)
        log("   iter %2d  pfac %5.2f  routed %2d/%d  shared cells %d"
            % (it + 1, pfac, len(routes), len(nets), len(over)))
        if not over and len(routes) == len(nets):
            log("   LEGAL: every net routed, no cell shared")
            break
        if len(over) < best[0]:
            best = (len(over), dict(routes), dict(foot))
        rt.bump_history(over)
        pfac = min(pfac * PGROW, PCAP)

    if over:
        # WHERE the residue is, not just how much. A node that stays contested
        # while pfac is in the hundreds has no alternative, and the usual reason
        # is that it is a TERMINAL -- a net has no choice about starting on its
        # own ring via or ending on its own pad.
        NN = rt.NN
        term_cells = set()
        for n2, (sp, dp) in terms.items():
            term_cells.add(rt.cell(sp))
            term_cells.add(rt.cell(dp))
        at_term = sum(1 for n in over if (n % NN) in term_cells)
        near = 0
        for n in over:
            c = n % NN
            i, j = c % rt.W, c // rt.W
            if any((i - (tc % rt.W)) ** 2 + (j - (tc // rt.W)) ** 2 <= 64
                   for tc in term_cells):
                near += 1
        log("   residue: %d contested nodes, %d exactly on a terminal, %d within"
            " 0.4 mm of one" % (len(over), at_term, near))
        xs = [rt.xy(n % NN) for n in list(over)[:400]]
        if xs:
            log("      sample: %s" % ", ".join("(%.1f,%.1f)" % q for q in xs[:8]))

    # If it did not converge, keep a legal subset rather than overlapping copper:
    # take nets in order and drop any whose cells a kept net already uses.
    if best[1] is not None and len(over) > best[0]:
        log("   keeping iteration with %d shared cells over the last with %d"
            % (best[0], len(over)))
        routes, foot = best[1], best[2]

    # FINAL LEGALISATION. The iterations get the residue down to a handful of
    # contested cells -- six, on this bus -- but "drop any net that touches one"
    # is a brutal way to cash that in: it cost five nets for six cells. Instead,
    # accept nets one at a time, and when one conflicts, RE-ROUTE it with every
    # already-accepted net turned into a hard obstacle. That is a greedy pass,
    # which on its own is worth 21 of 39 -- but seeded with a nearly-legal
    # PathFinder solution it only has to find its way around six cells.
    # TWO DISTINCT PASSES, and the order matters more than it looks. Doing this
    # in one loop -- re-route a net the moment it conflicts -- finished at 27 of
    # 39 against 34 for simply dropping them: the re-routed net takes a worse
    # path, joins the accepted set, and blocks nets further down the list that
    # were perfectly fine. So: take everything PathFinder placed cleanly FIRST,
    # and only then go back for the leftovers.
    NN = rt.NN
    used_foot, used_line, keep = set(), set(), {}
    for net in order:
        nodes = routes.get(net)
        fp = foot.get(net, set())
        if nodes and not used_foot.intersection(nodes) and not fp.intersection(used_line):
            used_foot |= fp
            used_line |= set(nodes)
            keep[net] = nodes
    retried = requeued = 0
    for net in [n for n in order if n not in keep]:
        # block what is already accepted, hard, and try again
        blocked = []
        for n in used_foot:
            li, c = divmod(n, NN)
            if rt.free[li][c]:
                rt.free[li][c] = 0
                blocked.append((li, c))
        (sp, dp) = terms[net]
        openings(net, True)
        dc2 = rt.cell(dp)
        ok2 = slay.get(net) if slay else None
        again = rt.route([(li, rt.cell(sp)) for li in range(len(layers))
                          if ok2 is None or layers[li] in ok2],
                         ([(li, dc2) for li in range(len(layers))] if thru
                          else [(li_last, dc2)]), 0.0,
                         (0, 0, rt.W - 1, rt.H - 1))
        openings(net, False)
        for li, c in blocked:
            rt.free[li][c] = 1
        retried += 1
        if not again:
            continue
        fp2 = rt.footprint(again)
        if fp2.intersection(used_line) or used_foot.intersection(again):
            continue
        used_foot |= fp2
        used_line |= set(again)
        keep[net] = again
        requeued += 1
    if retried:
        log("   final legalisation: %d net(s) re-routed against the accepted set,"
            " %d recovered" % (retried, requeued))
    out = {}
    for net, nodes in keep.items():
        runs, vias = to_segments(rt, nodes, layers)
        if not runs:
            continue
        # SNAP BOTH ENDS TO THE REAL TERMINALS. Every point in a path is a grid
        # cell centre, and the grid is 0.05 mm, so a route left as-is stops just
        # short of its own ring via and its own pad -- connected to nothing.
        # check_board said so plainly: "50 wire ends connect to nothing", and
        # the 369 clearance violations that came with it were the loose ends
        # sitting a few hundredths off neighbouring pads.
        sp, dp = terms[net]
        runs[0][1][0] = sp
        runs[-1][1][-1] = dp
        segs = []
        for lay, pts in runs:
            segs += [(a, c, lay) for a, c in zip(pts, pts[1:])]
        out[net] = (vias, segs)
    return out, [n for n in order if n not in keep]
