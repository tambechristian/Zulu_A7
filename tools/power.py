# -*- coding: utf-8 -*-
"""Route VCC1V0 and VCC1V8 as wide traces on L3.

    python tools/power.py            report only, writes nothing
    python tools/power.py --apply    write the traces and their vias

RUN IT AFTER ground.py. The order for the whole board is:

    make_board.py --fab jlcpcb  ->  escape.py --apply  ->  ground.py --apply
                                ->  power.py --apply

WHY THESE TWO ARE TRACES AND NOT A PLANE. L5 was carried as a three-way split
between VCC3V3, VCC1V0 and VCC1V8 until it was measured: both low rails run the
full length of the board, from U8 and its inductors at one end to the FPGA and
its decoupling at the other, and they interleave the whole way. The most
favourable partition that exists leaves VCC1V0 in ten disconnected pieces. Ten
pieces is not a plane. L5 is solid VCC3V3 now and these two are traces --
board/STACKUP.md has the measurement.

WHY L3. It is the only completely empty layer, and it has L2 and L4 -- both
solid ground -- directly above and below it. A power trace there is shielded on
both faces, and it disturbs neither the GND pours on L1 and L16 nor the VCC3V3
plane on L5. The cost is a via per pad, which is the price of any inner-layer
distribution.

VIA BESIDE THE PAD, NOT IN IT. These are 0402 and 0603 decoupling capacitors.
A via in the pad wicks solder off the joint during reflow unless it is filled
and capped, which is an HDI process this board is deliberately not using. So
each pad gets a via a short distance away and a stub on its own surface layer
to reach it.
"""

import re, io, os, sys, math, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E                                          # noqa: E402
import geom as G                                            # noqa: E402

BRD = E.BRD
APPLY = "--apply" in sys.argv

RAILS = ("VCC1V0", "VCC1V8")
# WHICH LAYER THE RAILS RUN ON. It was L3, the only signal layer between two
# solid ground planes -- which is exactly why they had to leave. L3 is also
# the only clean layer the SDRAM bus can cross the board on, and these two
# rails, sprawling at 5.1x their straight-line length, cut it into pockets:
# with none of the bus laid, an escape ring via could reach 33,470 of 710,000
# grid cells. See tools/signals.py.
LAYER = os.environ.get("PWR_LAYER", "3")
W = 0.25                    # trace width on L3
STUB_W = 0.30               # the surface stub from a pad to its via
VIA_D, VIA_L = 0.2, 0.3
OFFSET = 0.70               # how far a via sits from the pad it serves
STEP = 0.05
STEP_G = 0.05               # maze grid; 0.1 rounds a terminal into a neighbour


def pads_of(b, net, skip=("U1",)):
    """(x, y, side) for every pad on this net, EXCEPT the FPGA's.

    U1's balls are the escape's business and it has already done them: they are
    ganged together on L1 and brought out through one moat via, which is the
    terminal this router connects to. Treating them as loose pads instead put a
    via 0.70 mm from each ball -- inside the package, in the moat -- and took
    the moat from 54 vias to 62, which was enough to island the ground copper
    under the 7 x 7 core on L2 and L4. check_planes caught it; the escape's own
    verifier would not have, because the vias were not its.
    """
    out = []
    for onet, x, y, hx, hy, side in E.board_copper(b, skip=skip):
        if onet == net:
            out.append((x, y, side))
    return out


def blockers(b, net):
    """what an L3 trace on `net` must clear: every foreign via on the board.

    L3 is crossed by all 265 of them. A via that is not ours punches an antipad
    and the trace has to go round; a via that IS ours is a terminal, not an
    obstacle.
    """
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    out, mine = [], []
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S):
        for x, y, dia in G.vias(m.group(2)):
            (mine if m.group(1) == net else out).append((x, y, dia / 2))
    # PLATED HOLES ARE COPPER ON EVERY LAYER, exactly as vias are, so an L3
    # trace has to clear X2's 44 header pins, JP3, J1 and X1's shell nails just
    # as it clears a via. Leaving them out put a VCC1V0 trace 0.05 from a GND
    # pin where it needed 0.09. board_copper reports them with side 0, which is
    # what "all layers" means there.
    for onet, x, y, hx, hy, side in E.board_copper(b, skip=()):
        if side == 0:
            (mine if onet == net else out).append((x, y, math.hypot(hx, hy)))
    return out, mine


def clear(a, c, obst, clr, w):
    """does segment a-c keep `clr` from every obstacle circle"""
    for ox, oy, r in obst:
        if E.seg_pt(a, c, (ox, oy)) < r + clr + w / 2 - 1e-9:
            return False
    return True


class Maze(object):
    """a grid of L3, with every foreign via dilated into it.

    An L-shaped router will not do here. The FPGA's rails arrive INSIDE the
    stage-2 moat -- VCC1V0 at chebyshev 1.85 from the ball-field centre -- and
    to reach them a trace has to cross the moat and the stage-3 ring, both of
    which are near-solid walls of vias at 0.39 mm centres. Neither has a
    straight lane through it.

    Neither is sealed, though, and that is the point. The gaps are wildly uneven
    because the isotonic fit clusters vias near their own escapes: the ring's
    median gap is 0.390 mm and its largest is 8.067. Total capacity is 97 thin
    traces through 8 usable gaps, and one of those gaps takes eleven 0.60 mm
    power traces on its own. A maze router finds them; an L-shape router cannot,
    because the path through is neither an L nor a Z.
    """

    def __init__(self, obst, bx, clr, w, step=0.1):
        self.step, self.bx = step, bx
        self.W = int((bx[2] - bx[0]) / step) + 1
        self.H = int((bx[3] - bx[1]) / step) + 1
        self.free = bytearray(b"\x01" * (self.W * self.H))
        # Measure from the via's TRUE position to each cell's TRUE centre, not
        # from one rounded cell index to another. Rounding the obstacle onto the
        # grid first loses up to half a cell on each axis -- 0.07 mm at a 0.1 mm
        # step -- and a trace laid along the resulting boundary sits that much
        # too close. check_board caught it as 204 violations, all of them a few
        # hundredths short, which is exactly the size of the rounding.
        #
        # MARGIN covers the rest: the path runs between cell centres, and the
        # nearest point of a segment to a circle can be between its endpoints
        # rather than at one. The sagitta over a 0.1 mm step is about 0.002.
        margin = 0.02
        for ox, oy, r in obst:
            rad = r + clr + w / 2 + margin
            rr = int(rad / step) + 2
            ci, cj = self.i(ox), self.j(oy)
            for i in range(max(0, ci - rr), min(self.W, ci + rr + 1)):
                cxp = bx[0] + i * step
                for jj in range(max(0, cj - rr), min(self.H, cj + rr + 1)):
                    if (cxp - ox) ** 2 + (bx[1] + jj * step - oy) ** 2 <= rad * rad:
                        self.free[jj * self.W + i] = 0
        edge = int((w / 2 + 0.30) / step) + 1        # keep off the board outline
        for i in range(self.W):
            for jj in list(range(edge)) + list(range(self.H - edge, self.H)):
                self.free[jj * self.W + i] = 0
        for jj in range(self.H):
            for i in list(range(edge)) + list(range(self.W - edge, self.W)):
                self.free[jj * self.W + i] = 0

    def bfs(self, p):
        """cell distances and predecessors from p, over free cells.

        path() stops as soon as it reaches its goal, which is all a
        single-layer route needs. Choosing WHERE to put a via needs the whole
        field: the cost of a two-layer route is the L3 distance to a candidate
        plus the L16 distance from it, and that is only comparable if both are
        known everywhere.
        """
        from array import array
        N = self.W * self.H
        dist = array("i", [-1]) * N
        prev = array("i", [-1]) * N
        s = self.j(p[1]) * self.W + self.i(p[0])
        if not (0 <= s < N) or not self.free[s]:
            return None, None
        dist[s] = 0
        dq = collections.deque([s])
        while dq:
            c = dq.popleft()
            d = dist[c] + 1
            for step in (-1, 1, -self.W, self.W):
                n = c + step
                if not (0 <= n < N) or dist[n] >= 0 or not self.free[n]:
                    continue
                if step in (-1, 1) and (n % self.W == 0 or c % self.W == 0):
                    continue
                dist[n] = d
                prev[n] = c
                dq.append(n)
        return dist, prev

    def walk(self, prev, cell, start_pt, end_pt):
        """the polyline from a bfs start out to `cell`, collinear runs collapsed.

        Both ends are snapped back to the real coordinates they stand for: the
        grid is 0.05 mm and a terminal is wherever it is, so a path that stops
        at a cell centre stops short of its own via and connects to nothing.
        """
        cells = []
        c = cell
        while c >= 0:
            cells.append(c)
            c = prev[c]
        cells.reverse()
        pts = [self.xy(q) for q in cells]
        out = [pts[0]]
        for k in range(1, len(pts) - 1):
            a, m2, c2 = pts[k - 1], pts[k], pts[k + 1]
            if (a[0] == m2[0] == c2[0]) or (a[1] == m2[1] == c2[1]):
                continue
            out.append(m2)
        out.append(pts[-1])
        out[0], out[-1] = start_pt, end_pt
        return out

    def block_box(self, x0, y0, x1, y1):
        """blank a rectangle of the grid outright.

        Not a clearance test -- a routing corridor. The maze is breadth-first
        and therefore takes the shortest path it can find, which for the SDRAM
        bus means every net hugging the same thin strip below U3 until it is
        full. Blanking that strip for some of them is how they get pushed into
        the 186 mm2 of empty L3 under U3's body, which nothing else will use:
        U3 is on L16, so on L3 its footprint is open ground.
        """
        for i in range(max(0, self.i(x0)), min(self.W, self.i(x1) + 1)):
            for j in range(max(0, self.j(y0)), min(self.H, self.j(y1) + 1)):
                self.free[j * self.W + i] = 0

    def clone(self):
        """a copy sharing nothing mutable, so obstacles can be punched into it.

        Building a Maze means dilating thousands of circles and costs about a
        second. Rip-up needs a grid per attempt, so it copies a base grid that
        has the whole net group left out and punches back the members that are
        currently placed.
        """
        m = Maze.__new__(Maze)
        m.step, m.bx, m.W, m.H = self.step, self.bx, self.W, self.H
        m.free = bytearray(self.free)
        return m

    def block(self, obst, clr, w):
        """punch more copper into a grid that already exists.

        Rebuilding a Maze costs a second or so; with three layers live at once
        and an edge at a time being committed to one of them, rebuilding per
        edge would dominate. Same dilation as __init__, same true-position
        measurement.
        """
        margin = 0.02
        for ox, oy, r in obst:
            rad = r + clr + w / 2 + margin
            rr = int(rad / self.step) + 2
            ci, cj = self.i(ox), self.j(oy)
            for i in range(max(0, ci - rr), min(self.W, ci + rr + 1)):
                cxp = self.bx[0] + i * self.step
                for jj in range(max(0, cj - rr), min(self.H, cj + rr + 1)):
                    if (cxp - ox) ** 2 + (self.bx[1] + jj * self.step - oy) ** 2 <= rad * rad:
                        self.free[jj * self.W + i] = 0

    def i(self, x): return int(round((x - self.bx[0]) / self.step))
    def j(self, y): return int(round((y - self.bx[1]) / self.step))
    def xy(self, c): return (self.bx[0] + (c % self.W) * self.step,
                             self.bx[1] + (c // self.W) * self.step)

    # There is deliberately no open_at(). An earlier version cleared a disc
    # around every terminal so a trace could reach its own via -- but the net's
    # own vias were never obstacles in the first place (blockers() separates
    # mine from foreign), so all that disc actually did was erase FOREIGN vias
    # that happened to be near a terminal. check_board found it at once: 259
    # clearance violations, traces passing 0.03 mm too close to vias whose
    # blockage had been rubbed out. If a foreign via really is that close to a
    # terminal, the honest answer is that a 0.60 mm trace cannot reach it.

    def path(self, p, q):
        """breadth-first, 4-connected, then straightened into segments"""
        s, t = self.j(p[1]) * self.W + self.i(p[0]), self.j(q[1]) * self.W + self.i(q[0])
        if not (0 <= s < self.W * self.H and 0 <= t < self.W * self.H):
            return None
        prev = {s: None}
        dq = collections.deque([s])
        while dq:
            c = dq.popleft()
            if c == t:
                break
            for d in (-1, 1, -self.W, self.W):
                n = c + d
                if n in prev or not (0 <= n < self.W * self.H) or not self.free[n]:
                    continue
                if d in (-1, 1) and (n % self.W == 0 or c % self.W == 0):
                    continue
                prev[n] = c
                dq.append(n)
        if t not in prev:
            return None
        cells = []
        c = t
        while c is not None:
            cells.append(c); c = prev[c]
        cells.reverse()
        pts = [self.xy(c) for c in cells]
        out = [pts[0]]                                # collapse collinear runs
        for k in range(1, len(pts) - 1):
            a, m2, c2 = pts[k - 1], pts[k], pts[k + 1]
            if (a[0] == m2[0] == c2[0]) or (a[1] == m2[1] == c2[1]):
                continue
            out.append(m2)
        out.append(pts[-1])
        # The grid is 0.1 mm, so a path END is a rounded position, not the
        # terminal. Put the real coordinates back or the trace stops a few
        # hundredths short of its own via and connects to nothing.
        out[0], out[-1] = p, q
        return out


def via_obstacles(b, net):
    """everything a NEW via has to miss: pads, vias and every wire on any layer.

    A via is copper on all six layers, so a wire on L1 blocks it just as a pad
    does. The first version of this checked other vias only, and dropped 37 of
    them straight through the escape's gang traces -- check_board reported 419
    clearance violations, all of them "GND wire vs VCC1V0 pad", because it files
    vias under copper-on-every-layer and was quite right to.
    """
    pads, segs = [], []
    for onet, x, y, hx, hy, side in E.board_copper(b, skip=()):
        if onet != net:
            pads.append((x, y, math.hypot(hx, hy)))
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S):
        if m.group(1) == net:
            continue
        for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                             r' y2="([-\d.]+)" width="([\d.]+)"', m.group(2)):
            x1, y1, x2, y2, wd = map(float, w.groups())
            segs.append(((x1, y1), (x2, y2), wd / 2.0))
        for x, y, dia in G.vias(m.group(2)):
            pads.append((x, y, dia / 2.0))
    return pads, segs


def surface(b, net, side):
    """foreign copper on ONE side, for checking a pad-to-via stub.

    The stub is the one piece of this route that is not on L3, and it was the
    one piece never checked. It runs on the pad's own surface layer, straight
    into its neighbours if nothing stops it -- which is how a VCC1V0 stub ended
    up 0.05 mm from a GND pad where it needed 0.09.
    """
    pads, segs = [], []
    for onet, x, y, hx, hy, sd in E.board_copper(b, skip=()):
        if onet != net and sd in (0, side):
            pads.append((x, y, math.hypot(hx, hy)))
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    lay = str(side)
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S):
        if m.group(1) == net:
            continue
        for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                             r' y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"', m.group(2)):
            if w.group(6) != lay:
                continue
            x1, y1, x2, y2, wd = map(float, w.groups()[:5])
            segs.append(((x1, y1), (x2, y2), wd / 2.0))
    return pads, segs


def via_for(px, py, obst, mine, clr, bx, segs=(), surf=None):
    """a spot for this pad's via: nearest clear point on a ring around it"""
    for rad in (OFFSET, OFFSET + 0.25, OFFSET + 0.5, OFFSET + 0.8):
        best = None
        for k in range(48):
            a = 2 * math.pi * k / 48.0
            x, y = px + rad * math.cos(a), py + rad * math.sin(a)
            if not (bx[0] + 0.5 < x < bx[2] - 0.5 and bx[1] + 0.5 < y < bx[3] - 0.5):
                continue
            if not all(math.hypot(x - ox, y - oy) >= r + clr + VIA_L / 2 - 1e-9
                       for ox, oy, r in obst):
                continue
            if not all(E.seg_pt(a, c, (x, y)) >= r + clr + VIA_L / 2 - 1e-9
                       for a, c, r in segs):
                continue
            if any(math.hypot(x - ox, y - oy) < VIA_L + clr - 1e-9 for ox, oy, r in mine):
                continue
            if surf is not None:               # the stub, on the pad's own layer
                sp, ss = surf
                stub = ((px, py), (x, y))
                if not all(E.seg_pt(stub[0], stub[1], (ox, oy)) >= r + clr + STUB_W / 2 - 1e-9
                           for ox, oy, r in sp):
                    continue
                if not all(E.seg_seg(stub[0], stub[1], a, c) >= r + clr + STUB_W / 2 - 1e-9
                           for a, c, r in ss):
                    continue
            d = math.hypot(x - px, y - py)
            if best is None or d < best[0]:
                best = (d, (round(x, 4), round(y, 4)))
        if best:
            return best[1]
    return None


def mst(pts):
    """Prim, so the tree is short and every terminal is on it"""
    if len(pts) < 2:
        return []
    inn, out, edges = [0], list(range(1, len(pts))), []
    while out:
        best = None
        for i in inn:
            for j in out:
                d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
                if best is None or d < best[0]:
                    best = (d, i, j)
        edges.append((best[1], best[2]))
        inn.append(best[2]); out.remove(best[2])
    return edges


def main():
    b = open(BRD, encoding="utf-8").read()
    clr = float(re.search(r'<param name="mdWireWire" value="([\d.]+)mm"/>', b).group(1))
    w = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                   r' width="[\d.]+" layer="20"/>', b)
    xs = [float(v) for q in w for v in (q[0], q[2])]
    ys = [float(v) for q in w for v in (q[1], q[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))
    print("routing %s on L%s at %.2f mm, clearance %.3f"
          % (" and ".join(RAILS), LAYER, W, clr))

    # EVERY VIA FIRST, THEN EVERY TRACE. Doing a whole rail at a time only lets
    # the SECOND rail see the first: VCC1V0 went down before VCC1V8's vias
    # existed and ran straight over three of them, -0.44 mm at worst. Placing
    # all the vias up front means both mazes see all of them.
    allvias = {}
    for net in RAILS:
        vobst, vsegs = via_obstacles(b, net)
        pads = pads_of(b, net)
        obst0, mine0 = blockers(b, net)
        surf = {sd: surface(b, net, 1 if sd == 1 else 16) for sd in (1, 16)}
        vias, stubs, miss = [], [], []
        placed = [(x, y, VIA_L / 2) for r in allvias.values() for x, y in r[0]]
        for px, py, side in pads:
            if min((math.hypot(px - vx, py - vy) for vx, vy, r in mine0), default=9e9) < 0.01:
                continue
            # A PAD ALREADY ON THE ROUTING LAYER NEEDS NO VIA. When the rails
            # ran on L3 that was every pad, because an inner layer has none of
            # them. Routed on a surface it is not: 16 of the two rails' 26 pads
            # are on the bottom, so moving there removes 16 vias and 16 stubs
            # rather than adding any. Side 0 is a plated hole -- copper on every
            # layer, reachable from wherever this is routing.
            if side == 0 or str(side) == LAYER:
                continue
            sd = 16 if side == 16 else 1
            v = via_for(px, py, vobst + placed + [(a, c, VIA_L / 2) for a, c in vias],
                        mine0, clr, bx, vsegs, surf[sd])
            if v is None:
                miss.append((px, py)); continue
            vias.append(v)
            stubs.append(((px, py), v, str(sd)))
        allvias[net] = (vias, stubs, miss)

    # EVERY EDGE PICKS ITS OWN LAYER, and L3 is the last one it may pick.
    #
    # No single layer carries these rails. L3 does, but L3 is the layer the
    # SDRAM bus needs. L16 leaves 2 and 10 edges open, L1 leaves 9 and 10 -- it
    # is full of the escape. Which is fine, because a power net is a tree of
    # through-holes and has no reason to stay on one layer: every terminal here
    # is a via or a plated hole, so an edge routed on L16 and the next one on L1
    # meet at a terminal that already spans both. No extra vias, no stubs.
    #
    # PREF is the order each edge tries. L3 stays in it as a last resort rather
    # than being banned outright: a rail that does not close is worse for the
    # board than one that borrows a little L3, and the report says how much.
    PREF = [q for q in os.environ.get("PWR_PREF", "16,1,3").split(",") if q]
    plan = {}
    laid = dict((L, []) for L in PREF)   # copper this run has put on each layer
    for net in RAILS:
        _o, mine = blockers(b, net)
        # THE LAYER'S REAL COPPER, not just its vias. blockers() reports vias and
        # plated holes only, which was true enough when the rails had L3 to
        # themselves and is not true anywhere else -- on a surface layer it would
        # drive straight through pads and through the ground pour's neighbours.
        foreign = [(x, y, VIA_L / 2) for n2, r in allvias.items() if n2 != net
                   for x, y in r[0]]
        obs = dict((L, G.obstacles(b, net, int(L), laid[L]) + foreign) for L in PREF)
        obst = obs[PREF[-1]]
        vobst, vsegs = via_obstacles(b, net)
        pads = pads_of(b, net)
        print("")
        print("%s -- %d pads, %d via(s) already, %d foreign vias to dodge on L3"
              % (net, len(pads), len(mine), len(obst)))
        vias, stubs, miss = allvias[net]
        onlayer = [(x, y) for x, y, sd in pads if sd == 0 or str(sd) == LAYER]
        term = [(x, y) for x, y, r in mine] + vias + onlayer
        print("   %d terminals on L%s (%d new vias, %d already there), "
              "%d piece(s) to join"
              % (len(term), LAYER, len(vias), len(mine), len(G.components(b, net, term))))
        if miss:
            print("   **** %d pad(s) could not be given a via: %s"
                  % (len(miss), [(round(a, 1), round(c, 1)) for a, c in miss[:4]]))
        mzs = dict((L, Maze(obs[L], bx, clr, W, STEP_G)) for L in PREF)
        segs, failed = [], 0
        used = collections.Counter()
        # EDGE ORDER. Longest-first was the original and it is the wrong way
        # round here: the long trunk is laid across open copper first and then
        # stands as a wall between the short local hops and the rest of the
        # tree. Shortest-first grows the tree outward from its clusters and
        # leaves the trunk to find its way around what already exists.
        _ord = os.environ.get("PWR_ORDER", "short")
        _len = lambda e: math.hypot(term[e[0]][0] - term[e[1]][0],
                                    term[e[0]][1] - term[e[1]][1])
        # SPAN THE PIECES, NOT THE TERMINALS. Most of this net is already joined
        # by the escape's gang copper; only the gaps between those pieces need a
        # wire. See geom.components.
        grp = G.components(b, net, term)
        edges = G.mst_groups(term, grp)
        edges = edges if _ord == "prim" else             sorted(edges, key=_len if _ord == "short" else (lambda e: -_len(e)))
        for i, j in edges:
            p = lay = None
            for L in PREF:
                p = mzs[L].path(term[i], term[j])
                if p is not None:
                    lay = L
                    break
            if p is None:
                failed += 1
                print("   **** no path on any of L%s: (%.2f,%.2f) -> (%.2f,%.2f), "
                      "%.2f mm apart"
                      % ("/L".join(PREF), term[i][0], term[i][1],
                         term[j][0], term[j][1], _len((i, j))))
                continue
            obst = obs[lay]
            # STRAIGHTEN. Maze.path's docstring says "straightened" but it only
            # collapses collinear runs, so every staircase turn survived and
            # VCC1V8 came out 471 mm against a 91.6 mm bound.
            p = G.straighten(p, obst, clr, W)
            new = list(zip(p, p[1:]))
            segs += [(a, c, lay) for a, c in new]
            used[lay] += sum(math.hypot(c[0] - a[0], c[1] - a[1]) for a, c in new)
            # A RAIL'S OWN COPPER IS NOT AN OBSTACLE TO ITSELF. Two traces of
            # one net may touch -- they are the same net. Punching each edge
            # into its own rail's grid as it was committed took L3-only from
            # 15 of 15 edges to 6, because the tree kept walling itself off
            # from the pieces it had yet to reach. It goes into `laid`, which
            # is what the NEXT rail sees, and nowhere else.
            add = []
            for a, c in new:
                add += G.sample(a, c, W / 2)
            laid[lay] += add
        print("   %d tree edges, %d routed, %d could not be"
              % (len(edges), len(edges) - failed, failed))
        tot = sum(math.hypot(c[0] - a[0], c[1] - a[1]) for a, c, _l in segs)
        print("   %d segments, %.1f mm of %.2f mm trace: %s"
              % (len(segs), tot, W,
                 ", ".join("L%s %.1f mm" % (L, used[L]) for L in PREF if used[L])))
        # ALL OR NOTHING PER RAIL. A rail whose tree does not close is worse on
        # the board than one that was never started: it looks routed, and the
        # part that is missing is invisible until something is measured. Both
        # orderings leave ONE of the two short by two edges -- VCC1V0 first
        # strands the FPGA's VCCAUX, VCC1V8 first strands VCC1V0's regulator end
        # -- and routing the longest edges first does not change it. Closing
        # both needs rip-up-and-retry, which this router does not do.
        if failed or miss:
            print("   ---- NOT WRITTEN: the tree does not close, so nothing goes down")
            plan[net] = ([], [], [], failed, miss)
        else:
            plan[net] = (vias, stubs, segs, failed, miss)
        # a via is copper on every layer, so it blocks all of them
        for L in PREF:
            laid[L] += [(x, y, VIA_L / 2) for x, y in vias]

    print("")
    print("CURRENT CAPACITY. %.2f mm on 0.035 mm inner copper carries about 1.1 A at a"
          % W)
    print("   10 C rise by IPC-2152. VCCINT on an XC7A35T-1 is the larger draw and sits")
    print("   well inside that at this device size; VCCAUX is a fraction of it.")
    print("   The narrow point is NOT the trace -- it is that the FPGA's whole rail")
    print("   leaves the package through ONE escape via, which is noted below.")

    if not APPLY:
        print("")
        print("report only -- re-run with --apply to write it into the board")
        return 0
    for net in RAILS:
        m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net), b, re.S)
        if m and re.search(r'<wire [^>]*width="%s"' % E.g(W), m.group(1)):
            print("")
            print("REFUSING TO APPLY: %s already carries routed copper." % net)
            return 1

    g = E.g
    out = b
    nv = nw = 0
    for net in RAILS:
        vias, stubs, segs, failed, miss = plan[net]
        add = []
        for x, y in vias:
            add.append('<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
                       % (g(x), g(y), g(VIA_D), g(VIA_L)))
            nv += 1
        for a, c, lay in stubs:
            add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                       % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(STUB_W), lay))
            nw += 1
        for a, c, lay in segs:
            if math.hypot(c[0] - a[0], c[1] - a[1]) < 1e-9:
                continue
            add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                       % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(W), lay))
            nw += 1
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), out)
        out = out[:m.end()] + "".join(add) + out[m.end():]
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    open(BRD, "w", encoding="utf-8").write(out)
    print("")
    print("wrote %d wires and %d vias into %s" % (nw, nv, BRD))
    return 0


if __name__ == "__main__":
    sys.exit(main())
