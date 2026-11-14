# -*- coding: utf-8 -*-
"""Geometry + rule checker for the D0-D15 series-R plan (READ-ONLY on the board; used by design_arrays.py).

Board model = si/series_r/board_extract.json (read from the saved PcbDoc, md5 in its 'source').
A plan = removals (existing tracks/vias matched by layer, net and end points to 1 um) + part moves +
pad re-nets + additions (tracks, vias, new parts' pads).  check_plan() then measures, for every
ADDED or MOVED copper object, the distance to every other copper object on the same layer of a
different net, and applies the board's Rules6 values:

  Clearance            0.09 mm all/all (binds on Top/Bottom)
  Clearance_SDRAM_INNER 0.10 mm for SDRAM_DATA/ADDR/CTRL on L3/L4 (SDRAM-Dn are added to SDRAM_DATA)
  Clearance_SDRAM_CLK  0.20 mm for SDRAM-CLK on L3/L4
  HoleToHole           0.24 mm (stacked microvias at one x,y are allowed, as on the board)
  MinimumSolderMaskSliver 0.10 mm between pad mask openings (+0.05 per side; vias are tented)
  Width_SDRAM          Bottom 0.10..0.15, Top 0.0762..0.15, L3/L4 0.10..0.15 for D/SDRAM-D nets
  ComponentClearance   0.254 mm -- NOT in the board's batch DRC (docs/drc_jtag_column.drc lists the
                       processed rules and this is not one); reported as an advisory on pad boxes
plus connectivity of every touched net (all its pads in one island) and net antennae (a track end
that touches nothing of its own net), both of which ARE in the batch DRC (Un-Routed, Net Antennae).
Geometry: tracks/vias are capsules, rectangular pads are axis-aligned rectangles (all pads near U3
are at 0/90/180/270 deg), round pads circles, rounded-rect pads are treated as full rectangles
(conservative).
"""
import json
import math
from collections import defaultdict

EXTRACT = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/si/series_r/board_extract.json'
COPPER = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
SIG = ['Top', 'L3-SIG', 'L4-SIG', 'Bottom']
CL = 0.09
CL_SDRAM_INNER = 0.10
CL_CLK_INNER = 0.20
HOLE_HOLE = 0.24
MASK = 0.05
SLIVER = 0.10
COMP_CL = 0.254
EPS = 1e-6


# ----------------------------------------------------------------------------- geometry
def _pt_seg(p, a, b):
    abx, aby = b[0] - a[0], b[1] - a[1]
    L2 = abx * abx + aby * aby
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / L2))
    return math.hypot(p[0] - a[0] - t * abx, p[1] - a[1] - t * aby)


def seg_seg(a, b, c, d):
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = cr(c, d, a), cr(c, d, b), cr(a, b, c), cr(a, b, d)
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return 0.0
    return min(_pt_seg(a, c, d), _pt_seg(b, c, d), _pt_seg(c, a, b), _pt_seg(d, a, b))


def seg_rect(a, b, r):
    x0, y0, x1, y1 = r
    if (x0 <= a[0] <= x1 and y0 <= a[1] <= y1) or (x0 <= b[0] <= x1 and y0 <= b[1] <= y1):
        return 0.0
    E = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return min(seg_seg(a, b, p, q) for p, q in E)


def rect_rect(r, s):
    dx = max(r[0] - s[2], s[0] - r[2], 0.0)
    dy = max(r[1] - s[3], s[1] - r[3], 0.0)
    return math.hypot(dx, dy)


class Obj:
    """kind: 'track' | 'via' | 'pad' ; shape 'cap' (segment+radius) or 'rect'."""
    __slots__ = ('kind', 'shape', 'g', 'r', 'net', 'layer', 'src', 'tag', 'rec')

    def __init__(self, kind, shape, g, r, net, layer, src, tag, rec):
        self.kind, self.shape, self.g, self.r, self.net, self.layer, self.src, self.tag, self.rec = \
            kind, shape, g, r, net, layer, src, tag, rec

    def bbox(self):
        if self.shape == 'rect':
            return self.g
        (x1, y1), (x2, y2) = self.g
        return (min(x1, x2) - self.r, min(y1, y2) - self.r, max(x1, x2) + self.r, max(y1, y2) + self.r)

    def describe(self):
        if self.kind == 'track':
            (x1, y1), (x2, y2) = self.g
            return '%s track %s (%.3f,%.3f)-(%.3f,%.3f) w%.4g' % (self.layer, self.net, x1, y1, x2, y2, 2 * self.r)
        if self.kind == 'via':
            v = self.rec
            return 'via %s (%.3f,%.3f) %.2f/%.2f %s>%s' % (self.net, v['x'], v['y'], v['size'], v['hole'], v['span'][0], v['span'][-1])
        return '%s pad %s (%s)' % (self.layer, self.tag, self.net)


def dist(A, B):
    if A.shape == 'cap' and B.shape == 'cap':
        return seg_seg(A.g[0], A.g[1], B.g[0], B.g[1]) - A.r - B.r
    if A.shape == 'rect' and B.shape == 'rect':
        return rect_rect(A.g, B.g)
    c, r = (A, B) if A.shape == 'cap' else (B, A)
    return seg_rect(c.g[0], c.g[1], r.g) - c.r


def pad_objs(p, src='board', planes=False):
    Ls = [L for L in COPPER] if p['layer'] == 'Multi' else [p['layer']]
    out = []
    tag = '%s-%s' % (p['ref'], p['pad'])
    for L in Ls:
        if L in ('L2-GND', 'L5-VCC3V3') and p['layer'] == 'Multi' and not planes:
            continue          # plane layers: the pour makes its own clearance (not modelled)
        if p['shape'] in ('round', 'circle') and abs(p['w'] - p['h']) < 1e-4:
            o = Obj('pad', 'cap', ((p['x'], p['y']), (p['x'], p['y'])), p['w'] / 2, p['net'], L, src, tag, p)
        elif p['shape'] in ('round', 'circle'):
            if p['w'] > p['h']:
                g = ((p['x'] - (p['w'] - p['h']) / 2, p['y']), (p['x'] + (p['w'] - p['h']) / 2, p['y'])); r = p['h'] / 2
            else:
                g = ((p['x'], p['y'] - (p['h'] - p['w']) / 2), (p['x'], p['y'] + (p['h'] - p['w']) / 2)); r = p['w'] / 2
            o = Obj('pad', 'cap', g, r, p['net'], L, src, tag, p)
        else:
            o = Obj('pad', 'rect', (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2),
                    0.0, p['net'], L, src, tag, p)
        out.append(o)
    return out


def track_obj(t, src='board'):
    return Obj('track', 'cap', ((t['x1'], t['y1']), (t['x2'], t['y2'])), t['w'] / 2, t['net'], t['layer'], src, None, t)


def via_objs(v, src='board'):
    return [Obj('via', 'cap', ((v['x'], v['y']), (v['x'], v['y'])), v['size'] / 2, v['net'], L, src, None, v)
            for L in v['span'] if L in SIG or True]


# ----------------------------------------------------------------------------- board
class Board:
    def __init__(self, path=EXTRACT):
        self.d = json.load(open(path))
        self.tracks = [t for t in self.d['tracks'] if t['layer'] in COPPER]
        self.vias = list(self.d['vias'])
        self.pads = list(self.d['pads'])
        self.comps = {c['ref']: c for c in self.d['components']}
        self.classes = self.d['net_classes']


def _same(a, b, tol=1.5e-3):
    return abs(a - b) <= tol


def match_track(t, spec):
    if t['layer'] != spec['layer'] or t['net'] != spec['net']:
        return False
    a = (spec['x1'], spec['y1'], spec['x2'], spec['y2'])
    for (p, q, r, s) in ((t['x1'], t['y1'], t['x2'], t['y2']), (t['x2'], t['y2'], t['x1'], t['y1'])):
        if _same(p, a[0]) and _same(q, a[1]) and _same(r, a[2]) and _same(s, a[3]):
            return True
    return False


def match_via(v, spec):
    return v['net'] == spec['net'] and _same(v['x'], spec['x']) and _same(v['y'], spec['y']) and \
        v['span'][0] == spec['span'][0] and v['span'][-1] == spec['span'][-1]


def apply_plan(B, plan):
    """returns (tracks, vias, pads, report) of the board after the plan; added objects carry 'new': True."""
    rep = {'removed_tracks': [], 'removed_vias': [], 'missing': []}
    tracks = []
    used = set()
    for t in B.tracks:
        hit = None
        for i, s in enumerate(plan.get('remove_tracks', [])):
            if match_track(t, s):
                hit = i
                break
        if hit is None:
            tracks.append(dict(t))
        else:
            used.add(('t', hit))
            rep['removed_tracks'].append(t)
    for i, s in enumerate(plan.get('remove_tracks', [])):
        if ('t', i) not in used:
            rep['missing'].append(('track', s))
    vias = []
    for v in B.vias:
        hit = None
        for i, s in enumerate(plan.get('remove_vias', [])):
            if match_via(v, s):
                hit = i
                break
        if hit is None:
            vias.append(dict(v))
        else:
            used.add(('v', hit))
            rep['removed_vias'].append(v)
    for i, s in enumerate(plan.get('remove_vias', [])):
        if ('v', i) not in used:
            rep['missing'].append(('via', s))
    moves = {m['ref']: m for m in plan.get('move_parts', [])}
    renet = {(r['ref'], r['pad']): r['net'] for r in plan.get('renet_pads', [])}
    pads = []
    for p in B.pads:
        q = dict(p)
        if p['ref'] in moves:
            m = moves[p['ref']]
            q['x'] += m['dx']
            q['y'] += m['dy']
            if m.get('swap_wh'):
                q['w'], q['h'] = q['h'], q['w']
            q['moved'] = True
        if (p['ref'], p['pad']) in renet:
            q['net'] = renet[(p['ref'], p['pad'])]
            q['renet'] = True
        pads.append(q)
    for t in plan.get('add_tracks', []):
        q = dict(t)
        q['new'] = True
        tracks.append(q)
    for v in plan.get('add_vias', []):
        q = dict(v)
        q['new'] = True
        vias.append(q)
    for p in plan.get('add_pads', []):
        q = dict(p)
        q['new'] = True
        pads.append(q)
    for t in plan.get('reshape_tracks', []):      # width change of an existing record (kept, re-measured)
        for q in tracks:
            if match_track(q, t):
                q['w'] = t['new_w']
                q['new'] = True
    return tracks, vias, pads, rep


def objects(tracks, vias, pads):
    by = defaultdict(list)
    for t in tracks:
        by[t['layer']].append(track_obj(t, 'new' if t.get('new') else 'board'))
    for v in vias:
        for o in via_objs(v, 'new' if v.get('new') else 'board'):
            by[o.layer].append(o)
    for p in pads:
        for o in pad_objs(p, 'new' if (p.get('new') or p.get('moved') or p.get('renet')) else 'board'):
            by[o.layer].append(o)
    return by


def sdram_class(classes):
    s = set()
    for k in ('SDRAM_DATA', 'SDRAM_ADDR', 'SDRAM_CTRL'):
        s |= set(classes[k])
    s |= set('SDRAM-D%d' % i for i in range(16))
    return s


def rule_cl(a, b, layer, sd):
    if layer in ('L3-SIG', 'L4-SIG'):
        if 'SDRAM-CLK' in (a.net, b.net):
            return CL_CLK_INNER
        if a.net in sd or b.net in sd:
            return CL_SDRAM_INNER
    return CL


class Grid:
    def __init__(self, objs, cell=1.0):
        self.c = cell
        self.g = defaultdict(list)
        for o in objs:
            x0, y0, x1, y1 = o.bbox()
            for i in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for j in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    self.g[(i, j)].append(o)

    def near(self, o, pad=0.5):
        x0, y0, x1, y1 = o.bbox()
        seen = set()
        for i in range(int(math.floor((x0 - pad) / self.c)), int(math.floor((x1 + pad) / self.c)) + 1):
            for j in range(int(math.floor((y0 - pad) / self.c)), int(math.floor((y1 + pad) / self.c)) + 1):
                for q in self.g.get((i, j), ()):
                    if id(q) not in seen:
                        seen.add(id(q))
                        yield q


def _dielectrics(v):
    sp = v.get('span') or COPPER
    i, j = COPPER.index(sp[0]), COPPER.index(sp[-1])
    return set(range(min(i, j), max(i, j)))


def _spans_overlap(a, b):
    return bool(_dielectrics(a) & _dielectrics(b))


def check_plan(B, plan, touched_nets):
    tracks, vias, pads, rep = apply_plan(B, plan)
    by = objects(tracks, vias, pads)
    sd = sdram_class(B.classes)
    viol, worst = [], {}

    def note(rule, margin, a, b):
        k = rule
        if k not in worst or margin < worst[k][0]:
            worst[k] = (round(margin, 4), a.describe(), b.describe() if b is not None else '')

    for L, objs in by.items():
        if L in ('L2-GND', 'L5-VCC3V3'):
            continue
        grid = Grid(objs)
        for a in objs:
            if a.src != 'new':
                continue
            for b in grid.near(a):
                if b is a or (b.net == a.net and a.net):
                    continue
                if a.kind == 'via' and b.kind == 'via' and a.rec is b.rec:
                    continue
                need = rule_cl(a, b, L, sd)
                dd = dist(a, b)
                note('clearance', dd - need, a, b)
                if dd < need - EPS:
                    viol.append(('clearance', L, round(dd, 4), need, a.describe(), b.describe()))
    # hole to hole (new vias vs every drilled object); stacked microvias at the same x,y are allowed
    holes = [(v['x'], v['y'], v['hole'], v, bool(v.get('new'))) for v in vias] + \
            [(p['x'], p['y'], p['hole'], p, bool(p.get('new'))) for p in pads if p.get('hole', 0) > 0]
    for (x, y, h, v, new) in holes:
        if not new:
            continue
        for (x2, y2, h2, v2, new2) in holes:
            if v2 is v:
                continue
            c = math.hypot(x - x2, y - y2)
            if c < 1e-3 and v.get('kind') == 'micro' and v2.get('kind') == 'micro':
                continue
            if not _spans_overlap(v, v2):
                continue          # drills in different dielectric spans never meet (the saved board, DRC 0, has such pairs)
            gap = c - h / 2 - h2 / 2
            if gap < 2.0:
                note('hole_to_hole', gap - HOLE_HOLE, Obj('via', 'cap', ((x, y), (x, y)), h / 2, v.get('net'), 'drill', 'new', None, v),
                     Obj('via', 'cap', ((x2, y2), (x2, y2)), h2 / 2, v2.get('net'), 'drill', 'b', None, v2))
                if gap < HOLE_HOLE - EPS:
                    viol.append(('hole_to_hole', round(gap, 4), (x, y), (x2, y2)))
    # solder-mask sliver between pad openings (outer layers), for new/moved pads
    for L in ('Top', 'Bottom'):
        pl = [o for o in by[L] if o.kind == 'pad']
        grid = Grid(pl)
        for a in pl:
            if a.src != 'new':
                continue
            ea = 0.0 if a.rec['ref'] == 'U1' else MASK
            for b in grid.near(a):
                if b is a:
                    continue
                eb = 0.0 if b.rec['ref'] == 'U1' else MASK
                web = dist(a, b) - ea - eb
                if web <= 0:
                    continue          # openings merge (Altium reports no sliver for overlapping openings)
                note('mask_sliver', web - SLIVER, a, b)
                if web < SLIVER - EPS:
                    viol.append(('mask_sliver', L, round(web, 4), a.describe(), b.describe()))
    # width rule on the D / SDRAM-D nets for added tracks
    for t in tracks:
        if not t.get('new'):
            continue
        n = t['net']
        if n in sd and (n.startswith('D') or n.startswith('SDRAM-D')):
            lo, hi = {'Top': (0.0762, 0.15), 'Bottom': (0.10, 0.15), 'L3-SIG': (0.10, 0.15), 'L4-SIG': (0.10, 0.15)}[t['layer']]
            if not (lo - EPS <= t['w'] <= hi + EPS):
                viol.append(('width', t['layer'], n, t['w'], (lo, hi)))
        elif n in B.classes['PWR_RAILS'] or n == 'VCC3V3':
            if t['w'] < 0.15 - EPS and n != 'VCC3V3':
                viol.append(('width', t['layer'], n, t['w'], '>=0.15'))
    # component clearance advisory (pad boxes; Rules6 ComponentClearance 0.254, not in the batch DRC)
    comp_box = defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
    side = {}
    for p in pads:
        if p['ref'] in ('X2',):
            continue
        b = comp_box[p['ref']]
        b[0] = min(b[0], p['x'] - p['w'] / 2); b[1] = min(b[1], p['y'] - p['h'] / 2)
        b[2] = max(b[2], p['x'] + p['w'] / 2); b[3] = max(b[3], p['y'] + p['h'] / 2)
        side[p['ref']] = p['layer']
    newrefs = set(p['ref'] for p in pads if p.get('new') or p.get('moved'))
    advis = []
    for a in newrefs:
        for b, bb in comp_box.items():
            if b == a or side.get(b) not in (side.get(a), 'Multi'):
                continue
            g = rect_rect(comp_box[a], bb)
            if g < COMP_CL:
                advis.append((a, b, round(g, 3)))
    # connectivity + antennae for the touched nets
    conn = {}
    for net in sorted(touched_nets):
        conn[net] = connectivity(net, tracks, vias, pads)
        if not conn[net]['ok']:
            viol.append(('connectivity', net, conn[net]))
    return dict(violations=viol, worst=worst, component_advisory=sorted(advis, key=lambda r: r[2]),
                connectivity=conn, removal=rep, n_tracks=len(tracks), n_vias=len(vias))


def connectivity(net, tracks, vias, pads):
    objs = []
    for t in tracks:
        if t['net'] == net:
            objs.append(track_obj(t))
    for v in vias:
        if v['net'] == net:
            objs += via_objs(v)
    for p in pads:
        if p['net'] == net:
            objs += pad_objs(p, planes=True)
    n = len(objs)
    par = list(range(n))

    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    byrec = defaultdict(list)
    for i, o in enumerate(objs):
        byrec[id(o.rec)].append(i)
    for idx in byrec.values():
        for i in idx[1:]:
            par[f(i)] = f(idx[0])
    bylayer = defaultdict(list)
    for i, o in enumerate(objs):
        bylayer[o.layer].append(i)
    for L, idx in bylayer.items():
        for k, i in enumerate(idx):
            for j in idx[k + 1:]:
                if dist(objs[i], objs[j]) <= 1e-4:
                    par[f(i)] = f(j)
    plane = {'GND': 'L2-GND', 'VCC3V3': 'L5-VCC3V3'}.get(net)
    if plane:                       # the pour on the plane layer joins every via / through pad of its net
        idx = [i for i, o in enumerate(objs) if o.layer == plane]
        for i in idx[1:]:
            par[f(i)] = f(idx[0])
    padroots = defaultdict(list)
    for i, o in enumerate(objs):
        if o.kind == 'pad':
            padroots[f(i)].append(o.tag)
    islands = [sorted(set(v)) for v in padroots.values()]
    # antennae: track end points touching nothing else of the net on that layer
    ant = []
    for i, o in enumerate(objs):
        if o.kind != 'track':
            continue
        for e in o.g:
            pt = Obj('track', 'cap', (e, e), 0.0, net, o.layer, '', None, None)
            ok = False
            for j in bylayer[o.layer]:
                if j == i:
                    continue
                if dist(pt, objs[j]) <= 1e-4:
                    ok = True
                    break
            if not ok:
                ant.append((o.layer, round(e[0], 4), round(e[1], 4)))
    # tracks not attached to any pad island
    orphan = sum(1 for i, o in enumerate(objs) if o.kind != 'pad' and f(i) not in padroots)
    npads = sum(len(v) for v in islands)
    return dict(ok=(len(islands) <= 1 and not ant and orphan == 0), islands=len(islands),
                island_pads=[v[:6] for v in islands] if len(islands) > 1 else [], antennae=ant,
                orphan_objects=orphan, pads=npads)
