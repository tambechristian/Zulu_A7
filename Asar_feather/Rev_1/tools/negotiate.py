"""Negotiated-congestion routing (PathFinder style) for a group of two-ended nets, used by router.py --negotiate.

Every net in the group is routed on the same window; nets may share cells, but a cell's cost grows with the number
of other nets whose footprint covers it ("present" cost, raised every iteration) and with how often it was
contested before ("history" cost). The present cost is capped at 50; iteration stops when no two footprints
overlap, or after 6 iterations without improvement. A net's footprint on a layer is
its NEW path cells (not those inside its own pads or stage-1 stubs, which are fixed and already legal) dilated by
width/2 + clearance/2 (+ half the raster allowance), so two footprints are disjoint exactly
when the centrelines keep width + clearance apart; a via's footprint covers every layer of its span with the larger
of land/2 + clearance/2 and half the hole-to-hole pitch. The board's own copper is a hard obstacle (router.Router
distance fields); only the group's paths negotiate. The result is committed through router.Router.commit, without
string pulling (pulled lines could cut into paths committed later), and must still pass route_check.py.
"""
import heapq
import math

import numpy as np

import router as R

STEPS = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142),
         (1, 1, 1.4142)]


def disk(r):
    c = int(math.ceil(r / R.G))
    return [(di, dj) for di in range(-c, c + 1) for dj in range(-c, c + 1) if (di * di + dj * dj) * R.G * R.G <= r * r]


def run(Rt, M, isl, nets, iters=40, log=print):
    B = Rt.B
    jobs = []
    boxes = []
    for n in nets:
        gs = isl[n]
        if len(gs) != 2:
            log('negotiate: %s has %d islands, skipped' % (n, len(gs)))
            continue
        jobs.append(n)
        boxes += [R.bbox(M, g) for g in gs]
    if not jobs:
        return [], list(nets)
    win = R.window(B, boxes, 1.5)
    i0, i1, j0, j1 = win
    h, w = i1 - i0, j1 - j0
    L = {l: k for k, l in enumerate(R.ROUTE)}
    occ = np.zeros((4, h, w), np.int16)
    hist = np.zeros((4, h, w), np.float32)
    info = {}
    for n in jobs:
        D = Rt.dist(n, win)
        free = np.zeros((4, h, w), bool)
        for l in R.ROUTE:
            free[L[l]] = D[l] >= R.width(n, l) / 2 + R.clearance(n, l) + R.MARGIN
        src = R.island_mask(B, M, isl[n][0], win)
        dst = R.island_mask(B, M, isl[n][1], win)
        tgt = np.zeros((4, h, w), bool)
        for l, m in dst.items():
            if l in L:
                tgt[L[l]] = m
        from scipy import ndimage
        anyt = tgt.any(axis=0)
        Hd = (ndimage.distance_transform_edt(~anyt) * R.G).astype(np.float32)
        own = np.zeros((h, w), bool)
        for m in src.values():
            own |= m
        mine = np.zeros((4, h, w), bool)              # the net's existing copper: not part of its footprint
        for d_ in (src, dst):
            for l, m in d_.items():
                if l in L:
                    mine[L[l]] |= m
        fp = {l: disk(R.width(n, l) / 2 + R.clearance(n, l) / 2 + R.MARGIN / 2) for l in R.ROUTE}
        info[n] = dict(D=D, free=free, src=src, tgt=tgt, Hd=Hd, own=own, mine=mine, fp=fp, path=None, cells=None)

    def paint(cells, d):
        for k, i, j in cells:
            occ[k, i, j] += d

    def footprint(n, path):
        out = set()
        mine = info[n]['mine']
        for l, x, y, kind in path:
            i, j = int(round(y / R.G)) - i0, int(round(x / R.G)) - j0
            if not kind and mine[L[l], i, j]:
                continue                               # still inside the net's own pad or stage-1 stub
            layers = [l]
            offs = info[n]['fp'][l]
            if kind:
                objs, occl, _ = R.VIAS[kind]
                layers = [q for q in occl if q in L]
                rv = max(max(o[2] for o in objs) / 2 + R.CLEAR / 2, (R.HOLE_HOLE + max(o[3] for o in objs)) / 2)
                offs = disk(rv + R.MARGIN / 2)
            for q in layers:
                k = L[q]
                for di, dj in offs:
                    a, b = i + di, j + dj
                    if 0 <= a < h and 0 <= b < w:
                        out.add((k, a, b))
        return out

    def astar(n, pres):
        I = info[n]
        free, tgt, Hd, D = I['free'], I['tgt'], I['Hd'], I['D']
        lc = Rt.layer_cost.get(n, {})
        mult = np.array([lc.get(l, 1.0) for l in R.ROUTE], np.float32)[:, None, None]
        cost = (1.0 + hist) * (1.0 + pres * occ) * mult      # per-net layer preference (router.py --layers)
        g = np.full((4, h, w), np.inf, np.float32)
        came = {}
        pq = []
        for l, m in I['src'].items():
            if l not in L:
                continue
            k = L[l]
            for i, j in np.argwhere(m & free[k]):
                g[k, i, j] = 0
                heapq.heappush(pq, (float(Hd[i, j]), 0.0, k, int(i), int(j)))
        pops = 0
        while pq:
            f, gc, k, i, j = heapq.heappop(pq)
            if gc > g[k, i, j]:
                continue
            pops += 1
            if pops > Rt.max_pops:
                return None
            if tgt[k, i, j]:
                return Rt._trace(came, (k, i, j), win)
            for di, dj, c in STEPS:
                ni, nj = i + di, j + dj
                if 0 <= ni < h and 0 <= nj < w and free[k, ni, nj]:
                    ng = gc + c * R.G * float(cost[k, ni, nj])
                    if ng < g[k, ni, nj]:
                        g[k, ni, nj] = ng
                        came[(k, ni, nj)] = (k, i, j, None)
                        heapq.heappush(pq, (ng + float(Hd[ni, nj]), ng, k, ni, nj))
            l = R.ROUTE[k]
            x, y = (j + j0) * R.G, (i + i0) * R.G
            for kind, (objs, occl, joins) in R.VIAS.items():
                if l not in joins:
                    continue
                for l2 in joins:
                    k2 = L[l2]
                    if l2 == l or not free[k2, i, j]:
                        continue
                    if kind == 'through' and I['own'][i, j]:
                        continue
                    vc = R.VIA_COST[kind] * max(float(cost[q, i, j]) for q in (k, k2))
                    ng = gc + vc
                    if ng < g[k2, i, j] and not Rt.recent_via(came, (k, i, j), x, y, win) and \
                            Rt.via_ok(n, kind, x, y, D, win):
                        g[k2, i, j] = ng
                        came[(k2, i, j)] = (k, i, j, kind)
                        heapq.heappush(pq, (ng + float(Hd[i, j]), ng, k2, i, j))
        return None

    pres = 0.5
    best, stale = None, 0
    for it in range(iters):
        for n in jobs:
            I = info[n]
            if I['cells']:
                paint(I['cells'], -1)
            p = astar(n, pres)
            I['path'] = p
            I['cells'] = footprint(n, p) if p else None
            if I['cells']:
                paint(I['cells'], +1)
        over = occ > 1
        nover = int(over.sum())
        unrouted = [n for n in jobs if not info[n]['path']]
        log('negotiate iteration %d: %d shared cells, %d nets without a path, present cost %.2f' % (
            it + 1, nover, len(unrouted), pres))
        if nover == 0:
            break
        score = (len(unrouted), nover)
        if best is None or score < best:
            best, stale = score, 0
        else:
            stale += 1
            if stale >= 6:
                log('negotiate: no improvement for 6 iterations, stopping')
                break
        hist[over] += 0.3
        pres = min(pres * 1.6, 50.0)                    # capped: an unbounded present cost starves the A* budget
    # nets whose footprint still overlaps another's are dropped (the later ones), so the rest is legal
    keep, drop = [], []
    taken = np.zeros((4, h, w), bool)
    for n in sorted(jobs, key=lambda n: len(info[n]['cells'] or ())):
        c = info[n]['cells']
        if not c:
            drop.append(n)
            continue
        idx = tuple(np.array(list(c)).T)
        if taken[idx].any():
            drop.append(n)
            continue
        taken[idx] = True
        keep.append(n)
    for n in keep:
        Rt.last = (Rt.dist(n, win), win)
        Rt.commit(n, info[n]['path'], None, pull=False)
    return keep, drop
