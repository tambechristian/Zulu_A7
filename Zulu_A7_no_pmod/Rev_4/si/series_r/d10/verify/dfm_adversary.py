"""Adversarial DFM / DRC check of a series-R plan JSON (emit_copper format + parts / renet_pads / net_class_add /
microvias), written from scratch for the D10 review.  It imports NOTHING from dfm_check.py, judge_check.py,
geom.py, plan_check.py or d10/judge/*.py; geometry, rule resolution, pour model and connectivity are all new code.

Inputs : ../../board_extract.json (PcbDoc md5 2a616c1c, Rules6 included) + the plan (default ../final_plan.json)
Outputs: adversary_<tag>.log / adversary_<tag>.json in this folder.  Nothing else is written.

Independent choices:
  * every rule value is parsed from Rules6 in board_extract.json (no hard-coded gaps); scope expressions are
    evaluated by a small query interpreter (InNet / InNetClass / OnLayer / InComponent / InNamedPolygon / Is*Via);
  * the interpreter is CALIBRATED on the unmodified board first: the board is DRC 0, so any rule interpretation
    that reports a violation on the baseline is rejected (via OnLayer semantics, Width per-layer key mapping,
    stacked-hole exemption, mask sliver semantics);
  * the after-board is checked ALL-PAIRS (not only near new objects), and baseline findings are subtracted;
  * pours are re-poured by raster (0.01 mm whole board, 0.0025 mm in windows round every changed L2/L5 object);
  * connectivity (net islands, shorts, R bypass) is computed by union-find over every copper object + pour island.
Usage: python dfm_adversary.py [--plan PATH] [--tag NAME]
"""
import argparse, collections, json, math, os, re, sys, time
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SR = os.path.normpath(os.path.join(HERE, '..', '..')).replace('\\', '/')
ap = argparse.ArgumentParser()
ap.add_argument('--plan', default=SR + '/d10/final_plan.json')
ap.add_argument('--tag', default='final')
ap.add_argument('--board', default=SR + '/board_extract.json')
ap.add_argument('--no-baseline-allpairs', action='store_true')
args = ap.parse_args()

B = json.load(open(args.board))
P = json.load(open(args.plan))
STACK = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
LI = {l: i for i, l in enumerate(STACK)}
PLANE_POLY = {}            # layer -> (polygon name, net)
for pg in B['polygons']:
    # MID3 / MID4 are the layer IDs of L2 / L5 (named in the polygon names); verified by the net
    L = {'GND': 'L2-GND', 'VCC3V3': 'L5-VCC3V3'}[pg['net']]
    PLANE_POLY[L] = (pg['name'], pg['net'], pg['outline'])
EPS = 1e-6
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def LN(s):
    return {'Top Layer': 'Top', 'Bottom Layer': 'Bottom'}.get(s, s)


def mm(v):
    v = str(v).strip()
    if v.endswith('mil'):
        return float(v[:-3]) * 0.0254
    if v.endswith('mm'):
        return float(v[:-2])
    return float(v)


# ============================================================== rules (parsed, never hard-coded)
RULES = collections.defaultdict(list)
for r in B['rules']:
    if r.get('ENABLED', 'TRUE') == 'TRUE':
        RULES[r['RULEKIND']].append(r)
for k in RULES:
    RULES[k].sort(key=lambda r: int(r['PRIORITY']))

CLASSES0 = {k: set(v) for k, v in B['net_classes'].items()}


def classes_with(add):
    c = {k: set(v) for k, v in CLASSES0.items()}
    for k, v in (add or {}).items():
        c.setdefault(k, set()).update(v)
    return c


_SC = {}


def _compile(expr):
    e = re.sub(r'\bAnd\b', ' and ', expr)
    e = re.sub(r'\bOr\b', ' or ', e)
    e = re.sub(r'\bNot\b', ' not ', e)
    return compile(e, '<scope>', 'eval')


def scope(expr, o, layer, ctx):
    """o: dict(kind, net, comp, poly, vtype, multi)."""
    code = _SC.get(expr)
    if code is None:
        code = _SC[expr] = _compile(expr)
    k = o['kind']
    if k == 'via':
        onl = ctx['via_onlayer']
    elif k == 'pad':
        onl = not o.get('multi')
    else:
        onl = True
    env = {
        'All': True,
        'InComponent': lambda r: o.get('comp') == r,
        'InNamedPolygon': lambda n: o.get('poly') == n,
        'IsThruVia': k == 'via' and o.get('vtype') == 'thru',
        'IsMicroVia': k == 'via' and o.get('vtype') == 'micro',
        'IsBuriedVia': k == 'via' and o.get('vtype') == 'buried',
        'IsVia': k == 'via',
        'IsPad': k == 'pad',
        'InNet': lambda n: o.get('net') == n,
        'InNetClass': lambda c: o.get('net') in ctx['classes'].get(c, ()),
        'OnLayer': lambda L: bool(onl and layer == L),
    }
    return bool(eval(code, {'__builtins__': {}}, env))


def sig(o):
    return (o['kind'], o.get('net'), o.get('comp'), o.get('poly'), o.get('vtype'), bool(o.get('multi')))


_CR = {}


def clearance_rule(a, b, layer, ctx):
    key = (sig(a), sig(b), layer, ctx['name'])
    if key in _CR:
        return _CR[key]
    res = (0.0, 'none')
    for r in RULES['Clearance']:
        s1, s2 = r['SCOPE1EXPRESSION'], r['SCOPE2EXPRESSION']
        if (scope(s1, a, layer, ctx) and scope(s2, b, layer, ctx)) or (scope(s1, b, layer, ctx) and scope(s2, a, layer, ctx)):
            res = (mm(r['GAP']), r['NAME'])
            break
    _CR[key] = res
    return res


WMAPS = {  # candidate Rules6 per-layer key prefixes; calibrated on the baseline board
    'A(L3=MID1,L4=MID2,L2=MID3,L5=MID4)': {'Top': 'TOPLAYER', 'Bottom': 'BOTTOMLAYER', 'L3-SIG': 'MIDLAYER1',
                                           'L4-SIG': 'MIDLAYER2', 'L2-GND': 'MIDLAYER3', 'L5-VCC3V3': 'MIDLAYER4'},
    'B(stack order L2..L5=MID1..4)': {'Top': 'TOPLAYER', 'Bottom': 'BOTTOMLAYER', 'L2-GND': 'MIDLAYER1',
                                      'L3-SIG': 'MIDLAYER2', 'L4-SIG': 'MIDLAYER3', 'L5-VCC3V3': 'MIDLAYER4'},
}


def width_limits(net, layer, ctx, wmap):
    o = {'kind': 'track', 'net': net}
    for r in RULES['Width']:
        if scope(r['SCOPE1EXPRESSION'], o, layer, ctx):
            p = wmap[layer]
            lo = mm(r.get(p + '_MINWIDTH', r['MINLIMIT']))
            hi = mm(r.get(p + '_MAXWIDTH', r['MAXLIMIT']))
            return lo, hi, r['NAME']
    return 0.0, 99.0, 'none'


def holesize_rule(o, ctx):
    for r in RULES['HoleSize']:
        if scope(r['SCOPE1EXPRESSION'], o, None, ctx):
            return mm(r['MINLIMIT']), mm(r['MAXLIMIT']), r['NAME']
    return 0, 99, 'none'


def viastyle_rule(o, ctx):
    for r in RULES['RoutingVias']:
        if scope(r['SCOPE1EXPRESSION'], o, None, ctx):
            return (mm(r['MINWIDTH']), mm(r['MAXWIDTH']), mm(r['MINHOLEWIDTH']), mm(r['MAXHOLEWIDTH']), r['NAME'])
    return None


def mask_rule(o, side, ctx):
    for r in RULES['SolderMaskExpansion']:
        if scope(r['SCOPE1EXPRESSION'], o, None, ctx):
            if o['kind'] == 'via':
                tent = r.get('ISTENTINGTOP' if side == 'Top' else 'ISTENTINGBOTTOM', 'FALSE') == 'TRUE'
                if tent:
                    return None
            if side == 'Bottom' and r.get('USESEPARATEEXPANSIONS') == 'TRUE' and 'EXPANSIONBOTTOM' in r:
                return mm(r['EXPANSIONBOTTOM'])
            return mm(r['EXPANSION'])
    return 0.0


R1 = lambda kind, name: next(r for r in RULES[kind] if r['NAME'] == name)
H2H = mm(RULES['HoleToHoleClearance'][0]['GAP'])
H2H_STACK_OK = RULES['HoleToHoleClearance'][0].get('ALLOWSTACKEDMICROVIAS') == 'TRUE'
SLIVER = mm(RULES['MinimumSolderMaskSliver'][0]['MINSOLDERMASKWIDTH'])
SILK2MASK = mm(RULES['SilkToSolderMaskClearance'][0]['MINSILKSCREENTOMASKGAP'])
CC_GAP = mm(RULES['ComponentClearance'][0]['GAP'])
ANT_TOL = mm(RULES['NetAntennae'][0]['NETANTENNAETOLERANCE'])

# ============================================================== exact geometry
# shape: ('c', x1, y1, x2, y2, r)  capsule (track / round pad / via)   ('b', x0, y0, x1, y1) axis box (rect pad)


def pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    if L <= 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / L
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def _ori(ax, ay, bx, by, cx, cy):
    v = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    return 0 if abs(v) < 1e-15 else (1 if v > 0 else -1)


def seg_cross(a, b):
    o1 = _ori(a[0], a[1], a[2], a[3], b[0], b[1])
    o2 = _ori(a[0], a[1], a[2], a[3], b[2], b[3])
    o3 = _ori(b[0], b[1], b[2], b[3], a[0], a[1])
    o4 = _ori(b[0], b[1], b[2], b[3], a[2], a[3])
    return o1 * o2 < 0 and o3 * o4 < 0


def seg_seg(a, b):
    if seg_cross(a, b):
        return 0.0
    return min(pt_seg(a[0], a[1], *b), pt_seg(a[2], a[3], *b), pt_seg(b[0], b[1], *a), pt_seg(b[2], b[3], *a))


def pt_box(px, py, b):
    dx = max(b[0] - px, 0.0, px - b[2])
    dy = max(b[1] - py, 0.0, py - b[3])
    return math.hypot(dx, dy)


def seg_box(s, b):
    if pt_box(s[0], s[1], b) == 0 or pt_box(s[2], s[3], b) == 0:
        return 0.0
    edges = ((b[0], b[1], b[2], b[1]), (b[2], b[1], b[2], b[3]), (b[2], b[3], b[0], b[3]), (b[0], b[3], b[0], b[1]))
    return min(seg_seg(s, e) for e in edges)


def box_box(a, b):
    dx = max(a[0] - b[2], 0.0, b[0] - a[2])
    dy = max(a[1] - b[3], 0.0, b[1] - a[3])
    return math.hypot(dx, dy)


def gap(sa, sb):
    if sa[0] == 'c' and sb[0] == 'c':
        return seg_seg(sa[1:5], sb[1:5]) - sa[5] - sb[5]
    if sa[0] == 'c':
        return seg_box(sa[1:5], sb[1:5]) - sa[5]
    if sb[0] == 'c':
        return seg_box(sb[1:5], sa[1:5]) - sb[5]
    return box_box(sa[1:5], sb[1:5])


def grow(s, g):
    if s[0] == 'c':
        return ('c', s[1], s[2], s[3], s[4], s[5] + g)
    return ('b', s[1] - g, s[2] - g, s[3] + g, s[4] + g)


def sbbox(s):
    if s[0] == 'c':
        r = s[5]
        return (min(s[1], s[3]) - r, min(s[2], s[4]) - r, max(s[1], s[3]) + r, max(s[2], s[4]) + r)
    return s[1:5]


def pad_shape(x, y, w, h, shape):
    if shape == 'round':
        if abs(w - h) < 1e-9:
            return ('c', x, y, x, y, w / 2)
        if w > h:
            d = (w - h) / 2
            return ('c', x - d, y, x + d, y, h / 2)
        d = (h - w) / 2
        return ('c', x, y - d, x, y + d, w / 2)
    return ('b', x - w / 2, y - h / 2, x + w / 2, y + h / 2)


def contains_pt(s, x, y):
    if s[0] == 'c':
        return pt_seg(x, y, *s[1:5]) <= s[5] + 1e-9
    return s[1] - 1e-9 <= x <= s[3] + 1e-9 and s[2] - 1e-9 <= y <= s[4] + 1e-9


# ============================================================== object model
def vtype_of(span):
    if len(span) == 6:
        return 'thru'
    if span[0] == 'L3-SIG' and span[-1] == 'L4-SIG':
        return 'buried'
    return 'micro'


class Board:
    def __init__(s):
        s.objs = []

    def add(s, **o):
        o['id'] = len(s.objs)
        o.setdefault('new', False)
        o.setdefault('comp', None)
        o.setdefault('poly', None)
        o.setdefault('vtype', None)
        o.setdefault('multi', False)
        s.objs.append(o)
        return o


def pad_obj(bd, p, new=False, net=None):
    shapes = {}
    if p['layer'] == 'Multi':
        for L in STACK:
            if L == 'Top':
                w, h = p['w'], p['h']
            elif L == 'Bottom':
                w, h = p['size_bot'] if p.get('size_bot') else (p['w'], p['h'])
            else:
                w, h = p['size_mid'] if p.get('size_mid') else (p['w'], p['h'])
            shapes[L] = pad_shape(p['x'], p['y'], w, h, p['shape'])
    else:
        shapes[p['layer']] = pad_shape(p['x'], p['y'], p['w'], p['h'], p['shape'])
    return bd.add(kind='pad', net=net if net is not None else (p['net'] or ''), shapes=shapes, comp=p['ref'],
                  pad=p['pad'], multi=p['layer'] == 'Multi', hole=p.get('hole') or 0.0, x=p['x'], y=p['y'],
                  side=p['layer'], new=new, src=p)


def track_obj(bd, t, new=False):
    L = LN(t['layer'])
    sh = ('c', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2)
    return bd.add(kind='track', net=t['net'] or '', shapes={L: sh}, layer=L, w=t['w'], new=new, src=t,
                  comp=t.get('comp'))


def via_obj(bd, v, new=False):
    if 'span' in v:
        span = [LN(x) for x in v['span']]
        i0, i1 = LI[span[0]], LI[span[-1]]
    else:
        i0, i1 = sorted((LI[LN(v['from'])], LI[LN(v['to'])]))
    span = STACK[i0:i1 + 1]
    shapes = {L: ('c', v['x'], v['y'], v['x'], v['y'], v['size'] / 2) for L in span}
    return bd.add(kind='via', net=v['net'] or '', shapes=shapes, span=span, vtype=vtype_of(span), hole=v['hole'],
                  size=v['size'], x=v['x'], y=v['y'], new=new, src=v)


def netkey(o):
    return o['net'] if o['net'] else '#%d' % o['id']


def build_baseline():
    bd = Board()
    for p in B['pads']:
        pad_obj(bd, p)
    for t in B['tracks']:
        if t['layer'] in LI and not t['keepout']:
            track_obj(bd, t)
    for v in B['vias']:
        via_obj(bd, v)
    return bd


def same_xy(a, b, tol=1e-4):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def build_after(plan):
    """apply the plan literally; every remove must hit exactly one board object."""
    errs = []
    base = build_baseline()
    keep = [True] * len(base.objs)
    for r in plan.get('remove', []):
        L = LN(r['layer'])
        hits = []
        for o in base.objs:
            if o['kind'] != 'track' or not keep[o['id']] or o['layer'] != L or o['net'] != r['net']:
                continue
            t = o['src']
            if abs(t['w'] - r['w']) > 1e-4:
                continue
            if (same_xy((t['x1'], t['y1']), (r['x1'], r['y1'])) and same_xy((t['x2'], t['y2']), (r['x2'], r['y2']))) or \
               (same_xy((t['x1'], t['y1']), (r['x2'], r['y2'])) and same_xy((t['x2'], t['y2']), (r['x1'], r['y1']))):
                hits.append(o['id'])
        if len(hits) != 1:
            errs.append(('remove track', r, len(hits)))
        for h in hits[:1]:
            keep[h] = False
    for r in plan.get('remove_vias', []):
        span = [LN(x) for x in r['span']]
        hits = [o['id'] for o in base.objs if o['kind'] == 'via' and keep[o['id']] and o['net'] == r['net'] and
                same_xy((o['x'], o['y']), (r['x'], r['y'])) and abs(o['hole'] - r['hole']) < 1e-4 and
                o['span'][0] == span[0] and o['span'][-1] == span[-1]]
        if len(hits) != 1:
            errs.append(('remove via', r, len(hits)))
        for h in hits[:1]:
            keep[h] = False
    renet = {(r['ref'], r['pad']): r['net'] for r in plan.get('renet_pads', [])}
    bd = Board()
    found_renet = set()
    for o in base.objs:
        if not keep[o['id']]:
            continue
        if o['kind'] == 'pad':
            k = (o['comp'], o['pad'])
            if k in renet:
                found_renet.add(k)
                pad_obj(bd, o['src'], new=True, net=renet[k])
                bd.objs[-1]['old_net'] = o['net']
            else:
                pad_obj(bd, o['src'])
        elif o['kind'] == 'track':
            track_obj(bd, o['src'])
        else:
            via_obj(bd, o['src'])
    for k in renet:
        if k not in found_renet:
            errs.append(('renet pad not found', k, 0))
    for t in plan.get('tracks', []):
        track_obj(bd, t, new=True)
    for v in plan.get('vias', []):
        via_obj(bd, v, new=True)
    # 'microvias' is the typing list for entries that are ALSO in 'vias' (emit_copper format): check, do not add
    for m in plan.get('microvias', []):
        if not any(abs(v['x'] - m['x']) < 1e-6 and abs(v['y'] - m['y']) < 1e-6 and v['from'] == m['from'] and
                   v['to'] == m['to'] and v['net'] == m['net'] for v in plan.get('vias', [])):
            errs.append(('microvia typing entry with no matching via', m, 0))
    R0201 = [p for p in B['pads'] if p['ref'] == 'R5'] or []
    for part in plan.get('parts', []):
        side = part['side']
        lib = [p for p in B['pads'] if p['layer'] == side and any(
            c['ref'] == p['ref'] and c['footprint'] == part['footprint'] for c in B['components'])]
        pw, ph = (lib[0]['w'], lib[0]['h']) if lib else (0.3, 0.3)
        for pn in ('1', '2'):
            q = part['pad' + pn]
            pad_obj(bd, dict(ref=part['ref'], pad=pn, layer=side, net=q['net'], x=q['x'], y=q['y'], w=pw, h=ph,
                             shape='rect', hole=0.0), new=True, net=q['net'])
    return bd, errs, base, keep


# ============================================================== spatial pairs
def pairs_on_layers(objs, reach=0.3, only_new=False):
    cell = 0.5
    grid = collections.defaultdict(list)
    for o in objs:
        for L, s in o['shapes'].items():
            x0, y0, x1, y1 = sbbox(s)
            for i in range(int(math.floor((x0 - reach) / cell)), int(math.floor((x1 + reach) / cell)) + 1):
                for j in range(int(math.floor((y0 - reach) / cell)), int(math.floor((y1 + reach) / cell)) + 1):
                    grid[(L, i, j)].append(o['id'])
    seen = set()
    for (L, i, j), ids in grid.items():
        n = len(ids)
        for a in range(n):
            for b in range(a + 1, n):
                ia, ib = ids[a], ids[b]
                if ia > ib:
                    ia, ib = ib, ia
                k = (L, ia, ib)
                if k in seen:
                    continue
                seen.add(k)
                yield L, ia, ib


# ============================================================== clearance / shorts
def clearance_scan(bd, ctx, new_only):
    objs = bd.objs
    viol, short, margins = [], [], []
    for L, ia, ib in pairs_on_layers(objs):
        a, b = objs[ia], objs[ib]
        if new_only and not (a['new'] or b['new']):
            continue
        if netkey(a) == netkey(b):
            continue
        if a['kind'] == 'pad' and b['kind'] == 'pad' and a['comp'] == b['comp'] and a['pad'] == b['pad']:
            continue
        g = gap(a['shapes'][L], b['shapes'][L])
        if g > 0.25:
            continue
        rule, name = clearance_rule(a, b, L, ctx)
        rec = dict(layer=L, a=desc(a), b=desc(b), gap=round(g, 5), rule=name, need=round(rule, 5),
                   margin=round(g - rule, 5), new=bool(a['new'] or b['new']))
        if g <= EPS:
            short.append(rec)
        elif g < rule - EPS:
            viol.append(rec)
        if (a['new'] or b['new']) and g - rule < 0.04:
            margins.append(rec)
    return viol, short, margins


def desc(o):
    if o['kind'] == 'pad':
        return 'pad %s-%s [%s]' % (o['comp'], o['pad'], o['net'])
    if o['kind'] == 'via':
        return 'via %s (%.4f,%.4f) %s>%s %.2f/%.2f' % (o['net'], o['x'], o['y'], o['span'][0], o['span'][-1],
                                                    o['size'], o['hole'])
    t = o['src']
    return 'track %s %s (%.4f,%.4f)-(%.4f,%.4f) w%.4f' % (o['net'], o['layer'], t['x1'], t['y1'], t['x2'], t['y2'],
                                                         t['w'])


# ============================================================== holes
def holes(bd):
    H = []
    for o in bd.objs:
        if o['kind'] == 'via':
            H.append((o, o['x'], o['y'], o['hole'], LI[o['span'][0]], LI[o['span'][-1]]))
        elif o['kind'] == 'pad' and o.get('hole', 0) > 0:
            H.append((o, o['x'], o['y'], o['hole'], 0, 5))
    return H


def hole_scan(bd, new_only):
    H = holes(bd)
    out_any, out_shared = [], []
    grid = collections.defaultdict(list)
    for k, h in enumerate(H):
        grid[(int(h[1] / 1.0), int(h[2] / 1.0))].append(k)
    for k, h in enumerate(H):
        gi, gj = int(h[1] / 1.0), int(h[2] / 1.0)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for m in grid.get((gi + di, gj + dj), ()):
                    if m <= k:
                        continue
                    a, b = h, H[m]
                    if new_only and not (a[0]['new'] or b[0]['new']):
                        continue
                    d = math.hypot(a[1] - b[1], a[2] - b[2]) - a[3] / 2 - b[3] / 2
                    if d >= H2H - EPS:
                        continue
                    stacked = math.hypot(a[1] - b[1], a[2] - b[2]) < 1e-4 and (a[5] == b[4] or b[5] == a[4])
                    shared_diel = min(a[5], b[5]) - max(a[4], b[4]) >= 1
                    shared_layer = min(a[5], b[5]) - max(a[4], b[4]) >= 0
                    rec = dict(a=desc(a[0]), b=desc(b[0]), gap=round(d, 5), stacked=stacked,
                               shared_dielectric=shared_diel, shared_layer=shared_layer,
                               new=bool(a[0]['new'] or b[0]['new']))
                    if stacked and H2H_STACK_OK:
                        continue
                    out_any.append(rec)
                    if shared_diel:
                        out_shared.append(rec)
    return out_any, out_shared


# ============================================================== width
def width_scan(bd, ctx, wmap, new_only):
    out = []
    for o in bd.objs:
        if o['kind'] != 'track' or (new_only and not o['new']):
            continue
        lo, hi, name = width_limits(o['net'], o['layer'], ctx, wmap)
        if o['w'] < lo - 1e-5 or o['w'] > hi + 1e-5:
            out.append(dict(track=desc(o), rule=name, min=round(lo, 4), max=round(hi, 4)))
    return out


# ============================================================== mask
def openings(bd, ctx):
    ops = []
    for o in bd.objs:
        if o['kind'] == 'via':
            for side in ('Top', 'Bottom'):
                if side in o['shapes']:
                    e = mask_rule(o, side, ctx)
                    if e is not None:
                        ops.append((o, side, grow(o['shapes'][side], e)))
        elif o['kind'] == 'pad':
            for side in ('Top', 'Bottom'):
                if side in o['shapes']:
                    e = mask_rule(o, side, ctx)
                    ops.append((o, side, grow(o['shapes'][side], e)))
    return ops


def mask_scan(bd, ctx, new_only):
    ops = openings(bd, ctx)
    sliv, foreign = [], []
    by = collections.defaultdict(list)
    for k, (o, side, s) in enumerate(ops):
        x0, y0, x1, y1 = sbbox(s)
        for i in range(int(x0 / 0.5) - 1, int(x1 / 0.5) + 2):
            for j in range(int(y0 / 0.5) - 1, int(y1 / 0.5) + 2):
                by[(side, i, j)].append(k)
    seen = set()
    for key, ks in by.items():
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                p, q = sorted((ks[a], ks[b]))
                if (p, q) in seen:
                    continue
                seen.add((p, q))
                oa, sa, ga = ops[p]
                ob, sb_, gb = ops[q]
                if sa != sb_ or oa['id'] == ob['id']:
                    continue
                if new_only and not (oa['new'] or ob['new']):
                    continue
                w = gap(ga, gb)
                if EPS < w < SLIVER - EPS:
                    sliv.append(dict(side=sa, a=desc(oa), b=desc(ob), web=round(w, 5), need=round(SLIVER, 4),
                                     new=bool(oa['new'] or ob['new'])))
    # other-net copper exposed in an opening (or covered by < 0.05 mm of mask)
    tr = [o for o in bd.objs if o['kind'] in ('track', 'via')]
    for (o, side, s) in ops:
        if o['kind'] != 'pad':
            continue
        for t in tr:
            if side not in t['shapes'] or netkey(t) == netkey(o):
                continue
            if new_only and not (o['new'] or t['new']):
                continue
            g = gap(s, t['shapes'][side])
            if g < 0.05:
                foreign.append(dict(side=side, opening=desc(o), copper=desc(t), cover=round(g, 5),
                                    exposed=g <= 0, new=bool(o['new'] or t['new'])))
    return sliv, foreign, ops


# ============================================================== silk
def text_boxes():
    tb = []
    comps = {c['ref']: c for c in B['components']}
    for t in B['texts']:
        if t['layer'] not in ('TopOverlay', 'BottomOverlay') or t['hidden']:
            continue
        h = t['height']
        w = max(1, len(t['text'])) * h * 1.0       # conservative stroke-font advance (Altium stroke ~0.6-0.9 h)
        st = t.get('stroke', 0.2) / 2
        rot = int(round(t['rot'])) % 360
        dx, dy = (w, h) if rot in (0, 180) else (h, w)
        x0, y0 = t['x'], t['y']
        # anchor ambiguity (rotation / mirror): take the union of every orientation round the anchor
        cands = [(x0, y0, x0 + dx, y0 + dy), (x0 - dx, y0, x0, y0 + dy), (x0, y0 - dy, x0 + dx, y0),
                 (x0 - dx, y0 - dy, x0, y0)]
        if rot == 0 and not t.get('mirror'):
            cands = cands[:1]
        for c in cands:
            tb.append((t, 'Top' if t['layer'] == 'TopOverlay' else 'Bottom', ('b', c[0] - st, c[1] - st, c[2] + st, c[3] + st)))
    return tb


def silk_scan(ops, new_only):
    out = []
    for (t, side, box) in text_boxes():
        for (o, s2, sh) in ops:
            if s2 != side or o['kind'] != 'pad' or (new_only and not o['new']):
                continue
            g = gap(box, sh)
            if g < SILK2MASK - EPS:
                out.append(dict(text=t['text'], comp=t['comp'], side=side, pad=desc(o), gap=round(g, 4)))
    return out


# ============================================================== raster pours
RES = 0.01


def stamp(mask, x0g, y0g, res, s, g):
    ny, nx = mask.shape
    bx0, by0, bx1, by1 = sbbox(grow(s, g))
    i0, i1 = max(0, int((bx0 - x0g) / res) - 1), min(nx, int((bx1 - x0g) / res) + 2)
    j0, j1 = max(0, int((by0 - y0g) / res) - 1), min(ny, int((by1 - y0g) / res) + 2)
    if i0 >= i1 or j0 >= j1:
        return
    X = x0g + (np.arange(i0, i1) + 0.5) * res
    Y = y0g + (np.arange(j0, j1) + 0.5) * res
    XX, YY = np.meshgrid(X, Y)
    if s[0] == 'b':
        dx = np.maximum(np.maximum(s[1] - XX, XX - s[3]), 0)
        dy = np.maximum(np.maximum(s[2] - YY, YY - s[4]), 0)
        m = np.hypot(dx, dy) <= g          # rounded growth, as Altium pours round convex corners
    else:
        x1, y1, x2, y2, r = s[1:6]
        ddx, ddy = x2 - x1, y2 - y1
        L2 = ddx * ddx + ddy * ddy
        if L2 == 0:
            d = np.hypot(XX - x1, YY - y1)
        else:
            t = np.clip(((XX - x1) * ddx + (YY - y1) * ddy) / L2, 0, 1)
            d = np.hypot(XX - x1 - t * ddx, YY - y1 - t * ddy)
        m = d <= r + g
    mask[j0:j1, i0:i1] |= m


def poly_obj(L):
    name, net, _ = PLANE_POLY[L]
    return {'kind': 'poly', 'net': net, 'poly': name, 'comp': None, 'vtype': None, 'multi': False}


def pour(bd, L, ctx, window=None, res=RES):
    name, net, outline = PLANE_POLY[L]
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    if window is None:
        x0g, y0g, x1g, y1g = 0.0, 0.0, 60.96, 25.4
    else:
        x0g, y0g, x1g, y1g = window
    nx, ny = int(round((x1g - x0g) / res)), int(round((y1g - y0g) / res))
    X = x0g + (np.arange(nx) + 0.5) * res
    Y = y0g + (np.arange(ny) + 0.5) * res
    area = (Y[:, None] >= min(ys)) & (Y[:, None] <= max(ys)) & (X[None, :] >= min(xs)) & (X[None, :] <= max(xs))
    void = np.zeros((ny, nx), bool)
    cu = np.zeros((ny, nx), bool)
    po = poly_obj(L)
    for o in bd.objs:
        s = o['shapes'].get(L)
        if s is None:
            continue
        bx = sbbox(s)
        if bx[2] < x0g - 0.3 or bx[0] > x1g + 0.3 or bx[3] < y0g - 0.3 or bx[1] > y1g + 0.3:
            continue
        if o['net'] == net:
            stamp(cu, x0g, y0g, res, s, 0.0)
        else:
            g, _ = clearance_rule(po, o, L, ctx)
            stamp(void, x0g, y0g, res, s, g)
    raw = area & ~void
    lab, n = ndimage.label(raw | cu)
    live = np.unique(lab[cu & (lab > 0)])
    kept = np.isin(lab, live) & (lab > 0)
    return dict(lab=lab, n=n, live=live, kept=kept, raw=raw, void=void, cu=cu, origin=(x0g, y0g), res=res)


def lab_at(pr, x, y):
    x0g, y0g = pr['origin']
    i, j = int((x - x0g) / pr['res']), int((y - y0g) / pr['res'])
    if 0 <= j < pr['lab'].shape[0] and 0 <= i < pr['lab'].shape[1]:
        return int(pr['lab'][j, i])
    return 0


def disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return (xx * xx + yy * yy) <= r * r


# ============================================================== connectivity
class UF:
    def __init__(s):
        s.p = {}

    def f(s, a):
        s.p.setdefault(a, a)
        while s.p[a] != a:
            s.p[a] = s.p[s.p[a]]
            a = s.p[a]
        return a

    def u(s, a, b):
        a, b = s.f(a), s.f(b)
        if a != b:
            s.p[a] = b


def connectivity(bd, pours):
    uf = UF()
    objs = bd.objs
    for o in objs:
        uf.f(o['id'])
    for L, ia, ib in pairs_on_layers(objs, reach=0.01):
        a, b = objs[ia], objs[ib]
        if not a['net'] or a['net'] != b['net']:
            continue
        if gap(a['shapes'][L], b['shapes'][L]) <= 1e-6:
            uf.u(ia, ib)
    for L, pr in pours.items():
        net = PLANE_POLY[L][1]
        for o in objs:
            if o['net'] != net or L not in o['shapes']:
                continue
            s = o['shapes'][L]
            pts = [(s[1], s[2])] if s[0] == 'c' else [((s[1] + s[3]) / 2, (s[2] + s[4]) / 2)]
            for (x, y) in pts:
                lb = lab_at(pr, x, y)
                if lb and pr['kept'][int((y - pr['origin'][1]) / pr['res']), int((x - pr['origin'][0]) / pr['res'])]:
                    uf.u(o['id'], ('pour', L, lb))
    isl = collections.defaultdict(set)
    padisl = collections.defaultdict(set)
    for o in objs:
        if not o['net']:
            continue
        r = uf.f(o['id'])
        isl[o['net']].add(r)
        if o['kind'] == 'pad':
            padisl[o['net']].add(r)
    return uf, isl, padisl


def antennae(bd, uf):
    """track ends (new tracks) that touch no other same-net copper."""
    out = []
    objs = bd.objs
    for o in objs:
        if o['kind'] != 'track' or not o['new']:
            continue
        t = o['src']
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            hit = False
            for p in objs:
                if p['id'] == o['id'] or p['net'] != o['net'] or o['layer'] not in p['shapes']:
                    continue
                s = p['shapes'][o['layer']]
                if contains_pt(grow(s, ANT_TOL + 1e-6), x, y):
                    hit = True
                    break
            if not hit:
                out.append(dict(track=desc(o), end=(x, y)))
    return out


# ============================================================== main
def main():
    t0 = time.time()
    log('dfm_adversary.py  plan=%s  tag=%s' % (args.plan, args.tag))
    log('board_extract md5 source:', B['source']['pcbdoc_md5'], ' plan source:', P.get('source', {}).get('pcbdoc_md5'))
    OUT = {'plan': args.plan, 'tag': args.tag}
    if B['source']['pcbdoc_md5'] != P.get('source', {}).get('pcbdoc_md5'):
        log('!! plan was made against a different PcbDoc')
    cls_after = classes_with(P.get('net_class_add'))
    base = build_baseline()
    after, errs, _, _ = build_after(P)
    log('\n== 0. apply: %d errors' % len(errs))
    for e in errs:
        log('   ', e)
    OUT['apply_errors'] = [str(e) for e in errs]

    # ---------------------------------------------------------------- calibration on the unmodified board
    log('\n== 1. CALIBRATION on the unmodified board (DRC 0 => a correct interpretation reports 0)')
    calib = {}
    ctx_b = {'classes': CLASSES0, 'via_onlayer': True, 'name': 'b_vy'}
    ctx_bn = {'classes': CLASSES0, 'via_onlayer': False, 'name': 'b_vn'}
    for nm, c in (('vias OnLayer=TRUE', ctx_b), ('vias OnLayer=FALSE', ctx_bn)):
        v, s, _ = clearance_scan(base, c, new_only=False)
        calib['clearance ' + nm] = (len(v), len(s))
        log('   clearance, %-20s violations %d, shorts %d' % (nm, len(v), len(s)))
        for x in v[:6]:
            log('       ', x)
    ok_maps = []
    for nm, wm in WMAPS.items():
        w = width_scan(base, ctx_b, wm, new_only=False)
        calib['width ' + nm] = len(w)
        log('   width map %-40s violations %d' % (nm, len(w)))
        for x in w[:3]:
            log('       ', x)
        if not w:
            ok_maps.append(nm)
    WMAP = WMAPS[ok_maps[0]] if ok_maps else WMAPS['A(L3=MID1,L4=MID2,L2=MID3,L5=MID4)']
    ha, hs = hole_scan(base, new_only=False)
    hl = [x for x in ha if x['shared_layer']]
    calib['hole2hole any-span / shared-layer / shared-dielectric'] = (len(ha), len(hl), len(hs))
    log('   hole-to-hole %.4f (stacked microvias exempt): any-span %d, sharing a copper layer %d, sharing a drilled dielectric %d' % (
        H2H, len(ha), len(hl), len(hs)))
    log('     -> DRC 0 on the board means Altium checks hole pairs whose spans SHARE A DIELECTRIC (any-span and shared-layer would fire)')
    for x in hl[:3]:
        log('       e.g. shared-layer pair the DRC accepts:', x)
    sl, fo, ops_b = mask_scan(base, ctx_b, new_only=False)
    calib['mask slivers'] = len(sl)
    calib['foreign copper exposed'] = sum(1 for x in fo if x['exposed'])
    log('   mask slivers < %.4f: %d ; other-net copper exposed in an opening: %d' % (SLIVER, len(sl), calib['foreign copper exposed']))
    for x in sl[:4]:
        log('       ', x)
    hs_bad = []
    for o in base.objs:
        if o['kind'] == 'via':
            lo, hi, nm = holesize_rule(o, ctx_b)
            if not (lo - 1e-4 <= o['hole'] <= hi + 1e-4):
                hs_bad.append((desc(o), nm))
    calib['holesize'] = len(hs_bad)
    log('   HoleSize with typed vias (thru / micro / L3-L4 buried): %d violations' % len(hs_bad))
    via_templates = collections.Counter((round(o['size'], 4), round(o['hole'], 4), o['span'][0], o['span'][-1])
                                        for o in base.objs if o['kind'] == 'via')
    OUT['calibration'] = calib
    VIA_ONLAYER = calib['clearance vias OnLayer=TRUE'] == (0, 0)
    log('   -> using via OnLayer=%s (both are reported for the plan anyway), width map %s' % (VIA_ONLAYER, ok_maps))

    # ---------------------------------------------------------------- plan bookkeeping
    log('\n== 2. plan bookkeeping')
    book = []
    nca = P.get('net_class_add', {})
    newnets = sorted({p['pad1']['net'] for p in P['parts']})
    for n in newnets:
        if n not in nca.get('SDRAM_DATA', []):
            book.append('net %s NOT added to SDRAM_DATA' % n)
    log('   new U3-side nets: %s' % newnets)
    log('   SDRAM-D10 in SDRAM_DATA add-list: %s' % ('SDRAM-D10' in nca.get('SDRAM_DATA', [])))
    comps = {c['ref']: c for c in B['components']}
    # pad-1 offset convention by (footprint, side, rot) from the board's own R0201 / C0201 parts
    conv = {}
    padsby = collections.defaultdict(dict)
    for p in B['pads']:
        padsby[p['ref']][p['pad']] = p
    for c in B['components']:
        if c['footprint'] in ('R0201', 'C0201') and '1' in padsby[c['ref']]:
            p1 = padsby[c['ref']]['1']
            conv[(c['side'], int(c['rot']) % 360)] = (round(p1['x'] - c['x'], 3), round(p1['y'] - c['y'], 3))
    for part in P['parts']:
        if part['ref'] in comps:
            book.append('%s already exists on the board' % part['ref'])
        exp = conv.get((part['side'], int(part['rot']) % 360))
        off = (round(part['pad1']['x'] - part['x'], 3), round(part['pad1']['y'] - part['y'], 3))
        if exp is None:
            # Top rot 0 never occurs on the board: the library default (pad 1 at -x) is implied by Top rot 180 = +x
            r180 = conv.get((part['side'], (int(part['rot']) + 180) % 360))
            exp = (-r180[0], -r180[1]) if r180 else None
        if exp is not None and (abs(exp[0] - off[0]) > 1e-3 or abs(exp[1] - off[1]) > 1e-3):
            book.append('%s pad 1 offset %s does not match the footprint convention %s for %s rot %s' %
                        (part['ref'], off, exp, part['side'], part['rot']))
        log('   %-5s %-6s rot %3d  pad1 %s exp %s  pad1 net %-10s pad2 net %-4s hidden=%s' % (
            part['ref'], part['side'], part['rot'], off, exp, part['pad1']['net'], part['pad2']['net'],
            part.get('designator_hidden')))
        if not part.get('designator_hidden'):
            book.append('%s designator not hidden' % part['ref'])
        bit = part['net_bit']
        if part['pad1']['net'] != 'SDRAM-D%d' % bit or part['pad2']['net'] != 'D%d' % bit:
            book.append('%s pad nets do not match bit %d' % (part['ref'], bit))
    # U3 renet: old net must be Dn
    for r in P['renet_pads']:
        p = padsby[r['ref']][r['pad']]
        if r['net'] != 'SDRAM-' + p['net']:
            book.append('renet %s-%s: board net %s -> %s' % (r['ref'], r['pad'], p['net'], r['net']))
    # every new track 0/45/90 degrees (RoutingCorners is a router rule, not a batch-DRC rule: info only)
    offangle = []
    for t in P['tracks']:
        dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
        if abs(dx) > 1e-6 and abs(dy) > 1e-6 and abs(abs(dx) - abs(dy)) > 2e-4:
            offangle.append(t)
    # every new via a board template
    for v in P['vias'] + P['microvias']:
        i0, i1 = sorted((LI[LN(v['from'])], LI[LN(v['to'])]))
        key = (round(v['size'], 4), round(v['hole'], 4), STACK[i0], STACK[i1])
        if key not in via_templates:
            book.append('via %s at (%.3f,%.3f) %s matches no via already on the board' % (v['net'], v['x'], v['y'], key))
    nb_off = sum(1 for o in base.objs if o['kind'] == 'track' and abs(o['src']['x2'] - o['src']['x1']) > 1e-6 and
                 abs(o['src']['y2'] - o['src']['y1']) > 1e-6 and
                 abs(abs(o['src']['x2'] - o['src']['x1']) - abs(o['src']['y2'] - o['src']['y1'])) > 2e-4)
    log('   info: %d plan tracks are any-angle (%d of them renames of existing copper); the unmodified board already has %d any-angle copper tracks' % (
        len(offangle), sum(1 for t in offangle if t.get('why') == 'rename'), nb_off))
    for t in offangle:
        if 'D10' in t['net'] or 'D11' in t['net']:
            log('       any-angle D10/D11 track: %s' % t)
    OUT['any_angle_tracks'] = offangle
    for b_ in book:
        log('   !!', b_)
    log('   bookkeeping problems: %d' % len(book))
    OUT['bookkeeping'] = book

    # ---------------------------------------------------------------- rule checks on the after-board
    ctxA = {'classes': cls_after, 'via_onlayer': True, 'name': 'a_vy'}
    ctxAn = {'classes': cls_after, 'via_onlayer': False, 'name': 'a_vn'}
    ctxA0 = {'classes': CLASSES0, 'via_onlayer': True, 'name': 'a0_vy'}   # if the class add were forgotten
    log('\n== 3. copper clearance + shorts, ALL PAIRS on the after-board (baseline subtracted)')
    res3 = {}
    for nm, c in (('classes updated, via OnLayer=TRUE', ctxA), ('classes updated, via OnLayer=FALSE', ctxAn),
                  ('class add FORGOTTEN, via OnLayer=TRUE', ctxA0)):
        v, s, m = clearance_scan(after, c, new_only=False)
        log('   %-40s violations %d (on new/changed objects %d), shorts %d' % (
            nm, len(v), sum(1 for x in v if x['new']), len(s)))
        for x in v + s:
            log('       ', x)
        res3[nm] = dict(violations=v, shorts=s)
        if c is ctxA:
            margins = sorted(m, key=lambda r: r['margin'])
    log('   tightest margins on new/changed objects (gap - rule < 0.04 mm), classes updated, via OnLayer=TRUE:')
    for x in margins[:40]:
        log('       %+.4f  %-9s %s  <->  %s  gap %.4f (%s %.4f)' % (x['margin'], x['layer'], x['a'], x['b'], x['gap'],
                                                                 x['rule'], x['need']))
    OUT['clearance'] = res3
    OUT['margins'] = margins

    log('\n== 4. hole-to-hole %.4f mm (new holes vs every hole)' % H2H)
    ha, hs = hole_scan(after, new_only=True)
    log('   CALIBRATED (shared dielectric) violations %d ; any-span (info) %d' % (len(hs), len(ha)))
    for x in hs:
        log('       VIOL', x)
    for x in ha:
        if not x['shared_dielectric']:
            log('       info (no shared dielectric, DRC-legal):', x)
    # worst new-hole spacing for the record
    H = holes(after)
    worst = []
    for h in H:
        if not h[0]['new']:
            continue
        for k in H:
            if k[0]['id'] == h[0]['id']:
                continue
            d0 = math.hypot(h[1] - k[1], h[2] - k[2])
            if d0 < 1e-4:
                continue
            d = d0 - h[3] / 2 - k[3] / 2
            if d < 0.30:
                worst.append((round(d, 4), desc(h[0]), desc(k[0]), min(h[5], k[5]) - max(h[4], k[4]) >= 1))
    worst = sorted(set(worst))[:8]
    for w_ in worst:
        log('       closest: %.4f  %s  <->  %s  shared-dielectric=%s' % w_)
    OUT['hole_to_hole'] = dict(any=ha, shared=hs, closest=worst)

    log('\n== 5. via typing / HoleSize / RoutingVias on new vias')
    vt = []
    for o in after.objs:
        if o['kind'] != 'via' or not o['new']:
            continue
        lo, hi, nm = holesize_rule(o, ctxA)
        vs = viastyle_rule(o, ctxA)
        ok_h = lo - 1e-4 <= o['hole'] <= hi + 1e-4
        ok_s = vs is None or (vs[0] - 1e-4 <= o['size'] <= vs[1] + 1e-4 and vs[2] - 1e-4 <= o['hole'] <= vs[3] + 1e-4)
        o2 = dict(o)
        o2['vtype'] = 'thru' if len(o['span']) == 6 else None   # untyped (scripted) via: only the generic rule
        lo2, hi2, nm2 = holesize_rule(o2, ctxA)
        untyped_ok = lo2 - 1e-4 <= o['hole'] <= hi2 + 1e-4
        vt.append(dict(via=desc(o), type=o['vtype'], holesize_rule=nm, ok=ok_h, viastyle=vs[-1] if vs else None,
                       viastyle_ok=ok_s, passes_if_left_untyped=untyped_ok))
        log('   %-60s type %-6s %s %s | %s %s | untyped would %s' % (
            desc(o), o['vtype'], nm, 'OK' if ok_h else 'FAIL', vs[-1] if vs else '-', 'OK' if ok_s else 'FAIL',
            'pass' if untyped_ok else 'FAIL'))
    OUT['via_typing'] = vt

    log('\n== 6. width rules (Width map %s) on new/renamed tracks' % ok_maps)
    w1 = width_scan(after, ctxA, WMAP, new_only=True)
    w0 = width_scan(after, ctxA0, WMAP, new_only=True)
    log('   classes updated: %d violations ; class add forgotten: %d' % (len(w1), len(w0)))
    for x in w1 + w0:
        log('       ', x)
    wl = collections.Counter()
    for o in after.objs:
        if o['kind'] == 'track' and o['new']:
            lo, hi, nm = width_limits(o['net'], o['layer'], ctxA, WMAP)
            lo0, hi0, nm0 = width_limits(o['net'], o['layer'], ctxA0, WMAP)
            wl[(o['net'], o['layer'], o['w'], nm, lo, hi, nm0)] += 1
    for k, n in sorted(wl.items()):
        if k[0].startswith('SDRAM-D10') or k[0] in ('D10', 'D11', 'SDRAM-D11'):
            log('       %-10s %-7s w %.4f  %-14s [%.4f, %.4f]  (without class add: %s)  x%d' % (k + (n,)))
    OUT['width'] = dict(updated=w1, forgotten=w0)

    log('\n== 7. solder mask (expansion from Rules6, vias tented) on new/changed pads')
    sl, fo, ops = mask_scan(after, ctxA, new_only=True)
    log('   slivers < %.4f: %d' % (SLIVER, len(sl)))
    for x in sl:
        log('       ', x)
    exp_ = [x for x in fo if x['exposed']]
    log('   other-net copper EXPOSED in a new/changed opening: %d' % len(exp_))
    for x in exp_:
        log('       ', x)
    log('   other-net copper under < 0.05 mm of mask next to an opening (registration watch-list):')
    for x in sorted(fo, key=lambda r: r['cover']):
        if not x['exposed']:
            log('       cover %.4f  %s | %s' % (x['cover'], x['opening'], x['copper']))
    # webs between new openings
    webs = []
    newops = [(o, s, g) for (o, s, g) in ops if o['new'] and o['kind'] == 'pad']
    for (o, s, g) in newops:
        best = None
        for (q, s2, g2) in ops:
            if s2 != s or q['id'] == o['id'] or netkey(q) == netkey(o):
                continue
            w = gap(g, g2)
            if best is None or w < best[0]:
                best = (round(w, 4), desc(q))
        webs.append((desc(o), best))
    for w_ in webs:
        if w_[0].startswith('pad R129') or w_[0].startswith('pad R130'):
            log('       narrowest other-net web from %s: %s' % w_)
    OUT['mask'] = dict(slivers=sl, foreign=fo, webs=webs)

    log('\n== 8. silk (visible overlay text, conservative box) vs new openings, need %.4f' % SILK2MASK)
    sk = silk_scan(ops, new_only=True)
    log('   violations %d' % len(sk))
    for x in sk:
        log('       ', x)
    OUT['silk'] = sk

    log('\n== 9. component clearance (%.4f) and IPC-7351B courtyards' % CC_GAP)
    boxes = collections.defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
    full = collections.defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
    sides = {}

    def ext(bx, b):
        bx[0], bx[1], bx[2], bx[3] = min(bx[0], b[0]), min(bx[1], b[1]), max(bx[2], b[2]), max(bx[3], b[3])

    plan_refs = {p['ref'] for p in P['parts']}
    for c in B['components']:
        if c['ref'] in plan_refs:
            continue
        sides[c['ref']] = c['side']
    for o in after.objs:
        if o['kind'] == 'pad':
            s = list(o['shapes'].values())[0]
            ext(boxes[o['comp']], sbbox(s))
            ext(full[o['comp']], sbbox(s))
    for ref, d in B['component_outlines'].items():
        for k, b in d.items():
            if ref in plan_refs:
                continue
            ext(full[ref], b)
    u3b = B['u3']['body']['max']
    ext(full['U3'], (u3b['x0'], u3b['y0'], u3b['x1'], u3b['y1']))
    multi = {o['comp'] for o in after.objs if o['kind'] == 'pad' and o['multi']}
    cc = []
    BODY_NOM, BODY_MAX = (0.60, 0.30), (0.63, 0.33)
    for part in P['parts']:
        ref, side = part['ref'], part['side']
        pb = boxes[ref]
        rot = int(part['rot']) % 180
        bl, bw = BODY_MAX if True else BODY_NOM
        bodyx, bodyy = (bl / 2, bw / 2) if rot == 0 else (bw / 2, bl / 2)
        body = (part['x'] - bodyx, part['y'] - bodyy, part['x'] + bodyx, part['y'] + bodyy)
        cy = (min(pb[0], body[0]) - 0.15, min(pb[1], body[1]) - 0.15, max(pb[2], body[2]) + 0.15, max(pb[3], body[3]) + 0.15)
        for other, os_ in list(sides.items()) + [(p['ref'], p['side']) for p in P['parts'] if p['ref'] != ref]:
            if other == ref or (os_ != side and other not in multi):
                continue
            ob, of = boxes.get(other), full.get(other)
            if ob is None or ob[0] > 1e8:
                continue
            g_p = box_box(tuple(pb), tuple(ob))
            g_f = box_box(tuple(pb), tuple(of)) if of[0] < 1e8 else g_p
            if g_p == 0 and other in multi and (ob[2] - ob[0]) * (ob[3] - ob[1]) > 100:
                # the part sits INSIDE a perimeter header's bounding box (X2 rings the whole board): use its pads
                g_p = g_f = min(gap(('b',) + tuple(pb), list(o['shapes'].values())[0]) for o in after.objs
                                if o['kind'] == 'pad' and o['comp'] == other)
                of = ob = [pb[0] - g_p - 1, pb[1] - g_p - 1, pb[0] - g_p, pb[1] - g_p]
            if min(g_p, g_f) > 1.0:
                continue
            if other in plan_refs:
                op = next(p for p in P['parts'] if p['ref'] == other)
                orot = int(op['rot']) % 180
                ox, oy = (bl / 2, bw / 2) if orot == 0 else (bw / 2, bl / 2)
                obody = (op['x'] - ox, op['y'] - oy, op['x'] + ox, op['y'] + oy)
                ocy = (min(ob[0], obody[0]) - 0.15, min(ob[1], obody[1]) - 0.15, max(ob[2], obody[2]) + 0.15, max(ob[3], obody[3]) + 0.15)
                bodygap = box_box(body, obody)
            else:
                exc = 0.15 if (other.startswith('R') or other.startswith('C')) else 0.25
                ocy = (of[0] - exc, of[1] - exc, of[2] + exc, of[3] + exc)
                bodygap = box_box(body, tuple(of))
            ov = max(0.0, min(cy[2], ocy[2]) - max(cy[0], ocy[0])) if box_box(cy, ocy) == 0 else 0.0
            ovy = max(0.0, min(cy[3], ocy[3]) - max(cy[1], ocy[1])) if box_box(cy, ocy) == 0 else 0.0
            rec = dict(part=ref, other=other, pad_box_gap=round(g_p, 4), full_box_gap=round(g_f, 4),
                       body_gap_max=round(bodygap, 4), courtyard_overlap=round(min(ov, ovy), 4),
                       body=[round(v, 4) for v in body], other_box=[round(v, 4) for v in of])
            if g_p < CC_GAP - EPS or g_f < CC_GAP - EPS or rec['courtyard_overlap'] > 0:
                cc.append(rec)
    for x in sorted(cc, key=lambda r: r['pad_box_gap']):
        flag = 'VIOL(pad box)' if x['pad_box_gap'] < CC_GAP - EPS else ('viol(full box)' if x['full_box_gap'] < CC_GAP - EPS else 'courtyard only')
        log('   %-5s vs %-6s pad-box %.4f full-box %.4f body(max) %.4f courtyard overlap %.4f  %s' % (
            x['part'], x['other'], x['pad_box_gap'], x['full_box_gap'], x['body_gap_max'], x['courtyard_overlap'], flag))
    # explicit look at U1 / U2 for the Top parts
    for part in P['parts']:
        if part['side'] != 'Top':
            continue
        pb = boxes[part['ref']]
        for other in ('U1', 'U2'):
            log('   %-5s to %s: pad box %.4f, full box (pads+mech) %.4f' % (
                part['ref'], other, box_box(tuple(pb), tuple(boxes[other])), box_box(tuple(pb), tuple(full[other]))))
    OUT['components'] = cc

    log('\n== 10. tombstoning: per-pad solderable area (pad + same-net copper inside the opening) and attached copper')
    tomb = []
    for part in P['parts']:
        rows = []
        for pn in ('1', '2'):
            po = next(o for o in after.objs if o['kind'] == 'pad' and o['comp'] == part['ref'] and o['pad'] == pn)
            side = part['side']
            ps = po['shapes'][side]
            e = mask_rule(po, side, ctxA)
            op = grow(ps, e)
            res = 0.002
            x0, y0, x1, y1 = sbbox(op)
            nx, ny = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
            m = np.zeros((ny, nx), bool)
            stamp(m, x0, y0, res, ps, 0.0)
            att = []
            vip = []
            for o in after.objs:
                if o['id'] == po['id'] or o['net'] != po['net'] or side not in o['shapes']:
                    continue
                s = o['shapes'][side]
                if gap(s, ps) <= 1e-6:
                    if o['kind'] == 'track':
                        att.append(round(o['w'], 4))
                    elif o['kind'] == 'via':
                        if contains_pt(ps, o['x'], o['y']):
                            vip.append('%s>%s' % (o['span'][0], o['span'][-1]))
                        else:
                            att.append('via-ring')
                if gap(s, op) <= 0:
                    stamp(m, x0, y0, res, s, 0.0)
            opm = np.zeros_like(m)
            stamp(opm, x0, y0, res, op, 0.0)
            area = float((m & opm).sum()) * res * res
            plane_vip = any(('L2-GND' in v or 'L5-VCC3V3' in v) for v in vip) and po['net'] in ('GND', 'VCC3V3')
            rows.append(dict(pad=pn, net=po['net'], area=round(area, 5), tracks=att, vip=vip, plane=plane_vip))
        a1, a2 = rows[0]['area'], rows[1]['area']
        asym = abs(a1 - a2) / max(a1, a2)
        wsum = [sum(x for x in r['tracks'] if isinstance(x, float)) for r in rows]
        vipasym = (len(rows[0]['vip']) > 0) != (len(rows[1]['vip']) > 0)
        flag = asym > 0.10 or vipasym or rows[0]['plane'] != rows[1]['plane'] or (max(wsum) > 2 * min(wsum) + 0.05)
        tomb.append(dict(part=part['ref'], rows=rows, area_asym=round(asym, 4), attached_width=wsum, flag=flag))
        log('   %-5s %-6s pad1 area %.4f tracks %-18s vip %-34s | pad2 area %.4f tracks %-18s vip %-34s | asym %4.1f %% %s' % (
            part['ref'], part['side'], a1, rows[0]['tracks'], rows[0]['vip'], a2, rows[1]['tracks'], rows[1]['vip'],
            100 * asym, 'FLAG' if flag else 'ok'))
    OUT['tombstone'] = tomb

    log('\n== 11. pours L2-GND / L5-VCC3V3 re-poured (raster %.3f mm, Rules6 clearances via the polygon scope)' % RES)
    pours_b, pours_a = {}, {}
    pres = {}
    for L in ('L2-GND', 'L5-VCC3V3'):
        pb_ = pour(base, L, ctx_b)
        pa_ = pour(after, L, ctxA)
        pours_b[L], pours_a[L] = pb_, pa_
        # islands that survive dead-copper removal, and copper area
        dead_b = len(np.setdiff1d(np.unique(pb_['lab'][pb_['lab'] > 0]), pb_['live']))
        dead_a = len(np.setdiff1d(np.unique(pa_['lab'][pa_['lab'] > 0]), pa_['live']))
        ab = pb_['kept'].sum() * RES * RES
        aa = pa_['kept'].sum() * RES * RES
        # plane-net objects not on the biggest island
        def off_main(pr, bd):
            sizes = np.bincount(pr['lab'].ravel())
            sizes[0] = 0
            main = int(np.argmax(sizes))
            net = PLANE_POLY[L][1]
            n = 0
            for o in bd.objs:
                if o['net'] == net and L in o['shapes']:
                    s = o['shapes'][L]
                    x, y = (s[1], s[2]) if s[0] == 'c' else ((s[1] + s[3]) / 2, (s[2] + s[4]) / 2)
                    if lab_at(pr, x, y) != main:
                        n += 1
            return n
        ob_, oa_ = off_main(pb_, base), off_main(pa_, after)
        log('   %-10s live islands %d -> %d ; dead islands removed %d -> %d ; plane-net objects off the main island %d -> %d ; copper %.3f -> %.3f mm2 (%+.4f)' % (
            L, len(pb_['live']), len(pa_['live']), dead_b, dead_a, ob_, oa_, ab, aa, aa - ab))
        pres[L] = dict(live=(len(pb_['live']), len(pa_['live'])), dead=(dead_b, dead_a), off_main=(ob_, oa_),
                       area=(round(ab, 4), round(aa, 4)))
    # fine windows round every changed object that touches L2 / L5
    log('   fine windows (0.0025 mm) round each changed L2/L5 object: new necks/slivers narrower than 0.10 mm')
    changed = []
    bset = {(o['kind'], o['net'], round(o.get('x', 0), 4), round(o.get('y', 0), 4), tuple(o.get('span', ())))
            for o in base.objs if o['kind'] == 'via'}
    aset = {(o['kind'], o['net'], round(o.get('x', 0), 4), round(o.get('y', 0), 4), tuple(o.get('span', ())))
            for o in after.objs if o['kind'] == 'via'}
    for k in (bset ^ aset):
        span = k[4]
        for L in ('L2-GND', 'L5-VCC3V3'):
            if L in span:
                changed.append((L, k[2], k[3], k[1], 'added' if k in aset else 'removed'))
    pad_changes = [o for o in after.objs if o['kind'] == 'pad' and o['new'] and o['multi']]
    win_res = []
    done = set()
    for (L, x, y, net, how) in sorted(changed):
        key = (L, round(x, 1), round(y, 1))
        if key in done:
            continue
        done.add(key)
        w = (x - 0.8, y - 0.8, x + 0.8, y + 0.8)
        fb = pour(base, L, ctx_b, window=w, res=0.0025)
        fa = pour(after, L, ctxA, window=w, res=0.0025)
        # treat window-edge-touching copper as kept (it continues outside the window)
        def kept_w(f):
            cop = f['raw'] | f['cu']
            lab, n = ndimage.label(cop)
            edge = np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]]))
            live = np.union1d(edge[edge > 0], np.unique(lab[f['cu'] & (lab > 0)]))
            return np.isin(lab, live) & (lab > 0), lab, n
        kb, _, _ = kept_w(fb)
        ka, laba, na = kept_w(fa)
        dk = disk(20)                            # 0.05 mm radius -> features narrower than 0.10 mm
        nb = kb & ~ndimage.binary_opening(kb, structure=dk)
        mna = ka & ~ndimage.binary_opening(ka, structure=dk)
        newn = mna & ~ndimage.binary_dilation(nb, structure=disk(2))
        lb2, n2 = ndimage.label(newn)
        sl_ = []
        for i in range(1, n2 + 1):
            a_ = float((lb2 == i).sum()) * 0.0025 ** 2
            if a_ >= 2e-4:
                jj, ii = np.nonzero(lb2 == i)
                sl_.append(dict(area_mm2=round(a_, 5), at=(round(w[0] + (ii.mean() + 0.5) * 0.0025, 3),
                                                             round(w[1] + (jj.mean() + 0.5) * 0.0025, 3))))
        # dead islands created inside the window
        dead_a = 0
        lab_a, n_a = ndimage.label(fa['raw'] | fa['cu'])
        for i in range(1, n_a + 1):
            m = lab_a == i
            if not (m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any() or (m & fa['cu']).any()):
                if m.sum() * 0.0025 ** 2 > 1e-5:
                    dead_a += 1
        win_res.append(dict(layer=L, at=(x, y), net=net, how=how, new_narrow=sl_, dead_islands_after=dead_a))
        log('      %-10s (%.3f,%.3f) %-10s %-7s new narrow regions %d %s ; dead islands in window after %d' % (
            L, x, y, net, how, len(sl_), sl_[:3], dead_a))
    pres['windows'] = win_res
    # reference-plane: signal tracks newly over a void
    log('   signal tracks newly over a plane void (Top/L3 -> L2, L4/Bottom -> L5), length > 0.01 mm:')
    refl = {'Top': 'L2-GND', 'L3-SIG': 'L2-GND', 'L4-SIG': 'L5-VCC3V3', 'Bottom': 'L5-VCC3V3'}

    def void_len(o, pr, prb=None):
        """length of the track centreline over a void of pr (and, with prb, over copper of prb = NEWLY voided)."""
        t = o['src']
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        n = max(2, int(L / 0.005))
        c = 0
        for k in range(n + 1):
            x = t['x1'] + (t['x2'] - t['x1']) * k / n
            y = t['y1'] + (t['y2'] - t['y1']) * k / n
            i, j = int(x / RES), int(y / RES)
            if 0 <= j < pr['kept'].shape[0] and 0 <= i < pr['kept'].shape[1] and not pr['kept'][j, i]:
                if prb is None or prb['kept'][j, i]:
                    c += 1
        return L * c / (n + 1)
    btr = {}
    for o in base.objs:
        if o['kind'] == 'track':
            t = o['src']
            btr[(o['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))] = o
    rp = []
    for o in after.objs:
        if o['kind'] != 'track':
            continue
        L = refl[o['layer']]
        t = o['src']
        x0, x1 = min(t['x1'], t['x2']), max(t['x1'], t['x2'])
        y0, y1 = min(t['y1'], t['y2']), max(t['y1'], t['y2'])
        near = any(abs(c[1] - (x0 + x1) / 2) < (x1 - x0) / 2 + 1.0 and abs(c[2] - (y0 + y1) / 2) < (y1 - y0) / 2 + 1.0
                   for c in changed if c[0] == L)
        if not near and not o['new']:
            continue
        va = void_len(o, pours_a[L])
        vn = void_len(o, pours_a[L], pours_b[L])
        if vn > 0.01:
            rp.append(dict(track=desc(o), ref=L, over_void_after=round(va, 3), newly_voided=round(vn, 3)))
    for x in rp:
        log('       ', x)
    log('   -> %d tracks' % len(rp))
    pres['ref_plane'] = rp
    OUT['pours'] = pres
    log('   Top / Bottom pours: %d polygons on Top/Bottom in the extract (only %s exist)' % (
        sum(1 for pg in B['polygons'] if pg['layer'] in ('TOP', 'BOTTOM', 'Top', 'Bottom')), [pg['name'] for pg in B['polygons']]))

    log('\n== 12. connectivity: net islands over ALL nets (pours included), shorts, R bypass, antennae')
    ufb, isb, pib = connectivity(base, pours_b)
    ufa, isa, pia = connectivity(after, pours_a)
    worse = []
    for n in sorted(set(isb) | set(isa)):
        nb_, na_ = len(pib.get(n, ())), len(pia.get(n, ()))
        if na_ > max(1, nb_) or (n not in isb and na_ != 1):
            worse.append((n, nb_, na_))
    base_multi = sorted((n, len(pib[n])) for n in pib if len(pib[n]) > 1)
    log('   nets on the board before %d, after %d' % (len(pib), len(pia)))
    log('   nets whose PADS sit on >1 island before (baseline): %s' % base_multi)
    log('   nets with more pad islands after than before (or a new net not in 1 island): %s' % worse)
    # per-bit split check
    split = []
    for part in P['parts']:
        bit = part['net_bit']
        n1, n2 = 'SDRAM-D%d' % bit, 'D%d' % bit
        pads1 = sorted('%s-%s' % (o['comp'], o['pad']) for o in after.objs if o['kind'] == 'pad' and o['net'] == n1)
        pads2 = sorted('%s-%s' % (o['comp'], o['pad']) for o in after.objs if o['kind'] == 'pad' and o['net'] == n2)
        r1 = {ufa.f(o['id']) for o in after.objs if o['net'] == n1}
        r2 = {ufa.f(o['id']) for o in after.objs if o['net'] == n2}
        # physical bypass: any copper of n1 touching n2 (net-agnostic)
        cu1 = [o for o in after.objs if o['net'] == n1]
        cu2 = [o for o in after.objs if o['net'] == n2]
        byp = 0
        for a in cu1:
            for b in cu2:
                for L in set(a['shapes']) & set(b['shapes']):
                    if gap(a['shapes'][L], b['shapes'][L]) <= 1e-6:
                        byp += 1
        c1 = sum(math.hypot(o['src']['x2'] - o['src']['x1'], o['src']['y2'] - o['src']['y1']) for o in cu1 if o['kind'] == 'track')
        split.append(dict(bit=bit, part=part['ref'], n1=n1, islands1=len(r1), pads1=pads1, n2=n2, islands2=len(r2),
                          pads2=pads2, bypass_contacts=byp, n1_track_mm=round(c1, 3)))
        log('   D%-2d %-5s %-10s islands %d pads %-22s | %-4s islands %d pads %-22s | bypass contacts %d | U3-side track %.3f mm' % (
            bit, part['ref'], n1, len(r1), pads1, n2, len(r2), pads2, byp, c1))
    ant = antennae(after, ufa)
    log('   dangling new-track ends (NetAntennae tol %.4f): %d %s' % (ANT_TOL, len(ant), ant[:5]))
    # D10 untouched? (still unsplit)
    OUT['connectivity'] = dict(worse=worse, baseline_multi=base_multi, split=split, antennae=ant)

    log('\n== 13. acid traps: same-net track corners on new tracks with an interior angle < 90 deg outside a pad')
    acid = []
    pads_all = [o for o in after.objs if o['kind'] == 'pad']
    trs = [o for o in after.objs if o['kind'] == 'track']
    ends = collections.defaultdict(list)
    for o in trs:
        t = o['src']
        ends[(o['layer'], o['net'], round(t['x1'], 4), round(t['y1'], 4))].append((o, (t['x2'] - t['x1'], t['y2'] - t['y1'])))
        ends[(o['layer'], o['net'], round(t['x2'], 4), round(t['y2'], 4))].append((o, (t['x1'] - t['x2'], t['y1'] - t['y2'])))
    for (L, net, x, y), lst in ends.items():
        if len(lst) < 2 or not any(o['new'] for o, _ in lst):
            continue
        inpad = any(L in p['shapes'] and contains_pt(p['shapes'][L], x, y) for p in pads_all)
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (a, va), (b, vb) = lst[i], lst[j]
                na, nb_ = math.hypot(*va), math.hypot(*vb)
                if na < 1e-9 or nb_ < 1e-9:
                    continue
                ang = math.degrees(math.acos(max(-1, min(1, (va[0] * vb[0] + va[1] * vb[1]) / (na * nb_)))))
                if ang < 90 - 1e-6 and not inpad:
                    acid.append(dict(at=(x, y), layer=L, net=net, angle=round(ang, 1)))
                if ang < 135 - 1e-6 and ('D10' in net or 'D11' in net):
                    log('   corner %-9s %-7s (%.4f,%.4f) %.1f deg %s' % (net, L, x, y, ang, 'inside a pad' if inpad else 'OUTSIDE a pad'))
    log('   acute corners outside pads on new copper: %d %s' % (len(acid), acid[:6]))
    OUT['acid_traps'] = acid

    # ---------------------------------------------------------------- verdict
    cv = res3['classes updated, via OnLayer=TRUE']
    cvn = res3['classes updated, via OnLayer=FALSE']
    fails = []
    if errs:
        fails.append('apply errors %d' % len(errs))
    if book:
        fails.append('bookkeeping %d' % len(book))
    if cv['violations'] or cv['shorts'] or cvn['violations'] or cvn['shorts']:
        fails.append('clearance/short')
    if hs:
        fails.append('hole-to-hole %d' % len(hs))
    if w1:
        fails.append('width %d' % len(w1))
    if sl or exp_:
        fails.append('mask %d/%d' % (len(sl), len(exp_)))
    if sk:
        fails.append('silk %d' % len(sk))
    if worse or any(s['islands1'] != 1 or s['islands2'] != 1 or s['bypass_contacts'] for s in split) or ant:
        fails.append('connectivity')
    if acid:
        fails.append('acid traps %d' % len(acid))
    if any(pres[L]['live'][1] > pres[L]['live'][0] or pres[L]['off_main'][1] > pres[L]['off_main'][0] for L in ('L2-GND', 'L5-VCC3V3')):
        fails.append('pour islands')
    ccv = [x for x in cc if x['pad_box_gap'] < CC_GAP - EPS]
    log('\n== VERDICT inputs: hard failures %s ; ComponentClearance pad-box violations %d (batch DRC does not run it) ; '
        'tombstone flags %s ; elapsed %.0f s' % (fails or 'none', len(ccv), [t['part'] for t in tomb if t['flag']], time.time() - t0))
    OUT['hard_failures'] = fails
    json.dump(OUT, open(HERE + '/adversary_%s.json' % args.tag, 'w'), indent=1, default=str)
    open(HERE + '/adversary_%s.log' % args.tag, 'w').write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
