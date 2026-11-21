"""u1_end candidate engine for R132 (D13), R133 (D14), R134 (D15).

Base = board_extract.json + dq_series_r_plan.json (13-R plan, md5 f2949630) applied by this folder's copy of
d10/fold/check.py.  Everything here is a PRE-FILTER / generator: a candidate is called legal only after
check.py has run on (13-R plan + candidate) -- see fullcheck.py.

Families (R = 22 ohm R0201; pad 1 = SDRAM-Dn (U3 side), pad 2 = Dn (U1 side)):
  F1   Top R between the second through via V2 and U1's ball: the Top run V2->ball is removed; pad 1 is routed on
       Top to V2 (V2 and everything west of it become SDRAM-Dn), pad 2 is routed on Top to the ball.
  F2a  Top R, V2 removed, pad 1 carries a via-in-pad column Top>L2>L3(>L4 buried) down to the inner layer and the
       inner run is re-attached to it (last inner segment truncated + routed); pad 2 routed on Top to the ball.
  F2b  as F2a but V2 and the Top run are kept (Dn); pad 2 is routed on Top to V2/the Top run; the inner run is
       cut away from V2.
  F3T  Top R over the last inner segment: columns in BOTH pads; the inner run is cut between them; V2 and the Top
       run stay Dn.
  F3B  same from the Bottom: Bottom>L5>L4(>L3 buried) columns.
  F4   Bottom R near V2: column in pad 1 (Bottom>L5>L4(>L3)), inner run cut away from V2 and routed to it; pad 2
       routed on Bottom to V2 (Dn), V2 + Top run kept.
"""
import json, math, os, sys, collections, heapq, copy, hashlib
import numpy as np
import ulib
C = ulib.C
B = C.B
CU = C.CU
HERE = ulib.HERE
EMIT = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG',
        'L5-VCC3V3': 'L5-VCC3V3'}
REF = {13: 'R132', 14: 'R133', 15: 'R134'}
SDRAM_ALL = C.SDRAM | C.SDRAM_NEW
W_OUTER = 0.0762      # Top: Width_SDRAM Top pref/min
W_BOT = 0.10          # Bottom: Width_SDRAM Bottom min
W_INNER = 0.125       # L3/L4: Width_SDRAM pref (impedance width); 0.10 is the minimum, tried as a fallback

# --------------------------------------------------------------------------- base board (13-R plan applied)
E13 = C.load_plan()
PADS, TRACKS, VIAS, _nf, _err = C.apply(E13)
assert not _err
TRACKS = [t for t in TRACKS if t is not None]
VIAS = [v for v in VIAS if v is not None]
ORIG_T = {(t['layer'], t['net'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4)) for t in B['tracks'] if t['layer'] in CU}


def poly_of(net):
    return NETS[net]


NETS = {
    13: dict(inner='L3-SIG', pin='50', ball='H1', v1=(35.625, 16.65), v2=(40.6, 12.75), ballxy=(41.9, 12.8999), first_to=2,
             poly=[(35.625, 16.65), (36.275, 16.025), (38.65, 15.3), (38.8, 15.15), (38.85, 15.05), (38.85, 14.5), (40.6, 12.75)],
             last_from=4),  # F3 cut zone: vertices index >= last_from (segments (38.85,15.05)->(38.85,14.5)->V2)
    14: dict(inner='L4-SIG', pin='51', ball='A14', v1=(36.125, 16.65), v2=(47.9, 17.15), ballxy=(48.4001, 16.4), first_to=2,
             poly=[(36.125, 16.65), (36.725, 17.25), (38.0, 17.25), (47.9, 17.15)], last_from=2),
    15: dict(inner='L4-SIG', pin='53', ball='A15', v1=(38.35, 16.725), v2=(48.9, 16.8), ballxy=(48.9, 16.4), first_to=1,
             poly=[(38.35, 16.725), (48.9, 16.8)], last_from=0),
}


def is_fam(net, n):
    return net in ('D%d' % n, 'SDRAM-D%d' % n)


def fam_records(n):
    nm = 'D%d' % n
    return ([t for t in TRACKS if t['net'] == nm], [v for v in VIAS if v['net'] == nm], [p for p in PADS if p['net'] == nm])


def same(a, b, tol=2e-3):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


# --------------------------------------------------------------------------- static obstacle objects (non-family)
def build_static():
    objs = C.build_objs(PADS, TRACKS, VIAS, set())
    return objs


STATIC = build_static()


class SGrid:
    """layer-bucketed spatial index of O objects"""
    def __init__(s, objs, cell=0.5):
        s.c = cell
        s.G = collections.defaultdict(list)
        for o in objs:
            s.add(o)

    def add(s, o):
        x0, y0, x1, y1 = C.bbox(o.shape)
        c = s.c
        for gx in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for gy in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                s.G[(o.layer, gx, gy)].append(o)

    def near(s, layer, bb, pad=0.3):
        x0, y0, x1, y1 = bb
        seen = set()
        c = s.c
        for gx in range(int(math.floor((x0 - pad) / c)), int(math.floor((x1 + pad) / c)) + 1):
            for gy in range(int(math.floor((y0 - pad) / c)), int(math.floor((y1 + pad) / c)) + 1):
                for q in s.G.get((layer, gx, gy), ()):
                    if id(q) not in seen:
                        seen.add(id(q))
                        yield q


SG = SGrid(STATIC)   # everything; the current family is excluded per call with an ignore predicate


def gap_nets(na, nb, L, ra=None, rb=None):
    g = 0.09
    if L in ('L3-SIG', 'L4-SIG'):
        if na in SDRAM_ALL or nb in SDRAM_ALL:
            g = 0.10
        if na == 'SDRAM-CLK' or nb == 'SDRAM-CLK':
            g = 0.20
    if 'X1' in (ra, rb) and L == 'L5-VCC3V3' and 'VCC3V3' in (na, nb):
        g = 0.10
    return g


# drills (for hole-to-hole) of the static board
def drills_static():
    out = []
    for v in VIAS:
        out.append(((v['x'], v['y']), v['hole'], set(v['span']), v['net']))
    return out


DRILLS = drills_static()
DGRID = collections.defaultdict(list)
for d in DRILLS:
    DGRID[(int(d[0][0] / 0.5), int(d[0][1] / 0.5))].append(d)


def drills_near(x, y, r=1.0):
    out = []
    for gx in range(int((x - r) / 0.5) - 1, int((x + r) / 0.5) + 2):
        for gy in range(int((y - r) / 0.5) - 1, int((y + r) / 0.5) + 2):
            out += DGRID.get((gx, gy), [])
    return out


# --------------------------------------------------------------------------- raster helpers
RR = 0.025


class Win:
    def __init__(s, x0, y0, x1, y1):
        s.x0, s.y0 = math.floor(x0 / RR) * RR, math.floor(y0 / RR) * RR
        s.nx = int(round((x1 - s.x0) / RR)) + 1
        s.ny = int(round((y1 - s.y0) / RR)) + 1
        s.xs = s.x0 + np.arange(s.nx) * RR
        s.ys = s.y0 + np.arange(s.ny) * RR

    def ij(s, x, y):
        return int(round((x - s.x0) / RR)), int(round((y - s.y0) / RR))

    def xy(s, i, j):
        return s.x0 + i * RR, s.y0 + j * RR

    def bb(s):
        return (s.x0, s.y0, s.x0 + (s.nx - 1) * RR, s.y0 + (s.ny - 1) * RR)


def shape_dist_grid(W, S):
    """exact distance from every grid point to shape S (>=0, 0 inside)"""
    X, Y = np.meshgrid(W.xs, W.ys)   # [j, i]
    if S[0] == 'R':
        dx = np.maximum(np.abs(X - S[1]) - S[3], 0)
        dy = np.maximum(np.abs(Y - S[2]) - S[4], 0)
        return np.hypot(dx, dy)
    x1, y1, x2, y2, r = S[1:6]
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        d = np.hypot(X - x1, Y - y1)
    else:
        t = np.clip(((X - x1) * dx + (Y - y1) * dy) / L2, 0, 1)
        d = np.hypot(X - x1 - t * dx, Y - y1 - t * dy)
    return np.maximum(d - r, 0)


def stamp_block(W, M, S, thr):
    """M[j,i] |= dist(point, S) < thr (local window update)"""
    x0, y0, x1, y1 = C.bbox(S)
    i0 = max(0, int(math.floor((x0 - thr - W.x0) / RR)) - 1); i1 = min(W.nx, int(math.ceil((x1 + thr - W.x0) / RR)) + 2)
    j0 = max(0, int(math.floor((y0 - thr - W.y0) / RR)) - 1); j1 = min(W.ny, int(math.ceil((y1 + thr - W.y0) / RR)) + 2)
    if i0 >= i1 or j0 >= j1:
        return
    sub = Win.__new__(Win)
    sub.x0, sub.y0 = W.x0 + i0 * RR, W.y0 + j0 * RR
    sub.nx, sub.ny = i1 - i0, j1 - j0
    sub.xs = sub.x0 + np.arange(sub.nx) * RR
    sub.ys = sub.y0 + np.arange(sub.ny) * RR
    d = shape_dist_grid(sub, S)
    M[j0:j1, i0:i1] |= d < thr


def static_block(W, layer, net, extra_r, objs_extra=(), exclude=None):
    """grid of points where a disc of radius extra_r (centre at the point) would be closer than the clearance rule
    to any static (non-family) object on `layer`, or to objs_extra (other nets)."""
    M = np.zeros((W.ny, W.nx), bool)
    bb = W.bb()
    for q in SG.near(layer, bb, pad=0.6):
        if exclude and exclude(q):
            continue
        g = gap_nets(net, q.net, layer, None, q.ref)
        stamp_block(W, M, q.shape, g + extra_r)
    for q in objs_extra:
        if q.layer != layer or q.net == net:
            continue
        g = gap_nets(net, q.net, layer, None, q.ref)
        stamp_block(W, M, q.shape, g + extra_r)
    return M


# --------------------------------------------------------------------------- R pose helpers
def pad_xy(x, y, rot):
    d = {0: (-0.3, 0), 180: (0.3, 0), 90: (0, -0.3), 270: (0, 0.3)}[rot]
    return (x + d[0], y + d[1]), (x - d[0], y - d[1])


def pad_obj(side, net, xy, ref, pn):
    rec = dict(ref=ref, pad=pn, layer=side, net=net, x=xy[0], y=xy[1], w=0.3, h=0.3, shape='rect', hole=0.0, rot=0.0)
    return C.O('pad', side, net, ('R', xy[0], xy[1], 0.15, 0.15), rec, 'pad %s-%s' % (ref, pn), ('np', ref, pn), new=True,
               span=[side], xy=xy, ref=ref, pad=pn)


def column(side, inner, xy, net):
    """stacked via-in-pad column from the R side down to `inner` (list of via dicts, plan-style + span)"""
    if side == 'Top':
        chain = [('Top', 'L2-GND', 0.3), ('L2-GND', 'L3-SIG', 0.3)]
        if inner == 'L4-SIG':
            chain.append(('L3-SIG', 'L4-SIG', 0.27))
    else:
        chain = [('L5-VCC3V3', 'Bottom', 0.3), ('L4-SIG', 'L5-VCC3V3', 0.3)]
        if inner == 'L3-SIG':
            chain.append(('L3-SIG', 'L4-SIG', 0.27))
    out = []
    for a, b, sz in chain:
        s0, s1 = CU.index(a), CU.index(b)
        out.append(dict(net=net, x=xy[0], y=xy[1], size=sz, hole=0.15, span=CU[s0:s1 + 1], kind='micro' if sz >= 0.29 else 'buried'))
    return out


def via_objs(v, tagp='new'):
    return [C.O('via', L, v['net'], ('C', v['x'], v['y'], v['x'], v['y'], v['size'] / 2), v,
                'via %s (%.3f,%.3f) %s>%s d%.2f' % (v['net'], v['x'], v['y'], v['span'][0], v['span'][-1], v['size']),
                ('nv', id(v)), new=True, span=v['span'], hole=v['hole'], xy=(v['x'], v['y'])) for L in v['span']]


def track_obj(t):
    return C.O('track', t['layer'], t['net'], ('C', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), t,
               'track %s %s (%.3f,%.3f)-(%.3f,%.3f) w%.4f' % (t['layer'], t['net'], t['x1'], t['y1'], t['x2'], t['y2'], t['w']),
               ('nt', id(t)), new=True, w=t['w'])


# --------------------------------------------------------------------------- A* router (one layer, one net)
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def astar(blocked, start, goal_mask, max_nodes=400000):
    ny, nx = blocked.shape
    si, sj = start
    if not (0 <= si < nx and 0 <= sj < ny):
        return None
    INF = 1e18
    best = {}
    h = [(0.0, 0.0, si, sj, -1, None)]
    prev = {}
    gi = np.argwhere(goal_mask)
    if len(gi) == 0:
        return None
    gx, gy = gi[:, 1], gi[:, 0]
    # heuristic: distance to goal bbox (admissible)
    bx0, bx1, by0, by1 = gx.min(), gx.max(), gy.min(), gy.max()

    def hh(i, j):
        dx = max(bx0 - i, 0, i - bx1); dy = max(by0 - j, 0, j - by1)
        return math.hypot(dx, dy)
    n = 0
    while h:
        f, g, i, j, d, par = heapq.heappop(h)
        key = (i, j, d)
        if key in best:
            continue
        best[key] = g
        prev[key] = par
        if goal_mask[j, i]:
            path = []
            k = key
            while k is not None:
                path.append((k[0], k[1]))
                k = prev[k]
            return path[::-1]
        n += 1
        if n > max_nodes:
            return None
        for di, (dx, dy) in enumerate(DIRS):
            ni, nj = i + dx, j + dy
            if not (0 <= ni < nx and 0 <= nj < ny) or blocked[nj, ni]:
                continue
            step = 1.41421356 if dx and dy else 1.0
            ng = g + step + (0.0 if d in (-1, di) else 0.6)
            if (ni, nj, di) in best:
                continue
            heapq.heappush(h, (ng + hh(ni, nj), ng, ni, nj, di, key))
    return None


def seg_clear(layer, net, w, a, b, extra=(), ignore=None):
    """exact: capsule a-b of width w vs all static non-family objects + extra objects (other nets)"""
    S = ('C', a[0], a[1], b[0], b[1], w / 2)
    bb = C.bbox(S)
    for q in SG.near(layer, bb, pad=0.3):
        if q.net == net or (ignore and ignore(q)):
            continue
        if C.dist(S, q.shape) < gap_nets(net, q.net, layer, None, q.ref) - 1e-9:
            return False
    for q in extra:
        if q.layer != layer or q.net == net:
            continue
        if C.dist(S, q.shape) < gap_nets(net, q.net, layer, None, q.ref) - 1e-9:
            return False
    return True


def route(layer, net, w, start_xy, goal, W, extra=(), ignore=None, margin=0.004):
    """goal: dict(kind='point', xy, r) (end inside a round land / pad, track ends at its centre) or
    dict(kind='poly', pts, s_lo, s_hi) (end on the polyline; returns the attach parameter s).
    Returns (pts list, attach) or None."""
    blocked = static_block(W, layer, net, w / 2 + margin, extra, exclude=ignore)
    si, sj = W.ij(*start_xy)
    if not (0 <= si < W.nx and 0 <= sj < W.ny):
        return None
    # free the start cell's immediate area inside its own pad (pad copper is same-net)
    blocked[sj, si] = False
    G = np.zeros_like(blocked)
    X, Y = np.meshgrid(W.xs, W.ys)
    if goal['kind'] == 'point':
        gx, gy = goal['xy']
        G = np.hypot(X - gx, Y - gy) <= goal['r']
        G &= ~blocked | (np.hypot(X - gx, Y - gy) <= goal['r'])
        blocked = blocked & ~G
    else:
        pts = goal['pts']
        best = np.full(X.shape, 1e9)
        sacc = 0.0
        for k in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[k], pts[k + 1]
            L = math.hypot(x2 - x1, y2 - y1)
            t = np.clip(((X - x1) * (x2 - x1) + (Y - y1) * (y2 - y1)) / (L * L), 0, 1)
            d = np.hypot(X - x1 - t * (x2 - x1), Y - y1 - t * (y2 - y1))
            s = sacc + t * L
            ok = (d <= RR * 0.75) & (s >= goal['s_lo']) & (s <= goal['s_hi'])
            G |= ok
            sacc += L
        blocked = blocked & ~G
    path = astar(blocked, (si, sj), G)
    if path is None:
        return None
    pts = [start_xy] + [W.xy(i, j) for i, j in path[1:]]
    attach = None
    if goal['kind'] == 'point':
        pts.append(goal['xy'])
    else:
        ex, ey = pts[-1]
        attach = project_poly(goal['pts'], ex, ey)
        pts.append(attach[1])
    # string pulling with exact checks
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not seg_clear(layer, net, w, pts[i], pts[j], extra, ignore):
            j -= 1
        out.append(pts[j])
        i = j
    # drop zero-length
    o2 = [out[0]]
    for p in out[1:]:
        if math.hypot(p[0] - o2[-1][0], p[1] - o2[-1][1]) > 1e-6:
            o2.append(p)
    return o2, attach


def project_poly(pts, x, y):
    best = None
    sacc = 0.0
    for k in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[k], pts[k + 1]
        L = math.hypot(x2 - x1, y2 - y1)
        t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / (L * L)))
        px, py = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
        d = math.hypot(x - px, y - py)
        if best is None or d < best[0]:
            best = (d, (round(px, 4), round(py, 4)), sacc + t * L, k)
        sacc += L
    return best[2], best[1], best[3]


def poly_cut(pts, s):
    """polyline from start to arc-length s (returns vertex list) and from s to end"""
    out_a, out_b = [pts[0]], None
    sacc = 0.0
    for k in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[k], pts[k + 1]
        L = math.hypot(x2 - x1, y2 - y1)
        if sacc + L >= s - 1e-9:
            t = (s - sacc) / L
            p = (round(x1 + t * (x2 - x1), 4), round(y1 + t * (y2 - y1), 4))
            a = out_a + ([p] if math.hypot(p[0] - out_a[-1][0], p[1] - out_a[-1][1]) > 1e-6 else [])
            b = [p] + list(pts[k + 1:]) if math.hypot(p[0] - x2, p[1] - y2) > 1e-6 else list(pts[k + 1:])
            return a, b
        out_a.append(pts[k + 1])
        sacc += L
    return list(pts), [pts[-1]]


def poly_len(pts):
    return sum(math.hypot(pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1))
