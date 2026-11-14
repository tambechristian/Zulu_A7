"""Raster reachability (0.01 mm) of a track centreline of width W on one layer, from a seed, against every
other-net copper object grown by (rule gap + W/2).  Used to find where a feed/return can go; final legality is
always proven by check.py on exact geometry."""
import sys, math, json, collections
import numpy as np
from scipy import ndimage
import base
C = base.C
RES = 0.01

def objs_applied():
    E, pads, tracks, vias, nf = base.applied()
    return E, pads, tracks, vias, C.build_objs(pads, tracks, vias, nf)

def forbid(objs, layer, allow_nets, W, box, gap=0.09, extra_skip=lambda o: False):
    X0, Y0, X1, Y1 = box
    nx, ny = int(round((X1 - X0) / RES)), int(round((Y1 - Y0) / RES))
    m = np.zeros((ny, nx), bool)
    xs = X0 + (np.arange(nx) + 0.5) * RES
    ys = Y0 + (np.arange(ny) + 0.5) * RES
    for o in objs:
        if o.layer != layer or o.net in allow_nets or extra_skip(o):
            continue
        g = gap + W / 2
        bx = C.bbox(C.grow(o.shape, g))
        if bx[2] < X0 or bx[0] > X1 or bx[3] < Y0 or bx[1] > Y1:
            continue
        i0, i1 = max(0, int((bx[0] - X0) / RES) - 1), min(nx, int((bx[2] - X0) / RES) + 2)
        j0, j1 = max(0, int((bx[1] - Y0) / RES) - 1), min(ny, int((bx[3] - Y0) / RES) + 2)
        X, Y = np.meshgrid(xs[i0:i1], ys[j0:j1])
        S = o.shape
        if S[0] == 'R':
            dx = np.maximum(np.abs(X - S[1]) - S[3], 0); dy = np.maximum(np.abs(Y - S[2]) - S[4], 0)
            d = np.hypot(dx, dy)
        else:
            x1, y1, x2, y2, r = S[1:6]
            ddx, ddy = x2 - x1, y2 - y1; L2 = ddx * ddx + ddy * ddy
            t = np.clip(((X - x1) * ddx + (Y - y1) * ddy) / L2, 0, 1) if L2 > 0 else 0
            d = np.hypot(X - x1 - t * ddx, Y - y1 - t * ddy) - r
        m[j0:j1, i0:i1] |= d < g + 0.003     # 3 um raster guard
    return m, xs, ys
