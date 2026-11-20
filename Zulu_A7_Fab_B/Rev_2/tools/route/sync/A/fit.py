"""fit.py: exact hand-routing helpers for Strategy A (rules = route_check / judge with SDRAM-D0..15 patched in).

    import fit; F = fit.Fit(model_json_or_dict)
    F.near(x, y, r=0.6, layers=None)          -> objects of every net near a point (debug listing)
    F.via_probs(net, x, y, pieces)           -> problems of a via stack, pieces = [(from, to, size, hole), ...]
    F.track_probs(net, layer, w, x1, y1, x2, y2)
    F.add_track(...), F.add_via(...)          -> commit into the working model + index; F.plan holds the additions
    F.search_via(net, pieces, x0, y0, x1, y1, step=0.005, must=callable) -> passing positions sorted by distance

Only exact geometry (geo.problems: clearance per router.clearance, hole-hole 0.24, edge 0.30, width).
"""
import json
import math
import os
import sys

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(A), 'prep', 'scripts'))
import geo  # noqa: E402

J, C, R = geo.J, geo.C, geo.R
STACK = J.STACK
LASER = {'TL2': ('Top Layer', 'L2-GND', 0.30, 0.15), 'L23': ('L2-GND', 'L3-SIG', 0.30, 0.15),
         'B34': ('L3-SIG', 'L4-SIG', 0.27, 0.15), 'L45': ('L4-SIG', 'L5-VCC3V3', 0.30, 0.15),
         'L5B': ('L5-VCC3V3', 'Bottom Layer', 0.30, 0.15), 'THR': ('Top Layer', 'Bottom Layer', 0.35, 0.20)}
STK = {'top_l3': ['TL2', 'L23'], 'top_l4': ['TL2', 'L23', 'B34'], 'l3_l4': ['B34'], 'l4_bot': ['L45', 'L5B'],
       'l3_bot': ['B34', 'L45', 'L5B'], 'top_bot_stack': ['TL2', 'L23', 'B34', 'L45', 'L5B'], 'top_l2': ['TL2'],
       'thr': ['THR'], 'l5_bot': ['L5B']}


def sp(fr, to):
    return STACK[STACK.index(fr):STACK.index(to) + 1]


class Fit:
    def __init__(self, M):
        if isinstance(M, str):
            M = json.load(open(M))
        self.M = M
        for v in M['vias']:
            v['span'] = J.span(v)
        self.idx = geo.Index()
        for p in M['pads']:
            self.idx.add('p', p)
        for t in M['tracks']:
            self.idx.add('t', t)
        for v in M['vias']:
            self.idx.add('v', v)
        self.plan = {'tracks': [], 'vias': []}

    def near(self, x, y, r=0.6, layers=None):
        probe = {'x': x, 'y': y, 'size': 2 * r, 'hole': 0, 'net': '', 'span': layers or STACK}
        out = []
        seen = set()
        for l in probe['span']:
            for k, o, _ in self.idx.near('v', probe, l):
                if id(o) in seen:
                    continue
                seen.add(id(o))
                g = J.gap('v', dict(probe, size=0), k, o)
                if g <= r:
                    out.append((round(g, 4), J.desc(k, o) if k != 'v' else J.desc('v', o)))
        return sorted(out)

    def _via_objs(self, net, x, y, pieces):
        return [{'net': net, 'x': x, 'y': y, 'size': LASER[p][2] if isinstance(p, str) else p[2],
                 'hole': LASER[p][3] if isinstance(p, str) else p[3],
                 'span': sp(*(LASER[p][:2] if isinstance(p, str) else p[:2]))} for p in pieces]

    def via_probs(self, net, x, y, pieces):
        out = []
        for v in self._via_objs(net, x, y, pieces):
            out += geo.problems('v', v, self.idx, self.M['board'])
        return out

    def track_probs(self, net, layer, w, x1, y1, x2, y2):
        t = {'net': net, 'layer': layer, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
        return geo.problems('t', t, self.idx, self.M['board'])

    def add_track(self, net, layer, w, x1, y1, x2, y2, check=True):
        t = {'net': net, 'layer': layer, 'w': w, 'x1': round(x1, 4), 'y1': round(y1, 4), 'x2': round(x2, 4),
             'y2': round(y2, 4)}
        if check:
            pr = geo.problems('t', t, self.idx, self.M['board'])
            if pr:
                raise ValueError('track %s: %s' % (t, [p[:4] + (J.desc(p[4], p[5]) if p[5] else '',) for p in pr]))
        self.M['tracks'].append(t)
        self.idx.add('t', t)
        self.plan['tracks'].append(t)
        return t

    def add_via(self, net, x, y, pieces, check=True):
        vs = self._via_objs(net, round(x, 4), round(y, 4), pieces)
        if check:
            pr = []
            for v in vs:
                pr += geo.problems('v', v, self.idx, self.M['board'])
            if pr:
                raise ValueError('via %s %.4f,%.4f: %s' % (net, x, y, [p[:4] + (J.desc(p[4], p[5]) if p[5] else '',)
                                                                      for p in pr]))
        for v in vs:
            self.M['vias'].append(v)
            self.idx.add('v', v)
            self.plan['vias'].append({'net': net, 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'],
                                      'from': v['span'][0], 'to': v['span'][-1]})
        return vs

    def search_via(self, net, pieces, x0, y0, x1, y1, step=0.005, must=None, limit=20, cx=None, cy=None):
        cx = (x0 + x1) / 2 if cx is None else cx
        cy = (y0 + y1) / 2 if cy is None else cy
        res = []
        nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
        for i in range(nx + 1):
            for j in range(ny + 1):
                x, y = round(x0 + i * step, 4), round(y0 + j * step, 4)
                if must and not must(x, y):
                    continue
                if not self.via_probs(net, x, y, pieces):
                    res.append((math.hypot(x - cx, y - cy), x, y))
        res.sort()
        return res[:limit]

    def smd_hits(self, x, y, size, span):
        smd = [p for p in self.M['pads'] if not p['drill']]
        return J.via_pad_hits({'x': x, 'y': y, 'size': size, 'span': span}, smd)
