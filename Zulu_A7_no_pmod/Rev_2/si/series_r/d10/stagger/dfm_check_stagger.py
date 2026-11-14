"""dfm_check_stagger.py -- COPY of si/series_r/dfm_check.py (that file is not edited), adapted to read a finished
plan in dq_series_r_plan.json format (default: d10/stagger/plan.json) LITERALLY: every 'remove' / 'remove_vias' entry
is deleted from the board extract, every 'tracks' / 'vias' entry added (renames included, as remove + re-add), every
'renet_pads' entry applied and every 'parts' entry placed as two 0.30 x 0.30 pads.  Step 1 then re-derives the
SDRAM-Dn / Dn split from physical connectivity; a complete plan needs 0 further renames there.  Additions vs the
original (marked 'STAGGER'): plan reader, output names, a hard Top ComponentClearance/body check for the new Top
parts with design_top.py's 0.90 x 0.396 R0201 body proxy, and a pass/fail summary.

    python dfm_check_stagger.py [--plan path/to/plan.json] [--tag name]

ORIGINAL DOCSTRING:
Adversarial DFM / DRC review of the CHOSEN series-R plan (judge's HYBRID: arrays south D0-D7 + top D8/D11/D12 +
judge D9), written from scratch.  It imports nothing from judge_check.py, geom.py, plan_check.py, design_*.py or
route_check.py; it only READS their saved plan JSONs as the description of the edit.

Input : board_extract.json (PcbDoc md5 2a616c1c) + design_arrays.json (south_plan.copper), design_top.json
        (placements D8/D11/D12), judge_sim_d9_plan.json (D9).
Output: dfm_check.json + dfm_check.log in this folder.  Nothing else is written.

Independent choices (different from the judge's checker on purpose):
  * net renaming is DERIVED from physical connectivity after the edit (the island holding the U3 pad becomes
    SDRAM-Dn), then compared with the designers' rename lists;
  * a net-agnostic short check over every copper object (before vs after);
  * L2/L5 pours are rasterised (0.01 mm) with the Rules6 clearances and re-poured before/after: islands,
    dead copper, necks < 0.10 mm, and which plane-net vias/pads each island feeds;
  * per-net island counts for EVERY net on the board before vs after (plane nets through the rasterised pour);
  * mask openings, via-in-pad / via-to-opening, silk, component clearance + IPC courtyards, TSOP toe keep-out,
    tombstone (solderable-area and attached-copper asymmetry), acid traps, decoupling path lengths.
Usage: python dfm_check.py [--variant FINAL|FIXED]
"""
import json, math, os, sys, collections, itertools
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.dirname(os.path.dirname(HERE))                       # STAGGER: si/series_r (read-only)
B = json.load(open(os.path.join(SR, 'board_extract.json')))
PLAN = os.path.join(HERE, 'plan.json')                             # STAGGER
if '--plan' in sys.argv:
    PLAN = os.path.abspath(sys.argv[sys.argv.index('--plan') + 1])
TAG = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'stagger'
CU = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
LN = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom'}
for L in CU:
    LN[L] = L
SDRAM = set()
for k in ('SDRAM_DATA', 'SDRAM_ADDR', 'SDRAM_CTRL'):
    SDRAM |= set(B['net_classes'][k])
SDRAM_NEW = {'SDRAM-D%d' % i for i in range(16)}
PWR_RAILS = set(B['net_classes']['PWR_RAILS'])
PLANE = {'L2-GND': 'GND', 'L5-VCC3V3': 'VCC3V3'}
DPIN = {0: 2, 1: 4, 2: 5, 3: 7, 4: 8, 5: 10, 6: 11, 7: 13, 8: 42, 9: 44, 10: 45, 11: 47, 12: 48, 13: 50, 14: 51, 15: 53}
U1BALL = {0: 'V8', 1: 'V7', 2: 'W7', 3: 'W6', 4: 'U5', 5: 'W5', 6: 'V5', 7: 'U4', 8: 'L1', 9: 'K3', 10: 'K2', 11: 'J1',
          12: 'J3', 13: 'H1', 14: 'A14', 15: 'A15'}
LOG = []
VARIANT = 'PLAN'
if '--variant' in sys.argv:
    VARIANT = sys.argv[sys.argv.index('--variant') + 1]


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s)


# ------------------------------------------------------------------ geometry (exact)
def d_pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def _orient(ax, ay, bx, by, cx, cy):
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def segs_cross(a, b):
    o1 = _orient(a[0], a[1], a[2], a[3], b[0], b[1]); o2 = _orient(a[0], a[1], a[2], a[3], b[2], b[3])
    o3 = _orient(b[0], b[1], b[2], b[3], a[0], a[1]); o4 = _orient(b[0], b[1], b[2], b[3], a[2], a[3])
    return (o1 * o2 < 0) and (o3 * o4 < 0)


def d_seg_seg(a, b):
    if segs_cross(a, b):
        return 0.0
    return min(d_pt_seg(a[0], a[1], *b), d_pt_seg(a[2], a[3], *b), d_pt_seg(b[0], b[1], *a), d_pt_seg(b[2], b[3], *a))


def rect_edges(r):
    cx, cy, hw, hh = r
    x0, x1, y0, y1 = cx - hw, cx + hw, cy - hh, cy + hh
    return [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]


def in_rect(px, py, r, eps=0.0):
    return abs(px - r[0]) <= r[2] + eps and abs(py - r[1]) <= r[3] + eps


def d_seg_rect(s, r):
    if in_rect(s[0], s[1], r) or in_rect(s[2], s[3], r):
        return 0.0
    return min(d_seg_seg(s, e) for e in rect_edges(r))


def d_rect_rect(a, b):
    dx = max(0.0, abs(a[0] - b[0]) - a[2] - b[2])
    dy = max(0.0, abs(a[1] - b[1]) - a[3] - b[3])
    return math.hypot(dx, dy)


def dist(A, Bs):
    """shapes: ('R', cx, cy, hw, hh) axis-aligned rect; ('C', x1, y1, x2, y2, r) capsule (circle when x1=x2,y1=y2)."""
    if A[0] == 'R' and Bs[0] == 'R':
        return d_rect_rect(A[1:], Bs[1:])
    if A[0] == 'C' and Bs[0] == 'C':
        return max(0.0, d_seg_seg(A[1:5], Bs[1:5]) - A[5] - Bs[5])
    if A[0] == 'R':
        A, Bs = Bs, A
    return max(0.0, d_seg_rect(A[1:5], Bs[1:]) - A[5])


def grow(S, g):
    if S[0] == 'R':
        return ('R', S[1], S[2], S[3] + g, S[4] + g)       # square-cornered growth (conservative)
    return ('C',) + tuple(S[1:5]) + (S[5] + g,)


def bbox(S):
    if S[0] == 'R':
        return (S[1] - S[3], S[2] - S[4], S[1] + S[3], S[2] + S[4])
    r = S[5]
    return (min(S[1], S[3]) - r, min(S[2], S[4]) - r, max(S[1], S[3]) + r, max(S[2], S[4]) + r)


def pad_shape(p, layer=None, g=0.0):
    w, h = p['w'], p['h']
    if p['layer'] == 'Multi' and layer is not None:
        if layer == 'Bottom':
            w, h = p['size_bot'] if p['rot'] % 180 == 0 else p['size_bot'][::-1]
        elif layer != 'Top':
            w, h = p['size_mid'] if p['rot'] % 180 == 0 else p['size_mid'][::-1]
    w += 2 * g; h += 2 * g
    if p['shape'] == 'rect':
        return ('R', p['x'], p['y'], w / 2, h / 2)
    if abs(w - h) < 1e-6:
        return ('C', p['x'], p['y'], p['x'], p['y'], w / 2)
    if w > h:
        e = (w - h) / 2
        return ('C', p['x'] - e, p['y'], p['x'] + e, p['y'], h / 2)
    e = (h - w) / 2
    return ('C', p['x'], p['y'] - e, p['x'], p['y'] + e, w / 2)


# ------------------------------------------------------------------ objects
class O:
    __slots__ = ('kind', 'layer', 'net', 'shape', 'rec', 'new', 'tag', 'span', 'hole', 'xy', 'ref', 'pad', 'uid', 'w')

    def __init__(s, kind, layer, net, shape, rec, tag, uid, new=False, span=None, hole=0.0, xy=None, ref=None, pad=None, w=None):
        s.kind, s.layer, s.net, s.shape, s.rec, s.tag, s.uid = kind, layer, net, shape, rec, tag, uid
        s.new, s.span, s.hole, s.xy, s.ref, s.pad, s.w = new, span, hole, xy, ref, pad, w


def same(a, b, tol=2e-3):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def board_records():
    pads = [dict(p) for p in B['pads']]
    tracks = [dict(t) for t in B['tracks'] if t['layer'] in CU]
    vias = [dict(v) for v in B['vias']]
    return pads, tracks, vias


def build_objs(pads, tracks, vias, newflags):
    objs = []
    for i, p in enumerate(pads):
        tag = 'pad %s-%s' % (p['ref'], p['pad'])
        layers = CU if p['layer'] == 'Multi' else [p['layer']]
        for L in layers:
            objs.append(O('pad', L, p['net'], pad_shape(p, L), p, tag, ('p', i), new=('p', i) in newflags,
                          span=layers, hole=p.get('hole', 0.0), xy=(p['x'], p['y']), ref=p['ref'], pad=p['pad']))
    for i, t in enumerate(tracks):
        if t is None:
            continue
        objs.append(O('track', t['layer'], t['net'], ('C', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), t,
                      'track %s %s (%.3f,%.3f)-(%.3f,%.3f) w%.4f' % (t['layer'], t['net'], t['x1'], t['y1'], t['x2'], t['y2'], t['w']),
                      ('t', i), new=('t', i) in newflags, w=t['w']))
    for i, v in enumerate(vias):
        if v is None:
            continue
        for L in v['span']:
            objs.append(O('via', L, v['net'], ('C', v['x'], v['y'], v['x'], v['y'], v['size'] / 2), v,
                          'via %s (%.3f,%.3f) %s>%s d%.2f' % (v['net'], v['x'], v['y'], v['span'][0], v['span'][-1], v['size']),
                          ('v', i), new=('v', i) in newflags, span=v['span'], hole=v['hole'], xy=(v['x'], v['y'])))
    return objs


class Grid:
    def __init__(s, objs, cell=0.5):
        s.c = cell
        s.G = collections.defaultdict(list)
        for o in objs:
            x0, y0, x1, y1 = bbox(o.shape)
            for gx in range(int(math.floor(x0 / cell)), int(math.floor(x1 / cell)) + 1):
                for gy in range(int(math.floor(y0 / cell)), int(math.floor(y1 / cell)) + 1):
                    s.G[(o.layer, gx, gy)].append(o)

    def near(s, layer, bb, pad=0.6):
        x0, y0, x1, y1 = bb
        seen = set()
        for gx in range(int(math.floor((x0 - pad) / s.c)), int(math.floor((x1 + pad) / s.c)) + 1):
            for gy in range(int(math.floor((y0 - pad) / s.c)), int(math.floor((y1 + pad) / s.c)) + 1):
                for q in s.G.get((layer, gx, gy), ()):
                    if id(q) not in seen:
                        seen.add(id(q))
                        yield q


# ------------------------------------------------------------------ plan loading (FINAL = judge's winner)
def load_plan():
    """STAGGER: read a dq_series_r_plan.json-format plan literally (renames are remove + re-add)"""
    P = json.load(open(PLAN))
    E = dict(rm_t=[], add_t=[], rm_v=[], add_v=[], renet=[], add_p=[], parts={}, designer_renames=collections.defaultdict(list))
    for t in P['remove']:
        E['rm_t'].append(dict(t, layer=LN[t['layer']]))
    for t in P['tracks']:
        E['add_t'].append(dict(net=t['net'], layer=LN[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in P['remove_vias']:
        m = [b for b in B['vias'] if same((b['x'], b['y']), (v['x'], v['y'])) and b['span'][0] == LN.get(v['span'][0], v['span'][0])
             and b['span'][-1] == LN.get(v['span'][-1], v['span'][-1]) and b['net'] == v['net']]
        assert len(m) == 1, ('remove_vias entry matches %d board vias' % len(m), v)
        E['rm_v'].append(dict(x=v['x'], y=v['y'], span=list(m[0]['span'])))
    for v in P['vias']:
        a_, b_ = CU.index(LN[v['from']]), CU.index(LN[v['to']])
        sp = CU[min(a_, b_):max(a_, b_) + 1]
        E['add_v'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=sp,
                               kind='through' if len(sp) == 6 else 'micro'))
    E['renet'] = [dict(r) for r in P['renet_pads']]
    for pr in P['parts']:
        for k, pd in (('1', pr['pad1']), ('2', pr['pad2'])):
            E['add_p'].append(dict(ref=pr['ref'], pad=k, layer=pr['side'], net=pd['net'], x=pd['x'], y=pd['y'],
                                   w=0.3, h=0.3, shape='rect', hole=0.0))
        E['parts'][pr['net_bit']] = dict(ref=pr['ref'], side=pr['side'], x=pr['x'], y=pr['y'], rot=pr['rot'])
    E['net_class_add'] = P.get('net_class_add', {})
    return E


FIXES = {}   # filled by --variant FIXED (see apply_fixes)


F1XY = tuple(float(x) for x in os.environ.get('DFM_F1XY', '39.49,15.81').split(','))


def apply_fixes(E):
    """Concrete fixes proposed by this review, re-checked by the same code (variant FIXED)."""
    # F1: D12 line-side column centred in R131-2 (full via-in-pad, VIPPO) instead of 0.1 mm off-centre; the Top jog
    #     and the L4 dog-leg go; one L4 segment (39.5,15.8)-(40.9,15.1) re-joins the kept D12 route.
    for v in E['add_v']:
        if v['net'] == 'D12' and same((v['x'], v['y']), (39.3, 15.9)):
            v['x'], v['y'] = F1XY
    E['add_t'] = [t for t in E['add_t'] if not (t['net'] == 'D12')]
    E['add_t'].append(dict(layer='L4-SIG', net='D12', x1=F1XY[0], y1=F1XY[1], x2=40.9, y2=15.1, w=0.125))
    FIXES['F1'] = ('D12 line-side Top>L2>L3>L4 column moved (39.3,15.9)->(%.3f,%.3f), hole inside R131-2; Top jog and '
                   'L4 dog-leg (39.3,15.9)-(39.2061,15.5293)-(40.9,15.1) replaced by one L4 segment to (40.9,15.1) w0.125' % F1XY)
    # F2: the five HORIZONTAL south Rs (pad 2 faces a different-net U3 pad) move DY south with their feed/return.
    DY = float(os.environ.get('DFM_DY', '-0.04'))
    if DY:
        refs = {'R119': 0, 'R120': 1, 'R122': 3, 'R123': 4}   # R126 cannot move: TDO via (29.15,4.80) and the U3-12 GND re-run sit south of it
        ys = (5.21015, 5.41015)
        for p in E['add_p']:
            if p['ref'] in refs:
                p['y'] += DY
        for t in E['add_t']:
            n = t['net'].replace('SDRAM-', '')
            if n not in ['D%d' % k for k in refs.values()] or t['layer'] != 'Bottom':
                continue
            for k in ('1', '2'):
                if any(abs(t['y' + k] - y0) < 1e-4 for y0 in ys):
                    t['y' + k] += DY
        FIXES['F2'] = 'R119/R120/R122/R123 (+feed end, return start and first bend) moved %.3f mm in y' % DY
    return E


def apply(E):
    pads, tracks, vias = board_records()
    errors = []
    newflags = set()
    for rm in E['rm_t']:
        hit = None
        for i, t in enumerate(tracks):
            if t is None or t['layer'] != rm['layer'] or (rm.get('net') and t['net'] != rm['net']):
                continue
            a, b = (rm['x1'], rm['y1']), (rm['x2'], rm['y2'])
            if (same(a, (t['x1'], t['y1'])) and same(b, (t['x2'], t['y2']))) or (same(a, (t['x2'], t['y2'])) and same(b, (t['x1'], t['y1']))):
                hit = i
                break
        if hit is None:
            errors.append('track removal unmatched: %s' % rm)
        else:
            tracks[hit] = None
    for rm in E['rm_v']:
        hit = [i for i, v in enumerate(vias) if v is not None and same((v['x'], v['y']), (rm['x'], rm['y'])) and v['span'] == rm['span']]
        if not hit:
            errors.append('via removal unmatched: %s' % rm)
        for i in hit[:1]:
            vias[i] = None
    for rp in E['renet']:
        hit = [i for i, p in enumerate(pads) if p['ref'] == rp['ref'] and p['pad'] == rp['pad']]
        if len(hit) != 1:
            errors.append('renet pad %s matched %d' % (rp, len(hit)))
        for i in hit:
            pads[i]['net'] = rp['net']
            newflags.add(('p', i))
    for p in E['add_p']:
        pads.append(dict(p, rot=0.0, corners=None))
        newflags.add(('p', len(pads) - 1))
    for t in E['add_t']:
        tracks.append(dict(layer=t['layer'], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], w=t['w']))
        newflags.add(('t', len(tracks) - 1))
    for v in E['add_v']:
        vias.append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=list(v['span']), kind=v.get('kind', 'micro')))
        newflags.add(('v', len(vias) - 1))
    return pads, tracks, vias, newflags, errors


# ------------------------------------------------------------------ connectivity
class UF:
    def __init__(s, n):
        s.p = list(range(n))

    def f(s, a):
        while s.p[a] != a:
            s.p[a] = s.p[s.p[a]]
            a = s.p[a]
        return a

    def u(s, a, b):
        s.p[s.f(a)] = s.f(b)


def phys_islands(objs, net_aware=True, plane_join=None):
    """union-find of touching copper.  net_aware: only same-net objects join (Altium connectivity);
    plane_join: {layer: label array + mapping} to join plane-net objects through the poured pour."""
    G = Grid(objs, 0.5)
    uf = UF(len(objs))
    idx = {id(o): k for k, o in enumerate(objs)}
    for k, o in enumerate(objs):
        for q in G.near(o.layer, bbox(o.shape), pad=0.01):
            kq = idx[id(q)]
            if kq <= k:
                continue
            if net_aware and q.net != o.net:
                continue
            if dist(o.shape, q.shape) <= 1e-4:
                uf.u(k, kq)
    # same via / through pad on several layers
    by = collections.defaultdict(list)
    for k, o in enumerate(objs):
        if o.kind in ('via', 'pad') and o.uid is not None:
            by[o.uid].append(k)
    for ks in by.values():
        for a in ks[1:]:
            uf.u(ks[0], a)
    if plane_join:
        for L, (lab, net) in plane_join.items():
            comp = {}
            for k, o in enumerate(objs):
                if o.layer != L or o.net != net:
                    continue
                c = lab_at(lab, o.xy if o.xy else ((o.shape[1] + o.shape[3]) / 2, (o.shape[2] + o.shape[4]) / 2))
                if c:
                    if c in comp:
                        uf.u(k, comp[c])
                    else:
                        comp[c] = k
    return uf


# ------------------------------------------------------------------ plane pour raster
RES = 0.01
NX, NY = int(round(60.96 / RES)), int(round(25.4 / RES))


def stamp(mask, S, g, val=True):
    x0, y0, x1, y1 = bbox(grow(S, g))
    i0, i1 = max(0, int(x0 / RES) - 1), min(NX, int(x1 / RES) + 2)
    j0, j1 = max(0, int(y0 / RES) - 1), min(NY, int(y1 / RES) + 2)
    if i0 >= i1 or j0 >= j1:
        return
    xs = (np.arange(i0, i1) + 0.5) * RES
    ys = (np.arange(j0, j1) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys)
    if S[0] == 'R':
        m = (np.abs(X - S[1]) <= S[3] + g) & (np.abs(Y - S[2]) <= S[4] + g)
    else:
        x1_, y1_, x2_, y2_, r = S[1:6]
        dx, dy = x2_ - x1_, y2_ - y1_
        L2 = dx * dx + dy * dy
        if L2 == 0:
            d = np.hypot(X - x1_, Y - y1_)
        else:
            t = np.clip(((X - x1_) * dx + (Y - y1_) * dy) / L2, 0, 1)
            d = np.hypot(X - x1_ - t * dx, Y - y1_ - t * dy)
        m = d <= r + g
    mask[j0:j1, i0:i1] |= m if val else False


def lab_at(lab, xy):
    i, j = int(xy[0] / RES), int(xy[1] / RES)
    if 0 <= i < NX and 0 <= j < NY:
        return int(lab[j, i])
    return 0


def pour(objs, L):
    net = PLANE[L]
    area = np.zeros((NY, NX), bool)
    b0, b1 = int(0.25 / RES), int(60.71 / RES)
    c0, c1 = int(0.25 / RES), int(25.15 / RES)
    area[c0:c1, b0:b1] = True
    void = np.zeros_like(area)
    cu = np.zeros_like(area)
    for o in objs:
        if o.layer != L:
            continue
        if o.net == net:
            stamp(cu, o.shape, 0.0)
            continue
        if o.kind == 'via':
            g = 0.175 if len(o.span) == 6 else 0.09
        elif o.kind == 'pad':
            g = 0.10 if (o.ref == 'X1' and L == 'L5-VCC3V3') else 0.09
        else:
            g = 0.10 if (o.net in SDRAM | SDRAM_NEW and False) else 0.09
        stamp(void, o.shape, g)
    raw = area & ~void
    lab, n = ndimage.label(raw | cu)
    live = set()
    for o in objs:
        if o.layer == L and o.net == net:
            c = lab_at(lab, o.xy if o.xy else (o.shape[1], o.shape[2]))
            if c:
                live.add(c)
    kept = np.isin(lab, list(live))
    # necks: open by a 0.10 mm wide disk (remove copper narrower than 0.10 mm) and relabel
    r = 5
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (xx * xx + yy * yy) <= r * r
    opened = ndimage.binary_opening(kept, structure=disk)
    lab2, n2 = ndimage.label(opened | (cu & kept))
    return dict(lab=lab, kept=kept, live=live, opened=opened, lab2=lab2, void=void, cu=cu)


# ------------------------------------------------------------------ checks
def gap_rule(a, b, L, classes_updated=True):
    sd = SDRAM | (SDRAM_NEW if classes_updated else set())
    g = 0.09
    if L in ('L3-SIG', 'L4-SIG'):
        if a.net in sd or b.net in sd:
            g = 0.10
        if a.net == 'SDRAM-CLK' or b.net == 'SDRAM-CLK':
            g = 0.20
    if 'X1' in (a.ref, b.ref) and L == 'L5-VCC3V3' and 'VCC3V3' in (a.net, b.net):
        g = 0.10
    return g


def width_rule(net, L):
    """(min, max, rule) per Rules6 priority (sparse per-layer table)."""
    if net in SDRAM | SDRAM_NEW:
        lo = {'Top': 0.0762, 'L3-SIG': 0.10, 'L4-SIG': 0.10, 'Bottom': 0.10}.get(L, 0.0762)
        return lo, 0.15, 'Width_SDRAM'
    if net == 'VCC3V3':
        lo = {'L3-SIG': 1.05, 'L4-SIG': 1.05, 'Bottom': 0.20}.get(L, 0.0762)
        return lo, 1.5, 'Width_PWR_VCC3V3'
    if net in ('VU', 'USB5V0', 'VBATT'):
        return {'L3-SIG': 1.1, 'L4-SIG': 1.1}.get(L, 0.2), 1.5, 'Width_PWR_U8'
    if net == 'VCC1V0':
        return {'L3-SIG': 0.5, 'L4-SIG': 0.5}.get(L, 0.15), 1.5, 'Width_PWR_VCC1V0'
    if net in PWR_RAILS:
        return 0.15, 1.0, 'Width_PWR_RAILS'
    return 0.0762, 0.5, 'Width'


def mask_exp(o):
    if o.ref == 'U1':
        return 0.0
    if o.ref == 'X3':
        return 0.04
    return 0.05


def text_box(t):
    """visible overlay text: approximate stroke-font extent (Altium default stroke font: char cell ~ 0.8 x height incl. spacing)."""
    w = len(t['text']) * t['height'] * 0.8
    h = t['height']
    if int(round(t['rot'])) % 180 == 90:
        x0, y0, x1, y1 = t['x'] - h, t['y'], t['x'], t['y'] + w
    else:
        x0, y0, x1, y1 = t['x'], t['y'], t['x'] + w, t['y'] + h
    if t.get('mirror'):
        x0, x1 = 2 * t['x'] - x1, 2 * t['x'] - x0
    return ('R', (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2)


def main():
    E = load_plan()
    out = dict(variant=VARIANT, plan=PLAN, source=B['source']['pcbdoc_md5'], fixes_applied=FIXES)
    pads0, tracks0, vias0 = board_records()
    before = build_objs(pads0, tracks0, vias0, set())
    pads, tracks, vias, newflags, errors = apply(E)
    log('==== dfm_check_stagger.py  plan %s  (PcbDoc md5 %s) ====' % (PLAN, B['source']['pcbdoc_md5']))
    log('apply: -%d tracks +%d tracks, -%d vias +%d vias, %d pads renet, %d new pads; errors: %d' % (
        len(E['rm_t']), len(E['add_t']), len(E['rm_v']), len(E['add_v']), len(E['renet']), len(E['add_p']), len(errors)))
    for e in errors:
        log('  APPLY ERROR', e)
    out['apply_errors'] = errors

    # ---------- 1. derive the SDRAM-Dn / Dn split from physical connectivity
    objs = build_objs(pads, tracks, vias, newflags)
    rename_report = {}
    for n in sorted(E['parts']):
        fam = {'D%d' % n, 'SDRAM-D%d' % n}
        sub = [o for o in objs if o.net in fam]
        uf = phys_islands(sub, net_aware=False)
        isl = collections.defaultdict(list)
        for k, o in enumerate(sub):
            isl[uf.f(k)].append(o)
        u3 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U3' for o in os_)]
        u1 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U1' for o in os_)]
        ref = E['parts'][n]['ref']
        rep = dict(ref=ref, islands=len(isl), ok=True, notes=[])
        if len(u3) != 1 or len(u1) != 1 or u3[0] == u1[0]:
            rep['ok'] = False
            rep['notes'].append('U3 island %s, U1 island %s -- R bypassed or net open' % (u3, u1))
        else:
            A_, B_ = isl[u3[0]], isl[u1[0]]
            pa = sorted(o.tag for o in A_ if o.kind == 'pad')
            pb = sorted(o.tag for o in B_ if o.kind == 'pad')
            if pa != sorted(['pad U3-%d' % DPIN[n], 'pad %s-1' % ref]) or pb != sorted(['pad %s-2' % ref, 'pad U1-%s' % U1BALL[n]]):
                rep['ok'] = False
                rep['notes'].append('pads per side: U3 side %s / U1 side %s' % (pa, pb))
            extra = [r for r in isl if r not in (u3[0], u1[0])]
            if extra:
                rep['notes'].append('%d extra island(s): %s' % (len(extra), [[o.tag for o in isl[r]][:4] for r in extra]))
                rep['ok'] = False
            # relabel; record what changes vs the plan labels
            relabel = []
            for o in A_:
                if o.net != 'SDRAM-D%d' % n:
                    relabel.append(o.tag)
                    o.net = 'SDRAM-D%d' % n
                    o.new = True
            for o in B_:
                if o.net != 'D%d' % n:
                    rep['notes'].append('U1-side object labelled %s: %s' % (o.net, o.tag))
                    rep['ok'] = False
            rep['derived_renames'] = sorted(set(relabel))
            # compare with the designer's rename list (top plan only)
            dr = E['designer_renames'].get('D%d' % n)
            if dr:
                want = len(dr['tracks']) + len(dr['vias']) + len(dr['pads'])
                got_t = sum(1 for t in set(relabel) if t.startswith('track'))
                got_v = len(set(t for t in relabel if t.startswith('via')))
                rep['designer_vs_derived'] = dict(designer_tracks=len(dr['tracks']), designer_vias=len(dr['vias']),
                                                  derived_tracks=got_t, derived_vias=got_v)
            rep['u3_side_len_mm'] = round(sum(math.hypot(o.shape[3] - o.shape[1], o.shape[4] - o.shape[2]) for o in A_ if o.kind == 'track'), 3)
        rename_report['D%d' % n] = rep
    # propagate labels to the records (pads/tracks/vias share uids)
    lab_by_uid = {}
    for o in objs:
        lab_by_uid.setdefault(o.uid, (o.net, o.new))
    for o in objs:
        o.net, nw = lab_by_uid[o.uid][0], lab_by_uid[o.uid][1]
        o.new = o.new or nw
    log('\n-- 1. SDRAM-Dn / Dn split derived from connectivity --')
    for k, r in rename_report.items():
        log('  %-4s %-5s islands %d ok=%s U3-side copper %.3f mm  derived renames %d %s %s' % (
            k, r['ref'], r['islands'], r['ok'], r.get('u3_side_len_mm', -1), len(r.get('derived_renames', [])),
            r.get('designer_vs_derived', ''), '; '.join(r['notes'])))
    out['split'] = rename_report

    # ---------- 2. net-agnostic short check (before vs after)
    def shorts(oo):
        uf = phys_islands(oo, net_aware=False)
        nets = collections.defaultdict(set)
        for k, o in enumerate(oo):
            if o.net:
                nets[uf.f(k)].add(o.net)
        return sorted(tuple(sorted(s)) for s in nets.values() if len(s) > 1)
    sh0, sh1 = shorts(before), shorts(objs)
    new_sh = [s for s in sh1 if s not in sh0]
    log('\n-- 2. physical shorts (any copper touching across nets): before %d, after %d, NEW %d' % (len(sh0), len(sh1), len(new_sh)))
    for s in new_sh:
        log('  NEW SHORT', s)
    out['shorts'] = dict(before=sh0, after=sh1, new=new_sh)

    # ---------- 3. plane pours before/after
    log('\n-- 3. L2/L5 pours re-poured from Rules6 clearances (0.01 mm raster) --')
    P0 = {L: pour(before, L) for L in PLANE}
    P1 = {L: pour(objs, L) for L in PLANE}
    plane_rep = {}
    for L, net in PLANE.items():
        a, b = P0[L], P1[L]

        def feeds(P, oo):
            m = collections.defaultdict(set)
            m2 = collections.defaultdict(set)
            for o in oo:
                if o.layer == L and o.net == net:
                    m[lab_at(P['lab'], o.xy or (o.shape[1], o.shape[2]))].add(o.tag)
                    m2[lab_at(P['lab2'], o.xy or (o.shape[1], o.shape[2]))].add(o.tag)
            return m, m2
        f0, g0 = feeds(a, before)
        f1, g1 = feeds(b, objs)
        main0 = max(f0.items(), key=lambda kv: len(kv[1]))[0]
        main1 = max(f1.items(), key=lambda kv: len(kv[1]))[0]
        off0 = sorted(t for c, s in f0.items() if c != main0 for t in s)
        off1 = sorted(t for c, s in f1.items() if c != main1 for t in s)
        gm0 = max(g0.items(), key=lambda kv: len(kv[1]))[0]
        gm1 = max(g1.items(), key=lambda kv: len(kv[1]))[0]
        neck0 = sorted(t for c, s in g0.items() if c != gm0 for t in s)
        neck1 = sorted(t for c, s in g1.items() if c != gm1 for t in s)
        diff = (a['kept'] != b['kept'])
        lost = int((a['kept'] & ~b['kept']).sum())
        gained = int((~a['kept'] & b['kept']).sum())
        thin0 = a['kept'] & ~a['opened']
        thin1 = b['kept'] & ~b['opened']
        new_thin = thin1 & ~thin0
        lab_t, nt = ndimage.label(new_thin)
        thin_spots = []
        for sl, k in zip(ndimage.find_objects(lab_t), range(1, nt + 1)):
            cnt = int((lab_t[sl] == k).sum())
            if cnt < 3:
                continue
            ys, xs = sl
            thin_spots.append(dict(x=round((xs.start + xs.stop) / 2 * RES, 3), y=round((ys.start + ys.stop) / 2 * RES, 3), area_mm2=round(cnt * RES * RES, 4)))
        ys, xs = np.nonzero(diff)
        bb = [round(xs.min() * RES, 2), round(ys.min() * RES, 2), round(xs.max() * RES, 2), round(ys.max() * RES, 2)] if len(xs) else None
        rep = dict(plane_net=net, live_islands_before=len(a['live']), live_islands_after=len(b['live']),
                   objects_off_main_before=off0, objects_off_main_after=off1,
                   off_main_through_necks_lt_0p10_before=neck0, off_main_through_necks_lt_0p10_after=neck1,
                   copper_lost_mm2=round(lost * RES * RES, 4), copper_gained_mm2=round(gained * RES * RES, 4), changed_bbox=bb,
                   new_sub_0p10_slivers=thin_spots)
        plane_rep[L] = rep
        log('  %s: live islands %d -> %d; plane-net objects off the main island %d -> %d; only-through-<0.10mm-necks %d -> %d; copper -%.4f/+%.4f mm2; new <0.10 mm slivers: %d' % (
            L, rep['live_islands_before'], rep['live_islands_after'], len(off0), len(off1), len(neck0), len(neck1),
            rep['copper_lost_mm2'], rep['copper_gained_mm2'], len(thin_spots)))
        for t in sorted(set(off1) - set(off0)):
            log('    NEWLY ISOLATED from main pour:', t)
        for t in sorted(set(neck1) - set(neck0)):
            log('    newly attached only through a <0.10 mm neck:', t)
        for s in thin_spots:
            log('    new sliver <0.10 mm wide at (%.2f,%.2f) %.4f mm2' % (s['x'], s['y'], s['area_mm2']))
    out['planes'] = plane_rep
    # reference-plane continuity: tracks on the adjacent signal layers whose centreline now runs over removed pour
    ADJ = {'L2-GND': ('Top', 'L3-SIG'), 'L5-VCC3V3': ('L4-SIG', 'Bottom')}
    refx = []
    for L in PLANE:
        lost = P0[L]['kept'] & ~P1[L]['kept']
        for o in objs:
            if o.kind != 'track' or o.layer not in ADJ[L]:
                continue
            x1, y1, x2, y2 = o.shape[1:5]
            Lg = math.hypot(x2 - x1, y2 - y1)
            nseg = max(2, int(Lg / 0.005))
            hit = 0
            for k in range(nseg + 1):
                t = k / nseg
                i, j = int((x1 + t * (x2 - x1)) / RES), int((y1 + t * (y2 - y1)) / RES)
                if 0 <= i < NX and 0 <= j < NY and lost[j, i] and not P1[L]['kept'][j, i]:
                    hit += 1
            if hit:
                refx.append(dict(plane=L, track=o.tag, over_new_void_mm=round(hit * Lg / nseg, 3)))
    log('  tracks on layers adjacent to L2/L5 now running over NEW pour voids: %d' % len(refx))
    for r in refx:
        log('    ', r)
    out['reference_plane_new_voids'] = refx
    # plane-web metric around new openings
    webs = []
    for L, net in PLANE.items():
        holes = [o for o in objs if o.layer == L and o.net != net and o.kind in ('via', 'pad')]
        for o in holes:
            if not o.new:
                continue
            ro = o.shape[5] + (0.175 if (o.kind == 'via' and len(o.span) == 6) else 0.09) if o.shape[0] == 'C' else 0
            best = (9, None)
            for q in holes:
                if q is o or same(q.xy, o.xy, 1e-4):
                    continue
                rq = q.shape[5] + (0.175 if (q.kind == 'via' and len(q.span) == 6) else 0.09) if q.shape[0] == 'C' else 0
                w_ = math.hypot(q.xy[0] - o.xy[0], q.xy[1] - o.xy[1]) - ro - rq
                if w_ < best[0]:
                    best = (w_, q.tag)
            webs.append(dict(layer=L, at=o.tag, web=round(best[0], 3), to=best[1]))
    out['plane_webs_new_or_renamed_openings'] = webs

    # ---------- 4. per-net connectivity, EVERY net, before vs after (plane nets through the poured pour)
    def islands(oo, P):
        pj = {L: (P[L]['lab'], PLANE[L]) for L in PLANE}
        uf = phys_islands(oo, net_aware=True, plane_join=pj)
        res = collections.defaultdict(set)
        for k, o in enumerate(oo):
            if o.kind == 'pad' and o.net:
                res[o.net].add(uf.f(k))
        return {n: len(s) for n, s in res.items()}, uf
    i0, _ = islands(before, P0)
    i1, uf1 = islands(objs, P1)
    worse = {n: (i0.get(n), i1.get(n)) for n in set(i0) | set(i1) if i1.get(n, 0) > i0.get(n, 1) and not n.startswith('SDRAM-D')}
    newnets = {n: i1[n] for n in i1 if n.startswith('SDRAM-D')}
    log('\n-- 4. per-net pad islands, all %d nets: nets with more islands after than before: %s' % (len(i1), worse or 'none'))
    log('     SDRAM-Dn nets (new): %s' % newnets)
    pre_open = {n: v for n, v in i0.items() if v > 1}
    log('     nets already >1 island BEFORE (extract-level, unchanged by the plan unless listed above): %s' % pre_open)
    out['net_islands'] = dict(worse=worse, sdram_new=newnets, before_multi=pre_open)
    # antennae on touched nets
    touched = set(o.net for o in objs if o.new) | set(t['net'] for t in E['rm_t'])
    ant = []
    G = Grid(objs, 0.5)
    for o in objs:
        if o.kind != 'track' or o.net not in touched or o.layer in PLANE:
            continue
        for ex, ey in ((o.shape[1], o.shape[2]), (o.shape[3], o.shape[4])):
            P_ = ('C', ex, ey, ex, ey, 0.0)
            ok = any(q is not o and q.net == o.net and dist(P_, q.shape) <= 1e-4 for q in G.near(o.layer, bbox(P_), 0.01))
            if not ok:
                ant.append('%s end (%.3f,%.3f)' % (o.tag, ex, ey))
    log('     dangling track ends on touched nets: %d %s' % (len(ant), ant[:10]))
    out['antennae'] = ant

    # ---------- 5. copper clearance (new / renamed objects)
    viol, worst, near_list = [], {}, []
    G = Grid(objs, 0.5)
    seen = set()
    for o in objs:
        if not o.new:
            continue
        for q in G.near(o.layer, bbox(o.shape), 0.3):
            if q is o or (q.net == o.net and o.net):
                continue
            key = tuple(sorted((id(o), id(q))))
            if key in seen:
                continue
            seen.add(key)
            if o.uid == q.uid:
                continue
            d = dist(o.shape, q.shape)
            g = gap_rule(o, q, o.layer)
            m = d - g
            r = 'clearance %s' % o.layer
            if r not in worst or m < worst[r][0]:
                worst[r] = (round(m, 4), round(d, 4), g, o.tag, q.tag)
            if m < -1e-6:
                viol.append(dict(rule='Clearance', layer=o.layer, value=round(d, 4), limit=g, a=o.tag, b=q.tag))
            elif m < 0.01:
                near_list.append(dict(layer=o.layer, margin=round(m, 4), a=o.tag, b=q.tag))
            # what if SDRAM-Dn is NOT added to SDRAM_DATA: the inner rule silently drops to 0.09
    log('\n-- 5. copper clearance on new/renamed objects: %d violations' % len(viol))
    for v in viol:
        log('  VIOL', v)
    for r, w in sorted(worst.items()):
        log('  worst %-20s margin %+.4f (gap %.4f, rule %.3f)  %s  vs  %s' % (r, w[0], w[1], w[2], w[3], w[4]))
    out['clearance'] = dict(violations=viol, worst=worst, within_0p01=near_list)

    # ---------- 6. hole to hole
    drills = []
    for o in objs:
        if o.kind == 'via' and o.layer == o.span[0]:
            drills.append((o.xy, o.hole, set(o.span), o.new, o.tag, o.rec.get('kind', '')))
    for p in pads:
        if p.get('hole', 0) > 0:
            drills.append(((p['x'], p['y']), p['hole'], set(CU), False, 'pad %s-%s' % (p['ref'], p['pad']), 'pth'))
    h2h, h2h_worst = [], None
    for i, a in enumerate(drills):
        if not a[3]:
            continue
        for j, b in enumerate(drills):
            if i == j or (b[3] and j < i):
                continue
            if same(a[0], b[0], 1e-4):
                continue
            d = math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]) - a[1] / 2 - b[1] / 2
            if d > 0.6:
                continue
            shared = bool(a[2] & b[2])
            rec = dict(value=round(d, 4), shared_layer=shared, a=a[4], b=b[4])
            if shared and (h2h_worst is None or d < h2h_worst['value']):
                h2h_worst = rec
            if shared and d < 0.24 - 1e-6:
                h2h.append(rec)
    log('\n-- 6. hole-to-hole (0.24, shared span): %d violations; worst %s' % (len(h2h), h2h_worst))
    out['hole_to_hole'] = dict(violations=h2h, worst=h2h_worst)

    # ---------- 7. width rules on every added/renamed track
    wv = []
    for o in objs:
        if o.kind == 'track' and o.new:
            lo, hi, rn = width_rule(o.net, o.layer)
            if not (lo - 1e-6 <= o.w <= hi + 1e-6):
                wv.append(dict(rule=rn, layer=o.layer, net=o.net, width=o.w, limits=(lo, hi), tag=o.tag))
    log('\n-- 7. width rules on new/renamed tracks: %d violations %s' % (len(wv), wv))
    out['width'] = wv

    # ---------- 8. solder mask: slivers, merged openings, via-in-pad, via-to-opening
    sides = {}
    for side in ('Top', 'Bottom'):
        sides[side] = [o for o in objs if o.kind == 'pad' and o.layer == side]
    ms, mworst = [], {}
    for side, ps in sides.items():
        Gp = Grid(ps, 0.5)
        for o in ps:
            if not o.new:
                continue
            mo = grow(o.shape, mask_exp(o))
            for q in Gp.near(side, bbox(mo), 0.3):
                if q is o:
                    continue
                mq = grow(q.shape, mask_exp(q))
                d = dist(mo, mq)
                if d > 0.4:
                    continue
                k = 'mask sliver ' + side
                if d > 0 and (k not in mworst or d < mworst[k][0]):
                    mworst[k] = (round(d, 4), o.tag, q.tag)
                if 0 < d < 0.10 - 1e-6:
                    ms.append(dict(rule='MinimumSolderMaskSliver 0.10', side=side, value=round(d, 4), a=o.tag, b=q.tag))
                if d == 0 and q.net != o.net:
                    ms.append(dict(rule='mask openings merge across nets', side=side, value=0.0, a=o.tag, b=q.tag))
    vip = []
    for side in ('Top', 'Bottom'):
        for o in sides[side]:
            if not (o.new and o.ref and o.ref.startswith('R') and int(o.ref[1:]) >= 119):
                continue
            op = grow(o.shape, mask_exp(o))
            for q in objs:
                if q.kind != 'via' or q.layer != side:
                    continue
                dcu = dist(o.shape, q.shape)
                if dcu > 0.2:
                    continue
                hole = ('C', q.xy[0], q.xy[1], q.xy[0], q.xy[1], q.hole / 2)
                land_in_open = dist(op, q.shape) == 0
                hole_to_open = dist(op, hole)
                inside = all(in_rect(q.xy[0] + dx, q.xy[1] + dy, o.shape[1:], 1e-6) for dx, dy in
                             ((q.hole / 2, 0), (-q.hole / 2, 0), (0, q.hole / 2), (0, -q.hole / 2)))
                vip.append(dict(pad=o.tag, via=q.tag, same_net=q.net == o.net, copper_gap=round(dcu, 4),
                                land_exposed_in_opening=land_in_open, hole_edge_to_opening=round(hole_to_open, 4),
                                hole_fully_inside_pad=inside, via_kind=q.rec.get('kind')))
    log('\n-- 8. mask: %d violations %s; worst %s' % (len(ms), ms, mworst))
    log('   vias within 0.2 mm of a new R pad (copper):')
    for v in vip:
        log('    ', v)
    # 8b: each new R pad vs the nearest pad of ANOTHER component (opening web + copper gap + nets)
    rpairs = []
    for side, ps in sides.items():
        for o in ps:
            if not (o.new and o.ref and o.ref.startswith('R') and int(o.ref[1:]) >= 119):
                continue
            mo = grow(o.shape, mask_exp(o))
            best = None
            for q in ps:
                if q.ref == o.ref:
                    continue
                d = dist(mo, grow(q.shape, mask_exp(q)))
                if best is None or d < best[0]:
                    best = (d, q)
            d, q = best
            rpairs.append(dict(pad=o.tag, net=o.net, other=q.tag, other_net=q.net, same_net=q.net == o.net,
                               mask_web=round(d, 4), copper_gap=round(dist(o.shape, q.shape), 4)))
    log('   8b. new R pad -> nearest other-part pad (mask web / copper gap):')
    for r in rpairs:
        if r['mask_web'] < 0.3:
            log('     %-10s %-9s vs %-9s %-9s web %.3f cu %.3f %s' % (r['pad'], r['net'], r['other'], r['other_net'], r['mask_web'], r['copper_gap'], '' if r['same_net'] else 'DIFFERENT NETS'))
    # 8c: mask cover between new tracks and other-net pad openings (registration margin)
    tcov = []
    for o in objs:
        if o.kind != 'track' or not o.new or o.layer not in ('Top', 'Bottom'):
            continue
        best = None
        for q in sides[o.layer]:
            if q.net == o.net:
                continue
            d = dist(o.shape, grow(q.shape, mask_exp(q)))
            if best is None or d < best[0]:
                best = (d, q.tag, q.net)
        if best and best[0] < 0.1:
            tcov.append(dict(track=o.tag, mask_cover_to_opening=round(best[0], 4), opening=best[1], opening_net=best[2]))
    tcov.sort(key=lambda x: x['mask_cover_to_opening'])
    log('   8c. new tracks whose edge is < 0.10 mm from an other-net pad opening: %d' % len(tcov))
    for t in tcov[:20]:
        log('     ', t)
    out['mask'] = dict(violations=ms, worst=mworst, via_near_new_pads=vip, r_pad_neighbours=rpairs, track_mask_cover=tcov)

    # ---------- 9. silk
    silk = []
    vis = [t for t in B['texts'] if t['layer'] in ('TopOverlay', 'BottomOverlay') and not t['hidden']]
    for o in objs:
        if o.kind == 'pad' and o.new and o.ref and o.ref.startswith('R'):
            side = 'TopOverlay' if o.layer == 'Top' else 'BottomOverlay'
            op = grow(o.shape, mask_exp(o))
            for t in vis:
                if t['layer'] != side:
                    continue
                d = dist(text_box(t), op)
                if d < 0.6:
                    silk.append(dict(pad=o.tag, text=t['text'], at=(t['x'], t['y']), gap_to_opening=round(d, 3), ok=d >= 0.254))
    log('\n-- 9. visible silk within 0.6 mm of a new pad opening: %s' % silk)
    out['silk'] = silk

    # ---------- 10. component clearance, IPC courtyard, TSOP toe keep-out
    side_of = {c['ref']: c['side'] for c in B['components']}
    fp_of = {c['ref']: c['footprint'] for c in B['components']}
    co = B['component_outlines']
    boxes = {}
    for ref, v in co.items():
        if ref == 'X2':
            continue
        bx = [v[k] for k in ('pads', 'Mech3', 'Mech4', 'Mech3(region)', 'Mech4(region)') if k in v]
        if ref == 'U3':
            m = B['u3']['body']['max']
            bx.append([m['x0'], m['y0'], m['x1'], m['y1']])
        if ref == 'U1':
            bx = [v['pads'], [41.4, 6.9, 51.4, 16.9]]
        if bx:
            boxes[ref] = (side_of.get(ref), bx)
    newbox = {}
    for n, pinfo in E['parts'].items():
        ps = [o for o in objs if o.kind == 'pad' and o.ref == pinfo['ref']]
        x0 = min(o.shape[1] - o.shape[3] for o in ps); x1 = max(o.shape[1] + o.shape[3] for o in ps)
        y0 = min(o.shape[2] - o.shape[4] for o in ps); y1 = max(o.shape[2] + o.shape[4] for o in ps)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        horiz = (x1 - x0) > (y1 - y0)
        body = [cx - 0.315, cy - 0.165, cx + 0.315, cy + 0.165] if horiz else [cx - 0.165, cy - 0.315, cx + 0.165, cy + 0.315]   # RC0201 max 0.63 x 0.33
        newbox[pinfo['ref']] = (ps[0].layer, [[x0, y0, x1, y1], body], 'D%d' % n)

    def rr(a, b):
        return d_rect_rect(((a[0] + a[2]) / 2, (a[1] + a[3]) / 2, (a[2] - a[0]) / 2, (a[3] - a[1]) / 2),
                           ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, (b[3] - b[1]) / 2))

    def cy_excess(ref):
        f = fp_of.get(ref, 'R0201')
        if f in ('R0201', 'C0201', 'R0402', 'C0402'):
            return 0.15
        return 0.25
    comp = []
    allb = dict(boxes)
    for r, (s, bx, _) in newbox.items():
        allb[r] = (s, bx)
    for r, (s, bx, net) in newbox.items():
        rows = []
        for r2, (s2, bx2) in allb.items():
            if r2 == r or s2 != s:
                continue
            d = min(rr(a, b) for a in bx for b in bx2)
            if d < 0.6:
                # courtyard = union bbox + IPC-7351B nominal excess (0.15 chip <=0402, 0.25 others)
                ua = [min(a[0] for a in bx), min(a[1] for a in bx), max(a[2] for a in bx), max(a[3] for a in bx)]
                ub = [min(a[0] for a in bx2), min(a[1] for a in bx2), max(a[2] for a in bx2), max(a[3] for a in bx2)]
                ea, eb = 0.15, cy_excess(r2)
                ca = [ua[0] - ea, ua[1] - ea, ua[2] + ea, ua[3] + ea]
                cb = [ub[0] - eb, ub[1] - eb, ub[2] + eb, ub[3] + eb]
                ov = min(ca[2], cb[2]) - max(ca[0], cb[0]), min(ca[3], cb[3]) - max(ca[1], cb[1])
                rows.append(dict(other=r2, gap=round(d, 4), altium_0p254_ok=d >= 0.254 - 1e-6,
                                 courtyard_overlap=bool(ov[0] > 1e-6 and ov[1] > 1e-6), overlap_mm=[round(ov[0], 3), round(ov[1], 3)]))
        rows.sort(key=lambda x: x['gap'])
        # TSOP toe keep-out (U3 lead tips at HE max: pad-field centre +- 5.98)
        tip_lo, tip_hi = B['u3']['pad_field_centre'][1] - 5.98, B['u3']['pad_field_centre'][1] + 5.98
        toe = None
        if s == 'Bottom' and r in [E['parts'][n]['ref'] for n in range(8)]:
            pb, body = bx
            toe = dict(pad_to_U3_pad_toe=round(B['u3']['pad_outer_edges'][0] - pb[3], 4),
                       body_to_lead_tip=round(tip_lo - body[3], 4))
        comp.append(dict(ref=r, net=net, side=s, nearest=rows[:4], toe=toe))
    log('\n-- 10. component clearance (0.254) / IPC-7351B nominal courtyards / TSOP toe:')
    for c in comp:
        log('  %s %-4s %-6s %s  toe=%s' % (c['ref'], c['net'], c['side'], [(x['other'], x['gap'], 'OK' if x['altium_0p254_ok'] else '<0.254',
                                                                          'CY-OVERLAP' if x['courtyard_overlap'] else '') for x in c['nearest'][:3]], c['toe']))
    out['components'] = comp

    # ---------- 11. tombstone: solderable area + attached copper per pad
    tomb = []
    for n, pinfo in sorted(E['parts'].items()):
        ref = pinfo['ref']
        rowp = []
        for pn in ('1', '2'):
            o = [q for q in objs if q.kind == 'pad' and q.ref == ref and q.pad == pn][0]
            op = grow(o.shape, mask_exp(o))
            # raster the opening at 2.5 um and count copper (same net) inside it
            r_ = 0.0025
            x0, y0, x1, y1 = bbox(op)
            xs = np.arange(x0 + r_ / 2, x1, r_); ys = np.arange(y0 + r_ / 2, y1, r_)
            X, Y = np.meshgrid(xs, ys)
            cu = np.zeros_like(X, bool)
            holes = np.zeros_like(X, bool)
            att = []
            for q in objs:
                if q.layer != o.layer or q.net != o.net or dist(q.shape, op) > 0:
                    continue
                if q.kind == 'track':
                    att.append(('track', q.w))
                elif q.kind == 'via':
                    att.append(('via', q.rec.get('kind'), q.tag))
                S = q.shape
                if S[0] == 'R':
                    cu |= (np.abs(X - S[1]) <= S[3]) & (np.abs(Y - S[2]) <= S[4])
                else:
                    dx, dy = S[3] - S[1], S[4] - S[2]
                    L2 = dx * dx + dy * dy
                    t = np.clip(((X - S[1]) * dx + (Y - S[2]) * dy) / L2, 0, 1) if L2 > 0 else 0
                    cu |= np.hypot(X - S[1] - t * dx, Y - S[2] - t * dy) <= S[5]
                if q.kind == 'via':
                    holes |= np.hypot(X - q.xy[0], Y - q.xy[1]) <= q.hole / 2
            sold = int(cu.sum()) * r_ * r_
            hole_open = int(holes.sum()) * r_ * r_
            rowp.append(dict(pad=pn, net=o.net, solderable_mm2=round(sold, 5), via_hole_in_opening_mm2=round(hole_open, 5), attached=att))
        a1, a2 = rowp[0]['solderable_mm2'], rowp[1]['solderable_mm2']
        asym = abs(a1 - a2) / max(a1, a2)
        vipside = [r_['via_hole_in_opening_mm2'] > 0 for r_ in rowp]
        flag = []
        if asym > 0.10:
            flag.append('solderable-area asymmetry %.0f %%' % (100 * asym))
        if vipside[0] != vipside[1]:
            flag.append('via hole in ONE pad opening only')
        if any(vipside):
            flag.append('via-in-pad (needs VIPPO listing)')
        tomb.append(dict(ref=ref, net='D%d' % n, pads=rowp, area_asym=round(asym, 3), flags=flag))
    log('\n-- 11. tombstone / wetting balance per new 0201:')
    for t in tomb:
        log('  %s %-4s pad1 %.4f mm2 (hole %.4f) | pad2 %.4f mm2 (hole %.4f)  asym %.1f %%  %s' % (
            t['ref'], t['net'], t['pads'][0]['solderable_mm2'], t['pads'][0]['via_hole_in_opening_mm2'],
            t['pads'][1]['solderable_mm2'], t['pads'][1]['via_hole_in_opening_mm2'], 100 * t['area_asym'], t['flags']))
        log('        attached: p1 %s | p2 %s' % (t['pads'][0]['attached'], t['pads'][1]['attached']))
    out['tombstone'] = tomb

    # ---------- 12. acid traps (acute copper angles at joints of new tracks, outside pads/via lands)
    acid = []
    newtr = [o for o in objs if o.kind == 'track' and o.new]
    for o in newtr:
        for ex, ey in ((o.shape[1], o.shape[2]), (o.shape[3], o.shape[4])):
            P_ = ('C', ex, ey, ex, ey, 0.0)
            covered = any(q.kind in ('pad', 'via') and q.net == o.net and dist(P_, q.shape) == 0 for q in G.near(o.layer, bbox(P_), 0.01))
            if covered:
                continue
            ox, oy = (o.shape[3], o.shape[4]) if same((ex, ey), (o.shape[1], o.shape[2]), 1e-4) else (o.shape[1], o.shape[2])
            va = (ox - ex, oy - ey)
            for q in G.near(o.layer, bbox(P_), 0.01):
                if q is o or q.kind != 'track' or q.net != o.net:
                    continue
                cands = []
                if same((ex, ey), (q.shape[1], q.shape[2]), 2e-3):
                    cands.append((q.shape[3], q.shape[4]))
                elif same((ex, ey), (q.shape[3], q.shape[4]), 2e-3):
                    cands.append((q.shape[1], q.shape[2]))
                elif d_pt_seg(ex, ey, *q.shape[1:5]) < 1e-3:
                    cands += [(q.shape[1], q.shape[2]), (q.shape[3], q.shape[4])]
                for cx_, cy_ in cands:
                    vb = (cx_ - ex, cy_ - ey)
                    la, lb = math.hypot(*va), math.hypot(*vb)
                    if la < 1e-6 or lb < 1e-6:
                        continue
                    ang = math.degrees(math.acos(max(-1, min(1, (va[0] * vb[0] + va[1] * vb[1]) / la / lb))))
                    if ang < 90 - 0.5:
                        acid.append(dict(at=(round(ex, 4), round(ey, 4)), layer=o.layer, net=o.net, angle=round(ang, 1), a=o.tag, b=q.tag))
    dedup = {}
    for a in acid:
        dedup[(a['at'], a['layer'], a['angle'])] = a
    acid = list(dedup.values())
    log('\n-- 12. acid traps (< 90 deg copper joints outside pads/vias): %d' % len(acid))
    for a in acid:
        log('   ', a)
    out['acid_traps'] = acid

    # ---------- 13. decoupling paths (track length pad -> plane / pad -> cap), before vs after
    def graph(oo):
        Gx = Grid(oo, 0.5)
        node = {}
        adj = collections.defaultdict(list)

        def nid(key):
            if key not in node:
                node[key] = len(node)
            return node[key]
        for k, o in enumerate(oo):
            if o.kind == 'track':
                a = nid(('e', id(o), 0)); b = nid(('e', id(o), 1))
                Lg = math.hypot(o.shape[3] - o.shape[1], o.shape[4] - o.shape[2])
                adj[a].append((b, Lg)); adj[b].append((a, Lg))
            else:
                nid(('o', o.uid))
        for o in oo:
            if o.kind != 'track':
                continue
            for e, (ex, ey) in enumerate(((o.shape[1], o.shape[2]), (o.shape[3], o.shape[4]))):
                me = node[('e', id(o), e)]
                P_ = ('C', ex, ey, ex, ey, o.shape[5])
                for q in Gx.near(o.layer, bbox(P_), 0.01):
                    if q is o or q.net != o.net or dist(P_, q.shape) > 1e-4:
                        continue
                    if q.kind == 'track':
                        for e2, (qx, qy) in enumerate(((q.shape[1], q.shape[2]), (q.shape[3], q.shape[4]))):
                            w_ = math.hypot(qx - ex, qy - ey)
                            o2 = node[('e', id(q), e2)]
                            adj[me].append((o2, w_)); adj[o2].append((me, w_))
                    else:
                        c = node[('o', q.uid)]
                        w_ = math.hypot(q.xy[0] - ex, q.xy[1] - ey)
                        adj[me].append((c, w_)); adj[c].append((me, w_))
        for o in oo:
            if o.kind == 'track':
                continue
            for q in Gx.near(o.layer, bbox(o.shape), 0.01):
                if q is o or q.kind == 'track' or q.net != o.net or q.uid == o.uid or dist(o.shape, q.shape) > 1e-4:
                    continue
                a, b = node[('o', o.uid)], node[('o', q.uid)]
                w_ = math.hypot(q.xy[0] - o.xy[0], q.xy[1] - o.xy[1])
                adj[a].append((b, w_)); adj[b].append((a, w_))
        for o in oo:
            if o.kind != 'track' and o.layer in PLANE and PLANE[o.layer] == o.net:
                c = node[('o', o.uid)]
                pl = nid(('PLANE', o.layer))
                adj[c].append((pl, 0.0)); adj[pl].append((c, 0.0))
        return node, adj

    import heapq

    def dij(node, adj, src):
        D = {src: 0.0}
        h = [(0.0, src)]
        while h:
            d, u = heapq.heappop(h)
            if d > D.get(u, 1e9):
                continue
            for v, w_ in adj[u]:
                nd = d + w_
                if nd < D.get(v, 1e9):
                    D[v] = nd
                    heapq.heappush(h, (nd, v))
        return D
    region = lambda o: (24 < o.xy[0] < 44 and 0 < o.xy[1] < 10) or (o.ref == 'U2' and o.net == 'FT-VCORE')
    dec_nets = ['VCC3V3', 'GND', 'FT-VCORE']
    dec = []
    for tag, oo, pr, pd_ in (('before', before, pads0, None), ('after', objs, pads, None)):
        sub = [o for o in oo if o.net in dec_nets and o.layer in ('Top', 'Bottom', 'L2-GND', 'L5-VCC3V3', 'L3-SIG', 'L4-SIG')]
        node, adj = graph(sub)
        res = {}
        padobjs = [o for o in sub if o.kind == 'pad' and region(o) and o.layer in ('Top', 'Bottom')]
        for o in padobjs:
            D = dij(node, adj, node[('o', o.uid)])
            row = {}
            for L in PLANE:
                if PLANE[L] == o.net and ('PLANE', L) in node:
                    row['to_plane_mm'] = round(D.get(node[('PLANE', L)], float('inf')), 3)
            caps = []
            for q in padobjs:
                if q is o or q.ref == o.ref or not (q.ref.startswith('C')) or q.net != o.net:
                    continue
                dd = D.get(node[('o', q.uid)], float('inf'))
                caps.append((round(dd, 3), q.tag))
            caps.sort()
            row['nearest_caps'] = caps[:2]
            res[o.tag] = row
        dec.append(res)
    chg = []
    for k in sorted(set(dec[0]) | set(dec[1])):
        a, b = dec[0].get(k, {}), dec[1].get(k, {})
        if a != b:
            chg.append(dict(pad=k, before=a, after=b))
    log('\n-- 13. decoupling-path changes (track mm, pads x24..44 y0..10, nets %s):' % dec_nets)
    for c in chg:
        log('   %-12s before %s  ->  after %s' % (c['pad'], c['before'], c['after']))
    out['decoupling'] = chg
    # ---------- 14. STAGGER: hard checks for the new TOP parts (design_top.py rules) + summary
    log('\n\n-- 14. new Top parts: ComponentClearance 0.254 with the 0.90 x 0.396 R0201 body proxy, vs every Top part --')

    def body_proxy(cx, cy, rot):
        return [cx - 0.45, cy - 0.198, cx + 0.45, cy + 0.198] if rot % 180 == 0 else [cx - 0.198, cy - 0.45, cx + 0.198, cy + 0.45]
    top_new = {p['ref']: body_proxy(p['x'], p['y'], p['rot']) for p in E['parts'].values() if p['side'] == 'Top'}
    tops = {}
    for ref, v in co.items():
        if side_of.get(ref) != 'Top' or ref == 'X2':
            continue
        bs = [v[k] for k in v if k == 'pads' or k.startswith('Mech3') or k.startswith('Mech4')]
        if bs:
            tops[ref] = [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]
    pu = co['U1']['pads']
    cxu, cyu = (pu[0] + pu[2]) / 2, (pu[1] + pu[3]) / 2
    tops['U1'] = [min(tops['U1'][0], cxu - 5), min(tops['U1'][1], cyu - 5), max(tops['U1'][2], cxu + 5), max(tops['U1'][3], cyu + 5)]
    for q in B['pads']:
        if q['ref'] == 'X2' and q['layer'] in ('Top', 'Multi'):
            tops['X2-%s' % q['pad']] = [q['x'] - q['w'] / 2, q['y'] - q['h'] / 2, q['x'] + q['w'] / 2, q['y'] + q['h'] / 2]
    tops.update(top_new)
    cc_viol, cc_rows = [], []
    for r, b in sorted(top_new.items()):
        best = min(((rr(b, b2), r2) for r2, b2 in tops.items() if r2 != r), key=lambda x: x[0])
        cc_rows.append(dict(ref=r, nearest=best[1], gap=round(best[0], 4), margin=round(best[0] - 0.254, 4)))
        log('   %s nearest %-8s body gap %.4f (margin %+.4f)' % (r, best[1], best[0], best[0] - 0.254))
        if best[0] < 0.254 - 1e-6:
            cc_viol.append(cc_rows[-1])
    out['top_component_clearance'] = dict(rows=cc_rows, violations=cc_viol)
    nca = set(E.get('net_class_add', {}).get('SDRAM_DATA', []))
    missing_class = sorted({'SDRAM-D%d' % n for n in E['parts']} - nca)
    summ = dict(apply_errors=len(errors), split_ok=all(r['ok'] for r in rename_report.values()),
                further_renames=sum(len(r.get('derived_renames', [])) for r in rename_report.values()),
                new_shorts=len(new_sh), clearance=len(viol), hole_to_hole=len(h2h), width=len(wv), mask=len(ms),
                worse_nets=len(worse), pours_single_island=all(plane_rep[L]['live_islands_after'] == 1 for L in PLANE),
                plane_objects_newly_off_main=sum(len(set(plane_rep[L]['objects_off_main_after']) - set(plane_rep[L]['objects_off_main_before'])) for L in PLANE),
                antennae=len(ant), acid_traps=len(acid), top_component_clearance=len(cc_viol), net_class_missing=missing_class,
                silk_under_0p254=sum(1 for x in silk if not x['ok']))
    summ['PASS'] = (summ['apply_errors'] == 0 and summ['split_ok'] and summ['further_renames'] == 0 and summ['new_shorts'] == 0
                    and summ['clearance'] == 0 and summ['hole_to_hole'] == 0 and summ['width'] == 0 and summ['mask'] == 0
                    and summ['worse_nets'] == 0 and summ['pours_single_island'] and summ['plane_objects_newly_off_main'] == 0
                    and summ['antennae'] == 0 and summ['acid_traps'] == 0 and summ['top_component_clearance'] == 0
                    and not missing_class and summ['silk_under_0p254'] == 0)
    out['summary'] = summ
    log('\n== SUMMARY %s' % summ)
    json.dump(out, open(os.path.join(HERE, 'dfm_check_%s.json' % TAG), 'w'), indent=1, default=str)
    open(os.path.join(HERE, 'dfm_check_%s.log' % TAG), 'w').write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
