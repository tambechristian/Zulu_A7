"""adv13.py -- adversarial DFM/DRC review of a series-R plan (emit_copper format + parts / renet_pads /
net_class_add / microvias), written for the D13-D15 review.

Independence: imports nothing from the series_r tool set (dfm_check, judge_check, geom, plan_check, d10/fold/check,
d10/verify/dfm_adversary, d13/combine/*).  Own choices:
  * one geometry primitive for everything: a convex polygon (1, 2 or 4 vertices) dilated by a radius ("rounded
    convex polygon"); distance = convex-polygon distance minus both radii (SAT-free: edge/edge + containment);
  * rules parsed from Rules6 in board_extract.json; scope expressions translated to Python predicates on the fly;
  * interpretation choices (via OnLayer, Width per-layer key map, hole-to-hole span semantics) are CALIBRATED on
    the unmodified board (which is Altium DRC 0); the semantics that make the baseline clean are used, and the
    alternatives are reported too;
  * after-board checked ALL PAIRS, baseline subtracted by object identity;
  * pours re-poured by distance-field raster (0.01 mm whole board; 0.0025 mm windows round every change);
  * connectivity by union-find over copper + pour islands; R bypass = SDRAM-Dn island containing a Dn object.
Usage: python adv13.py --plan PLAN --tag TAG   (writes adv13_<tag>.log/.json next to itself)
"""
import argparse, collections, hashlib, json, math, os, re, sys, time
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SR = os.path.normpath(os.path.join(HERE, '..', '..')).replace('\\', '/')
ap = argparse.ArgumentParser()
ap.add_argument('--plan', required=True)
ap.add_argument('--tag', required=True)
ap.add_argument('--board', default=SR + '/board_extract.json')
ap.add_argument('--res', type=float, default=0.01)
ap.add_argument('--wres', type=float, default=0.0025)
A = ap.parse_args()

BX = json.load(open(A.board))
PL = json.load(open(A.plan))
STACK = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
IDX = {l: i for i, l in enumerate(STACK)}
OUTER = ('Top', 'Bottom')
OUT = {'plan': A.plan, 'plan_md5': hashlib.md5(open(A.plan, 'rb').read()).hexdigest(),
       'board_md5': hashlib.md5(open(A.board, 'rb').read()).hexdigest(), 'tag': A.tag}
LOGL = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    LOGL.append(s)
    print(s, flush=True)


def lname(s):
    return {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'TopLayer': 'Top', 'BottomLayer': 'Bottom'}.get(s, s)


def to_mm(v):
    s = str(v).strip()
    if s.endswith('mil'):
        return float(s[:-3]) * 0.0254
    if s.endswith('mm'):
        return float(s[:-2])
    return float(s)


# ------------------------------------------------------------------------------------------------ geometry
# shape = (pts, r): pts a tuple of (x, y) forming a convex polygon (or a segment / a point), r >= 0 dilation

def d_pt_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    q = vx * vx + vy * vy
    if q == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * vx + (py - ay) * vy) / q
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def cross(ax, ay, bx, by, cx, cy):
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def segs_cross(a, b):
    (ax, ay), (bx, by) = a
    (cx, cy), (dx, dy) = b
    d1 = cross(cx, cy, dx, dy, ax, ay)
    d2 = cross(cx, cy, dx, dy, bx, by)
    d3 = cross(ax, ay, bx, by, cx, cy)
    d4 = cross(ax, ay, bx, by, dx, dy)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 != 0 and d2 != 0 and d3 != 0 and d4 != 0


def d_seg_seg(a, b):
    if segs_cross(a, b):
        return 0.0
    (ax, ay), (bx, by) = a
    (cx, cy), (dx, dy) = b
    return min(d_pt_seg(ax, ay, cx, cy, dx, dy), d_pt_seg(bx, by, cx, cy, dx, dy),
               d_pt_seg(cx, cy, ax, ay, bx, by), d_pt_seg(dx, dy, ax, ay, bx, by))


def edges(p):
    n = len(p)
    if n == 1:
        return [(p[0], p[0])]
    if n == 2:
        return [(p[0], p[1])]
    return [(p[i], p[(i + 1) % n]) for i in range(n)]


def inside_convex(pt, poly):
    if len(poly) < 3:
        return False
    s = 0
    x, y = pt
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        c = cross(ax, ay, bx, by, x, y)
        if c > 1e-15:
            if s < 0:
                return False
            s = 1
        elif c < -1e-15:
            if s > 0:
                return False
            s = -1
    return True


def poly_dist(p, q):
    if inside_convex(p[0], q) or inside_convex(q[0], p):
        return 0.0
    best = 1e9
    for e in edges(p):
        for f in edges(q):
            d = d_seg_seg(e, f)
            if d < best:
                best = d
                if d == 0.0:
                    return 0.0
    return best


def sgap(s, t):
    return poly_dist(s[0], t[0]) - s[1] - t[1]


def sbox(s):
    xs = [p[0] for p in s[0]]
    ys = [p[1] for p in s[0]]
    r = s[1]
    return (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)


def box_gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


def dilate(s, g):
    return (s[0], s[1] + g)


def rect_shape(x, y, w, h):
    return (((x - w / 2, y - h / 2), (x + w / 2, y - h / 2), (x + w / 2, y + h / 2), (x - w / 2, y + h / 2)), 0.0)


def pad_geom(x, y, w, h, shape):
    if shape == 'rect':
        return rect_shape(x, y, w, h)
    # round / oblong
    if abs(w - h) < 1e-9:
        return (((x, y),), w / 2)
    if w > h:
        return (((x - (w - h) / 2, y), (x + (w - h) / 2, y)), h / 2)
    return (((x, y - (h - w) / 2), (x, y + (h - w) / 2)), w / 2)


def seg_shape(x1, y1, x2, y2, w):
    return (((x1, y1), (x2, y2)), w / 2)


def circ(x, y, r):
    return (((x, y),), r)


def point_in_shape(x, y, s, tol=1e-6):
    return poly_dist(((x, y),), s[0]) <= s[1] + tol


# ------------------------------------------------------------------------------------------------ rules
RULES = collections.defaultdict(list)
for r in BX['rules']:
    if r.get('ENABLED', 'TRUE') == 'TRUE':
        RULES[r['RULEKIND']].append(r)
for k in RULES:
    RULES[k].sort(key=lambda r: int(r['PRIORITY']))
BASE_CLASSES = {k: set(v) for k, v in BX['net_classes'].items()}
POLYS = {}
for pg in BX['polygons']:
    L = 'L2-GND' if pg['net'] == 'GND' else 'L5-VCC3V3'
    POLYS[L] = pg

_tr_cache = {}


def scope_fn(expr):
    if expr in _tr_cache:
        return _tr_cache[expr]
    e = expr
    e = re.sub(r"\bInComponent\('([^']*)'\)", r"(o.comp=='\1')", e)
    e = re.sub(r"\bInNamedPolygon\('([^']*)'\)", r"(o.poly=='\1')", e)
    e = re.sub(r"\bInNetClass\('([^']*)'\)", r"(o.net in C.get('\1',()))", e)
    e = re.sub(r"\bInNet\('([^']*)'\)", r"(o.net=='\1')", e)
    e = re.sub(r"\bOnLayer\('([^']*)'\)", r"(o.onlayer(L,'\1'))", e)
    e = re.sub(r"\bIsThruVia\b", "(o.kind=='via' and o.vtype=='thru')", e)
    e = re.sub(r"\bIsMicroVia\b", "(o.kind=='via' and o.vtype=='micro')", e)
    e = re.sub(r"\bIsBuriedVia\b", "(o.kind=='via' and o.vtype=='buried')", e)
    e = re.sub(r"\bIsVia\b", "(o.kind=='via')", e)
    e = re.sub(r"\bIsPad\b", "(o.kind=='pad')", e)
    e = re.sub(r"\bAll\b", "True", e)
    e = re.sub(r"\bAnd\b", " and ", e)
    e = re.sub(r"\bOr\b", " or ", e)
    e = re.sub(r"\bNot\b", " not ", e)
    f = eval('lambda o, L, C: ' + e)
    _tr_cache[expr] = f
    return f


class Ctx:
    def __init__(s, classes, via_onlayer):
        s.C = classes
        s.via_onlayer = via_onlayer       # 'span' | 'never'
        s.cache = {}


class O:
    """copper object"""
    __slots__ = ('id', 'kind', 'net', 'comp', 'pad', 'poly', 'vtype', 'multi', 'shp', 'hole', 'x', 'y', 'span',
                 'new', 'src', 'layer', 'w', 'old_net', 'size', 'tag', 'ident')

    def __init__(s, **k):
        for a in s.__slots__:
            setattr(s, a, k.get(a))
        if s.shp is None:
            s.shp = {}

    def onlayer(s, L, name):
        if L is None:
            return False
        if s.kind == 'via':
            return CTX_ONL[0] == 'span' and L == name
        return L == name

    def nk(s):
        return s.net if s.net else '#nonet%d' % s.id

    def d(s):
        if s.kind == 'pad':
            return 'pad %s-%s[%s]' % (s.comp, s.pad, s.net or 'NoNet')
        if s.kind == 'via':
            return 'via %s (%.4f,%.4f) %s>%s %.2f/%.2f' % (s.net, s.x, s.y, s.span[0], s.span[-1], s.size, s.hole)
        t = s.src
        return 'track %s %s (%.4f,%.4f)-(%.4f,%.4f) w%.4f' % (s.layer, s.net, t['x1'], t['y1'], t['x2'], t['y2'], s.w)


CTX_ONL = ['span']


def sig(o):
    return (o.kind, o.net, o.comp, o.poly, o.vtype)


def clr_rule(a, b, L, ctx):
    key = (sig(a), sig(b), L, CTX_ONL[0])
    c = ctx.cache.get(key)
    if c is not None:
        return c
    res = (0.0, 'none')
    for r in RULES['Clearance']:
        f1, f2 = scope_fn(r['SCOPE1EXPRESSION']), scope_fn(r['SCOPE2EXPRESSION'])
        if r['NETSCOPE'] == 'DifferentNets' and a.net and a.net == b.net:
            continue
        if (f1(a, L, ctx.C) and f2(b, L, ctx.C)) or (f1(b, L, ctx.C) and f2(a, L, ctx.C)):
            res = (to_mm(r['GAP']), r['NAME'])
            break
    ctx.cache[key] = res
    return res


WMAP = {
    'MAP_A(L3=MID1,L4=MID2,L2=MID3,L5=MID4)': {'Top': 'TOPLAYER', 'Bottom': 'BOTTOMLAYER', 'L3-SIG': 'MIDLAYER1',
                                               'L4-SIG': 'MIDLAYER2', 'L2-GND': 'MIDLAYER3', 'L5-VCC3V3': 'MIDLAYER4'},
    'MAP_B(L2=MID1..L5=MID4)': {'Top': 'TOPLAYER', 'Bottom': 'BOTTOMLAYER', 'L2-GND': 'MIDLAYER1',
                                'L3-SIG': 'MIDLAYER2', 'L4-SIG': 'MIDLAYER3', 'L5-VCC3V3': 'MIDLAYER4'},
}


def width_lim(o, ctx, wmap):
    for r in RULES['Width']:
        if scope_fn(r['SCOPE1EXPRESSION'])(o, o.layer, ctx.C):
            k = wmap[o.layer]
            return to_mm(r.get(k + '_MINWIDTH', r['MINLIMIT'])), to_mm(r.get(k + '_MAXWIDTH', r['MAXLIMIT'])), r['NAME']
    return 0.0, 1e9, 'none'


def hole_lim(o, ctx):
    for r in RULES['HoleSize']:
        if scope_fn(r['SCOPE1EXPRESSION'])(o, None, ctx.C):
            return to_mm(r['MINLIMIT']), to_mm(r['MAXLIMIT']), r['NAME']
    return 0.0, 1e9, 'none'


def via_style(o, ctx):
    for r in RULES['RoutingVias']:
        if scope_fn(r['SCOPE1EXPRESSION'])(o, None, ctx.C):
            return to_mm(r['MINWIDTH']), to_mm(r['MAXWIDTH']), to_mm(r['MINHOLEWIDTH']), to_mm(r['MAXHOLEWIDTH']), r['NAME']
    return None


def mask_exp(o, side, ctx):
    """None = tented"""
    for r in RULES['SolderMaskExpansion']:
        if scope_fn(r['SCOPE1EXPRESSION'])(o, None, ctx.C):
            if o.kind == 'via':
                key = 'ISTENTINGTOP' if side == 'Top' else ('ISTENTINGBOTTOM' if r.get('USESEPARATEEXPANSIONS') == 'TRUE' else 'ISTENTINGTOP')
                if r.get(key, 'FALSE') == 'TRUE':
                    return None
            if side == 'Bottom' and r.get('USESEPARATEEXPANSIONS') == 'TRUE' and r.get('EXPANSIONBOTTOM'):
                return to_mm(r['EXPANSIONBOTTOM'])
            return to_mm(r['EXPANSION'])
    return 0.0


H2H = to_mm(RULES['HoleToHoleClearance'][0]['GAP'])
H2H_STACKED_OK = RULES['HoleToHoleClearance'][0].get('ALLOWSTACKEDMICROVIAS') == 'TRUE'
SLIVER = to_mm(RULES['MinimumSolderMaskSliver'][0]['MINSOLDERMASKWIDTH'])
SILK_MASK = to_mm(RULES['SilkToSolderMaskClearance'][0]['MINSILKSCREENTOMASKGAP'])
CCGAP = to_mm(RULES['ComponentClearance'][0]['GAP'])


# ------------------------------------------------------------------------------------------------ boards
def vtype(span):
    if span[0] == 'Top' and span[-1] == 'Bottom':
        return 'thru'
    if span[0] in OUTER or span[-1] in OUTER:
        return 'micro'
    if (span[0], span[-1]) == ('L3-SIG', 'L4-SIG'):
        return 'buried'
    return 'micro'      # L2>L3 / L4>L5 inner steps of the stacked HDI columns; typed microvia on this board


def mk_pad(p, objs, new=False, net=None, ident=None):
    shp = {}
    if p['layer'] == 'Multi':
        for L in STACK:
            if L == 'Top':
                w, h = p['w'], p['h']
            elif L == 'Bottom':
                w, h = (p.get('size_bot') or (p['w'], p['h']))
                if p['rot'] in (90.0, 270.0) and p.get('size_bot'):
                    w, h = h, w
            else:
                w, h = (p.get('size_mid') or (p['w'], p['h']))
                if p['rot'] in (90.0, 270.0) and p.get('size_mid'):
                    w, h = h, w
            shp[L] = pad_geom(p['x'], p['y'], w, h, p['shape'])
    else:
        shp[p['layer']] = pad_geom(p['x'], p['y'], p['w'], p['h'], p['shape'])
    o = O(id=len(objs), kind='pad', net=(net if net is not None else (p['net'] or '')), comp=p['ref'], pad=p['pad'],
          multi=p['layer'] == 'Multi', shp=shp, hole=p.get('hole') or 0.0, x=p['x'], y=p['y'], new=new, src=p,
          layer=p['layer'], ident=ident or ('pad', p['ref'], p['pad']))
    if o.multi:
        o.span = list(STACK)
    objs.append(o)
    return o


def mk_track(t, objs, new=False):
    L = lname(t['layer'])
    o = O(id=len(objs), kind='track', net=t['net'] or '', shp={L: seg_shape(t['x1'], t['y1'], t['x2'], t['y2'], t['w'])},
          layer=L, w=t['w'], new=new, src=t, comp=t.get('comp'),
          ident=('trk', L, t['net'] or '', round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4), round(t['w'], 4)))
    objs.append(o)
    return o


def mk_via(v, objs, new=False):
    if 'span' in v and len(v['span']) == 6:
        a, b = 0, 5
    elif 'span' in v:
        a, b = sorted((IDX[lname(v['span'][0])], IDX[lname(v['span'][-1])]))
    else:
        a, b = sorted((IDX[lname(v['from'])], IDX[lname(v['to'])]))
    span = STACK[a:b + 1]
    o = O(id=len(objs), kind='via', net=v['net'] or '', shp={L: circ(v['x'], v['y'], v['size'] / 2) for L in span},
          span=span, vtype=vtype(span), hole=v['hole'], size=v['size'], x=v['x'], y=v['y'], new=new, src=v,
          ident=('via', v['net'] or '', round(v['x'], 4), round(v['y'], 4), span[0], span[-1], round(v['hole'], 4)))
    objs.append(o)
    return o


def board_base():
    objs = []
    for p in BX['pads']:
        mk_pad(p, objs)
    for t in BX['tracks']:
        if t['layer'] in IDX and not t['keepout']:
            mk_track(t, objs)
    for v in BX['vias']:
        mk_via(v, objs)
    return objs


def near(a, b, tol=1.5e-4):
    return abs(a - b) <= tol


R0201_PAD = None
for p in BX['pads']:
    c = next((c for c in BX['components'] if c['ref'] == p['ref']), None)
    if c and c['footprint'] == 'R0201':
        R0201_PAD = (p['w'], p['h']) if c['rot'] in (0.0, 180.0) else (p['h'], p['w'])
        break


def pad1_offset(fp, side, rot):
    """learn pad-1 offset from the board's own parts of that footprint/side/rot"""
    offs = []
    for c in BX['components']:
        if c['footprint'] in (fp, fp.replace('R', 'C')) and c['side'] == side and int(c['rot']) % 360 == int(rot) % 360:
            p1 = next(p for p in BX['pads'] if p['ref'] == c['ref'] and p['pad'] == '1')
            offs.append((round(p1['x'] - c['x'], 3), round(p1['y'] - c['y'], 3)))
    if offs:
        return collections.Counter(offs)
    # none at this rotation: rotate the same side's convention from another rotation (CCW positive)
    for c in BX['components']:
        if c['footprint'] in (fp, fp.replace('R', 'C')) and c['side'] == side:
            p1 = next(p for p in BX['pads'] if p['ref'] == c['ref'] and p['pad'] == '1')
            dx, dy = p1['x'] - c['x'], p1['y'] - c['y']
            a = math.radians(rot - c['rot'])
            offs.append((round(dx * math.cos(a) - dy * math.sin(a), 3) + 0.0, round(dx * math.sin(a) + dy * math.cos(a), 3) + 0.0))
    return collections.Counter(offs)


def board_after(plan):
    errs = []
    base = board_base()
    alive = [True] * len(base)
    trk_index = collections.defaultdict(list)
    for o in base:
        if o.kind == 'track':
            trk_index[(o.layer, o.net)].append(o)
    for r in plan.get('remove', []):
        L = lname(r['layer'])
        hits = []
        for o in trk_index[(L, r['net'])]:
            if not alive[o.id] or not near(o.w, r['w'], 1e-4):
                continue
            t = o.src
            fwd = near(t['x1'], r['x1']) and near(t['y1'], r['y1']) and near(t['x2'], r['x2']) and near(t['y2'], r['y2'])
            rev = near(t['x1'], r['x2']) and near(t['y1'], r['y2']) and near(t['x2'], r['x1']) and near(t['y2'], r['y1'])
            if fwd or rev:
                hits.append(o)
        if len(hits) != 1:
            errs.append('remove track matched %d: %s' % (len(hits), r))
        for h in hits[:1]:
            alive[h.id] = False
    for r in plan.get('remove_vias', []):
        e0, e1 = lname(r['span'][0]), lname(r['span'][-1])
        hits = [o for o in base if o.kind == 'via' and alive[o.id] and o.net == r['net'] and near(o.x, r['x']) and
                near(o.y, r['y']) and near(o.hole, r['hole'], 1e-4) and o.span[0] == e0 and o.span[-1] == e1]
        if len(hits) != 1:
            errs.append('remove via matched %d: %s' % (len(hits), r))
        for h in hits[:1]:
            alive[h.id] = False
    ren = {(r['ref'], r['pad']): r['net'] for r in plan.get('renet_pads', [])}
    seen = set()
    objs = []
    for o in base:
        if not alive[o.id]:
            continue
        if o.kind == 'pad':
            k = (o.comp, o.pad)
            if k in ren:
                seen.add(k)
                n = mk_pad(o.src, objs, new=True, net=ren[k])
                n.old_net = o.net
            else:
                mk_pad(o.src, objs)
        elif o.kind == 'track':
            mk_track(o.src, objs)
        else:
            mk_via(o.src, objs)
    for k in ren:
        if k not in seen:
            errs.append('renet pad not found %s' % (k,))
    for t in plan.get('tracks', []):
        mk_track(t, objs, new=True).tag = t.get('why', 'new')
    for v in plan.get('vias', []):
        mk_via(v, objs, new=True).tag = v.get('why', 'new')
    pw, ph = R0201_PAD
    for part in plan.get('parts', []):
        for pn in ('1', '2'):
            q = part['pad' + pn]
            w, h = (pw, ph) if int(part['rot']) % 180 == 0 else (ph, pw)
            mk_pad(dict(ref=part['ref'], pad=pn, layer=part['side'], net=q['net'], x=q['x'], y=q['y'], w=w, h=h,
                        shape='rect', hole=0.0, rot=part['rot']), objs, new=True, net=q['net'])
    return objs, errs, base, alive


# ------------------------------------------------------------------------------------------------ pair scan
def grid_pairs(objs, reach):
    cell = 0.4
    g = collections.defaultdict(list)
    for o in objs:
        for L, s in o.shp.items():
            b = sbox(s)
            for i in range(int(math.floor((b[0] - reach) / cell)), int(math.floor((b[2] + reach) / cell)) + 1):
                for j in range(int(math.floor((b[1] - reach) / cell)), int(math.floor((b[3] + reach) / cell)) + 1):
                    g[(L, i, j)].append(o.id)
    done = set()
    for (L, i, j), ids in g.items():
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                p, q = ids[a], ids[b]
                if p > q:
                    p, q = q, p
                k = (L, p, q)
                if k in done:
                    continue
                done.add(k)
                yield L, p, q


def same_object(a, b):
    return a.kind == 'pad' and b.kind == 'pad' and a.comp == b.comp and a.pad == b.pad


def clearance_scan(objs, ctx, report_margin=0.012):
    viol, shorts, tight = [], [], []
    for L, i, j in grid_pairs(objs, 0.3):
        a, b = objs[i], objs[j]
        if a.nk() == b.nk() or same_object(a, b):
            continue
        sa, sb = a.shp[L], b.shp[L]
        if box_gap(sbox(sa), sbox(sb)) > 0.25:
            continue
        g = sgap(sa, sb)
        req, rn = clr_rule(a, b, L, ctx)
        rec = dict(layer=L, a=a.d(), b=b.d(), gap=round(g, 5), req=round(req, 5), margin=round(g - req, 5), rule=rn,
                   new=bool(a.new or b.new), key=tuple(sorted((a.ident, b.ident))) + (L,))
        if g <= 1e-9:
            shorts.append(rec)
        elif g < req - 1e-7:
            viol.append(rec)
        elif g < req + report_margin and (a.new or b.new):
            tight.append(rec)
    return viol, shorts, tight


# ------------------------------------------------------------------------------------------------ holes
def hole_list(objs):
    hs = []
    for o in objs:
        if o.kind == 'via':
            hs.append(o)
        elif o.kind == 'pad' and o.multi and o.hole and o.hole > 0:
            hs.append(o)
    return hs


def hole_scan(objs, mode):
    """mode: 'any' (all hole pairs) | 'shared_layer' (spans share a layer) | 'overlap_dielectric' (spans share a
    dielectric, i.e. >= 2 common layers)"""
    hs = hole_list(objs)
    g = collections.defaultdict(list)
    for h in hs:
        g[(int(h.x / 0.6), int(h.y / 0.6))].append(h)
    out, worst_new = [], []
    seen = set()
    for h in hs:
        ci, cj = int(h.x / 0.6), int(h.y / 0.6)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for k in g.get((ci + di, cj + dj), []):
                    if k.id <= h.id or (h.id, k.id) in seen:
                        continue
                    seen.add((h.id, k.id))
                    d = math.hypot(h.x - k.x, h.y - k.y)
                    e = d - h.hole / 2 - k.hole / 2
                    if e > H2H + 0.05:
                        continue
                    common = set(h.span) & set(k.span)
                    if mode == 'shared_layer' and not common:
                        continue
                    if mode == 'overlap_dielectric' and len(common) < 2:
                        continue
                    stacked = d < 1e-4 and h.kind == 'via' and k.kind == 'via' and len(common) <= 1 and \
                        h.vtype != 'thru' and k.vtype != 'thru'
                    if stacked and H2H_STACKED_OK:
                        continue
                    rec = dict(a=h.d(), b=k.d(), edge=round(e, 5), req=H2H, common=sorted(common, key=IDX.get),
                               new=bool(h.new or k.new), key=tuple(sorted((h.ident, k.ident))))
                    if e < H2H - 1e-7:
                        out.append(rec)
                    elif h.new or k.new:
                        worst_new.append(rec)
    worst_new.sort(key=lambda r: r['edge'])
    return out, worst_new


# ------------------------------------------------------------------------------------------------ mask / silk
def mask_openings(objs, ctx):
    ops = []
    for o in objs:
        for side in OUTER:
            if side not in o.shp:
                continue
            if o.kind == 'track':
                continue
            e = mask_exp(o, side, ctx)
            if e is None:
                continue
            ops.append((o, side, dilate(o.shp[side], e), e))
    return ops


def mask_scan(objs, ctx):
    ops = mask_openings(objs, ctx)
    g = collections.defaultdict(list)
    for k, (o, side, s, e) in enumerate(ops):
        b = sbox(s)
        for i in range(int(b[0] / 0.4) - 1, int(b[2] / 0.4) + 2):
            for j in range(int(b[1] / 0.4) - 1, int(b[3] / 0.4) + 2):
                g[(side, i, j)].append(k)
    seen = set()
    sliv, webs_new = [], []
    for key, ks in g.items():
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                p, q = sorted((ks[a], ks[b]))
                if (p, q) in seen:
                    continue
                seen.add((p, q))
                oa, sa, ga, _ = ops[p]
                ob, sb, gb, _ = ops[q]
                if sa != sb or oa.id == ob.id:
                    continue
                if box_gap(sbox(ga), sbox(gb)) > SLIVER + 0.05:
                    continue
                w = sgap(ga, gb)
                rec = dict(side=sa, a=oa.d(), b=ob.d(), web=round(w, 5), new=bool(oa.new or ob.new),
                           key=tuple(sorted((oa.ident, ob.ident))) + (sa,))
                if 1e-7 < w < SLIVER - 1e-7:
                    sliv.append(rec)
                elif (oa.new or ob.new) and w < SLIVER + 0.05:
                    webs_new.append(rec)
    # foreign copper inside / near a pad opening
    cu = [o for o in objs if o.kind in ('track', 'via')]
    gc = collections.defaultdict(list)
    for o in cu:
        for side in OUTER:
            if side in o.shp:
                b = sbox(o.shp[side])
                for i in range(int(b[0] / 0.4) - 1, int(b[2] / 0.4) + 2):
                    for j in range(int(b[1] / 0.4) - 1, int(b[3] / 0.4) + 2):
                        gc[(side, i, j)].append(o)
    expo = []
    for (o, side, s, e) in ops:
        if o.kind != 'pad':
            continue
        b = sbox(s)
        cand = {}
        for i in range(int(b[0] / 0.4) - 1, int(b[2] / 0.4) + 2):
            for j in range(int(b[1] / 0.4) - 1, int(b[3] / 0.4) + 2):
                for t in gc.get((side, i, j), []):
                    cand[t.id] = t
        for t in cand.values():
            if t.nk() == o.nk():
                continue
            c = sgap(s, t.shp[side])
            if c < 0.05:
                expo.append(dict(side=side, opening=o.d(), copper=t.d(), mask_cover=round(c, 5), exposed=c <= 0,
                                 new=bool(o.new or t.new), key=tuple(sorted((o.ident, t.ident))) + (side,)))
    return sliv, webs_new, expo, ops


def text_boxes():
    out = []
    for t in BX['texts']:
        if t['layer'] not in ('TopOverlay', 'BottomOverlay') or t['hidden']:
            continue
        h = t['height']
        sw = t.get('stroke') or 0.15
        n = max(1, len(t['text']))
        for label, adv in (('nominal', 0.667), ('conservative', 1.0)):
            w = n * h * adv
            rot = int(round(t['rot'])) % 360
            mir = bool(t.get('mirror'))
            x, y = t['x'], t['y']
            dx = -w if mir else w
            if rot == 0:
                bx = (min(x, x + dx), y, max(x, x + dx), y + h)
            elif rot == 90:
                bx = (x - h, min(y, y + w), x, max(y, y + w))
            elif rot == 180:
                bx = (min(x, x - dx), y - h, max(x, x - dx), y)
            else:
                bx = (x, min(y, y - w), x + h, max(y, y - w))
            bx = (bx[0] - sw / 2, bx[1] - sw / 2, bx[2] + sw / 2, bx[3] + sw / 2)
            out.append((t, 'Top' if t['layer'] == 'TopOverlay' else 'Bottom', label,
                        rect_shape((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, bx[2] - bx[0], bx[3] - bx[1])))
    return out


def silk_scan(ops):
    res = []
    for (t, side, label, s) in text_boxes():
        for (o, s2, sh, e) in ops:
            if s2 != side or o.kind != 'pad':
                continue
            if box_gap(sbox(s), sbox(sh)) > SILK_MASK + 0.1:
                continue
            g = sgap(s, sh)
            if g < SILK_MASK - 1e-7:
                res.append(dict(text=t['text'], comp=t['comp'], side=side, estimate=label, opening=o.d(),
                                gap=round(g, 4), req=round(SILK_MASK, 4), new=bool(o.new),
                                key=(t['comp'], t['text'], o.ident, label)))
    return res


# ------------------------------------------------------------------------------------------------ pours
def distance_to_shape(X, Y, s):
    pts, r = s
    if len(pts) == 1:
        d = np.hypot(X - pts[0][0], Y - pts[0][1])
    else:
        d = None
        for (a, b) in edges(pts):
            vx, vy = b[0] - a[0], b[1] - a[1]
            q = vx * vx + vy * vy
            if q == 0:
                dd = np.hypot(X - a[0], Y - a[1])
            else:
                t = np.clip(((X - a[0]) * vx + (Y - a[1]) * vy) / q, 0, 1)
                dd = np.hypot(X - a[0] - t * vx, Y - a[1] - t * vy)
            d = dd if d is None else np.minimum(d, dd)
        if len(pts) >= 3:
            ins = np.ones(X.shape, bool)
            sgn = None
            n = len(pts)
            cs = []
            for i in range(n):
                a, b = pts[i], pts[(i + 1) % n]
                cs.append((b[0] - a[0]) * (Y - a[1]) - (b[1] - a[1]) * (X - a[0]))
            allp = np.all([c >= 0 for c in cs], axis=0)
            alln = np.all([c <= 0 for c in cs], axis=0)
            d = np.where(allp | alln, 0.0, d)
    return d - r


def paint(arr, x0, y0, res, s, grow):
    b = sbox(s)
    ny, nx = arr.shape
    i0 = max(0, int((b[0] - grow - x0) / res) - 1)
    i1 = min(nx, int((b[2] + grow - x0) / res) + 2)
    j0 = max(0, int((b[1] - grow - y0) / res) - 1)
    j1 = min(ny, int((b[3] + grow - y0) / res) + 2)
    if i0 >= i1 or j0 >= j1:
        return
    X = x0 + (np.arange(i0, i1) + 0.5) * res
    Y = y0 + (np.arange(j0, j1) + 0.5) * res
    XX, YY = np.meshgrid(X, Y)
    arr[j0:j1, i0:i1] |= distance_to_shape(XX, YY, s) <= grow


def pour(objs, L, ctx, win=None, res=None):
    pg = POLYS[L]
    res = res or A.res
    ox = [p[0] for p in pg['outline']]
    oy = [p[1] for p in pg['outline']]
    if win is None:
        win = (min(ox), min(oy), max(ox), max(oy))
    x0, y0, x1, y1 = win
    nx, ny = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    X = x0 + (np.arange(nx) + 0.5) * res
    Y = y0 + (np.arange(ny) + 0.5) * res
    inside = (X[None, :] >= min(ox)) & (X[None, :] <= max(ox)) & (Y[:, None] >= min(oy)) & (Y[:, None] <= max(oy))
    void = np.zeros((ny, nx), bool)
    same = np.zeros((ny, nx), bool)
    po = O(id=-1, kind='poly', net=pg['net'], poly=pg['name'])
    for o in objs:
        s = o.shp.get(L)
        if s is None:
            continue
        b = sbox(s)
        if b[2] < x0 - 0.4 or b[0] > x1 + 0.4 or b[3] < y0 - 0.4 or b[1] > y1 + 0.4:
            continue
        if o.net == pg['net']:
            paint(same, x0, y0, res, s, 0.0)
        else:
            g, _ = clr_rule(po, o, L, ctx)
            paint(void, x0, y0, res, s, g)
    cu = (inside & ~void) | same
    lab, n = ndimage.label(cu)
    live_ids = np.unique(lab[same & (lab > 0)])
    kept = np.isin(lab, live_ids) & (lab > 0)
    return dict(lab=lab, n=n, live=live_ids, kept=kept, same=same, void=void, cu=cu, win=win, res=res)


def disk(rpx):
    yy, xx = np.mgrid[-rpx:rpx + 1, -rpx:rpx + 1]
    return (xx * xx + yy * yy) <= rpx * rpx + 1e-9


# ------------------------------------------------------------------------------------------------ connectivity
class UF:
    def __init__(s):
        s.p = {}

    def f(s, a):
        s.p.setdefault(a, a)
        r = a
        while s.p[r] != r:
            r = s.p[r]
        while s.p[a] != r:
            s.p[a], a = r, s.p[a]
        return r

    def u(s, a, b):
        a, b = s.f(a), s.f(b)
        if a != b:
            s.p[a] = b


def connect(objs, pours):
    uf = UF()
    for o in objs:
        uf.f(o.id)
    for L, i, j in grid_pairs(objs, 0.01):
        a, b = objs[i], objs[j]
        if not a.net or a.net != b.net:
            continue
        if box_gap(sbox(a.shp[L]), sbox(b.shp[L])) > 1e-6:
            continue
        if sgap(a.shp[L], b.shp[L]) <= 1e-6:
            uf.u(i, j)
    for L, pr in pours.items():
        net = POLYS[L]['net']
        x0, y0 = pr['win'][0], pr['win'][1]
        res = pr['res']
        for o in objs:
            if o.net != net or L not in o.shp:
                continue
            s = o.shp[L]
            px, py = s[0][0] if len(s[0]) <= 2 else (sum(p[0] for p in s[0]) / 4, sum(p[1] for p in s[0]) / 4)
            i, j = int((px - x0) / res), int((py - y0) / res)
            if 0 <= j < pr['lab'].shape[0] and 0 <= i < pr['lab'].shape[1] and pr['kept'][j, i]:
                uf.u(o.id, ('pour', L, int(pr['lab'][j, i])))
    return uf


# ------------------------------------------------------------------------------------------------ main
def main():
    t0 = time.time()
    say('adv13.py  plan=%s  tag=%s' % (A.plan, A.tag))
    say('plan md5 %s   board_extract md5 %s   PcbDoc md5 (extract) %s   plan made against %s' % (
        OUT['plan_md5'], OUT['board_md5'], BX['source']['pcbdoc_md5'], PL.get('source', {}).get('pcbdoc_md5')))
    findings = []    # hard violations (would fail Altium batch DRC or fab)
    advis = []       # advisory items

    def hard(cat, msg, **k):
        findings.append(dict(cat=cat, msg=msg, **k))
        say('  !! HARD [%s] %s' % (cat, msg))

    def adv(cat, msg, **k):
        advis.append(dict(cat=cat, msg=msg, **k))
        say('  -- ADVISORY [%s] %s' % (cat, msg))

    classes_after = {k: set(v) for k, v in BASE_CLASSES.items()}
    for k, v in (PL.get('net_class_add') or {}).items():
        classes_after.setdefault(k, set()).update(v)

    base = board_base()
    after, errs, _, _ = board_after(PL)
    say('\n== 0. apply: %d errors; after-board %d objects (base %d), new/renamed objects %d' % (
        len(errs), len(after), len(base), sum(1 for o in after if o.new)))
    for e in errs:
        hard('apply', e)

    # ---------------------------------------------------------------- 0b. plan self-consistency
    say('\n== 0b. plan self-consistency')
    comps = {c['ref']: c for c in BX['components']}
    for part in PL.get('parts', []):
        if part['ref'] in comps:
            hard('designator', '%s already exists on the board' % part['ref'])
        offs = pad1_offset(part['footprint'], part['side'], part['rot'])
        exp = offs.most_common(1)[0][0] if offs else None
        got = (round(part['pad1']['x'] - part['x'], 3), round(part['pad1']['y'] - part['y'], 3))
        got2 = (round(part['pad2']['x'] - part['x'], 3), round(part['pad2']['y'] - part['y'], 3))
        ok = exp is not None and near(got[0], exp[0], 2e-3) and near(got[1], exp[1], 2e-3) and \
            near(got2[0], -exp[0], 2e-3) and near(got2[1], -exp[1], 2e-3)
        say('   %s %s rot %s: pad1 offset %s, board convention %s (n=%d) -> %s' % (
            part['ref'], part['side'], part['rot'], got, exp, sum(offs.values()), 'OK' if ok else 'MISMATCH'))
        if not ok:
            hard('pad1-orientation', '%s pad-1 offset %s vs board convention %s' % (part['ref'], got, exp))
        bit = part.get('net_bit')
        if part['pad1']['net'] != 'SDRAM-D%d' % bit or part['pad2']['net'] != 'D%d' % bit:
            hard('part-nets', '%s nets %s/%s' % (part['ref'], part['pad1']['net'], part['pad2']['net']))
    # renet: old net must be Dn, the TSOP pin must be DQn
    tsop_dq = {2: 0, 4: 1, 5: 2, 7: 3, 8: 4, 10: 5, 11: 6, 13: 7, 42: 8, 44: 9, 45: 10, 47: 11, 48: 12, 50: 13, 51: 14, 53: 15}
    for r in PL.get('renet_pads', []):
        p = next((p for p in BX['pads'] if p['ref'] == r['ref'] and p['pad'] == r['pad']), None)
        n = int(r['net'].split('D')[-1])
        ok = p is not None and p['net'] == 'D%d' % n and tsop_dq.get(int(r['pad'])) == n
        if not ok:
            hard('renet', '%s-%s -> %s (old net %s)' % (r['ref'], r['pad'], r['net'], p and p['net']))
    say('   renet_pads: %d, all old-net Dn / TSOP-54 DQn pin map checked' % len(PL.get('renet_pads', [])))
    sdn = sorted({r['net'] for r in PL.get('renet_pads', [])} | {p['pad1']['net'] for p in PL.get('parts', [])},
                 key=lambda s: int(s.split('D')[-1]))
    for n in sdn:
        if n not in classes_after.get('SDRAM_DATA', set()):
            hard('netclass', '%s not in SDRAM_DATA after net_class_add' % n)
        dn = n.replace('SDRAM-', '')
        if dn not in classes_after.get('SDRAM_DATA', set()):
            hard('netclass', '%s not in SDRAM_DATA' % dn)
    say('   net-class membership: %s' % ', '.join('%s:%s' % (n, n in classes_after['SDRAM_DATA']) for n in sdn))
    # microvia typing list vs new non-through vias
    newv = [o for o in after if o.kind == 'via' and o.new and o.tag != 'rename']
    typed = PL.get('microvias', [])
    missing = []
    for o in newv:
        if o.vtype == 'thru':
            continue
        m = [m for m in typed if near(m['x'], o.x, 1e-6) and near(m['y'], o.y, 1e-6) and m['net'] == o.net and
             {lname(m['from']), lname(m['to'])} == {o.span[0], o.span[-1]}]
        if len(m) != 1:
            missing.append(o.d())
        else:
            want = 'buried' if o.vtype == 'buried' else 'microvia'
            if not m[0]['type'].startswith(want):
                hard('via-typing', '%s typed "%s" but span says %s' % (o.d(), m[0]['type'], o.vtype))
    extra = [m for m in typed if not any(near(m['x'], o.x, 1e-6) and near(m['y'], o.y, 1e-6) and m['net'] == o.net
                                         for o in newv)]
    say('   new vias (not renames) %d: thru %d, micro %d, buried %d; typing list %d; missing from list %d; orphan entries %d' % (
        len(newv), sum(o.vtype == 'thru' for o in newv), sum(o.vtype == 'micro' for o in newv),
        sum(o.vtype == 'buried' for o in newv), len(typed), len(missing), len(extra)))
    for m in missing:
        hard('via-typing', 'new non-through via not in the microvia typing list: %s' % m)
    for m in extra:
        hard('via-typing', 'typing entry with no via: %s' % m)

    # ---------------------------------------------------------------- 1. calibration of interpretations on baseline
    say('\n== 1. calibration on the unmodified board (Altium DRC 0)')
    calib = {}
    ctx_b = Ctx(BASE_CLASSES, 'span')
    for mode in ('span', 'never'):
        CTX_ONL[0] = mode
        ctx_b.cache = {}
        v, s, _ = clearance_scan(base, ctx_b)
        calib['clearance_via_onlayer_' + mode] = (len(v), len(s))
        say('   clearance, via OnLayer=%-5s: %d violations, %d shorts' % (mode, len(v), len(s)))
        for r in v[:4]:
            say('      e.g.', r['layer'], r['a'], '|', r['b'], r['gap'], '<', r['req'], r['rule'])
    best_onl = min(('span', 'never'), key=lambda m: sum(calib['clearance_via_onlayer_' + m]))
    CTX_ONL[0] = best_onl
    say('   -> via OnLayer semantics used: %s (the other is reported for information)' % best_onl)
    for name, wm in WMAP.items():
        n = 0
        for o in base:
            if o.kind == 'track':
                lo, hi, rn = width_lim(o, ctx_b, wm)
                if o.w < lo - 3e-6 or o.w > hi + 3e-6:
                    n += 1
        calib['width_' + name] = n
        say('   width map %s: %d baseline violations' % (name, n))
    wsel = min(WMAP, key=lambda k: calib['width_' + k])
    say('   -> width map used: %s' % wsel)
    for mode in ('any', 'shared_layer', 'overlap_dielectric'):
        hv, _ = hole_scan(base, mode)
        calib['h2h_' + mode] = len(hv)
        say('   hole-to-hole %-18s: %d baseline violations' % (mode, len(hv)))
        for r in hv[:3]:
            say('      e.g.', r['a'], '|', r['b'], r['edge'], r['common'])
    hsel = min(('any', 'shared_layer', 'overlap_dielectric'), key=lambda m: (calib['h2h_' + m], ['any', 'shared_layer', 'overlap_dielectric'].index(m)))
    say('   -> hole-to-hole semantics used: %s (strictest with the fewest baseline hits)' % hsel)
    sl_b, _, ex_b, ops_b = mask_scan(base, ctx_b)
    calib['mask_sliver_baseline'] = len(sl_b)
    say('   mask slivers on baseline: %d' % len(sl_b))
    for r in sl_b[:5]:
        say('      e.g.', r['side'], r['a'], '|', r['b'], r['web'])
    silk_b = silk_scan(ops_b)
    calib['silk_baseline'] = collections.Counter(r['estimate'] for r in silk_b)
    say('   silk-to-mask on baseline: %s' % dict(calib['silk_baseline']))
    OUT['calibration'] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in calib.items()}

    # ---------------------------------------------------------------- 2. clearance / shorts all pairs
    ctx_a = Ctx(classes_after, best_onl)
    say('\n== 2. copper clearance, all pairs of the after-board (rules from Rules6, via OnLayer=%s)' % best_onl)
    vb, sb, _ = clearance_scan(base, ctx_b)
    va, sa, tight = clearance_scan(after, ctx_a)
    bkeys = {r['key'] for r in vb} | {r['key'] for r in sb}
    nv = [r for r in va if r['key'] not in bkeys]
    ns = [r for r in sa if r['key'] not in bkeys]
    say('   baseline: %d violations %d shorts | after: %d violations %d shorts | NEW: %d violations %d shorts' % (
        len(vb), len(sb), len(va), len(sa), len(nv), len(ns)))
    for r in nv:
        hard('clearance', '%s %s | %s gap %.5f < %.4f (%s)' % (r['layer'], r['a'], r['b'], r['gap'], r['req'], r['rule']))
    for r in ns:
        hard('short', '%s %s | %s gap %.5f' % (r['layer'], r['a'], r['b'], r['gap']))
    tight.sort(key=lambda r: r['margin'])
    say('   tightest pairs involving a new/renamed object (margin < 0.012 mm): %d' % len(tight))
    for r in tight[:40]:
        say('     %+.5f  %-9s %s | %s  (gap %.5f, %s)' % (r['margin'], r['layer'], r['a'], r['b'], r['gap'], r['rule']))
    OUT['clearance'] = dict(baseline=[len(vb), len(sb)], after=[len(va), len(sa)], new_viol=nv, new_shorts=ns,
                            tight=[{k: v for k, v in r.items() if k != 'key'} for r in tight[:80]])
    for r in tight:
        if r['margin'] < 0.00254:
            adv('sub-2.54um-margin', '%s %s | %s margin %+.5f (%s); Altium rounds to 2.54 um' % (
                r['layer'], r['a'], r['b'], r['margin'], r['rule']))

    # rule coverage spot check: which rule applies to each new SDRAM-Dn/Dn object on L3/L4
    say('   rule resolution for new SDRAM objects on L3/L4 (vs an unrelated net):')
    dummy = O(id=-9, kind='track', net='__other__')
    seen_r = set()
    for o in after:
        if o.new and o.net and ('D1' in o.net or 'D' in o.net) and o.net.replace('SDRAM-', '').startswith('D'):
            for L in o.shp:
                if L in ('L3-SIG', 'L4-SIG'):
                    k = (o.net, o.kind, L)
                    if k in seen_r:
                        continue
                    seen_r.add(k)
                    g, rn = clr_rule(o, dummy, L, ctx_a)
                    if rn != 'Clearance_SDRAM_INNER':
                        hard('rule-coverage', '%s %s on %s resolves to %s (%.3f), not Clearance_SDRAM_INNER' % (o.kind, o.net, L, rn, g))
    say('     %d (net, kind, layer) combos checked' % len(seen_r))

    # ---------------------------------------------------------------- 3. holes
    say('\n== 3. hole-to-hole (%.4f, semantics %s; stacked microvias exempt=%s)' % (H2H, hsel, H2H_STACKED_OK))
    hb, _ = hole_scan(base, hsel)
    ha, hw = hole_scan(after, hsel)
    hk = {r['key'] for r in hb}
    hn = [r for r in ha if r['key'] not in hk]
    say('   baseline %d, after %d, NEW %d' % (len(hb), len(ha), len(hn)))
    for r in hn:
        hard('hole-to-hole', '%s | %s edge %.4f < %.4f' % (r['a'], r['b'], r['edge'], r['req']))
    # also run the strictest semantics for information on the new objects
    hany, _ = hole_scan(after, 'any')
    hany_base = {x['key'] for x in hole_scan(base, 'any')[0]}
    hany_new = [r for r in hany if r['new'] and r['key'] not in hany_base]
    say('   for information, "any span" semantics NEW hits: %d' % len(hany_new))
    for r in hany_new:
        say('     ', r['a'], '|', r['b'], r['edge'], r['common'])
    say('   tightest new-hole pairs:')
    for r in hw[:12]:
        say('     edge %.4f  %s | %s  common %s' % (r['edge'], r['a'], r['b'], r['common']))
    OUT['holes'] = dict(semantics=hsel, new=hn, any_span_new=hany_new, tightest=[{k: v for k, v in r.items() if k != 'key'} for r in hw[:20]])

    say('   projected hole overlap across the core (different nets, no shared layer, edge < 0):')

    def proj(objs):
        out = {}
        hs = [h for h in hole_list(objs) if h.kind == 'via']
        g = collections.defaultdict(list)
        for h in hs:
            g[(int(h.x / 0.5), int(h.y / 0.5))].append(h)
        for h in hs:
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    for k in g.get((int(h.x / 0.5) + di, int(h.y / 0.5) + dj), []):
                        if k.id <= h.id or h.net == k.net or set(h.span) & set(k.span):
                            continue
                        e = math.hypot(h.x - k.x, h.y - k.y) - h.hole / 2 - k.hole / 2
                        if e < 0:
                            key = tuple(sorted(((h.net, round(h.x, 4), round(h.y, 4)), (k.net, round(k.x, 4), round(k.y, 4)))))
                            out[key] = min(out.get(key, 9), e)
        return out
    pj_b, pj_a = proj(base), proj(after)
    pj_new = {k: v for k, v in pj_a.items() if k not in pj_b}
    say('     baseline %d site pairs (worst edge %.4f), after %d, NEW %d' % (
        len(pj_b), min(pj_b.values(), default=0), len(pj_a), len(pj_new)))
    for k, v in sorted(pj_new.items(), key=lambda kv: kv[1]):
        say('     NEW %s | %s  projected edge %.4f' % (k[0], k[1], v))
        adv('projected-hole-overlap', 'opposite-side microvia stacks of different nets overlap in projection: %s | %s edge %.4f '
            '(no shared layer, so not an Altium hole-to-hole hit; baseline has %d such pairs, worst %.4f)' % (
                k[0], k[1], v, len(pj_b), min(pj_b.values(), default=0)))
    OUT['projected_overlap'] = dict(baseline=len(pj_b), baseline_worst=min(pj_b.values(), default=0),
                                    new={'%s|%s' % k: v for k, v in pj_new.items()})

    # ---------------------------------------------------------------- 4. via types / hole size / via style
    say('\n== 4. via typing, HoleSize, RoutingVias for every new via (renames included)')
    vt = []
    for o in after:
        if o.kind != 'via' or not o.new:
            continue
        lo, hi, rn = hole_lim(o, ctx_a)
        vs = via_style(o, ctx_a)
        ok_h = lo - 1e-6 <= o.hole <= hi + 1e-6
        ok_s = vs is None or (vs[0] - 1e-6 <= o.size <= vs[1] + 1e-6 and vs[2] - 1e-6 <= o.hole <= vs[3] + 1e-6)
        # untyped fallback (what Altium does if the via type is not set)
        untyped = O(id=-2, kind='via', net=o.net, vtype=('thru' if o.vtype == 'thru' else ('buried' if o.span[0] not in OUTER and o.span[-1] not in OUTER else 'none')))
        ulo, uhi, urn = hole_lim(untyped, ctx_a)
        u_ok = ulo - 1e-6 <= o.hole <= uhi + 1e-6
        vt.append(dict(via=o.d(), type=o.vtype, holesize_rule=rn, ok=ok_h, style=vs and vs[4], style_ok=ok_s,
                       untyped_rule=urn, untyped_ok=u_ok, why=o.tag))
        if not ok_h:
            hard('holesize', '%s hole %.3f outside %s [%.3f, %.3f]' % (o.d(), o.hole, rn, lo, hi))
        if not ok_s:
            adv('via-style', '%s does not match %s (routing rule, not batch DRC)' % (o.d(), vs and vs[4]))
        if o.tag != 'rename':
            say('   %-60s %-6s %-15s ok=%s style=%s ok=%s | if left untyped: %s ok=%s' % (
                o.d(), o.vtype, rn, ok_h, vs and vs[4], ok_s, urn, u_ok))
    OUT['via_types'] = vt

    # ---------------------------------------------------------------- 5. widths
    say('\n== 5. width rules (map %s) on every track of the after-board' % wsel)
    wv = []
    wnew = []
    for o in after:
        if o.kind != 'track':
            continue
        lo, hi, rn = width_lim(o, ctx_a, WMAP[wsel])
        bad = o.w < lo - 3e-6 or o.w > hi + 3e-6     # Altium resolution 0.0001 mil = 2.54e-6 mm
        if bad:
            wv.append(dict(track=o.d(), w=o.w, lo=lo, hi=hi, rule=rn, new=o.new))
        if o.new:
            wnew.append((round(o.w - lo, 5), o.d(), rn, round(lo, 5), round(hi, 5)))
    wb = []
    for o in base:
        if o.kind == 'track':
            lo, hi, rn = width_lim(o, ctx_b, WMAP[wsel])
            if o.w < lo - 3e-6 or o.w > hi + 3e-6:
                wb.append('%s rule %s [%.4f, %.4f]' % (o.d(), rn, lo, hi))
    say('   baseline violations %d, after %d (new objects %d)' % (len(wb), len(wv), sum(r['new'] for r in wv)))
    for d in wb[:25]:
        say('      baseline:', d)
    for r in wv:
        if r['new']:
            hard('width', '%s w %.4f outside %s [%.4f, %.4f]' % (r['track'], r['w'], r['rule'], r['lo'], r['hi']))
    wnew.sort()
    say('   tightest new-track widths vs min (margin, track, rule, min, max):')
    for r in wnew[:10]:
        say('     %+.5f %s %s [%.4f, %.4f]' % r)
    # SDRAM-Dn width rule must be Width_SDRAM
    for o in after:
        if o.kind == 'track' and o.new and o.net.startswith('SDRAM-D'):
            lo, hi, rn = width_lim(o, ctx_a, WMAP[wsel])
            if rn != 'Width_SDRAM':
                hard('rule-coverage', '%s resolves to width rule %s' % (o.d(), rn))
    OUT['width'] = dict(viol=wv, tightest=wnew[:20])

    # ---------------------------------------------------------------- 6. mask
    say('\n== 6. solder mask (sliver %.4f; vias tented per rule; U1 0 / X3 %.4f / default %.4f expansion)' % (
        SLIVER, to_mm(next(r for r in RULES['SolderMaskExpansion'] if r['NAME'] == 'SolderMaskExpansion_X3')['EXPANSION']),
        to_mm(next(r for r in RULES['SolderMaskExpansion'] if r['NAME'] == 'SolderMaskExpansion')['EXPANSION'])))
    sl_a, webs, ex_a, ops_a = mask_scan(after, ctx_a)
    sk = {r['key'] for r in sl_b}
    sn = [r for r in sl_a if r['key'] not in sk]
    say('   slivers baseline %d after %d NEW %d' % (len(sl_b), len(sl_a), len(sn)))
    for r in sn:
        hard('mask-sliver', '%s %s | %s web %.5f < %.4f' % (r['side'], r['a'], r['b'], r['web'], SLIVER))
    webs.sort(key=lambda r: r['web'])
    say('   narrowest legal webs involving a new opening:')
    for r in webs[:10]:
        say('     web %.5f %s %s | %s' % (r['web'], r['side'], r['a'], r['b']))
    ek = {r['key'] for r in ex_b}
    en = [r for r in ex_a if r['key'] not in ek]
    en.sort(key=lambda r: r['mask_cover'])
    say('   foreign copper under < 0.05 mm of mask next to a pad opening: baseline %d, after %d, NEW %d' % (
        len(ex_b), len(ex_a), len(en)))
    bmin = min((r['mask_cover'] for r in ex_b), default=None)
    say('   baseline worst cover %s' % bmin)
    for r in en:
        line = '%s opening %s | copper %s cover %.4f%s' % (r['side'], r['opening'], r['copper'], r['mask_cover'],
                                                          ' EXPOSED' if r['exposed'] else '')
        if r['exposed']:
            hard('exposed-copper', line)
        else:
            adv('mask-cover', line)
    OUT['mask'] = dict(new_slivers=sn, narrow_webs=[{k: v for k, v in r.items() if k != 'key'} for r in webs[:20]],
                       new_cover=[{k: v for k, v in r.items() if k != 'key'} for r in en])

    # ---------------------------------------------------------------- 7. silk
    say('\n== 7. silk-to-mask (%.4f) for visible overlay text vs pad openings' % SILK_MASK)
    silk_a = silk_scan(ops_a)
    sbk = {r['key'] for r in silk_b}
    silk_n = [r for r in silk_a if r['key'] not in sbk]
    for r in silk_n:
        line = '"%s" (%s, %s estimate) vs %s gap %.4f < %.4f' % (r['text'], r['comp'], r['estimate'], r['opening'], r['gap'], r['req'])
        if r['estimate'] == 'nominal':
            hard('silk-to-mask', line)
        else:
            adv('silk-to-mask', line)
    say('   new silk hits: %d (baseline had %d)' % (len(silk_n), len(silk_b)))
    OUT['silk'] = [{k: v for k, v in r.items() if k != 'key'} for r in silk_n]

    # ---------------------------------------------------------------- 8. component clearance / courtyards
    say('\n== 8. component clearance (Altium pad-box measure, %.3f) and IPC-7351B courtyards' % CCGAP)
    boxes = {}
    for c in BX['components']:
        ps = [p for p in BX['pads'] if p['ref'] == c['ref']]
        if not ps:
            continue
        sides = {c['side']} if all(p['layer'] != 'Multi' for p in ps) else {'Top', 'Bottom'}
        x0 = min(p['x'] - p['w'] / 2 for p in ps)
        x1 = max(p['x'] + p['w'] / 2 for p in ps)
        y0 = min(p['y'] - p['h'] / 2 for p in ps)
        y1 = max(p['y'] + p['h'] / 2 for p in ps)
        boxes[c['ref']] = dict(box=(x0, y0, x1, y1), sides=sides, fp=c['footprint'])
    newparts = {}
    for part in PL.get('parts', []):
        xs = [part['pad1']['x'], part['pad2']['x']]
        ys = [part['pad1']['y'], part['pad2']['y']]
        pw, ph = R0201_PAD
        w, h = (pw, ph) if int(part['rot']) % 180 == 0 else (ph, pw)
        newparts[part['ref']] = dict(box=(min(xs) - w / 2, min(ys) - h / 2, max(xs) + w / 2, max(ys) + h / 2),
                                     sides={part['side']}, fp='R0201', rot=part['rot'], c=(part['x'], part['y']))
    allb = dict(boxes)
    allb.update(newparts)

    def courtyard(ref, b):
        bx = b['box']
        if b['fp'] in ('R0201', 'C0201'):
            # IPC-7351B nominal: max(land, body 0.6x0.33) + 0.15 excess
            cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
            horiz = (bx[2] - bx[0]) > (bx[3] - bx[1])
            hx = max((bx[2] - bx[0]) / 2, 0.33) + 0.15
            hy = max((bx[3] - bx[1]) / 2, 0.165) + 0.15
            if not horiz:
                hx, hy = max((bx[2] - bx[0]) / 2, 0.165) + 0.15, max((bx[3] - bx[1]) / 2, 0.33) + 0.15
            return (cx - hx, cy - hy, cx + hx, cy + hy)
        if ref == 'U3':
            b3 = BX['u3']['body']['max']
            return (min(bx[0], b3['x0']) - 0.25, min(bx[1], b3['y0']) - 0.25, max(bx[2], b3['x1']) + 0.25, max(bx[3], b3['y1']) + 0.25)
        if ref == 'U1':
            # CPG236 body 10 x 10 mm centred on the ball field; BGA courtyard excess 1.0 (IPC nominal)
            cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
            return (cx - 5 - 1.0, cy - 5 - 1.0, cx + 5 + 1.0, cy + 5 + 1.0)
        return (bx[0] - 0.25, bx[1] - 0.25, bx[2] + 0.25, bx[3] + 0.25)

    cents = [(c['x'], c['y']) for c in BX['components']]
    hollow = set()
    for q, ob in boxes.items():
        bx = ob['box']
        n_in = sum(1 for c in BX['components'] if c['ref'] != q and (c['side'] in ob['sides']) and
                   bx[0] < c['x'] < bx[2] and bx[1] < c['y'] < bx[3])
        if n_in >= 5:
            hollow.add(q)
    say('   components whose pad-box swallows >= 5 other parts (measured pad by pad instead): %s' % sorted(hollow))
    padsby = collections.defaultdict(list)
    for p in BX['pads']:
        padsby[p['ref']].append(p)
    cc = []
    for r, nb in newparts.items():
        for q, ob in allb.items():
            if q == r or not (nb['sides'] & ob['sides']):
                continue
            if q in hollow:
                g = min(box_gap(nb['box'], (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2))
                        for p in padsby[q])
                if g >= CCGAP + 0.2:
                    continue
                cc.append(dict(a=r, b=q, padbox_gap=round(g, 4), cc_ok=g >= CCGAP - 1e-6, courtyard_overlap=0.0, per_pad=True))
                continue
            g = box_gap(nb['box'], ob['box'])
            ca, cb = courtyard(r, nb), courtyard(q, ob)
            ov = min(ca[2], cb[2]) - max(ca[0], cb[0]), min(ca[3], cb[3]) - max(ca[1], cb[1])
            overlap = ov[0] > 1e-9 and ov[1] > 1e-9
            if g < CCGAP + 0.2 or overlap:
                cc.append(dict(a=r, b=q, padbox_gap=round(g, 4), cc_ok=g >= CCGAP - 1e-6,
                               courtyard_overlap=(round(min(ov), 4) if overlap else 0.0)))
    seenp = set()
    for r in sorted(cc, key=lambda r: r['padbox_gap']):
        k = tuple(sorted((r['a'], r['b'])))
        if k in seenp:
            continue
        seenp.add(k)
        say('   %-5s %-5s %s gap %.4f %s  courtyard overlap %.4f' % (
            r['a'], r['b'], 'per-pad' if r.get('per_pad') else 'pad-box', r['padbox_gap'], 'OK' if r['cc_ok'] else '< %.3f' % CCGAP, r['courtyard_overlap']))
        if not r['cc_ok'] and ('R132' in k or 'R133' in k or 'R134' in k) and not r.get('per_pad'):
            adv('component-clearance', '%s-%s pad-box gap %.4f < %.3f (ComponentClearance; not in batch DRC)' % (k[0], k[1], r['padbox_gap'], CCGAP))
        elif r['courtyard_overlap'] > 0 and ('R132' in k or 'R133' in k or 'R134' in k):
            adv('courtyard', '%s-%s IPC nominal courtyards overlap by %.4f' % (k[0], k[1], r['courtyard_overlap']))
    OUT['component_clearance'] = cc

    # ---------------------------------------------------------------- 9. via-in-pad + tombstoning
    say('\n== 9. via-in-pad sites and 0201 tombstoning balance (all plan parts)')
    smd = [o for o in after if o.kind == 'pad' and not o.multi]
    vip = []
    for v in after:
        if v.kind != 'via':
            continue
        for side in OUTER:
            if side not in v.shp:
                continue
            for p in smd:
                if p.layer != side or abs(p.x - v.x) > 1.5 or abs(p.y - v.y) > 1.5:
                    continue
                hole_c = circ(v.x, v.y, v.hole / 2)
                d = sgap(hole_c, p.shp[side])
                if d < 0:
                    # fully inside?  the hole disc inside the pad rect
                    pts = p.shp[side][0]
                    xs = [q[0] for q in pts]
                    ys = [q[1] for q in pts]
                    full = (min(xs) <= v.x - v.hole / 2 and v.x + v.hole / 2 <= max(xs) and
                            min(ys) <= v.y - v.hole / 2 and v.y + v.hole / 2 <= max(ys))
                    vip.append(dict(pad='%s-%s' % (p.comp, p.pad), via=v.d(), full=full, same_net=p.net == v.net,
                                    new=bool(v.new or p.new)))
    newvip = [r for r in vip if r['new'] and 'rename' not in r['via']]
    for r in vip:
        if r['new']:
            say('   VIPPO %s  %s  fully-inside=%s same-net=%s' % (r['pad'], r['via'], r['full'], r['same_net']))
            if not r['full']:
                hard('via-in-pad', 'hole straddles pad edge: %s %s' % (r['pad'], r['via']))
            if not r['same_net']:
                hard('via-in-pad', 'different net: %s %s' % (r['pad'], r['via']))
    OUT['vippo'] = [r for r in vip if r['new']]
    # tombstoning: per pad, solderable area (VIPPO filled -> no hole loss; unfilled -> hole lost), and heat paths
    tomb = []
    for part in PL.get('parts', []):
        per = {}
        for pn in ('1', '2'):
            p = next(o for o in after if o.kind == 'pad' and o.comp == part['ref'] and o.pad == pn)
            side = p.layer
            area = R0201_PAD[0] * R0201_PAD[1]
            holes = [v for v in after if v.kind == 'via' and side in v.shp and sgap(circ(v.x, v.y, v.hole / 2), p.shp[side]) < 0]
            hole_area = sum(math.pi * (v.hole / 2) ** 2 for v in holes)
            trk = [t for t in after if t.kind == 'track' and t.layer == side and t.net == p.net and sgap(t.shp[side], p.shp[side]) <= 1e-6]
            width_in = sum(t.w for t in trk)
            per[pn] = dict(area=area, hole_area=hole_area, n_holes=len(holes), track_w=width_in, n_tracks=len(trk))
        a1u = per['1']['area'] - per['1']['hole_area']
        a2u = per['2']['area'] - per['2']['hole_area']
        asym_unfilled = abs(a1u - a2u) / max(a1u, a2u)
        h1 = per['1']['track_w'] + sum(1 for _ in range(per['1']['n_holes'])) * math.pi * 0.15
        h2 = per['2']['track_w'] + sum(1 for _ in range(per['2']['n_holes'])) * math.pi * 0.15
        asym_heat = abs(h1 - h2) / max(h1, h2) if max(h1, h2) > 0 else 0
        tomb.append(dict(ref=part['ref'], side=part['side'], pad1=per['1'], pad2=per['2'],
                         area_asym_if_unfilled=round(asym_unfilled, 4), heatpath_asym=round(asym_heat, 4)))
        say('   %s %s: pad1 holes %d tracks %d (%.3f mm), pad2 holes %d tracks %d (%.3f mm); solder-area asym if '
            'NOT filled %.1f %% (0 %% if VIPPO filled+capped); heat-path asym %.0f %%' % (
                part['ref'], part['side'], per['1']['n_holes'], per['1']['n_tracks'], per['1']['track_w'],
                per['2']['n_holes'], per['2']['n_tracks'], per['2']['track_w'], 100 * asym_unfilled, 100 * asym_heat))
        if per['1']['n_tracks'] + per['1']['n_holes'] == 0 or per['2']['n_tracks'] + per['2']['n_holes'] == 0:
            hard('tombstone', '%s has a pad with no connection' % part['ref'])
    OUT['tombstone'] = tomb

    # ---------------------------------------------------------------- 10. pours
    say('\n== 10. L2-GND / L5-VCC3V3 re-poured (raster %.3f mm board, %.4f mm windows); PolygonConnect vias Direct' % (A.res, A.wres))
    pours_b, pours_a = {}, {}
    for L in ('L2-GND', 'L5-VCC3V3'):
        pours_b[L] = pour(base, L, ctx_b)
        pours_a[L] = pour(after, L, ctx_a)
        pb, pa = pours_b[L], pours_a[L]
        res = pb['res']
        dead_b = (pb['cu'] & ~pb['kept']).sum() * res * res
        dead_a = (pa['cu'] & ~pa['kept']).sum() * res * res
        say('   %s: live islands %d -> %d; dead copper %.4f -> %.4f mm2; copper %.4f -> %.4f mm2' % (
            L, len(pb['live']), len(pa['live']), dead_b, dead_a, pb['kept'].sum() * res * res, pa['kept'].sum() * res * res))
        if len(pa['live']) > len(pb['live']):
            hard('pour-island', '%s live islands %d -> %d' % (L, len(pb['live']), len(pa['live'])))
        if dead_a - dead_b > 0.002:
            adv('pour-dead', '%s dead copper grows by %.4f mm2 (removed by Remove Dead Copper)' % (L, dead_a - dead_b))
    # fine windows round every changed object touching L2/L5
    changed = [o for o in after if o.new and o.tag != 'rename' and any(L in o.shp for L in pours_a)]
    removed_keys = set()
    bid = {o.ident for o in base}
    aid = {o.ident for o in after}
    gone = [o for o in base if o.ident not in aid and any(L in o.shp for L in pours_a)]
    wins = []
    for o in changed + gone:
        for L in pours_a:
            if L in o.shp:
                b = sbox(o.shp[L])
                wins.append((L, (b[0] - 0.6, b[1] - 0.6, b[2] + 0.6, b[3] + 0.6)))
    # merge overlapping windows per layer
    merged = []
    for L in pours_a:
        ws = [w for (l, w) in wins if l == L]
        changed_flag = True
        while changed_flag:
            changed_flag = False
            out = []
            for w in ws:
                for k, m in enumerate(out):
                    if not (w[2] < m[0] or w[0] > m[2] or w[3] < m[1] or w[1] > m[3]):
                        out[k] = (min(w[0], m[0]), min(w[1], m[1]), max(w[2], m[2]), max(w[3], m[3]))
                        changed_flag = True
                        break
                else:
                    out.append(w)
            ws = out
        merged += [(L, w) for w in ws]
    say('   %d fine windows' % len(merged))
    sliv_rep = []
    neck_r = 0.05
    for L, w in merged:
        fb = pour(base, L, ctx_b, win=w, res=A.wres)
        fa = pour(after, L, ctx_a, win=w, res=A.wres)
        rp = int(round(neck_r / A.wres))
        st = disk(rp)
        # thin copper = copper not covered by an opening with a 0.10 mm diameter disk
        for nm, fr in (('base', fb), ('after', fa)):
            opened = ndimage.binary_opening(fr['cu'], structure=st)
            fr['thin'] = fr['cu'] & ~opened
        newthin = fa['thin'] & ~fb['thin']
        lab, n = ndimage.label(newthin)
        for k in range(1, n + 1):
            m = lab == k
            area = m.sum() * A.wres ** 2
            if area < 2e-5:
                continue
            jj, ii = np.nonzero(m)
            cx, cy = w[0] + (ii.mean() + 0.5) * A.wres, w[1] + (jj.mean() + 0.5) * A.wres
            # is it attached copper (neck) or a free sliver?  free if the connected copper component is small
            sliv_rep.append(dict(layer=L, at=(round(float(cx), 3), round(float(cy), 3)), area_mm2=round(float(area), 5)))
        # isolated pour fragments (no same-net object, not touching the window edge) after vs base
        def frags(fr):
            la, na = ndimage.label(fr['cu'])
            out = []
            if na == 0:
                return out
            sl = ndimage.find_objects(la)
            H, W = la.shape
            for k, s_ in enumerate(sl, start=1):
                if s_[0].start == 0 or s_[1].start == 0 or s_[0].stop == H or s_[1].stop == W:
                    continue
                m = la[s_] == k
                if (fr['same'][s_] & m).any():
                    continue
                jj, ii = np.nonzero(m)
                out.append((round(w[0] + (ii.mean() + 0.5 + s_[1].start) * A.wres, 3),
                            round(w[1] + (jj.mean() + 0.5 + s_[0].start) * A.wres, 3), round(m.sum() * A.wres ** 2, 5)))
            return out
        f_b, f_a = frags(fb), frags(fa)
        for fx in f_a:
            pre = any(abs(fx[0] - q[0]) < 0.02 and abs(fx[1] - q[1]) < 0.02 for q in f_b)
            say('     %s isolated pour fragment at (%.3f,%.3f) %.5f mm2 (dead copper, removed by Remove Dead)%s' % (
                L, fx[0], fx[1], fx[2], ' -- also on baseline' if pre else ' -- NEW'))
            if not pre:
                adv('pour-fragment', '%s new isolated pour fragment at (%.3f,%.3f) %.5f mm2' % (L, fx[0], fx[1], fx[2]))
    for r in sliv_rep:
        say('   NEW thin (<0.10 mm) pour copper %s at %s area %.5f mm2' % (r['layer'], r['at'], r['area_mm2']))
        adv('pour-sliver', '%s new <0.10 mm pour feature at %s, %.5f mm2' % (r['layer'], r['at'], r['area_mm2']))
    OUT['pour_slivers'] = sliv_rep
    # reference plane: new signal tracks over pour voids on the adjacent plane
    say('   new signal tracks over voids of their reference plane:')
    refp = {'Top': 'L2-GND', 'L3-SIG': 'L2-GND', 'L4-SIG': 'L5-VCC3V3', 'Bottom': 'L5-VCC3V3'}
    rp_rep = []
    for o in after:
        if o.kind != 'track' or not o.new or o.tag == 'rename':
            continue
        P = refp.get(o.layer)
        if not P:
            continue
        pa, pb = pours_a[P], pours_b[P]
        t = o.src
        n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.005))
        voidlen = 0.0
        newvoid = 0.0
        L0 = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / n
        for k in range(n):
            x = t['x1'] + (t['x2'] - t['x1']) * (k + 0.5) / n
            y = t['y1'] + (t['y2'] - t['y1']) * (k + 0.5) / n
            i, j = int((x - pa['win'][0]) / pa['res']), int((y - pa['win'][1]) / pa['res'])
            if not (0 <= j < pa['kept'].shape[0] and 0 <= i < pa['kept'].shape[1]):
                continue
            if not pa['kept'][j, i]:
                voidlen += L0
                if pb['kept'][j, i]:
                    newvoid += L0
        if voidlen > 0.02:
            rp_rep.append(dict(track=o.d(), plane=P, over_void_mm=round(voidlen, 3), over_new_void_mm=round(newvoid, 3)))
            say('     %s over %s void %.3f mm (new void %.3f mm)' % (o.d(), P, voidlen, newvoid))
    OUT['refplane'] = rp_rep

    # ---------------------------------------------------------------- 11. connectivity
    say('\n== 11. connectivity (union-find over copper + pour islands)')
    ufb = connect(base, pours_b)
    ufa = connect(after, pours_a)

    def islands(objs, uf):
        isl = collections.defaultdict(set)
        padisl = collections.defaultdict(set)
        for o in objs:
            if not o.net:
                continue
            r = uf.f(o.id)
            isl[o.net].add(r)
            if o.kind == 'pad':
                padisl[o.net].add(r)
        return isl, padisl

    ib, pib = islands(base, ufb)
    ia, pia = islands(after, ufa)
    nets = sorted(set(ib) | set(ia))
    worse = []
    for n in nets:
        b_, a_ = len(pib.get(n, ())), len(pia.get(n, ()))
        bo, ao = len(ib.get(n, ())), len(ia.get(n, ()))
        if a_ > max(b_, 1) or ao > max(bo, 1):
            worse.append((n, b_, a_, bo, ao))
    say('   nets %d; nets whose pad islands or copper islands grew: %d' % (len(nets), len(worse)))
    for w in worse:
        hard('island', '%s pad islands %d -> %d, copper islands %d -> %d' % w)
    pre_multi = {n: (len(pib[n]), len(ib[n])) for n in ib if len(ib[n]) > 1}
    say('   nets already >1 copper island on the baseline: %d %s' % (len(pre_multi), dict(list(pre_multi.items())[:8])))
    # split per bit: SDRAM-Dn island has exactly {U3 pin, Rn-1}; Dn island has exactly {U1 ball(s), Rn-2}
    say('   per-bit split:')
    split = {}
    for part in PL.get('parts', []):
        bit = part['net_bit']
        sn, dn = 'SDRAM-D%d' % bit, 'D%d' % bit
        sp = sorted('%s-%s' % (o.comp, o.pad) for o in after if o.kind == 'pad' and o.net == sn)
        dp = sorted('%s-%s' % (o.comp, o.pad) for o in after if o.kind == 'pad' and o.net == dn)
        ok = (len(ia.get(sn, ())) == 1 and len(ia.get(dn, ())) == 1 and
              any(p.startswith('U3-') for p in sp) and '%s-1' % part['ref'] in sp and len(sp) == 2 and
              any(p.startswith('U1-') for p in dp) and '%s-2' % part['ref'] in dp)
        # bypass: any SDRAM-Dn object geometrically touching a Dn object (also caught as a short)
        sroot = {ufa.f(o.id) for o in after if o.net == sn}
        droot = {ufa.f(o.id) for o in after if o.net == dn}
        byp = bool(sroot & droot)
        lens = sum(math.hypot(o.src['x2'] - o.src['x1'], o.src['y2'] - o.src['y1']) for o in after if o.kind == 'track' and o.net == sn)
        nv = sum(1 for o in after if o.kind == 'via' and o.net == sn)
        split[bit] = dict(sdram_pads=sp, d_pads=dp, sdram_islands=len(ia.get(sn, ())), d_islands=len(ia.get(dn, ())),
                          ok=ok, bypass=byp, sdram_track_mm=round(lens, 3), sdram_vias=nv)
        say('     D%-2d %s: %s islands %d pads %s | %s islands %d pads %s | U3-side copper %.3f mm %d vias %s%s' % (
            bit, part['ref'], sn, len(ia.get(sn, ())), sp, dn, len(ia.get(dn, ())), dp, lens, nv,
            'OK' if ok else 'FAIL', ' BYPASS' if byp else ''))
        if not ok:
            hard('split', 'D%d split wrong: %s' % (bit, split[bit]))
        if byp:
            hard('bypass', 'D%d resistor bypassed' % bit)
    OUT['split'] = split
    # dangling new track ends
    dang = []
    for o in after:
        if o.kind != 'track' or not o.new:
            continue
        t = o.src
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            hit = False
            for p in after:
                if p.id == o.id or p.net != o.net or o.layer not in p.shp:
                    continue
                s = p.shp[o.layer]
                b = sbox(s)
                if x < b[0] - 1e-3 or x > b[2] + 1e-3 or y < b[1] - 1e-3 or y > b[3] + 1e-3:
                    continue
                if point_in_shape(x, y, s):
                    hit = True
                    break
            if not hit:
                dang.append((o.d(), (x, y)))
    say('   dangling new track ends: %d' % len(dang))
    for d in dang:
        hard('dangling', '%s end %s' % d)
    # new vias: every layer at its span ends must carry same-net copper (else a stub/antenna)
    for o in after:
        if o.kind != 'via' or not o.new or o.tag == 'rename':
            continue
        for L in (o.span[0], o.span[-1]):
            touch = [p for p in after if p.id != o.id and p.net == o.net and L in p.shp and
                     sgap(p.shp[L], o.shp[L]) <= 1e-6]
            plane = L in pours_a and POLYS[L]['net'] == o.net
            if not touch and not plane:
                hard('via-end', '%s has nothing on %s' % (o.d(), L))
    # acid traps on new track joints
    acid = []
    tr = [o for o in after if o.kind == 'track']
    byend = collections.defaultdict(list)
    for o in tr:
        t = o.src
        byend[(o.layer, round(t['x1'], 4), round(t['y1'], 4))].append((o, (t['x2'] - t['x1'], t['y2'] - t['y1'])))
        byend[(o.layer, round(t['x2'], 4), round(t['y2'], 4))].append((o, (t['x1'] - t['x2'], t['y1'] - t['y2'])))
    for k, lst in byend.items():
        if not any(o.new for o, _ in lst):
            continue
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                (oa, va), (ob, vb) = lst[a], lst[b]
                if oa.net != ob.net:
                    continue
                na, nb = math.hypot(*va), math.hypot(*vb)
                if na < 1e-9 or nb < 1e-9:
                    continue
                ang = math.degrees(math.acos(max(-1, min(1, (va[0] * vb[0] + va[1] * vb[1]) / (na * nb)))))
                if ang < 90 - 1e-6 and (oa.new or ob.new):
                    acid.append(dict(at=k, a=oa.d(), b=ob.d(), angle=round(ang, 1)))
    say('   acute (<90 deg) joints involving new tracks: %d' % len(acid))
    for r in acid:
        adv('acid-trap', '%s angle %.1f deg: %s | %s' % (r['at'], r['angle'], r['a'], r['b']))
    OUT['acid'] = acid

    # ---------------------------------------------------------------- verdict
    OUT['hard'] = findings
    OUT['advisory'] = advis
    say('\n== VERDICT input: %d hard findings, %d advisory' % (len(findings), len(advis)))
    for f in findings:
        say('   HARD', f['cat'], f['msg'])
    say('   (%.0f s)' % (time.time() - t0))
    with open(HERE + '/adv13_%s.json' % A.tag, 'w') as fh:
        json.dump(OUT, fh, indent=1, default=str)
    with open(HERE + '/adv13_%s.log' % A.tag, 'w') as fh:
        fh.write('\n'.join(LOGL) + '\n')


main()
