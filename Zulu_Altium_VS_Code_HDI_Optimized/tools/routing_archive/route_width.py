# -*- coding: utf-8 -*-
"""How wide can this net still be routed from A to B?  A width-aware reachability gate.

    python tools/route_width.py --net VU --from C78-2,U8-10,U8-11 --to X2-22
    python tools/route_width.py --net VCC1V0 --from C84-2,L3-2 --to L3-SIG:40,41.5,5,23 --widen L3-SIG,L4-SIG
    python tools/route_width.py --net VU --from U8-10 --to X2-22 --layers Bottom     Bottom only
        --inputs F      another route_inputs.json (e.g. tools/block_place.py --write-inputs)
        --plans a.json  routing plans whose copper counts as placed (comma separated)
        --widen LIST    layers the trial width applies to (default: all four); the others stay at
                        the net's per-layer Width minimum
        --hi W          upper bound of the search (default 1.6 mm)

route_reach.py asks "is there a 3 mil path?"; this asks "at what width?", which is the question a
power feed actually poses -- VU's inner minimum alone is 1.10 mm, and a corridor that carries 3 mil
may not carry that.  A binary search (7 steps, ~0.01 mm) over the same raster: per layer, cells
within clearance + w/2 of foreign copper are blocked, the net's own pads/vias/TH pads are carved,
components are joined across layers at legal via cells, and the answer is whether the source pads
and the target share a component.  Grown from the throwaway scripts two reviewers wrote during the
2026-09-15 regulator-block run (blk_exits/review_mfg/wreach*.py), which is where its numbers -- VU
to X2-22 at 1.588 mm on the outer layers, 1.225 mm on Bottom alone -- first came from.
"""
import io
import json
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_reach as rr
import hdi

RI = os.path.join(HERE, 'route_inputs.json')
LAY = rr.LAYERS


class World(object):
    def __init__(self, inp, plans):
        self.inp = inp
        self.R = rr.Raster(inp['outline'])
        self.objs = rr.world(inp, plans)
        # one via raster per candidate span hdi.json allows (2026-09-29, HDI); via_cov0 / edge_v stay
        # the through raster for stage3/stage6 corr.py
        self.H = hdi.load(inp)
        self.spans = [S for S in self.H.allowed() if len(hdi.signal_layers(S)) >= 2]
        _, self.via_cov, _, self.edge_vs = rr.base_rasters(self.R, inp, self.objs, self.spans)
        self.via_cov0, self.edge_v = self.via_cov.get(hdi.THROUGH), self.edge_vs.get(hdi.THROUGH)
        if self.via_cov0 is None:
            raise SystemExit('tools/hdi.json does not list the through span: route_width.World (and the stage3..6 '
                             'corr.py via_ok_mask / via_sites / widest2 built on it) need its raster')
        self.X = self.R.x0 + np.arange(self.R.nx) * rr.CELL
        self.Y = self.R.y0 + np.arange(self.R.ny) * rr.CELL

    def blocked(self, net, layer, w):
        """cells a track of width w on this layer may not use"""
        R = self.R
        m = np.zeros((R.ny, R.nx), bool)
        for o in self.objs:
            if o['net'] == net and not o.get('keepout'):
                continue
            if layer not in o['layers']:
                continue
            s = rr.shape_mask(R, o, rr.clr_on(o, layer) + w / 2)
            if s is not None:
                m[s[0]] |= s[1]
        ol = self.inp['outline']
        e = self.inp.get('edge_clearance', 0.25)
        m |= ((self.Y < ol['y0'] + e + w / 2) | (self.Y > ol['y1'] - e - w / 2))[:, None]
        m |= ((self.X < ol['x0'] + e + w / 2) | (self.X > ol['x1'] - e - w / 2))[None, :]
        return m

    def reaches(self, net, widths, layers, src_pads, target):
        """can the source pads' copper reach `target` at these per-layer widths?"""
        R = self.R
        own = [o for o in self.objs if o['net'] == net]
        tc = [np.zeros((R.ny, R.nx), np.int16) for _ in LAY]
        vc = {S: c.copy() for S, c in self.via_cov.items()}
        rr.accumulate(R, own, -1, tc, vc, own_net=net, H=self.H)
        # the net's own copper is not a free pass -- a wide track must clear foreign copper
        # everywhere -- but its pads, its through-hole pads and its vias are where it starts
        carve = [o for o in own if o.get('pad') or o.get('via')]
        oc = rr.own_cells(R, carve)
        free = []
        for i, L in enumerate(LAY):
            if L not in layers:
                free.append(np.zeros((R.ny, R.nx), bool))
                continue
            free.append((~self.blocked(net, L, widths[L])) | oc[i])
        labels, off = [], 0
        st = np.ones((3, 3), int)
        for i in range(4):
            lab, n = ndimage.label(free[i], structure=st)
            lab = lab.astype(np.int64)
            lab[lab > 0] += off
            labels.append(lab)
            off += n
        parent = np.arange(off + 1)

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(ids):
            ids = sorted(set(int(v) for v in ids if v > 0))
            for v in ids[1:]:
                a, b = find(ids[0]), find(v)
                if a != b:
                    parent[b] = a
        for S in vc:                         # a layer change joins only the signal layers of its span
            idx = [LAY.index(L) for L in hdi.signal_layers(S)]
            ys, xs = np.nonzero((vc[S] <= 0) & ~self.edge_vs[S])
            for row in np.unique(np.stack([labels[i][ys, xs] for i in idx], axis=1), axis=0):
                union(row)
        for o in carve:                      # an own via or TH pad joins the layers it spans
            if o.get('via') or len(o['layers']) == 4:
                s = rr.shape_mask(R, o, 0.0)
                if s is not None:
                    union([l for L in o['layers'] for l in np.unique(labels[LAY.index(L)][s[0]][s[1]])])

        def roots(o):
            s = rr.shape_mask(R, o, rr.CELL * 0.75)
            if s is None:
                return set()
            return {find(int(l)) for L in o['layers'] for l in np.unique(labels[LAY.index(L)][s[0]][s[1]]) if l > 0}
        src = set()
        for o in own:
            if o.get('pad') and '%s-%s' % (o['ref'], o['name']) in src_pads:
                src |= roots(o)
        if not src:
            return False
        if isinstance(target, str):
            hit = [o for o in own if o.get('pad') and '%s-%s' % (o['ref'], o['name']) == target]
            if not hit:
                raise SystemExit('route_width: %s has no pad %s' % (net, target))
            return bool(roots(hit[0]) & src)
        L, x0, x1, y0, y1 = target
        i = LAY.index(L)
        j0, j1 = int((y0 - R.y0) / rr.CELL), int((y1 - R.y0) / rr.CELL) + 1
        i0, i1 = int((x0 - R.x0) / rr.CELL), int((x1 - R.x0) / rr.CELL) + 1
        return any(find(int(l)) in src for l in np.unique(labels[i][j0:j1, i0:i1]) if l > 0)


def rule_widths(inp, net):
    r = inp['nets'].get(net)
    if r is None:                       # a net no routing stage owns yet: the global Width rule
        return dict((L, 0.0762) for L in LAY)
    w = r['width']
    return {'Top': w['top_min'], 'L3-SIG': w['inner_min'], 'L4-SIG': w['inner4_min'], 'Bottom': w['bottom_min']}


def max_width(world, net, src, target, layers, widen, hi=1.6, steps=7):
    base = rule_widths(world.inp, net)

    def W(w):
        return dict((L, max(base[L], w) if L in widen else base[L]) for L in LAY)
    if not world.reaches(net, W(0.0), layers, src, target):
        return None
    lo = 0.0
    for _ in range(steps):
        mid = (lo + hi) / 2
        if world.reaches(net, W(mid), layers, src, target):
            lo = mid
        else:
            hi = mid
    return lo


def parse_target(s):
    if ':' not in s:
        return s
    layer, box = s.split(':', 1)
    x0, x1, y0, y1 = [float(v) for v in box.split(',')]
    return (layer, x0, x1, y0, y1)


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    net = opt('--net')
    src = (opt('--from') or '').split(',')
    target = parse_target(opt('--to') or '')
    if not net or not src[0] or not target:
        print(__doc__)
        return 2
    inp = json.load(io.open(opt('--inputs', RI), encoding='utf-8'))
    plans = [json.load(io.open(p, encoding='utf-8')) for p in (opt('--plans', '') or '').split(',') if p]
    layers = tuple((opt('--layers') or ','.join(LAY)).split(','))
    widen = tuple((opt('--widen') or ','.join(LAY)).split(','))
    w = max_width(World(inp, plans), net, src, target, layers, widen, float(opt('--hi', '1.6')))
    print('%-8s %-24s -> %-28s layers %-22s widen %-18s  %s' % (
        net, ','.join(src), target if isinstance(target, str) else str(target), ','.join(layers), ','.join(widen),
        ('max width %.3f mm' % w) if w is not None else 'UNREACHABLE even at the rule minimum'))
    return 0 if w is not None else 1


if __name__ == '__main__':
    sys.exit(main())
