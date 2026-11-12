"""Router stage 3 (2026-10-24): a targeted grid router for the connections Freerouting left open, using the
board's own HDI via types.

    python tools/router.py [--nets N1,N2] [--remove tools/route/remove.json] [--out tools/route/stage3.json]
                           [--checkpoint tools/route/stage3.partial.json]

Reads tools/route/model.json (route_model.py) and finds the open connections with route_conn.py (it agrees with
Altium's DRC count). Plane nets (GND on L2, VCC3V3 on L5) are closed by dropping a via onto their pour; every other
open connection is routed island to island with A* on a 0.025 mm grid over the four signal layers.

MODEL
  layers   Top, L3-SIG, L4-SIG, Bottom are routed; L2-GND and L5-VCC3V3 only carry via lands
  vias     uvia_top   Top->L2 0.30/0.15 (GND plane tie)          uvia_bot   L5->Bottom 0.30/0.15 (VCC3V3 tie)
           stack_top  Top->L2->L3 0.30/0.15 x2 (signal Top<->L3)  stack_bot  L4->L5->Bottom 0.30/0.15 x2
           uvia_top   Top->L2 0.30/0.15 (GND plane tie only)      uvia_bot   L5->Bottom (VCC3V3 tie only)
           stack_tie  Top>L2>L3 + L3>L4 + L4>L5 column (a Top pad to the VCC3V3 plane, via-in-pad allowed)
           buried     L3->L4 0.27/0.15                            through    0.35/0.20 (any layer change)
  widths   the board's per-layer Width minimums (WIDTH below); SDRAM 0.1 on L3/L4/Bottom; USB 0.15
  clearance 0.09 mm (Clearance rule), 0.10 for SDRAM nets on L3/L4 and 0.20 for SDRAM-CLK there; 0.30 to the
           board edge; vias: land-to-land 0.09 on every layer of both spans and hole-to-hole 0.24 when the spans share
           a layer
  exactness every shape is painted 0.7 cell fatter, distances get a further 0.02 mm allowance; every emitted primitive
           is then re-checked exactly against all copper by check() before the plan is written
"""
import argparse
import heapq
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import ndimage

HERE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))  # tools/
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402

G = 0.025                       # grid, mm
MARGIN = 0.02                   # raster allowance, mm
INFL = 0.71 * G                 # every shape is painted this much fatter, so the raster always covers real copper
CLEAR = 0.09                    # router.py --clear: the Clearance rule (3 mil = 0.0762 opens the lanes between U1's lands)
SDRAM_RULES = True              # router.py --sdram-plain: False routes SDRAM nets with the default width/clearance
EDGE = 0.30
HOLE_HOLE = 0.24
ROUTE = ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
SDRAM = set(['D%d' % i for i in range(16)] + ['A%d' % i for i in range(13)] +
            ['BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CS#', 'SDRAM-CLK'])
INNER = ('L3-SIG', 'L4-SIG')
# via types: name -> (list of (from, to, size, hole) objects, layers the stack occupies, routing layers it joins)
VIAS = {
    'stack_top': ([('Top Layer', 'L2-GND', 0.30, 0.15), ('L2-GND', 'L3-SIG', 0.30, 0.15)], STACK[0:3], ('Top Layer', 'L3-SIG')),
    'stack_bot': ([('L4-SIG', 'L5-VCC3V3', 0.30, 0.15), ('L5-VCC3V3', 'Bottom Layer', 0.30, 0.15)], STACK[3:6], ('L4-SIG', 'Bottom Layer')),
    'buried': ([('L3-SIG', 'L4-SIG', 0.27, 0.15)], STACK[2:4], ('L3-SIG', 'L4-SIG')),
    'through': ([('Top Layer', 'Bottom Layer', 0.35, 0.20)], STACK, tuple(ROUTE)),
    # single-level microvias: plane ties only (they join no pair of routing layers)
    'uvia_top': ([('Top Layer', 'L2-GND', 0.30, 0.15)], STACK[0:2], ('Top Layer',)),
    'uvia_bot': ([('L5-VCC3V3', 'Bottom Layer', 0.30, 0.15)], STACK[4:6], ('Bottom Layer',)),
    # a Top pad down to the VCC3V3 plane: stacked microvias over the buried via, Bottom untouched
    'stack_tie': ([('Top Layer', 'L2-GND', 0.30, 0.15), ('L2-GND', 'L3-SIG', 0.30, 0.15),
                   ('L3-SIG', 'L4-SIG', 0.27, 0.15), ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15)], STACK[0:5], ('Top Layer',)),
}
VIA_COST = {'stack_top': 0.8, 'stack_bot': 0.8, 'buried': 0.8, 'through': 1.5, 'uvia_top': 0.5, 'uvia_bot': 0.5,
            'stack_tie': 1.5}


WIDTH_OVERRIDE = {}           # router.py --widths: {net: [outer, inner]} (2026-11-10, LTC3556 power nets)


def width(net, layer):
    inner = layer in INNER
    if net in WIDTH_OVERRIDE:
        return WIDTH_OVERRIDE[net][1 if inner else 0]
    if net == 'VCC3V3':
        return 1.05 if inner else (0.2 if layer == 'Bottom Layer' else 0.0762)
    if net in ('VU', 'USB5V0', 'VBATT'):
        return 1.1 if inner else 0.2
    if net == 'VCC1V0':
        return 0.5 if inner else 0.15
    if net in ('NetL1_1', 'NetL2_1', 'NetL3_1'):
        return 0.2
    if net in ('VCC1V8', 'VCCADC', 'GNDADC', 'FT-VCORE', 'FT-VPHY', 'FT-VPLL'):
        return 0.15
    if net in ('USB_D_P', 'USB_D_N'):
        return 0.15
    if SDRAM_RULES and net in SDRAM and (inner or layer == 'Bottom Layer'):
        return 0.1
    return 0.0762


def clearance(net, layer):
    if SDRAM_RULES and layer in INNER and net == 'SDRAM-CLK':
        return 0.20
    if SDRAM_RULES and layer in INNER and net in SDRAM:
        return 0.10
    return CLEAR


class Board:
    """rasters of copper per layer: an int32 net index (0 empty, -1 edge / hole / keepout)"""

    def __init__(self, M):
        self.M = M
        self.W = int(math.ceil(M['board']['w'] / G)) + 1
        self.H = int(math.ceil(M['board']['h'] / G)) + 1
        nets = sorted({p['net'] for p in M['pads'] if p['net']} | {t['net'] for t in M['tracks']} |
                      {v['net'] for v in M['vias']})
        self.nid = {n: i + 1 for i, n in enumerate(nets)}
        self.net_by_nid = {i: n for n, i in self.nid.items()}
        self.r = {l: np.zeros((self.H, self.W), np.int32) for l in STACK}
        e = int(round(EDGE / G))
        cr = int(round(1.2 / G))
        for l in ROUTE:
            a = self.r[l]
            a[:e, :] = -1
            a[-e:, :] = -1
            a[:, :e] = -1
            a[:, -e:] = -1
            for ys in (slice(0, cr), slice(self.H - cr, self.H)):
                for xs in (slice(0, cr), slice(self.W - cr, self.W)):
                    a[ys, xs] = -1
        for p in M['pads']:
            self.add_pad(p)
        for t in M['tracks']:
            self.add_track(t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
        for v in M['vias']:
            self.add_via_land(v['net'], v['x'], v['y'], v['size'], v['span'])
        self.vias = [(v['x'], v['y'], v['hole'], set(v['span']), v['net']) for v in M['vias']]
        self.holes = [(p['x'], p['y'], p['drill']) for p in M['pads'] if p['drill'] > 0]
        self.smd = [(p['x'], p['y'], p['w'] / 2, p['h'] / 2) for p in M['pads'] if not p['drill']]
        self.base = {l: a.copy() for l, a in self.r.items()}       # the board before this router added copper
        self.base_vias = list(self.vias)

    def ij(self, x, y):
        return int(round(y / G)), int(round(x / G))

    def _paint(self, layer, net, mask_fn, x0, y0, x1, y1):
        a = self.r[layer]
        i0, j0 = max(0, int(math.floor(y0 / G))), max(0, int(math.floor(x0 / G)))
        i1, j1 = min(self.H - 1, int(math.ceil(y1 / G))), min(self.W - 1, int(math.ceil(x1 / G)))
        if i1 < i0 or j1 < j0:
            return
        yy, xx = np.mgrid[i0:i1 + 1, j0:j1 + 1]
        m = mask_fn(xx * G, yy * G)
        v = self.nid.get(net, -1) if net else -1
        sub = a[i0:i1 + 1, j0:j1 + 1]
        clash = m & (sub != 0) & (sub != v)
        sub[m & (sub == 0)] = v
        sub[clash] = -1 if v != -1 else -1          # two nets on one cell: block it for everyone

    def add_pad(self, p):
        layers = p['layers'] if p['layers'] else (STACK if p['drill'] > 0 else [])
        if p['drill'] > 0 and not p['plated']:
            layers = STACK
        r = min(p['w'], p['h']) / 2 + INFL
        for l in layers:
            if C.pad_round(p) or (p['drill'] > 0 and not p['plated']):
                rr = max(r, p['drill'] / 2 + INFL)
                self._paint(l, p['net'] if p['plated'] or p['layers'] else None,
                            lambda X, Y: (X - p['x']) ** 2 + (Y - p['y']) ** 2 <= rr * rr,
                            p['x'] - rr, p['y'] - rr, p['x'] + rr, p['y'] + rr)
            else:
                hw, hh = p['w'] / 2 + INFL, p['h'] / 2 + INFL
                self._paint(l, p['net'], lambda X, Y: (abs(X - p['x']) <= hw) & (abs(Y - p['y']) <= hh),
                            p['x'] - hw, p['y'] - hh, p['x'] + hw, p['y'] + hh)

    def add_track(self, net, layer, w, x1, y1, x2, y2):
        r = w / 2 + INFL
        vx, vy = x2 - x1, y2 - y1
        L = vx * vx + vy * vy

        def m(X, Y):
            t = np.zeros_like(X) if L == 0 else np.clip(((X - x1) * vx + (Y - y1) * vy) / L, 0, 1)
            return (X - x1 - t * vx) ** 2 + (Y - y1 - t * vy) ** 2 <= r * r
        self._paint(layer, net, m, min(x1, x2) - r, min(y1, y2) - r, max(x1, x2) + r, max(y1, y2) + r)

    def add_via_land(self, net, x, y, size, span):
        r = size / 2 + INFL
        for l in span:
            self._paint(l, net, lambda X, Y: (X - x) ** 2 + (Y - y) ** 2 <= r * r, x - r, y - r, x + r, y + r)


class Router:
    def __init__(self, B, max_pops=400000):
        self.B = B
        self.max_pops = max_pops                     # A* expansion budget per connection
        self.layer_cost = {}                         # net -> {layer: step-cost multiplier} (router.py --layers)
        self.why = ''
        self.soft = 0.0                              # base=True routes: penalty (mm) per cell of rippable copper
        self.out_v, self.out_t = [], []

    def dist(self, net, win, base=False):
        """per-layer free radius after the larger of this net's and each obstacle net's clearance"""
        i0, i1, j0, j1 = win
        n = self.B.nid[net]
        hp = int(round(1.5 / G))                     # halo: copper just outside the window still counts
        a0, a1, b0, b1 = max(0, i0 - hp), min(self.B.H, i1 + hp), max(0, j0 - hp), min(self.B.W, j1 + hp)
        D = {}
        for l in STACK:
            sub = (self.B.base if base else self.B.r)[l][a0:a1, b0:b1]
            foreign = (sub != 0) & (sub != n)
            d = ndimage.distance_transform_edt(~foreign) * G if foreign.any() else np.full(sub.shape, 99.0)
            own_clear = clearance(net, l)
            available = d - own_clear
            ids_by_clear = defaultdict(list)
            for oid in np.unique(sub[(sub > 0) & (sub != n)]):
                obstacle_clear = clearance(self.B.net_by_nid[int(oid)], l)
                if obstacle_clear > own_clear:
                    ids_by_clear[obstacle_clear].append(oid)
            for obstacle_clear, ids in ids_by_clear.items():
                high_clearance = np.isin(sub, ids)
                hd = ndimage.distance_transform_edt(~high_clearance) * G
                available = np.minimum(available, hd - obstacle_clear)
            D[l] = available[i0 - a0:i1 - a0, j0 - b0:j1 - b0]
        return D

    def via_ok(self, net, kind, x, y, D, win, base=False):
        i0, _, j0, _ = win
        i, j = int(round(y / G)) - i0, int(round(x / G)) - j0
        objs, occ, _ = VIAS[kind]
        land = max(o[2] for o in objs) / 2
        for l in occ:
            a = D[l]
            if not (0 <= i < a.shape[0] and 0 <= j < a.shape[1]) or a[i, j] < land + MARGIN:
                return False
        hole = max(o[3] for o in objs) / 2
        for vx, vy, vh, vspan, vnet in (self.B.base_vias if base else self.B.vias):
            # hole to hole 0.24 mm for every pair of vias whose spans share a layer, the same net included; only a
            # stack at exactly the same point is exempt (Altium's HoleToHoleClearance behaves this way)
            dd = math.hypot(vx - x, vy - y)
            if dd > 1e-6 and vspan & set(occ) and dd < HOLE_HOLE + hole + vh / 2 + 0.001:
                return False
        for hx, hy, hd in self.B.holes:
            if math.hypot(hx - x, hy - y) < HOLE_HOLE + hole + hd / 2:
                return False
        if kind == 'through':                        # strategy A: no through via land on ANY SMD pad (user rule)
            for px, py, hw, hh in self.B.smd:
                if math.hypot(max(abs(x - px) - hw, 0), max(abs(y - py) - hh, 0)) < land + 0.005:
                    return False
        return True

    def route(self, net, src, dst, win, plane=None, base=False):
        """A* from the cells of `src` to those of `dst` ({layer: bool array in window}); plane: a via type set whose
        placement anywhere on the given layer reaches the goal. Returns (path, end via) or None."""
        D = self.dist(net, win, base)
        self.last = (D, win)
        i0, i1, j0, j1 = win
        h, w = i1 - i0, j1 - j0
        free = {}
        soft = bool(base and self.soft > 0)          # pass through rippable copper, at a price per cell crossed
        Dl = self.dist(net, win, False) if soft else None
        pen = {}
        for l in ROUTE:
            need = width(net, l) / 2 + MARGIN
            free[l] = D[l] >= need
            pen[l] = np.zeros((h, w), np.float32)
            if soft:
                pen[l] = np.where(Dl[l] >= need, 0.0, self.soft).astype(np.float32)
        if net in ('VCC3V3', 'VU', 'USB5V0', 'VBATT'):
            for l in INNER:
                free[l][:] = False
        tgt = None
        Hd = np.zeros((h, w), np.float32)            # admissible heuristic: straight-line distance to the target
        if dst:
            tgt = {l: dst[l] for l in ROUTE if l in dst}
            anyt = np.zeros((h, w), bool)
            for m in tgt.values():
                anyt |= m
            if not anyt.any():
                return None
            Hd = (ndimage.distance_transform_edt(~anyt) * G).astype(np.float32)
            if getattr(self, 'hw', 1.0) != 1.0:      # finish.py: weighted A* (greedy probe, bounded suboptimal)
                Hd *= self.hw
        own = np.zeros((h, w), bool)                 # cells of the source copper (no through via in a pad)
        L = {l: k for k, l in enumerate(ROUTE)}
        lc = self.layer_cost.get(net, {})
        mult = [lc.get(l, 1.0) for l in ROUTE]         # >= 1, so the straight-line heuristic stays admissible
        INF = 1e18
        g = np.full((4, h, w), INF, np.float32)
        came = {}
        pq = []
        for l, m in src.items():
            if l not in L:
                continue
            own |= m
            for i, j in np.argwhere(m & free[l]):
                g[L[l], i, j] = 0
                heapq.heappush(pq, (float(Hd[i, j]), 0.0, L[l], int(i), int(j)))
        steps = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142),
                 (1, 1, 1.4142)]
        pops = 0
        while pq:
            f, gc, k, i, j = heapq.heappop(pq)
            if gc > g[k, i, j]:
                continue
            pops += 1
            self.pops = pops
            if pops > self.max_pops:
                self.why = 'budget'
                return None
            l = ROUTE[k]
            x, y = (j + j0) * G, (i + i0) * G
            if dst and tgt.get(l) is not None and tgt[l][i, j]:
                return self._trace(came, (k, i, j), win), None
            if plane:
                for kind in plane.get(l, ()):
                    if kind == 'through' and own[i, j]:
                        continue
                    if self.via_ok(net, kind, x, y, D, win, base):
                        return self._trace(came, (k, i, j), win), (kind, x, y)
            for di, dj, c in steps:
                ni, nj = i + di, j + dj
                if 0 <= ni < h and 0 <= nj < w and free[l][ni, nj]:
                    ng = gc + c * G * mult[k] + pen[l][ni, nj]
                    if ng < g[k, ni, nj]:
                        g[k, ni, nj] = ng
                        came[(k, ni, nj)] = (k, i, j, None)
                        heapq.heappush(pq, (ng + float(Hd[ni, nj]), ng, k, ni, nj))
            for kind, (objs, occ, joins) in VIAS.items():
                if l not in joins:
                    continue
                for l2 in joins:
                    if l2 == l or not free[l2][i, j]:
                        continue
                    k2 = L[l2]
                    ng = gc + VIA_COST[kind]
                    if kind == 'through' and own[i, j]:
                        continue
                    if ng < g[k2, i, j] and self.recent_via(came, (k, i, j), x, y, win):
                        continue
                    if ng < g[k2, i, j] and self.via_ok(net, kind, x, y, D, win, base):
                        if soft and not self.via_ok(net, kind, x, y, Dl, win, False):
                            ng += self.soft * 12               # about what crossing one track costs
                            if ng >= g[k2, i, j]:
                                continue
                        g[k2, i, j] = ng
                        came[(k2, i, j)] = (k, i, j, kind)
                        heapq.heappush(pq, (ng + float(Hd[i, j]), ng, k2, i, j))
        self.why = 'nopath'
        return None

    def recent_via(self, came, node, x, y, win):
        """does the best path to `node` already hold a via (not at this exact point) closer than any hole spacing
        allows? Walks back up to 40 cells (1 mm), which covers the largest spacing, 0.24 + 0.10 + 0.10 mm."""
        i0, _, j0, _ = win
        for _ in range(40):
            prev = came.get(node)
            if not prev:
                return False
            if prev[3]:                              # the step into `node` was a via, at node's position
                d = math.hypot((node[2] + j0) * G - x, (node[1] + i0) * G - y)
                if 1e-6 < d < HOLE_HOLE + 0.2 + 0.005:
                    return True
            node = prev[:3]
        return False

    def _trace(self, came, node, win):
        """cells from source to `node`; each entry carries the via type taken to ARRIVE at it (None for a step)"""
        i0, _, j0, _ = win
        path = []
        while True:
            prev = came.get(node)
            path.append((ROUTE[node[0]], (node[2] + j0) * G, (node[1] + i0) * G, prev[3] if prev else None))
            if not prev:
                return path[::-1]
            node = prev[:3]

    def line_free(self, net, l, a, b):
        """is the straight track a-b clear, judged on the route's distance field (half-cell samples)?"""
        D, win = self.last
        i0, i1, j0, j1 = win
        need = width(net, l) / 2 + MARGIN + G / 2
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (G / 2)))
        d = D[l]
        for k in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
            i, j = int(round(y / G)) - i0, int(round(x / G)) - j0
            if not (0 <= i < d.shape[0] and 0 <= j < d.shape[1]) or d[i, j] < need:
                return False
        return True

    def merge(self, pts):
        """collinear cell steps merged into their corners"""
        c = [pts[0]]
        for q in range(1, len(pts) - 1):
            (ax, ay), (bx, by), (cx, cy) = c[-1], pts[q], pts[q + 1]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                c.append(pts[q])
        if len(pts) > 1:
            c.append(pts[-1])
        return c

    def pull(self, net, l, pts):
        """string pulling: from each kept point, go straight to the farthest later point the track can reach
        without losing clearance (greedy, stops at the first blocked one); collinear cell steps always merge"""
        c = [pts[0]]                                 # collinear cell steps merge first: their corners only
        for q in range(1, len(pts) - 1):
            (ax, ay), (bx, by), (cx, cy) = c[-1], pts[q], pts[q + 1]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-9:
                c.append(pts[q])
        if len(pts) > 1:
            c.append(pts[-1])
        pts = c
        keep = [pts[0]]
        i = 0
        while i < len(pts) - 1:
            j = i + 1
            while j + 1 < len(pts) and self.line_free(net, l, pts[i], pts[j + 1]):
                j += 1
            keep.append(pts[j])
            i = j
        return keep

    def blockers(self, net, path, tight=False):
        """nets whose router-added copper lies near a path found with base=True (generous radius; tight: only
        copper the path's own clearance actually overlaps, for a minimum-victim path)"""
        n = self.B.nid[net]
        inv = {v: k for k, v in self.B.nid.items()}
        out = set()
        extra = 0.0 if tight else 0.2
        for l, x, y, kind in path:
            rad = width(net, l) / 2 + clearance(net, l) + MARGIN + extra
            layers = [l]
            if kind:
                layers = VIAS[kind][1]
                rad = max(rad, max(o[2] for o in VIAS[kind][0]) / 2 + CLEAR + MARGIN + extra)
            c = int(math.ceil(rad / G))
            i, j = int(round(y / G)), int(round(x / G))
            sl = (slice(max(0, i - c), i + c + 1), slice(max(0, j - c), j + c + 1))
            for ll in layers:
                cur, base = self.B.r[ll][sl], self.B.base[ll][sl]
                ids = np.unique(cur[(cur != base) & (cur > 0) & (cur != n)])
                out |= {inv[int(v)] for v in ids}
        return out

    def rip(self, nets):
        """remove every router-added track and via of these nets and repaint the board from its base"""
        self.out_t = [t for t in self.out_t if t['net'] not in nets]
        self.out_v = [v for v in self.out_v if v['net'] not in nets]
        self.B.r = {l: a.copy() for l, a in self.B.base.items()}
        self.B.vias = list(self.B.base_vias)
        for t in self.out_t:
            self.B.add_track(t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
        for v in self.out_v:
            span = STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
            self.B.add_via_land(v['net'], v['x'], v['y'], v['size'], span)
            self.B.vias.append((v['x'], v['y'], v['hole'], set(span), v['net']))

    def commit(self, net, path, endvia, pull=True):
        """turn a cell path into tracks and vias, paint them, and record them"""
        segs, vias = [], []
        cur = [path[0]]
        for a, b in zip(path, path[1:]):
            if b[3]:                                   # a via was taken into b
                vias.append((b[3], b[1], b[2]))
                segs.append(cur)
                cur = [b]
            else:
                cur.append(b)
        segs.append(cur)
        if endvia:
            vias.append(endvia)
        for s in segs:
            pts = [(p[1], p[2]) for p in s]
            l = s[0][0]
            keep = self.pull(net, l, pts) if pull else self.merge(pts)
            for (x1, y1), (x2, y2) in zip(keep, keep[1:]):
                w = width(net, l)
                t = {'net': net, 'layer': l, 'w': w, 'x1': round(x1, 4), 'y1': round(y1, 4), 'x2': round(x2, 4),
                     'y2': round(y2, 4)}
                self.out_t.append(t)
                self.B.add_track(net, l, w, x1, y1, x2, y2)
        for kind, x, y in vias:
            objs, occ, _ = VIAS[kind]
            for fr, to, size, hole in objs:
                if any(v['net'] == net and v['from'] == fr and v['to'] == to and abs(v['x'] - x) < 1e-6 and
                       abs(v['y'] - y) < 1e-6 for v in self.out_v):
                    continue                           # the same via is already there (two routes met at it)
                self.out_v.append({'net': net, 'x': round(x, 4), 'y': round(y, 4), 'size': size, 'hole': hole,
                                   'from': fr, 'to': to})
                span = STACK[STACK.index(fr):STACK.index(to) + 1]
                self.B.add_via_land(net, x, y, size, span)
                self.B.vias.append((x, y, hole, set(span), net))


def island_mask(B, M, isl, win):
    """{layer: bool array} of the cells covered by an island's copper, inside the window"""
    i0, i1, j0, j1 = win
    out = {}
    def get(l):
        if l not in out:
            out[l] = np.zeros((i1 - i0, j1 - j0), bool)
        return out[l]
    for pi in isl['pads']:
        p = M['pads'][pi]
        for l in (p['layers'] or []):
            if l in ROUTE:
                a = get(l)
                r = min(p['w'], p['h']) / 2
                yy, xx = np.mgrid[i0:i1, j0:j1]
                X, Y = xx * G, yy * G
                if C.pad_round(p):
                    m = (X - p['x']) ** 2 + (Y - p['y']) ** 2 <= (r * 0.8) ** 2
                else:
                    m = (abs(X - p['x']) <= p['w'] / 2 * 0.8) & (abs(Y - p['y']) <= p['h'] / 2 * 0.8)
                a |= m
    for ti in isl['tracks']:
        t = M['tracks'][ti]
        if t['layer'] in ROUTE:
            a = get(t['layer'])
            n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / G) + 1)
            for s in np.linspace(0, 1, n):
                x, y = t['x1'] + s * (t['x2'] - t['x1']), t['y1'] + s * (t['y2'] - t['y1'])
                i, j = int(round(y / G)) - i0, int(round(x / G)) - j0
                if 0 <= i < a.shape[0] and 0 <= j < a.shape[1]:
                    a[i, j] = True
    for vi in isl['vias']:
        v = M['vias'][vi]
        for l in v['span']:
            if l in ROUTE:
                a = get(l)
                i, j = int(round(v['y'] / G)) - i0, int(round(v['x'] / G)) - j0
                if 0 <= i < a.shape[0] and 0 <= j < a.shape[1]:
                    a[i, j] = True
    return out


def bbox(M, isl):
    xs, ys = [], []
    for pi in isl['pads']:
        xs.append(M['pads'][pi]['x']); ys.append(M['pads'][pi]['y'])
    for ti in isl['tracks']:
        t = M['tracks'][ti]
        xs += [t['x1'], t['x2']]; ys += [t['y1'], t['y2']]
    for vi in isl['vias']:
        xs.append(M['vias'][vi]['x']); ys.append(M['vias'][vi]['y'])
    return min(xs), min(ys), max(xs), max(ys)


def window(B, boxes, margin):
    x0 = min(b[0] for b in boxes) - margin
    y0 = min(b[1] for b in boxes) - margin
    x1 = max(b[2] for b in boxes) + margin
    y1 = max(b[3] for b in boxes) + margin
    return (max(0, int(y0 / G)), min(B.H, int(y1 / G) + 1), max(0, int(x0 / G)), min(B.W, int(x1 / G) + 1))


PLANE_VIAS = {'GND': {'Top Layer': ('uvia_top', 'stack_top', 'through'), 'Bottom Layer': ('through',),
                      'L3-SIG': ('stack_top',), 'L4-SIG': ('through',)},
              'VCC3V3': {'Bottom Layer': ('uvia_bot', 'stack_bot', 'through'), 'Top Layer': ('through', 'stack_tie'),
                         'L4-SIG': ('stack_bot',), 'L3-SIG': ('through',)}}

def _laser_objs(objs, size, hole):
    return [(fr, to, size, hole) if (sz, hl) == (0.30, 0.15) else (fr, to, sz, hl) for fr, to, sz, hl in objs]


def set_laser(size, hole):
    """router.py --laser S/H: every standard laser microvia (0.30/0.15) becomes S/H (the buried and through vias stay)"""
    for kind, (objs, occ, joins) in list(VIAS.items()):
        VIAS[kind] = (_laser_objs(objs, size, hole), occ, joins)


def add_small_lasers(size, hole, extra_cost=0.3):
    """router.py --laser-small S/H: a second laser family (kinds *_s) the router may pick where the standard
    0.30/0.15 land does not fit, e.g. interstitial sites inside a BGA field; costs extra_cost more per via"""
    for kind in ('stack_top', 'stack_bot', 'uvia_top', 'uvia_bot', 'stack_tie'):
        objs, occ, joins = VIAS[kind]
        VIAS[kind + '_s'] = (_laser_objs(objs, size, hole), occ, joins)
        VIA_COST[kind + '_s'] = VIA_COST[kind] + extra_cost
    for net, per_layer in PLANE_VIAS.items():
        for l, kinds in list(per_layer.items()):
            per_layer[l] = kinds + tuple(k + '_s' for k in kinds if k + '_s' in VIAS)



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nets', default='')
    ap.add_argument('--remove', default='')
    ap.add_argument('--out', default=os.path.join(HERE, 'route', 'stage3.json'))
    ap.add_argument('--margin', type=float, default=2.5)
    ap.add_argument('--model', default=os.path.join(HERE, 'route', 'model.json'))
    ap.add_argument('--layers', default='', help='per-net layer costs, e.g. tools/route/sdram_layers.json')
    ap.add_argument('--order', default='name', choices=['name', 'short', 'y'], help='net order after the plane nets')
    ap.add_argument('--negotiate', type=int, default=0, help='route the two-ended SDRAM nets together first, with up '
                    'to this many negotiated-congestion iterations (0: off)')
    ap.add_argument('--rip', type=int, default=2, help='rip-up limit per net (0: no rip-up)')
    ap.add_argument('--pops', type=int, default=400000, help='A* expansions allowed per connection')
    ap.add_argument('--seed', default='', help='comma-separated plans loaded as router copper (rippable): their nets '
                    'are re-routed from the live islands when ripped')
    ap.add_argument('--checkpoint', default='', help='write the complete in-progress routing plan after each net so '
                    'an interrupted run can resume by using it as --seed')
    ap.add_argument('--soft', type=float, default=0.0, help='rip-up picks the path crossing the least rippable copper: '
                    'this many mm of cost per cell of it (0: the straight base-only path, every net near it ripped)')
    ap.add_argument('--laser', default='', help='standard laser microvia SIZE/HOLE instead of 0.30/0.15')
    ap.add_argument('--laser-small', default='', help='add a second, smaller laser family SIZE/HOLE (kinds *_s)')
    ap.add_argument('--slack', type=float, default=MARGIN, help='raster allowance in mm on top of every clearance '
                    '(default 0.02); 0 lets a local repair re-enter a lane routed at the rule limit -- route_check it')
    ap.add_argument('--widths', default='', help='JSON {net: [outer width, inner width]} overriding the width table')
    ap.add_argument('--clear', type=float, default=CLEAR, help='Clearance rule in mm (default 0.09; 0.0762 = 3 mil)')
    ap.add_argument('--sdram-plain', action='store_true', help='SDRAM nets use the default width and clearance on '
                    'the inner layers and Bottom too (no 0.1 width / 0.10 clearance / 0.20 for SDRAM-CLK)')
    a = ap.parse_args()
    globals()['MARGIN'] = a.slack
    globals()['CLEAR'] = a.clear
    if a.widths:
        WIDTH_OVERRIDE.update(json.load(open(a.widths)))
    globals()['SDRAM_RULES'] = not a.sdram_plain
    if a.clear != 0.09 or a.sdram_plain:
        print('rules: clearance %.4f, SDRAM rules %s' % (CLEAR, 'on' if SDRAM_RULES else 'OFF (plain)'), flush=True)
    if a.laser:
        set_laser(*[float(v) for v in a.laser.split('/')])
    if a.laser_small:
        add_small_lasers(*[float(v) for v in a.laser_small.split('/')])
    M = json.load(open(a.model))
    removed = []
    if a.remove:
        R = json.load(open(a.remove))
        keep = []
        for t in M['tracks']:
            if any(t['net'] == r['net'] and t['layer'] == r['layer'] and
                   {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} ==
                   {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))} for r in R['tracks']):
                removed.append(t)
            else:
                keep.append(t)
        M['tracks'] = keep
        print('removed %d tracks before routing' % len(removed))
    B = Board(M)
    Rt = Router(B, a.pops)
    Rt.soft = a.soft
    if a.layers:
        Rt.layer_cost = json.load(open(a.layers))['cost']
    S = {'M': M}

    def cur():
        """the model plus the copper the router holds now (seeds and commits)"""
        Mx = dict(M)
        Mx['tracks'] = M['tracks'] + Rt.out_t
        Mx['vias'] = M['vias'] + [dict(v, span=STACK[STACK.index(v['from']):STACK.index(v['to']) + 1])
                                  for v in Rt.out_v]
        return Mx
    if a.seed:
        for f in a.seed.split(','):
            P = json.load(open(f))
            Rt.out_t += P['tracks']
            Rt.out_v += P['vias']
        Rt.rip(set())                                 # repaint: the seeds are router copper, so rip-up can move them
        S['M'] = cur()
        print('seeded %d vias, %d tracks' % (len(Rt.out_v), len(Rt.out_t)), flush=True)
    isl = C.islands(S['M'])
    want = set(a.nets.split(',')) if a.nets else None
    log = []
    ripped = defaultdict(int)

    def try_route(net, main_g, gi, base=False):
        M = S['M']
        mb = bbox(M, main_g)
        for mg in (a.margin, a.margin * 2.5, 60.0):
            win = window(B, [mb, bbox(M, gi)], mg)
            r = Rt.route(net, island_mask(B, M, main_g, win), island_mask(B, M, gi, win), win, base=base)
            if r:
                return r
        return None

    def route_net(net):
        """join the net's islands nearest first; returns the nets ripped up to make room"""
        if a.seed:                                    # islands as the net stands now (seeds, rips, commits)
            S['M'] = cur()
            now = C.islands(S['M']).get(net, [])
        else:
            now = isl[net]
        M = S['M']
        groups = [{k: (list(v) if isinstance(v, list) else v) for k, v in g.items()} for g in now]
        if net in PLANE_VIAS:
            tied = [g for g in groups if g['plane']]
            torn = set()

            def tie(base=False):
                for mg in (0.8, 1.6, 3.0):
                    win = window(B, [bx], mg)
                    r = Rt.route(net, island_mask(B, M, gi, win), None, win, plane=PLANE_VIAS[net], base=base)
                    if r:
                        return r
                return None
            for gi in groups:
                if gi['plane']:
                    continue
                bx = bbox(M, gi)
                r = tie()
                if r:
                    Rt.commit(net, *r)
                    gi['plane'] = True
                    tied.append(gi)
                else:                                 # no tie via fits: join the nearest island that is tied
                    cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
                    r = None
                    for tg in sorted(tied, key=lambda g: math.hypot((bbox(M, g)[0] + bbox(M, g)[2]) / 2 - cx,
                                                                    (bbox(M, g)[1] + bbox(M, g)[3]) / 2 - cy))[:3]:
                        r = try_route(net, tg, gi)
                        if r:
                            Rt.commit(net, *r)
                            for k in ('pads', 'tracks', 'vias'):
                                tg[k] = tg[k] + gi[k]
                            log.append('plane join %s at %.2f,%.2f' % (net, cx, cy))
                            break
                    if not r and a.rip:               # rip up the least rippable copper in the way of a tie via
                        rb = tie(base=True)
                        if rb:
                            path, (kind, vx, vy) = rb
                            victims = {v for v in Rt.blockers(net, path + [(path[-1][0], vx, vy, kind)],
                                                              tight=Rt.soft > 0) if v not in PLANE_VIAS}
                            if victims and all(ripped[v] < a.rip for v in victims):
                                for v in victims:
                                    ripped[v] += 1
                                Rt.rip(victims)
                                torn |= victims
                                r = tie()
                                if r:
                                    Rt.commit(net, *r)
                                    gi['plane'] = True
                                    tied.append(gi)
                                    log.append('plane tie %s at %.2f,%.2f ripped %s' % (net, cx, cy, ' '.join(sorted(victims))))
                    if not r:
                        log.append('FAIL plane tie %s at %.2f,%.2f' % (net, cx, cy))
            return torn
        main_g, rest = groups[0], groups[1:]
        torn = set()
        while rest:
            mb = bbox(M, main_g)
            rest.sort(key=lambda g: math.hypot((bbox(M, g)[0] + bbox(M, g)[2]) / 2 - (mb[0] + mb[2]) / 2,
                                               (bbox(M, g)[1] + bbox(M, g)[3]) / 2 - (mb[1] + mb[3]) / 2))
            gi = rest.pop(0)
            r = try_route(net, main_g, gi)
            if not r and a.rip:
                rb = try_route(net, main_g, gi, base=True)
                if rb:
                    victims = {v for v in Rt.blockers(net, rb[0], tight=Rt.soft > 0) if v not in PLANE_VIAS}
                    if victims and all(ripped[v] < a.rip for v in victims):
                        for v in victims:
                            ripped[v] += 1
                        Rt.rip(victims)
                        torn |= victims
                        r = try_route(net, main_g, gi)
            if r:
                Rt.commit(net, *r)
                for k in ('pads', 'tracks', 'vias'):
                    main_g[k] = main_g[k] + gi[k]
            else:
                log.append('FAIL %s (%s)' % (net, getattr(Rt, 'why', '?')))
        return torn

    def span_of(n):                                  # straight distance between a net's two farthest islands
        bs = [bbox(S['M'], g) for g in isl[n]]
        cs = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in bs]
        return max((math.hypot(p[0] - q[0], p[1] - q[1]) for p in cs for q in cs), default=0)

    def u1_y(n):
        ys = [M['pads'][i]['y'] for g in isl[n] for i in g['pads'] if M['pads'][i]['ref'] == 'U1']
        return min(ys) if ys else 99
    keyf = {'name': lambda n: n, 'short': span_of, 'y': u1_y}[a.order]
    order = [n for n in sorted(isl, key=lambda n: (n not in ('GND', 'VCC3V3'), keyf(n))) if not want or n in want]
    queue = [n for n in order if n in PLANE_VIAS or len(isl[n]) > 1]
    if a.negotiate:
        import negotiate
        group = [n for n in queue if n in SDRAM and len(isl[n]) == 2]
        keep, drop = negotiate.run(Rt, M, isl, group, iters=a.negotiate,
                                   log=lambda m: print(m, flush=True))
        print('negotiated SDRAM: %d committed, %d left to the normal pass: %s' % (len(keep), len(drop), ' '.join(drop)),
              flush=True)
        queue = [n for n in queue if n not in keep]
    touched = set()
    while queue:
        net = queue.pop(0)
        if net in queue:
            continue                                  # a later copy of this net is still waiting
        touched.add(net)
        torn = route_net(net)
        for v in sorted(torn):
            if v not in queue:
                queue.append(v)                       # its copper is gone: route it again from scratch
        print('%-14s %s' % (net, ('ripped ' + ' '.join(sorted(torn))) if torn else ''), flush=True)
        if a.checkpoint:
            json.dump({'vias': Rt.out_v, 'tracks': Rt.out_t, 'remove': removed,
                       'log': ['CHECKPOINT: %d queued nets remain' % len(queue)]},
                      open(a.checkpoint, 'w'), indent=0)
    # what the kept copper actually closes (a ripped net's earlier successes may not have survived)
    Mx = cur()
    oc_b = C.open_count(isl)
    oc_a = C.open_count(C.islands(Mx))
    if want:                                      # report the wanted nets and every net the pass touched
        oc_b = {k: v for k, v in oc_b.items() if k in want or k in touched}
        oc_a = {k: v for k, v in oc_a.items() if k in want or k in touched}
    done, fail = sum(oc_b.values()) - sum(oc_a.values()), sum(oc_a.values())
    log = ['OPEN %s %d' % kv for kv in sorted(oc_a.items())] + [l for l in log if l.startswith(('FAIL', 'plane '))]
    json.dump({'vias': Rt.out_v, 'tracks': Rt.out_t, 'remove': removed, 'log': log}, open(a.out, 'w'), indent=0)
    print('routed %d connections, failed %d; %d vias, %d tracks -> %s' % (done, fail, len(Rt.out_v), len(Rt.out_t),
                                                                         a.out))
    for l in log:
        print(l)


if __name__ == '__main__':
    main()
