"""exact_router.py: router_b.py (SOURCE's router run from TARGET's tools) with an EXACT free-space field.

    python B/scripts/exact_router.py <router_b.py arguments>

router.py rasters copper 0.7 cell fatter and adds a 0.02 mm allowance, so a 0.0762 track can never pass between two
of U1's 0.5 mm-pitch lands (0.275 mm gap, 0.256 needed) and a 0.30 laser never fits a BGA interstitial site (0.091
gap, 0.09 needed) - every JA ball of the Pmod whose old escape SOURCE's copper took is 'sealed' for it.
Here Router.dist() is computed exactly at every cell centre from the real objects (pads round / rect as route_conn
models them, tracks as capsules, via lands as discs, board edge 0.30 inset and 1.2 mm corner squares, the larger of
the two nets' clearances per layer), so:
  * a cell is free for a track when its exact clearance distance >= w/2 + TRACK_SLACK (0.0015 mm covers the dip of
    a 0.035 mm diagonal step between two free cell centres, s^2/8d < 0.0013 mm for d >= 0.12 mm);
  * a via fits when the exact distance at its centre >= land radius + VIA_SLACK (0.0003 mm), on every layer of its
    span, plus router.py's exact hole-to-hole / hole-to-pad tests and SOURCE's through-via-in-SMD-pad block.
Everything else (A*, via types, rip-up of seeded copper, commit, string pulling) is router.py's. Every plan is still
judged afterwards by route_check.py and the full-board DRC.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router_b as R  # noqa: E402

TRACK_SLACK = 0.0015
VIA_SLACK = 0.0003
REACH = 0.7              # copper farther than this from a cell never limits it (cap: free radius >= REACH - 0.2)
CAP = 0.5


def _layers_of_pad(p):
    if p['drill'] > 0 and not p['plated']:
        return R.STACK
    return p['layers'] if p['layers'] else (R.STACK if p['drill'] > 0 else [])


def _prep(B):
    """per layer: list of (kind, params, net, bbox) for the board model's copper (B.M), cached on the board"""
    if getattr(B, '_exact', None) is not None:
        return B._exact
    per = {l: [] for l in R.STACK}
    for p in B.M['pads']:
        lays = _layers_of_pad(p)
        if not lays:
            continue
        npth = p['drill'] > 0 and not p['plated']
        net = None if npth else (p['net'] or None)
        if R.C.pad_round(p) or npth:
            r = min(p['w'], p['h']) / 2
            if p['drill'] > 0:
                r = max(r, p['drill'] / 2) if npth else r
            o = ('c', (p['x'], p['y'], r), net, (p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r))
        else:
            o = ('r', (p['x'], p['y'], p['w'] / 2, p['h'] / 2), net,
                 (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2))
        for l in lays:
            per[l].append(o)
    for t in B.M['tracks']:
        r = t['w'] / 2
        per[t['layer']].append(('t', (t['x1'], t['y1'], t['x2'], t['y2'], r), t['net'],
                                (min(t['x1'], t['x2']) - r, min(t['y1'], t['y2']) - r,
                                 max(t['x1'], t['x2']) + r, max(t['y1'], t['y2']) + r)))
    for v in B.M['vias']:
        r = v['size'] / 2
        for l in v['span']:
            per[l].append(('c', (v['x'], v['y'], r), v['net'], (v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r)))
    out = {}
    for l, objs in per.items():
        bb = np.array([o[3] for o in objs]) if objs else np.zeros((0, 4))
        out[l] = (objs, bb)
    B._exact = out
    return out


def _added(Rt):
    per = {l: [] for l in R.STACK}
    for t in Rt.out_t:
        r = t['w'] / 2
        per[t['layer']].append(('t', (t['x1'], t['y1'], t['x2'], t['y2'], r), t['net'],
                                (min(t['x1'], t['x2']) - r, min(t['y1'], t['y2']) - r,
                                 max(t['x1'], t['x2']) + r, max(t['y1'], t['y2']) + r)))
    for v in Rt.out_v:
        r = v['size'] / 2
        span = R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]
        for l in span:
            per[l].append(('c', (v['x'], v['y'], r), v['net'], (v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r)))
    return per


def _obj_dist(kind, par, X, Y):
    if kind == 'c':
        x, y, r = par
        return np.hypot(X - x, Y - y) - r
    if kind == 'r':
        x, y, hw, hh = par
        return np.hypot(np.maximum(np.abs(X - x) - hw, 0), np.maximum(np.abs(Y - y) - hh, 0))
    x1, y1, x2, y2, r = par
    vx, vy = x2 - x1, y2 - y1
    L = vx * vx + vy * vy
    if L == 0:
        return np.hypot(X - x1, Y - y1) - r
    t = np.clip(((X - x1) * vx + (Y - y1) * vy) / L, 0, 1)
    return np.hypot(X - x1 - t * vx, Y - y1 - t * vy) - r


def exact_dist(self, net, win, base=False):
    B = self.B
    i0, i1, j0, j1 = win
    G = R.G
    xs = np.arange(j0, j1) * G
    ys = np.arange(i0, i1) * G
    wx0, wx1, wy0, wy1 = xs[0] - REACH, xs[-1] + REACH, ys[0] - REACH, ys[-1] + REACH
    W, H = B.M['board']['w'], B.M['board']['h']
    Xw, Yw = np.meshgrid(xs, ys)
    # board edge (0.30 inset) and the 1.2 mm corner squares, as route_check's edge test
    edge = np.minimum(np.minimum(Xw, W - Xw), np.minimum(Yw, H - Yw)) - R.EDGE
    for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
        edge = np.minimum(edge, np.maximum(np.maximum(np.abs(Xw - cx), np.abs(Yw - cy)) - 1.2, -1.0))
    pre = _prep(B)
    add = None if base else _added(self)
    D = {}
    for l in R.STACK:
        own = R.clearance(net, l)
        A = np.minimum(np.full((i1 - i0, j1 - j0), CAP), edge if l in R.ROUTE else np.full_like(edge, CAP))
        objs, bb = pre[l]
        cand = []
        if len(objs):
            sel = np.nonzero((bb[:, 2] >= wx0) & (bb[:, 0] <= wx1) & (bb[:, 3] >= wy0) & (bb[:, 1] <= wy1))[0]
            cand = [objs[k] for k in sel]
        if add is not None:
            cand += [o for o in add[l] if o[3][2] >= wx0 and o[3][0] <= wx1 and o[3][3] >= wy0 and o[3][1] <= wy1]
        for kind, par, onet, (bx0, by0, bx1, by1) in cand:
            if onet is not None and onet == net:
                continue
            clr = max(own, R.clearance(onet, l)) if onet else own
            a0 = max(0, int(math.floor((by0 - REACH) / G)) - i0)
            a1 = min(i1 - i0, int(math.ceil((by1 + REACH) / G)) - i0 + 1)
            b0 = max(0, int(math.floor((bx0 - REACH) / G)) - j0)
            b1 = min(j1 - j0, int(math.ceil((bx1 + REACH) / G)) - j0 + 1)
            if a1 <= a0 or b1 <= b0:
                continue
            d = _obj_dist(kind, par, Xw[a0:a1, b0:b1], Yw[a0:a1, b0:b1]) - clr
            sub = A[a0:a1, b0:b1]
            np.minimum(sub, d, out=sub)
        D[l] = A
    return D


def _global(B):
    """the whole board's exact field of the board model's copper, once: per layer the smallest (distance - obstacle
    clearance) d1 with its net n1, and d2 = the smallest over objects of any OTHER net than n1. For a net N whose own
    clearance is the minimum (CLEAR <= every obstacle's), the field is d2 where n1 == N, else d1 - exact."""
    if getattr(B, '_gfield', None) is not None:
        return B._gfield
    G = R.G
    H, W = B.H, B.W
    xs = np.arange(W) * G
    ys = np.arange(H) * G
    Xw, Yw = np.meshgrid(xs, ys)
    BW, BH = B.M['board']['w'], B.M['board']['h']
    edge = np.minimum(np.minimum(Xw, BW - Xw), np.minimum(Yw, BH - Yw)) - R.EDGE
    for cx, cy in ((0, 0), (BW, 0), (0, BH), (BW, BH)):
        edge = np.minimum(edge, np.maximum(np.maximum(np.abs(Xw - cx), np.abs(Yw - cy)) - 1.2, -1.0))
    pre = _prep(B)
    out = {}
    for l in R.STACK:
        d1 = np.full((H, W), CAP, np.float32)
        d2 = np.full((H, W), CAP, np.float32)
        n1 = np.full((H, W), -9, np.int32)
        objs, _ = pre[l]
        for kind, par, onet, (bx0, by0, bx1, by1) in objs:
            nid = B.nid.get(onet, -2) if onet else -2          # NPTH / no net: blocks everyone
            clr = R.clearance(onet, l) if onet else R.CLEAR
            a0 = max(0, int(math.floor((by0 - REACH) / G)))
            a1 = min(H, int(math.ceil((by1 + REACH) / G)) + 1)
            b0 = max(0, int(math.floor((bx0 - REACH) / G)))
            b1 = min(W, int(math.ceil((bx1 + REACH) / G)) + 1)
            if a1 <= a0 or b1 <= b0:
                continue
            d = (_obj_dist(kind, par, Xw[a0:a1, b0:b1], Yw[a0:a1, b0:b1]) - clr).astype(np.float32)
            s1, s2, sn = d1[a0:a1, b0:b1], d2[a0:a1, b0:b1], n1[a0:a1, b0:b1]
            same = sn == nid
            # same net as the current nearest: d1 = min(d1, d)
            np.minimum(s1, np.where(same, d, s1), out=s1)
            # other net, nearer than d1: (d1, n1) -> (d, nid), d2 = old d1
            closer = (~same) & (d < s1)
            s2[closer] = s1[closer]
            s1[closer] = d[closer]
            sn[closer] = nid
            # other net, not nearer: d2 = min(d2, d)
            farther = (~same) & ~closer
            s2[farther] = np.minimum(s2[farther], d[farther])
        out[l] = (d1, n1, d2)
    B._gfield = (out, edge.astype(np.float32))
    return B._gfield


def fast_dist(self, net, win, base=False):
    """exact_dist from the cached whole-board field (the board model) plus the router's own copper (not base)"""
    if any(R.clearance(net, l) > R.CLEAR + 1e-9 for l in R.STACK):
        return exact_dist(self, net, win, base)
    B = self.B
    i0, i1, j0, j1 = win
    G = R.G
    out, edge = _global(B)
    own = B.nid.get(net, -3)
    D = {}
    add = None if base else _added(self)
    xs = np.arange(j0, j1) * G
    ys = np.arange(i0, i1) * G
    wx0, wx1, wy0, wy1 = xs[0] - REACH, xs[-1] + REACH, ys[0] - REACH, ys[-1] + REACH
    Xw = Yw = None
    for l in R.STACK:
        d1, n1, d2 = out[l]
        A = np.where(n1[i0:i1, j0:j1] == own, d2[i0:i1, j0:j1], d1[i0:i1, j0:j1]).astype(np.float64)
        if l in R.ROUTE:
            np.minimum(A, edge[i0:i1, j0:j1], out=A)
        if add is not None:
            for kind, par, onet, (bx0, by0, bx1, by1) in add[l]:
                if onet == net or bx1 < wx0 or bx0 > wx1 or by1 < wy0 or by0 > wy1:
                    continue
                if Xw is None:
                    Xw, Yw = np.meshgrid(xs, ys)
                clr = max(R.clearance(net, l), R.clearance(onet, l))
                a0 = max(0, int(math.floor((by0 - REACH) / G)) - i0)
                a1 = min(i1 - i0, int(math.ceil((by1 + REACH) / G)) - i0 + 1)
                b0 = max(0, int(math.floor((bx0 - REACH) / G)) - j0)
                b1 = min(j1 - j0, int(math.ceil((bx1 + REACH) / G)) - j0 + 1)
                if a1 <= a0 or b1 <= b0:
                    continue
                d = _obj_dist(kind, par, Xw[a0:a1, b0:b1], Yw[a0:a1, b0:b1]) - clr
                sub = A[a0:a1, b0:b1]
                np.minimum(sub, d, out=sub)
        D[l] = A
    return D


def exact_via_ok(self, net, kind, x, y, D, win, base=False):
    i0, _, j0, _ = win
    i, j = int(round(y / R.G)) - i0, int(round(x / R.G)) - j0
    objs, occ, _ = R.VIAS[kind]
    if kind == 'through' and self.B.thr_block[int(round(y / R.G)), int(round(x / R.G))]:
        return False
    for l in occ:
        land = max(o[2] for o in objs if l in R.STACK[R.STACK.index(o[0]):R.STACK.index(o[1]) + 1]) / 2
        a = D[l]
        if not (0 <= i < a.shape[0] and 0 <= j < a.shape[1]) or a[i, j] < land + VIA_SLACK:
            return False
    hole = max(o[3] for o in objs) / 2
    for vx, vy, vh, vspan, vnet in (self.B.base_vias if base else self.B.vias):
        dd = math.hypot(vx - x, vy - y)
        if dd > 1e-6 and vspan & set(occ) and dd < R.HOLE_HOLE + hole + vh / 2 + 0.0005:
            return False
    for hx, hy, hd in self.B.holes:
        if math.hypot(hx - x, hy - y) < R.HOLE_HOLE + hole + hd / 2:
            return False
    return True


R.Router.dist = fast_dist if os.environ.get('EXACT_FAST', '1') == '1' else exact_dist
R.Router.via_ok = exact_via_ok


if __name__ == '__main__':
    if '--slack' not in sys.argv:
        sys.argv += ['--slack', str(TRACK_SLACK)]
    R.main()
