# -*- coding: utf-8 -*-
"""Route VCC1V0 and VCC1V8 as wide traces on L3.

    python tools/power.py            report only, writes nothing
    python tools/power.py --apply    write the traces and their vias

RUN IT AFTER BOTH ESCAPES AND BEFORE ground.py:

    make_board.py --fab jlcpcb        regenerates <signals> EMPTY
        -> escape.py --apply          the BGA fan-out, U1
        -> escape_qfn.py --apply      the QFN fan-out, U2
        -> QFN_PART=U8 QFN_POWER=VU escape_qfn.py --apply       and U8
        -> signals.py pairs --apply   the differential pairs, BEFORE power
        -> power.py --apply           the eight rails
        -> signals.py sdram --apply
        -> ROUTER=greedy signals.py rest --apply     second, see below
        -> signals.py GRP --apply     x2, usb, microsd, jtag
        -> ground.py --apply          the pour and the stitching, LAST

PAIRS BEFORE POWER, which is one stage further up than it looks like it needs
to be. A pair wants one corridor of 2*PAIR_W + PAIR_GAP running its whole
length and can only take it on a layer where such a corridor exists; a rail
like FT-VPLL is a three-pad local tree beside U2 with a plane's worth of
freedom. Run power first and it lays FT-VPLL straight across U2's south side,
which is where the USB pair's fan-in legs have to be -- the pair then has
exactly one route left, through that copper, and correctly refuses it. Run the
pair first and it takes L16 at 21.6/21.6 mm, skew 0.921 against a 1.27 budget,
and power routes around it without complaint. When two things want the same
copper the one with alternatives yields.

ground.py used to come before this and it cost VCC1V0 its route -- see the
header of ground.py for the measurement.

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

# U2'S THREE RAILS BELONG HERE AND HAD NO ROUTER AT ALL. FT-VCORE, FT-VPHY and
# FT-VPLL are the FT2232H's internal LDO outputs -- VCORE on four pins with two
# decouplers, and VPHY and VPLL each through a ferrite (L4, L5) to one more.
# They match signals.py's usb group on its "^FT-" regex, so that is where they
# were being sent, and a point-to-point signal router is the wrong shape for a
# six-pad power tree. escape_qfn.py declines them too, on the grounds that power
# nets are left to ground.py and power.py -- correct, except that power.py's
# RAILS did not name them, so nothing owned them and all three routed as
# airwires every time. They are trees of terminals like the other two, just
# smaller and local to U2, so they route the same way.
# VU, VEXT and USB5V0 join them for the same reason: they are supply nets that
# no group regex matched and no rail list named, so nothing routed them either.
# VU is the 5 V bus with 13 pads on it.
RAILS = ("VCC1V0", "VCC1V8", "FT-VCORE", "FT-VPHY", "FT-VPLL",
         "VU", "VEXT", "USB5V0")
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


def _rect(q):
    """a surface() entry as rect_seg wants it: (x, y, hx, hy, corner radius)"""
    return q if len(q) == 5 else (q[0], q[1], q[2], q[3], 0.0)


def surface(b, net, side):
    """foreign copper on ONE side, for checking a pad-to-via stub.

    The stub is the one piece of this route that is not on L3, and it was the
    one piece never checked. It runs on the pad's own surface layer, straight
    into its neighbours if nothing stops it -- which is how a VCC1V0 stub ended
    up 0.05 mm from a GND pad where it needed 0.09.

    THE PADS ARE RECTANGLES. This returned hypot(hx, hy), the CIRCUMSCRIBED
    circle, which is the safe direction to be wrong in and is wrong by the whole
    corner-to-edge difference on anything long and thin. A USB receptacle pin is
    0.40 x 1.36 and becomes a disc of radius 0.709: X1.1 could not be given a
    via anywhere within 5.5 mm, not because the board is full -- a via sits
    legally 0.90 mm away -- but because every stub reaching one was measured
    against a circle that swallows 0.3 mm of empty board on each side of its
    neighbour. signals.py fixed this same error against pad rectangles; this
    copy of it survived.
    """
    pads, segs = [], []
    for onet, x, y, hx, hy, sd in E.board_copper(b, skip=()):
        if onet != net and sd in (0, side):
            pads.append((x, y, hx, hy))
    # AND THE VIAS. This collected foreign PADS and foreign WIRES and stopped
    # there, which was survivable while the only vias near a stub were ones this
    # function had just placed itself. It stopped being survivable the moment a
    # second package was fanned out: escape_qfn on U8 puts 15 vias around the
    # regulator, and VCC1V0's stub came out 0.0123 mm from FB3_NODE's -- a short
    # in everything but name, and invisible here because a via is not a pad and
    # not a wire. A via is copper on EVERY layer, so it belongs in every side's
    # obstacle set. Modelled as a rectangle of zero extent with a corner radius,
    # which is what rect_seg wants for a circle.
    for vx, vy, vd in re.findall(r'<via x="([-\d.]+)" y="([-\d.]+)"'
                                r'[^>]*diameter="([\d.]+)"', b):
        pads.append((float(vx), float(vy), 0.0, 0.0, float(vd) / 2.0))
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


def via_for(px, py, obst, mine, clr, bx, segs=(), surf=None, stub_w=STUB_W,
            escapes=()):
    """a spot for this pad's via: nearest clear point on a ring around it"""
    # THE LADDER ONLY MATTERS TO A PAD THAT WOULD OTHERWISE GET NOTHING, because
    # this returns the NEAREST clear spot and walks outward: a pad with room at
    # 0.70 takes 0.70 whatever the ladder ends at. It used to stop at 1.50 and
    # one pad in thirty fell off the end -- C89, whose neighbour C106 is 0.53 mm
    # away ON THE OTHER SIDE OF THE BOARD. Two 0201 fields tiled per side at
    # 0.35 mm gap interleave to about 0.5 mm in plan, which is fine for two
    # parts and not fine for the through hole one of them needs. Reaching 2.50
    # buys that pad a via at the cost of a longer surface stub, and the report
    # below names any stub long enough to be worth looking at.
    for rad in [OFFSET + 0.25 * k for k in range(8)]:
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
            # BOTH RULES, and the drill one binds. See escape.via_sep: two
            # 0.30 lands at 0.09 want 0.39, two 0.2 mm HOLES at mdDrill want
            # 0.40, and a hole is a hole whoever owns it -- this test is against
            # the net's OWN vias, where the copper rule does not apply at all
            # and the drill rule still does.
            if any(math.hypot(x - ox, y - oy) < E.via_sep(clr) - 1e-9 for ox, oy, r in mine):
                continue
            # AND A TRACE HAS TO BE ABLE TO LEAVE IT. via_for and the router were
            # measuring against DIFFERENT obstacle sets -- via_obstacles() here,
            # geom.obstacles() there -- and via_for's is the looser of the two, so
            # it could and did place a via that the maze then could not reach.
            # USB5V0's via beside X1 came out with zero violations by this
            # function's reckoning and its cell BLOCKED on every layer by the
            # router's: the flood from it reached 0 cells of 619760. The net was
            # reported as an unroutable 35 mm edge when the truth was a via
            # sited 0.116 mm from a shell pad in a model that could not see it.
            # A via nothing can leave is not a via, so require the spot to admit
            # a trace on at least one layer the edge is allowed to use.
            if escapes and not any(
                    all(math.hypot(x - ox, y - oy) >= r + clr + W / 2 - 1e-9
                        for ox, oy, r in one) for one in escapes):
                continue
            if surf is not None:               # the stub, on the pad's own layer
                sp, ss = surf
                stub = ((px, py), (x, y))
                if not all(G.rect_seg(_rect(q), stub[0], stub[1])
                           >= clr + stub_w / 2 - 1e-9 for q in sp):
                    continue
                if not all(E.seg_seg(stub[0], stub[1], a, c) >= r + clr + stub_w / 2 - 1e-9
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
    # L4 IS IN HERE NOW. It stopped being a ground plane on 2026-08-27 and
    # became a signal layer; nothing told power.py. With 16,1,3 the VU tree
    # would not close -- one 3.86 mm hop across the regulator corner had no path
    # on any of them -- and VEXT could not make either of its two edges. Adding
    # L4 closes both, VU 12 of 12 and VEXT 2 of 2. It stays LAST but one, ahead
    # only of L3: L3 is the SDRAM bus's layer and the one worth hoarding.
    PREF = [q for q in os.environ.get("PWR_PREF", "16,1,4,3").split(",") if q]

    allvias = {}
    for net in RAILS:
        vobst, vsegs = via_obstacles(b, net)
        pads = pads_of(b, net)
        obst0, mine0 = blockers(b, net)
        surf = {sd: surface(b, net, 1 if sd == 1 else 16) for sd in (1, 16)}
        vias, stubs, miss, narrow = [], [], [], []
        esc = [G.obstacles(b, net, int(L)) for L in PREF]
        # THE STUB MUST ALSO MISS THE VIAS THIS RUN IS STILL PLACING. surface()
        # reads the board FILE, so it sees every via that was already on it and
        # none of the ones power.py is putting down right now for the other
        # rails. The via-to-via check has had `placed` for exactly this reason
        # since "EVERY VIA FIRST" was written; the stub check never got it, and
        # VCC1V0's stub came out 0.223 mm THROUGH VCC1V8's new via -- a short
        # between the two main rails on a board that reported both as routed.
        placed = [(x, y, VIA_L / 2) for r in allvias.values() for x, y in r[0]]
        # AND THE MIRROR OF IT, which is the half that actually bit. `placed`
        # only ever looks BACKWARDS: VCC1V0 is the first rail in RAILS, so when
        # its stubs were checked VCC1V8's vias did not exist yet, and when
        # VCC1V8's via was sited it was checked against VCC1V0's VIAS but not
        # against VCC1V0's STUBS. Neither side of that pair ever met the other,
        # and VCC1V0's stub ended 0.223 mm inside VCC1V8's via -- a short
        # between the two main rails, reported by both as routed. So a new via
        # must clear the stubs this run has already laid, whatever rail laid
        # them and whatever side they are on: a via is copper on every layer.
        pstub = [(q, v2, w2 / 2.0) for n2, r in allvias.items() if n2 != net
                 for q, v2, _sd2, w2 in r[1]]
        sfx = dict((k, (surf[k][0] + [(qx, qy, 0.0, 0.0, VIA_L / 2)
                                      for qx, qy, _qr in placed],
                        surf[k][1] + [(q, v2, w2 / 2.0)
                                      for n2, r in allvias.items() if n2 != net
                                      for q, v2, sd2, w2 in r[1] if int(sd2) == k]))
                   for k in surf)
        # A PAD THAT IS ALREADY WIRED TO THIS NET NEEDS NOTHING. The test was
        # "is one of this net's vias AT this pad", which is the only way a pad
        # got connected before anything fanned out a package. escape_qfn.py
        # connects one differently: a stub from the pad to a via 1.00 or 1.60 mm
        # away, which leaves the pad wired to the net and 1.60 mm from the
        # nearest via. power.py went on demanding a via of its own beside it and
        # reported five of U8's six VU pins as unreachable while looking
        # straight at the copper that already reached them. Ask whether any of
        # this net's wires ENDS on the pad instead.
        wend = set()
        _m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net), b, re.S)
        if _m:
            for _x1, _y1, _x2, _y2 in re.findall(
                    r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"',
                    _m.group(1)):
                wend.add((round(float(_x1), 3), round(float(_y1), 3)))
                wend.add((round(float(_x2), 3), round(float(_y2), 3)))
        for px, py, side in pads:
            if min((math.hypot(px - vx, py - vy) for vx, vy, r in mine0), default=9e9) < 0.01:
                continue
            if (round(px, 3), round(py, 3)) in wend:
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
            # A NARROW STUB WHERE A WIDE ONE WILL NOT GO. The check measures
            # the stub from the pad's CENTRE, so the first fraction of a
            # millimetre of it is inside the pad's own copper and is being held
            # to the trace's clearance rather than the pad's. C89 is 0.189 mm
            # from a Pmod through hole's square corner: legal for the pad,
            # which owes it 0.090, and 0.051 mm short of what a 0.30 mm trace
            # from the centre owes it. Nothing is wrong with the placement and
            # nothing is wrong with the rule -- the stub is simply wider than
            # it needs to be. It feeds a bypass capacitor, not the rail: 0.15 mm
            # on outer copper carries about 0.5 A, which is far more than a
            # 0.47 uF ever passes, and it is twice msWidth.
            v, sw = None, STUB_W
            for sw in (STUB_W, 0.15):
                v = via_for(px, py, vobst + placed + [(a, c, VIA_L / 2) for a, c in vias],
                            mine0, clr, bx, vsegs + pstub, sfx[sd], stub_w=sw,
                            escapes=esc)
                if v is not None:
                    break
            if v is None:
                miss.append((px, py, sd)); continue
            vias.append(v)
            stubs.append(((px, py), v, str(sd), sw))
            if sw != STUB_W:
                narrow.append((px, py, sw))
        # A BOXED-IN PAD CAN STILL REACH WHATEVER IS ALREADY ON THE NET. C89 is
        # a 0201 on the back with C106 0.53 mm away ON THE FRONT: two decoupling
        # fields tiled per side interleave in plan, legally, and then the through
        # hole one of them needs has nowhere to land. C90 is 0.60 mm along the
        # same strip, same side, same rail, and already has a via. Chaining an
        # adjacent pair onto one via is ordinary practice.
        #
        # IT HAS TO WALK, AND IT HAS TO CHAIN TO PADS AND NOT ONLY TO VIAS. This
        # looked once at each stranded pad, only ever at this net's VIAS, and
        # gave up past 2.00 mm -- which cannot express the case it is most needed
        # for. U8 is a QFN-20 on 0.5 mm pitch and VU arrives on SIX of its pins;
        # power.py wants a via beside each and the package has room for two. The
        # other four are not isolated, they are a chain: 11.75,5.54 -> 13.90,6.19
        # is 2.25 mm, -> 13.90,7.69 is 1.50, -> 12.25,9.34 is 2.33, and THAT one
        # has a via. Every link is short; only the walk was missing. So iterate,
        # and treat a pad that has just been chained as an anchor for the next --
        # it is on the net now, the stub put it there.
        #
        # This is what a hand layout does with a multi-pin power input: tie the
        # pins along the package edge and take one via out of the group. The
        # pins are in parallel anyway. 2.50 mm of 0.30 mm trace on outer copper
        # carries about 1 A against VU's 500 mA, and there are six of them.
        DAISY = 2.50
        keep, daisy = list(miss), []
        anchors = list(vias)
        moved = True
        while moved and keep:
            moved, still = False, []
            for px, py, sd in keep:
                sp, ss = sfx[sd]
                hit = None
                for d, v in sorted((math.hypot(px - ax, py - ay), (ax, ay))
                                   for ax, ay in anchors):
                    if d > DAISY:
                        break
                    if not all(G.rect_seg(_rect(q), (px, py), v)
                               >= clr + STUB_W / 2 - 1e-9 for q in sp):
                        continue
                    if not all(E.seg_seg((px, py), v, q1, q2) >= r + clr + STUB_W / 2 - 1e-9
                               for q1, q2, r in ss):
                        continue
                    hit = (d, v)
                    break
                if hit:
                    stubs.append(((px, py), hit[1], str(sd), STUB_W))
                    daisy.append((px, py, hit[0], sd))
                    anchors.append((px, py))
                    moved = True
                else:
                    still.append((px, py, sd))
            keep = still
        miss = keep
        allvias[net] = (vias, stubs, miss, daisy, narrow)

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
        vias, stubs, miss, daisy, narrow = allvias[net]
        onlayer = [(x, y) for x, y, sd in pads if sd == 0 or str(sd) == LAYER]
        term = [(x, y) for x, y, r in mine] + vias + onlayer
        print("   %d terminals on L%s (%d new vias, %d already there), "
              "%d piece(s) to join"
              % (len(term), LAYER, len(vias), len(mine), len(G.components(b, net, term))))
        if narrow:
            print("   %d stub(s) narrowed to clear a neighbour the pad itself clears: %s"
                  % (len(narrow), ", ".join("(%.1f, %.1f) at %.2f mm"
                                            % (x, y, w) for x, y, w in narrow)))
        for px, py, d, sd in daisy:
            print("   daisy chain: pad (%.1f, %.1f) had no room for a via and joins"
                  " one %.2f mm away on L%d" % (px, py, d, sd))
        # A PAD THAT CANNOT TAKE A VIA IS STILL A TERMINAL -- ON ITS OWN LAYER.
        # X1.1 is USB VBUS on the receptacle and there is NO legal via within
        # 5.5 mm of it: the shell's plated hole has a 0.72 mm half-extent and
        # sits 1.20 mm away, so its edge is 0.18 mm from the pad centre, and D-
        # is 0.65 mm off. The pad does not need a via. Its partner D1.A already
        # has one, a via is copper on every layer, and L1 is in PREF -- so an L1
        # trace from this pad to that via joins them and no new hole is needed
        # anywhere. What lost it was the terminal model: every off-layer pad had
        # to own a via, and one that could not was dropped, taking the whole net
        # down with it. Take it as a terminal instead and remember that an edge
        # reaching it must run on the pad's own layer.
        tlay, kept = {}, []
        for _x, _y, _sd in miss:
            if str(_sd) in PREF:
                tlay[len(term)] = str(_sd)
                term.append((_x, _y))
            else:
                kept.append((_x, _y, _sd))
        if tlay:
            print("   %d pad(s) with no room for a via, taken as terminals on "
                  "their own layer: %s"
                  % (len(tlay), ", ".join("(%.1f, %.1f) on L%s" % (term[k][0], term[k][1], v)
                                          for k, v in sorted(tlay.items()))))
        miss = kept
        if miss:
            print("   **** %d pad(s) could not be given a via: %s"
                  % (len(miss), [(round(a, 1), round(c, 1)) for a, c, _ in miss[:4]]))
        far = sorted(((math.hypot(q[0] - v[0], q[1] - v[1]), q) for q, v, _s, _w in stubs),
                     reverse=True)
        far = [(d, q) for d, q in far if d > 1.5]
        if far:
            print("   ---- %d boxed-in pad(s) reached by a long surface stub: %s"
                  % (len(far), ", ".join("%.2f mm at (%.1f, %.1f)" % (d, q[0], q[1])
                                         for d, q in far)))
            print("        a stub is series inductance in front of the capacitor it")
            print("        serves -- roughly 1 nH per mm -- so these decouple less")
            print("        than the ones that got a via at 0.70 mm.")
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
                # a surface terminal is only reachable on its own layer
                if tlay.get(i, L) != L or tlay.get(j, L) != L:
                    continue
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
        for a, c, lay, sw in stubs:
            add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                       % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(sw), lay))
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
