# -*- coding: utf-8 -*-
"""Shared routing geometry: what copper is where, and how close a path may go.

Split out of power.py and signals.py because both need it and the two had
drifted apart, each carrying a different and separately wrong idea of how big a
pad is. Everything here is measured against the same model check_board.py uses,
which is the point: a router whose clearance model is looser than the checker's
lays copper that then fails, and one whose model is tighter refuses routes that
are perfectly legal. Both happened.

THE PAD MODEL. A pad is a rounded rectangle. Eagle gives dx, dy and a roundness
percentage of the short axis; that is the Minkowski sum of a smaller rectangle
with a disc, so distance is measured to the shrunken rectangle and the corner
radius subtracted. The two failures this replaces:

  * a circumscribed circle, radius hypot(hx, hy) -- power.py. Fine for the big
    isolated pads the rails land on. On U3's 0.40 x 1.35 TSOP-II pads at 0.80 mm
    pitch it makes adjacent pads of the SAME PART overlap, so no via could be
    placed anywhere near that package and all 39 bus nets failed at once.

  * an inscribed chain of discs -- the first as_circles. It touches a long pad's
    edges only at the disc centres and leaves scallops between, so traces grazed
    U3's pads and check_board reported it, correctly.

Rectangles for the exact tests, and a COVERING chain of discs where a circle is
all the consumer can take (the maze). Covering, never inscribed: a router's
approximation has to be a superset or it lays copper the checker rejects.
"""

import re, os, sys, math, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import escape as E                                          # noqa: E402


# ------------------------------------------------------------ distances
def rect_pt(r, px, py):
    """distance from a point to an axis-aligned rectangle (0 if inside)"""
    cx, cy, hx, hy = r[:4]
    return math.hypot(max(abs(px - cx) - hx, 0.0), max(abs(py - cy) - hy, 0.0))


def rect_seg(r, a, c, n=48):
    """distance from a segment to a rectangle.

    Sampled rather than solved. rect_pt along a segment is convex, so the
    sampled minimum overstates the true distance by at most the sagitta over one
    step -- microns on a stub, against a 0.09 mm limit.
    """
    return min(rect_pt(r, a[0] + (c[0] - a[0]) * k / float(n),
                       a[1] + (c[1] - a[1]) * k / float(n))
               for k in range(n + 1)) - (r[4] if len(r) > 4 else 0.0)


def as_circles(rects, step=0.20):
    """a rectangle as a chain of circles that CONTAINS it.

    Centres spaced d along the long axis with radius hypot(d/2, short): each
    disc reaches exactly +/- d/2 at the pad's edge, so consecutive discs meet
    there and the union covers the whole rectangle.
    """
    out = []
    for r in rects:
        cx, cy, hx, hy = r[:4]
        cr = r[4] if len(r) > 4 else 0.0
        hx, hy = hx + cr, hy + cr          # the disc chain covers the full pad
        flip = hy > hx
        L, S = (hy, hx) if flip else (hx, hy)
        n = max(1, int(math.ceil(2.0 * L / step)))
        d = 2.0 * L / n
        rad = math.hypot(d / 2.0, S)
        for k in range(n + 1):
            t = -L + d * k
            out.append((cx, cy + t, rad) if flip else (cx + t, cy, rad))
    return out


def sample(a, c, r, step=0.1):
    """a segment as a chain of discs COVERING it, for consumers that take circles.

    The radius is inflated to hypot(r, step/2), and that is not fussiness. Discs
    of radius r spaced step apart pinch to sqrt(r^2 - (step/2)^2) between
    centres, and the usual call here is a 0.10 mm trace at step 0.1 -- r = 0.05,
    step/2 = 0.05, so the waist is EXACTLY ZERO. The chain then represents the
    centreline and nothing either side of it, and a straightened chord can pass
    a trace by less than the rule allows: check_board found it as four
    violations at 0.0803 against 0.0900, which is 0.0097 -- the size of the gap
    this leaves. Inflating makes the PINCH equal r, which is what was meant.
    """
    n = max(1, int(math.hypot(c[0] - a[0], c[1] - a[1]) / step))
    d = math.hypot(c[0] - a[0], c[1] - a[1]) / n
    rad = math.hypot(r, d / 2.0)
    return [(a[0] + (c[0] - a[0]) * k / float(n),
             a[1] + (c[1] - a[1]) * k / float(n), rad) for k in range(n + 1)]


def clear(a, c, obst, clr, w):
    """does segment a-c keep `clr` from every obstacle circle"""
    for ox, oy, r in obst:
        if E.seg_pt(a, c, (ox, oy)) < r + clr + w / 2 - 1e-9:
            return False
    return True


def straighten(pts, obst, clr, w):
    """pull a breadth-first staircase straight, as far as line of sight allows.

    Maze.path is 4-connected and only collapses collinear runs, so every turn
    survives. On a diagonal that is a staircase of length |dx| + |dy|, and the
    length is the smaller half of the problem: a staircase sweeps a broad
    corridor, and every trace laid is a wall for the next. VCC1V8 came out at
    471 mm against a 91.6 mm straight-line bound -- 5.1x -- and between them the
    two rails cut L3 into pockets the SDRAM bus could not cross.

    Greedy string-pulling against the same obstacle set the maze was built from,
    so nothing is smoothed through copper the maze was avoiding.
    """
    if len(pts) < 3:
        return pts
    out, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not clear(pts[i], pts[j], obst, clr, w):
            j -= 1
        out.append(pts[j])
        i = j
    return out


# ------------------------------------------------------------ the board
def vias(txt, dflt=0.3):
    """(x, y, diameter) for every via in `txt`, however it was written.

    THESE TOOLS WRITE ONE FORM AND FUSION WRITES ANOTHER:

        ours    <via x="16.966" y="4.835" extent="1-16" drill="0.2" diameter="0.3"/>
        Fusion  <via x="10.512" y="7.936" extent="1-16" drill="0.2">

    An OPEN tag, and no diameter. Every reader in this toolchain matched on
    `/>` or required `diameter=`, so the moment a board came back from Fusion
    they all read it as having ZERO vias -- 868 of them invisible at once. The
    damage is silent and it flatters: check_board reported that every wire
    cleared foreign copper while never testing a single via, on a board whose
    autorouter had just added 440 of them.

    A missing diameter is the design rules' business, not the file's: Eagle
    takes drill plus a restring of 25 %% clamped to 0.05 minimum, which is where
    a 0.2 drill gets the 0.3 these tools write explicitly.
    """
    out = []
    for m in re.finditer(r"<via\s([^>]*)>", txt):
        at = m.group(1)
        mx, my = re.search(r'x="([-\d.]+)"', at), re.search(r'y="([-\d.]+)"', at)
        if not (mx and my):
            continue
        md = re.search(r'diameter="([\d.]+)"', at)
        mr = re.search(r'drill="([\d.]+)"', at)
        if md:
            dia = float(md.group(1))
        elif mr:
            d = float(mr.group(1))
            dia = d + 2 * max(d * 0.25, 0.05)
        else:
            dia = dflt
        out.append((float(mx.group(1)), float(my.group(1)), dia))
    return out

def copper_model(b, net, layer=None):
    """foreign copper: pads as rounded rectangles, vias and holes as circles.

    layer=None means "on any layer" -- what a through via has to miss.
    layer=1 / 3 / 16 restricts pads and wires to copper that layer actually sees.
    Inner layers carry no pads at all, only plated holes and vias.
    """
    # `net` may be a single name or a set of them. The set form is what lets a
    # router build ONE base obstacle grid with the whole group left out, then
    # add back only the group members that are currently placed -- which is what
    # makes rip-up affordable, since ripping means REMOVING copper and a grid
    # can only have copper punched into it.
    own = net if isinstance(net, (set, frozenset)) else {net}
    rects, circs, segs = [], [], []
    for rec in E.board_copper(b, skip=()):
        onet, x, y, hx, hy, side = rec[:6]
        if onet in own:
            continue
        # A plated hole is copper on EVERY layer, so it counts whatever we are
        # routing on. Rectangle, not hypot(hx, hy): board_copper reports these
        # with hx = hy = diameter/2, and circumscribing that inflates the pad by
        # 1.41. X2's header pins are 1.88 mm on a 2.54 mm pitch -- the inflated
        # circles overlap, which sealed the whole header field on every layer
        # and left rail terminals inside it unreachable. Square is exact for
        # X2/JP3/J1, which are shape="square", and conservative for a round pad.
        if side == 0 or layer in (None, side):
            rects.append((x, y, hx, hy, 0.0))
    sig = re.search(r"<signals>(.*)</signals>", b, re.S)
    sig = sig.group(1) if sig else ""
    for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', sig, re.S):
        if m.group(1) in own:
            continue
        for vx, vy, vd in vias(m.group(2)):
            circs.append((vx, vy, vd / 2.0))
        for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                             r' y2="([-\d.]+)" width="([\d.]+)" layer="(\d+)"', m.group(2)):
            # LAYER 19 IS NOT COPPER. It is the ratsnest, and a signal element
            # carries its airwires right alongside its wires. The layer filter
            # below only bites when a specific layer was asked for; layer=None
            # means "a through via, which must clear every layer", and that is
            # precisely the case where 107 imaginary lines were being dilated
            # into the maze and refusing real via sites. check_board hit this
            # same trap once -- 404 phantom clearance violations -- and was
            # fixed by restricting copper to 1-16. This never was.
            if not 1 <= int(w.group(6)) <= 16:
                continue
            if layer is not None and w.group(6) != str(layer):
                continue
            x1, y1, x2, y2, wd = map(float, w.groups()[:5])
            segs.append(((x1, y1), (x2, y2), wd / 2.0))
    return rects, circs, segs


def obstacles(b, net, layer, extra=()):
    """everything on `layer` that `net` must clear, as circles for the maze"""
    rects, circs, segs = copper_model(b, net, layer)
    out = as_circles(rects) + circs + list(extra)
    for u, v, r in segs:
        out += sample(u, v, r)
    return out


def element_pads(b):
    """board_copper, but keeping which element owns each pad"""
    pkg = {}
    for lm in re.finditer(r'<library name="([^"]+)">(.*?)</library>', b, re.S):
        for pm in re.finditer(r'<package name="([^"]+)">(.*?)</package>', lm.group(2), re.S):
            pkg[(lm.group(1), pm.group(1))] = pm.group(2)

    def rp(x, y, rot):
        r = re.sub(r"^M", "", rot)
        x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
        return (-x, y) if rot.startswith("M") else (x, y)

    out = collections.defaultdict(list)
    for m in re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"'
                         r'[^>]*x="([-\d.]+)" y="([-\d.]+)"(?:[^>]*rot="([^"]+)")?', b):
        nm, lib, pk = m.group(1), m.group(2), m.group(3)
        ex, ey, rot = float(m.group(4)), float(m.group(5)), m.group(6) or "R0"
        body = pkg.get((lib, pk), "")
        for s in re.finditer(r'<smd name="[^"]+" x="([-\d.]+)" y="([-\d.]+)" ', body):
            a = rp(float(s.group(1)), float(s.group(2)), rot)
            out[nm].append((ex + a[0], ey + a[1]))
        for s in re.finditer(r'<pad name="[^"]+" x="([-\d.]+)" y="([-\d.]+)"', body):
            a = rp(float(s.group(1)), float(s.group(2)), rot)
            out[nm].append((ex + a[0], ey + a[1]))
    return out


def components(b, net, term, tol=0.06):
    """group terminals by the copper of `net` that ALREADY joins them.

    Without this a router spans every terminal it can see, including pairs that
    are already the same piece of copper, and pays whatever the detour costs.
    VCC1V8's worst edge was two escape moat vias 3.2 mm apart routed as 53.2 mm
    -- 16.7x -- because both sit INSIDE U1's stage-3 via ring, which is a wall,
    so the only way between them was out of the ring and back in. They needed no
    wire at all: the escape had already ganged those balls together on L1 and
    brought them out. Four more of that rail's edges were the same mistake, and
    together they were most of its 405 mm.

    Union-find over the net's existing wires, then attach each terminal to any
    wire it physically touches.
    """
    sig = re.search(r"<signals>(.*)</signals>", b, re.S)
    m = re.search(r'<signal name="%s"[^>]*>(.*?)</signal>' % re.escape(net),
                  sig.group(1) if sig else "", re.S)
    segs = []
    if m:
        for w in re.finditer(r'<wire x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)"'
                             r' y2="([-\d.]+)" width="([\d.]+)"', m.group(1)):
            x1, y1, x2, y2, wd = map(float, w.groups())
            segs.append(((x1, y1), (x2, y2), wd / 2.0))

    node = {}                       # rounded point -> index

    def idx(p):
        k = (round(p[0], 3), round(p[1], 3))
        if k not in node:
            node[k] = len(node)
        return node[k]

    par = {}

    def find(a):
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def uni(a, c):
        a, c = find(a), find(c)
        if a != c:
            par[a] = c

    for u, v, r in segs:
        uni(idx(u), idx(v))
    # a terminal joins a wire when it actually touches it, not only at an end:
    # the escape's gang traces run past a via as often as they stop on one
    tid = [idx(t) for t in term]
    for k, t in enumerate(term):
        for u, v, r in segs:
            if E.seg_pt(u, v, t) <= r + tol:
                uni(tid[k], idx(u))
    groups = collections.defaultdict(list)
    for k in range(len(term)):
        groups[find(tid[k])].append(k)
    return list(groups.values())


def mst_groups(term, groups):
    """MST over groups of already-connected terminals.

    Returns (i, j) terminal pairs -- the closest pair between the two groups an
    edge joins, so the wire that gets drawn is the shortest one that would make
    them one piece.
    """
    if len(groups) < 2:
        return []
    def near(g, h):
        best = None
        for i in g:
            for j in h:
                d = math.hypot(term[i][0] - term[j][0], term[i][1] - term[j][1])
                if best is None or d < best[0]:
                    best = (d, i, j)
        return best
    inn, out, edges = [0], list(range(1, len(groups))), []
    while out:
        best = None
        for a in inn:
            for c in out:
                d, i, j = near(groups[a], groups[c])
                if best is None or d < best[0]:
                    best = (d, i, j, c)
        edges.append((best[1], best[2]))
        inn.append(best[3]); out.remove(best[3])
    return edges


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


# ------------------------------------------------- differential pairs
def offset_polyline(pts, d):
    """the polyline `pts` shifted sideways by d, mitred at the corners.

    THIS IS WHY A PAIR DOES NOT NEED HAND ROUTING. Route the pair's CENTRELINE
    once, then generate both traces from it at -d and +d. Constant gap and
    mirrored bends are not something the router has to try to achieve, they fall
    out of the construction. Eagle's autorouter warns you off differential pairs
    because it models them as two independent nets and cannot hold a gap between
    two searches that do not know about each other -- that is a property of that
    router, not of differential pairs.

    The corner is a MITRE, not a fillet: the bisector is extended by d/cos(t/2)
    so the offset segments meet, which keeps the perpendicular distance exactly d
    on both sides of the bend. Capped at 4d so a hairpin cannot fly off.
    """
    if len(pts) < 2:
        return list(pts)
    norms = []
    for a, c in zip(pts, pts[1:]):
        dx, dy = c[0] - a[0], c[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        norms.append((-dy / L, dx / L))
    out = [(pts[0][0] + norms[0][0] * d, pts[0][1] + norms[0][1] * d)]
    for k in range(1, len(pts) - 1):
        n1, n2 = norms[k - 1], norms[k]
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        bl = math.hypot(bx, by)
        if bl < 1e-9:                      # doubles back on itself
            out.append((pts[k][0] + n1[0] * d, pts[k][1] + n1[1] * d))
            continue
        ux, uy = bx / bl, by / bl
        proj = ux * n1[0] + uy * n1[1]
        m = d / proj if abs(proj) > 1e-6 else d
        m = max(min(m, 4.0 * abs(d)), -4.0 * abs(d))
        out.append((pts[k][0] + ux * m, pts[k][1] + uy * m))
    out.append((pts[-1][0] + norms[-1][0] * d, pts[-1][1] + norms[-1][1] * d))
    return out


def polylen(pts):
    return sum(math.hypot(c[0] - a[0], c[1] - a[1]) for a, c in zip(pts, pts[1:]))


def find_pairs(names):
    """P/N partners, by the naming conventions Eagle and everyone else uses.

    EAGLE ONLY KNOWS _P/_N, and only when the two names are otherwise identical.
    This board's USB pair was USB_D+ / USB_D-, which Eagle does NOT pair: its
    router would have routed the one pair on the board that genuinely needs
    matched geometry as two ordinary nets, without a word, while warning loudly
    about the XADC analog inputs, which are sampled at 1 MSPS and do not care.
    The nets were renamed USB_D_P / USB_D_N on 2026-08-28 so that Eagle and this
    file agree, and so the pair can be routed and length-tuned in the GUI.

    The +/- and _p/_n and _H/_L forms are still accepted, because the naming is
    a convention rather than a rule and the next board may not follow it.
    """
    out = {}
    for n in names:
        for pos, neg in (("_P", "_N"), ("+", "-"), ("_p", "_n"), ("_H", "_L")):
            if n.endswith(pos) and n[:-len(pos)] + neg in names:
                out[n] = (n[:-len(pos)] + neg, +1)
                out[n[:-len(pos)] + neg] = (n, -1)
    return out
