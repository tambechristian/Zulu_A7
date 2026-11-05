"""Local finisher for an almost complete plan (2026-11-05): closes the open connections of <seed> on <model> by
PARTIAL rip-up. router.py rips whole nets and re-routes them from scratch, which cascades on a full board; this
tool cuts a victim only where the new path crosses it and re-joins it locally, recursively (depth-limited search with
backtracking, conflict-directed: a victim that cannot be re-joined becomes immovable for the next attempt).

    python tools/finish.py --model model.json --seed plan.json --out out.json --clear 0.077 --slack 0.005
                           --laser-small 0.25/0.10 [--depth 3] [--alts 3] [--rc 0.4] [--maxv 4] [--soft 1.0]
                           [--pops 1500000] [--lpops 400000] [--tlimit 1800] [--passes 2] [--nets A,B]

For an open connection of net N:
  1. hard route (the live board); done if it works
  2. probe: the cheapest path through rippable copper (router.py's base=True route with --soft), with GND / VCC3V3,
     the nets locked by the levels above and the victims that already failed painted hard
  3. cut every victim within --rc of the cells where the path conflicts with it (tie_cut.clip), drop its pad-less
     fragments, route N hard along the freed corridor, then re-join each victim the same way one level down
  4. any failure restores the snapshot and marks the failing victim immovable for the next probe
The result is an ordinary plan (vias / tracks / remove / log): judge it with route_check.py and plan_open.py.
GND / VCC3V3 tie copper the router added is a victim like any other (re-tied with a plane via after the cut) unless
--planes-hard. Dangling stub tails stay (prune afterwards). Router.via_ok is replaced by a numpy version (same test)."""
import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402
from tie_cut import clip  # noqa: E402

G = R.G
PLANES = {'GND', 'VCC3V3'}


class Timeout(Exception):
    pass


# ---- a fast Router.via_ok ------------------------------------------------------------------------------------------
# router.py's via_ok walks every via of the board in Python for each candidate (about 0.3 ms); on a base=True probe
# the land test passes almost everywhere, so the probe ran at a few hundred expansions a second. Same test, numpy.
_BIT = {l: 1 << i for i, l in enumerate(R.STACK)}
_commit0, _rip0 = R.Router.commit, R.Router.rip


def _commit(self, *a, **k):
    r = _commit0(self, *a, **k)
    self.vver = getattr(self, 'vver', 0) + 1
    return r


def _rip(self, nets):
    r = _rip0(self, nets)
    self.vver = getattr(self, 'vver', 0) + 1
    return r


def _via_ok(self, net, kind, x, y, D, win, base=False):
    i0, _, j0, _ = win
    i, j = int(round(y / G)) - i0, int(round(x / G)) - j0
    objs, occ, _ = R.VIAS[kind]
    land = max(o[2] for o in objs) / 2
    for l in occ:
        a = D[l]
        if not (0 <= i < a.shape[0] and 0 <= j < a.shape[1]) or a[i, j] < land + R.MARGIN:
            return False
    hole = max(o[3] for o in objs) / 2
    key = (base, getattr(self, 'vver', 0))
    vc = getattr(self, '_vc', {})
    if key not in vc:
        vl = self.B.base_vias if base else self.B.vias
        vc = {k: v for k, v in vc.items() if k[1] == key[1]}
        vc[key] = (np.array([v[0] for v in vl]), np.array([v[1] for v in vl]), np.array([v[2] for v in vl]) / 2,
                   np.array([sum(_BIT[l] for l in v[3]) for v in vl], np.int64))
        self._vc = vc
    X, Y, Hh, S = vc[key]
    if len(X):
        om = sum(_BIT[l] for l in occ)
        dd = np.hypot(X - x, Y - y)
        if ((dd > 1e-6) & ((S & om) != 0) & (dd < R.HOLE_HOLE + hole + Hh + 0.001)).any():
            return False
    hs = getattr(self, '_holes', None)
    if hs is None:
        hs = self._holes = (np.array([h[0] for h in self.B.holes]), np.array([h[1] for h in self.B.holes]),
                            np.array([h[2] for h in self.B.holes]) / 2)
    if len(hs[0]) and (np.hypot(hs[0] - x, hs[1] - y) < R.HOLE_HOLE + hole + hs[2]).any():
        return False
    return True


R.Router.commit, R.Router.rip, R.Router.via_ok = _commit, _rip, _via_ok


def span(v):
    return R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]


class Fin:
    def __init__(self, a):
        self.a = a
        R.CLEAR = a.clear
        R.MARGIN = a.slack
        if a.laser_small:
            R.add_small_lasers(*[float(v) for v in a.laser_small.split('/')])
        M = json.load(open(a.model))
        P = json.load(open(a.seed))
        self.removed = P.get('remove', [])
        if self.removed:
            def same(t, r):
                return t['net'] == r['net'] and t['layer'] == r['layer'] and \
                    {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == \
                    {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))}
            M['tracks'] = [t for t in M['tracks'] if not any(same(t, r) for r in self.removed)]
        self.M = M
        self.B = R.Board(M)
        self.Rt = R.Router(self.B, a.pops)
        self.Rt.soft = a.soft
        self.Rt.out_t += P['tracks']
        self.Rt.out_v += P['vias']
        self.Rt.rip(set())
        self.cache = {}
        self.deadline = 1e18
        self.log = []
        self.ind = 0
        self.disks = {}

    # ---- state ---------------------------------------------------------------------------------------------------
    def say(self, msg):
        line = '%s%s' % ('  ' * self.ind, msg)
        print(line, flush=True)
        self.log.append(line)

    def snap(self):
        return list(self.Rt.out_t), list(self.Rt.out_v)

    def restore(self, s):
        self.Rt.out_t, self.Rt.out_v = list(s[0]), list(s[1])
        self.Rt.rip(set())

    def full(self):
        Mx = dict(self.M)
        Mx['tracks'] = self.M['tracks'] + self.Rt.out_t
        Mx['vias'] = self.M['vias'] + [dict(v, span=span(v)) for v in self.Rt.out_v]
        return Mx

    def opens(self):
        return C.open_count(C.islands(self.full()))

    def netmodel(self, net):
        """a model holding only this net's copper (indexes of islands refer to it), and the router copper in it"""
        M = self.M
        if net not in self.cache:
            self.cache[net] = ([p for p in M['pads'] if p['net'] == net], [t for t in M['tracks'] if t['net'] == net],
                               [v for v in M['vias'] if v['net'] == net])
        P_, T_, V_ = self.cache[net]
        ot = [t for t in self.Rt.out_t if t['net'] == net]
        ov = [v for v in self.Rt.out_v if v['net'] == net]
        Mn = {'pads': P_, 'tracks': T_ + ot, 'vias': V_ + [dict(v, span=span(v)) for v in ov],
              'planes': M['planes'], 'board': M['board']}
        return Mn, len(T_), len(V_), ot, ov

    def isl(self, net):
        Mn = self.netmodel(net)[0]
        return Mn, C.islands(Mn).get(net, [])

    def drop_fragments(self, net):
        """remove the router copper of `net` that no longer belongs to an island with a pad"""
        Mn, nT, nV, ot, ov = self.netmodel(net)
        gs = C.islands(dict(Mn, planes={})).get(net, [])
        used_t = {i for g in gs for i in g['tracks']}
        used_v = {i for g in gs for i in g['vias']}
        dead_t = {id(t) for i, t in enumerate(ot) if nT + i not in used_t}
        dead_v = {id(v) for i, v in enumerate(ov) if nV + i not in used_v}
        if dead_t or dead_v:
            self.Rt.out_t = [t for t in self.Rt.out_t if id(t) not in dead_t]
            self.Rt.out_v = [v for v in self.Rt.out_v if id(v) not in dead_v]
        return len(dead_t) + len(dead_v)

    # ---- geometry ------------------------------------------------------------------------------------------------
    def gdist(self, Mn, g, c):
        d = [math.hypot(Mn['pads'][i]['x'] - c[0], Mn['pads'][i]['y'] - c[1]) for i in g['pads']]
        d += [C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], c[0], c[1]) for t in (Mn['tracks'][i] for i in g['tracks'])]
        d += [math.hypot(Mn['vias'][i]['x'] - c[0], Mn['vias'][i]['y'] - c[1]) for i in g['vias']]
        return min(d) if d else 1e9

    def disk(self, c):
        if c not in self.disks:
            yy, xx = np.mgrid[-c:c + 1, -c:c + 1]
            self.disks[c] = np.hypot(xx, yy) * G
        return self.disks[c]

    def hard_raster(self, nets):
        """the base raster plus the router copper of `nets` (immovable for a probe)"""
        B, Rt = self.B, self.Rt
        sr, sv = B.r, B.vias
        B.r = {l: a.copy() for l, a in B.base.items()}
        B.vias = list(B.base_vias)
        for t in Rt.out_t:
            if t['net'] in nets:
                B.add_track(t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
        for v in Rt.out_v:
            if v['net'] in nets:
                sp = span(v)
                B.add_via_land(v['net'], v['x'], v['y'], v['size'], sp)
                B.vias.append((v['x'], v['y'], v['hole'], set(sp), v['net']))
        hr, hv = B.r, B.vias
        B.r, B.vias = sr, sv
        return hr, hv

    def conflicts(self, net, path, base, base_vias):
        """{victim: [(x, y, layers)]}: where the path's copper comes inside the clearance of movable router copper"""
        B = self.B
        n = B.nid[net]
        out = defaultdict(set)
        for l, x, y, kind in path:
            items = [([l], R.width(net, l) / 2)]
            if kind:
                objs, occ, _ = R.VIAS[kind]
                items.append((list(occ), max(o[2] for o in objs) / 2))
            for layers, half in items:
                c = int(math.ceil((half + 0.20 + R.MARGIN) / G)) + 1
                i, j = int(round(y / G)), int(round(x / G))
                i0, i1, j0, j1 = max(0, i - c), min(B.H, i + c + 1), max(0, j - c), min(B.W, j + c + 1)
                dd = self.disk(c)[i0 - (i - c):i1 - (i - c), j0 - (j - c):j1 - (j - c)]
                for ll in layers:
                    cur, bs = B.r[ll][i0:i1, j0:j1], base[ll][i0:i1, j0:j1]
                    mv = (cur != bs) & (cur > 0) & (cur != n)
                    if not mv.any():
                        continue
                    for oid in np.unique(cur[mv]):
                        vn = B.net_by_nid[int(oid)]
                        clr = max(R.clearance(net, ll), R.clearance(vn, ll)) if ll in R.ROUTE else R.CLEAR
                        if (dd[mv & (cur == oid)] < half + clr + R.MARGIN).any():
                            out[vn].add((round(x, 1), round(y, 1), tuple(layers)))
            if kind:                                   # hole to hole against movable vias
                objs, occ, _ = R.VIAS[kind]
                hole = max(o[3] for o in objs) / 2
                fixed = {(v[0], v[1]) for v in base_vias}
                for vx, vy, vh, vspan, vnet in B.vias:
                    d = math.hypot(vx - x, vy - y)
                    if 1e-6 < d < R.HOLE_HOLE + hole + vh / 2 + 0.001 and vspan & set(occ) and vnet != net and \
                            (vx, vy) not in fixed:
                        out[vnet].add((round(vx, 1), round(vy, 1), tuple(vspan)))
        return {k: sorted(v) for k, v in out.items()}

    def cut(self, conf, rc):
        Rt = self.Rt
        kill = set()                                   # (net, x, y) of vias to remove, the whole stack at the point
        for v in Rt.out_v:
            pts = conf.get(v['net'])
            if not pts:
                continue
            sp = set(span(v))
            if any(sp & set(ls) and math.hypot(v['x'] - x, v['y'] - y) < rc + v['size'] / 2 for x, y, ls in pts):
                kill.add((v['net'], round(v['x'], 4), round(v['y'], 4)))
        Rt.out_v = [v for v in Rt.out_v if (v['net'], round(v['x'], 4), round(v['y'], 4)) not in kill]
        new_t = []
        for t in Rt.out_t:
            pts = conf.get(t['net'])
            if not pts:
                new_t.append(t)
                continue
            pieces = [t]
            for x, y, ls in pts:
                if t['layer'] not in ls:
                    continue
                nxt = []
                for p in pieces:
                    if C.seg_dist(p['x1'], p['y1'], p['x2'], p['y2'], x, y) < rc:
                        nxt += [q for q in clip(p, x, y, rc)
                                if math.hypot(q['x2'] - q['x1'], q['y2'] - q['y1']) > 0.03 and
                                not (math.hypot(q['x1'] - x, q['y1'] - y) < rc - 1e-6 and
                                     math.hypot(q['x2'] - x, q['y2'] - y) < rc - 1e-6)]
                    else:
                        nxt.append(p)
                pieces = nxt
            new_t += pieces
        Rt.out_t = new_t

    # ---- routing -------------------------------------------------------------------------------------------------
    def hard(self, net, Mn, ga, gb, wins, pops):
        self.Rt.max_pops = pops
        for win in wins:
            r = self.Rt.route(net, R.island_mask(self.B, Mn, ga, win), R.island_mask(self.B, Mn, gb, win), win)
            if r:
                return r
        return None

    def probe(self, net, Mn, ga, gb, wins, hardnets):
        B, Rt = self.B, self.Rt
        tb, tbv = B.base, B.base_vias
        hr, hv = self.hard_raster(hardnets)
        B.base, B.base_vias = hr, hv
        Rt.vver = getattr(Rt, 'vver', 0) + 1
        Rt.max_pops = self.a.pops
        Rt.hw = self.a.hw
        try:
            r = None
            for win in wins:
                r = Rt.route(net, R.island_mask(B, Mn, ga, win), R.island_mask(B, Mn, gb, win), win, base=True)
                if r:
                    break
            if not r:
                return None
            return r[0], self.conflicts(net, r[0], hr, hv)
        finally:
            B.base, B.base_vias = tb, tbv
            Rt.vver += 1
            Rt.hw = 1.0

    def kick(self, net, x, y, r):
        """cut `net` within r of (x, y) on every layer and re-join it with a wider raster allowance first (a copper
        object route_check found a hair inside the clearance: the 0.005 allowance does not cover every raster case)"""
        snap = self.snap()
        before = len(self.isl(net)[1])
        self.cut({net: [(x, y, tuple(R.STACK))]}, r)
        self.drop_fragments(net)
        self.Rt.rip(set())
        if len(self.isl(net)[1]) <= before:
            self.say('kick %s at %.3f,%.3f: nothing to re-join after the cut' % (net, x, y))
            return True
        for m in (0.02, 0.012, self.a.slack):
            s2 = self.snap()
            R.MARGIN = m
            try:
                ok = self.solve(net, self.a.depth if m == self.a.slack else 0, set(), (x - r, y - r, x + r, y + r), before)
            finally:
                R.MARGIN = self.a.slack
            if ok:
                self.say('kick %s at %.3f,%.3f: re-joined with allowance %.3f' % (net, x, y, m))
                return True
            self.restore(s2)
        self.restore(snap)
        self.say('kick %s at %.3f,%.3f: FAILED, copper left as it was' % (net, x, y))
        return False

    def solve(self, net, depth, locked, focus=None, target=1):
        """join the islands of `net` down to `target`; True when done. `focus`: (x0, y0, x1, y1) of the cut."""
        a, B, Rt = self.a, self.B, self.Rt
        guard = 0
        while True:
            if time.time() > self.deadline:
                raise Timeout()
            Mn, gs = self.isl(net)
            if len(gs) <= target:
                return True
            guard += 1
            if guard > 8:
                return False
            if net in PLANES:                          # tie the untied island nearest the cut with a plane via
                un = [g for g in gs if not g['plane']]
                if focus:
                    c = ((focus[0] + focus[2]) / 2, (focus[1] + focus[3]) / 2)
                    un.sort(key=lambda g: self.gdist(Mn, g, c))
                bx, r = R.bbox(Mn, un[0]), None
                Rt.max_pops = a.lpops
                for mg in (0.8, 1.6, 3.0):
                    win = R.window(B, [bx], mg)
                    r = Rt.route(net, R.island_mask(B, Mn, un[0], win), None, win, plane=R.PLANE_VIAS[net])
                    if r:
                        break
                if not r:
                    return False
                Rt.commit(net, *r)
                self.say('%s tied at %.2f,%.2f' % (net, (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2))
                continue
            if focus:
                c = ((focus[0] + focus[2]) / 2, (focus[1] + focus[3]) / 2)
                gs.sort(key=lambda g: self.gdist(Mn, g, c))
                ga, gb = gs[0], gs[1]
                wins = [R.window(B, [focus], m) for m in (1.2, 3.0)]
                wins += [R.window(B, [R.bbox(Mn, ga), R.bbox(Mn, gb)], 1.0)]
            else:
                ga = gs[0]
                ca = R.bbox(Mn, ga)
                ca = ((ca[0] + ca[2]) / 2, (ca[1] + ca[3]) / 2)
                gb = min(gs[1:], key=lambda g: self.gdist(Mn, g, ca))
                wins = [R.window(B, [R.bbox(Mn, ga), R.bbox(Mn, gb)], m) for m in (a.margin, a.margin * 2.5)]
            r = self.hard(net, Mn, ga, gb, wins, a.lpops if focus else a.hpops)
            if r:
                Rt.commit(net, *r)
                self.say('%s joined (hard)' % net)
                continue
            if depth <= 0:
                return False
            extra, ok = set(), False
            for alt in range(a.alts):
                if time.time() > self.deadline:
                    raise Timeout()
                snap = self.snap()
                pr = self.probe(net, Mn, ga, gb, wins, locked | extra | (PLANES if a.planes_hard else set()))
                if not pr:
                    self.say('%s: no probe path (%s)' % (net, Rt.why))
                    break
                path, conf = pr
                victims = sorted(conf, key=lambda v: len(conf[v]))
                if not victims:
                    self.say('%s: probe path is free but the hard route failed (%s)' % (net, Rt.why))
                    break
                if len(victims) > a.maxv:
                    worst = victims[-1]
                    self.say('%s: %d victims (%s), fixing %s' % (net, len(victims), ' '.join(victims), worst))
                    extra.add(worst)
                    continue
                before = {v: len(self.isl(v)[1]) for v in victims}
                xs, ys = [p[1] for p in path], [p[2] for p in path]
                box = (min(xs), min(ys), max(xs), max(ys))
                r = None
                for rc in (a.rc, a.rc * 1.8):
                    self.cut(conf, rc)
                    for v in victims:
                        self.drop_fragments(v)
                    Rt.rip(set())
                    r = self.hard(net, Mn, ga, gb, [R.window(B, [box], m) for m in (0.6, 1.5)], a.lpops * 2)
                    if r:
                        break
                    self.restore(snap)
                if not r:
                    self.say('%s: corridor through %s not routable after the cut' % (net, ' '.join(victims)))
                    extra.add(victims[-1])
                    continue
                Rt.commit(net, *r)
                self.say('%s joined through %s' % (net, ' '.join(victims)))
                done, fail = set(), None
                self.ind += 1
                try:
                    for v in victims:
                        px, py = [p[0] for p in conf[v]], [p[1] for p in conf[v]]
                        fb = (min(px), min(py), max(px), max(py))
                        if not self.solve(v, depth - 1, locked | {net} | done, fb, before[v]):
                            fail = v
                            break
                        done.add(v)
                finally:
                    self.ind -= 1
                if fail is None:
                    ok = True
                    break
                self.say('%s: victim %s could not be re-joined, undo' % (net, fail))
                self.restore(snap)
                extra.add(fail)
            if not ok:
                return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--seed', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--clear', type=float, default=0.077)
    ap.add_argument('--slack', type=float, default=0.005)
    ap.add_argument('--laser-small', default='')
    ap.add_argument('--depth', type=int, default=3)
    ap.add_argument('--alts', type=int, default=3)
    ap.add_argument('--rc', type=float, default=0.4)
    ap.add_argument('--maxv', type=int, default=4)
    ap.add_argument('--soft', type=float, default=1.0)
    ap.add_argument('--hw', type=float, default=2.0, help='heuristic weight of the probe (1: exact A*)')
    ap.add_argument('--hpops', type=int, default=300000, help='budget of the first hard attempt of an open net')
    ap.add_argument('--margin', type=float, default=2.5)
    ap.add_argument('--planes-hard', action='store_true', help='never cut GND / VCC3V3 tie copper')
    ap.add_argument('--pops', type=int, default=1500000)
    ap.add_argument('--lpops', type=int, default=400000)
    ap.add_argument('--tlimit', type=float, default=1800, help='seconds per open net and pass')
    ap.add_argument('--passes', type=int, default=2)
    ap.add_argument('--nets', default='', help='only these nets, in this order')
    ap.add_argument('--kick', default='', help='before anything else: cut and re-join copper at "NET@x,y,r;NET@x,y,r"')
    ap.add_argument('--no-open', action='store_true', help='only the kicks, leave the open connections alone')
    a = ap.parse_args()
    t0 = time.time()
    F = Fin(a)
    oc = F.opens()
    print('seeded %d vias, %d tracks; open %d on %d nets: %s (%.0f s)' % (
        len(F.Rt.out_v), len(F.Rt.out_t), sum(oc.values()), len(oc), ' '.join(sorted(oc)), time.time() - t0), flush=True)

    def write():
        json.dump({'vias': F.Rt.out_v, 'tracks': F.Rt.out_t, 'remove': F.removed, 'log': F.log},
                  open(a.out, 'w'), indent=0)
    for k in [k for k in a.kick.split(';') if k]:
        net, xyr = k.rsplit('@', 1)
        x, y, r = [float(v) for v in xyr.split(',')]
        F.deadline = time.time() + a.tlimit
        try:
            F.kick(net, x, y, r)
        except Timeout:
            F.say('kick %s: time limit' % net)
        write()
    for ps in range(0 if a.no_open else a.passes):
        progress = False
        oc = F.opens()
        nets = [n for n in (a.nets.split(',') if a.nets else sorted(oc)) if n in oc and n not in PLANES]
        for net in nets:
            snap = F.snap()
            before = sum(F.opens().values())
            F.deadline = time.time() + a.tlimit
            t1 = time.time()
            F.say('== %s (pass %d)' % (net, ps + 1))
            try:
                F.solve(net, a.depth, set())
                why = ''
            except Timeout:
                why = ' (time limit)'
            after = sum(F.opens().values())
            if after < before:
                progress = True
                F.say('== %s: open %d -> %d%s, %.0f s' % (net, before, after, why, time.time() - t1))
                write()
            else:
                F.restore(snap)
                F.say('== %s: not closed%s, %.0f s' % (net, why, time.time() - t1))
        if not progress:
            break
    oc = F.opens()
    F.log.append('OPEN after finish: %s' % ' '.join('%s %d' % kv for kv in sorted(oc.items())))
    write()
    print('finish: open %d on %d nets: %s; %d vias, %d tracks -> %s (%.0f s)' % (
        sum(oc.values()), len(oc), ' '.join(sorted(oc)), len(F.Rt.out_v), len(F.Rt.out_t), a.out, time.time() - t0))


if __name__ == '__main__':
    main()
