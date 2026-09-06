# -*- coding: utf-8 -*-
"""Draw the XC7A35T-CPG236 escape into zulu_a7.brd.

    python tools/escape.py            report only, writes nothing
    python tools/escape.py --apply    write the copper into the board

RUN IT AFTER make_board.py, NEVER BEFORE. make_board.py regenerates the board
from the schematic with empty <signals>; this pass adds copper to them. Running
make_board again throws the escape away, which is intended -- placement is the
source of truth and the escape is derived from it. Re-run this afterwards.

THE FIELD. 19 x 19 on 0.5 mm pitch, 238 balls. Three complete rings around a
three-cell EMPTY moat, then a 7 x 7 core with three balls missing at K9, K10,
K11:

    rings 0,1,2   192 balls   117 signal, 67 power/ground, 8 no-connect
    rings 3,4,5   empty       the moat, 2.00 mm wide, where the vias go
    rings 6,7,8    46 balls   all power or ground

WHY NO VIA GOES INSIDE THE BALL FIELD. At a 0.225 mm land the free circle at a
four-ball void is 0.4821 mm across, and 0.09 mm of clearance leaves 0.3021 for a
via land. The board's via land is 0.300. It "fits" by 0.0021 mm, which is not a
fit, it is a rounding error. So every via lands in the moat or outside the
package, and inside the field there is only L1 copper.

IT RUNS IN THREE STAGES, AND THE DOCSTRING USED TO CLAIM ONLY THE FIRST WAS
BUILT. All three are, and they close: 1297 wires and 157 vias go in, every one
clearing foreign copper by the full 0.090.

STAGE 1. Gang the power and ground balls.
113 of the 238 carry a plane net, and same-net neighbours do not each need their
own escape -- joined on L1 they need one between them. Three kinds of edge, all
at 0.225 mm, all verified against every other net's land before anything is
written:

    orthogonal   0.500 apart, nearest foreign ball 0.500 away
    diagonal     0.707 apart, the two flanking balls 0.354 away
    jump         1.000 apart THROUGH AN EMPTY GRID CELL

The jump is not a nicety. L11 is a GND ball at the dead centre of the core with
VCC1V0 left, VCC1V0 below, VCC3V3 right and nothing above, because K11 is one of
the three missing balls. Orthogonal and diagonal ganging both strand it, and a
ball at ring 8 with two populated rows around it has no other way out -- there is
no room for a via beside it and none inside its land. Jumping the empty K11 to
J11, which is GND, is the only thing that connects it. J10/L10 and J9/L9 get the
same treatment through K10 and K9.

STAGE 2, THE MOAT. 54 escapes leave the inner rings and the core and drop
through a via in the 2.00 mm moat, 0.3525 to 0.8125 mm in from the ball each
serves. Nothing goes inside the field, for the reason above.

STAGE 3, OUT OF THE PACKAGE. 103 escapes leave ring 0 and ring 1 outward and
drop on a fan-out ring at 7.260 mm half-width -- 103 vias at 0.390 pitch, which
needs 40.170 of the 58.080 mm available on that perimeter. That ring is why
make_board reserves the annulus it does, and why the decoupling had to move to
the bands above and below it.

WHAT IS NOT DONE HERE. Seven ganged components are STRANDED -- P2, B14, H18 and
V18 on GND, V6, V9 and V11 on VCC3V3. Ganging cannot reach a plane from them, so
they need a lane of their own like any signal, and this file does not draw one.
The 52 signals still carrying no copper are the rest of the routing job.
"""

import re, io, os, sys, math, collections, itertools

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
APPLY = "--apply" in sys.argv
SELECTED_NETS = {q.strip() for q in os.environ.get("ESCAPE_NETS", "").split(",")
                 if q.strip()}
BRD = os.path.join(ROOT, "zulu_a7.brd")
BGA = "XC7A35T-CPG236"
GANG_W = 0.225                      # gang trace width, same as the land
POWER = re.compile(r"^(GND|VCC|VDD|\+)", re.I)
MAX_IN = 0                          # ring-1 escapes allowed into the moat
CORNER_SP = 4.0                     # via spacing multiplier at a ring corner, see stage3()


def g(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def load(path):
    import geom as G

    b = open(path, encoding="utf-8").read()
    m = re.search(r'<element name="U1"[^>]*x="([-\d.]+)" y="([-\d.]+)"([^>]*)>', b)
    ox, oy = float(m.group(1)), float(m.group(2))
    rot = (re.search(r'rot="(M?R\d+)"', m.group(3)) or [None, "R0"])[1]
    assert rot == "R0", "U1 is %s; the escape assumes R0" % rot
    pk = re.search(
        r'<package name="%s"[^>]*>(.*?)</package>' % BGA, b, re.S
    ).group(1)
    pos, land = {}, None
    for mm in re.finditer(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)"', pk):
        pos[mm.group(1)] = (ox + float(mm.group(2)), oy + float(mm.group(3)))
        land = float(mm.group(4))
    net = {}
    for sm in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', b, re.S):
        for c in re.finditer(r'<contactref element="U1" pad="([^"]+)"/>', sm.group(2)):
            net[c.group(1)] = sm.group(1)
    clr = G.rule_mm(b, "mdWireWire")
    return b, pos, land, net, clr


def grid(pos):
    xs = sorted({round(p[0], 3) for p in pos.values()})
    ys = sorted({round(p[1], 3) for p in pos.values()})
    ci = {v: i for i, v in enumerate(xs)}
    ri = {v: i for i, v in enumerate(ys)}
    cell = {k: (ci[round(p[0], 3)], ri[round(p[1], 3)]) for k, p in pos.items()}
    n = max(len(xs), len(ys))
    at = {v: k for k, v in cell.items()}
    ring = {k: min(i, j, n - 1 - i, n - 1 - j) for k, (i, j) in cell.items()}
    return cell, at, ring, n


# --- geometry ---------------------------------------------------------------
def seg_pt(a, c, p):
    ax, ay = a; cx, cy = c; px, py = p
    dx, dy = cx - ax, cy - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg(a, c, p, q):
    def cr(o, x, y):
        return (x[0] - o[0]) * (y[1] - o[1]) - (x[1] - o[1]) * (y[0] - o[0])
    d1, d2, d3, d4 = cr(p, q, a), cr(p, q, c), cr(a, c, p), cr(a, c, q)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(seg_pt(a, c, p), seg_pt(a, c, q), seg_pt(p, q, a), seg_pt(p, q, c))


def seg_box(a, c, ox, oy, hx, hy):
    """shortest distance from segment a-c to the axis-aligned box at (ox, oy).

    Pads are RECTANGLES. The old code measured to the pad's centre and then
    subtracted hypot(hx, hy) -- the box's own diagonal -- which is only correct
    if the trace approaches along that diagonal and overstates the pad's reach
    everywhere else. On a 1.2 x 1.4 mm oscillator pad that is 0.922 against a
    true half-extent of 0.70, so the pad appeared 0.22 mm larger than it is in
    the direction that mattered. It cost the fan-out ring half a millimetre of
    radius: Q1's pads blocked h = 6.40 by 0.01 mm under the circle, and clear it
    by 0.21 under the box.

    Being wrong in the safe direction is still being wrong. It does not fail
    loudly, it just quietly withholds room and makes the next stage look harder
    than it is.
    """
    ax, ay = a[0] - ox, a[1] - oy                # box centred on the origin
    bx, by = c[0] - ox, c[1] - oy
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0                            # slab clip: do they touch at all
    for p, q, h in ((ax, dx, hx), (ay, dy, hy)):
        if abs(q) < 1e-12:
            if abs(p) > h:
                t0, t1 = 1.0, 0.0
                break
        else:
            lo, hi = (-h - p) / q, (h - p) / q
            if lo > hi:
                lo, hi = hi, lo
            t0, t1 = max(t0, lo), min(t1, hi)
    if t0 <= t1:
        return 0.0
    # Disjoint convex sets touch at a vertex of one: try both segment ends
    # against the box, and all four corners against the segment.
    def pt_box(px, py):
        return math.hypot(max(0.0, abs(px) - hx), max(0.0, abs(py) - hy))
    best = min(pt_box(ax, ay), pt_box(bx, by))
    for qx in (-hx, hx):
        for qy in (-hy, hy):
            best = min(best, seg_pt((ax, ay), (bx, by), (qx, qy)))
    return best


def box_ring(ox, oy, hx, hy, cx, cy):
    """(nearest, furthest) chebyshev radius of a box about a centre.

    The fan-out ring is a square, so "how far out is this pad" is a chebyshev
    question, and a box spans a RANGE of it.
    """
    ux, uy = abs(ox - cx), abs(oy - cy)
    near = max(max(0.0, ux - hx), max(0.0, uy - hy))
    return near, max(ux + hx, uy + hy)


def gang(pos, net, cell, at):
    """same-net components: orthogonal, then diagonal, then jumps over gaps"""
    pwr = [k for k in pos if k in net and POWER.match(net[k])]
    parent = {k: k for k in pwr}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, c):
        ra, rc = find(a), find(c)
        if ra == rc:
            return False
        parent[ra] = rc
        return True

    ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
    DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    edges, used_diag = [], set()
    for tag, kinds in (("orth", ORTH), ("diag", DIAG), ("jump", ORTH)):
        for k in sorted(pwr):
            i, j = cell[k]
            for di, dj in kinds:
                if tag == "jump":
                    # straight run of exactly one empty grid cell
                    if at.get((i + di, j + dj)) is not None:
                        continue
                    di, dj = di * 2, dj * 2
                o = at.get((i + di, j + dj))
                if not o or net.get(o) != net[k]:
                    continue
                if tag == "diag":
                    c = (min(i, i + di), min(j, j + dj))
                    if c in used_diag:
                        continue
                if union(k, o):
                    edges.append((k, o, tag))
                    if tag == "diag":
                        used_diag.add((min(i, i + di), min(j, j + dj)))
    comp = collections.defaultdict(list)
    for k in pwr:
        comp[find(k)].append(k)
    return pwr, edges, {r: sorted(v) for r, v in comp.items()}


def verify(edges, pos, net, land, clr):
    """no gang trace may come within clearance of another net's land or trace"""
    bad = []
    need_pad = land / 2 + GANG_W / 2 + clr
    need_seg = GANG_W + clr
    for a, c, tag in edges:
        for k, p in pos.items():
            if k in (a, c) or net.get(k) == net[a]:
                continue
            d = seg_pt(pos[a], pos[c], p)
            if d < need_pad - 1e-9:
                bad.append("%s-%s (%s) is %.4f from %s land, needs %.4f"
                           % (a, c, tag, d, k, need_pad))
    for x in range(len(edges)):
        for y in range(x + 1, len(edges)):
            a, c, _ = edges[x]
            p, q, _ = edges[y]
            if net[a] == net[p]:
                continue
            d = seg_seg(pos[a], pos[c], pos[p], pos[q])
            if d < need_seg - 1e-9:
                bad.append("%s-%s and %s-%s are %.4f apart, need %.4f" % (a, c, p, q, d, need_seg))
    return bad


def walk(at, n, r):
    """the cells of ring r, once round, so consecutive pairs are its gaps"""
    lo, hi = r, n - 1 - r
    return ([(i, lo) for i in range(lo, hi + 1)] +
            [(hi, j) for j in range(lo + 1, hi + 1)] +
            [(i, hi) for i in range(hi - 1, lo - 1, -1)] +
            [(lo, j) for j in range(hi - 1, lo, -1)])


def lanes(pos, net, cell, at, ring, n, edges, stranded):
    """Can every enclosed ball get out, and through which gap?

    Ring 0 escapes straight outward and ring 2 straight inward into the moat;
    neither crosses anything. Ring 1 is the only enclosed row, and it has two
    ways out: inward between two ring-2 balls, or outward between two ring-0
    balls. Inward is preferred -- the moat is empty and has via room, where
    outside the package a ring-1 trace joins ring 0's own 42 in one perimeter.

    A gang trace laid along a ring occupies the gap it spans, so those gaps come
    out of the supply. That is the one place stage 1 costs stage 2 anything.
    """
    ganged = {frozenset((a, c)) for a, c, _ in edges}
    cx = cy = (n - 1) / 2.0
    ang = lambda p: math.atan2(p[1] - cy, p[0] - cx)
    slots = []
    for r, tag in ((2, "in"), (0, "out")):
        w = walk(at, n, r)
        for i in range(len(w)):
            a, c = at.get(w[i]), at.get(w[(i + 1) % len(w)])
            if not a or not c:
                continue
            mid = ((w[i][0] + w[(i + 1) % len(w)][0]) / 2.0,
                   (w[i][1] + w[(i + 1) % len(w)][1]) / 2.0)
            slots.append(dict(tag=tag, a=a, c=c, ang=ang(mid),
                              blocked=frozenset((a, c)) in ganged))
    need = [k for k in pos if ring[k] == 1 and k in net
            and (not POWER.match(net[k]) or k in stranded)]
    free = [i for i, s in enumerate(slots) if not s["blocked"]]

    def reach(k, span=2):
        a = ang(cell[k])
        d = lambda i: abs((slots[i]["ang"] - a + math.pi) % (2 * math.pi) - math.pi)
        return (sorted([i for i in free if slots[i]["tag"] == "in"], key=d)[:span] +
                sorted([i for i in free if slots[i]["tag"] == "out"], key=d)[:span])

    match = {}
    sys.setrecursionlimit(20000)
    def aug(k, seen):
        for gi in reach(k):
            if gi in seen:
                continue
            seen.add(gi)
            if gi not in match or aug(match[gi], seen):
                match[gi] = k
                return True
        return False
    for k in sorted(need, key=lambda k: ang(cell[k])):
        aug(k, set())
    miss = [k for k in need if k not in set(match.values())]

    # Inward is not free. The moat has no lateral channel -- 0.090 mm between
    # the ring-2 lands and the first via ring, and the same between via rings --
    # so every trace in there runs radially and needs 0.2781 mm of arc to clear
    # the vias beside it. That caps the moat near 90 escapes, and 54 of those
    # are spoken for before ring 1 gets a look in. Anything over MAX_IN goes out
    # through ring 0 instead, where the perimeter is 36 mm and nothing is tight.
    if MAX_IN is not None:
        inward = [gi for gi in match if slots[gi]["tag"] == "in"]
        inward.sort(key=lambda gi: ang(cell[match[gi]]))
        taken_out = set(gi for gi in match if slots[gi]["tag"] == "out")
        while len(inward) > MAX_IN:
            gi = inward.pop(len(inward) // 2)
            k = match[gi]
            a = ang(cell[k])
            d = lambda i: abs((slots[i]["ang"] - a + math.pi) % (2 * math.pi) - math.pi)
            cand = [i for i in free if slots[i]["tag"] == "out" and i not in taken_out]
            if not cand:
                inward.append(gi)
                break
            gj = min(cand, key=d)
            del match[gi]
            match[gj] = k
            taken_out.add(gj)
    return slots, need, match, miss




# ============================================================================
# STAGE 2 -- the moat: 97 enclosed escapes and the vias they land on.
#
# Ring 0 is NOT here. Its 42 signals and 14 power groups face open board, and
# where their vias go depends on where their traces are headed, which is
# ordinary routing. Stage 2 is the part that is boxed in.
#
# The annulus is a square ring. Parameterise it by arc length around the ring-2
# ball centre square -- half-width 3.500, perimeter 28.000, 56 balls at 0.500 --
# and scale every deeper ring onto the same 28.000 so one scalar orders
# everything. Allocate monotonically in that scalar and no two traces cross.
#
# The constraint that shapes it all is not via count. It is that a trace bound
# for a deeper ring has to pass BETWEEN two vias of every ring above it. One
# empty place leaves 0.487 mm, which holds two 3 mil traces and not three. So
# the perimeter escapes go round in a 0 1 2 cycle: between any two vias on the
# outer ring exactly two deeper traces pass, and each aims at a real gap rather
# than wherever a straight line to its via would have taken it.
#
# The eight core groups come outward from ring 6 and take the innermost ring,
# which nothing has to cross.
# ============================================================================
S2_W = 0.0762                       # 3 mil, the fan-out width
# 0.40, NOT 0.39, AND THE DIFFERENCE IS A DRILL. 0.39 is VIA_L + clr, the
# COPPER rule -- two 0.30 mm lands at 0.09 clearance. It is not the only rule a
# via has to meet: mdDrill says two HOLES must be 0.20 mm apart edge to edge,
# and on 0.2 mm drills that wants 0.40 mm centre to centre. At 0.39 the ring was
# 0.190 mm edge to edge, 0.010 short, on all 93 adjacent pairs -- and nothing
# here checked it, because every clearance test in this toolchain was written
# about copper. Fusion's DRC found all 93. A drill is a mechanical operation and
# the rule applies whoever owns the hole; see check_board.py, which now tests it.
# Stage 3 reported 103 vias at 0.390 needing 40.170 mm of a 58.080 mm perimeter,
# so the extra 1.03 mm is affordable.
VIA_D, VIA_L, VIA_PITCH = 0.2, 0.30, 0.40
MD_DRILL = 0.20                      # mdDrill: hole EDGE to hole EDGE


def via_sep(clr):
    """centre-to-centre two vias need, by BOTH rules that apply to them

    VIA_L + clr is the copper rule -- two lands at the clearance -- and it is
    the only one this file used to know about. VIA_D + MD_DRILL is the
    mechanical one, and here it is the binding one: 0.30 + 0.09 = 0.39 against
    0.20 + 0.20 = 0.40. Every clearance test in this toolchain was written about
    copper, so nothing noticed that the fan-out ring sat 0.010 mm inside mdDrill
    on all 93 of its adjacent pairs. Fusion's DRC noticed.
    """
    return max(VIA_L + clr, VIA_D + MD_DRILL)
CLEAROUT = 0.25                     # radial run before a trace is allowed to angle


def annulus(pos, land, clr):
    xs = sorted({round(p[0], 3) for p in pos.values()})
    ys = sorted({round(p[1], 3) for p in pos.values()})
    cx, cy = (xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2
    h2, h6 = (xs[16] - xs[2]) / 2, (xs[12] - xs[6]) / 2
    inset = land / 2 + clr + VIA_L / 2
    return cx, cy, h2, h6, [h2 - inset - r * VIA_PITCH for r in range(3)]


# The field is a Cartesian grid, so the annulus is four straight sides, not a
# circle. A trace leaving a ball crosses its side PERPENDICULARLY -- straight up
# out of the bottom row, straight left out of the right column. An earlier
# version moved points by homothety about the package centre, which is radial in
# the polar sense and wrong here: it slid the crossing sideways and put the
# ring-1 traces 0.0326 mm from a ring-2 land instead of 0.25.
#
#   side 0 bottom   inward is +y, the along-coordinate is x
#   side 1 right    inward is -x, along is y
#   side 2 top      inward is -y, along is x
#   side 3 left     inward is +x, along is y
SIDE = ((0, 1), (-1, 0), (0, -1), (1, 0))


def side_of(x, y, cx, cy, h):
    u, v = x - cx, y - cy
    if abs(v + h) < 1e-6 and abs(u) <= h + 1e-6: return 0, x
    if abs(u - h) < 1e-6 and abs(v) <= h + 1e-6: return 1, y
    if abs(v - h) < 1e-6 and abs(u) <= h + 1e-6: return 2, x
    if abs(u + h) < 1e-6 and abs(v) <= h + 1e-6: return 3, y
    return None, None


def at_depth(side, along, cx, cy, h, depth):
    """the point on `side`, `along` it, `depth` inboard of the h square"""
    if side == 0: return along, cy - h + depth
    if side == 1: return cx + h - depth, along
    if side == 2: return along, cy + h - depth
    return cx - h + depth, along


def stage2(pos, net, ring, land, clr, match, slots, comp):
    """One via per escape, directly inboard of it, on one of three rings.

    Nothing slides sideways in the annulus -- 0.090 mm between the ring-2 lands
    and the first via ring, and the same between via rings -- so a via has to sit
    where its trace already is, and the trace leaves its ball along the one
    direction that is clear.

    That direction is perpendicular to its side, except at the four corners of
    ring 2, where perpendicular runs straight down the adjoining column of balls.
    A corner escapes at 45 degrees instead.

    Rings are chosen greedily and checked in 2D, not per side, because the
    corners are exactly where two sides' via rows would otherwise collide.
    """
    cx, cy, h2, h6, rings = annulus(pos, land, clr)
    depth = [h2 - h for h in rings]
    esc = []
    for k in pos:
        if ring[k] == 2 and k in net and not POWER.match(net[k]):
            esc.append((pos[k], k, net[k], "r2", None))
    for gi, k in match.items():
        if slots[gi]["tag"] != "in":
            continue
        a, c = slots[gi]["a"], slots[gi]["c"]
        mid = ((pos[a][0] + pos[c][0]) / 2, (pos[a][1] + pos[c][1]) / 2)
        esc.append((mid, k, net[k], "r1", mid))
    for r, v in comp.items():
        if any(ring[x] == 0 for x in v):
            continue
        at2 = sorted(x for x in v if ring[x] == 2)
        if at2:
            esc.append((pos[at2[0]], at2[0], net[at2[0]], "pwr", None))
        elif any(ring[x] == 6 for x in v):
            x = sorted(x for x in v if ring[x] == 6)[0]
            esc.append((pos[x], x, net[x], "core", None))

    posmap = pos

    def direction(p, h):
        """unit vector from a point on the h square, inboard; 45 deg at a corner"""
        u, v = p[0] - cx, p[1] - cy
        dx = -1.0 if u > h - 1e-6 else (1.0 if u < -h + 1e-6 else 0.0)
        dy = -1.0 if v > h - 1e-6 else (1.0 if v < -h + 1e-6 else 0.0)
        if dx and dy:
            return dx / math.sqrt(2), dy / math.sqrt(2)
        return dx, dy

    ang = lambda p: math.atan2(p[1] - cy, p[0] - cx)

    def corner(e):
        p, h = e[0], (h6 if e[3] == "core" else h2)
        return abs(abs(p[0] - cx) - h) < 1e-6 and abs(abs(p[1] - cy) - h) < 1e-6

    # Corners first. A corner has one clear direction, the 45 degree diagonal,
    # where a ball on a straight side has a whole row it can shuffle along. Let
    # the sides claim their vias first and the corners are left with nothing.
    esc.sort(key=lambda e: (not corner(e), ang(e[0])))
    SAME = via_sep(clr)
    PASS = VIA_L / 2 + clr + S2_W / 2
    plan, over, placed = [], [], []
    for p, k, nm, kind, extra in esc:
        h = h6 if kind == "core" else h2
        d = direction(p, h)
        if kind == "core":
            d = (-d[0], -d[1])                      # the core escapes outward
        if d == (0.0, 0.0):
            over.append((k, nm, "no clear direction"))
            continue
        # Neither depth nor direction is fixed. Three rings work along a
        # straight side, where the ball pitch is 0.500 and SAME is 0.390, but
        # they collapse at the four corners: the two balls flanking a corner put
        # their vias 0.209 mm apart, and going deeper makes it worse, because
        # deeper at a corner means closer together. So the escape may lean off
        # perpendicular. A ray leaving a ball at angle t clears its neighbours
        # by 0.5*cos(t), which stays above the 0.2406 needed out to 61 degrees,
        # so there is a lot of room to lean and none to burrow.
        lo = land / 2 + clr + VIA_L / 2
        hi = (h2 - h6) - lo
        base = math.atan2(d[1], d[0])
        pick = None
        for lean in [0.0] + [s * i * math.pi / 36 for i in range(1, 11) for s in (1, -1)]:
            ux, uy = math.cos(base + lean), math.sin(base + lean)
            for step in range(int((hi - lo) / 0.02) + 1):
                dep = lo + step * 0.02
                vx, vy = p[0] + ux * dep, p[1] + uy * dep
                if any(math.hypot(vx - q[0], vy - q[1]) < SAME - 1e-9 for q in placed):
                    continue
                if any(seg_pt(p, (vx, vy), q) < PASS - 1e-9 for q in placed):
                    continue
                if any(math.hypot(vx - b[0], vy - b[1]) < VIA_L / 2 + land / 2 + clr - 1e-9
                       or seg_pt(p, (vx, vy), b) < land / 2 + S2_W / 2 + clr - 1e-9
                       for bk, b in posmap.items() if net.get(bk) != nm and bk != k):
                    continue
                pick, pv = dep, (vx, vy)
                break
            if pick is not None:
                break
        if pick is None:
            over.append((k, nm, "no way in"))
            continue
        placed.append(pv)
        plan.append((k, nm, kind, pick, pv, extra))
    return cx, cy, h2, h6, rings, depth, plan, over


def draw2(pos, cx, cy, h2, plan):
    """the ball, maybe a run in the channel, then straight to the via"""
    CH = h2 + 0.25                                  # between the ring-1 and ring-2 lands
    wires, vias = [], []
    for k, nm, kind, ri, (vx, vy), extra in plan:
        pts = [pos[k]]
        if kind == "r1":
            bx, by = pos[k]
            mx, my = extra
            if abs(by - cy) > abs(bx - cx):         # top or bottom row
                pts += [(bx, cy + math.copysign(CH, by - cy)),
                        (mx, cy + math.copysign(CH, by - cy)), (mx, my)]
            else:
                pts += [(cx + math.copysign(CH, bx - cx), by),
                        (cx + math.copysign(CH, bx - cx), my), (mx, my)]
        pts.append((vx, vy))
        for a, c in zip(pts, pts[1:]):
            if math.hypot(c[0] - a[0], c[1] - a[1]) > 1e-6:
                wires.append((nm, a, c, S2_W))
        vias.append((nm, vx, vy, kind, ri))
    return wires, vias


def verify2(wires, vias, gangs, pos, net, land, clr):
    """measure everything stage 2 drew against everything already on L1"""
    bad = []
    for nm, a, c, w in wires:
        for k, p in pos.items():
            if net.get(k) == nm:
                continue
            d = seg_pt(a, c, p) - land / 2 - w / 2
            if d < clr - 1e-6:
                bad.append(("land", "%s trace vs %s land: %.4f" % (nm, k, d)))
        for vn, vx, vy, _, _ in vias:
            if vn == nm:
                continue
            d = seg_pt(a, c, (vx, vy)) - VIA_L / 2 - w / 2
            if d < clr - 1e-6:
                bad.append(("via", "%s trace vs %s via: %.4f" % (nm, vn, d)))
    allw = list(wires) + [(net[x], pos[x], pos[y], GANG_W) for x, y, _t in gangs]
    for i in range(len(allw)):
        for j in range(i + 1, len(allw)):
            if allw[i][0] == allw[j][0]:
                continue
            d = seg_seg(allw[i][1], allw[i][2], allw[j][1], allw[j][2]) \
                - allw[i][3] / 2 - allw[j][3] / 2
            if d < clr - 1e-6:
                bad.append(("trace", "%s vs %s: %.4f" % (allw[i][0], allw[j][0], d)))
    for i in range(len(vias)):
        for j in range(i + 1, len(vias)):
            if vias[i][0] == vias[j][0]:
                continue
            d = math.hypot(vias[i][1] - vias[j][1], vias[i][2] - vias[j][2]) - VIA_L
            if d < clr - 1e-6:
                bad.append(("viavia", "%s via vs %s via: %.4f" % (vias[i][0], vias[j][0], d)))
        for k, p in pos.items():
            if net.get(k) == vias[i][0]:
                continue
            d = math.hypot(vias[i][1] - p[0], vias[i][2] - p[1]) - VIA_L / 2 - land / 2
            if d < clr - 1e-6:
                bad.append(("vialand", "%s via vs %s land: %.4f" % (vias[i][0], k, d)))
    return bad

# ============================================================================
# STAGE 3 -- out of the package: ring 0, and ring 1's outward crossings.
#
# Unlike the moat, these are not trapped. They come out onto open board, so no
# belt is reserved for them. Reserving a two-ring belt was tried and it evicted
# 25 of the 39 FPGA decoupling capacitors, which are UG483 Table 2-2 exactly and
# not padding. The vias go in the gaps between those capacitors instead, which
# means stage 3 has to know about the whole board and not just U1.
# ============================================================================
S3_W = 0.09                         # 3.5 mil once clear of the ball field


def board_copper(brd, skip=("U1",)):
    """every pad, smd and plated hole on the board, as (net, x, y, hx, hy, side).

    side 1 top, 16 bottom, 0 a plated hole and therefore every layer. Stage 3
    puts through vias into the space between back-side capacitors, so a model
    that only knew about U1 would drill straight through them.
    """
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', brd, re.S):
        for pm in re.finditer(
            r'<package name="([^"]+)"[^>]*>(.*?)</package>', lm.group(2), re.S
        ):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)
    pnet = {}
    for sm in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', brd, re.S):
        for c in re.finditer(r'<contactref element="([^"]+)" pad="([^"]+)"/>', sm.group(2)):
            pnet[(c.group(1), c.group(2))] = sm.group(1)

    def rp(x, y, rot):
        r = re.sub(r"^M", "", rot)
        x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
        return (-x, y) if rot.startswith("M") else (x, y)

    out = []
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"'
                         r'[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', brd):
        nm, lib, pk = m.group(1), m.group(2), m.group(3)
        ex, ey, rot = float(m.group(4)), float(m.group(5)), m.group(6) or "R0"
        if nm in skip:
            continue
        body = pkg.get((lib, pk), "")
        side = 16 if rot.startswith("M") else 1
        for s in re.finditer(r'<smd name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)" '
                             r'dx="([\d.]+)" dy="([\d.]+)"', body):
            x, y, dx, dy = map(float, s.groups()[1:])
            a = rp(x, y, rot)
            # axis half-extents, not a circumscribed circle: a 1206 pad is
            # 1.60 x 1.80, and calling that a radius of 1.204 throws away
            # 0.40 mm of clearance on the axis that matters.
            hx, hy = (dx / 2, dy / 2) if not rot.lstrip("M") in ("R90", "R270")                 else (dy / 2, dx / 2)
            out.append((pnet.get((nm, s.group(1))), ex + a[0], ey + a[1], hx, hy, side))
        for s in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"[^>]*'
                             r'drill="([\d.]+)"(?:[^>]*diameter="([\d.]+)")?', body):
            x, y, dr = float(s.group(2)), float(s.group(3)), float(s.group(4))
            di = float(s.group(5)) if s.group(5) else dr + 0.5
            a = rp(x, y, rot)
            out.append((pnet.get((nm, s.group(1))), ex + a[0], ey + a[1], di / 2, di / 2, 0))
    return out


def fanout_h(pos, cop, net, clr, lo=4.90, hi=7.40, step=0.02):
    """the largest half-width where a whole ring of vias still clears the board.

    Measured, not assumed: the escapes have to reach a radius where 103 vias fit
    at 0.39 pitch, which is 8h >= 40.2 so h >= 5.03, and they have to stop before
    they hit the first thing on either side of the board.

    hi WAS 6.20, and that number was doing real damage while looking like a
    formality. It is not a board limit -- the edge allows 9.46 and X2's pad rows
    allow 7.43 -- it was just where the search stopped, and it happened to match
    where the decoupling capacitors blocked the ring on the 0.800 in board, so
    nothing ever noticed. Raising it does nothing on its own: make_board.py has
    to reserve the annulus first, or parts fill it and the search finds 6.20
    again. The two go together.
    """
    xs = sorted({round(p[0], 3) for p in pos.values()})
    ys = sorted({round(p[1], 3) for p in pos.values()})
    cx, cy = (xs[0] + xs[-1]) / 2, (ys[0] + ys[-1]) / 2
    # The band to keep clear is not just the via's. The run-in reaches STUB
    # inboard of the ring and the via land reaches VIA_L/2 + clr outboard, so
    # that whole span has to be free, and it has to be measured the way verify3
    # measures it or the search hands back a radius the verifier then rejects --
    # which is worse than no search, because the failure resurfaces a stage later
    # wearing a different name.
    #
    # Both use the BOX now. They used to inflate each pad to a circle of its own
    # diagonal, which on a 1.2 x 1.4 mm pad overstates it by 0.22 mm; Q1's pads
    # blocked h = 6.40 by 0.01 mm on that reckoning and clear it by 0.21 on this
    # one. See seg_box().
    inner = STUB + clr + S3_W / 2                # the run-in, plus its clearance
    outer = VIA_L / 2 + clr                      # the via land, plus its clearance
    best = None
    h = lo
    while h <= hi + 1e-9:
        ok = True
        for onet, ox, oy, ohx, ohy, side in cop:
            near, far = box_ring(ox, oy, ohx, ohy, cx, cy)
            if near < h + outer and far > h - inner:
                ok = False
                break
        if ok:
            best = h
        h += step
    return cx, cy, best


def stage3(pos, net, ring, land, clr, match, slots, comp, cop, moat_vias):
    """Fan 103 escapes out to a ring of vias, and do not let them cross.

    They arrive at the package edge at 0.25 mm spacing -- a ring-0 ball and the
    ring-1 gap beside it -- and a via needs 0.39. There is no way to interleave
    out of that: a trace can never slip past the via of its immediate neighbour.
    The only thing that works is to go OUT until there is room. The perimeter
    grows as 8h, so 103 vias at 0.39 need 8h >= 40.2, h >= 5.03; below that no
    arrangement fits and above it the fan is straightforward.

    Vias are placed once round in perimeter order, each as near its own escape as
    the 0.39 spacing allows. Monotonic order means the traces cannot cross, and
    they only ever diverge -- 0.25 apart where they leave the balls, wider all the
    way out -- so the tightest point is the start, where 0.18 is needed.
    """
    xs = sorted({round(p[0], 3) for p in pos.values()})
    ys = sorted({round(p[1], 3) for p in pos.values()})
    h0 = (xs[-1] - xs[0]) / 2
    cx, cy, h = fanout_h(pos, cop, net, clr)
    esc = []
    for k in pos:
        if ring[k] == 0 and k in net and not POWER.match(net[k]):
            esc.append((pos[k], k, net[k], "r0", None))
    for gi, k in match.items():
        if slots[gi]["tag"] != "out":
            continue
        a, c = slots[gi]["a"], slots[gi]["c"]
        mid = ((pos[a][0] + pos[c][0]) / 2, (pos[a][1] + pos[c][1]) / 2)
        esc.append((mid, k, net[k], "r1o", mid))
    for r, v in comp.items():
        at0 = sorted(x for x in v if ring[x] == 0)
        if at0:
            esc.append((pos[at0[0]], at0[0], net[at0[0]], "pwr0", None))

    def perim(p, hh):
        """arc length once round the square of half-width hh, from bottom-left"""
        u, v = p[0] - cx, p[1] - cy
        s = max(abs(u), abs(v))
        u, v = u * hh / s, v * hh / s
        if abs(v + hh) < 1e-6: return u + hh
        if abs(u - hh) < 1e-6: return 2 * hh + (v + hh)
        if abs(v - hh) < 1e-6: return 4 * hh + (hh - u)
        return 6 * hh + (hh - v)

    def xy(s, hh):
        s %= 8 * hh
        if s < 2 * hh: return cx - hh + s, cy - hh
        if s < 4 * hh: return cx + hh, cy - hh + (s - 2 * hh)
        if s < 6 * hh: return cx + hh - (s - 4 * hh), cy + hh
        return cx - hh, cy + hh - (s - 6 * hh)

    esc.sort(key=lambda e: perim(e[0], h0))
    P, SP = 8 * h, via_sep(clr)
    want = [perim(e[0], h0) * (h / h0) for e in esc]
    n = len(esc)
    if n * SP > P:
        return cx, cy, h0, h, [], [(e[1], e[2], "ring is full") for e in esc]
    # Each via wants to sit directly outboard of its own escape, and they cannot
    # all have that -- 0.25 mm of arc arrives and 0.39 is needed. Pushing each
    # one forward off the previous is the obvious fix and a bad one: the shift
    # only ever accumulates, so by the far side the vias are a corner away from
    # their balls and the traces cut back across the package.
    #
    # Isotonic regression instead. Subtract the mandatory spacing, fit the
    # nearest non-decreasing sequence by pooling adjacent violators, and add it
    # back. That is the arrangement with the least total movement, and it shares
    # the shift out instead of dumping it all at one end.
    #
    # CUT THE CIRCLE AT THE WIDEST VOID rather than closing the wrap afterwards.
    # This used to fit the sequence in escape order and then, if the last via
    # failed to clear the first, subtract a share of the overrun from every
    # position: s[i] -= over * i / (n - 1). That takes a local overrun at the
    # seam and spreads it as a global one -- it shortens EVERY gap, so the ring
    # came out with a median spacing of 0.3774 against a 0.390 minimum, illegal
    # on 98 of 103 gaps, while the largest gap on the same ring was 6.876 mm.
    # The demand is not uniform round the package (the SDRAM bus leaves one
    # side), so there is always a void; start the sequence just after the widest
    # one and the wrap constraint is slack by construction and never binds.
    # Measured on the current board: 163 violations before, 58 after.
    gap = [(((want[(i + 1) % n] - want[i]) % P), i) for i in range(n)]
    rot = (max(gap)[1] + 1) % n
    order = [(rot + i) % n for i in range(n)]
    base = want[rot]
    w = [(want[j] - base) % P for j in order]

    # Minimum spacing is per PAIR, not one constant, because a 90 degree corner
    # eats clearance twice over. Two vias 0.390 of ARC apart either side of a
    # corner are only 0.390/sqrt(2) = 0.276 apart in a straight line, which is
    # what the DRC measures -- so sqrt(2) is the floor. But the TRACES running in
    # to those vias converge at 45 degrees as well, and they run out of room
    # before the vias do. sqrt(2) protects the vias and leaves the traces short.
    #
    # Measured at ring 7.26 with the eased lean, sweeping the multiplier:
    #
    #     x1.0  x1.4  x2.0  x2.4  x2.8  x3.0  x4.0  x6.0  x8.0
    #        4     4     4     3     3     1     1     1     6
    #
    # Flat at 1 from 3.0 to 6.0, so CORNER_SP = 4.0 sits in the middle of the
    # plateau rather than on either edge of it. Above that the corners eat so
    # much arc that the straights bunch and it gets worse again.
    #
    # The value is NOT portable: it depends on how much slack the ring has. At
    # half-width 6.20 the perimeter was 49.60 mm against 40.17 of minimum
    # spacing -- 9.43 of slack -- and sqrt(2) measured best because four corners
    # at x4.0 would have cost 4.68 of that. At 7.26 the perimeter is 58.08 and
    # the slack is 17.91, so the same 4.68 is affordable. Re-sweep it if the ring
    # moves again.
    #
    # Which pairs straddle a corner depends on the answer, so iterate: solve,
    # see who ended up on a corner, raise those gaps, solve again. It settles in
    # two or three passes. Doing this as a stretched coordinate instead -- add
    # the allowance to s, fit, map back -- does NOT work: the inverse is not
    # single valued at the corner and the round trip lands vias off the ring.
    sp = [SP] * n
    s = None
    for _pass in range(6):
        off = [0.0] + list(itertools.accumulate(sp[:n - 1]))
        v = [w[i] - off[i] for i in range(n)]
        blocks = []                              # (sum, count) pools
        for x in v:
            blocks.append([x, 1])
            while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
                b = blocks.pop()
                blocks[-1][0] += b[0]
                blocks[-1][1] += b[1]
        fit = []
        for tot, cnt in blocks:
            fit += [tot / cnt] * cnt
        s = [fit[i] + off[i] for i in range(n)]
        want_sp = [SP] * n
        for i in range(n - 1):
            a, c = (base + s[i]) % P, (base + s[i + 1]) % P
            if int(a / (2 * h)) != int(c / (2 * h)):     # different edges of the square
                want_sp[i] = SP * CORNER_SP
        if want_sp == sp:
            break
        sp = want_sp
    if s[-1] - s[0] > P - SP:                    # cannot happen with a real void
        return cx, cy, h0, h, [], [(e[1], e[2], "ring is full") for e in esc]
    plan, bad = [], []
    for i, j in enumerate(order):
        e = esc[j]
        plan.append((e[1], e[2], e[3], xy(base + s[i], h), e[4]))
    return cx, cy, h0, h, plan, bad


# The radial run-in to a ring via. Not a tuned number: the lean has to stay
# VIA_L/2 + clr + S3_W/2 = 0.150 + 0.090 + 0.045 = 0.285 mm clear of a foreign
# via, and the run-in is what holds it at that radius. 0.30 is that plus a hair,
# and it is exactly where the measurement stops finding trace-against-via:
#
#     stub        0.22  0.25  0.28  0.30  0.32  0.35  0.50
#     trace/via      2     1     1     0     0     0     0
#     conflicts     27    27    29    29    31    33    43
#
# Longer than that only steepens the fan, which costs more than it buys.
STUB = 0.30


def approach(vx, vy, cx, cy, h, L=None):
    """the point one stub INBOARD of a ring via, square to the edge it sits on.

    A via needs VIA_L/2 + clr + S3_W/2 = 0.285 mm of room from a foreign trace.
    Land the run-in on the edge normal and the neighbouring vias are 0.390 of
    arc away broadside, which clears. Arrive at a slant instead and the trace
    passes within a few hundredths of the neighbour -- which is what every one
    of the 58 remaining violations was.

    Within L of a corner the run-in would otherwise land outside the inner
    square, among the vias of the adjacent edge, so the free coordinate is
    SCALED back rather than clipped. Clipping stacks every near-corner via on
    the one corner point, and two traces aimed at one point touch by
    construction: CHAN1's via at (40.595, 3.500) and SD-DAT2's at
    (40.300, 3.756) sit on different edges a third of a millimetre apart and
    both clipped to (40.650, 3.850). Scaling keeps them in proportion, so
    distinct vias keep distinct run-ins.

    A via exactly on a corner satisfies both tests; take the horizontal edge, so
    the choice is at least consistent.
    """
    L = STUB if L is None else L
    u, w = vx - cx, vy - cy
    inner = h - L
    if abs(abs(w) - h) < 1e-6:                  # bottom or top edge
        return (cx + u * min(1.0, inner / max(abs(u), inner)),
                cy + math.copysign(inner, w))
    return (cx + math.copysign(inner, u),       # left or right edge
            cy + w * min(1.0, inner / max(abs(w), inner)))


# Segments the lean is cut into. Eight; four is measurably worse (the chords cut
# the arc), twelve and beyond buy nothing and trace the board with three times
# the copper. Read at CALL time, not captured as a default argument -- lean()
# and approach() both used to take these as defaults, which binds them at def
# time, so every sweep of them silently measured the original value and reported
# "no effect". The stepout sweep was real; the stub and step sweeps were not.
LEAN_STEPS = 8
# The straight-out run before the fan starts, and it wants to be SHORT. It was
# 0.35, which is a third of the radial room between the ball field and the ring,
# and every millimetre it takes the fan has to make up in lean angle. Measured,
# holding everything else fixed:
#
#     stepout   0.15  0.20  0.25  0.35  0.50  0.70  0.90
#     conflicts   31    33    36    40    45    63    93
#
# It cannot go to nothing, though. The run exists so a ring-1 escape leaving
# through the gap between two ring-0 balls clears their lands -- 0.1125 + 0.090
# + 0.045 = 0.2475 mm from each centre, against the 0.25 the gap gives it. Start
# fanning too early and the trace turns straight into one:
#
#     stepout   0.00  0.11  0.12  0.13  0.14  0.15
#     lands hit    40    12     8     5     1     0
#
# 0.15 is the cliff edge exactly. Where the cliff sits depends on the steepest
# lean in the isotonic fit, which moves whenever the placement does, so take a
# third again above it and pay the two extra trace conflicts.
STEPOUT = 0.20


def sq_frac(p, cx, cy):
    """(chebyshev radius, fraction of the way round) for a point about a centre.

    Same origin and direction as stage 2's s_of/xy: bottom-left, anticlockwise.
    """
    u, w = p[0] - cx, p[1] - cy
    r = max(abs(u), abs(w))
    if r < 1e-12:
        return 0.0, 0.0
    if abs(w + r) < 1e-9:   s = u + r                       # bottom
    elif abs(u - r) < 1e-9: s = 2 * r + (w + r)             # right
    elif abs(w - r) < 1e-9: s = 4 * r + (r - u)             # top
    else:                   s = 6 * r + (r - w)             # left
    return r, s / (8 * r)


def sq_pt(f, r, cx, cy):
    """the point at fraction f round the square of half-width r"""
    s = (f % 1.0) * 8 * r
    if s < 2 * r: return (cx - r + s, cy - r)
    if s < 4 * r: return (cx + r, cy - r + (s - 2 * r))
    if s < 6 * r: return (cx + r - (s - 4 * r), cy + r)
    return (cx - r, cy + r - (s - 6 * r))


def lean(a, c, cx, cy, steps=None):
    """a to c, holding ANGULAR position linear in radius instead of going straight.

    This is what stops neighbouring escapes converging, and it is worth being
    precise about why. Escapes leave the package 0.25 mm apart -- a ring-0 ball
    and the ring-1 gap beside it alternate -- and two 0.09 mm traces need 0.18
    between centres. Seven hundredths of a millimetre of margin, and the median
    escape leans 0.759 mm sideways across a 1.00 mm band to reach its via, about
    37 degrees. Any difference in lean angle between neighbours spends the
    margin immediately, which is what all 42 remaining conflicts were.

    A STRAIGHT line between two nested squares does not preserve angular
    spacing: it cuts the corner of the fan, so a trace leaning hard crosses the
    ground its gentler neighbour is standing on. Interpolate the fraction of the
    way round linearly in radius instead and every trace in the fan turns
    together. Two neighbours then stay a fixed fraction apart, and since the
    perimeter grows with radius -- 38.8 mm at the step-out, 46.8 at the run-in --
    their separation can only ever increase. The minimum is at the start, where
    it is the 0.25 mm the package hands over.

    Eight segments is enough that the chords do not measurably cut the arc.
    """
    steps = LEAN_STEPS if steps is None else steps
    r0, f0 = sq_frac(a, cx, cy)
    r1, f1 = sq_frac(c, cx, cy)
    d = f1 - f0
    d = d - 1.0 if d > 0.5 else (d + 1.0 if d < -0.5 else d)     # the short way
    out = []
    for i in range(1, steps + 1):
        t = float(i) / steps
        # SMOOTHSTEP, not linear. Linear leaves the ball field already turning at
        # its full rate, and the escape beside it is still going straight out --
        # so the first chord of one trace's lean cuts across the end of its
        # neighbour's step-out. Three of the last six conflicts were exactly
        # that, all with the same shape:
        #
        #    CHAN28  step-out (51.000,16.490)->(51.200,16.490)   r 4.50->4.70
        #    VCC3V3  lean     (51.200,16.240)->(51.482,16.524)   r 4.70->4.98
        #
        # t*t*(3-2*t) has zero slope at both ends, so a trace leaves radially
        # alongside whatever is still stepping out, and arrives radially into the
        # run-in. Measured: 6 conflicts -> 4. Every easing with f'(0) = 0 scores
        # the same, so it is the DEPARTURE that matters; smoothstep is chosen for
        # having f'(1) = 0 as well, which is what the stub wants.
        e = t * t * (3.0 - 2.0 * t)
        out.append(sq_pt(f0 + d * e, r0 + (r1 - r0) * t, cx, cy))
    return out


def draw3(pos, cx, cy, h0, plan, h=None, gangs=()):
    """gangs is stage 1's copper as (net, p, q) -- see the dogleg note below"""
    CH = h0 - 0.25                              # between the ring-1 and ring-0 lands
    wires, vias = [], []

    def clear_of_gangs(nm, pts):
        """worst clearance from this route to any FOREIGN stage-1 gang trace"""
        worst = 1e9
        for a, c in zip(pts, pts[1:]):
            for gn, p, q in gangs:
                if gn == nm:
                    continue
                worst = min(worst, seg_seg(a, c, p, q) - GANG_W / 2 - S3_W / 2)
        return worst

    for k, nm, kind, (vx, vy), extra in plan:
        pts = [pos[k]]
        if kind == "r1o":
            bx, by = pos[k]
            mx, my = extra
            # A ring-1 escape reaches its gap by an L, and which way the L turns
            # first used to be decided by whichever offset from the centre was
            # larger -- with a bare `else` when they were equal. Three of the 47
            # sit EXACTLY on the diagonal, where that test has nothing to go on,
            # and one of them was the last conflict on the board: CHAN28 at B18
            # left sideways along y = 16.240 and ran 0.0193 from VCC3V3's
            # diagonal gang, which leaves the ball next door heading down-left.
            # It needed 0.090.
            #
            # A gang trace is 0.225 mm wide, the full ball land, so it costs
            # 0.1125 + 0.045 = 0.1575 of half-width before clearance is counted.
            # There is no room to be careless about crossing one.
            #
            # So at the TIE, and only there, measure both Ls against stage 1's
            # copper and take the roomier. Everywhere else the original rule
            # stands: turn along the axis you are further out on, which is what
            # keeps the route inside its own corridor rather than across a row of
            # lands. Scoring every route on gang clearance alone instead was
            # tried and is much worse -- 215 violations, traces optimising
            # themselves straight over the ball field, because gang clearance is
            # not the only thing the L has to respect. The rule is kept where it
            # means something and given a reason only where it had none.
            #
            # Flipping the tie the other way unconditionally also reaches zero
            # here, but that is luck: it happens to point away from this
            # particular gang. Three routes are ties; two of them change.
            vert = [(bx, cy + math.copysign(CH, by - cy)),
                    (mx, cy + math.copysign(CH, by - cy)), (mx, my)]
            horz = [(cx + math.copysign(CH, bx - cx), by),
                    (cx + math.copysign(CH, bx - cx), my), (mx, my)]
            if abs(abs(by - cy) - abs(bx - cx)) < 1e-9 and gangs:
                pts += (vert if clear_of_gangs(nm, [pos[k]] + vert)
                        >= clear_of_gangs(nm, [pos[k]] + horz) else horz)
            elif abs(by - cy) > abs(bx - cx):
                pts += vert
            else:
                pts += horz
        # Step straight out past the ball lands before leaning towards the via,
        # or a trace whose via sits a long way round cuts back over the field.
        # PERPENDICULAR, not along a ray to the centre: the field is Cartesian,
        # and a homothety slides the point sideways by up to 0.35 mm, straight
        # at the neighbouring land. That is the same mistake stage 2 made.
        bx, by = pts[-1]
        u, w2 = bx - cx, by - cy
        dx = 1.0 if u > h0 - 1e-6 else (-1.0 if u < -h0 + 1e-6 else 0.0)
        dy = 1.0 if w2 > h0 - 1e-6 else (-1.0 if w2 < -h0 + 1e-6 else 0.0)
        if dx and dy:
            dx, dy = dx / math.sqrt(2), dy / math.sqrt(2)
        if dx or dy:
            pts.append((bx + dx * STEPOUT, by + dy * STEPOUT))
        # Come in square to the ring. The long lean is allowed to do whatever it
        # likes at a smaller radius, where there is no via to hit; only the last
        # STUB mm, where the vias are, has to be disciplined.
        if h is not None:
            ap = approach(vx, vy, cx, cy, h)
            if math.hypot(ap[0] - pts[-1][0], ap[1] - pts[-1][1]) > 1e-6:
                pts += lean(pts[-1], ap, cx, cy)
        pts.append((vx, vy))
        for a, c in zip(pts, pts[1:]):
            if math.hypot(c[0] - a[0], c[1] - a[1]) > 1e-6:
                wires.append((nm, a, c, S3_W))
        vias.append((nm, vx, vy, kind, 0))
    return wires, vias


def distinct(bad):
    """collapse a violation list to one entry per (kind, unordered net pair).

    The verifiers walk segments, and two nets that run alongside each other
    conflict once per segment pair, so a raw len() counts the same physical
    problem several times over and reports a pair from each end besides. It said
    191 where there were 163, then 86 where there were 58, then 57 where there
    were 44 -- every one of those numbers was quoted as progress. Count what a
    person would count: how many places on the board are wrong.

    Returns the deduplicated set and, for each, the worst distance found.
    """
    worst = {}
    for t, x in bad:
        m = re.match(r"(\S+?)(?: trace)? vs (\S+?)(?: via| copper| land)?: ([-\d.]+)", x)
        if not m:
            worst.setdefault((t, x), (0.0, x))
            continue
        key = (t if t != "via" else "trace/via", tuple(sorted((m.group(1), m.group(2)))))
        d = float(m.group(3))
        if key not in worst or d < worst[key][0]:
            worst[key] = (d, x)
    return worst


def verify3(wires, vias, cop, clr):
    """the stage-3 copper against the rest of the board, both sides"""
    bad = []
    for nm, a, c, w in wires:
        for onet, ox, oy, ohx, ohy, side in cop:
            if onet == nm or side == 16:
                continue                        # a top trace ignores back copper
            d = seg_box(a, c, ox, oy, ohx, ohy) - w / 2
            if d < clr - 1e-6:
                bad.append(("board", "%s trace vs %s copper: %.4f" % (nm, onet, d)))
    for nm, vx, vy, _k, _r in vias:
        for onet, ox, oy, ohx, ohy, side in cop:
            if onet == nm:
                continue
            d = max(abs(vx - ox) - ohx, abs(vy - oy) - ohy) - VIA_L / 2
            if d < clr - 1e-6:
                bad.append(("board", "%s via vs %s copper: %.4f" % (nm, onet, d)))
    return bad


def main():
    b, pos, land, net, clr = load(BRD)
    cell, at, ring, n = grid(pos)
    print("field %dx%d, %d balls, land %.3f, clearance %.3f" % (n, n, len(pos), land, clr))
    void = 2 * (0.5 * math.sqrt(2) / 2 - land / 2)
    print("four-ball void %.4f across -> a via land could be %.4f; the board's is 0.300, so none go inside"
          % (void, void - 2 * clr))
    for tag, d in (("orthogonal", 0.5), ("diagonal", 0.5 / math.sqrt(2)), ("jump", 0.5)):
        print("  %-10s gang trace clears a foreign land by %.4f" % (tag, d - land / 2 - GANG_W / 2))

    pwr, edges, comp = gang(pos, net, cell, at)
    kinds = collections.Counter(e[2] for e in edges)
    print("\n%d power/ground balls -> %d edges (%s) -> %d components"
          % (len(pwr), len(edges), ", ".join("%d %s" % (v, k) for k, v in sorted(kinds.items())), len(comp)))

    bad = verify(edges, pos, net, land, clr)
    print("verify: %s" % ("clean" if not bad else "%d VIOLATION(S)" % len(bad)))
    for v in bad[:8]:
        print("   " + v)
    if bad:
        return len(bad)

    print("\nnet         comps  balls  stranded (no ball in ring 0, 2 or 6)")
    stranded = []
    by = collections.defaultdict(list)
    for r, v in comp.items():
        by[net[v[0]]].append(v)
    for nm in sorted(by, key=lambda s: -sum(len(v) for v in by[s])):
        b2 = [v for v in by[nm] if not any(ring[k] in (0, 2, 6) for k in v)]
        stranded += b2
        print("  %-10s %5d %6d  %s" % (nm, len(by[nm]), sum(len(v) for v in by[nm]),
                                       "-" if not b2 else [c for c in b2]))
    strand = [k for c in stranded for k in c]
    print("\n%d stranded component(s): %s" % (len(stranded), strand if strand else "none"))
    print("   they cannot reach a plane by ganging, so they need a lane like a signal")

    # --- stage 2, proved here but not drawn yet -----------------------------
    slots, need, match, miss = lanes(pos, net, cell, at, ring, n, edges, set(strand))
    for tag, lbl in (("in", "ring 2, inward "), ("out", "ring 0, outward")):
        s = [x for x in slots if x["tag"] == tag]
        blk = [x for x in s if x["blocked"]]
        print("\n%s  %d gaps, %d taken by a gang trace -> %d free"
              % (lbl, len(s), len(blk), len(s) - len(blk)))
        if blk:
            print("      taken: %s" % ", ".join("%s-%s" % (x["a"], x["c"]) for x in blk))
    d = collections.Counter(slots[gi]["tag"] for gi in match)
    print("\n%d enclosed ring-1 balls, each offered its 2 nearest gaps either way:"
          " %d matched" % (len(need), len(match)))
    print("   %d inward through ring 2, %d outward through ring 0" % (d["in"], d["out"]))
    if miss:
        print("   ****  %d have nowhere to go: %s" % (len(miss), miss))
        return len(miss)
    print("   every enclosed ball has a lane -- THE ESCAPE CLOSES")

    # --- stage 2: the moat ---------------------------------------------------
    cx, cy, h2, h6, rings, depth, plan, over = stage2(
        pos, net, ring, land, clr, match, slots, comp)
    w2, v2 = draw2(pos, cx, cy, h2, plan)
    dep = [math.hypot(v[1] - pos[e[0]][0], v[2] - pos[e[0]][1]) for e, v in zip(plan, v2)]
    print("")
    print("stage 2, the moat: %d escapes  %s"
          % (len(plan), dict(collections.Counter(e[2] for e in plan))))
    print("   %d traces, %d vias, %.4f..%.4f mm in from the ball they serve"
          % (len(w2), len(v2), min(dep), max(dep)))
    if over:
        print("   ****  %d could not be placed: %s" % (len(over), over[:6]))
    bad2 = distinct(verify2(w2, v2, edges, pos, net, land, clr))
    print("   verify: %s" % ("clean" if not bad2 else "%d VIOLATION(S)" % len(bad2)))
    for _k, (_d, x) in sorted(bad2.items(), key=lambda kv: kv[1][0])[:6]:
        print("      " + x)
    if over or bad2:
        return len(over) + len(bad2)

    # --- stage 3: out of the package -----------------------------------------
    cop = board_copper(b)
    cx3, cy3, h0, hf, plan3, over3 = stage3(
        pos, net, ring, land, clr, match, slots, comp, cop, [(v[1], v[2]) for v in v2])
    w3, v3 = draw3(pos, cx3, cy3, h0, plan3, hf,
                   [(net[x], pos[x], pos[y]) for x, y, _t in edges])
    print("")
    print("stage 3, out of the package: %d escapes  %s"
          % (len(plan3), dict(collections.Counter(e[2] for e in plan3))))
    print("   fan-out ring at half-width %.3f mm; %d vias at %.3f pitch need %.3f"
          " of the %.3f mm perimeter"
          % (hf, len(v3), via_sep(clr), len(v3) * via_sep(clr), 8 * hf))
    print("   %d traces" % len(w3))
    if over3:
        print("   ****  %d could not be placed: %s" % (len(over3), over3[:6]))
    # set(), because both verifiers report a pair from each end and the raw list
    # double-counts. It said 191 where there were 163 distinct problems, which is
    # not a rounding difference when the number is the thing being tracked.
    bad3 = distinct(verify2(w2 + w3, v2 + v3, edges, pos, net, land, clr)
                    + verify3(w3, v3, cop, clr))
    print("   verify: %s" % ("clean" if not bad3 else
                             "%d VIOLATION(S) -- %s" % (len(bad3), dict(
                                 collections.Counter(k[0] for k in bad3)))))
    for _k, (_d, x) in sorted(bad3.items(), key=lambda kv: kv[1][0])[:6]:
        print("      " + x)
    # Stage 3 is reported, not written, so its shortfall must not stop stages 1
    # and 2 being applied. It used to return here and leave the board unrouted.
    if over3 or bad3:
        print("   stage 3 is NOT written: %d unplaced, %d violation(s)"
              % (len(over3), len(bad3)))

    if not APPLY:
        print("")
        print("report only -- re-run with --apply to write it into the board")
        return 0

    # Refuse to stack a second escape on top of the first. This pass appends
    # into <signals>, so running it twice doubles every wire and every via, and
    # nothing downstream would call that an error -- the board simply grows a
    # duplicate of itself. make_board.py is the reset.
    sg = re.search(r"<signals>.*?</signals>", b, re.S).group(0)
    if ("<wire " in sg or "<via " in sg) and not SELECTED_NETS:
        print("")
        print("REFUSING TO APPLY: the board already carries %d wires and %d vias."
              % (sg.count("<wire "), sg.count("<via ")))
        print("Run  python tools/make_board.py --fab jlcpcb  first, then this again.")
        return 1

    out = b
    wires = [(net[a], pos[a], pos[c], GANG_W) for a, c, _t in edges] + list(w2)
    vias = list(v2)
    # Stage 3 goes in ONLY when it verifies. Until now it never did, so there
    # was no code to write it and the board carried stages 1 and 2 alone; the
    # gate is what that absence really meant, so make it explicit rather than
    # implicit in what the list happens to contain.
    if over3 or bad3:
        stage3_note = "stage 3 held back: %d unplaced, %d violation(s)" % (len(over3), len(bad3))
    else:
        wires += list(w3)
        vias += list(v3)
        stage3_note = "including stage 3: %d traces and %d ring vias" % (len(w3), len(v3))
    if SELECTED_NETS:
        wires = [wire for wire in wires if wire[0] in SELECTED_NETS]
        vias = [via for via in vias if via[0] in SELECTED_NETS]
        missing = SELECTED_NETS - {wire[0] for wire in wires} - {via[0] for via in vias}
        if missing:
            print("REFUSING TO APPLY: no escape geometry for %s" %
                  ", ".join(sorted(missing)))
            return 1
    for nm, a, c, wd in wires:
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(nm), out)
        assert m, nm
        s = '<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="1"/>' % (
            g(a[0]), g(a[1]), g(c[0]), g(c[1]), g(wd))
        out = out[:m.end()] + s + out[m.end():]
    for nm, vx, vy, _kind, _r in vias:
        m = re.search(r'(<signal name="%s"[^>]*>)' % re.escape(nm), out)
        assert m, nm
        s = '<via x="%s" y="%s" extent="1-16" drill="%s" diameter="%s"/>' % (
            g(vx), g(vy), g(VIA_D), g(VIA_L))
        out = out[:m.end()] + s + out[m.end():]
    import xml.etree.ElementTree as ET
    ET.fromstring(out)
    open(BRD, "w", encoding="utf-8").write(out)
    print("")
    print("wrote %d wires and %d vias into %s" % (len(wires), len(vias), BRD))
    print("   %s" % stage3_note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
