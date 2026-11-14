"""Systematic D10 site search ('d10_elsewhere'): 4-signal-layer maze (Top, L3, L4, Bottom) on a 0.025 mm grid with
the board's via types as layer transitions, run on the board WITH the 12-resistor plan (dfm_check FIXED) applied.

Topology searched: the D10 net is split by a 22 ohm R0201 (pad 1 = SDRAM-D10, pad 2 = D10) placed ANYWHERE in the
window on Top or Bottom (rot 0/90, 0.025 mm grid, legal pads, mask web, component clearance >= 0.254 mm).
  mode A  'sdvia' : the existing through via (38.5,14.5) and the whole L3 run stay on the U3 side (SDRAM-D10);
                    the U1 side is re-entered on the existing Top run at a junction J (Top run upstream of J removed).
  mode B  'u1via' : the via (38.5,14.5) and the whole Top run stay on the U1 side (D10); the U3 side leaves the L3
                    run at a junction J' (L3 run downstream of J' removed).
Layer transitions (all types already on the board):
  T23 Top>L2 + L2>L3 microvia 0.30/0.15 stacked; T34 L3>L4 buried 0.27/0.15; T45 L4>L5 + L5>Bottom microvia
  0.30/0.15 stacked; TH through 0.35/0.20.
Stage 1: multi-source Dijkstra (scipy csgraph) gives cost-to-go maps for each side; every legal R site is scored.
Stage 2: the best sites are routed for real (U1 side first, then U3 side with the first route as an obstacle).
Every result is only a candidate: design.py turns it into plan.json and dfm_check_d10.py proves it exactly.

    python maze.py [--top N]     -> maze_result.json (+ maze_candidates.json)
"""
import json, math, os, sys, time, collections
ARGV = list(sys.argv)
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import freemap as F
D = F.D

G = 0.025
X0, X1, Y0, Y1 = 36.5, 44.75, 10.0, 17.5
NX, NY = int(round((X1 - X0) / G)) + 1, int(round((Y1 - Y0) / G)) + 1
XS = X0 + np.arange(NX) * G
YS = Y0 + np.arange(NY) * G
XX, YY = np.meshgrid(XS, YS)
RL = ['Top', 'L3-SIG', 'L4-SIG', 'Bottom']
TRK_W = {'Top': 0.0762, 'L3-SIG': 0.125, 'L4-SIG': 0.125, 'Bottom': 0.10}
EPS = float(ARGV[ARGV.index("--eps") + 1]) if "--eps" in ARGV else 0.006          # raster safety margin; the exact checker decides
COMP_MIN = float(ARGV[ARGV.index("--comp") + 1]) if "--comp" in ARGV else 0.254
VIA_COST = 0.7       # mm-equivalent per via transition
TT = {'T23': (('Top', 'L2-GND', 'L3-SIG'), 0.15, 0.15), 'T34': (('L3-SIG', 'L4-SIG'), 0.135, 0.15),
      'T45': (('L4-SIG', 'L5-VCC3V3', 'Bottom'), 0.15, 0.15), 'TH': (tuple(D.CU), 0.175, 0.20)}
TT_LAYERS = {'T23': (0, 1), 'T34': (1, 2), 'T45': (2, 3), 'TH': (0, 3)}
RUN_TOP = [(38.5, 14.5), (39.9785, 14.5), (39.9785, 12.21), (40.9, 12.21), (40.95, 12.205), (41.2, 12.14),
           (41.6875, 12.15), (42.1501, 12.15), (42.4001, 11.8999)]
RUN_L3 = [(32.275, 16.025), (38.5, 14.5)]
VIA = (38.5, 14.5)


def gap(layer, other_net):
    return F.gap(layer, other_net, sdram=True)


def stamp_block(M, S, g):
    x0, y0, x1, y1 = D.bbox(S)
    i0, i1 = max(0, int((x0 - g - X0) / G) - 1), min(NX, int((x1 + g - X0) / G) + 2)
    j0, j1 = max(0, int((y0 - g - Y0) / G) - 1), min(NY, int((y1 + g - Y0) / G) + 2)
    if i0 >= i1 or j0 >= j1:
        return
    M[j0:j1, i0:i1] |= F.shape_dist(S, XX[j0:j1, i0:i1], YY[j0:j1, i0:i1]) < g


def blocked(obstacles, layer, r):
    M = np.zeros((NY, NX), bool)
    for o in obstacles:
        if o.layer != layer:
            continue
        if layer in D.PLANE and o.net == D.PLANE[layer]:
            continue
        stamp_block(M, o.shape, gap(layer, o.net) + r + EPS)
    return M


def hole_block(holes, span, hole):
    M = np.zeros((NY, NX), bool)
    for (x, y), h, sp in holes:
        if not (set(span) & sp):
            continue
        M |= np.hypot(XX - x, YY - y) < 0.24 + h / 2 + hole / 2 + EPS / 2
    return M


class Obj:
    """minimal stand-in for dfm objects (extra obstacles: the other side's D10 copper, routes, R pads)"""
    def __init__(s, layer, net, shape, kind='track', span=None, xy=None, hole=0.0):
        s.layer, s.net, s.shape, s.kind, s.span, s.xy, s.hole = layer, net, shape, kind, span, xy, hole


def seg_objs(pts, layer, net, w):
    return [Obj(layer, net, ('C', a[0], a[1], b[0], b[1], w / 2)) for a, b in zip(pts, pts[1:])]


def via_objs(xy, span, size, net, hole):
    return [Obj(L, net, ('C', xy[0], xy[1], xy[0], xy[1], size / 2), 'via', list(span), xy, hole) for L in span]


class Board:
    def __init__(s):
        s.objs, s.recs = F.plan_objs()
        s.base = [o for o in s.objs if o.net not in F.FAM]
        s.holes = [(o.xy, o.hole, set(o.span)) for o in s.objs if o.kind == 'via' and o.layer == o.span[0] and o.net not in F.FAM]
        s.holes += [((p['x'], p['y']), p['hole'], set(D.CU)) for p in s.recs[0] if p.get('hole', 0) > 0]
        t0 = time.time()
        s.trk = {L: blocked(s.base, L, TRK_W[L] / 2) for L in RL}
        s.land = {}
        for name, (span, r, hole) in TT.items():
            m = hole_block(s.holes, span, hole)
            for L in span:
                m = m | blocked(s.base, L, r)
            s.land[name] = m
        print('base masks %.1f s' % (time.time() - t0), flush=True)

    def masks(s, extra, extra_holes=()):
        """base masks + extra obstacle objects"""
        trk = {L: s.trk[L] | blocked(extra, L, TRK_W[L] / 2) for L in RL}
        land = {}
        for name, (span, r, hole) in TT.items():
            m = s.land[name].copy()
            for L in span:
                m |= blocked(extra, L, r)
            if extra_holes:
                m |= hole_block(extra_holes, span, hole)
            land[name] = m
        return trk, land


def nid(k, j, i):
    return (k * NY + j) * NX + i


def build_graph(trk, land, free_cells=()):
    """free_cells: (layer_idx, j, i) forced free (own-net copper such as the R pad centre)"""
    free = np.stack([~trk[L] for L in RL])
    for k, j, i in free_cells:
        free[k, j, i] = True
    rows, cols, wts = [], [], []
    for k in range(4):
        f = free[k]
        J1, I1 = np.nonzero(f)
        for dj, di, w in ((0, 1, G), (1, 0, G), (1, 1, G * math.sqrt(2)), (1, -1, G * math.sqrt(2))):
            j2, i2 = J1 + dj, I1 + di
            inb = (j2 >= 0) & (j2 < NY) & (i2 >= 0) & (i2 < NX)
            j1, i1, j2, i2 = J1[inb], I1[inb], j2[inb], i2[inb]
            ok = f[j2, i2]
            if di != 0 and dj != 0:                 # diagonal: no corner cutting
                ok = ok & f[j1, i2] & f[j2, i1]
            rows.append(nid(k, j1[ok], i1[ok])); cols.append(nid(k, j2[ok], i2[ok])); wts.append(np.full(ok.sum(), w))
    for name, (ka, kb) in TT_LAYERS.items():
        ok = ~land[name] & free[ka] & free[kb]
        jj, ii = np.nonzero(ok)
        rows.append(nid(ka, jj, ii)); cols.append(nid(kb, jj, ii)); wts.append(np.full(len(jj), VIA_COST))
    r = np.concatenate(rows); c = np.concatenate(cols); w = np.concatenate(wts)
    n = 4 * NY * NX
    A = coo_matrix((np.concatenate([w, w]), (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(n, n)).tocsr()
    return A, free


def cell(x, y):
    return int(round((y - Y0) / G)), int(round((x - X0) / G))


def poly_cells(pts, k, within=0.013):
    out = []
    for a, b in zip(pts, pts[1:]):
        m = F.shape_dist(('C', a[0], a[1], b[0], b[1], 0.0), XX, YY) <= within
        jj, ii = np.nonzero(m)
        out += [(k, j, i) for j, i in zip(jj, ii)]
    return out


def side_copper(mode, J=None):
    """fixed D10-family copper of each side (as obstacle objects for the OTHER side)"""
    via_all = via_objs(VIA, D.CU, 0.35, 'X', 0.2)
    l3 = seg_objs(RUN_L3, 'L3-SIG', 'X', 0.125)
    top = seg_objs(RUN_TOP, 'Top', 'X', 0.0762)
    if mode == 'A':
        return dict(sd=via_all + l3, u1=top)
    return dict(sd=l3, u1=via_all + top)


def r_sites(B, side, region):
    """legal R0201 sites: pads clear of every non-D10 object (exact), mask web >= 0.10 to other openings,
    component clearance >= 0.254 to same-side component boxes (dfm_check section 10 boxes)."""
    co = D.B['component_outlines']
    side_of = {c['ref']: c['side'] for c in D.B['components']}
    boxes = []
    for ref, v in co.items():
        if ref == 'X2' or side_of.get(ref) != side:
            continue
        bx = [v[k] for k in ('pads', 'Mech3', 'Mech4', 'Mech3(region)', 'Mech4(region)') if k in v]
        if ref == 'U3':
            m = D.B['u3']['body']['max']
            bx.append([m['x0'], m['y0'], m['x1'], m['y1']])
        if ref == 'U1':
            bx = [v['pads'], [41.4, 6.9, 51.4, 16.9]]
        boxes += [(ref, b) for b in bx]
    for pr in [p for p in json.load(open(os.path.join(F.D.HERE, 'dq_series_r_plan.json')))['parts'] if p['side'] == side]:
        xs = [pr['pad1']['x'], pr['pad2']['x']]; ys = [pr['pad1']['y'], pr['pad2']['y']]
        boxes.append((pr['ref'], [min(xs) - .15, min(ys) - .15, max(xs) + .15, max(ys) + .15]))
    pads_side = [o for o in B.objs if o.kind == 'pad' and o.layer == side]
    Gd = D.Grid([o for o in B.base if o.layer == side], 0.5)
    Gp = D.Grid(pads_side, 0.5)
    x0, x1, y0, y1 = region
    out = []
    for cx in np.arange(x0, x1 + 1e-9, G):
        for cy in np.arange(y0, y1 + 1e-9, G):
            for rot in (0, 90):
                dx, dy = (0.3, 0) if rot == 0 else (0, 0.3)
                ok = True
                worst = 9
                for px, py in ((cx - dx, cy - dy), (cx + dx, cy + dy)):
                    S = ('R', px, py, 0.15, 0.15)
                    for q in Gd.near(side, D.bbox(S), 0.3):
                        d = D.dist(S, q.shape) - 0.09
                        worst = min(worst, d)
                        if d < 0.003:
                            ok = False
                            break
                    if not ok:
                        break
                    Sm = ('R', px, py, 0.2, 0.2)
                    for q in Gp.near(side, D.bbox(Sm), 0.3):
                        if q.net in F.FAM:
                            continue
                        if D.dist(Sm, D.grow(q.shape, D.mask_exp(q))) < 0.10 + 0.002:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    continue
                bb = [cx - abs(dx) - .15, cy - abs(dy) - .15, cx + abs(dx) + .15, cy + abs(dy) + .15]
                body = [cx - 0.315, cy - 0.165, cx + 0.315, cy + 0.165] if rot == 0 else [cx - 0.165, cy - 0.315, cx + 0.165, cy + 0.315]
                cc = 9
                for ref, b in boxes:
                    for a in (bb, body):
                        ddx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
                        ddy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
                        cc = min(cc, math.hypot(ddx, ddy))
                if cc < COMP_MIN:
                    continue
                out.append(dict(side=side, x=round(float(cx), 4), y=round(float(cy), 4), rot=rot, cu_margin=round(worst, 4), comp_gap=round(cc, 4)))
    return out


def path_nodes(pred, src_node):
    """walk predecessors from src_node back to the Dijkstra source set"""
    out = [src_node]
    while pred[out[-1]] >= 0:
        out.append(int(pred[out[-1]]))
    return out


def decode(nodes):
    """node list -> per-layer polylines + via sites"""
    res = []
    for n in nodes:
        k, rem = divmod(n, NY * NX)
        j, i = divmod(rem, NX)
        res.append((k, round(float(XS[i]), 4), round(float(YS[j]), 4)))
    segs, vias = [], []
    cur = [res[0]]
    for a, b in zip(res, res[1:]):
        if a[0] == b[0]:
            cur.append(b)
        else:
            if len(cur) > 1:
                segs.append((RL[cur[0][0]], [(p[1], p[2]) for p in cur]))
            vias.append(((a[1], a[2]), RL[a[0]], RL[b[0]]))
            cur = [b]
    if len(cur) > 1:
        segs.append((RL[cur[0][0]], [(p[1], p[2]) for p in cur]))
    out = []
    for L, pts in segs:                      # merge collinear runs
        q = [pts[0]]
        for k in range(1, len(pts) - 1):
            ax, ay = pts[k][0] - q[-1][0], pts[k][1] - q[-1][1]
            bx, by = pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]
            if abs(ax * by - ay * bx) > 1e-9:
                q.append(pts[k])
        q.append(pts[-1])
        out.append((L, q))
    return out, vias


def via_kinds(a, b):
    ka, kb = sorted((RL.index(a), RL.index(b)))
    if (ka, kb) == (0, 3):
        return ['TH']
    m = {(0, 1): 'T23', (1, 2): 'T34', (2, 3): 'T45'}
    return [m[(ka, kb)]]


def route_objs(segs, vias, net):
    objs, holes = [], []
    for L, pts in segs:
        objs += seg_objs(pts, L, net, TRK_W[L])
    for xy, a, b in vias:
        for t in via_kinds(a, b):
            span, r, hole = TT[t]
            objs += via_objs(xy, span, 2 * r, net, hole)
            holes.append((xy, hole, set(span)))
    return objs, holes


def run_mode(B, mode, sites, ntop):
    sc = side_copper(mode)
    t0 = time.time()
    # ---- stage 1: cost-to-go maps
    trkU, landU = B.masks(sc['sd'])                           # U1 side must clear the SDRAM side's fixed copper
    if mode == 'A':
        srcU = poly_cells(RUN_TOP, 0)
    else:
        srcU = poly_cells(RUN_TOP, 0) + [(k,) + cell(*VIA) for k in range(4)]
    AU, freeU = build_graph(trkU, landU, srcU)
    dU = dijkstra(AU, indices=[nid(*c) for c in srcU], min_only=True)
    trkS, landS = B.masks(sc['u1'])
    if mode == 'A':
        srcS = [(k,) + cell(*VIA) for k in range(4)] + poly_cells(RUN_L3, 1)
    else:
        srcS = [c for c in poly_cells(RUN_L3, 1) if XS[c[2]] < 38.0]
    AS, freeS = build_graph(trkS, landS, srcS)
    dS = dijkstra(AS, indices=[nid(*c) for c in srcS], min_only=True)
    print('mode %s: stage-1 maps %.1f s' % (mode, time.time() - t0), flush=True)
    scored = []
    for s in sites:
        k = RL.index(s['side'])
        dx, dy = (0.3, 0) if s['rot'] == 0 else (0, 0.3)
        for flip in (0, 1):                                    # which pad is SDRAM
            p1 = (s['x'] - dx, s['y'] - dy) if flip == 0 else (s['x'] + dx, s['y'] + dy)
            p2 = (s['x'] + dx, s['y'] + dy) if flip == 0 else (s['x'] - dx, s['y'] - dy)
            j1, i1 = cell(*p1); j2, i2 = cell(*p2)
            if not (0 <= j1 < NY and 0 <= i1 < NX and 0 <= j2 < NY and 0 <= i2 < NX):
                continue
            c = dU[nid(k, j2, i2)] + dS[nid(k, j1, i1)]
            if np.isfinite(c):
                scored.append(dict(s, p1=p1, p2=p2, cost=round(float(c), 3), cU=round(float(dU[nid(k, j2, i2)]), 3),
                                   cS=round(float(dS[nid(k, j1, i1)]), 3)))
    scored.sort(key=lambda d: d['cost'])
    print('mode %s: %d of %d site/orientation pairs reachable from both sides' % (mode, len(scored), 2 * len(sites)), flush=True)
    # ---- stage 2: real sequential routing for the best distinct sites
    results = []
    seen = set()
    for s in scored:
        key = (round(s['x'] / 0.2), round(s['y'] / 0.2), s['side'])
        if key in seen:
            continue
        seen.add(key)
        if len(results) >= ntop:
            break
        k = RL.index(s['side'])
        pad1 = [Obj(s['side'], 'SDRAM-D10', ('R', s['p1'][0], s['p1'][1], 0.15, 0.15), 'pad')]
        pad2 = [Obj(s['side'], 'D10', ('R', s['p2'][0], s['p2'][1], 0.15, 0.15), 'pad')]
        n1 = nid(k, *cell(*s['p1']))
        n2 = nid(k, *cell(*s['p2']))
        done = None
        for order in ('U1first', 'SDfirst'):
            routes = {}
            ok = True
            seq = (('U1', sc['sd'] + pad1, srcU, s['p2'], n2, 'D10'), ('SD', sc['u1'] + pad2, srcS, s['p1'], n1, 'SDRAM-D10'))
            if order == 'SDfirst':
                seq = seq[::-1]
            extra, extra_h = [], []
            for name, obst, src, pxy, nn, net in seq:
                trk, land = B.masks(obst + extra, extra_h)
                A, _ = build_graph(trk, land, src + [(k,) + cell(*pxy)])
                d, pred, srcs = dijkstra(A, indices=[nid(*c) for c in src], min_only=True, return_predecessors=True)
                if not np.isfinite(d[nn]):
                    ok = False
                    why = '%s side unroutable (%s)' % (name, order)
                    break
                segs, vv = decode(path_nodes(pred, nn))
                routes[name] = dict(segs=segs, vias=vv, cost=round(float(d[nn]), 3))
                o, h = route_objs(segs, vv, net)
                extra += o
                extra_h += h
            if ok:
                done = (order, routes)
                break
        if not done:
            results.append(dict(site=s, ok=False, why=why))
            continue
        order, routes = done
        segU, viaU, segS, viaS = routes['U1']['segs'], routes['U1']['vias'], routes['SD']['segs'], routes['SD']['vias']
        results.append(dict(site=s, ok=True, mode=mode, order=order, u1=routes['U1'], sd=routes['SD'],
                            n_vias=len(viaU) + len(viaS)))
        print('  %s site %s (%.3f,%.3f) rot %d cost %.2f: U1 %d segs %d vias, SD %d segs %d vias' % (
            mode, s['side'], s['x'], s['y'], s['rot'], s['cost'], len(segU), len(viaU), len(segS), len(viaS)), flush=True)
    return scored, results


def main():
    ntop = int(ARGV[ARGV.index('--top') + 1]) if '--top' in ARGV else 8
    B = Board()
    sites = []
    for side in ('Bottom', 'Top'):
        t0 = time.time()
        ss = r_sites(B, side, (X0 + 0.5, X1 - 0.5, Y0 + 0.5, Y1 - 0.5))
        print('%s: %d legal R sites (%.0f s)' % (side, len(ss), time.time() - t0), flush=True)
        sites += ss
    out = dict(window=[X0, X1, Y0, Y1], grid=G, eps=EPS, via_cost=VIA_COST, n_sites=len(sites),
               sites_by_side=collections.Counter(s['side'] for s in sites))
    allres, allscored = [], {}
    for mode in ('A', 'B'):
        scored, res = run_mode(B, mode, sites, ntop)
        allscored[mode] = scored[:400]
        allres += res
    out['results'] = allres
    json.dump(out, open(os.path.join(HERE, 'maze_result.json'), 'w'), indent=1)
    json.dump(dict(sites=sites, scored=allscored), open(os.path.join(HERE, 'maze_candidates.json'), 'w'))


if __name__ == '__main__':
    main()
