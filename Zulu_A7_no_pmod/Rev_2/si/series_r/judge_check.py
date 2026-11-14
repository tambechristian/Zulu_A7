"""Independent re-check of the three series-R placement plans (bottom / top / arrays) and of hybrids.

Judge step of the series-R planning workflow.  Written from scratch: it does NOT import geom.py, plan_check.py,
design_*.py or route_check.py, so it is a second opinion on the designers' numbers.

Input  : board_extract.json (PcbDoc md5 2a616c1c, read by extract.py) + design_bottom.json, design_top.json,
         design_arrays.json (the plans as the designers saved them).
Output : judge_check.json + judge_check.log in this folder.  Nothing else is written.

Rules (Rules6 of the PcbDoc, see board_extract.json rules_summary):
  Clearance 0.09 all; 0.10 when either object is SDRAM_DATA/ADDR/CTRL on L3/L4; 0.20 SDRAM-CLK on L3/L4.
  SDRAM-D0..15 (new) are counted in SDRAM_DATA (the schematic plan adds them to the class).
  Hole-to-hole 0.24 between drills whose layer spans share a layer (stacked microvias on the same xy are exempt).
  Solder-mask sliver 0.10 between pad openings (pad +0.05/side, U1 0.00, X3 0.04); vias tented.
  Width_SDRAM per layer: Top 0.0762-0.15, L3/L4 0.10-0.15, Bottom 0.10-0.15.
  ComponentClearance 0.254 (enabled in Rules6 but NOT processed by the board's batch DRC -- docs/drc_jtag_column.drc
  lists every processed rule and it is absent) -> reported as advisory, with the board's own existing minimum as
  calibration.
  Connectivity: every touched net must be one island (planes L2=GND, L5=VCC3V3 join their vias/pads) and no track
  end may dangle (Net Antennae, tolerance 0).
Geometry: pads are axis-aligned rectangles or circles/stadiums (no rounded-rect pads exist on this board), tracks
are capsules, via lands are circles.  Distances are exact edge-to-edge.
"""
import json, math, os, sys, itertools, collections

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, 'board_extract.json')))
CU = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
LN = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'Top': 'Top', 'Bottom': 'Bottom', 'L2-GND': 'L2-GND',
      'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}
SDRAM = set()
for k in ('SDRAM_DATA', 'SDRAM_ADDR', 'SDRAM_CTRL'):
    SDRAM |= set(B['net_classes'][k])
SDRAM |= {'SDRAM-D%d' % i for i in range(16)}
EPS = 1e-4
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


# ---------------------------------------------------------------- exact geometry
def pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def seg_inter(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-15:
        return False
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
    u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    return 0 <= t <= 1 and 0 <= u <= 1


def seg_seg(a, b):
    if seg_inter(a, b):
        return 0.0
    return min(pt_seg(a[0], a[1], *b), pt_seg(a[2], a[3], *b), pt_seg(b[0], b[1], *a), pt_seg(b[2], b[3], *a))


def pt_rect(px, py, r):
    return math.hypot(max(r[0] - px, 0, px - r[2]), max(r[1] - py, 0, py - r[3]))


def seg_rect(s, r):
    if pt_rect(s[0], s[1], r) == 0 or pt_rect(s[2], s[3], r) == 0:
        return 0.0
    E = [(r[0], r[1], r[2], r[1]), (r[2], r[1], r[2], r[3]), (r[2], r[3], r[0], r[3]), (r[0], r[3], r[0], r[1])]
    return min(seg_seg(s, e) for e in E)


def rect_rect(a, b):
    return math.hypot(max(a[0] - b[2], 0, b[0] - a[2]), max(a[1] - b[3], 0, b[1] - a[3]))


# a shape = ('rect', (x0,y0,x1,y1), 0) | ('cap', (x1,y1,x2,y2), r)  (circle = cap with zero length)
def dist(A, B_):
    ka, ga, ra = A
    kb, gb, rb = B_
    if ka == 'rect' and kb == 'rect':
        return rect_rect(ga, gb)
    if ka == 'rect':
        return max(0.0, seg_rect(gb, ga) - rb)
    if kb == 'rect':
        return max(0.0, seg_rect(ga, gb) - ra)
    return max(0.0, seg_seg(ga, gb) - ra - rb)


def bbox(S):
    k, g, r = S
    if k == 'rect':
        return g
    return (min(g[0], g[2]) - r, min(g[1], g[3]) - r, max(g[0], g[2]) + r, max(g[1], g[3]) + r)


def pad_shape(p, grow=0.0):
    x, y, w, h = p['x'], p['y'], p['w'], p['h']
    if p['shape'] == 'rect':
        return ('rect', (x - w / 2 - grow, y - h / 2 - grow, x + w / 2 + grow, y + h / 2 + grow), 0.0)
    if abs(w - h) < 1e-6:
        return ('cap', (x, y, x, y), w / 2 + grow)
    if w > h:
        return ('cap', (x - (w - h) / 2, y, x + (w - h) / 2, y), h / 2 + grow)
    return ('cap', (x, y - (h - w) / 2, x, y + (h - w) / 2), w / 2 + grow)


# ---------------------------------------------------------------- board model
class Obj:
    __slots__ = ('kind', 'layer', 'net', 'shape', 'rec', 'new', 'tag', 'span', 'hole', 'xy', 'ref')

    def __init__(s, kind, layer, net, shape, rec, new=False, tag='', span=None, hole=0.0, xy=None, ref=None):
        s.kind, s.layer, s.net, s.shape, s.rec, s.new, s.tag = kind, layer, net, shape, rec, new, tag
        s.span, s.hole, s.xy, s.ref = span, hole, xy, ref


def pad_layers(p):
    return CU if p['layer'] == 'Multi' else [p['layer']]


def build_board():
    pads, tracks, vias = [], [], []
    for p in B['pads']:
        pads.append(dict(p))
    for t in B['tracks']:
        if t['layer'] in CU and t.get('polygon', 65535) == 65535:
            tracks.append(dict(t))
    for v in B['vias']:
        vias.append(dict(v))
    return pads, tracks, vias


def same_pt(a, b, tol=2e-3):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def match_track(tracks, rm):
    lay = LN[rm['layer']]
    a, b = (rm['x1'], rm['y1']), (rm['x2'], rm['y2'])
    for i, t in enumerate(tracks):
        if t is None or t['layer'] != lay:
            continue
        if rm.get('net') and t['net'] != rm['net']:
            continue
        p, q = (t['x1'], t['y1']), (t['x2'], t['y2'])
        if (same_pt(a, p) and same_pt(b, q)) or (same_pt(a, q) and same_pt(b, p)):
            return i
    return None


def match_via(vias, rm):
    for i, v in enumerate(vias):
        if v is None:
            continue
        if same_pt((v['x'], v['y']), (rm['x'], rm['y'])) and list(v['span']) == list(rm['span']):
            if rm.get('net') is None or v['net'] == rm['net']:
                return i
    return None


def r0201_pads(ref, p1, p2, side, n1, n2):
    return [dict(ref=ref, pad='1', layer=side, net=n1, x=p1[0], y=p1[1], w=0.30, h=0.30, shape='rect', hole=0.0),
            dict(ref=ref, pad='2', layer=side, net=n2, x=p2[0], y=p2[1], w=0.30, h=0.30, shape='rect', hole=0.0)]


# ---------------------------------------------------------------- plan readers -> uniform edit lists
def plan_bottom(nets=None):
    d = json.load(open(os.path.join(HERE, 'design_bottom.json')))
    E = dict(remove_tracks=[], add_tracks=[], remove_vias=[], add_vias=[], renet_pads=[], add_pads=[],
             rename_tracks=[], rename_vias=[], parts={})
    for pl in d['placements']:
        net = 'D' + pl['ref'][1:] and None
        n = int(pl['ref'][1:]) - 119
        net = 'D%d' % n
        if nets and net not in nets:
            continue
        pin = {0: 2, 1: 4, 2: 5, 3: 7, 4: 8, 5: 10, 6: 11, 7: 13}[n]
        esc = B['d_escapes'][net] if isinstance(B['d_escapes'], dict) else None
        p1 = tuple(pl['pad1_xy'])
        p2 = (2 * pl['x'] - p1[0], 2 * pl['y'] - p1[1])
        E['add_pads'] += r0201_pads(pl['ref'], p1, p2, 'Bottom', 'SDRAM-' + net, net)
        E['renet_pads'].append(dict(ref='U3', pad=str(pin), net='SDRAM-' + net))
        padxy = [p for p in B['pads'] if p['ref'] == 'U3' and p['pad'] == str(pin)][0]
        fv = pl['first_via']
        E['remove_tracks'].append(dict(layer='Bottom', net=net, x1=padxy['x'], y1=padxy['y'], x2=fv[0], y2=fv[1]))
        for pts, nn, w in ((pl['neck_pts'], 'SDRAM-' + net, pl['neck_width']), (pl['return_pts'], net, pl['return_width'])):
            for a, b in zip(pts, pts[1:]):
                E['add_tracks'].append(dict(layer='Bottom', net=nn, x1=a[0], y1=a[1], x2=b[0], y2=b[1], w=w))
        E['parts'][net] = dict(ref=pl['ref'], side='Bottom', x=pl['x'], y=pl['y'], rot=pl['rot'], p1=p1, p2=p2)
    if not nets or 'D0' in nets:
        for rw in d['rework']:
            if rw['name'] == 'CH18':
                E['remove_tracks'].append(dict(layer='Bottom', net='CHAN18', x1=37.55, y1=5.55, x2=37.85, y2=4.10))
                for a, b in (((37.85, 4.1), (37.85, 4.45)), ((37.85, 4.45), (37.55, 4.75)), ((37.55, 4.75), (37.55, 5.55))):
                    E['add_tracks'].append(dict(layer='Bottom', net='CHAN18', x1=a[0], y1=a[1], x2=b[0], y2=b[1], w=0.0762))
    return E


def plan_top(nets=None):
    d = json.load(open(os.path.join(HERE, 'design_top.json')))
    E = dict(remove_tracks=[], add_tracks=[], remove_vias=[], add_vias=[], renet_pads=[], add_pads=[],
             rename_tracks=[], rename_vias=[], parts={})
    for net, p in d['placements'].items():
        if nets and net not in nets:
            continue
        E['add_pads'] += r0201_pads(p['ref'], p['pad_A'], p['pad_B'], 'Top', 'SDRAM-' + net, net)
        for t in p['remove_tracks']:
            E['remove_tracks'].append(dict(t, layer=LN[t['layer']]))
        for t in p['add_tracks']:
            E['add_tracks'].append(dict(t, layer=LN[t['layer']]))
        for v in p['add_vias']:
            E['add_vias'].append(dict(v, kind='micro'))
        rn = p['renamed_to_SDRAM']
        for t in rn['tracks']:
            E['rename_tracks'].append(dict(t, layer=LN[t['layer']], net=net, new='SDRAM-' + net))
        for v in rn['vias']:
            E['rename_vias'].append(dict(v, net=net, new='SDRAM-' + net))
        for pd in rn['pads']:
            r, n = pd.split('-')
            E['renet_pads'].append(dict(ref=r, pad=n, net='SDRAM-' + net))
        E['parts'][net] = dict(ref=p['ref'], side='Top', x=p['x'], y=p['y'], rot=p['rot'], p1=tuple(p['pad_A']),
                               p2=tuple(p['pad_B']))
    return E


def plan_arrays(nets=None):
    d = json.load(open(os.path.join(HERE, 'design_arrays.json')))
    c = d['south_plan']['copper']
    E = dict(remove_tracks=[dict(t, layer=LN[t['layer']]) for t in c['remove_tracks']],
             add_tracks=[dict(t, layer=LN[t['layer']]) for t in c['add_tracks']],
             remove_vias=list(c['remove_vias']), add_vias=list(c['add_vias']), renet_pads=list(c['renet_pads']),
             add_pads=list(c['add_pads']), rename_tracks=[], rename_vias=[], parts={})
    for pl in d['south_plan']['placements']:
        net = pl['nets'].split(' / ')[0]
        E['parts'][net] = dict(ref=pl['ref'], side='Bottom', x=pl['x'], y=pl['y'], rot=pl['rot'],
                               p1=(pl['pad1']['x'], pl['pad1']['y']), p2=(pl['pad2']['x'], pl['pad2']['y']))
    return E


def plan_judge_d9():
    """Judge-added (not in any designer's plan): D9's R on BOTTOM under its own L4 route, near U1, in the Bottom
    placement room [41.56,12.10,43.00,13.62] of board_extract.json free_area.  The L4 diagonal
    (41.75,13.275)-(42.425,12.60) is cut; each R pad carries an L4>L5 + L5>Bottom stacked microvia column (0.30/0.15,
    both via types already on the board).  Everything from U3-44 up to the cut becomes SDRAM-D9."""
    E = dict(remove_tracks=[], add_tracks=[], remove_vias=[], add_vias=[], renet_pads=[], add_pads=[],
             rename_tracks=[], rename_vias=[], parts={})
    p1, p2 = (41.75, 12.95), (42.35, 12.95)
    E['add_pads'] += r0201_pads('R128', p1, p2, 'Bottom', 'SDRAM-D9', 'D9')
    E['remove_tracks'].append(dict(layer='L4-SIG', net='D9', x1=41.75, y1=13.275, x2=42.425, y2=12.6))
    E['add_tracks'].append(dict(layer='L4-SIG', net='SDRAM-D9', x1=41.75, y1=13.275, x2=41.75, y2=12.95, w=0.125))
    E['add_tracks'].append(dict(layer='L4-SIG', net='D9', x1=42.35, y1=12.95, x2=42.425, y2=12.6, w=0.125))
    for (x, y), n in ((p1, 'SDRAM-D9'), (p2, 'D9')):
        E['add_vias'].append(dict(net=n, x=x, y=y, size=0.30, hole=0.15, span=['L4-SIG', 'L5-VCC3V3'], kind='micro'))
        E['add_vias'].append(dict(net=n, x=x, y=y, size=0.30, hole=0.15, span=['L5-VCC3V3', 'Bottom'], kind='micro'))
    E['renet_pads'].append(dict(ref='U3', pad='44', net='SDRAM-D9'))
    for t in B['tracks']:
        if t['net'] != 'D9' or t['layer'] not in ('Bottom', 'L4-SIG'):
            continue
        if same_pt((t['x1'], t['y1']), (41.75, 13.275)) and same_pt((t['x2'], t['y2']), (42.425, 12.6)):
            continue
        if {(round(t['x1'], 2), round(t['y1'], 2)), (round(t['x2'], 2), round(t['y2'], 2))} & {(42.43, 12.6), (43.4, 12.4)}:
            continue        # the U1-side tail stays D9
        E['rename_tracks'].append(dict(layer=t['layer'], net='D9', new='SDRAM-D9', x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in B['vias']:
        if v['net'] == 'D9' and not same_pt((v['x'], v['y']), (43.4001, 12.4)):
            E['rename_vias'].append(dict(x=v['x'], y=v['y'], span=v['span'], net='D9', new='SDRAM-D9'))
    E['parts']['D9'] = dict(ref='R128', side='Bottom', x=42.05, y=12.95, rot=0, p1=p1, p2=p2)
    return E


def merge(*Es):
    M = collections.defaultdict(list)
    parts = {}
    for E in Es:
        for k, v in E.items():
            if k == 'parts':
                parts.update(v)
            else:
                M[k] += v
    M = dict(M)
    M['parts'] = parts
    return M


# ---------------------------------------------------------------- apply + check
def apply(E):
    pads, tracks, vias = build_board()
    errors = []
    changed_tr, changed_v, changed_p = set(), set(), set()
    for rm in E['remove_tracks']:
        i = match_track(tracks, rm)
        if i is None:
            errors.append('unmatched track removal %s' % rm)
        else:
            tracks[i] = None
    for rm in E['remove_vias']:
        i = match_via(vias, rm)
        if i is None:
            errors.append('unmatched via removal %s' % rm)
        else:
            vias[i] = None
    for rn in E['rename_tracks']:
        i = match_track(tracks, rn)
        if i is None:
            # it may have been removed+re-added (trimmed) -- not an error if a removal covered it
            errors.append('rename: track not found (may be a removed one) %s' % rn)
        else:
            tracks[i] = dict(tracks[i], net=rn['new'])
            changed_tr.add(i)
    for rn in E['rename_vias']:
        i = match_via(vias, rn)
        if i is None:
            errors.append('rename: via not found %s' % rn)
        else:
            vias[i] = dict(vias[i], net=rn['new'])
            changed_v.add(i)
    for rp in E['renet_pads']:
        hit = [i for i, p in enumerate(pads) if p['ref'] == rp['ref'] and p['pad'] == rp['pad']]
        if not hit:
            errors.append('renet pad missing %s' % rp)
        for i in hit:
            pads[i] = dict(pads[i], net=rp['net'])
            changed_p.add(i)
    objs = []
    for i, p in enumerate(pads):
        for L in pad_layers(p):
            if p['layer'] != 'Multi' and L != p['layer']:
                continue
            objs.append(Obj('pad', L, p['net'], pad_shape(p), p, new=i in changed_p, tag='pad %s-%s' % (p['ref'], p['pad']),
                            span=pad_layers(p), hole=p.get('hole', 0.0), xy=(p['x'], p['y']), ref=p['ref']))
    for p in E['add_pads']:
        objs.append(Obj('pad', p['layer'], p['net'], pad_shape(p), p, new=True, tag='NEW pad %s-%s' % (p['ref'], p['pad']),
                        span=[p['layer']], xy=(p['x'], p['y']), ref=p['ref']))
    for i, t in enumerate(tracks):
        if t is None:
            continue
        objs.append(Obj('track', t['layer'], t['net'], ('cap', (t['x1'], t['y1'], t['x2'], t['y2']), t['w'] / 2), t,
                        new=i in changed_tr, tag='track %s %s (%.3f,%.3f)-(%.3f,%.3f)' % (t['layer'], t['net'], t['x1'], t['y1'], t['x2'], t['y2'])))
    for t in E['add_tracks']:
        objs.append(Obj('track', t['layer'], t['net'], ('cap', (t['x1'], t['y1'], t['x2'], t['y2']), t['w'] / 2), t, new=True,
                        tag='NEW track %s %s (%.3f,%.3f)-(%.3f,%.3f) w%.4f' % (t['layer'], t['net'], t['x1'], t['y1'], t['x2'], t['y2'], t['w'])))
    allv = [(v, i in changed_v, False) for i, v in enumerate(vias) if v is not None] + [(v, True, True) for v in E['add_vias']]
    for v, ch, isnew in allv:
        for L in v['span']:
            objs.append(Obj('via', L, v['net'], ('cap', (v['x'], v['y'], v['x'], v['y']), v['size'] / 2), v, new=ch,
                            tag='%svia %s (%.3f,%.3f) %s' % ('NEW ' if isnew else '', v['net'], v['x'], v['y'], '>'.join([v['span'][0], v['span'][-1]])),
                            span=v['span'], hole=v['hole'], xy=(v['x'], v['y'])))
    return objs, allv, pads, E, errors


def gap_rule(a, b, L):
    g = 0.09
    if L in ('L3-SIG', 'L4-SIG'):
        if a.net in SDRAM or b.net in SDRAM:
            g = 0.10
        if a.net == 'SDRAM-CLK' or b.net == 'SDRAM-CLK':
            g = 0.20
    return g


def grid_index(objs):
    G = collections.defaultdict(list)
    for o in objs:
        x0, y0, x1, y1 = bbox(o.shape)
        for gx in range(int(math.floor(x0)), int(math.floor(x1)) + 1):
            for gy in range(int(math.floor(y0)), int(math.floor(y1)) + 1):
                G[(o.layer, gx, gy)].append(o)
    return G


def neighbours(G, o, pad=0.5):
    x0, y0, x1, y1 = bbox(o.shape)
    seen = set()
    for gx in range(int(math.floor(x0 - pad)), int(math.floor(x1 + pad)) + 1):
        for gy in range(int(math.floor(y0 - pad)), int(math.floor(y1 + pad)) + 1):
            for q in G.get((o.layer, gx, gy), ()):
                if id(q) not in seen and q is not o:
                    seen.add(id(q))
                    yield q


def mask_open(o):
    """solder-mask opening shape of a pad on Top/Bottom (None for vias: tented)."""
    if o.kind != 'pad' or o.layer not in ('Top', 'Bottom'):
        return None
    e = 0.05
    if o.ref == 'U1':
        e = 0.0
    elif o.ref == 'X3':
        e = 0.04
    return pad_shape(o.rec, grow=e)


def check(objs, allv, E, name):
    G = grid_index(objs)
    viol, worst = [], {}

    def note(rule, val, lim, a, b):
        m = val - lim
        if rule not in worst or m < worst[rule][0]:
            worst[rule] = (round(m, 4), round(val, 4), a, b)
        if m < -1e-6:
            viol.append((rule, round(val, 4), lim, a, b))

    done = set()
    for o in objs:
        if not o.new:
            continue
        for q in neighbours(G, o):
            key = (min(id(o), id(q)), max(id(o), id(q)))
            if key in done:
                continue
            done.add(key)
            if q.net == o.net and o.net not in (None, ''):
                continue
            d = dist(o.shape, q.shape)
            if d > 0.6:
                continue
            note('clearance ' + o.layer, d, gap_rule(o, q, o.layer), o.tag, q.tag)
    # mask sliver (Top/Bottom pads), new/renamed pads against every pad on that side
    pads_side = [o for o in objs if o.kind == 'pad' and o.layer in ('Top', 'Bottom')]
    for o in pads_side:
        if not o.new:
            continue
        mo = mask_open(o)
        for q in pads_side:
            if q is o or q.layer != o.layer:
                continue
            mq = mask_open(q)
            d = dist(mo, mq)
            if d < 0.5 and d > 0:
                note('mask sliver ' + o.layer, d, 0.10, o.tag, q.tag)
            elif d == 0 and q.net != o.net:
                note('mask sliver ' + o.layer, 0.0, 0.10, o.tag, q.tag + ' (openings merge)')
    # hole to hole: new vias against all drills
    drills = []
    for v, ch, isnew in allv:
        drills.append((v['x'], v['y'], v['hole'], v['span'], isnew, 'via %s (%.3f,%.3f) %s>%s' % (v['net'], v['x'], v['y'], v['span'][0], v['span'][-1])))
    for p in B['pads']:
        if p.get('hole', 0) > 0:
            drills.append((p['x'], p['y'], p['hole'], CU, False, 'pad %s-%s' % (p['ref'], p['pad'])))
    for i, a in enumerate(drills):
        if not a[4]:
            continue
        for j, b in enumerate(drills):
            if i == j or (b[4] and j < i):
                continue
            if not set(a[3]) & set(b[3]):
                continue
            if abs(a[0] - b[0]) < 1e-4 and abs(a[1] - b[1]) < 1e-4:
                continue        # stacked (allowed)
            d = math.hypot(a[0] - b[0], a[1] - b[1]) - a[2] / 2 - b[2] / 2
            if d < 1.0:
                note('hole to hole', d, 0.24, a[5], b[5])
    # through-via land inside a new SMD pad's mask opening (board policy used by the top designer) -- advisory
    # width per layer for added D / SDRAM-D tracks
    WL = {'Top': (0.0762, 0.15), 'L3-SIG': (0.10, 0.15), 'L4-SIG': (0.10, 0.15), 'Bottom': (0.10, 0.15)}
    for t in E['add_tracks']:
        if t['net'] in SDRAM and t['layer'] in WL:
            lo, hi = WL[t['layer']]
            if not (lo - 1e-6 <= t['w'] <= hi + 1e-6):
                viol.append(('width', t['w'], WL[t['layer']], t['net'], t['layer']))
    return viol, worst


# ---------------------------------------------------------------- connectivity
def connectivity(objs, nets):
    res = {}
    for net in nets:
        mine = [o for o in objs if o.net == net]
        idx = {id(o): k for k, o in enumerate(mine)}
        par = list(range(len(mine)))

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        def u(a, b):
            par[f(a)] = f(b)
        byL = collections.defaultdict(list)
        for k, o in enumerate(mine):
            byL[o.layer].append(k)
        for L, ks in byL.items():
            for a, b in itertools.combinations(ks, 2):
                if dist(mine[a].shape, mine[b].shape) <= 1e-4:
                    u(a, b)
        # same physical via/through-pad across layers, and stacked microvias at one xy
        byxy = collections.defaultdict(list)
        for k, o in enumerate(mine):
            if o.kind in ('via', 'pad') and o.xy is not None:
                byxy[(round(o.xy[0], 3), round(o.xy[1], 3))].append(k)
        for ks in byxy.values():
            for a in ks[1:]:
                u(ks[0], a)
        # planes
        plane = {'GND': 'L2-GND', 'VCC3V3': 'L5-VCC3V3'}.get(net)
        if plane:
            ks = [k for k, o in enumerate(mine) if o.layer == plane]
            for a in ks[1:]:
                u(ks[0], a)
        pads = [k for k, o in enumerate(mine) if o.kind == 'pad']
        roots = set(f(k) for k in pads)
        # antennae: track ends touching nothing else of the net
        ant = []
        for k, o in enumerate(mine):
            if o.kind != 'track':
                continue
            g = o.shape[1]
            for (ex, ey) in ((g[0], g[1]), (g[2], g[3])):
                ok = False
                for k2, q in enumerate(mine):
                    if k2 == k or q.layer != o.layer:
                        continue
                    if dist(('cap', (ex, ey, ex, ey), 0.0), q.shape) <= 1e-4:
                        ok = True
                        break
                if not ok and o.layer not in (plane,):
                    ant.append('%s end (%.3f,%.3f)' % (o.tag, ex, ey))
        res[net] = dict(pads=len(pads), islands=len(roots), antennae=ant)
    return res


# ---------------------------------------------------------------- component clearance (advisory)
def comp_boxes():
    co = B['component_outlines']
    side = {c['ref']: c['side'] for c in B['components']}
    boxes = {}
    for ref, v in co.items():
        bx = []
        for k in ('pads', 'Mech3', 'Mech4', 'Mech3(region)', 'Mech4(region)'):
            if k in v:
                bx.append(v[k])
        if not bx:
            continue
        if ref == 'U3':
            m = B['u3']['body']['max']
            bx.append([m['x0'], m['y0'], m['x1'], m['y1']])
        if ref == 'U1':
            bx = [[41.4, 6.9, 51.4, 16.9]] + [v['pads']]     # 10 x 10 mm CPG236 body on the ball-field centre
        if ref == 'X2':
            bx = []          # castellated board-edge pins; its outline is the board
        boxes[ref] = (side.get(ref), bx)
    return boxes


def comp_check(E, boxes):
    out = []
    newp = collections.defaultdict(list)
    for p in E['add_pads']:
        newp[p['ref']].append(p)
    newbox = {}
    for ref, ps in newp.items():
        x0 = min(p['x'] - p['w'] / 2 for p in ps); x1 = max(p['x'] + p['w'] / 2 for p in ps)
        y0 = min(p['y'] - p['h'] / 2 for p in ps); y1 = max(p['y'] + p['h'] / 2 for p in ps)
        newbox[ref] = (ps[0]['layer'], [x0, y0, x1, y1])
    for ref, (side, b) in newbox.items():
        best = (9, None)
        for r2, (s2, bx) in list(boxes.items()) + [(k, (s, [bb])) for k, (s, bb) in newbox.items() if k != ref]:
            if s2 != side:
                continue
            for bb in bx:
                d = rect_rect(b, bb)
                if d < best[0]:
                    best = (d, r2)
        out.append((ref, side, round(best[0], 4), best[1]))
    return out


def existing_comp_min(boxes):
    """calibration: the closest pairs of EXISTING same-side parts on this board (same proxy)."""
    refs = [r for r in boxes if boxes[r][1]]
    pairs = []
    for a, b in itertools.combinations(refs, 2):
        if boxes[a][0] != boxes[b][0]:
            continue
        d = min(rect_rect(x, y) for x in boxes[a][1] for y in boxes[b][1])
        pairs.append((round(d, 4), a, b, boxes[a][0]))
    pairs.sort()
    return pairs


# ---------------------------------------------------------------- plane openings (L2/L5) for new vias
def plane_webs(objs):
    out = []
    for L, pnet in (('L2-GND', 'GND'), ('L5-VCC3V3', 'VCC3V3')):
        holes = [o for o in objs if o.layer == L and o.net != pnet and o.kind in ('via', 'pad')]
        for o in holes:
            if not o.new:
                continue
            thru = o.span is not None and len(o.span) == 6
            cl = 0.175 if thru else 0.09
            r = o.shape[2] + cl
            web = 9
            for q in holes:
                if q is o:
                    continue
                if abs(q.xy[0] - o.xy[0]) < 1e-4 and abs(q.xy[1] - o.xy[1]) < 1e-4:
                    continue
                cq = 0.175 if (q.span is not None and len(q.span) == 6) else 0.09
                rq = q.shape[2] + cq
                web = min(web, math.hypot(q.xy[0] - o.xy[0], q.xy[1] - o.xy[1]) - r - rq)
            out.append(dict(layer=L, at=o.tag, opening_d=round(2 * r, 3), min_web=round(web, 3)))
    return out


def run(name, E, boxes):
    objs, allv, pads, E, errors = apply(E)
    viol, worst = check(objs, allv, E, name)
    touched = set()
    for k in ('remove_tracks', 'add_tracks', 'add_vias', 'remove_vias', 'rename_tracks', 'rename_vias'):
        for t in E[k]:
            touched.add(t['net'])
            if 'new' in t:
                touched.add(t['new'])
    for p in E['add_pads'] + E['renet_pads']:
        touched.add(p['net'])
    for p in E['renet_pads']:
        touched.add('D' + str({2: 0, 4: 1, 5: 2, 7: 3, 8: 4, 10: 5, 11: 6, 13: 7, 42: 8, 44: 9, 45: 10, 47: 11, 48: 12, 50: 13, 51: 14, 53: 15}.get(int(p['pad']), '')))
    touched.discard('D')
    conn = connectivity(objs, sorted(touched))
    comp = comp_check(E, boxes)
    webs = plane_webs(objs)
    log('\n==== %s ====' % name)
    log('edits: -%d tracks +%d tracks, -%d vias +%d vias, %d pads renamed, %d new pads, %d tracks/%d vias renamed' % (
        len(E['remove_tracks']), len(E['add_tracks']), len(E['remove_vias']), len(E['add_vias']), len(E['renet_pads']),
        len(E['add_pads']), len(E['rename_tracks']), len(E['rename_vias'])))
    nonD = sorted(n for n in touched if not (n.startswith('D') and n[1:].isdigit()) and not n.startswith('SDRAM-D'))
    log('other nets whose copper changes:', nonD)
    for e in errors:
        log('  APPLY:', e)
    log('violations: %d' % len(viol))
    for v in viol:
        log('  VIOL', v)
    for r, w in sorted(worst.items()):
        log('  worst %-22s margin %+.4f (value %.4f)  %s  vs  %s' % (r, w[0], w[1], w[2], w[3]))
    bad = {n: c for n, c in conn.items() if c['islands'] != 1 or c['antennae']}
    log('connectivity: %d nets checked, %d bad' % (len(conn), len(bad)))
    for n, c in bad.items():
        log('  CONN', n, c)
    for c in comp:
        log('  component gap %s (%s): %.4f mm to %s %s' % (c[0], c[1], c[2], c[3], '(< 0.254 advisory)' if c[2] < 0.254 else ''))
    for w in webs:
        if w['min_web'] < 0.1:
            log('  plane web', w)
    return dict(errors=errors, violations=viol, worst=worst, connectivity=conn, component=comp, plane_webs=webs,
                parts=E['parts'], other_nets=nonD,
                counts=dict(rm_tracks=len(E['remove_tracks']), add_tracks=len(E['add_tracks']), rm_vias=len(E['remove_vias']),
                            add_vias=len(E['add_vias']), renamed_pads=len(E['renet_pads']), new_pads=len(E['add_pads'])))


def baseline_check():
    """calibration: mark every existing copper object in the U3/U2 region as new and check -> must give 0 violations
    (the board is DRC 0), and the closest pair must sit at the rule."""
    E = dict(remove_tracks=[], add_tracks=[], remove_vias=[], add_vias=[], renet_pads=[], add_pads=[], rename_tracks=[],
             rename_vias=[], parts={})
    objs, allv, pads, E, errors = apply(E)
    for o in objs:
        x0, y0, x1, y1 = bbox(o.shape)
        if x0 > 17 and x1 < 50 and y0 > 0.5 and y1 < 24:
            o.new = True
    viol, worst = check(objs, [], E, 'baseline')
    log('==== baseline (existing copper x17..50 treated as new) ====')
    log('violations: %d' % len(viol))
    for v in viol[:20]:
        log('  VIOL', v)
    for r, w in sorted(worst.items()):
        log('  worst %-22s margin %+.4f (value %.4f)  %s  vs  %s' % (r, w[0], w[1], w[2], w[3]))
    return dict(violations=viol, worst=worst)


if __name__ == '__main__':
    boxes = comp_boxes()
    out = {}
    if '--nobase' not in sys.argv:
        out['baseline'] = baseline_check()
    ex = existing_comp_min(boxes)
    log('existing same-side part pairs closer than 0.254 (same proxy): %d; closest 12:' % sum(1 for p in ex if p[0] < 0.254))
    for p in ex[:12]:
        log('  ', p)
    out['existing_comp_pairs_lt_0254'] = [p for p in ex if p[0] < 0.254]
    north_top = ['D8', 'D11', 'D12', 'D15']
    out['bottom'] = run('bottom (design_bottom.json, 4 nets)', plan_bottom(), boxes)
    out['top'] = run('top (design_top.json, 10 nets)', plan_top(), boxes)
    out['arrays'] = run('arrays (design_arrays.json south, 8 nets)', plan_arrays(), boxes)
    out['hybrid_arrays_south+top_north'] = run('HYBRID arrays D0-D7 + top D8/D11/D12/D15',
                                               merge(plan_arrays(), plan_top(north_top)), boxes)
    out['hybrid_arrays_south+top_north_noD15'] = run('HYBRID arrays D0-D7 + top D8/D11/D12',
                                                     merge(plan_arrays(), plan_top(['D8', 'D11', 'D12'])), boxes)
    out['judge_d9_alone'] = run('JUDGE D9 alone (Bottom, under the L4 route near U1)', plan_judge_d9(), boxes)
    out['FINAL'] = run('FINAL = arrays D0-D7 + top D8/D11/D12 + judge D9',
                       merge(plan_arrays(), plan_top(['D8', 'D11', 'D12']), plan_judge_d9()), boxes)
    out['FINAL_plus_D15'] = run('FINAL + top D15 (optional)',
                                merge(plan_arrays(), plan_top(['D8', 'D11', 'D12', 'D15']), plan_judge_d9()), boxes)
    json.dump(out, open(os.path.join(HERE, 'judge_check.json'), 'w'), indent=1, default=str)
    open(os.path.join(HERE, 'judge_check.log'), 'w').write('\n'.join(LOG) + '\n')
