"""Strategy E helpers: model apply, exact clearance check of a set of items against a model (route_check rules)."""
import json
import math
import os
import sys

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK
REV2 = os.path.join(TOOLS, 'route', 'rev2')
PREP = os.path.join(REV2, 'prep')
EDIR = os.path.join(REV2, 'E')


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def tkey(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4), round(t['w'], 4))


def vkey(v):
    sp = span(v)
    return (v['net'], round(v['x'], 4), round(v['y'], 4), sp[0], sp[-1])


def load(p):
    return json.load(open(p))


def dump(o, p, indent=None):
    json.dump(o, open(p, 'w'), indent=indent)


def apply(base, rm_t=(), rm_v=(), add_t=(), add_v=()):
    rt, rv = {tkey(t) for t in rm_t}, {vkey(v) for v in rm_v}
    M = dict(base)
    M['tracks'] = [t for t in base['tracks'] if tkey(t) not in rt] + [dict(t) for t in add_t]
    M['vias'] = [v for v in base['vias'] if vkey(v) not in rv] + [dict(v, span=span(v)) for v in add_v]
    return M


class Checker:
    """exact clearance of candidate items against a model's copper (pads, tracks, vias), route_check rules"""

    def __init__(self, M, cell=1.0):
        self.M = M
        self.cell = cell
        self.idx = {l: {} for l in STACK}
        self.holes = []
        for p in M['pads']:
            ls = p['layers'] or (STACK if p['drill'] > 0 else [])
            r = max(p['w'], p['h']) / 2
            for l in ls:
                self._ins(l, ('p', p), p['x'] - r, p['y'] - r, p['x'] + r, p['y'] + r)
            if p['drill'] > 0:
                self.holes.append(('p', p))
        for t in M['tracks']:
            self.add_track(t)
        for v in M['vias']:
            self.add_via(v)

    def _ins(self, l, o, x0, y0, x1, y1):
        c = self.cell
        for i in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for j in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                self.idx[l].setdefault((i, j), []).append(o)

    def add_track(self, t):
        r = t['w'] / 2
        self._ins(t['layer'], ('t', t), min(t['x1'], t['x2']) - r, min(t['y1'], t['y2']) - r,
                  max(t['x1'], t['x2']) + r, max(t['y1'], t['y2']) + r)

    def add_via(self, v):
        v = dict(v, span=span(v))
        r = v['size'] / 2
        for l in v['span']:
            self._ins(l, ('v', v), v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r)
        self.holes.append(('v', v))
        return v

    def near(self, l, x0, y0, x1, y1):
        c = self.cell
        seen = set()
        for i in range(int(math.floor((x0 - 0.5) / c)), int(math.floor((x1 + 0.5) / c)) + 1):
            for j in range(int(math.floor((y0 - 0.5) / c)), int(math.floor((y1 + 0.5) / c)) + 1):
                for o in self.idx[l].get((i, j), ()):
                    if id(o[1]) not in seen:
                        seen.add(id(o[1]))
                        yield o

    @staticmethod
    def gap(kind, o, geom):
        if geom[0] == 's':
            s, r = geom[1:5], geom[5]
            if kind == 'p':
                return C.pad_seg(o, s) - r
            if kind == 't':
                return C.seg_seg(s, (o['x1'], o['y1'], o['x2'], o['y2'])) - r - o['w'] / 2
            return C.seg_dist(s[0], s[1], s[2], s[3], o['x'], o['y']) - r - o['size'] / 2
        x, y, r = geom[1:4]
        if kind == 'p':
            return C.pad_point(o, x, y) - r
        if kind == 't':
            return C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) - r - o['w'] / 2
        return math.hypot(o['x'] - x, o['y'] - y) - r - o['size'] / 2

    def clr(self, n1, n2, l):
        return max(R.clearance(n1, l), R.clearance(n2, l))

    def edge_ok(self, x, y, r):
        W, H = self.M['board']['w'], self.M['board']['h']
        if x - r < R.EDGE or y - r < R.EDGE or x + r > W - R.EDGE or y + r > H - R.EDGE:
            return False
        for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
            if abs(x - cx) < 1.2 + r and abs(y - cy) < 1.2 + r:
                return False
        return True

    def track_bad(self, t, skip=()):
        out = []
        r = t['w'] / 2
        geom = ('s', t['x1'], t['y1'], t['x2'], t['y2'], r)
        for k, o in self.near(t['layer'], min(t['x1'], t['x2']) - r, min(t['y1'], t['y2']) - r,
                              max(t['x1'], t['x2']) + r, max(t['y1'], t['y2']) + r):
            if o is t or id(o) in skip:
                continue
            if o['net'] and o['net'] == t['net']:
                continue
            g = self.gap(k, o, geom)
            if g < self.clr(t['net'], o['net'] or '', t['layer']) - 1e-4:
                out.append((k, o, g))
        for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            if not self.edge_ok(x, y, r):
                out.append(('edge', None, 0))
        return out

    def via_bad(self, v, skip=()):
        v = dict(v, span=span(v))
        out = []
        r = v['size'] / 2
        geom = ('c', v['x'], v['y'], r)
        for l in v['span']:
            for k, o in self.near(l, v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r):
                if id(o) in skip:
                    continue
                if o['net'] and o['net'] == v['net']:
                    continue
                g = self.gap(k, o, geom)
                if g < self.clr(v['net'], o['net'] or '', l) - 1e-4:
                    out.append((k, o, g))
        for k, o in self.holes:
            if id(o) in skip:
                continue
            if k == 'v':
                if not (set(o['span']) & set(v['span'])):
                    continue
                d0 = math.hypot(o['x'] - v['x'], o['y'] - v['y'])
                if d0 < 1e-6:
                    continue
                d = d0 - o['hole'] / 2 - v['hole'] / 2
            else:
                if o['net'] == v['net'] and False:
                    continue
                if o['net'] == v['net']:
                    continue
                d = math.hypot(o['x'] - v['x'], o['y'] - v['y']) - o['drill'] / 2 - v['hole'] / 2
            if d < R.HOLE_HOLE - 1e-4:
                out.append(('hole', o, d))
        if not self.edge_ok(v['x'], v['y'], r):
            out.append(('edge', None, 0))
        return out


def smd_pads(M, layer):
    return [p for p in M['pads'] if not p['drill'] and layer in (p['layers'] or [])]


def via_in_pads(M, v):
    """SMD pads (any net) whose copper the via's land overlaps on the via's outer layers"""
    sp = span(v)
    out = []
    for l in ('Top Layer', 'Bottom Layer'):
        if l not in sp:
            continue
        for p in smd_pads(M, l):
            if abs(p['x'] - v['x']) > 3 or abs(p['y'] - v['y']) > 3:
                continue
            if C.pad_point(p, v['x'], v['y']) < v['size'] / 2 - 1e-6:
                out.append((l, p))
    return out
