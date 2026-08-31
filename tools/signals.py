# -*- coding: utf-8 -*-
"""Route point-to-point signal nets on L3, starting with the SDRAM bus.

    python tools/signals.py [group]           report only
    python tools/signals.py [group] --apply   write it into the board

RUN ORDER. Every group here runs after both escapes and after power.py, and
ground.py runs after all of them:

    make_board.py --fab jlcpcb        regenerates <signals> EMPTY
        -> escape.py --apply          the BGA fan-out, U1
        -> escape_qfn.py --apply      the QFN fan-out, U2
        -> QFN_PART=U8 QFN_POWER=VU escape_qfn.py --apply       and U8
        -> signals.py pairs --apply   the differential pairs, BEFORE power
        -> power.py --apply           the eight rails
        -> signals.py GRP --apply     sdram, x2, usb, microsd, jtag, in that
                                      order -- see the note below
        -> ROUTER=greedy signals.py rest --apply
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

GROUP ORDER MATTERS, and it is not the order you would guess. Each group's
copper is an obstacle to the next, so this was measured rather than reasoned
(nets routed, best of each run, on the same board):

    order                              usb  jtag  microsd  sdram  x2   total
    sdram, x2, usb, microsd, jtag        2     6        5     29  10      52
    sdram, jtag, usb, microsd, x2        2     7        6     29   5      49
    usb, jtag, microsd, sdram, x2        2     7        6     19  10      44

Most-constrained-first is the usual rule and it LOSES here. sdram is 39 nets
converging on U3 and wanting L3 between the planes, and starving it costs more
than every other group gains -- it drops 10 nets to buy 3. x2 is the opposite
of what it looks like: its far ends are X2's plated holes, copper on all six
layers, so it looks like the flexible one that should go last, and it does
better second (10) than last (5). Long hauls need room early.

make_board regenerates <signals> empty, so everything above is wiped on every
run. See the header of escape.py.

WHAT IS ACTUALLY BEING ROUTED. Each bus net already has exactly two pieces of
copper: the escape's fan-out on L1 ending in one through-hole via on the ring
around U1, and one pad on U3 on L16. Nothing joins them. So every net here is a
single two-point route: ring via -> L3 -> a new via beside the U3 pad -> a short
stub on L16 into the pad. Same shape as power.py's rail routing, which is why
this imports that module rather than reimplementing a maze router.

WHY L3. It is the only signal layer between two solid ground planes (L2 and L4),
which is what a memory bus wants for a tight return path. L1 and L16 are both
under a ground pour, and threading 39 traces through either would carve the pour
into islands for no benefit.

THE RING IS A WALL AND THAT IS FINE. Stage 3 leaves 103 vias at 0.390 mm centres
around the package. A 0.15 mm trace at 0.09 clearance needs 0.630 mm between via
centres, so nothing crosses that ring on L3 -- but nothing has to. Every bus net
starts ON the ring and routes outward, away from the package. The reason that
works at all is the repin: the bus used to escape on the right, away from U3,
and would have had to get round the package somehow. See tools/repin.py.
"""

import re, io, os, sys, math, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E                                          # noqa: E402
import power as P                                           # noqa: E402
import geom as G                                            # noqa: E402

BRD = E.BRD
APPLY = "--apply" in sys.argv

LAYER = "3"
# 0.10 mm, and that is a measured number rather than a preference. The strip
# below U3 is 3.65 mm of usable height and U3's bottom row wants 20 nets; at
# 0.15 mm trace plus 0.09 mm clearance that needs 4.80 mm and does not fit.
# Widths measured end to end, L3 + L16 fall-back, shortest-first:
#     0.15 -> 20 nets    0.12 -> 21    0.11 -> 32    0.10 -> 32    0.09 -> 32
# It plateaus at 0.11, so 0.10 is one step inside the knee and still comfortably
# above JLCPCB's 0.09 minimum. These carry no current -- see the note in main().
# IMPEDANCE IS NOT CONTROLLED HERE. 0.10 mm on L3 between two ground planes is
# a higher Z0 than a 0.15 mm trace would be; nobody has specified a target, and
# if one is wanted the board needs a real stackup from the fab first.
W = float(os.environ.get("W", "0.10"))
STUB_W = 0.20
# 0.05, not power.py's 0.1. A ring via sits 0.390 mm from its neighbours and
# the maze dilates them by 0.335, so the trace has 0.055 mm of room there. At a
# 0.1 mm step the nearest cell centre can be 0.071 mm off the via, which lands
# inside the dilated neighbour and makes the START cell unreachable -- 28 of 39
# nets "unroutable" with the path never leaving the via. At 0.05 the worst
# offset is 0.035 and the start is always free.
STEP = 0.05
VIA_D, VIA_L = P.VIA_D, P.VIA_L

OUTWARD = os.environ.get("OUTWARD", "1") == "1"
SPLIT = os.environ.get("SPLIT", "0") == "1"
# nets a previous pass could not place, retried first on the next one
HARD = set(q for q in os.environ.get("HARD", "").split(",") if q)
ORDER = os.environ.get("ORDER", "len")
SPLITVIA = os.environ.get("SPLITVIA", "1") == "1"
# "pathfinder" = negotiated congestion (tools/pathfinder.py); "greedy" = the
# rip-up router, kept because it is what every measurement above was taken on.
ROUTER = os.environ.get("ROUTER", "pathfinder")
# WHICH ONE TO USE, MEASURED. PathFinder needs START[net] -- an escape terminal
# on U1's ring -- and routes strictly two-terminal, so it SILENTLY DROPS every
# net that has neither: "PathFinder over 27 nets" out of a 59-net group, with
# the other 32 never attempted and reported as unrouted. The "rest" group is
# mostly local nets between discrete parts (LED cathodes, SW*_NET, N$BTN, the
# feedback dividers) and greedy is the only branch that will look at them:
# 33 of 59 against PathFinder's 7 on the same board. Run "rest" with
# ROUTER=greedy.
#
# GREEDY HAS AN ORDERING BUG, and it is why PMOD-4 is an airwire on the current
# board rather than a route. attempt() and attempt_split() both build their
# obstacle set from `rivals = [n for n in plan if n != net]`, which is whatever
# is in the plan AT THAT MOMENT. The rip-up loop then re-routes members, so a
# net can end up in the accepted plan having been checked against a set that no
# longer describes the plan: PMOD-4's L3 trace came out straight through
# PMOD-7's via at (58.954, 12.590), -0.16 mm, a short between two Pmod signals.
# check_board caught it; nothing in here did. FIXED: there is a final
# validation pass at the end of the greedy branch that re-checks the finished
# plan against itself and rips up what conflicts. The clearance test was never
# the problem -- collides() is stricter than check_board -- so the pass reuses
# it and only changes WHEN it is applied.

# A differential pair is not a member of a group, it is the most constrained
# object on the board, and it was being routed fourth. GROUPS["pairs"] is this
# sentinel rather than a regex: the members are whatever find_pairs() pairs up,
# which is where that question is already answered.
PAIRS = object()

GROUPS = {
    # FIRST, AND ON ITS OWN. The pair used to route inside whichever group
    # happened to contain it -- USB_D_P/N in "usb", which runs after sdram and
    # x2 have put 478 segments on L3 and L4. A pair needs ONE corridor wide
    # enough for both conductors and the gap (2*PAIR_W + PAIR_GAP = 0.425 mm)
    # running the whole way, and it is the one thing on the board that cannot
    # take what is left over: a single-ended net squeezes through a 0.28 mm
    # gap that a pair simply cannot enter. Route it against an empty board and
    # let everything else go round it. AIN15 and AIN16 come with it -- they were
    # stranded in "rest" and failed there for the same reason.
    "pairs": PAIRS,
    "sdram": re.compile(r"^(D\d+|A\d+|BS\d|RAS#|CAS#|WE#|CKE|LDQM|UDQM|SDRAM-)"),
    # The prototyping header. A completely different problem from the bus: the
    # far end of every one of these is a PLATED HOLE on X2, copper on all six
    # layers at a 2.54 mm pitch, so a route needs no fan-out via and can finish
    # on whichever layer it happens to be on. Vias were what the bus ran out of.
    "x2": re.compile(r"^(CHAN[-\d]|JA\d+|RST#$)"),
    # FT-VCORE/FT-VPHY/FT-VPLL are excluded: they are U2's supply rails, not
    # signals, and power.py routes them as trees. Left in, they matched here,
    # arrived with no escape terminal -- escape_qfn declines power nets -- and
    # reported "no route" on every run.
    "usb": re.compile(r"^(USB_D|UART_FT_|FT-(?!VCORE|VPHY|VPLL))"),
    # Six nets, U1 ball to the X3 card socket, four of them through a pull-up on
    # R34/R35. Multi-pad nets, so they need the general terminal model.
    "microsd": re.compile(r"^SD-"),
    # THE JTAG/CONFIG PATH, AND IT COMES IN TWO HALVES that the resistor pack R4
    # joins: FPGA-T* on U1's side, and TCK/TDI/TDO/TMS on the header side, which
    # touch JP3, R4, a series resistor and U2's ADBUS pins but NEVER U1. That
    # second half has no escape terminal at all -- the old model would have
    # dropped it silently, and the PathFinder branch still would ("if not
    # START.get(net): continue"), which is why this group is routed greedy.
    "jtag": re.compile(r"^(FPGA-T(CK|DI|DO|MS)|FPGA-DONE|FPGA-INIT#"
                       r"|TCK|TDI|TDO|TMS|PROG#|DONE)$"),
    # EVERYTHING ELSE, and it was most of what was left. The five groups above
    # are the buses somebody sat down and thought about; the board is not only
    # buses. The Pmod header's ten signals, the RGB LED and the two singles, the
    # pushbutton, the three slide switches, the regulator's feedback dividers
    # and PGOOD and MODE, the XADC analogue pair, the shared 12 MHz clock and
    # the EEPROM data line -- 32 nets, none of them matching any regex here, so
    # signals.py never attempted one of them and they read as "unrouted" every
    # run without ever having been tried. None is difficult. They were just not
    # on anybody's list.
    "rest": None,
}

# Differential pairs are routed as ONE object -- see route_pair below.
# MATCH THE DESIGN RULE. Net class 2 usb-diff is width 0.15, clearance 0.125 --
# derived in board/STACKUP.md from L1 over L2 across 0.1195 mm of prepreg 2116
# at er 4.45, which IPC-2141 puts at 90.5 ohm against the 90 ohm USB 2.0 target.
# The router had been building 0.20 / 0.20, which is 84.4 ohm AND does not fit:
# at 0.20 the two conductors close to 0.2793 mm in the fan-in where the pads are
# 0.50 mm apart, against the 0.29 that two 0.20 traces need. At 0.15 they need
# 0.24 and the same fan-in clears. The impedance and the geometry wanted the
# same number.
PAIR_W = float(os.environ.get("PAIR_W", "0.15"))     # each trace
PAIR_GAP = float(os.environ.get("PAIR_GAP", "0.125"))  # edge to edge between them
# Intra-pair skew budget. USB 2.0 high speed is 480 Mbps, edge about 500 ps,
# which is ~78 mm in FR-4; the usual working figure is 50 mil.
PAIR_SKEW = float(os.environ.get("PAIR_SKEW", "1.27"))
# How far from the pads the coupled section starts. A pair NECKS DOWN at the
# pins: the two conductors leave their own pads individually and only come
# together once there is room for the coupled corridor. Without this the
# centreline is asked to start at the midpoint between two pads 0.50 mm apart,
# where a 2*w + gap = 0.60 mm corridor cannot exist, and the pair never routes.
PAIR_BACKOFF = float(os.environ.get("PAIR_BACKOFF", "1.20"))

# How close an existing via has to be to a pad to count as that pad's escape.
# The QFN ring is placed at 1.00 and 1.60 mm; 2.5 leaves margin without reaching
# a neighbouring pad's via, which on U2 is at least 0.5 mm away along the edge.
QFN_NEAR = float(os.environ.get("QFN_NEAR", "2.5"))


# The clearance model, the covering disc chain and the string-puller all live in
# geom.py now -- power.py needs the same ones, and when the two files each kept
# their own they drifted into two different and separately wrong ideas of how
# big a pad is. geom.py's header records both mistakes.
rect_pt, rect_seg = G.rect_pt, G.rect_seg
as_circles, straighten = G.as_circles, G.straighten
copper_model, element_pads = G.copper_model, G.element_pads


def inward_map(b):
    """for each pad position, the unit vector pointing into its own package.

    U3 is a TSOP-II: two rows of pads on a 0.80 mm pitch with 186 mm2 of
    completely empty L3 between them, and nothing but other parts outside them.
    Putting each pad's via OUTWARD -- which is what a nearest-clear-point search
    does, since outward is emptier locally -- strands every via behind its own
    pad row, and a trace can then only reach it by threading a 0.17 mm gap
    between two 0.80 mm-pitch vias. That is what produced 28 unroutable nets and
    a 29 mm median on a 15 mm straight line.

    Aiming inward instead puts all 39 target vias on the edge of one open box
    and lets the fan spread out inside it.

    STAGGERED INTO TWO RANKS, because inward alone is still not enough. All 39
    vias at one depth just rebuilds the wall 0.7 mm further in: neighbours stay
    0.80 mm apart, which after dilation leaves a 0.13 mm slot, and a net has to
    reach its own via past 38 others. Alternating the depth puts each rank on a
    1.60 mm pitch with 1.3 mm between vias -- the ordinary dog-bone fan-out for
    a fine-pitch package, and the reason it is ordinary is that traces can then
    get through to the inner rank.
    """
    # RANKS. Two ranks put each on a 1.60 mm pitch. Three puts each on 2.40,
    # four on 3.20 -- every extra rank widens the gap a trace has to slip
    # through to reach an inner via, at the cost of a longer stub and a deeper
    # fan. This is the field that limits L3: an L3 route has to reach its own
    # fan-out via past 38 others, which is why only 6 nets landed there while
    # L16, where a route ends on the pad itself, took 14.
    STAGGER = tuple(float(q) for q in
                    os.environ.get("STAGGER", "0.70,1.45").split(","))
    SIGN = -1.0 if OUTWARD else 1.0
    out = {}
    for el, pts in element_pads(b).items():
        if len(pts) < 8:              # only worth it for a multi-pad package
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        # split the package's pads into rows, one per side, and walk each row in
        # order so neighbouring pads get alternating fan-out depths
        rows = collections.defaultdict(list)
        for x, y in pts:
            dx, dy = cx - x, cy - y
            side = ("v" if dy > 0 else "^") if abs(dy) >= abs(dx) else \
                   (">" if dx > 0 else "<")
            rows[side].append((x, y))
        for side, row in rows.items():
            row.sort(key=(lambda p: p[0]) if side in "v^" else (lambda p: p[1]))
            for k, (x, y) in enumerate(row):
                d = math.hypot(cx - x, cy - y)
                if d <= 1e-6:
                    continue
                out[(round(x, 3), round(y, 3))] = (
                    (SIGN * (cx - x) / d, SIGN * (cy - y) / d), STAGGER[k % len(STAGGER)])
    return out


def pair_ends(pa, pb, padsA, padsB):
    """match up the two nets' pads into the pair's two ENDS.

    Each end is one pad from each net -- at the FT2232 and at the receptacle --
    and the centreline runs between the midpoints. Matching is by proximity,
    which is unambiguous here: the two nets' pads are 0.50 mm apart at U2 and
    0.65 mm at X1, and 13.9 mm apart end to end.
    """
    used, ends = set(), []
    for a in padsA:
        best = min(((math.hypot(a[0] - c[0], a[1] - c[1]), i)
                    for i, c in enumerate(padsB) if i not in used), default=None)
        if best is None:
            continue
        used.add(best[1])
        c = padsB[best[1]]
        ends.append((a, c, ((a[0] + c[0]) / 2.0, (a[1] + c[1]) / 2.0)))
    return ends


# How long the side-swap takes. The two vias sit at opposite ends of it on
# opposite sides, and the conductor that stays on `lay` runs diagonally between
# them, so the vias' clearance to that diagonal is 2*half*XLEN/hypot(XLEN, 2*half)
# -- 0.386 mm at XLEN 1.4 and half 0.20, against the 0.34 a 0.30 via needs from a
# 0.20 trace at 0.09. Shorter than about 1.1 mm and the via touches the diagonal.
XLEN = float(os.environ.get('PAIR_XLEN', '1.40'))
# how far apart the conductors are pulled for the swap, and over what
# length they taper to it. XSEP has to exceed 2*(VIA_L/2 + PAIR_W/2 + clr)
# = 0.63 for the via to clear the other conductor at all.
# 0.40, not more. The flare has to clear the via (0.315 mm here) and NOTHING
# further: at 0.80 the two vias sit 0.40 mm either side of the centreline, which
# pushed them out of the corridor the pair had found and into U2's pad field, and
# the swap could not be placed anywhere at all. 2*hx*XLEN/hypot(XLEN, 2*hx) is
# 0.385 mm at XSEP 0.40, against the 0.315 needed.
XSEP = float(os.environ.get('PAIR_XSEP', '0.40'))
XTAPER = float(os.environ.get('PAIR_XTAPER', '0.50'))


def crossover(p, half, sgn, lay, xlays, b, pa, pb, clr, bx, extra, log):
    """swap which side of the centreline each conductor is on, exactly once.

    A pair whose pad order reverses between its ends cannot be built by constant
    offset: one conductor has to reach the other side, and in the plane that is a
    short. USB_D_P sits at x 32.683 and USB_D_N at 32.183 on U2's south edge, and
    at X1 it is the other way round, so this pair reverses.

    The swap is a layer change, which is how it is done by hand: one conductor
    dives to `xlay`, crosses UNDER the other, and comes back up, while the other
    runs straight through on `lay`. Two vias, on one conductor only, so THE PAIR
    IS NOT SYMMETRIC ACROSS THE SWAP. That is the cost of the reversal, and it is
    why the skew is measured and reported afterwards rather than assumed.

    THE PAIR FLARES FIRST. A via needs VIA_L/2 + PAIR_W/2 + clr from the other
    conductor -- 0.315 mm here -- and the furthest a via at +h can ever be from a
    diagonal running -h to +h is 2h, which at the 0.125 mm gap this board's
    design rule asks for is 0.275. Not marginal: impossible, at any crossover
    length. So the two conductors taper apart to XSEP/2 for the swap and taper
    back after. The gap is not held across the crossover, which is true of every
    hand-drawn one as well -- it is a discontinuity by construction.
    """
    hx = XSEP / 2.0
    order = sorted(range(len(p) - 1),
                   key=lambda i: -math.hypot(p[i + 1][0] - p[i][0],
                                             p[i + 1][1] - p[i][1]))
    vmz = P.Maze(G.obstacles(b, frozenset((pa, pb)), None, extra),
                 bx, clr, P.VIA_L, STEP)
    need_vb = P.VIA_L / 2.0 + PAIR_W / 2.0 + clr
    span = 2 * XTAPER + XLEN
    bo = G.obstacles(b, frozenset((pa, pb)), int(lay), extra)
    xo = dict((xl, G.obstacles(b, frozenset((pa, pb)), int(xl), extra))
              for xl in xlays)
    for i in order:
        a, c = p[i], p[i + 1]
        L = math.hypot(c[0] - a[0], c[1] - a[1])
        if L < span + 0.40:
            continue
        ux, uy = (c[0] - a[0]) / L, (c[1] - a[1]) / L
        nx, ny = -uy, ux
        at = lambda t: (a[0] + ux * t, a[1] + uy * t)
        off = lambda q, d: (q[0] + nx * d, q[1] + ny * d)
        h, k = half * sgn, hx * sgn
        # SLIDE ALONG THE SEGMENT rather than taking its midpoint and giving up.
        # That is what reported 'no room' on an 11 mm straight: the flare geometry
        # was fine everywhere -- 0.695 mm of via clearance against the 0.315
        # needed -- and the only thing failing was the two vias landing in U2's
        # pad field. A little further along the same segment they do not.
        steps = int((L - span) / 0.20) + 1
        for st in range(steps):
            t0 = 0.20 * st + (L - span - 0.20 * (steps - 1)) / 2.0
            P0, P1 = at(t0), at(t0 + span)
            Pa_, Pb_ = at(t0 + XTAPER), at(t0 + XTAPER + XLEN)
            A0, A1 = off(Pa_, +k), off(Pb_, -k)
            B0, B1 = off(Pa_, -k), off(Pb_, +k)
            if min(E.seg_pt(B0, B1, A0), E.seg_pt(B0, B1, A1)) < need_vb - 1e-9:
                continue
            if not all(vmz.free[vmz.j(q[1]) * vmz.W + vmz.i(q[0])]
                       for q in (A0, A1)):
                continue
            if not G.clear(B0, B1, bo, clr, PAIR_W):
                continue
            for xl in xlays:
                if not G.clear(A0, A1, xo[xl], clr, PAIR_W):
                    continue
                head, tail = p[:i + 1] + [P0], [P1] + p[i + 1:]
                Ah = G.offset_polyline(head, +h) + [A0]
                At = [A1] + G.offset_polyline(tail, -h)
                Bh = G.offset_polyline(head, -h) + [B0]
                Bt = [B1] + G.offset_polyline(tail, +h)
                log('   %s/%s: side swap on L%s, %.2f mm at (%.2f,%.2f), flared'
                    ' to %.2f mm; vias clear the other conductor by %.3f mm'
                    % (pa, pb, xl, XLEN, Pa_[0], Pa_[1], XSEP,
                       min(E.seg_pt(B0, B1, A0), E.seg_pt(B0, B1, A1))))
                return ((Ah, At), (Bh, Bt), [A0, A1], [(A0, A1, xl)], (B0, B1))
    return None


def route_pair(b, pa, pb, lay, clr, bx, extra, log=print):
    """route a differential pair as one object, then split it into two traces.

    The pair's centreline is routed ONCE, through a corridor wide enough for
    both traces and the gap between them (2*w + gap). Both conductors are then
    generated from that one path at -half and +half. Constant gap and mirrored
    bends are properties of the construction, not things the search has to be
    steered towards -- which is the whole answer to "why must pairs be routed by
    hand": they must not, they must be routed as one object rather than two.

    What this does NOT do is tune length. A 90 degree bend makes the outer
    conductor longer by twice the gap, so the skew is reported and left for a
    human to judge against the budget rather than silently serpentined.

    IT PLACES ITS OWN VIAS when the coupled layer is not the pads' layer, which
    is the normal case here: the pair wants L4 -- 13.9 mm dead straight, 0.003 mm
    of skew against a 1.27 mm budget, where L1 wanders to 30 mm and spends the
    whole budget on one bend -- while the pads are on L1. One via per conductor
    at each end, at the point where that conductor joins the coupled section, so
    the two are symmetric and the pair stays matched. The two vias at an end
    would sit w + gap apart -- 0.275 mm at the 0.15/0.125 this board uses for
    90 ohm -- against the 0.390 that two 0.30 mm vias at 0.09 need, so THE ENDS
    ARE SPLAYED to that 0.390 and taper back over their own first segment,
    0.0575 mm per conductor. The coupled section keeps its gap and its
    impedance; only the ends open up, and an end is coupled to nothing, it is
    about to become a via. This paragraph promised the widening for a long time
    while the code only measured the gap and gave up, which is why no pair on
    the board routed; the worked example it used to quote, 0.20/0.20 = 0.400,
    predates PAIR_W and PAIR_GAP being set for impedance.
    """
    padsA = [(x, y) for x, y, sd in P.pads_of(b, pa, skip=())]
    padsB = [(x, y) for x, y, sd in P.pads_of(b, pb, skip=())]
    ends = pair_ends(pa, pb, padsA, padsB)
    if len(ends) < 2:
        log("   **** %s/%s: found %d end(s), need 2" % (pa, pb, len(ends)))
        return None
    (a0, b0, m0), (a1, b1, m1) = ends[0], ends[1]
    # back the coupled section off the pads at both ends -- see PAIR_BACKOFF
    dx, dy = m1[0] - m0[0], m1[1] - m0[1]
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    # BACK OFF IN WHICHEVER DIRECTION HAS ROOM, per end. Backing off "towards
    # the other end" is wrong whenever the pins face away from the destination,
    # which is exactly this pair: the FT2232's DP/DM are on U2's SOUTH edge and
    # the receptacle is north, so a step towards X1 lands inside U2's own pad
    # field and the via has nowhere to go. A pair fans out AWAY from its part
    # first, then couples.
    weff = 2 * PAIR_W + PAIR_GAP
    kk = min(PAIR_BACKOFF, L / 3.0)
    starts = [(m0[0] + ux * kk, m0[1] + uy * kk), (m0[0] - ux * kk, m0[1] - uy * kk)]
    finish = [(m1[0] - ux * kk, m1[1] - uy * kk), (m1[0] + ux * kk, m1[1] + uy * kk)]
    vmz0 = P.Maze(G.obstacles(b, frozenset((pa, pb)), None, extra),
                  bx, clr, P.VIA_L, STEP)
    padlay0 = str(P.pads_of(b, pa, skip=())[0][2])

    def via_ok(pt):
        if padlay0 == lay:
            return True
        h = (PAIR_W + PAIR_GAP) / 2.0
        for sx, sy in ((-uy * h, ux * h), (uy * h, -ux * h)):
            q = (pt[0] + sx, pt[1] + sy)
            if not vmz0.free[vmz0.j(q[1]) * vmz0.W + vmz0.i(q[0])]:
                return False
        return True

    obst = G.obstacles(b, frozenset((pa, pb)), int(lay), extra)
    mz = P.Maze(obst, bx, clr, weff, STEP)

    # WHICH WAY TO BACK OFF IS A QUESTION FOR THE BOARD, and it was being
    # answered by the order of a list. via_ok() asks "can a via go here" and
    # short-circuits to True when the pads are already on the routing layer,
    # because then no via is needed -- so on L1, where U2 and X1 both sit,
    # `next((q for q in starts if via_ok(q)), starts[0])` always returned
    # starts[0]: the step TOWARDS the other end. For this pair that is a step
    # INTO THE PACKAGE. The FT2232's DP/DM are on U2's south edge and the
    # receptacle is north, so starts[0] is (32.43, 8.61) -- 1.2 mm inside a
    # QFN-64 whose pad field has no 0.425 mm corridor anywhere in it, and the
    # pair failed on every layer with "no corridor" while a perfectly good
    # start point sat unexamined 1.2 mm to the SOUTH. The comment on `starts`
    # already said a pair fans out away from its part first; only the code
    # disagreed.
    #
    # So ask whether each candidate is free on the layer about to be routed on,
    # prefer the ones that are, and try the combinations rather than committing
    # to one. Four path() calls at worst, against a maze that is already built.
    def usable(q):
        if not via_ok(q):
            return False
        i, j = mz.i(q[0]), mz.j(q[1])
        k = j * mz.W + i
        return 0 <= i < mz.W and 0 <= k < len(mz.free) and mz.free[k]

    cands = [(q0, q1) for q0 in starts for q1 in finish]
    cands.sort(key=lambda z: (not usable(z[0])) + (not usable(z[1])))
    c0, c1 = cands[0]
    p = None
    for q0, q1 in cands:
        p = mz.path(q0, q1)
        if p is not None:
            c0, c1 = q0, q1
            break
    if p is None:
        # SAY SO. This was the one exit in route_pair that returned None in
        # silence, so "could not be routed as a pair" covered both "the corridor
        # does not exist" and "the geometry is illegal", which are different
        # problems with different fixes.
        log("   **** %s/%s: no %.2f mm corridor on L%s between (%.2f,%.2f) and"
            " (%.2f,%.2f)" % (pa, pb, weff, lay, c0[0], c0[1], c1[0], c1[1]))
        return None
    p = straighten(p, obst, clr, weff)
    # CARRY THE CENTRELINE BACK TO THE PAD MIDPOINTS before offsetting. The maze
    # still runs between the backed-off points, because it needs a full weff of
    # room and there is not that much between two pads 0.50 mm apart -- that is
    # what PAIR_BACKOFF is for. But offsetting from the backed-off point leaves
    # each conductor to find its own pad from wherever the centreline happened to
    # be pointing, and when it points ALONG the pad-pair axis the two legs crowd:
    # 0.0593 mm at 0.15 conductors needing 0.24. Extending to m0 and m1 first
    # makes the offsets land on the pad axis by construction, so the legs come out
    # short and parallel. weff is 0.425 at 0.15/0.125, which does fit between two
    # pads on a 0.50 pitch -- at the old 0.20/0.20 it was 0.60 and did not.
    if weff < math.hypot(a0[0] - b0[0], a0[1] - b0[1]) - 1e-9:
        p = [m0] + p + [m1]
        p = [q for k, q in enumerate(p)
             if k == 0 or math.hypot(q[0] - p[k - 1][0], q[1] - p[k - 1][1]) > 1e-6]
    half = (PAIR_W + PAIR_GAP) / 2.0

    # DOES THE FAN-IN ACTUALLY CROSS? The side test this replaces asked which
    # side of the centreline each pad was on, which is degenerate precisely where
    # it matters: when the centreline leaves c0 running PARALLEL to the pad-pair
    # axis, the normal is perpendicular to it, dot(a0 - b0, n) is zero, and the
    # answer is noise. That is this pair -- the offsets came out stacked north
    # and south (8.74 and 8.47) while the pads sit side by side east and west,
    # and the two fan-in legs crossed at 0.0415 mm. Ask the question that is
    # actually being decided instead: do the two legs cross, yes or no.
    # MEASURE THE GAP, do not ask whether the legs intersect. An intersection
    # test answers no when two legs merely graze, and grazing is the same defect:
    # the fan-out came back 0.0117 mm apart with the crossing test satisfied.
    # Distance subsumes crossing -- segments that cross are zero apart.
    need_ff = PAIR_W + clr

    def fits(sgn):
        A = G.offset_polyline(p, +half * sgn)
        B = G.offset_polyline(p, -half * sgn)
        return (A, B,
                E.seg_seg(a0, A[0], b0, B[0]) >= need_ff - 1e-9,
                E.seg_seg(a1, A[-1], b1, B[-1]) >= need_ff - 1e-9)

    xvias, xsegs, xjoin = [], [], None
    opts = {sgn: fits(sgn) for sgn in (+1.0, -1.0)}
    ok = [sgn for sgn, (_A, _B, s, e) in opts.items() if s and e]
    if ok:
        A, B = opts[ok[0]][0], opts[ok[0]][1]
    else:
        # neither sign clears both ends: the pad order reverses, so swap sides
        # once, mid-run, through a layer change
        start_ok = [sgn for sgn, (_A, _B, st, _e) in opts.items() if st]
        if not start_ok:
            log('   **** %s/%s: neither offset clears the fan-in at the U2 end'
                % (pa, pb))
            return None
        sgn = start_ok[0]
        _L = [q for q in os.environ.get('BUS_LAYERS', '3,4,16').split(',') if q]
        _pl = str(P.pads_of(b, pa, skip=())[0][2])
        if _pl not in _L:
            _L.append(_pl)
        got = crossover(p, half, sgn, lay, [q for q in _L if q != lay],
                        b, pa, pb, clr, bx, extra, log)
        if got is None:
            log('   **** %s/%s: the pad order reverses between the ends, so the'
                ' pair needs a side swap, and no segment of the centreline on L%s'
                ' has room for one' % (pa, pb, lay))
            return None
        (Ah, At), (Bh, Bt), xvias, xsegs, _bd = got
        xjoin = len(Ah)   # the gap the swap fills, indexed before [a0] is added
        A, B = Ah + At, Bh + Bt
    # fan in: from each pad to where its conductor joins the coupled section
    padlay = str(P.pads_of(b, pa, skip=())[0][2])
    vias, segs = [], []
    if padlay == lay:
        A = [a0] + A + [a1]
        B = [b0] + B + [b1]
        # the swap's own copper: A's two vias, and its run on the other layer.
        # A jumps from head to tail, so the segment that would join them on `lay`
        # is dropped -- that gap IS the crossover.
        # DROP THE RIGHT SEGMENT. A is [a0] + Ah + At + [a1] by this point, so the
        # join between the head and the tail -- the gap the crossover fills -- is
        # segment len(Ah), not len(A) - len(At) - 1. Getting it wrong left the
        # crossing segment in place and cut the tail instead, which check_board
        # would have read as the two conductors touching at exactly 0.0000 mm.
        aseg = [(u, v, lay) for u, v in zip(A, A[1:])]
        if xsegs:
            aseg = [q for k, q in enumerate(aseg) if k != xjoin] + list(xsegs)
        segs = (aseg, [(u, v, lay) for u, v in zip(B, B[1:])])
        # The crossover's vias belong to A -- it is the conductor that dives to
        # the other layer and comes back. B stays put and owns none of them.
        viasA, viasB = list(xvias), []
    else:
        # two vias an end, one per conductor, where it meets the coupled run
        need = P.VIA_L + clr
        # THE FAN-OUT NEEDS MORE ROOM THAN THE COUPLED SECTION DOES, and the gap
        # that suits the impedance does not give it. The two vias at an end sit
        # where their conductors end -- PAIR_W + PAIR_GAP apart, 0.275 mm at
        # 0.15/0.125 -- and two 0.30 mm vias at 0.09 clearance need 0.390. The
        # docstring at the top has promised since it was written that "the
        # fan-out is widened if it does not hold"; it never was. route_pair
        # measured the gap, reported it and gave up, and the worked example in
        # that docstring assumes the older 0.20/0.20 = 0.400 that happened to
        # clear. PAIR_W and PAIR_GAP were later set to 0.15/0.125 for 90 ohm and
        # nothing rechecked the fan-out against them, so EVERY pair on this board
        # died here: USB_D_P/N after finding its corridor AND placing its side
        # swap, both XADC pairs on the identical number.
        #
        # Splay the two ends apart to exactly `need` and let each taper back over
        # its own first segment. At 0.15/0.125 that is 0.0575 mm per conductor.
        # The coupled section keeps its gap and its impedance -- only the ends
        # open up, and an end is not coupled to anything, it is about to become a
        # via. The check below stays as a backstop rather than being deleted: if
        # a future width and gap cannot be splayed apart for some other reason,
        # it should still say so rather than write a short.
        def splay(u, v):
            d = math.hypot(u[0] - v[0], u[1] - v[1])
            if d < 1e-9 or d >= need - 1e-9:
                return u, v
            k = (need - d) / 2.0 / d
            return ((u[0] + (u[0] - v[0]) * k, u[1] + (u[1] - v[1]) * k),
                    (v[0] + (v[0] - u[0]) * k, v[1] + (v[1] - u[1]) * k))

        if len(A) >= 2 and len(B) >= 2:
            _a0, _b0 = splay(A[0], B[0])
            _a1, _b1 = splay(A[-1], B[-1])
            A = [_a0] + A[1:-1] + [_a1]
            B = [_b0] + B[1:-1] + [_b1]
        for (pa_, pb_) in ((A[0], B[0]), (A[-1], B[-1])):
            if math.hypot(pa_[0] - pb_[0], pa_[1] - pb_[1]) < need - 1e-9:
                log("   **** %s/%s: via pair %.3f apart, needs %.3f -- widen the gap"
                    % (pa, pb, math.hypot(pa_[0] - pb_[0], pa_[1] - pb_[1]), need))
                return None
        vmz = P.Maze(G.obstacles(b, frozenset((pa, pb)), None, extra),
                     bx, clr, P.VIA_L, STEP)
        for q in (A[0], A[-1], B[0], B[-1]):
            if not vmz.free[vmz.j(q[1]) * vmz.W + vmz.i(q[0])]:
                log("   **** %s/%s: no room for a via at (%.2f, %.2f)"
                    % (pa, pb, q[0], q[1]))
                return None
        # THE SIDE SWAP APPLIES HERE TOO, and it was being thrown away. The
        # crossover is run for either branch -- it is what answers a reversed
        # pad order -- but only the padlay == lay branch above ever used its
        # result: this one rebuilt A's segments straight from the polyline,
        # keeping the very segment the layer change exists to replace, and
        # dropped xvias and xsegs on the floor. So the swap was computed,
        # reported ("side swap on L4, 1.40 mm ... vias clear by 0.385"), and
        # then not applied, and the two conductors crossed at 0.0000 mm. That
        # is the case for every pair whose pads are not on the coupled layer,
        # which here is USB_D_P/N: pads on L1, coupled on L3.
        #
        # The index differs by one between the branches. There A is
        # [a0] + Ah + At + [a1] and the head-to-tail join is segment len(Ah);
        # here the fan-in leg is a separate entry and the polyline is Ah + At,
        # so the same join is segment len(Ah) - 1. Getting this wrong removes a
        # real segment and leaves the crossing one in place, which reads as the
        # conductors touching at exactly 0.0000 mm -- the same symptom, so it
        # would look like no progress at all.
        amid = [(u, v, lay) for u, v in zip(A, A[1:])]
        if xsegs and xjoin is not None:
            amid = [q for k, q in enumerate(amid) if k != xjoin - 1] + list(xsegs)
        viasA, viasB = [A[0], A[-1]] + list(xvias), [B[0], B[-1]]
        segs = ([(a0, A[0], padlay)] + amid + [(A[-1], a1, padlay)],
                [(b0, B[0], padlay)] + [(u, v, lay) for u, v in zip(B, B[1:])]
                + [(B[-1], b1, padlay)])
        A = [a0] + A + [a1]
        B = [b0] + B + [b1]
    skew = abs(G.polylen(A) - G.polylen(B))
    log("   %s / %s on L%s: %.2f and %.2f mm, gap %.2f, skew %.3f mm (budget %.2f) %s"
        % (pa, pb, lay, G.polylen(A), G.polylen(B), PAIR_GAP, skew, PAIR_SKEW,
           "OK" if skew <= PAIR_SKEW else "**** OVER BUDGET"))
    # VERIFY THE CONSTRUCTION INSTEAD OF TRUSTING IT. Offsetting one centreline
    # by +/-half gives a constant gap along the coupled run, but it says nothing
    # about the two fan-in legs, and those are where this pair fails: USB_D_P sits
    # at x=32.683 and USB_D_N at 32.183 on U2's south edge, and the order reverses
    # at X1, so a constant-offset pair has to CROSS. It did, and it wrote the
    # crossing as copper -- check_board measured D+ against D- at -0.1000, two
    # 0.10 traces on one centreline, which is a short between the two halves of a
    # USB pair. It went unseen because the writer was dropping this route on the
    # floor; the geometry has been wrong for as long as it has existed.
    # LAYER BY LAYER. This compared every A segment against every B segment and
    # ignored which layer each was on. That was harmless while both conductors
    # lived on one layer, and wrong the moment a crossover exists: the whole
    # point of the side swap is that the two conductors DO cross, on different
    # layers, where crossing is exactly what is wanted.
    Aseg = list(segs[0])
    Bseg = list(segs[1])
    need = PAIR_W + clr
    for u, v, la in Aseg:
        for q, r, lb in Bseg:
            if la != lb:
                continue
            gap = E.seg_seg(u, v, q, r)
            if gap < need - 1e-9:
                log('   **** %s/%s: the two conductors come within %.4f mm on'
                    ' L%s, needs %.4f%s'
                    % (pa, pb, gap, la, need,
                       ' -- they CROSS' if gap < PAIR_W else
                       ' -- clearance, not a crossing'))
                return None
    # AGAINST THE PAD RECTANGLE, AND WITH THE RIGHT HALF-WIDTH. This compared a
    # conductor's CENTRELINE to a pad's CENTRE POINT and required PAIR_W + clr,
    # which is the conductor-to-conductor rule, not the conductor-to-pad one. A
    # U2 signal pad is 0.25 x 0.60, so measuring to its centre understates the
    # violation by a pad half-width: USB_D_N read 0.2793 mm from the USB_D_P pad
    # CENTRE, which is 0.054 mm from its EDGE against the 0.090 required.
    for nm, mine, other in ((pa, Aseg, pb), (pb, Bseg, pa)):
        for rec in E.board_copper(b, skip=()):
            onet, ox, oy, ohx, ohy, osd = rec[:6]
            if onet != other:
                continue
            for u, v, sl in mine:
                if not (osd == 0 or str(osd) == sl):
                    continue
                d = G.rect_seg((ox, oy, ohx, ohy, 0.0), u, v) - PAIR_W / 2.0
                if d < clr - 1e-9:
                    log('   **** %s/%s: %s runs %.4f mm from a %s pad edge on'
                        ' L%s, needs %.4f' % (pa, pb, nm, d, other, sl, clr))
                    return None
    # AND AGAINST THE REST OF THE BOARD, which nothing here was doing. The maze
    # routes the CENTRELINE and only the centreline: the fan-in legs from each
    # pad to where its conductor joins the coupled section are drawn afterwards,
    # and the crossover's segments come from crossover(). The only check either
    # of them ever faced was the loop above, which compares against the PARTNER
    # NET'S PADS -- one net, pads only. Every wire already on the board was
    # invisible to them. power.py routes FT-VPLL across U2's south side before
    # the pairs group runs, and both USB conductors came out 0.200 mm INSIDE it:
    # check_board found it, route_pair called the pair a success and reported
    # its skew. The coupled section passes this trivially -- the maze cleared it
    # at weff/2, which is wider than PAIR_W/2 -- so what this really guards is
    # every segment the maze did not produce.
    _obs = {}
    for u, v, sl in Aseg + Bseg:
        if sl not in _obs:
            _obs[sl] = G.obstacles(b, frozenset((pa, pb)), int(sl), extra)
        for ox, oy, orr in _obs[sl]:
            d = E.seg_pt(u, v, (ox, oy)) - orr - PAIR_W / 2.0
            if d < clr - 1e-9:
                log('   **** %s/%s: a conductor runs %.4f mm from foreign copper'
                    ' on L%s at (%.2f, %.2f), needs %.4f'
                    % (pa, pb, d, sl, ox, oy, clr))
                return None
    # SPLIT BY OWNERSHIP, NOT BY POSITION. This was vias[:2] and vias[2:], which
    # is right only while each conductor has exactly two and they are in that
    # order. Adding the crossover's vias to the list broke it silently: they went
    # to whichever half the slice happened to reach, so USB_D_N came out with
    # four vias and USB_D_P with two, and USB_D_P's own trace then ran through a
    # via that had been filed under USB_D_N -- 0.0000 mm, reported against the
    # wrong net. The two lists are built where the vias are, and named.
    return {pa: (viasA, segs[0]), pb: (viasB, segs[1])}


def escape_end(b, net, cx, cy):
    """where the escape leaves off -- what this router starts from.

    It used to be "the net's own via", which was fine while stage 3 gave every
    escape one. It no longer does: 44 of 103 now end as bare copper on L1,
    because their far end is reachable there and a via would have been a wall
    for nothing. For those the terminal is the FREE END of the fan -- the
    endpoint of the net's L1 copper that no second segment shares, taken
    furthest out from the ball field.
    """
    m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net), b, re.S)
    if not m:
        return None
    body = m.group(1)
    out = lambda p: max(abs(p[0] - cx), abs(p[1] - cy))
    vs = [(float(q.group(1)), float(q.group(2))) for q in
          re.finditer(r'<via x="([-\d.]+)" y="([-\d.]+)"', body)]
    if vs:
        return (max(vs, key=out), None)     # a via: reachable from every layer
    ends = collections.Counter()
    for q in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                         r' y2="([-\d.]+)" width="[\d.]+" layer="1"/>', body):
        ends[(round(float(q.group(1)), 3), round(float(q.group(2)), 3))] += 1
        ends[(round(float(q.group(3)), 3), round(float(q.group(4)), 3))] += 1
    free = [p for p, n in ends.items() if n == 1]
    # bare copper: the route MUST continue on the layer that copper is on, or it
    # starts at the right coordinates on the wrong layer and connects to nothing
    return (max(free, key=out), "1") if free else None


def place_via(px, py, allm, surfm, clr, bx, extra, hint=None):
    """a spot for this pad's via, and the stub to reach it.

    Scored by how much room it leaves, not just by how close it is. On a pad row
    at 0.80 mm pitch the shortest legal candidate is often sideways, wedged
    between two neighbours; maximising the tightest clearance instead walks the
    via straight out along the pad's long axis, which is what the part expects.
    """
    arects, acircs, asegs = allm
    srects, scircs, ssegs = surfm
    inward, want = (None, 0.70) if hint is None else hint
    best = None
    for rad in sorted((0.70, 0.85, 1.00, 1.15, 1.30, 1.45, 1.60, 1.75),
                      key=lambda r: (abs(r - want), r)):
        for k in range(72):
            a = 2 * math.pi * k / 72.0
            x, y = px + rad * math.cos(a), py + rad * math.sin(a)
            if not (bx[0] + 0.5 < x < bx[2] - 0.5 and bx[1] + 0.5 < y < bx[3] - 0.5):
                continue
            need_v = clr + VIA_L / 2
            m = min([rect_pt(r, x, y) - need_v for r in arects]
                    + [math.hypot(x - ox, y - oy) - (r + need_v)
                       for ox, oy, r in acircs + extra]
                    + [E.seg_pt(u, v, (x, y)) - (r + need_v) for u, v, r in asegs])
            if m < -1e-9:
                continue
            need_s = clr + STUB_W / 2
            st = ((px, py), (x, y))
            m2 = min([rect_seg(r, st[0], st[1]) - need_s for r in srects]
                     + [E.seg_pt(st[0], st[1], (ox, oy)) - (r + need_s)
                        for ox, oy, r in scircs + extra]
                     + [E.seg_seg(st[0], st[1], u, v) - (r + need_s)
                        for u, v, r in ssegs])
            if m2 < -1e-9:
                continue
            # prefer inward, then room, then short. The inward term is first
            # and binary on purpose: a candidate 0.1 mm further out but with
            # more local room must not win, because "more local room" is
            # exactly what points the via the wrong way.
            dot = 1.0 if inward is None else (
                math.cos(a) * inward[0] + math.sin(a) * inward[1])
            score = (dot > 0.3, min(m, m2), -rad)
            if best is None or score > best[0]:
                best = (score, (round(x, 4), round(y, 4)))
        if best:
            return best[1]
    return None


# WHAT ground.py AND power.py OWN. Everything else that no named group above
# claims belongs to "rest". Keep this in step with power.py's RAILS.
OWNED = re.compile(r"^(GND|VCC3V3|VCC1V0|VCC1V8|FT-V(CORE|PHY|PLL)|VU|VEXT|USB5V0)$")


def group_nets(b, rx):
    """the nets in one group

    rx PAIRS is every differential pair; None is everything nothing else
    claims. EVERY OTHER GROUP EXCLUDES THE PAIRS, because "pairs" routes them
    before any group runs and routing a net twice writes its copper twice --
    the apply guard only looks at the L3 routing layer and would not catch a
    pair written to L1 or L4.
    """
    sig = re.search(r"<signals>(.*)</signals>", b, re.S).group(1)
    names = [m.group(1) for m in re.finditer(r'<signal name="([^"]+)"[^>]*>', sig)]
    paired = G.find_pairs(set(names))
    if rx is PAIRS:
        return sorted(paired)
    if rx is not None:
        return sorted(n for n in names if rx.match(n) and n not in paired)
    named = [g for g in GROUPS.values() if g is not None and g is not PAIRS]
    return sorted(n for n in names
                  if not OWNED.match(n) and n not in paired
                  and not any(g.match(n) for g in named))


def main(gname="sdram"):
    b = io.open(BRD, encoding="utf-8", errors="replace").read()
    clr = float(re.search(r'<param name="mdWireWire" value="([\d.]+)mm"/>', b).group(1))
    # CLR overrides the board's own rule, for asking what a different fab would
    # buy us before committing to one. PCBWay answered on 2026-08-27 that their
    # floor is 3/3 mil = 0.0762 mm, against JLCPCB's 0.09 the board is built on.
    # Measuring only makes sense on the NEW copper: the escape, the pours and
    # the rails are already down at 0.09 and are not re-run for this.
    # MEASURED, and it buys nothing here: 0.0762 clearance routes the same 21
    # nets as 0.09, and dropping the trace to 0.0762 as well makes it slightly
    # worse (19). Which is what the 108-lane cut already said -- geometry is not
    # the constraint, this router is. Switching fab for the bus would be
    # spending an advanced-process tier on nothing.
    clr = float(os.environ.get("CLR", clr))
    w20 = re.findall(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"'
                     r' width="[\d.]+" layer="20"/>', b)
    xs = [float(q) for v in w20 for q in (v[0], v[2])]
    ys = [float(q) for v in w20 for q in (v[1], v[3])]
    bx = (min(xs), min(ys), max(xs), max(ys))
    nets = group_nets(b, GROUPS[gname])
    # WHICH LAYER THE FAR PADS ARE ON, read rather than assumed. This was "16"
    # in nine places, because U3 was on the back when it was written. Flip U3 to
    # the front and every one of them is wrong -- the first symptom is a
    # KeyError on boardpads[n2]["16"], and the ones that would not have crashed
    # are worse, because they would have routed to the wrong side in silence.
    _sides = collections.Counter(
        sd for net in nets for _x, _y, sd in P.pads_of(b, net, skip=("U1",)))
    PADLAY = str(_sides.most_common(1)[0][0]) if _sides else "16"
    # SIDE 0 MEANS A PLATED HOLE -- present on every layer, not on layer zero.
    # A group whose far end is a through hole needs no fan-out via and may
    # finish on any layer, so every layer is a pad layer for it.
    THRU = PADLAY == "0"
    if THRU:
        PADLAY = LAYER
    # L1 stays out by default. It carries the escape's 1170 stage-3 traces, and
    # measured with it in the list it is neutral at best. BUS_LAYERS=3,16,1
    # turns it on -- needed if stage 3 is ever changed to stop viaing, since
    # those escapes then end as bare copper ON L1 and a route that starts
    # anywhere else connects to nothing.
    # L4 IS A SIGNAL LAYER NOW. It was a second ground plane, which gave L3
    # ground above and below at the price of leaving the board with two usable
    # routing layers once L1 went to the escape. Freeing it is the only change
    # anyone has proposed that ADDS routing resource rather than rearranging it.
    LAYERS = [q for q in os.environ.get("BUS_LAYERS", "3,4,16").split(",") if q]
    # the layer the far pads are on must be routable, or the group cannot finish
    # on them at all -- the USB group's far ends are U2 and X1, both on L1
    if PADLAY not in LAYERS:
        LAYERS.append(PADLAY)
        print("   L%s added to the routable layers: the far pads are there" % PADLAY)
    _b2, _pos, _l2, _n2, _c2 = E.load(BRD)
    _xs = sorted({round(p[0], 3) for p in _pos.values()})
    _ys = sorted({round(p[1], 3) for p in _pos.values()})
    CX3, CY3 = (_xs[0] + _xs[-1]) / 2.0, (_ys[0] + _ys[-1]) / 2.0
    _E = dict((n, escape_end(b, n, CX3, CY3)) for n in nets)
    START = dict((n, v[0] if v else None) for n, v in _E.items())
    # which layers the route may START on: any, if the escape ended on a via;
    # only the escape layer, if it ended as bare copper
    SLAY = dict((n, (v[1],) if v and v[1] else tuple(LAYERS)) for n, v in _E.items())
    _bare = sum(1 for v in _E.values() if v and v[1])
    print("   escape terminals: %d on a via (any layer), %d on bare L1 copper"
          % (sum(1 for v in _E.values() if v) - _bare, _bare))
    # ---- DIFFERENTIAL PAIRS FIRST, as single objects.
    # They are the most constrained thing in any group and the least able to
    # take what is left over, so they choose their corridor before the
    # single-ended nets start filling it.
    PAIRED = G.find_pairs(set(nets))
    pairplan = {}
    if PAIRED:
        print("   %d differential pair(s) in this group: %s"
              % (len(PAIRED) // 2,
                 ", ".join(sorted(n for n in PAIRED if PAIRED[n][1] > 0))))
        for pa in sorted(n for n in PAIRED if PAIRED[n][1] > 0):
            pb = PAIRED[pa][0]
            sides = set(sd for n in (pa, pb)
                        for _x, _y, sd in P.pads_of(b, n, skip=()))
            # both ends on one surface means no via and no layer change; that is
            # the case for USB_D_P/- here, U2 and X1 are both on the front
            # TRY EVERY LAYER AND TAKE THE BEST, not the first that works.
            # On a clean board this pair routes on L1 at 30.0/28.7 mm with
            # 1.300 mm of skew -- over the 1.27 budget -- and on L4 at
            # 13.9/13.9 with 0.003. Both "work"; only one is right. Score by
            # skew first, then by length.
            cand = [str(next(iter(sides)))] if len(sides) == 1 else []
            tried = []
            # KEEP THE REASONS. This passed log=lambda *a: None, which is right
            # while iterating -- failing on L3 says nothing about L4 -- and
            # threw the reasons away when EVERY layer failed, leaving one
            # generic "could not be routed as a pair" for a function that has
            # eight distinct ways to give up and logs which one at each of
            # them. Collect per layer, print only if nothing worked.
            why = collections.OrderedDict()
            for lay in cand + [L for L in LAYERS if L not in cand]:
                why[lay] = []
                r = route_pair(b, pa, pb, lay, clr, bx,
                               [q for v in pairplan.values()
                                for u, c, _l in v[1]
                                for q in G.sample(u, c, PAIR_W / 2)],
                               log=lambda *a, **k: why[lay].append(
                                   " ".join(str(q) for q in a)))
                if r:
                    la = sum(math.hypot(c[0] - u[0], c[1] - u[1])
                             for u, c, _l in r[pa][1])
                    lb = sum(math.hypot(c[0] - u[0], c[1] - u[1])
                             for u, c, _l in r[pb][1])
                    tried.append((abs(la - lb), la + lb, lay, r))
            tried.sort(key=lambda q: (q[0] > PAIR_SKEW, q[0], q[1]))
            got = tried[0][3] if tried else None
            if tried:
                print("   %s/%s: %s -> chose L%s, %.1f/%.1f mm, skew %.3f (budget %.2f) %s"
                      % (pa, pb,
                         ", ".join("L%s skew %.3f" % (q[2], q[0]) for q in tried),
                         tried[0][2], tried[0][1] / 2, tried[0][1] / 2, tried[0][0],
                         PAIR_SKEW, "OK" if tried[0][0] <= PAIR_SKEW else "**** OVER"))
            if got:
                pairplan.update(got)
            else:
                print("   **** %s / %s could not be routed as a pair" % (pa, pb))
                for lay, msgs in why.items():
                    for m in msgs:
                        print("        L%-2s %s" % (lay, m.strip().lstrip("*").strip()))
        nets = [n for n in nets if n not in pairplan]

    hint = inward_map(b)
    print("routing group %r: %d nets, L%s to the far pads on L%s, %.2f mm trace,"
          " clearance %.3f" % (gname, len(nets), LAYER, PADLAY, W, clr))

    P.STUB_W = STUB_W          # via_for checks the stub at the width we will draw

    # SPLIT THE BUS ACROSS THE TWO LAYERS UP FRONT, rather than letting L16
    # mop up whatever L3 could not take. Used as a pure fall-back, L3 is
    # oversubscribed and fills with the short easy nets while L16 sits nearly
    # empty: 25 on L3, 7 on L16, 7 unroutable. Alternating along U3's pad order
    # gives each layer half the fan at twice the pitch, and each half still
    # nests because taking every other net out of a monotone sequence leaves it
    # monotone.
    half = {}
    for net in nets:
        pads = P.pads_of(b, net, skip=("U1",))
        half[net] = ("bot" if pads[0][1] < 11.5 else "top") if pads else "bot"
    pref = {}
    for hname in ("bot", "top"):
        row = sorted([n for n in nets if half[n] == hname],
                     key=lambda n: P.pads_of(b, n, skip=("U1",))[0][0])
        for k, n in enumerate(row):
            # SPLIT=1 alternates the two layers; it measured WORSE (21 of 39 at
            # 0.10 mm against 32 for plain fall-back), because L16 is far more
            # constrained than L3 -- U3's own 54 pads sit on it and block the
            # very region the bus has to cross. Half the fan is more than L16
            # can take, so forcing nets onto it strands them. Default off.
            pref[n] = (LAYER if k % 2 == 0 else "16") if SPLIT else LAYER
    print("   split by U3 pad order: L%s %d nets, L16 %d nets"
          % (LAYER, sum(1 for v in pref.values() if v == LAYER),
             sum(1 for v in pref.values() if v == "16")))

    # ------------------------------------------------------- rip up and retry
    #
    # Greedy one-pass routing tops out at 20 of 39 and no amount of reordering
    # moves it: shortest-first gives 20, river order along U3's pads gives 9,
    # hardest-first gives 16. The reason is that Maze.path has no cost function
    # -- it returns whichever shortest-cell-count path it happens to find, which
    # is not lane-like, so an early net can sprawl across a corridor a later one
    # needs and nothing in a single pass can undo it.
    #
    # So undo it. When a net cannot route against the copper that is down, route
    # it again against the BOARD ONLY, see which of the group's nets that path
    # runs into, rip those up, keep the new route, and put the victims back in
    # the queue. A net may be ripped only RIP_LIMIT times so the loop cannot
    # trade two nets back and forth for ever.
    GROUP = set(nets)
    # RIP_LIMIT IS LOW AND MUST STAY LOW. More ripping is worse, not better,
    # because this loop has no history cost and therefore does not converge --
    # it trades the same nets back and forth. Measured end to end:
    #     limit 4 -> 21 of 39      limit 8 -> 17      limit 25 -> 19
    # and the last of those took 789 rip-ups and twenty minutes. Fixing this
    # properly means negotiated congestion (PathFinder): route with a real cost
    # function, raise the cost of over-used cells, re-route everything, repeat.
    # That needs a cost-based search in place of Maze.path's breadth-first one.
    RIP_LIMIT = int(os.environ.get("RIP_LIMIT", "4"))
    ROUNDS = int(os.environ.get("ROUNDS", "6"))

    # ONE base grid per layer, with the whole group left out, cloned per attempt.
    # Rip-up means removing copper and a grid can only have copper punched in, so
    # the base has to exclude everything rippable from the start.
    # L1 IS A THIRD OPTION. It looks unavailable because the escape owns the top
    # layer, but stage 3 ENDS at the ring vias -- west of x 39.24 there is no
    # escape copper at all, only the GND pour and the top-side parts, and the
    # ring via is a through hole so a net can simply start there on L1 instead.
    # It reaches U3 the same way an L3 route does, through the fan-out via.
    # L1 IS NOT IN THIS LIST. Stage 3 ends at the ring vias, so west of x 39.24
    # the top layer looks free -- but a bus net's OWN escape fan is on L1, 339
    # wires across the group, and the base grid below deliberately hides the
    # whole group so that rip-up can add members back one at a time. On L3 and
    # L16 that hides only 39 vias, which are added back cheaply. On L1 it hides
    # the escape itself, and the router drove straight through it: 133 clearance
    # violations, "A0 vs D1 wire", A0 being a net that never routed at all --
    # what D1 hit was A0's escape. Routing the bus on L1 also carved that pour
    # from 93.4% to 71.5%. Both reasons point the same way.
    base_obst = dict((L, G.obstacles(b, GROUP, int(L))) for L in LAYERS)
    base_mz = dict((L, P.Maze(base_obst[L], bx, clr, W, STEP)) for L in LAYERS)
    # ...and one more whose free cells are where a THROUGH VIA may legally sit:
    # same obstacles taken on every layer at once, dilated by the via's radius
    # instead of the trace's.
    base_vobst = G.obstacles(b, GROUP, None)
    base_vmz = P.Maze(base_vobst, bx, clr, VIA_L, STEP)

    # the fan-out vias and stubs are placed once and never move, so they belong
    # in neither the base nor the rippable set -- they are added per attempt
    # every group member's PRE-EXISTING vias -- the escape's ring vias. The base
    # grid excludes the group, so without this a bus net would happily route
    # through another one's ring via.
    # ...AND THEIR PADS. Same hole, one step further: U3's pads belong to the
    # bus nets, so excluding the group from the base grid deleted all 39 of them
    # from L16 and routes ran straight over them -- "A12 wire vs SDRAM-CLK pad,
    # -0.0500". Anything of a group member's that is already on the board has to
    # be added back for every OTHER member: vias here, pads below.
    boardvias, boardpads, boardwires = {}, {}, {}
    # OVER THE PAIR AS WELL. `nets` has had the pair's two members removed by
    # now, so building these maps from it alone left fixed_for to KeyError on
    # boardvias['USB_D_P'] the moment it started consulting the pair's pads --
    # which killed the whole USB step, wrote nothing, and still printed the pair
    # routing happily on the line above.
    for net in list(nets) + sorted(pairplan):
        m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net), b, re.S)
        boardvias[net] = [(vx, vy, vd / 2.0)
                          for vx, vy, vd in G.vias(m.group(1))] if m else []
        pr = collections.defaultdict(list)
        for rec in E.board_copper(b, skip=()):
            onet, x, y, hx, hy, side = rec[:6]
            if onet != net:
                continue
            for L in LAYERS:
                if side == 0 or side == int(L):
                    pr[L].append((x, y, hx, hy, 0.0))
        boardpads[net] = dict((L, G.as_circles(pr[L])) for L in LAYERS)
        # AND THE WIRES ALREADY ON THE BOARD FOR THIS NET. base_obst excludes
        # the whole group, so a group-mate's existing copper is invisible while
        # we route -- and after escape_qfn.py there IS such copper: an 0.20 mm
        # stub from every U2 signal pad to its ring via. TCK and TDO were routed
        # straight down PROG#'s stub, which check_board caught at exactly
        # -0.1500 = 0.10/2 + 0.20/2, two centres on one line. Pads and vias were
        # added back here; wires never were.
        bw = collections.defaultdict(list)
        if m:
            for q in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)"'
                                 r' x2="([-\d.]+)" y2="([-\d.]+)"'
                                 r' width="([\d.]+)" layer="(\d+)"', m.group(1)):
                a = (float(q.group(1)), float(q.group(2)))
                c = (float(q.group(3)), float(q.group(4)))
                bw[q.group(6)].append((a, c, float(q.group(5)) / 2.0))
        boardwires[net] = bw
        allp = [(x, y, hx, hy, 0.0) for rec in E.board_copper(b, skip=())
                for onet, x, y, hx, hy, side in [rec[:6]] if onet == net]
        boardpads[net][None] = G.as_circles(allp)

    # ---- TERMINALS, GENERALLY.
    # The old model was "one escape terminal, one far pad", which is what the
    # SDRAM bus and the X2 header look like. It is not what a board looks like.
    # In the FT2232/USB group SIX of thirteen nets never touch U1 at all -- they
    # are U2 to a passive -- so they have no escape terminal and could not route
    # at all; and FT-VCORE has six pads, FT-VPHY and FT-VPLL three, which need a
    # tree rather than a path. So: the terminals of a net are its escape (if it
    # has one) plus every one of its pads, and a pad that is not on the layer
    # being routed gets a via beside it and a stub on its own surface.
    _tcache = {}
    _viacache = {}      # (net, pad) -> its fan-out via, decided once
    VIAPOOL = []        # every fan-out via decided so far, as an obstacle
    _stubcache = {}     # net -> its pad-to-via stubs, for other nets to avoid
    # THE PAIR IS NOT ON THE BOARD YET. terms_for builds its fan-out vias and
    # stubs from copper_model, which reads the board file, and the pair lives
    # only in pairplan until the writer runs. So FT-VCORE laid a stub straight
    # down USB_D_N at -0.1250 -- two centrelines on top of each other -- and put
    # a via 0.0522 from the crossover's. Hand it the pair's copper explicitly.
    PAIROBST = ([(x, y, VIA_L / 2)
                 for _n, (vv, _ss) in pairplan.items() for x, y in vv]
                + [q for _n, (_vv, ss) in pairplan.items()
                   for u, c, _sl in ss for q in G.sample(u, c, PAIR_W / 2)])

    def terms_for(net, lay, placed):
        key = (net, lay)
        if key in _tcache:
            return _tcache[key]
        t, vias, stubs = [], [], []
        if START.get(net) and lay in SLAY.get(net, tuple(LAYERS)):
            t.append(START[net])
        allm = copper_model(b, net, None)
        surfm = dict((sd, copper_model(b, net, sd)) for sd in (1, 16))
        for px, py, sd in P.pads_of(b, net, skip=("U1",)):
            if sd == 0 or str(sd) == lay:
                t.append((px, py))
                continue
            side = 16 if sd == 16 else 1
            # AN ESCAPE VIA MAY ALREADY BE THERE. escape_qfn.py fans U2's twenty
            # signal pads out to a planned two-ring stagger before any routing
            # starts, and a via that already exists is better than one invented
            # here: it was placed with all twenty decided together, and it is
            # board copper the other nets' obstacle models can already see.
            ev = min((q for q in boardvias[net]
                      if math.hypot(q[0] - px, q[1] - py) < QFN_NEAR),
                     key=lambda q: math.hypot(q[0] - px, q[1] - py), default=None)
            if ev is not None:
                t.append((ev[0], ev[1]))
                continue
            # ONE VIA PER PAD, NOT PER LAYER, and every net's visible to the
            # next. place_via works off the pad's OWN side -- allm and
            # surfm[side] -- so the position does not depend on `lay` at all, and
            # caching it per (net, lay) invented a separate via for every layer
            # the net might route on. That is what made the eager version so
            # costly: it reserved a via per net PER LAYER, including layers the
            # net never used, and USB fell 13 to 11. Keyed by pad, each net has
            # one, VIAPOOL carries them all, and TDO stops laying its stub
            # 0.0744 mm from TMS's via because it can finally see it.
            pk = (net, round(px, 3), round(py, 3))
            if pk in _viacache:
                v = _viacache[pk]
            else:
                v = place_via(px, py, allm, surfm[side], clr, bx,
                              placed + PAIROBST + VIAPOOL
                              + [(a, c, VIA_L / 2) for a, c in vias],
                              hint.get((round(px, 3), round(py, 3))))
                _viacache[pk] = v
                if v is not None:
                    VIAPOOL.append((v[0], v[1], VIA_L / 2))
                    _stubcache.setdefault(net, []).append(((px, py), v, str(side)))
            if v is None:
                _tcache[key] = None
                return None
            t.append(v)
            vias.append(v)
            stubs.append(((px, py), v, str(side)))
        out = (t, vias, stubs) if len(t) >= 2 else None
        _tcache[key] = out
        return out

    def fixed_for(net, lay):
        out = [(x, y, VIA_L / 2) for n2, r in allvias.items() if n2 != net
               for x, y in r[0]]
        # INCLUDING THE PAIR. Its two members are taken OUT of `nets` when
        # pairplan is built, so iterating `nets` here made their PADS invisible
        # to every other net in the group: FT-VPLL was routed 0.188 mm INTO the
        # USB_D_P pad. The pair's segments were already added below; its pads
        # were not, and a pad is the part that cannot move out of the way.
        for n2 in list(nets) + [q for q in pairplan if q != net]:
            if n2 != net:
                out += boardvias[n2]
                out += boardpads[n2][lay]
                # THE VIAS THIS RUN IS ABOUT TO PLACE. boardvias is what the
                # board file already held; the general terminal model invents a
                # fan-out via per off-layer pad while we route, and those were
                # in nobody's obstacle model. UART_FT_DTR#'s L4 route came out
                # 0.0682 mm inside UART_FT_RXD's new via -- a short. Taken over
                # every layer, not just `lay`, because a via is copper on all of
                # them and n2 may not end up routed on the layer we are asking
                # about. collides() is no help here: it only runs when attempt()
                # has already FAILED, and this attempt succeeded.
                for a2, c2, r2 in boardwires[n2].get(lay, ()):
                    out += G.sample(a2, c2, r2)
                # READ WHAT HAS BEEN DECIDED, do not force a decision. Calling
                # terms_for for every other net and every layer here is what made
                # the via pool eager: it invented a fan-out via for nets that go
                # on to fail, and for layers they never route on, and then held
                # the space. microSD went 2 to 0 that way. The vias that exist
                # are in _viacache; a net that has not been reached yet has none,
                # and will see THIS net's when its turn comes.
                for (vn, _px, _py), vv in _viacache.items():
                    if vn == n2 and vv is not None:
                        out.append((vv[0], vv[1], VIA_L / 2))
                for u, v2, sl in _stubcache.get(n2, ()):
                    if sl == lay:
                        out += G.sample(u, v2, STUB_W / 2)
        # a pair routed above is finished copper, not a rival to negotiate with
        for _n, (_v, psegs) in pairplan.items():
            # AND THE PAIR'S OWN VIAS. _v was being ignored here, which was
            # harmless while a pair never placed any and wrong the moment the
            # crossover did: those two vias are created during this run, so they
            # are in no board-read model, and FT-VPLL was routed 0.188 mm into
            # one. A via is copper on every layer, so no `sl` test.
            out += [(x, y, VIA_L / 2) for x, y in _v]
            for u, c, sl in psegs:
                if sl == lay:
                    out += G.sample(u, c, PAIR_W / 2)
        if lay == PADLAY:
            keep = set((q[0], q[1]) for q in allvias[net][1])
            for u, v, l in allstubs:
                if l == PADLAY and (u, v) not in keep:
                    out += G.sample(u, v, STUB_W / 2)
        return out

    # ---- every via first, then every trace (power.py's lesson: a net routed
    # before the next one's vias exist runs straight over them)
    allvias, allstubs = {}, []
    for net in nets:
        allm = copper_model(b, net, None)
        surfm = {sd: copper_model(b, net, sd) for sd in (1, 16)}
        placed = [(x, y, VIA_L / 2) for r in allvias.values() for x, y in r[0]]
        vias, stubs, miss = [], [], []
        # A NET ROUTED ON L16 NEEDS NO FAN-OUT VIA -- U3's pads are already on
        # L16, so it connects to the pad directly. Placing one for every net
        # regardless put 39 vias on the board when only the L3 nets use one, and
        # the other 32 were pure obstacle: they blocked the very layer the rest
        # were trying to cross. Place them where they will actually be used.
        #
        # With SPLITVIA none are pre-placed at all: the two-layer router picks
        # its own via position per net, so a pre-placed one would be 39 pieces
        # of pure obstacle serving nothing.
        if SPLITVIA or pref[net] != LAYER:
            allvias[net] = ([], [], [])
            continue
        for px, py, side in P.pads_of(b, net, skip=("U1",)):
            sd = 16 if side == 16 else 1
            # A STUB HAS TO CLEAR THE OTHER STUBS. They are all placed before
            # anything is routed, and this pass used to check each one against
            # board copper only -- so two fan-out stubs on neighbouring pads
            # could be laid across each other and nothing here would object.
            sm = (surfm[sd][0], surfm[sd][1],
                  surfm[sd][2] + [(a, c, STUB_W / 2) for a, c, l in allstubs
                                  if l == str(sd)])
            v = place_via(px, py, allm, sm, clr, bx,
                          placed + [(a, c, VIA_L / 2) for a, c in vias],
                          hint.get((round(px, 3), round(py, 3))))
            if v is None:
                miss.append((px, py))
                continue
            vias.append(v)
            stubs.append(((px, py), v, str(sd)))
            allstubs.append(((px, py), v, str(sd)))
        allvias[net] = (vias, stubs, miss)
    nmiss = sum(len(v[2]) for v in allvias.values())
    print("   %d via(s) placed beside a pad, %d pad(s) could not take one"
          % (sum(len(v[0]) for v in allvias.values()), nmiss))

    # ---- route, in an order that lets the fan nest rather than cross
    def key(net):
        """shortest first, so the fan nests instead of walling itself off.

        Every one of these is a ring via just outside U1 running to a pad on U3,
        and they all want the same lane -- the first eight routed independently
        all chose y = 5.4. Laid in ring order, the first trace runs from x 40 to
        x 23.5 along that lane and separates every remaining ring via (y ~ 5.0)
        from every remaining target (y >= 6.5). Five or six get through and the
        rest are walled off; that was the 10-of-39 that four other fixes did not
        move.

        Ring order and target order happen to be monotone in x, so the fan can
        nest. Route the SHORTEST first and it does: the short trace hugs the
        package, the next one passes underneath it and surfaces further west,
        and each longer trace nests outside the last. power.py sorts its MST
        edges longest-first, which is right for a spanning tree and wrong here.
        """
        _o, mine = P.blockers(b, net)
        t = [(x, y) for x, y, r in mine]
        v = allvias[net][0][0] if allvias[net][0] else None
        if not t or v is None:
            return (9, 9e9, 0.0)
        d = math.hypot(v[0] - t[0][0], v[1] - t[0][1])
        # ORDER. "len" is shortest-first, which nests a fan that all wants the
        # same lane. "tx" walks U3's pad row instead -- river order, which is
        # what this actually is: a comb of targets fed from a ring.
        pads = P.pads_of(b, net, skip=("U1",))
        tx = pads[0][0] if pads else 0.0
        half = 0 if (pads and pads[0][1] < 11.5) else 1
        if ORDER == "tx":
            return (0 if net in HARD else 1, half, tx)
        if ORDER == "-tx":
            return (0 if net in HARD else 1, half, -tx)
        return (0 if net in HARD else 1, d, 0.0)

    # x-range to blank and the y ceiling of the strip. West of BODY[0] so the
    # ring-via end is untouched; below BODY[2] so the inward fan-out ranks and
    # everything above them stay reachable.
    BODY = (17.0, 37.0, float(os.environ.get("BODY_Y", "5.6")),
            float(os.environ.get("BODY_Y_TOP", "19.0")))
    # OFF BY DEFAULT, and the reason is worth keeping. Pushing half the
    # bottom-half nets over U3's body instead of along the strip below it looked
    # like the breakthrough of this session -- 20 nets to 26. It was not: the
    # base grid was hiding the group's own pads and vias at the time, so those
    # routes were running through copper that is really there. With the obstacle
    # set correct the same setting gives 10 of 39 against 21 with it off,
    # because the fan-out vias are OUTWARD, which puts every target inside the
    # very band being blanked. It is only coherent with OUTWARD=0, and there it
    # still measures worse (12). Kept, switchable, and not used.
    FRAC = float(os.environ.get("BODY_FRAC", "0"))
    FRAC_T = float(os.environ.get("BODY_FRAC_TOP", "0"))
    via_body = {}
    for hname, fr in (("bot", FRAC), ("top", FRAC_T)):
        row = sorted([n for n in nets if half[n] == hname],
                     key=lambda n: P.pads_of(b, n, skip=("U1",))[0][0])
        every = max(1, int(round(1.0 / fr))) if fr else 0
        for k, n in enumerate(row):
            via_body[n] = bool(fr) and (k % every == 0)
        print("   %s half: %d of %d nets sent over U3's body, not along the strip"
              % (hname, sum(1 for n in row if via_body[n]), len(row)))

    plan = {}
    ripped = collections.Counter()
    geom_stuck = set()

    def attempt(net, lay, rivals):
        """route `net` on `lay` against the board plus `rivals`' copper"""
        tv = terms_for(net, lay, [])
        if tv is None:
            return None
        term, vias, stubs = tv
        extra = fixed_for(net, lay)
        for n2 in rivals:
            v = plan.get(n2)
            if not v:
                continue
            for u, c, sl in v[1]:
                if sl == lay:
                    extra += G.sample(u, c, W / 2)
            extra += [(x, y, VIA_L / 2) for x, y in v[0]]
        mz = base_mz[lay].clone()
        mz.block(extra, clr, W)
        # PUSH SOME NETS OFF THE STRIP. Bottom-half nets all want the same thin
        # lane below U3 and fill it; the open ground under U3's body is bigger
        # and goes unused because it is the longer way round and the maze is
        # breadth-first. Blanking the strip west of the entry for the nets
        # marked `via_body` forces them over the top of the fan-out ranks.
        if lay != PADLAY and via_body.get(net):
            if half[net] == "bot":
                mz.block_box(BODY[0], 0.0, BODY[1], BODY[2])
            else:
                mz.block_box(BODY[0], BODY[3], BODY[1], 99.0)
        obst = base_obst[lay] + extra
        # ONE PATH: a spanning tree over whatever terminals this net has on
        # this layer. Two of them is the old escape-to-pad case; six is
        # FT-VCORE. The `lay` on each segment is the layer it was actually
        # routed on -- labelling it with the pad layer instead once stacked 25
        # L16 routes onto L3, which check_board found as 2027 violations at
        # exactly -0.1000, two 0.10 traces sharing a centreline.
        # GROW THE TREE, do not route each MST edge on its own. Routing edge
        # (A,B) and edge (A,C) independently sends both down whatever corridor
        # leaves A, and the shared part gets WRITTEN TWICE: UART_FT_RXD came out
        # 235.7 mm on L3 as 46 segments of which the first 20 were the route and
        # the rest were the same copper again. A 3-terminal net on a 70 x 25 mm
        # board. Each new terminal is joined to the NEAREST POINT ALREADY IN THE
        # TREE instead, which is what a hand router does and what makes the
        # result a tree rather than a bundle of overlapping paths.
        segs, tree = [], [term[0]]
        left = list(term[1:])
        while left:
            best = min(((math.hypot(t[0] - q[0], t[1] - q[1]), ti, q)
                        for ti, t in enumerate(left) for q in tree),
                       key=lambda z: z[0])
            _d, ti, anchor = best
            tgt = left.pop(ti)
            p = mz.path(anchor, tgt)
            if p is None:
                return None
            p = straighten(p, obst, clr, W)
            segs += list(zip(p, p[1:]))
            tree += list(p)
        seen, uniq = set(), []
        for u, v in segs:
            k = (u, v) if u <= v else (v, u)
            if k not in seen:
                seen.add(k)
                uniq.append((u, v))
        segs = uniq
        return (vias, [(a, c, lay) for a, c in segs]
                + [(u, v2, sl) for u, v2, sl in stubs])

    def rival_copper(rivals, lay):
        """the group's currently-placed copper on `lay` (lay None = every layer)"""
        out = []
        for n2 in rivals:
            v = plan.get(n2)
            if not v:
                continue
            for u, c, sl in v[1]:
                if lay is None or sl == lay:
                    out += G.sample(u, c, W / 2)
            out += [(x, y, VIA_L / 2) for x, y in v[0]]
        return out

    def attempt_split(net, rivals):
        """L3 as far as it reaches, the via wherever that is, L16 to the pad.

        THE FAN-OUT VIA DOES NOT HAVE TO BE NEXT TO THE PAD. Placing it there
        first and then demanding L3 reach it is what caps L3 at 7 of 39 nets: a
        route has to arrive at one specific point inside a field of 38 other
        vias on a 0.80 mm pad pitch, which is the hardest possible target. But
        the via only has to be somewhere BOTH layers can reach -- L3 from the
        escape ring, L16 from the pad -- and L16 near U3 is comparatively open,
        because a trace there can run between the pad rows.

        So flood both layers, one from each end, and put the via at the cell
        minimising the sum. That is the shortest two-layer route there is for
        this net, and the via lands wherever it is cheapest rather than where a
        rule of thumb said.
        """
        pads = P.pads_of(b, net, skip=("U1",))
        start = START.get(net)
        if not start or not pads:
            return None
        pad = (pads[0][0], pads[0][1])
        e3 = fixed_for(net, LAYER) + rival_copper(rivals, LAYER)
        e16 = fixed_for(net, PADLAY) + rival_copper(rivals, PADLAY)
        ev = fixed_for(net, None) + rival_copper(rivals, None)
        mz3 = base_mz[LAYER].clone(); mz3.block(e3, clr, W)
        mz16 = base_mz[PADLAY].clone(); mz16.block(e16, clr, W)
        mzv = base_vmz.clone(); mzv.block(ev, clr, VIA_L)
        d3, p3 = mz3.bfs(start)
        if d3 is None:
            return None
        d16, p16 = mz16.bfs(pad)
        if d16 is None:
            return None
        fr, best = mzv.free, None
        for c in range(len(d3)):
            if d3[c] < 0 or d16[c] < 0 or not fr[c]:
                continue
            t = d3[c] + d16[c]
            if best is None or t < best[0]:
                best = (t, c)
        if best is None:
            return None
        c = best[1]
        vxy = mz3.xy(c)
        q3 = straighten(mz3.walk(p3, c, start, vxy), base_obst[LAYER] + e3, clr, W)
        q16 = straighten(mz16.walk(p16, c, pad, vxy), base_obst[PADLAY] + e16, clr, W)
        return ([vxy],
                [(a, cc, LAYER) for a, cc in zip(q3, q3[1:])]
                + [(a, cc, PADLAY) for a, cc in zip(q16, q16[1:])])

    def collides(route, net):
        """which placed nets does this route's copper run into"""
        hit = set()
        pts = collections.defaultdict(list)
        for u, c, sl in route[1]:
            pts[sl] += G.sample(u, c, 0.0, 0.2)
        # A VIA IS COPPER ON EVERY LAYER, and this loop used to compare wire
        # against wire only -- vias were invisible to it. The general terminal
        # model places a fan-out via per off-layer pad DURING the run, so those
        # vias are in no other net's obstacle model either, and UART_FT_DTR#'s
        # L4 route came out 0.0682 mm INSIDE UART_FT_RXD's via. That is a short
        # between two nets, not a margin that wants widening.
        mine_v = list(route[0])
        need_wv = STUB_W / 2.0 + VIA_L / 2.0 + clr   # a wire against a via
        need_vv = VIA_L + clr                        # a via against a via
        for n2, v in plan.items():
            if n2 == net or not v[1]:
                continue
            bad = False
            for u, c, sl in v[1]:
                if any(E.seg_pt(u, c, (px, py)) < W + clr - 1e-9
                       for px, py, _r in pts.get(sl, ())):
                    bad = True
                    break
                if any(E.seg_pt(u, c, q) < need_wv - 1e-9 for q in mine_v):
                    bad = True
                    break
            for q in v[0] if not bad else ():
                if any(E.seg_pt(u, c, q) < need_wv - 1e-9
                       for u, c, _sl in route[1]):
                    bad = True
                    break
                if any(math.hypot(q[0] - p[0], q[1] - p[1]) < need_vv - 1e-9
                       for p in mine_v):
                    bad = True
                    break
            if bad:
                hit.add(n2)
        # SORTED. Iterating a set of strings takes Python's per-process hash
        # randomisation with it, and the victim order decides what gets ripped:
        # two identical runs gave 23 and 22 of 39. A board generator has to be
        # reproducible.
        return sorted(hit)

    def validate_plan():
        """rip up whatever conflicts, once the plan has stopped moving

        THE ONLY CHECK MADE AGAINST THE FINISHED SET. Both routers check each
        route against the plan AS IT STANDS WHEN THAT ROUTE IS MADE, which is
        right when it is made and stops being right immediately -- the plan does
        not stand still. Greedy rip-up removes members and adds others, its
        best-round snapshot can restore a net that was placed before the net it
        now sits on, PathFinder's straightening moves chords after its own
        verify pass has looked at them, and BOTH branches merge pairplan in at
        the end having routed it against none of the group. Two shorts came out
        of that gap: PMOD-4's L3 trace through PMOD-7's via at -0.16 mm, and
        D10 against SDRAM-CLK at -0.1000. check_board.py found both; nothing in
        here could.

        The clearance test was never the problem -- collides() is if anything
        stricter than check_board -- so this reuses it unchanged and only
        changes WHEN it is applied.

        RIP UP, DO NOT RE-ROUTE. Re-routing here would be checked against a
        plan this loop is still changing, which is the original bug in a
        different hat. An airwire says "this run could not place it", which is
        true and is what the caller needs to know. Worst offender first, so one
        selfish route cannot evict several good ones; sorted(), because the
        victim order decides the result and a board generator is reproducible
        or it is nothing.

        IT RIPS SLIGHTLY MORE THAN check_board WOULD. collides() measures a
        wire against a via at STUB_W/2 + VIA_L/2 + clr because route[1] holds
        traces AND fan-out stubs and carries no width per segment, so the wider
        of the two has to be assumed: 0.34 mm where a 0.10 trace really owes
        0.29. EE-CLK is dropped by that margin and check_board passes it. That
        is the right way round for a guard -- it can cost a net, it cannot let a
        short through -- but it is the first thing to look at if a net that
        should route keeps coming out as an airwire.
        """
        dropped = []
        while True:
            hits = dict((n, collides(v, n)) for n, v in plan.items() if v[1])
            hits = dict((n, h) for n, h in hits.items() if h)
            if not hits:
                break
            victim = max(sorted(hits), key=lambda n: len(hits[n]))
            # A PAIR IS ONE OBJECT AND COMES OUT AS ONE. Ripping half of it
            # leaves one conductor routed and the other an airwire, which is
            # worse than neither: the survivor is a single-ended trace with a
            # differential net's name on it, it carries no return, and nothing
            # downstream would ever flag it. This nearly happened -- USB_D_N was
            # ripped on its own while USB_D_P stayed, over an overlap that was
            # really a via-ownership bug -- and the fix for that bug removed the
            # symptom without removing the hazard.
            drop = {victim}
            partner = G.find_pairs(set(plan))
            if victim in partner:
                drop.add(partner[victim][0])
            for n in sorted(drop):
                if plan.get(n) and plan[n][1]:
                    plan[n] = ([], [])
                    dropped.append(n)
        if dropped:
            print("   final validation: %d net(s) ripped up against the finished"
                  " plan: %s" % (len(dropped), ", ".join(dropped)))
        return dropped

    if ROUTER == "pathfinder":
        import pathfinder as PF
        terms, own, slay = {}, {}, {}
        for net in nets:
            pads = P.pads_of(b, net, skip=("U1",))
            if not START.get(net) or not pads:
                continue
            terms[net] = (START[net], (pads[0][0], pads[0][1]))
            slay[net] = SLAY[net]
            own[net] = boardvias[net] + boardpads[net][None]
        run = [n for n in sorted(nets, key=key) if n in terms]
        print("   PathFinder over %d nets, %s" % (len(run), " + L".join([""] + LAYERS)[3:]))
        got, missed = PF.route_group(b, run, terms, own, bx, clr, W, tuple(LAYERS),
                                     thru=THRU, slay=slay)
        # STRAIGHTEN AFTER, NOT DURING. The grid paths are legal but they are
        # 4-connected staircases; pulling them straight has to respect the other
        # nets' final copper as well as the board's, or it undoes the legality
        # the router just established.
        plan, rawseg = {}, {}
        for net, (vias, segs) in got.items():
            plan[net] = (vias, segs)
            rawseg[net] = list(segs)
        for net in list(plan):
            vias, segs = plan[net]
            out = []
            for lay in LAYERS:
                pts = []
                for a, c, sl in segs:
                    if sl != lay:
                        continue
                    if not pts:
                        pts = [a, c]
                    elif pts[-1] == a:
                        pts.append(c)
                    else:
                        out += [(u, v, lay) for u, v in zip(pts, pts[1:])]
                        pts = [a, c]
                if pts:
                    # ...AND THE OTHER NETS' VIAS. A via is copper on every
                    # layer, so it constrains a chord on both of them; leaving
                    # them out let the straightener pull traces across vias this
                    # very run had placed. Three violations, all a few microns,
                    # which is exactly what a missing obstacle looks like once
                    # everything else is right.
                    obst = base_obst[lay] + fixed_for(net, lay) + [
                        q for n2, (v2, s2) in plan.items() if n2 != net
                        for u, c2, sl in s2 if sl == lay
                        for q in G.sample(u, c2, W / 2)] + [
                        (vx, vy, VIA_L / 2) for n2, (v2, s2) in plan.items()
                        if n2 != net for vx, vy in v2]
                    q = straighten(pts, obst, clr, W)
                    out += [(u, v, lay) for u, v in zip(q, q[1:])]
            plan[net] = (vias, out)

        # STRAIGHTENING IS VERIFIED, NOT TRUSTED. Each chord is checked against
        # the copper that exists when it is pulled, but the nets straightened
        # AFTER it then move, and the pair can end up closer than either check
        # saw. It showed as JA3 against JA4 at 0.0803 where 0.0900 was needed --
        # centrelines 0.1803 apart, which is a (3, 2) cell diagonal on a 0.05
        # grid. One pair, eight segments, and no amount of reasoning about the
        # order was going to make it safe. So measure the finished article and
        # put any net that fails back on its unstraightened path, which is legal
        # by construction because the congestion model produced it.
        raw = dict(rawseg)
        for _round in range(3):
            bad = set()
            items = list(plan.items())
            for i, (n1, (v1, s1)) in enumerate(items):
                for n2, (v2, s2) in items[i + 1:]:
                    if not s1 or not s2 or n1 in bad or n2 in bad:
                        continue
                    hit = False
                    for a, c, l1 in s1:
                        for u, q, l2 in s2:
                            if l1 != l2:
                                continue
                            if E.seg_seg(a, c, u, q) < W + clr - 1e-9:
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        bad.add(n2 if n2 in raw else n1)
            if not bad:
                break
            print("   straightening reverted on %d net(s): %s"
                  % (len(bad), ", ".join(sorted(bad))))
            for n in bad:
                if n in raw:
                    plan[n] = (plan[n][0], raw[n])
                    del raw[n]

        for net in nets:
            plan.setdefault(net, ([], []))
        plan.update(pairplan)
        # The revert loop above compares WIRE AGAINST WIRE ON ONE LAYER only --
        # vias are invisible to it -- and its remedy is to put a net back on its
        # unstraightened path, which does nothing at all once neither net still
        # has a raw path to go back to: `bad.add(...)` then `if n in raw` fails
        # and three rounds pass in silence. It also runs before pairplan is
        # merged. This catches what is left.
        validate_plan()
        done = sum(1 for v in plan.values() if v[1])
        ntot = len(nets) + len(pairplan)
        fail = ntot - done
        for net in sorted(nets):
            if not plan[net][1]:
                print("   **** %-10s no route" % net)
    else:
        order = sorted(nets, key=key)
        queue = list(order)
        # KEEP THE BEST PASS. Naive rip-up does not converge -- it has no history
        # cost, so it will happily trade two nets back and forth and can finish
        # WORSE than the greedy pass it started from (18 of 39 against 20, after
        # 103 rip-ups). Snapshot after every round and return the best seen, so the
        # loop can only ever help.
        best = (0, {})
        for rnd in range(ROUNDS):
            stuck = []
            while queue:
                net = queue.pop(0)
                if plan.get(net) and plan[net][1]:
                    continue
                rivals = [n for n in plan if n != net]
                # a through-hole far end needs no layer change, so there is
                # nothing for the two-layer split router to decide
                got = attempt_split(net, rivals) if (SPLITVIA and not THRU) else None
                if not got:
                    for lay in LAYERS:
                        got = attempt(net, lay, rivals)
                        if got:
                            break
                if got:
                    plan[net] = got
                    continue
                # BLOCKED. Route it as though the board were empty and see who is
                # in the way -- but take the LEAST DISRUPTIVE of those routes, not
                # the first one found. Taking the first is what made rip-up finish
                # below the greedy pass it started from: an empty-board path is the
                # most selfish path there is, and on the wrong layer it evicted a
                # dozen nets that then had nowhere to go. 107 rip-ups, 23 routed.
                cands = []
                if SPLITVIA and not THRU:
                    f = attempt_split(net, [])
                    if f:
                        cands.append((len(collides(f, net)), -1, f))
                for lay in LAYERS:
                    f = attempt(net, lay, [])
                    if f:
                        cands.append((len(collides(f, net)), LAYERS.index(lay), f))
                if not cands:
                    # cannot route even on an EMPTY board: geometry, not congestion,
                    # and no amount of rip-up or reordering will reach it
                    geom_stuck.add(net)
                    stuck.append(net)
                    continue
                cands.sort(key=lambda q: (q[0], q[1]))
                free = cands[0][2]
                victims = [v for v in collides(free, net) if ripped[v] < RIP_LIMIT]
                if not victims or len(victims) != cands[0][0]:
                    stuck.append(net)           # someone in the way is un-rippable
                    continue
                for v in victims:
                    ripped[v] += 1
                    plan.pop(v, None)
                plan[net] = free
                queue.extend(v for v in victims if v not in queue)
            got = sum(1 for v in plan.values() if v[1])
            if got > best[0]:
                best = (got, dict(plan))
            if not stuck:
                break
            print("   round %d: %d routed, %d still stuck"
                  % (rnd + 1, got, len(stuck)))
            queue = stuck + [n for n in order if not (plan.get(n) and plan[n][1])
                             and n not in stuck]
            if queue == stuck and rnd:
                break

        if best[0] > sum(1 for v in plan.values() if v[1]):
            print("   keeping the best round (%d) over the last (%d)"
                  % (best[0], sum(1 for v in plan.values() if v[1])))
            plan = best[1]
        for net in nets:
            plan.setdefault(net, ([], []))
        plan.update(pairplan)

        validate_plan()
        done = sum(1 for v in plan.values() if v[1])
        ntot = len(nets) + len(pairplan)
        fail = ntot - done
        for net in sorted(nets):
            if not plan[net][1]:
                print("   **** %-10s no route on L%s or L16 -- nothing written"
                      % (net, LAYER))
        if geom_stuck:
            print("   %d net(s) cannot route even against an empty board -- that is"
                  " geometry, not congestion:" % len(geom_stuck))
            print("      %s" % ", ".join(sorted(geom_stuck)))
        if ripped:
            print("   rip-ups: %d over %d net(s), most-ripped %s"
                  % (sum(ripped.values()), len(ripped),
                     ", ".join("%s x%d" % q for q in ripped.most_common(3))))

    tot = sum(math.hypot(c[0] - a[0], c[1] - a[1])
              for v in plan.values() for a, c, _l in v[1])
    lens = sorted(sum(math.hypot(c[0] - a[0], c[1] - a[1]) for a, c, _l in v[1])
                  for v in plan.values() if v[1])
    byl = collections.Counter(sl for v in plan.values() for _a, _c, sl in v[1])
    print("")
    print("%d of %d nets routed, %d not   (%s)"
          % (done, ntot, fail,
             ", ".join("L%s %d seg" % (L, byl[L]) for L in sorted(byl))))
    if lens:
        print("   %.1f mm of %.2f mm trace" % (tot, W))
        print("   per net: shortest %.1f, median %.1f, longest %.1f mm"
              % (lens[0], lens[len(lens) // 2], lens[-1]))
        print("   skew (longest - shortest) %.1f mm" % (lens[-1] - lens[0]))

    if not APPLY:
        print("\nreport only -- re-run with --apply to write it into the board")
        return 0
    # WHAT PARTIAL MEANS HERE. The all-or-nothing rule is per NET and it still
    # holds: a net whose route did not close is written as nothing at all,
    # because half a trace looks routed and the missing half is invisible.
    #
    # A net that DID close is finished copper, and there is no reason to discard
    # it because a different net failed. An unrouted net is not silent either --
    # it stays an airwire in Eagle and check_board counts its endpoints. So the
    # nets that closed get written, and the ones that did not are named here.
    if fail:
        print("\n%d NET(S) STILL UNROUTED, left as airwires: %s"
              % (fail, ", ".join(sorted(n for n in nets if not plan[n][1]))))
    # EVERY NET WE PLANNED, NOT EVERY NET LEFT IN `nets`. The pair's two halves
    # are taken OUT of `nets` when pairplan is built and put back into `plan`, so
    # a writer that walks `nets` reports "chose L1, 29.3/29.3 mm, skew 1.300" and
    # then writes nothing at all. USB_D_P and USB_D_N carried no copper in any of
    # 7469e75, 3859abc or 59c79e6 -- three commits whose messages say the pair
    # was routed. The only time those nets got copper was a run where the pair
    # FAILED and both halves fell through to the single-ended router.
    written = list(nets) + sorted(pairplan)
    for net in written:
        m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net), b, re.S)
        if re.search(r'<wire [^>]*layer="%s"' % LAYER, m.group(1)):
            print("\nREFUSING TO APPLY: %s already carries L%s copper." % (net, LAYER))
            return 1

    stubset = set((u, v2, sl) for _n, r in allvias.items() for u, v2, sl in r[1])
    pairseg = set(q for _n, (_v, ps) in pairplan.items() for q in ps)
    g, out, nv, nw = E.g, b, 0, 0
    for net in written:
        vias, segs = plan[net]
        add = []
        for x, y in vias:
            add.append('<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>'
                       % (g(x), g(y), g(VIA_D), g(VIA_L)))
            nv += 1
        # EVERY SEGMENT CARRIES ITS OWN LAYER. It used to be one layer per net
        # plus a stub, and the stub loop rebound the variable holding it, which
        # silently wrote 25 L3 routes onto L16 -- 257 clearance violations, each
        # exactly -W, which is what two traces sharing a centreline measure.
        for a, c, slay in segs:
            if math.hypot(c[0] - a[0], c[1] - a[1]) < 1e-9:
                continue
            # A PAIR CONDUCTOR IS PAIR_W WIDE. It was being written at W: the
            # geometry was designed as 0.20 mm traces on a 0.20 mm gap and landed
            # as 0.10 on 0.30, which is not the impedance that was asked for.
            wd = (PAIR_W if (a, c, slay) in pairseg else
                  STUB_W if (a, c, slay) in stubset else W)
            add.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s"/>'
                       % (g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(wd), slay))
            nw += 1
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(net), out)
        out = out[:m.end()] + "".join(add) + out[m.end():]
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    io.open(BRD, "w", encoding="utf-8", newline="").write(out)
    print("\nwrote %d wires and %d vias into %s" % (nw, nv, BRD))
    return 0


if __name__ == "__main__":
    a = [q for q in sys.argv[1:] if not q.startswith("-")]
    sys.exit(main(a[0] if a else "sdram"))
