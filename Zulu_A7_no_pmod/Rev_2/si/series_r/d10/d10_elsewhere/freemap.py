"""Raster free-space maps (0.01 mm) for new D10 copper, computed from EXACT distances to every foreign object of the
board with the 12-resistor plan (dfm_check FIXED) applied.  Used only to FIND candidates; every candidate that is
kept is re-proven by dfm_check_d10.py on exact geometry."""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = sys.argv[:1]
import dfm_base as D

RES = 0.01
X0, X1, Y0, Y1 = 35.0, 44.0, 10.5, 18.5
NX, NY = int(round((X1 - X0) / RES)), int(round((Y1 - Y0) / RES))
XS = X0 + (np.arange(NX) + 0.5) * RES
YS = Y0 + (np.arange(NY) + 0.5) * RES
FAM = {'D10', 'SDRAM-D10'}


def plan_objs():
    E = D.apply_fixes(D.load_plan())
    pads, tracks, vias, newflags, errors = D.apply(E)
    assert not errors
    return D.build_objs(pads, tracks, vias, newflags), (pads, tracks, vias)


def shape_dist(S, X, Y):
    if S[0] == 'R':
        dx = np.maximum(np.abs(X - S[1]) - S[3], 0)
        dy = np.maximum(np.abs(Y - S[2]) - S[4], 0)
        return np.hypot(dx, dy)
    x1, y1, x2, y2, r = S[1:6]
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return np.maximum(np.hypot(X - x1, Y - y1) - r, 0)
    t = np.clip(((X - x1) * dx + (Y - y1) * dy) / L2, 0, 1)
    return np.maximum(np.hypot(X - x1 - t * dx, Y - y1 - t * dy) - r, 0)


def gap(layer, other_net, sdram=True):
    g = 0.09
    if layer in ('L3-SIG', 'L4-SIG'):
        if sdram or other_net in D.SDRAM | D.SDRAM_NEW:
            g = 0.10
        if other_net == 'SDRAM-CLK':
            g = 0.20
    return g


def blocked(objs, layer, r, skip=lambda o: False, extra=0.0):
    """True where a disc/track-end of radius r centred there would violate clearance to a foreign object."""
    M = np.zeros((NY, NX), bool)
    for o in objs:
        if o.layer != layer or o.net in FAM or skip(o):
            continue
        if layer in D.PLANE and o.net == D.PLANE[layer]:
            continue                      # plane copper itself re-pours around new objects
        g = gap(layer, o.net) + r + extra
        x0, y0, x1, y1 = D.bbox(o.shape)
        i0, i1 = max(0, int((x0 - g - X0) / RES) - 1), min(NX, int((x1 + g - X0) / RES) + 2)
        j0, j1 = max(0, int((y0 - g - Y0) / RES) - 1), min(NY, int((y1 + g - Y0) / RES) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        Xg, Yg = np.meshgrid(XS[i0:i1], YS[j0:j1])
        M[j0:j1, i0:i1] |= shape_dist(o.shape, Xg, Yg) < g
    return M


def ij(x, y):
    return int((y - Y0) / RES), int((x - X0) / RES)
