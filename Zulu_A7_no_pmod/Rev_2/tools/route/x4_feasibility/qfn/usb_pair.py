"""usb_pair.py <model.json> <seed.json> <out.json> [x0 x1 y0 y1]

Top-only, via-free USB pair (0.15 mm tracks, 0.15 mm gap) from U2 pins 8 (D+) / 7 (D-) to X1 pins 3 / 2.
The pair is routed as ONE 0.45 mm wide centreline (A*, octilinear, Top Layer, fixed copper is a wall, seed copper is a
priced obstacle) and then offset +-0.15 mm. P stays on the left of the heading, which is why the pair must enter the
X1 pads from the U2 side (heading north), not from the board-edge side.
Writes {'tracks': [...], 'seed_conflicts': {...}} where the conflicts are the seed objects the pair envelope touches."""
import heapq
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..'))
import router as R  # noqa: E402

TOP = 'Top Layer'
W_TRK, GAP = 0.15, 0.15
OFF = (W_TRK + GAP) / 2          # centreline to track centre
ENV = OFF + W_TRK / 2            # half width of the pair envelope
S = 0.05                         # A* step, mm (2 router cells)
DIRS = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]   # (di, dj): W, NW.. in (y, x) cells
# direction index -> (dx, dy) in mm: index 0 is west (-x), 2 is -y, 4 is east, 6 is +y


def dxy(k):
    di, dj = DIRS[k]
    return dj, di


def load(model, seed):
    M = json.load(open(model))
    M['tracks'] = [t for t in M['tracks'] if t['net'] not in ('USB_D_P', 'USB_D_N')]
    M['vias'] = [v for v in M['vias'] if v['net'] not in ('USB_D_P', 'USB_D_N')]
    B = R.Board(M)
    Rt = R.Router(B)
    P = json.load(open(seed))
    Rt.out_t = [t for t in P['tracks'] if t['net'] not in ('USB_D_P', 'USB_D_N')]
    Rt.out_v = [v for v in P['vias'] if v['net'] not in ('USB_D_P', 'USB_D_N')]
    Rt.rip(set())
    return M, B, Rt, P


def masks(B, Rt, box):
    x0, x1, y0, y1 = box
    i0, i1 = int(y0 / R.G) // 2 * 2, int(math.ceil(y1 / R.G))
    j0, j1 = int(x0 / R.G) // 2 * 2, int(math.ceil(x1 / R.G))
    win = (i0, i1, j0, j1)
    need = ENV + R.MARGIN
    Df = Rt.dist('USB_D_P', win, base=True)[TOP]
    Da = Rt.dist('USB_D_P', win, base=False)[TOP]
    fixed_ok = (Df >= need)[::2, ::2]
    all_ok = (Da >= need)[::2, ::2]
    return win, fixed_ok, all_ok


def astar(win, fixed_ok, all_ok, start, goal, sdir, gdir, seed_cost, turn_cost, straight_min=3):
    """start/goal (x, y) mm on the 0.05 grid; returns the list of (x, y) vertices"""
    i0, _, j0, _ = win
    h, w = fixed_ok.shape

    def cell(x, y):
        return int(round(y / S)) - i0 // 2, int(round(x / S)) - j0 // 2
    si, sj = cell(*start)
    gi, gj = cell(*goal)
    open_ = [(0.0, 0.0, si, sj, sdir, 0)]
    best = {(si, sj, sdir): 0.0}
    came = {}
    pops = 0
    while open_:
        f, g, i, j, d, run = heapq.heappop(open_)
        if best.get((i, j, d), 1e9) < g - 1e-9:
            continue
        pops += 1
        if (i, j) == (gi, gj) and d == gdir:
            path = [(i, j, d)]
            while (path[-1][0], path[-1][1], path[-1][2]) in came:
                path.append(came[path[-1]])
            path.reverse()
            return [((p[1] + j0 // 2) * S, (p[0] + i0 // 2) * S) for p in path], pops
        for nd in (d, (d + 1) % 8, (d - 1) % 8):
            if nd != d and run < straight_min:
                continue                           # no tiny jogs: the previous leg must be long enough
            di, dj = DIRS[nd]
            ni, nj = i + di, j + dj
            if not (0 <= ni < h and 0 <= nj < w) or not fixed_ok[ni, nj]:
                continue
            step = S * (math.sqrt(2) if di and dj else 1.0)
            cost = step * (1.0 + (seed_cost if not all_ok[ni, nj] else 0.0)) + (turn_cost if nd != d else 0.0)
            ng = g + cost
            key = (ni, nj, nd)
            if ng < best.get(key, 1e9):
                best[key] = ng
                came[key] = (i, j, d)
                hh = math.hypot(gi - ni, gj - nj) * S
                heapq.heappush(open_, (ng + hh, ng, ni, nj, nd, 1 if nd != d else run + 1))
    return None, pops


def simplify(pts):
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        u = (round(b[0] - a[0], 4), round(b[1] - a[1], 4))
        v = (round(c[0] - b[0], 4), round(c[1] - b[1], 4))
        if abs(u[0] * v[1] - u[1] * v[0]) > 1e-6:
            out.append(b)
    out.append(pts[-1])
    return out


def offset(pts, d):
    """polyline offset by d to the left of the heading (mitred joins)"""
    nrm = []
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        nrm.append((-(b[1] - a[1]) / L, (b[0] - a[0]) / L))
    out = [(pts[0][0] + d * nrm[0][0], pts[0][1] + d * nrm[0][1])]
    for k in range(1, len(pts) - 1):
        n1, n2 = nrm[k - 1], nrm[k]
        s = 1 + n1[0] * n2[0] + n1[1] * n2[1]
        out.append((pts[k][0] + d * (n1[0] + n2[0]) / s, pts[k][1] + d * (n1[1] + n2[1]) / s))
    out.append((pts[-1][0] + d * nrm[-1][0], pts[-1][1] + d * nrm[-1][1]))
    return out


def plen(p):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(p, p[1:]))


def tracks(pts, net):
    return [{'net': net, 'layer': TOP, 'w': W_TRK, 'x1': round(a[0], 4), 'y1': round(a[1], 4),
             'x2': round(b[0], 4), 'y2': round(b[1], 4)} for a, b in zip(pts, pts[1:])
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-6]


def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def seg_seg(a, b, c, d):
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    if cr(a, b, c) * cr(a, b, d) < 0 and cr(c, d, a) * cr(c, d, b) < 0:
        return 0.0
    return min(seg_dist(a, c, d), seg_dist(b, c, d), seg_dist(c, a, b), seg_dist(d, a, b))


def conflicts(polys, P):
    """seed tracks / vias whose copper comes within clearance of the pair's tracks"""
    clr = R.CLEAR + R.MARGIN
    out_t, out_v = [], []
    segs = [s for p in polys for s in zip(p, p[1:])]
    for t in P['tracks']:
        if t['layer'] != TOP or t['net'] in ('USB_D_P', 'USB_D_N'):
            continue
        a, b = (t['x1'], t['y1']), (t['x2'], t['y2'])
        if min(seg_seg(a, b, s, e) for s, e in segs) < W_TRK / 2 + t['w'] / 2 + clr:
            out_t.append(t)
    for v in P['vias']:
        if v['net'] in ('USB_D_P', 'USB_D_N'):
            continue
        span = R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]
        if TOP not in span:
            continue
        if min(seg_dist((v['x'], v['y']), s, e) for s, e in segs) < W_TRK / 2 + v['size'] / 2 + clr:
            out_v.append(v)
    return out_t, out_v


def add_bumps(poly, need, away, ok, h=0.2, top=0.3, gap=0.2):
    """lengthen `poly` by `need` mm with trapezoid bumps (45 degree sides) on a straight leg, towards the side `away`
    (+1: left of the heading, -1: right). The longest leg whose bumps pass ok(polyline) is used."""
    per = 2 * h * (math.sqrt(2) - 1)
    k = max(1, int(round(need / per)))
    h = need / (k * 2 * (math.sqrt(2) - 1))                 # exact length for k bumps
    span = 2 * h + top
    legs = sorted(range(len(poly) - 1), key=lambda n: -math.hypot(poly[n + 1][0] - poly[n][0], poly[n + 1][1] - poly[n][1]))
    for n in legs:
        a, b = poly[n], poly[n + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < k * span + (k - 1) * gap + 0.2:
            continue
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        nb = (-u[1] * away, u[0] * away)
        s = (L - (k * span + (k - 1) * gap)) / 2
        pts = []
        for _ in range(k):
            pts += [(a[0] + u[0] * s, a[1] + u[1] * s),
                    (a[0] + u[0] * (s + h) + nb[0] * h, a[1] + u[1] * (s + h) + nb[1] * h),
                    (a[0] + u[0] * (s + h + top) + nb[0] * h, a[1] + u[1] * (s + h + top) + nb[1] * h),
                    (a[0] + u[0] * (s + 2 * h + top), a[1] + u[1] * (s + 2 * h + top))]
            s += span + gap
        new = poly[:n + 1] + pts + poly[n + 1:]
        if ok(pts):
            return new
    raise SystemExit('no leg takes %d bumps of %.3f mm' % (k, h))


def main():
    model, seed, out = sys.argv[1:4]
    box = [float(v) for v in sys.argv[4:8]] if len(sys.argv) > 7 else [22.0, 36.0, 12.0, 24.5]
    seed_cost = float(os.environ.get('SEED_COST', '6'))
    turn_cost = float(os.environ.get('TURN_COST', '0.4'))
    M, B, Rt, Pseed = load(model, seed)
    win, fixed_ok, all_ok = masks(B, Rt, box)
    # the pair leaves U2 pins 8/7 westwards (P on the left = -y side) and enters X1 pins 3/2 heading north (+y)
    start, goal = (25.30, 15.05), (30.80, 20.25)
    path, pops = astar(win, fixed_ok, all_ok, start, goal, 0, 6, seed_cost, turn_cost)
    if not path:
        print('NO PATH after', pops, 'pops')
        sys.exit(1)
    c = simplify(path)
    print('centreline', len(c), 'vertices, %.2f mm, %d pops' % (plen(c), pops))
    print(' '.join('(%.2f,%.2f)' % v for v in c))
    Pc, Nc = offset(c, OFF), offset(c, -OFF)
    pfan = [(26.075, 14.8), (25.65, 14.8), (25.55, 14.9)]
    nfan = [(26.075, 15.3), (25.65, 15.3), (25.55, 15.2)]
    Pp = pfan + Pc[:-1] + [(30.65, 20.25), (30.65, 20.85)]
    Np = nfan + Nc[:-1] + [(30.95, 20.25), (30.95, 20.85)]
    Pp, Np = simplify(Pp), simplify(Np)
    print('P %.4f  N %.4f  N-P %.4f' % (plen(Pp), plen(Np), plen(Np) - plen(Pp)))
    dl = plen(Pp) - plen(Np)
    if abs(dl) > 0.005:
        i0, _, j0, _ = win
        Dt = Rt.dist('USB_D_P', win, base=True)[TOP] >= W_TRK / 2 + R.MARGIN

        def ok(poly):
            for a, b in zip(poly, poly[1:]):
                n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.025))
                for k in range(n + 1):
                    x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
                    i, j = int(round(y / R.G)) - i0, int(round(x / R.G)) - j0
                    if not (0 <= i < Dt.shape[0] and 0 <= j < Dt.shape[1]) or not Dt[i, j]:
                        return False
            return True
        if dl > 0:
            Np = add_bumps(Np, dl, -1, ok)           # N is on the right of the heading: bump away from P
        else:
            Pp = add_bumps(Pp, -dl, +1, ok)
    print('tuned P %.4f  N %.4f  N-P %.4f' % (plen(Pp), plen(Np), plen(Np) - plen(Pp)))
    ct, cv = conflicts([Pp, Np], Pseed)
    nets = sorted({t['net'] for t in ct} | {v['net'] for v in cv})
    print('seed conflicts: %d tracks, %d vias; nets %s' % (len(ct), len(cv), nets))
    json.dump({'center': c, 'P': Pp, 'N': Np, 'tracks': tracks(Pp, 'USB_D_P') + tracks(Np, 'USB_D_N'),
               'conflict_tracks': ct, 'conflict_vias': cv, 'conflict_nets': nets}, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
