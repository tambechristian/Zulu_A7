"""Exact blocker report: the region a new track centreline (net, width) can reach on one layer from a seed, and the
objects that bound it (each boundary cell -> the obstacle with the smallest dist - (gap + w/2))."""
import sys, json, math, collections
import numpy as np
from scipy import ndimage
import engine as G
C = G.C

def report(c, layer, net, w, seed, box, title):
    R = G.Router(c, layer, net, w, box, guard=0.0)
    lab, n = ndimage.label(R.free, structure=np.ones((3, 3)))
    i, j = R.cell(*seed)
    if not R.free[j, i]:
        # nearest free cell to seed
        fj, fi = np.nonzero(R.free)
        k = np.argmin((fi - i) ** 2 + (fj - j) ** 2)
        i, j = fi[k], fj[k]
    comp = lab == lab[j, i]
    area = comp.sum() * G.GRID ** 2
    ys, xs = np.nonzero(comp)
    bb = (round(R.xs[xs.min()], 3), round(R.ys[ys.min()], 3), round(R.xs[xs.max()], 3), round(R.ys[ys.max()], 3))
    border = ndimage.binary_dilation(comp, structure=np.ones((3, 3))) & ~comp
    cnt = collections.Counter()
    an = G.NO(net)
    objs = []
    for q in c.W.grid.near(layer, box, 0.8):
        if q.uid in c.removed:
            continue
        qn = c.net_of(q)
        if qn == net:
            continue
        objs.append((q.tag + ' [' + str(qn) + ']', q.shape, C.gap_rule(an, G.NO(qn, q.ref), layer)))
    for a in c.new:
        if a['layer'] == layer and a['net'] != net:
            objs.append((G.desc(a), a['shape'], C.gap_rule(an, G.NO(a['net'], a.get('ref')), layer)))
    by, bx = np.nonzero(border)
    for yy, xx in zip(by, bx):
        x, y = R.xs[xx], R.ys[yy]
        P = ('C', x, y, x, y, w / 2)
        best = min(objs, key=lambda o: C.dist(P, o[1]) - o[2] - G.DESIGN_MARGIN)
        cnt[best[0]] += 1
    out = dict(title=title, layer=layer, net=net, width=w, seed=seed, reach_area_mm2=round(area, 3), reach_bbox=bb,
               boundary_objects=[(k, round(v * G.GRID, 2)) for k, v in cnt.most_common(14)])
    return out, comp, R

if __name__ == '__main__':
    pass
