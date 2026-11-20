"""router_a.py: TARGET's tools/router.py with SOURCE's 2026-11-13..19 fixes ported in-process (TARGET's file is not edited).

    python router_a.py [router.py arguments]

Ports from Zulu_A7_no_pmod/Rev_2/tools/router.py:
  1. SDRAM set += SDRAM-D0..D15 (the DQ series-resistor nets are SDRAM_DATA: 0.10 clearance on L3/L4, 0.10 width on
     L3/L4/Bottom);
  2. Board.thr_block: no through via whose 0.35 land overlaps any SMD pad (the user rule; microvias in pads are allowed);
  3. Router.blockers: a router via within hole-to-hole spacing of the path's vias names its net as a blocker.
Extra (Strategy A): --keep-out JSON {"nets": [...]} forbids ripping these nets' router copper (never needed in practice);
--no-through forbids through vias entirely (laser stacks / buried only).
"""
import json
import math
import os
import sys

import numpy as np

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, TOOLS)
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

R.SDRAM |= {'SDRAM-D%d' % i for i in range(16)}

_orig_init = R.Board.__init__


def _through_in_pad_mask(self):
    r = max(o[2] for o in R.VIAS['through'][0]) / 2 - 1e-4
    mask = np.zeros((self.H, self.W), bool)
    G = R.G
    for p in self.M['pads']:
        if p['drill'] or not p['layers']:
            continue
        ext = max(p['w'], p['h']) / 2 + r
        i0, j0 = max(0, int(math.floor((p['y'] - ext) / G))), max(0, int(math.floor((p['x'] - ext) / G)))
        i1, j1 = min(self.H - 1, int(math.ceil((p['y'] + ext) / G))), min(self.W - 1, int(math.ceil((p['x'] + ext) / G)))
        if i1 < i0 or j1 < j0:
            continue
        yy, xx = np.mgrid[i0:i1 + 1, j0:j1 + 1]
        X, Y = xx * G, yy * G
        if C.pad_round(p):
            d = np.hypot(X - p['x'], Y - p['y']) - min(p['w'], p['h']) / 2
        else:
            d = np.hypot(np.maximum(np.abs(X - p['x']) - p['w'] / 2, 0), np.maximum(np.abs(Y - p['y']) - p['h'] / 2, 0))
        mask[i0:i1 + 1, j0:j1 + 1] |= d < r + 0.01        # 0.01 mm extra margin: the grid rounds the via centre
    return mask


def _init(self, M):
    _orig_init(self, M)
    self.thr_block = _through_in_pad_mask(self)


R.Board.__init__ = _init
NO_THROUGH = '--no-through' in sys.argv
if NO_THROUGH:
    sys.argv.remove('--no-through')
if '--via-cost-mult' in sys.argv:                     # e.g. 4: every via kind costs 4x (fewer layer changes)
    _k = sys.argv.index('--via-cost-mult')
    _m = float(sys.argv[_k + 1])
    del sys.argv[_k:_k + 2]
    for _kind in list(R.VIA_COST):
        R.VIA_COST[_kind] *= _m

_LBIT = {l: 1 << k for k, l in enumerate(R.STACK)}
_cache = {}


def _via_arrays(vias):
    """numpy view of a via list (x, y, hole, span bits), cached on the list's identity and length"""
    hit = _cache.get(id(vias))
    if hit is None or hit[0] != len(vias) or hit[1] is not vias:
        if len(_cache) > 8:
            _cache.clear()
        a = np.array([(v[0], v[1], v[2], sum(_LBIT[l] for l in v[3])) for v in vias] or [(0, 0, 0, 0)], float)
        hit = (len(vias), vias, (a[:, 0], a[:, 1], a[:, 2], a[:, 3].astype(np.int64)))
        _cache[id(vias)] = hit
    return hit[2]


def _via_ok(self, net, kind, x, y, D, win, base=False):
    """router.via_ok with the hole-to-hole loop vectorised (same rule: 0.24 mm between holes of every pair of vias
    whose spans share a layer, the same net included; only a stack at exactly the same point is exempt)"""
    if kind == 'through':
        if NO_THROUGH:
            return False
        i, j = int(round(y / R.G)), int(round(x / R.G))
        if self.B.thr_block[i, j]:
            return False
    i0, _, j0, _ = win
    i, j = int(round(y / R.G)) - i0, int(round(x / R.G)) - j0
    objs, occ, _ = R.VIAS[kind]
    land = max(o[2] for o in objs) / 2
    for l in occ:
        a = D[l]
        if not (0 <= i < a.shape[0] and 0 <= j < a.shape[1]) or a[i, j] < land + R.MARGIN:
            return False
    hole = max(o[3] for o in objs) / 2
    vx, vy, vh, vb = _via_arrays(self.B.base_vias if base else self.B.vias)
    ob = sum(_LBIT[l] for l in occ)
    dd = np.hypot(vx - x, vy - y)
    if np.any((dd > 1e-6) & ((vb & ob) != 0) & (dd < R.HOLE_HOLE + hole + vh / 2 + 0.001)):
        return False
    for hx, hy, hd in self.B.holes:
        if math.hypot(hx - x, hy - y) < R.HOLE_HOLE + hole + hd / 2:
            return False
    return True


R.Router.via_ok = _via_ok

_orig_blockers = R.Router.blockers


def _blockers(self, net, path, tight=False):
    out = _orig_blockers(self, net, path, tight)
    for l, x, y, kind in path:
        if not kind:
            continue
        objs, occ, _ = R.VIAS[kind]
        hole = max(o[3] for o in objs) / 2
        for vx, vy, vh, vspan, vnet in self.B.vias[len(self.B.base_vias):]:
            if (vnet != net and vnet in self.B.nid and vspan & set(occ) and
                    math.hypot(vx - x, vy - y) < R.HOLE_HOLE + hole + vh / 2 + 0.001):
                out.add(vnet)
    return out


R.Router.blockers = _blockers

if __name__ == '__main__':
    R.main()
