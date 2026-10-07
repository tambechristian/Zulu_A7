# -*- coding: utf-8 -*-
"""Stage-4 plan builder (a copy of tools/stage3/lib.py with the board guard moved on): every width is measured with route_emit's own distance code (segw.maxwidth)
against the board as it will stand -- plan removals applied, remedy-(b) replacements added -- plus the
plan copper already laid.  A segment gets min(wish, rule max, the widest width that keeps CLR to every
foreign object); if that is under the rule minimum the clearance target is relaxed step by step to the
0.09 rule, and the segment is reported."""
import io, json, math, os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import segw

INP0 = segw.load()
GRID = 0.005


class Plan(object):
    def __init__(self, remove=None, replace_vias=(), replace_tracks=(), base_plans=()):
        self.remove = remove or {'vias': [], 'tracks': []}
        self.VIAS, self.TRACKS, self.REPORT = [], [], []
        # base_plans: other plans (the trunk, a neighbouring region) whose copper counts for clearance and
        # as same-net copper but is NOT part of this plan and never dumped
        self.BASE_VIAS = [dict(v) for bp in base_plans for v in bp.get('vias', [])]
        self.BASE_TRACKS = [dict(t) for bp in base_plans for t in bp.get('tracks', [])]
        inp = copy.deepcopy(INP0)
        rk = lambda v: (v['net'], round(v['x'], 4), round(v['y'], 4))
        rv = {rk(v) for v in self.remove.get('vias', [])}
        tk = lambda t: (t['net'], t['layer']) + tuple(sorted(((round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4)))))
        rt = {tk(t) for t in self.remove.get('tracks', [])}
        n0v, n0t = len(inp['vias']), len(inp['tracks'])
        inp['vias'] = [v for v in inp['vias'] if rk(v) not in rv]
        inp['tracks'] = [t for t in inp['tracks'] if tk(t) not in rt]
        assert n0v - len(inp['vias']) == len(rv) and n0t - len(inp['tracks']) == len(rt), 'removal mismatch'
        self.INP = inp
        for v in replace_vias:
            self.via(v['net'], v['x'], v['y'], check=False)
        for t in replace_tracks:
            self.TRACKS.append(dict(t))

    def rule(self, net, layer):
        w = self.INP['nets'].get(net, {}).get('width')
        if w is None:
            return 0.0762, 9.9
        if layer == 'Top':
            return w['top_min'], w['top_max']
        if layer == 'Bottom':
            return w['bottom_min'], w['bottom_max']
        if layer == 'L3-SIG':
            return w['inner_min'], w['inner_max']
        return w['inner4_min'], w['inner4_max']

    def via(self, net, x, y, check=True):
        self.VIAS.append(dict(net=net, x=round(x, 4), y=round(y, 4)))

    def maxw(self, net, layer, seg):
        return segw.maxwidth(self.INP, net, layer, seg, plan_tracks=self.BASE_TRACKS + self.TRACKS,
                             plan_vias=self.BASE_VIAS + self.VIAS)

    def run(self, net, layer, pts, wish=9.9, tag='', clr=0.12, floor=0.09, exact=None):
        lo, hi = self.rule(net, layer)
        for a, b in zip(pts, pts[1:]):
            seg = (a[0], a[1], b[0], b[1])
            m, who = self.maxw(net, layer, seg)
            if exact is not None:
                w = exact
                c_used = (m - w) / 2 + 0.09
            else:
                c = clr
                while True:
                    cap = min(wish, hi, m - 2 * (c - 0.09))
                    w = math.floor(cap / GRID + 1e-9) * GRID
                    if w >= lo - 1e-9 or c <= floor + 1e-9:
                        break
                    c = max(floor, c - 0.005)
                if w < lo - 1e-9 and (m - 2 * (floor - 0.09)) >= lo - 1e-9:
                    w = lo
                c_used = (m - w) / 2 + 0.09
            self.TRACKS.append(dict(net=net, layer=layer, x1=round(a[0], 4), y1=round(a[1], 4),
                                    x2=round(b[0], 4), y2=round(b[1], 4), width=round(w, 4)))
            self.REPORT.append(dict(net=net, layer=layer, tag=tag, seg=seg, w=round(w, 4),
                                    L=math.hypot(b[0] - a[0], b[1] - a[1]), max=round(m, 4),
                                    who=who[0] if who else '-', clr=round(c_used, 4), short=w < lo - 1e-9))

    def dump(self, path):
        out = dict(vias=self.VIAS, tracks=self.TRACKS)
        if self.remove.get('vias') or self.remove.get('tracks'):
            out['remove'] = self.remove
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(out, indent=1))

    def print_report(self, only_tight=False):
        for r in self.REPORT:
            if only_tight and r['clr'] >= 0.12 - 1e-6 and not r['short']:
                continue
            s = r['seg']
            print('%-7s %-7s %-30s (%.3f,%.3f)-(%.3f,%.3f) w %.3f len %.2f max %.3f clr %.3f %s%s' % (
                r['net'], r['layer'], r['tag'][:30], s[0], s[1], s[2], s[3], r['w'], r['L'], r['max'], r['clr'], r['who'][:40],
                '  <-- BELOW RULE MIN' if r['short'] else ''))
