"""Exact geometry + rules for the prep checks: TARGET's router/route_conn/judge, with the DQ series-resistor nets
SDRAM-D0..D15 added to the SDRAM rule set (as SOURCE's router.py has it since 2026-11-13; TARGET's router.py lacks it)."""
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import TOOLS, STACK  # noqa: E402

sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, 'route', 'rev2', 'judge'))
import router as R  # noqa: E402
import route_conn as C  # noqa: E402
import prune_stubs as PS  # noqa: E402
import judge as J  # noqa: E402

R.SDRAM |= {'SDRAM-D%d' % i for i in range(16)}
CELL = 0.5
MARG = 0.3


def layers_of(k, o):
    if k == 'p':
        return J.pad_layers(o)
    if k == 't':
        return [o['layer']]
    return o['span']


def bbox(k, o):
    return J.bbox(k, o)


class Index:
    """grid of (kind, obj, tag) per layer"""

    def __init__(self):
        self.g = defaultdict(list)

    def add(self, k, o, tag=None):
        x0, y0, x1, y1 = bbox(k, o)
        for l in layers_of(k, o):
            for gx in range(int(math.floor((x0 - MARG) / CELL)), int(math.floor((x1 + MARG) / CELL)) + 1):
                for gy in range(int(math.floor((y0 - MARG) / CELL)), int(math.floor((y1 + MARG) / CELL)) + 1):
                    self.g[(l, gx, gy)].append((k, o, tag))

    def near(self, k, o, layer):
        x0, y0, x1, y1 = bbox(k, o)
        seen = set()
        for gx in range(int(math.floor((x0 - MARG) / CELL)), int(math.floor((x1 + MARG) / CELL)) + 1):
            for gy in range(int(math.floor((y0 - MARG) / CELL)), int(math.floor((y1 + MARG) / CELL)) + 1):
                for it in self.g.get((layer, gx, gy), ()):
                    if id(it[1]) not in seen:
                        seen.add(id(it[1]))
                        yield it


def edge_ok(W, H, x, y, r):
    if x - r < R.EDGE or y - r < R.EDGE or x + r > W - R.EDGE or y + r > H - R.EDGE:
        return False
    for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
        if abs(x - cx) < 1.2 + r and abs(y - cy) < 1.2 + r:
            return False
    return True


def problems(k, o, idx, board, skip=None):
    """clearance / hole-hole / edge problems of object o against the index (other nets; holes any net)"""
    out = []
    net = o.get('net') or ''
    for l in layers_of(k, o):
        for k2, q, tag in idx.near(k, o, l):
            if q is o or (skip and skip(q)):
                continue
            n2 = q.get('net') or ''
            if k == 'p' and k2 == 'p' and o['ref'] == q['ref']:
                continue
            if net and net == n2:
                continue
            clr = max(R.clearance(net, l), R.clearance(n2, l))
            g = J.gap(k, o, k2, q)
            if g < clr - 1e-4:
                out.append(('clearance', l, round(g, 4), clr, k2, q, tag))
    if k == 'v':
        for l in o['span']:
            for k2, q, tag in idx.near(k, o, l):
                if q is o or (skip and skip(q)):
                    continue
                if k2 == 'v':
                    dd = math.hypot(q['x'] - o['x'], q['y'] - o['y'])
                    if dd < 1e-6:
                        continue
                    d = dd - q['hole'] / 2 - o['hole'] / 2
                    if d < R.HOLE_HOLE - 1e-4:
                        out.append(('hole-hole', l, round(d, 4), R.HOLE_HOLE, k2, q, tag))
                elif k2 == 'p' and q['drill'] > 0 and not (q['net'] and q['net'] == o['net']):
                    d = math.hypot(q['x'] - o['x'], q['y'] - o['y']) - q['drill'] / 2 - o['hole'] / 2
                    if d < R.HOLE_HOLE - 1e-4:
                        out.append(('hole-pad', l, round(d, 4), R.HOLE_HOLE, k2, q, tag))
        if not edge_ok(board['w'], board['h'], o['x'], o['y'], o['size'] / 2):
            out.append(('edge', None, None, None, None, None, None))
    if k == 't':
        for x, y in ((o['x1'], o['y1']), (o['x2'], o['y2'])):
            if not edge_ok(board['w'], board['h'], x, y, o['w'] / 2):
                out.append(('edge', None, None, None, None, None, None))
        if o['w'] < R.width(o['net'], o['layer']) - 1e-6:
            out.append(('width', o['layer'], o['w'], R.width(o['net'], o['layer']), None, None, None))
    # dedupe hole problems found on several layers
    seen, res = set(), []
    for p in out:
        key = (p[0], id(p[5]))
        if key in seen:
            continue
        seen.add(key)
        res.append(p)
    return res


def touches(k, o, k2, q):
    """same-net galvanic contact (gap <= 0) on a shared layer"""
    if not set(layers_of(k, o)) & set(layers_of(k2, q)):
        return False
    return J.gap(k, o, k2, q) <= 1e-4


def via_in_smd_pad(v, pads):
    return J.via_pad_hits(v, [p for p in pads if not p['drill']])
