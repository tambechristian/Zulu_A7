# -*- coding: utf-8 -*-
"""Widest-corridor finder on route_width's own raster (CELL 0.025) for one net on one layer.
(Written by the stage-3 "outer only" planner of 2026-09-16; promoted to a shared helper.)

    python corr.py NET LAYER x1 y1 x2 y2 [plan.json ...] [--min W]     widest path A -> B (maximin), simplified
    python corr.py NET via x0 x1 y0 y1 [plan.json ...]                  legal via sites in a window, by margin

wmax(cell) = 2 * (distance to the nearest cell within clearance of foreign copper): the widest centreline
track legal there, approximately (the exact number comes from Plan.run / segw.maxwidth afterwards).
"""
import heapq, io, json, math, os, sys
import numpy as np
from scipy import ndimage
TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools'
sys.path.insert(0, TOOLS)
import route_reach as rr
import route_width as rw
import hdi

RI = sys.argv[sys.argv.index('--inputs') + 1] if '--inputs' in sys.argv else os.path.join(TOOLS, 'route_inputs.json')


def load(plans=()):
    inp = json.load(io.open(RI, encoding='utf-8'))
    pl = [json.load(io.open(p, encoding='utf-8')) if isinstance(p, str) else p for p in plans]
    return rw.World(inp, pl)


def wmap(W, net, layer):
    b0 = W.blocked(net, layer, 0.0)
    d = ndimage.distance_transform_edt(~b0) * rr.CELL
    return 2.0 * d


def cell(W, x, y):
    return int(round((y - W.R.y0) / rr.CELL)), int(round((x - W.R.x0) / rr.CELL))


def xy(W, j, i):
    return W.R.x0 + i * rr.CELL, W.R.y0 + j * rr.CELL


def widest(W, net, layer, a, b, wm=None, wmin=0.0):
    """maximin path from a to b; returns (bottleneck width, list of (x,y) cells)"""
    if wm is None:
        wm = wmap(W, net, layer)
    ny, nx = wm.shape
    ja, ia = cell(W, *a); jb, ib = cell(W, *b)
    best = np.full(wm.shape, -1.0)
    prev = np.full(wm.shape, -1, np.int64)
    best[ja, ia] = wm[ja, ia]
    h = [(-wm[ja, ia], ja * nx + ia)]
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    while h:
        nw, k = heapq.heappop(h)
        nw = -nw
        j, i = divmod(k, nx)
        if nw < best[j, i]:
            continue
        if (j, i) == (jb, ib):
            break
        for dj, di in nb:
            jj, ii = j + dj, i + di
            if jj < 0 or ii < 0 or jj >= ny or ii >= nx:
                continue
            v = min(nw, wm[jj, ii])
            if v <= wmin:
                continue
            if v > best[jj, ii]:
                best[jj, ii] = v
                prev[jj, ii] = k
                heapq.heappush(h, (-v, jj * nx + ii))
    if best[jb, ib] < 0:
        return 0.0, []
    path = []
    k = jb * nx + ib
    while k >= 0:
        j, i = divmod(k, nx)
        path.append(xy(W, j, i))
        k = prev[j, i]
    path.reverse()
    return best[jb, ib], path


def via_ok_mask(W, net, span=hdi.THROUGH):
    """legal via cells for `net` for one via span (default through; route_width's per-span rasters)"""
    if span not in W.via_cov:
        raise SystemExit('route_width built no via raster for span %s: tools/hdi.json does not list it, or it joins fewer '
                         'than two signal layers (a plane tie, not a layer change)' % '/'.join(span))
    own = [o for o in W.objs if o['net'] == net]
    vc = {span: W.via_cov[span].copy()}
    tc = [np.zeros(vc[span].shape, np.int16) for _ in rr.LAYERS]
    rr.accumulate(W.R, own, -1, tc, vc, own_net=net, H=W.H)
    return (vc[span] <= 0) & ~W.edge_vs[span]


def widest2(W, net, a, b, la='Top', lb='Top', wmin=0.0, via_pen=0.0):
    """maximin path over Top and Bottom with layer changes at legal via cells; returns
    (bottleneck, [(layer, x, y), ...])"""
    wm = {'Top': wmap(W, net, 'Top'), 'Bottom': wmap(W, net, 'Bottom')}
    vok = via_ok_mask(W, net)
    # the net's own vias and through-hole pads join the layers wherever they stand -- a via only if
    # its span reaches both Top and Bottom (2026-09-29, HDI)
    joins = [o for o in W.objs if o['net'] == net and ((o.get('via') and 'Top' in o['layers'] and 'Bottom' in o['layers'])
                                                       or (o.get('pad') and len(o['layers']) == 4))]
    oc = rr.own_cells(W.R, joins)
    vok = vok | oc[0]
    ny, nx = vok.shape
    ja, ia = cell(W, *a); jb, ib = cell(W, *b)
    L = ('Top', 'Bottom')
    best = np.full((2, ny, nx), -1.0)
    prev = np.full((2, ny, nx), -1, np.int64)
    s0 = L.index(la); s1 = L.index(lb)
    best[s0, ja, ia] = wm[la][ja, ia]
    h = [(-best[s0, ja, ia], (s0 * ny + ja) * nx + ia)]
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    while h:
        nw, k = heapq.heappop(h)
        nw = -nw
        s, r = divmod(k, ny * nx)
        j, i = divmod(r, nx)
        if nw < best[s, j, i]:
            continue
        if (s, j, i) == (s1, jb, ib):
            break
        for dj, di in nb:
            jj, ii = j + dj, i + di
            if jj < 0 or ii < 0 or jj >= ny or ii >= nx:
                continue
            v = min(nw, wm[L[s]][jj, ii])
            if v <= wmin:
                continue
            if v > best[s, jj, ii]:
                best[s, jj, ii] = v
                prev[s, jj, ii] = k
                heapq.heappush(h, (-v, (s * ny + jj) * nx + ii))
        if vok[j, i]:
            t = 1 - s
            v = min(nw, wm[L[t]][j, i]) - via_pen
            if v > best[t, j, i]:
                best[t, j, i] = v
                prev[t, j, i] = k
                heapq.heappush(h, (-v, (t * ny + j) * nx + i))
    if best[s1, jb, ib] < 0:
        return 0.0, []
    path = []
    k = (s1 * ny + jb) * nx + ib
    while k >= 0:
        s, r = divmod(k, ny * nx)
        j, i = divmod(r, nx)
        x, y = xy(W, j, i)
        path.append((L[s], x, y))
        k = prev[s, j, i]
    path.reverse()
    return best[s1, jb, ib], path


def simplify(path, tol=0.05):
    if len(path) < 3:
        return list(path)
    def rdp(pts):
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        dm, im = -1, 0
        for k in range(1, len(pts) - 1):
            px, py = pts[k]
            d = abs(dx * (y1 - py) - dy * (x1 - px)) / L if L else math.hypot(px - x1, py - y1)
            if d > dm:
                dm, im = d, k
        if dm > tol:
            return rdp(pts[:im + 1])[:-1] + rdp(pts[im:])
        return [pts[0], pts[-1]]
    return rdp(list(path))


def via_sites(W, net, x0, x1, y0, y1, margin=0.0, span=hdi.THROUGH):
    """legal via cells in the window for `net` (own tracks do not block; own pads and vias do), with the
    distance (mm) to the nearest illegal cell as a margin, sorted by margin descending; `span` picks
    the via span (default through).  A via-in-pad cell -- the one cell accumulate() frees at an
    own-net pad centre on the span's outer layer -- is returned at the pad's EXACT centre, where
    route_emit demands the via (PAD_CENTRE 1 um); the raster cell can sit up to 0.0177 mm off it"""
    ok = via_ok_mask(W, net, span)
    d = ndimage.distance_transform_edt(ok) * rr.CELL
    j0, i0 = cell(W, x0, y0); j1, i1 = cell(W, x1, y1)
    centres = []
    if W.H.via_in_pad(span):
        centres = [(o['x'], o['y']) for o in W.objs
                   if o.get('pad') and o['net'] == net and len(o['layers']) == 1 and o['layers'][0] in W.H.outer(span)]
    out = []
    snapped = set()
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            if ok[j, i] and d[j, i] >= margin:
                x, y = xy(W, j, i)
                for cx, cy in centres:
                    if abs(cx - x) <= rr.CELL * 0.75 and abs(cy - y) <= rr.CELL * 0.75:
                        if (cx, cy) in snapped:       # a centre near a cell boundary frees two cells: one site
                            x = None
                        else:
                            snapped.add((cx, cy))
                            x, y = cx, cy
                        break
                if x is not None:
                    out.append((d[j, i], x, y))
    out.sort(reverse=True)
    return out


def main():
    a = sys.argv[1:]
    if '--inputs' in a:
        k = a.index('--inputs'); del a[k:k + 2]
    plans = [p for p in a if p.endswith('.json')]
    a = [p for p in a if not p.endswith('.json')]
    wmin = 0.0
    if '--min' in a:
        wmin = float(a[a.index('--min') + 1]); k = a.index('--min'); del a[k:k + 2]
    net = a[0]
    W = load(plans)
    if a[1] == 'via':
        x0, x1, y0, y1 = [float(v) for v in a[2:6]]
        s = via_sites(W, net, x0, x1, y0, y1)
        print('%d legal via cells; best by margin:' % len(s))
        for m, x, y in s[:25]:
            print('  margin %.3f  (%.3f, %.3f)' % (m, x, y))
        return
    layer = a[1]
    x1, y1, x2, y2 = [float(v) for v in a[2:6]]
    if layer == 'both':
        la = a[6] if len(a) > 6 else 'Top'; lb = a[7] if len(a) > 7 else 'Top'
        w, path = widest2(W, net, (x1, y1), (x2, y2), la, lb, wmin)
        print('%s Top+Bottom (%s %.2f,%.2f)->(%s %.2f,%.2f): bottleneck %.3f mm, %d cells' % (net, la, x1, y1, lb, x2, y2, w, len(path)))
        # split into per-layer runs and simplify each
        runs = []
        for (l, x, y) in path:
            if runs and runs[-1][0] == l:
                runs[-1][1].append((x, y))
            else:
                runs.append((l, [(x, y)]))
        for l, pts in runs:
            sp = simplify(pts, 0.06)
            print(' %s run, %d pts:' % (l, len(pts)))
            for (px, py) in sp:
                print('    (%.3f, %.3f)' % (px, py))
        return
    wm = wmap(W, net, layer)
    w, path = widest(W, net, layer, (x1, y1), (x2, y2), wm, wmin)
    print('%s %s (%.2f,%.2f)->(%.2f,%.2f): bottleneck %.3f mm, %d cells' % (net, layer, x1, y1, x2, y2, w, len(path)))
    if not path:
        return
    sp = simplify(path, 0.06)
    print('simplified (%d pts):' % len(sp))
    for (px, py) in sp:
        j, i = cell(W, px, py)
        print('  (%.3f, %.3f)  wmax %.3f' % (px, py, wm[j, i]))
    # per-segment min along the raw path
    k0 = 0
    for q in range(1, len(sp)):
        # find raw index of sp[q]
        k1 = next(k for k in range(k0, len(path)) if abs(path[k][0] - sp[q][0]) < 1e-6 and abs(path[k][1] - sp[q][1]) < 1e-6)
        seg = path[k0:k1 + 1]
        mn = min(wm[cell(W, px, py)] for px, py in seg)
        print('  seg %d: (%.3f,%.3f)-(%.3f,%.3f) raw-min %.3f' % (q, sp[q - 1][0], sp[q - 1][1], sp[q][0], sp[q][1], mn))
        k0 = k1


if __name__ == '__main__':
    main()
