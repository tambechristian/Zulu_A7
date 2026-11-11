"""Exact reachability per U1 ball (2026-10-28): flood the router's free cells from the ball's island (its stub, or
the bare pad for an unconnected ball), crossing layers wherever the router's own via test passes, with the ball's
net stripped to the stub and everything else fixed. For every single-ball net, says whether the net's far-end pads
are touched by the flood. A swap X:a->b can only work if reach[b] holds X and reach[a] holds b's net;
swap_eval.py --reach takes the output and tries only those (pairs, and rotations through a spare ball).

    python tools/swap_reach.py <model.json> <plan.json> <stage1_model.json> --out reach.json [--procs 16]

Every A* search for an open connection ends by exhausting its pocket, never its budget (2026-10-28 probes), so
this flood is the exact test of what the current copper allows, in seconds per ball instead of minutes."""
import argparse
import itertools
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import router as R  # noqa: E402
import route_conn as C  # noqa: E402
import swap_eval as E  # noqa: E402
import swap_rules as W  # noqa: E402
from diagnose_open import with_plan  # noqa: E402

G = {}


def init(model, plan, stage1):
    M = json.load(open(model))
    P = json.load(open(plan))
    Mx = with_plan(M, P)
    G['Mx'] = Mx
    G['fan'] = E.fanout(json.load(open(stage1)))
    G['opens'] = C.open_count(C.islands(Mx))
    u1 = {}
    for p in Mx['pads']:
        if p['ref'] == 'U1' and p['net']:
            u1.setdefault(p['net'], []).append(p['pad'])
    G['u1'] = u1
    # far-end pad cells per net (nets with one U1 ball): pad cells dilated by what a track needs to touch them
    H = int(np.ceil(Mx['board']['h'] / R.G)) + 1
    Wd = int(np.ceil(Mx['board']['w'] / R.G)) + 1
    far = {}
    for n, balls in u1.items():
        if len(balls) != 1 or W.kind(n) == 'fixed' or n in W.POWER:
            continue
        cells = {}
        for p in Mx['pads']:
            if p['net'] != n or p['ref'] == 'U1':
                continue
            layers = p['layers'] if p['layers'] else (R.STACK if p['drill'] > 0 else [])
            grow = R.width(n, 'Top Layer') / 2 + R.CLEAR + R.MARGIN + R.INFL + R.G
            r = min(p['w'], p['h']) / 2 + grow
            for l in layers:
                if l not in R.ROUTE:
                    continue
                i0, j0 = max(0, int((p['y'] - r) / R.G)), max(0, int((p['x'] - r) / R.G))
                i1, j1 = min(H - 1, int((p['y'] + r) / R.G) + 1), min(Wd - 1, int((p['x'] + r) / R.G) + 1)
                yy, xx = np.mgrid[i0:i1 + 1, j0:j1 + 1]
                if C.pad_round(p):
                    m = (xx * R.G - p['x']) ** 2 + (yy * R.G - p['y']) ** 2 <= r * r
                else:
                    m = (abs(xx * R.G - p['x']) <= p['w'] / 2 + grow) & (abs(yy * R.G - p['y']) <= p['h'] / 2 + grow)
                a = cells.setdefault(l, ([], []))
                a[0].append(yy[m])
                a[1].append(xx[m])
        far[n] = {l: (np.concatenate(v[0]), np.concatenate(v[1])) for l, v in cells.items()}
    G['far'] = far


def flood(ball):
    Mx, fan = G['Mx'], G['fan']
    pad = next(p for p in Mx['pads'] if p['ref'] == 'U1' and p['pad'] == ball)
    nb = pad['net']
    if nb:
        Ms, _ = E.swapped(Mx, fan, [(ball, ball)])
        net = nb
    else:
        Ms = dict(Mx)
        Ms['pads'] = [dict(p) for p in Mx['pads']]
        for p in Ms['pads']:
            if p['ref'] == 'U1' and p['pad'] == ball:
                p['net'] = 'PROBE'
        net = 'PROBE'
    B = R.Board(Ms)
    Rt = R.Router(B, 1)
    win = (0, B.H, 0, B.W)
    Dd = Rt.dist(net, win)
    free = {l: Dd[l] >= R.width(net, l) / 2 + R.MARGIN for l in R.ROUTE}
    via = {}
    for kind, (objs, occ, joins) in R.VIAS.items():
        land = max(o[2] for o in objs) / 2
        ok = np.ones((B.H, B.W), bool)
        for l in occ:
            ok &= Dd[l] >= land + R.MARGIN
        hole = max(o[3] for o in objs) / 2

        def block(x, y, r):
            i0, j0 = max(0, int((y - r) / R.G)), max(0, int((x - r) / R.G))
            i1, j1 = min(B.H - 1, int((y + r) / R.G) + 1), min(B.W - 1, int((x + r) / R.G) + 1)
            yy, xx = np.mgrid[i0:i1 + 1, j0:j1 + 1]
            d2 = (xx * R.G - x) ** 2 + (yy * R.G - y) ** 2
            ok[i0:i1 + 1, j0:j1 + 1] &= ~((d2 < r * r) & (d2 > 1e-12))
        for vx, vy, vh, vspan, vnet in B.vias:
            if vspan & set(occ):
                block(vx, vy, R.HOLE_HOLE + hole + vh / 2 + 0.005)
        for hx, hy, hd in B.holes:
            block(hx, hy, R.HOLE_HOLE + hole + hd / 2)
        via[kind] = ok
    isl = C.islands(Ms)[net]
    g = next(g for g in isl if any(Ms['pads'][i]['ref'] == 'U1' and Ms['pads'][i]['pad'] == ball for i in g['pads']))
    src = R.island_mask(B, Ms, g, win)
    lab, nlab = {}, {}
    for l in R.ROUTE:
        lab[l], nlab[l] = ndimage.label(free[l], structure=np.ones((3, 3)))
    parent = {}

    def find(a):
        while parent.get(a, a) != a:
            parent[a] = parent.get(parent[a], parent[a])
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    for kind, (objs, occ, joins) in R.VIAS.items():
        for la, lb in itertools.combinations(joins, 2):
            m = via[kind] & free[la] & free[lb]
            if not m.any():
                continue
            pairs = np.unique(np.stack([lab[la][m], lab[lb][m]], 1), axis=0)
            for a, b in pairs:
                union((la, int(a)), (lb, int(b)))
    roots = set()
    for l, m in src.items():
        if l in free:
            for lb in np.unique(lab[l][m & free[l]]):
                if lb:
                    roots.add(find((l, int(lb))))
    reached = {}
    for l in R.ROUTE:
        good = np.array([k for k in range(1, nlab[l] + 1) if find((l, k)) in roots], int)
        reached[l] = np.isin(lab[l], good) if len(good) else np.zeros_like(free[l])
    out = []
    for n, fm in G['far'].items():
        if any(reached[l][ii, jj].any() for l, (ii, jj) in fm.items()):
            out.append(n)
    return ball, nb, {l: int(reached[l].sum()) for l in R.ROUTE}, sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model')
    ap.add_argument('plan')
    ap.add_argument('stage1')
    ap.add_argument('--out', required=True)
    ap.add_argument('--procs', type=int, default=16)
    a = ap.parse_args()
    init(a.model, a.plan, a.stage1)
    Mx, opens, u1 = G['Mx'], G['opens'], G['u1']
    balls = []
    for p in Mx['pads']:
        if p['ref'] != 'U1':
            continue
        n = p['net']
        if not n:
            if W.BALLS.get(p['pad'], {}).get('type') == 'HR' and W.BALLS[p['pad']]['bank'] in W.HR_BANKS:
                balls.append(p['pad'])
        elif W.kind(n) != 'fixed' and n not in W.POWER and len(u1[n]) == 1:
            balls.append(p['pad'])
    print('%d balls to flood, %d far-end nets' % (len(balls), len(G['far'])), flush=True)
    res = {}
    with Pool(a.procs, initializer=init, initargs=(a.model, a.plan, a.stage1)) as pool:
        for ball, nb, cells, reach in pool.imap_unordered(flood, balls, chunksize=1):
            res[ball] = {'net': nb, 'cells': cells, 'reach': reach}
            print('%-4s %-14s cells %-70s reaches %d: %s' % (ball, nb or '-', cells, len(reach), ' '.join(reach)),
                  flush=True)
            json.dump(res, open(a.out, 'w'), indent=1)
    print('\nCANDIDATE SWAPS (X on a -> b, b has Y -> a):')
    for X in sorted(n for n in opens if opens[n] > 0):
        if X not in u1 or len(u1[X]) != 1 or W.kind(X) == 'fixed' or X in W.POWER:
            continue
        a = u1[X][0]
        base = X in res.get(a, {}).get('reach', [])
        cands = []
        for b, r in res.items():
            if b == a or X not in r['reach'] or not W.legal(X, b):
                continue
            Y = r['net']
            if Y and (W.kind(Y) == 'fixed' or not W.legal(Y, a) or Y not in res.get(a, {}).get('reach', [])):
                continue
            cands.append('%s(%s)' % (b, Y or '-'))
        print('  %-14s on %-4s own ball reaches it: %-5s  candidates: %s' % (X, a, base, ' '.join(cands) or 'NONE'))


if __name__ == '__main__':
    main()
