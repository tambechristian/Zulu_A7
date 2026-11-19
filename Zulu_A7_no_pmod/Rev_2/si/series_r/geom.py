"""Small exact 2-D geometry kernel for design_bottom.py (no shapely on this machine).

Objects are dicts with 'kind' in {'rect','circ','seg'}:
  rect: g = (x0, y0, x1, y1)          axis-aligned copper rectangle (pads; rotations here are all 0/90/180/270)
  circ: g = (cx, cy, r)               via land / round pad
  seg : g = (x1, y1, x2, y2, r)       track = capsule of half-width r (Altium tracks have round ends)
dist(a, b) = edge-to-edge distance (0 when touching/overlapping).
"""
import math
import numpy as np


def _pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 <= 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _pt_rect(px, py, r):
    dx = max(r[0] - px, 0.0, px - r[2])
    dy = max(r[1] - py, 0.0, py - r[3])
    return math.hypot(dx, dy)


def _seg_cross(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b

    def orient(ax, ay, bx, by, cx, cy):
        v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)

    def on(ax, ay, bx, by, cx, cy):
        return min(ax, bx) - 1e-12 <= cx <= max(ax, bx) + 1e-12 and min(ay, by) - 1e-12 <= cy <= max(ay, by) + 1e-12
    o1, o2 = orient(x1, y1, x2, y2, x3, y3), orient(x1, y1, x2, y2, x4, y4)
    o3, o4 = orient(x3, y3, x4, y4, x1, y1), orient(x3, y3, x4, y4, x2, y2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on(x1, y1, x2, y2, x3, y3): return True
    if o2 == 0 and on(x1, y1, x2, y2, x4, y4): return True
    if o3 == 0 and on(x3, y3, x4, y4, x1, y1): return True
    if o4 == 0 and on(x3, y3, x4, y4, x2, y2): return True
    return False


def _seg_seg(a, b):
    if _seg_cross(a, b):
        return 0.0
    return min(_pt_seg(a[0], a[1], *b), _pt_seg(a[2], a[3], *b), _pt_seg(b[0], b[1], *a), _pt_seg(b[2], b[3], *a))


def _seg_rect(s, r):
    x1, y1, x2, y2 = s
    if _pt_rect(x1, y1, r) == 0 or _pt_rect(x2, y2, r) == 0:
        return 0.0
    edges = [(r[0], r[1], r[2], r[1]), (r[2], r[1], r[2], r[3]), (r[2], r[3], r[0], r[3]), (r[0], r[3], r[0], r[1])]
    return min(_seg_seg(s, e) for e in edges)


def core(o):
    k, g = o['kind'], o['g']
    if k == 'rect':
        return 'rect', tuple(g), 0.0
    if k == 'circ':
        return 'pt', (g[0], g[1]), g[2]
    return 'seg', tuple(g[:4]), g[4]


def dist(a, b):
    ka, ga, ra = core(a)
    kb, gb, rb = core(b)
    if ka > kb:
        ka, ga, kb, gb = kb, gb, ka, ga
    # order: 'pt' < 'rect' < 'seg'
    if ka == 'pt' and kb == 'pt':
        d = math.hypot(ga[0] - gb[0], ga[1] - gb[1])
    elif ka == 'pt' and kb == 'rect':
        d = _pt_rect(ga[0], ga[1], gb)
    elif ka == 'pt' and kb == 'seg':
        d = _pt_seg(ga[0], ga[1], *gb)
    elif ka == 'rect' and kb == 'rect':
        d = math.hypot(max(0.0, ga[0] - gb[2], gb[0] - ga[2]), max(0.0, ga[1] - gb[3], gb[1] - ga[3]))
    elif ka == 'rect' and kb == 'seg':
        d = _seg_rect(gb, ga)
    else:
        d = _seg_seg(ga, gb)
    return max(0.0, d - ra - rb)


def bbox(o):
    k, g = o['kind'], o['g']
    if k == 'rect':
        return g
    if k == 'circ':
        return (g[0] - g[2], g[1] - g[2], g[0] + g[2], g[1] + g[2])
    return (min(g[0], g[2]) - g[4], min(g[1], g[3]) - g[4], max(g[0], g[2]) + g[4], max(g[1], g[3]) + g[4])


# ---------- vectorised point distances (for the routing raster) ----------
def vd_rect(X, Y, r):
    dx = np.maximum(np.maximum(r[0] - X, 0.0), X - r[2])
    dy = np.maximum(np.maximum(r[1] - Y, 0.0), Y - r[3])
    return np.hypot(dx, dy)


def vd_seg(X, Y, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 <= 0:
        return np.hypot(X - x1, Y - y1)
    t = np.clip(((X - x1) * dx + (Y - y1) * dy) / L2, 0.0, 1.0)
    return np.hypot(X - (x1 + t * dx), Y - (y1 + t * dy))


def vdist(X, Y, o):
    k, g = o['kind'], o['g']
    if k == 'rect':
        return vd_rect(X, Y, g)
    if k == 'circ':
        return np.maximum(np.hypot(X - g[0], Y - g[1]) - g[2], 0.0)
    return np.maximum(vd_seg(X, Y, *g[:4]) - g[4], 0.0)
