"""design_top.py -- Zulu_a7_no_pmod Rev 2: place the 16 SDRAM DQ series resistors (0201) on the TOP layer.

Approach "top": each DQ leaves U3 (Bottom) through a Bottom stub and a 6-layer through via (the "first via"), then runs
on L3-SIG or L4-SIG to a second through via near U1 and a short Top run to the ball. The resistor goes on Top as close
to U3 (electrically) as Top room allows:

  variant 'F'  (first via reachable on Top): first via -> NEW Top track (0.0762) -> R pad A ; R pad B -> stacked
               microvias (via-in-pad) Top>L2>L3(>L4) -> NEW inner jog -> the existing inner route. The inner route
               from the first via up to the jog point is removed.
  variant 'I'  (inline, both pads via-in-pad): the inner route is cut; pad A's stacked microvias land on the U3-side
               piece (jog track if the pad is off the route), pad B's on the U1-side piece. The removed piece is the
               part of the route between the two jog points.

All geometry comes from si/series_r/board_extract.json (read from the PcbDoc on disk, md5 in its 'source'); the rules
are the PcbDoc's own (Rules6, via board_extract.json 'rules_summary'):
  Clearance 0.09 (all), 0.10 for SDRAM nets on L3/L4 (Clearance_SDRAM_INNER), 0.20 SDRAM-CLK on L3/L4;
  HoleToHole 0.24 (stacked microvias allowed); microvia 0.30/0.15; buried L3-L4 0.27/0.15;
  ComponentClearance 0.254; SolderMaskExpansion +0.05 (U1 0.00, X3 0.04), MinimumSolderMaskSliver 0.10;
  SilkToSolderMask 0.254; Width_SDRAM: Top 0.0762..0.15, L3/L4 0.10..0.15 (pref 0.125).
The new parts are 0201 (board footprint R0201: two 0.30 x 0.30 pads, centres 0.60 apart; body proxy = pads bbox U
the R0201 Mech3 drawing 0.40 x 0.396, i.e. 0.90 x 0.396 mm).

Via-in-pad: the board already has 68 microvia-in-pad sites (VIPPO, user decision 2026-11-11, docs/ltc3556.md);
through vias in SMD pads are banned: every check keeps each through via's land outside the new pads' mask openings.

Writes (only inside si/series_r):
  design_top.json      placements, copper removed/added per net, every clearance margin, electrical positions
  design_top_plan.json the copper edit in the tools/route_check.py plan format (remove / tracks / vias)
  design_top_model.json tools/route/model.json + the 16 resistors' pads, U3-side copper renamed SDRAM-Dn
  design_top.png       plot

    python design_top.py
"""
import json
import math
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REV2 = os.path.dirname(os.path.dirname(HERE))
EX = json.load(open(os.path.join(HERE, 'board_extract.json')))

LAYERS = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
INNER = ('L3-SIG', 'L4-SIG')
SDRAM_CLASSES = {n for k in ('SDRAM_DATA', 'SDRAM_ADDR', 'SDRAM_CTRL') for n in EX['net_classes'][k]}
SDRAM_CLASSES |= {'SDRAM-D%d' % i for i in range(16)}       # schematic_plan.md: the new U3-side nets join SDRAM_DATA
NETS = ['D%d' % i for i in range(16)]

CLEAR = 0.09
CLEAR_SDRAM_INNER = 0.10
CLEAR_CLK_INNER = 0.20
HOLE_HOLE = 0.24
COMP_CLEAR = 0.254
MASK_EXP = 0.05
MASK_SLIVER = 0.10
SILK_MASK = 0.254
EDGE = 0.30                     # tools/route_check.py's board-edge allowance (no Rules6 edge rule exists)
W_TOP = 0.0762
W_INNER = 0.125
PAD = 0.30                      # R0201 pad (square)
PITCH = 0.60                    # R0201 pad centre spacing
R_BODY = (0.90, 0.396)          # R0201 body proxy along / across the part axis
UVIA = (0.30, 0.15)             # Top>L2, L2>L3 microvia
BURIED = (0.27, 0.15)           # L3>L4
JOG_MAX = 0.50                  # longest inner jog from a pad's via to the route
MARGIN_REQ = 0.005             # new copper, holes and bodies keep >= 5 um beyond every rule (Altium rounds
                               # to 0.1 mil = 2.54 um); a trimmed piece of an existing track keeps its own margin
BOARD_W, BOARD_H = 60.96, 25.4

# stack heights (si/spice/fieldsolve.stack_z('fab')): Top 0, L2 0.1365, L3 0.2258, L4 1.306, L5 1.3923, Bottom 1.5118
Z = {'Top': 0.0, 'L2-GND': 0.1365, 'L3-SIG': 0.2258, 'L4-SIG': 1.306, 'L5-VCC3V3': 1.3923, 'Bottom': 1.5118}
# delays from si/spice/lines.json (fab stack, field-solved)
PS_PER_MM = {'Bottom': 6.3025, 'Top': 6.2926, 'L3-SIG': 6.7714, 'L4-SIG': 6.7713}
PS_PER_MM_VIA = 6.77            # ASSUMPTION: barrel delay ~ the inner-layer stripline velocity (eps_eff 4.12)


# ----------------------------------------------------------------------------------------------- geometry primitives
def seg_pt(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - u * dx, py - y1 - u * dy)


def seg_seg(a, b):
    (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = a, b

    def orient(px, py, qx, qy, rx, ry):
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)
    d1 = orient(bx1, by1, bx2, by2, ax1, ay1)
    d2 = orient(bx1, by1, bx2, by2, ax2, ay2)
    d3 = orient(ax1, ay1, ax2, ay2, bx1, by1)
    d4 = orient(ax1, ay1, ax2, ay2, bx2, by2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 * d2 < 0 and d3 * d4 < 0:
        return 0.0
    return min(seg_pt(ax1, ay1, ax2, ay2, bx1, by1), seg_pt(ax1, ay1, ax2, ay2, bx2, by2),
               seg_pt(bx1, by1, bx2, by2, ax1, ay1), seg_pt(bx1, by1, bx2, by2, ax2, ay2))


def rect_seg(r, s):
    """distance between an axis-aligned rectangle (x0,y0,x1,y1) and a segment"""
    x0, y0, x1, y1 = r
    sx1, sy1, sx2, sy2 = s
    if (x0 <= sx1 <= x1 and y0 <= sy1 <= y1) or (x0 <= sx2 <= x1 and y0 <= sy2 <= y1):
        return 0.0
    edges = ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0))
    return min(seg_seg(e, s) for e in edges)


def rect_rect(a, b):
    dx = max(0.0, a[0] - b[2], b[0] - a[2])
    dy = max(0.0, a[1] - b[3], b[1] - a[3])
    return math.hypot(dx, dy)


def gdist(g1, g2):
    """distance between copper shapes: ('s', x1,y1,x2,y2, r) capsule or ('r', x0,y0,x1,y1) rectangle"""
    if g1[0] == 's' and g2[0] == 's':
        return seg_seg(g1[1:5], g2[1:5]) - g1[5] - g2[5]
    if g1[0] == 'r' and g2[0] == 'r':
        return rect_rect(g1[1:5], g2[1:5])
    r, s = (g1, g2) if g1[0] == 'r' else (g2, g1)
    return rect_seg(r[1:5], s[1:5]) - s[5]


def gbox(g):
    if g[0] == 'r':
        return g[1:5]
    r = g[5]
    return (min(g[1], g[3]) - r, min(g[2], g[4]) - r, max(g[1], g[3]) + r, max(g[2], g[4]) + r)


def circle(x, y, d):
    return ('s', x, y, x, y, d / 2)


def rect_c(x, y, w, h):
    return ('r', x - w / 2, y - h / 2, x + w / 2, y + h / 2)


# ----------------------------------------------------------------------------------------------- board objects
class Obj:
    __slots__ = ('kind', 'layer', 'net', 'g', 'ref', 'hole', 'span', 'key', 'mask')

    def __init__(self, kind, layer, net, g, ref=None, hole=0.0, span=None, key=None, mask=None):
        self.kind, self.layer, self.net, self.g, self.ref = kind, layer, net or '', g, ref
        self.hole, self.span, self.key, self.mask = hole, span, key, mask


def pad_geom(p, layer):
    w, h = p['w'], p['h']
    if p['layer'] == 'Multi' and layer not in ('Top', 'Bottom'):
        w, h = p['size_mid']
    if p['shape'] == 'round':
        if abs(w - h) < 1e-6:
            return circle(p['x'], p['y'], w)
        if w > h:
            return ('s', p['x'] - (w - h) / 2, p['y'], p['x'] + (w - h) / 2, p['y'], h / 2)
        return ('s', p['x'], p['y'] - (h - w) / 2, p['x'], p['y'] + (h - w) / 2, w / 2)
    return rect_c(p['x'], p['y'], w, h)


def mask_exp(ref):
    return {'U1': 0.0, 'X3': 0.04}.get(ref, MASK_EXP)


def build_objects():
    objs = []
    for i, p in enumerate(EX['pads']):
        ls = LAYERS if p['layer'] == 'Multi' else [p['layer']]
        for L in ls:
            g = pad_geom(p, L)
            m = None
            if L in ('Top', 'Bottom'):
                e = mask_exp(p['ref'])
                m = ('r', g[1] - e, g[2] - e, g[3] + e, g[4] + e) if g[0] == 'r' else \
                    ('s', g[1], g[2], g[3], g[4], g[5] + e)
            objs.append(Obj('pad', L, p['net'], g, ref='%s-%s' % (p['ref'], p['pad']), hole=p.get('hole') or 0.0,
                            key=('p', i), mask=m))
    for i, t in enumerate(EX['tracks']):
        if t['layer'] in LAYERS:
            objs.append(Obj('track', t['layer'], t['net'], ('s', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2),
                            key=('t', i)))
    for i, v in enumerate(EX['vias']):
        for L in v['span']:
            objs.append(Obj('via', L, v['net'], circle(v['x'], v['y'], v['size']), hole=v['hole'], span=v['span'],
                            key=('v', i)))
    return objs


class Index:
    def __init__(self, objs, cell=0.5):
        self.cell = cell
        self.b = defaultdict(list)
        for o in objs:
            self.add(o)

    def add(self, o):
        x0, y0, x1, y1 = gbox(o.g)
        c = self.cell
        for i in range(int(math.floor(x0 / c)), int(math.floor(x1 / c)) + 1):
            for j in range(int(math.floor(y0 / c)), int(math.floor(y1 / c)) + 1):
                self.b[(o.layer, i, j)].append(o)

    def near(self, layer, box, pad):
        c = self.cell
        seen = set()
        for i in range(int(math.floor((box[0] - pad) / c)), int(math.floor((box[2] + pad) / c)) + 1):
            for j in range(int(math.floor((box[1] - pad) / c)), int(math.floor((box[3] + pad) / c)) + 1):
                for o in self.b.get((layer, i, j), ()):
                    if id(o) not in seen:
                        seen.add(id(o))
                        yield o


def clearance(n1, n2, layer):
    if layer in INNER:
        if 'SDRAM-CLK' in (n1, n2):
            return CLEAR_CLK_INNER
        if n1 in SDRAM_CLASSES or n2 in SDRAM_CLASSES:
            return CLEAR_SDRAM_INNER
    return CLEAR


# ----------------------------------------------------------------------------------------------- part bodies, silk
def comp_proxies():
    """Top-side body proxies: bbox of the part's pads + Mech3/Mech4 drawings (the same proxy phase 1 used);
    X2 by its pads only (its outline is the whole board). U1 also gets its 10 x 10 mm datasheet body centred on the
    ball field (its PcbDoc owns no Mech3/4 drawing)."""
    out = {}
    side = {c['ref']: c['side'] for c in EX['components']}
    for ref, o in EX['component_outlines'].items():
        if side.get(ref) != 'Top':
            continue
        keys = ['pads'] if ref == 'X2' else [k for k in o if k == 'pads' or k.startswith('Mech3') or k.startswith('Mech4')]
        bs = [o[k] for k in keys if k in o]
        if ref == 'X2':
            continue                              # handled pad-by-pad below (its pads ring the board)
        if not bs:
            continue
        out[ref] = [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]
    if 'U1' in out:
        p = EX['component_outlines']['U1']['pads']
        cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        b = out['U1']
        out['U1'] = [min(b[0], cx - 5.0), min(b[1], cy - 5.0), max(b[2], cx + 5.0), max(b[3], cy + 5.0)]
    x2 = [p for p in EX['pads'] if p['ref'] == 'X2' and p['layer'] in ('Top', 'Multi')]
    for p in x2:
        out['X2-%s' % p['pad']] = [p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2]
    return out


def courtyards():
    """secondary report only: Mech7 boxes (EAGLE-import courtyard/outline layer) of Top parts"""
    side = {c['ref']: c['side'] for c in EX['components']}
    return {r: o['Mech7'] for r, o in EX['component_outlines'].items() if side.get(r) == 'Top' and 'Mech7' in o}


def silk_boxes():
    """visible Top Overlay texts. Stroke-font width = 0.955 x height per character: MEASURED from the Fab B Rev 2 top
    overlay Gerber (zulu_a7_fab_b.GTO, aperture D11 0.18 mm: 'ZULU A7 2.2' at 1.3 mm spans x 37.70..51.35, 11 chars);
    ASSUMED the same for the other texts. Anchor = lower-left, rotation about the anchor; + half the stroke.
    The free title (37.7, 5.0) is 'ZULU A7 2.3' (tools/NoPmod_Title23.pas); the extract's text field lost 'ZUL'."""
    out = []
    for t in EX['texts']:
        if t['layer'] != 'TopOverlay' or t['hidden']:
            continue
        txt = t['text']
        if txt.endswith('A7 2.3') and t['comp'] is None:
            txt = 'ZULU A7 2.3'
        w = 0.955 * t['height'] * len(txt)
        h = t['height']
        s = t['stroke'] / 2
        r = round(t['rot']) % 360
        x, y = t['x'], t['y']
        if r == 0:
            b = [x, y, x + w, y + h]
        elif r == 90:
            b = [x - h, y, x, y + w]
        elif r == 180:
            b = [x - w, y - h, x, y]
        else:
            b = [x, y - w, x + h, y]
        out.append({'text': txt, 'comp': t['comp'], 'box': [b[0] - s, b[1] - s, b[2] + s, b[3] + s]})
    return out


# ----------------------------------------------------------------------------------------------- the DQ routes
def _match_track(net, o):
    hits = [i for i, t in enumerate(EX['tracks']) if t['net'] == net and t['layer'] == o['layer'] and
            abs(t['w'] - o['w']) < 0.002 and
            ({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} ==
             {(round(o['x1'], 3), round(o['y1'], 3)), (round(o['x2'], 3), round(o['y2'], 3))})]
    assert len(hits) >= 1, (net, o)
    return hits


def _match_via(net, o):
    hits = [i for i, v in enumerate(EX['vias']) if v['net'] == net and abs(v['x'] - o['x']) < 0.002 and
            abs(v['y'] - o['y']) < 0.002]
    assert len(hits) == 1, (net, o, hits)
    return hits[0]


def route_of(net):
    """the net's path U3 pad -> U1 ball as a chain of oriented tracks and vias with global arc positions g0/g1,
    grouped into same-layer sections. The tiny jog joints of D4/D12 (listed by the extract as branches) are part of
    the chain."""
    e = EX['d_escapes'][net]
    path = e['path']
    chain = []
    cur = (path[0]['x'], path[0]['y'])
    g = 0.0
    br = list(e['branches_off_path'])
    for o in path[1:-1]:
        if o['kind'] == 'via':
            chain.append(dict(kind='via', x=o['x'], y=o['y'], span=o['span'], size=o['size'], hole=o['hole'],
                              g0=g, g1=g, vix=_match_via(net, o)))
            cur = (o['x'], o['y'])
            continue
        a, b = (o['x1'], o['y1']), (o['x2'], o['y2'])
        if math.hypot(a[0] - cur[0], a[1] - cur[1]) > math.hypot(b[0] - cur[0], b[1] - cur[1]):
            a, b = b, a
        if math.hypot(a[0] - cur[0], a[1] - cur[1]) > 1e-3:
            bt = [t for t in br if t['layer'] == o['layer'] and
                  min(math.hypot(t['x1'] - cur[0], t['y1'] - cur[1]), math.hypot(t['x2'] - cur[0], t['y2'] - cur[1])) < 1e-3]
            assert bt, (net, a, cur)
            bt = bt[0]
            L = math.hypot(a[0] - cur[0], a[1] - cur[1])
            chain.append(dict(kind='track', layer=bt['layer'], w=bt['w'], x1=cur[0], y1=cur[1], x2=a[0], y2=a[1],
                              g0=g, g1=g + L, tix=_match_track(net, bt)))
            g += L
            cur = a
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        chain.append(dict(kind='track', layer=o['layer'], w=o['w'], x1=a[0], y1=a[1], x2=b[0], y2=b[1], g0=g, g1=g + L,
                          tix=_match_track(net, o)))
        g += L
        cur = b
    secs = []
    for c in chain:
        if c['kind'] != 'track':
            continue
        if secs and secs[-1]['layer'] == c['layer'] and abs(secs[-1]['segs'][-1]['g1'] - c['g0']) < 1e-9 and \
                math.hypot(secs[-1]['segs'][-1]['x2'] - c['x1'], secs[-1]['segs'][-1]['y2'] - c['y1']) < 1e-6:
            secs[-1]['segs'].append(c)
        else:
            secs.append(dict(layer=c['layer'], segs=[c]))
    vias = [c for c in chain if c['kind'] == 'via']
    F, S = vias[0], vias[-1]
    inner = [s for s in secs if s['layer'] in INNER]
    top = [s for s in secs if s['layer'] == 'Top' and s['segs'][0]['g0'] >= S['g0'] - 1e-9]
    assert len(inner) == 1 and len(top) == 1, (net, [s['layer'] for s in secs])
    return dict(net=net, layer=inner[0]['layer'], F=F, S=S, chain=chain, secs={'inner': inner[0], 'top': top[0]},
                stub=e['bottom_stub_length'], e=e, length=g)


def project(sec, x, y):
    best = None
    for k, s in enumerate(sec['segs']):
        dx, dy = s['x2'] - s['x1'], s['y2'] - s['y1']
        L2 = dx * dx + dy * dy
        u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - s['x1']) * dx + (y - s['y1']) * dy) / L2))
        qx, qy = s['x1'] + u * dx, s['y1'] + u * dy
        d = math.hypot(x - qx, y - qy)
        if best is None or d < best[0] - 1e-9:
            best = (d, s['g0'] + u * math.sqrt(L2), qx, qy, k)
    return best


def point_at(sec, g):
    for s in sec['segs']:
        if s['g0'] - 1e-9 <= g <= s['g1'] + 1e-9:
            L = s['g1'] - s['g0']
            u = 0.0 if L == 0 else (g - s['g0']) / L
            return s['x1'] + u * (s['x2'] - s['x1']), s['y1'] + u * (s['y2'] - s['y1'])
    s = sec['segs'][-1]
    return s['x2'], s['y2']


def cut_section(sec, gA, gB):
    removed, keepA, keepB = [], [], []
    for s in sec['segs']:
        if s['g1'] <= gA + 1e-9 or s['g0'] >= gB - 1e-9:
            continue
        removed.append(s)
        if s['g0'] < gA - 1e-6:
            x, y = point_at(sec, gA)
            keepA.append(dict(layer=s['layer'], w=s['w'], x1=s['x1'], y1=s['y1'], x2=x, y2=y, keep=True))
        if s['g1'] > gB + 1e-6:
            x, y = point_at(sec, gB)
            keepB.append(dict(layer=s['layer'], w=s['w'], x1=x, y1=y, x2=s['x2'], y2=s['y2'], keep=True))
    return removed, keepA, keepB


# ----------------------------------------------------------------------------------------------- candidate build + check
def via_stack(layer):
    st = [('Top', 'L2-GND', UVIA), ('L2-GND', 'L3-SIG', UVIA)]
    if layer == 'L4-SIG':
        st.append(('L3-SIG', 'L4-SIG', BURIED))
    return st


def stack_objs(x, y, layer, net):
    out = []
    for a, b, (size, hole) in via_stack(layer):
        sp = LAYERS[LAYERS.index(a):LAYERS.index(b) + 1]
        for L in sp:
            out.append(Obj('via', L, net, circle(x, y, size), hole=hole, span=sp, key=('new', a, b)))
    return out


def body_rect(cx, cy, rot):
    a, c = R_BODY
    return [cx - a / 2, cy - c / 2, cx + a / 2, cy + c / 2] if rot % 180 == 0 else \
        [cx - c / 2, cy - a / 2, cx + c / 2, cy + a / 2]


class Board:
    def __init__(self, movable_silk=()):
        self.objs = build_objects()
        self.idx = Index(self.objs)
        self.proxies = comp_proxies()
        self.court = courtyards()
        self.silk_all = silk_boxes()
        self.silk = [s for s in self.silk_all if s['text'] not in movable_silk]
        self.routes = {n: route_of(n) for n in NETS}
        self.placed = []
        self.placed_bodies = []
        self.tix_pos = {}
        self.vix_pos = {}
        for n, R in self.routes.items():
            for c in R['chain']:
                if c['kind'] == 'track':
                    for i in c['tix']:
                        self.tix_pos[i] = (c['g0'], c['g1'])
                else:
                    self.vix_pos[c['vix']] = c['g0']

    def candidate(self, net, cx, cy, rot, variant):
        R = self.routes[net]
        ux, uy = (1.0, 0.0) if rot % 180 == 0 else (0.0, 1.0)
        p1 = (cx - ux * PITCH / 2, cy - uy * PITCH / 2)
        p2 = (cx + ux * PITCH / 2, cy + uy * PITCH / 2)
        sec = R['secs']['top' if variant == 'T' else 'inner']
        L = sec['layer']
        F = R['F']
        jogw = W_TOP if L == 'Top' else W_INNER
        if variant in ('I', 'T'):
            j1, j2 = project(sec, *p1), project(sec, *p2)
            if j1[1] > j2[1]:
                p1, p2, j1, j2 = p2, p1, j2, j1
            if j1[0] > JOG_MAX or j2[0] > JOG_MAX or j2[1] - j1[1] < 0.15:
                return None
            gA, gB = j1[1], j2[1]
        else:
            if math.hypot(p2[0] - F['x'], p2[1] - F['y']) < math.hypot(p1[0] - F['x'], p1[1] - F['y']):
                p1, p2 = p2, p1
            j2 = project(sec, *p2)
            if j2[0] > JOG_MAX:
                return None
            gA, gB = F['g0'], j2[1]
            j1 = None
        A, B = 'SDRAM-' + net, net
        new = []
        padA = Obj('rpad', 'Top', A, rect_c(p1[0], p1[1], PAD, PAD), ref='new R pad A')
        padB = Obj('rpad', 'Top', B, rect_c(p2[0], p2[1], PAD, PAD), ref='new R pad B')
        for pd in (padA, padB):
            g = pd.g
            pd.mask = ('r', g[1] - MASK_EXP, g[2] - MASK_EXP, g[3] + MASK_EXP, g[4] + MASK_EXP)
        new += [padA, padB]
        tracks_add, vias_add = [], []
        if variant == 'I':
            new += stack_objs(p1[0], p1[1], L, A)
            vias_add.append((p1[0], p1[1], A))
            new += stack_objs(p2[0], p2[1], L, B)
            vias_add.append((p2[0], p2[1], B))
        elif variant == 'F':
            new.append(Obj('track', 'Top', A, ('s', F['x'], F['y'], p1[0], p1[1], W_TOP / 2)))
            tracks_add.append(dict(net=A, layer='Top', w=W_TOP, x1=F['x'], y1=F['y'], x2=p1[0], y2=p1[1]))
            new += stack_objs(p2[0], p2[1], L, B)
            vias_add.append((p2[0], p2[1], B))
        removed, keepA, keepB = cut_section(sec, gA, gB)
        for kt in keepA:
            new.append(Obj('track', L, A, ('s', kt['x1'], kt['y1'], kt['x2'], kt['y2'], kt['w'] / 2), ref='keep'))
            tracks_add.append(dict(net=A, **kt))
        for kt in keepB:
            new.append(Obj('track', L, B, ('s', kt['x1'], kt['y1'], kt['x2'], kt['y2'], kt['w'] / 2), ref='keep'))
            tracks_add.append(dict(net=B, **kt))
        if j1 is not None and j1[0] > 1e-4:
            new.append(Obj('track', L, A, ('s', p1[0], p1[1], j1[2], j1[3], jogw / 2)))
            tracks_add.append(dict(net=A, layer=L, w=jogw, x1=p1[0], y1=p1[1], x2=j1[2], y2=j1[3]))
        if j2[0] > 1e-4:
            new.append(Obj('track', L, B, ('s', p2[0], p2[1], j2[2], j2[3], jogw / 2)))
            tracks_add.append(dict(net=B, layer=L, w=jogw, x1=p2[0], y1=p2[1], x2=j2[2], y2=j2[3]))
        return dict(net=net, variant=variant, cx=cx, cy=cy, rot=rot, p1=p1, p2=p2, gA=gA, gB=gB, j1=j1, j2=j2,
                    new=new, removed=removed, tracks_add=tracks_add, vias_add=vias_add, layer=L)

    def label(self, net, o, cand):
        """net of an existing object after the cut; None = removed. U3-side copper of Dn becomes SDRAM-Dn."""
        if o.net != net:
            return o.net
        A, B = 'SDRAM-' + net, net
        gA, gB = cand['gA'], cand['gB']
        if o.kind == 'track' and o.key[0] == 't':
            pos = self.tix_pos.get(o.key[1])
            if pos is None:
                return B
            if pos[1] <= gA + 1e-9:
                return A
            if pos[0] >= gB - 1e-9:
                return B
            return None
        if o.kind == 'via':
            g = self.vix_pos.get(o.key[1])
            if g is None:
                return B
            return A if g <= gA + 1e-9 else B
        if o.kind == 'pad':
            return A if o.ref.startswith('U3-') else B
        return B

    def check(self, cand, full=False, others=True):
        net = cand['net']
        removed_ids = {i for sg in cand['removed'] for i in sg['tix']}
        worst, viol = {}, []

        def note(rule, margin, what, req=MARGIN_REQ):
            if rule not in worst or margin < worst[rule][0]:
                worst[rule] = (round(margin, 4), what)
            if margin < req - 1e-6:
                viol.append('%s %.4f %s' % (rule, margin, what))
                return not full
            return False

        br = body_rect(cand['cx'], cand['cy'], cand['rot'])
        for ref, b in self.proxies.items():
            if note('component_clearance', rect_rect(br, b) - COMP_CLEAR, ref):
                return False, worst, viol
        if others:
            for ref, b in self.placed_bodies:
                if note('component_clearance', rect_rect(br, b) - COMP_CLEAR, ref):
                    return False, worst, viol
        if note('edge', min(br[0], br[1], BOARD_W - br[2], BOARD_H - br[3]) - EDGE, 'board edge'):
            return False, worst, viol
        new = cand['new']
        for o in new:
            for e in self.idx.near(o.layer, gbox(o.g), 0.6):
                if e.kind == 'track' and e.key[0] == 't' and e.key[1] in removed_ids:
                    continue
                en = self.label(net, e, cand)
                if en is None:
                    continue
                if en != o.net or not en:
                    d = gdist(o.g, e.g)
                    if note('clearance_%s' % o.layer, d - clearance(o.net, en, o.layer),
                            '%s %s vs %s %s %s' % (o.kind, o.net, e.kind, en, e.ref or ''),
                            0.0 if o.ref == 'keep' else MARGIN_REQ):
                        return False, worst, viol
                if o.kind == 'rpad' and e.kind == 'pad' and e.mask is not None:
                    if note('mask_sliver', gdist(o.mask, e.mask) - MASK_SLIVER, 'vs %s' % e.ref):
                        return False, worst, viol
                if o.kind == 'rpad' and e.kind == 'via' and len(e.span or []) == 6:
                    # board policy (docs/ltc3556.md, 2026-11-11): no through via in an SMD pad -- its land stays
                    # outside the pad's mask opening
                    if note('thru_via_in_pad', gdist(o.mask, e.g), 'through via %s at %.3f,%.3f' % (en, e.g[1], e.g[2]), 0.0):
                        return False, worst, viol
                if o.kind == 'via' and e.hole > 0 and e.kind in ('via', 'pad'):
                    if e.kind == 'via' and not (set(o.span) & set(e.span)):
                        continue
                    dc = math.hypot(e.g[1] - o.g[1], e.g[2] - o.g[2])
                    if dc < 1e-6:
                        continue
                    if note('hole_to_hole', dc - o.hole / 2 - e.hole / 2 - HOLE_HOLE, '%s vs %s %s' % (o.net, e.kind, en)):
                        return False, worst, viol
            if others:
                for e in self.placed:
                    if e.layer != o.layer:
                        continue
                    if e.net != o.net:
                        if note('clearance_%s' % o.layer, gdist(o.g, e.g) - clearance(o.net, e.net, o.layer),
                                '%s %s vs new %s %s' % (o.kind, o.net, e.kind, e.net)):
                            return False, worst, viol
                    if o.kind == 'rpad' and e.kind == 'rpad':
                        if note('mask_sliver', gdist(o.mask, e.mask) - MASK_SLIVER, 'vs new pad %s' % e.net):
                            return False, worst, viol
                    if o.kind == 'via' and e.kind == 'via' and (set(o.span) & set(e.span)):
                        dc = math.hypot(e.g[1] - o.g[1], e.g[2] - o.g[2])
                        if dc > 1e-6 and note('hole_to_hole', dc - o.hole / 2 - e.hole / 2 - HOLE_HOLE, 'vs new via %s' % e.net):
                            return False, worst, viol
            if o.kind == 'rpad':
                for s in self.silk:
                    if note('silk_to_mask', rect_rect(o.mask[1:5], s['box']) - SILK_MASK, 'silk %r' % s['text']):
                        return False, worst, viol
        for i in range(len(new)):
            for j in range(i + 1, len(new)):
                a, b = new[i], new[j]
                if a.layer != b.layer:
                    continue
                if a.net != b.net:
                    if note('clearance_%s' % a.layer, gdist(a.g, b.g) - clearance(a.net, b.net, a.layer),
                            'own A/B %s %s' % (a.kind, b.kind), 0.0 if (a.ref == 'keep' and b.ref == 'keep') else MARGIN_REQ):
                        return False, worst, viol
                if a.kind == 'via' and b.kind == 'via':
                    dc = math.hypot(a.g[1] - b.g[1], a.g[2] - b.g[2])
                    if dc > 1e-6 and note('hole_to_hole', dc - a.hole / 2 - b.hole / 2 - HOLE_HOLE, 'own vias'):
                        return False, worst, viol
        return (not viol), worst, viol

    def column_sites(self, net, reach=1.0, step=0.05):
        """points near the inner route where a stacked microvia column Top>L2>L3(>L4) is legal on every layer it
        touches (the net's own copper ignored; the full check of a candidate covers it)"""
        R = self.routes[net]
        sec = R['secs']['inner']
        L = sec['layer']
        xs = [p for s in sec['segs'] for p in (s['x1'], s['x2'])]
        ys = [p for s in sec['segs'] for p in (s['y1'], s['y2'])]
        own = {net, 'SDRAM-' + net}
        out = []
        for x in frange(round((min(xs) - reach) / step) * step, max(xs) + reach, step):
            for y in frange(round((min(ys) - reach) / step) * step, max(ys) + reach, step):
                j = project(sec, x, y)
                if j[0] > reach:
                    continue
                ok = True
                for o in stack_objs(x, y, L, 'SDRAM-' + net):
                    for e in self.idx.near(o.layer, gbox(o.g), 0.6):
                        if e.net in own:
                            continue
                        if gdist(o.g, e.g) < clearance('SDRAM-' + net, e.net, o.layer) - 1e-6:
                            ok = False
                            break
                        if e.hole > 0 and (e.kind == 'pad' or set(o.span) & set(e.span or [])):
                            dc = math.hypot(e.g[1] - o.g[1], e.g[2] - o.g[2])
                            if dc > 1e-6 and dc - o.hole / 2 - e.hole / 2 < HOLE_HOLE - 1e-6:
                                ok = False
                                break
                    if not ok:
                        break
                if ok and any(b[0] < x < b[2] and b[1] < y < b[3] for b in self.proxies.values()):
                    ok = False                          # under a Top part body: no Top track could reach it
                if ok:
                    out.append((round(x, 4), round(y, 4), j))
        return out

    def candidate_col(self, net, s1, s2, cx, cy, rot):
        """variant 'C': pad A <- Top track <- column s1 <- inner jog <- route (U3 side); pad B -> Top track -> column s2
        -> inner jog -> route (U1 side). s1 None = variant 'FC': pad A <- Top track <- the first via F."""
        R = self.routes[net]
        sec = R['secs']['inner']
        L = sec['layer']
        F = R['F']
        ux, uy = (1.0, 0.0) if rot % 180 == 0 else (0.0, 1.0)
        p1 = (cx - ux * PITCH / 2, cy - uy * PITCH / 2)
        p2 = (cx + ux * PITCH / 2, cy + uy * PITCH / 2)
        a_pt = (F['x'], F['y']) if s1 is None else s1[:2]
        if math.hypot(p2[0] - a_pt[0], p2[1] - a_pt[1]) < math.hypot(p1[0] - a_pt[0], p1[1] - a_pt[1]):
            p1, p2 = p2, p1
        j2 = s2[2]
        if s1 is None:
            gA, j1 = F['g0'], None
        else:
            j1 = s1[2]
            gA = j1[1]
        gB = j2[1]
        if gB - gA < 0.15:
            return None
        A, B = 'SDRAM-' + net, net
        new, tracks_add, vias_add = [], [], []
        padA = Obj('rpad', 'Top', A, rect_c(p1[0], p1[1], PAD, PAD), ref='new R pad A')
        padB = Obj('rpad', 'Top', B, rect_c(p2[0], p2[1], PAD, PAD), ref='new R pad B')
        for pd in (padA, padB):
            g = pd.g
            pd.mask = ('r', g[1] - MASK_EXP, g[2] - MASK_EXP, g[3] + MASK_EXP, g[4] + MASK_EXP)
        new += [padA, padB]

        def toptrack(net_, a, b):
            if math.hypot(a[0] - b[0], a[1] - b[1]) > 1e-4:
                new.append(Obj('track', 'Top', net_, ('s', a[0], a[1], b[0], b[1], W_TOP / 2)))
                tracks_add.append(dict(net=net_, layer='Top', w=W_TOP, x1=a[0], y1=a[1], x2=b[0], y2=b[1]))

        def injog(net_, a, j):
            if j[0] > 1e-4:
                new.append(Obj('track', L, net_, ('s', a[0], a[1], j[2], j[3], W_INNER / 2)))
                tracks_add.append(dict(net=net_, layer=L, w=W_INNER, x1=a[0], y1=a[1], x2=j[2], y2=j[3]))
        toptrack(A, a_pt, p1)
        toptrack(B, s2[:2], p2)
        if s1 is not None:
            new += stack_objs(s1[0], s1[1], L, A)
            vias_add.append((s1[0], s1[1], A))
            injog(A, s1[:2], j1)
        new += stack_objs(s2[0], s2[1], L, B)
        vias_add.append((s2[0], s2[1], B))
        injog(B, s2[:2], j2)
        removed, keepA, keepB = cut_section(sec, gA, gB)
        for kt in keepA:
            new.append(Obj('track', L, A, ('s', kt['x1'], kt['y1'], kt['x2'], kt['y2'], kt['w'] / 2), ref='keep'))
            tracks_add.append(dict(net=A, **kt))
        for kt in keepB:
            new.append(Obj('track', L, B, ('s', kt['x1'], kt['y1'], kt['x2'], kt['y2'], kt['w'] / 2), ref='keep'))
            tracks_add.append(dict(net=B, **kt))
        return dict(net=net, variant='FC' if s1 is None else 'C', cx=cx, cy=cy, rot=rot, p1=p1, p2=p2, gA=gA, gB=gB,
                    j1=j1, j2=j2, s1=s1, s2=s2, new=new, removed=removed, tracks_add=tracks_add, vias_add=vias_add,
                    layer=L)

    def accept(self, cand):
        self.placed += cand['new']
        self.placed_bodies.append(('R(%s)' % cand['net'], body_rect(cand['cx'], cand['cy'], cand['rot'])))


# ----------------------------------------------------------------------------------------------- electrical position
def electrical(R, cand):
    """U3 pin -> the R's U3-side pad: copper along the chain up to the cut + via barrels + the final jog/stack"""
    v = cand['variant']
    L = R['layer']
    gA = cand['gA']
    parts = defaultdict(float)
    ps = 0.0
    for c in R['chain']:
        if c['kind'] == 'track':
            a, b = c['g0'], min(c['g1'], gA)
            if b > a:
                parts[c['layer']] += b - a
                ps += (b - a) * PS_PER_MM[c['layer']]
    # barrels: F (Bottom -> inner, or Bottom -> Top for variant F), S (inner -> Top) when the cut is beyond S
    if v in ('F', 'FC'):
        parts['via F barrel Bottom->Top'] = Z['Bottom'] - Z['Top']
        topt = math.hypot(cand['p1'][0] - R['F']['x'], cand['p1'][1] - R['F']['y'])
        parts['Top track F->R'] = topt
        ps += (Z['Bottom'] - Z['Top']) * PS_PER_MM_VIA + topt * PS_PER_MM['Top']
    else:
        parts['via F barrel Bottom->%s' % L] = Z['Bottom'] - Z[L]
        ps += (Z['Bottom'] - Z[L]) * PS_PER_MM_VIA
        if v == 'T':
            parts['via S barrel %s->Top' % L] = Z[L] - Z['Top']
            ps += (Z[L] - Z['Top']) * PS_PER_MM_VIA
            parts['Top jog'] = cand['j1'][0]
            ps += cand['j1'][0] * PS_PER_MM['Top']
        else:
            parts['inner jog'] = cand['j1'][0]
            ps += cand['j1'][0] * PS_PER_MM[L]
            parts['microvia stack %s->Top' % L] = Z[L] - Z['Top']
            ps += (Z[L] - Z['Top']) * PS_PER_MM_VIA
            if v == 'C':
                topt = math.hypot(cand['p1'][0] - cand['s1'][0], cand['p1'][1] - cand['s1'][1])
                parts['Top track column->R'] = topt
                ps += topt * PS_PER_MM['Top']
    mm = sum(parts.values())
    return dict(mm=round(mm, 3), ps=round(ps, 1), parts={k: round(x, 3) for k, x in parts.items()})


# ----------------------------------------------------------------------------------------------- search
def frange(a, b, st):
    n = int(math.floor((b - a) / st + 1e-9))
    return [a + i * st for i in range(n + 1)]


def cand_key(c):
    return (c['elec']['ps'], (c['j1'][0] if c['j1'] else 0.0) + c['j2'][0])


def search(board, net, step=0.05, variants=('F', 'I', 'T')):
    R = board.routes[net]
    out = []
    m = JOG_MAX + 0.35
    for variant in variants:
        sec = R['secs']['top' if variant == 'T' else 'inner']
        if variant == 'F':
            fx, fy = R['F']['x'], R['F']['y']
            bx = (fx - 1.6, fy - 1.6, fx + 1.6, fy + 1.6)
        else:
            xs = [p for s in sec['segs'] for p in (s['x1'], s['x2'])]
            ys = [p for s in sec['segs'] for p in (s['y1'], s['y2'])]
            bx = (min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m)
        for x in frange(round(bx[0] / step) * step, bx[2], step):
            for y in frange(round(bx[1] / step) * step, bx[3], step):
                if variant != 'F' and project(sec, x, y)[0] > m:
                    continue
                for rot in (0, 90):
                    c = board.candidate(net, round(x, 4), round(y, 4), rot, variant)
                    if c is None:
                        continue
                    ok, worst, viol = board.check(c, others=False)
                    if ok:
                        c['elec'] = electrical(R, c)
                        c['worst'] = worst
                        out.append(c)
    out.sort(key=cand_key)
    return out


def search_col(board, net, max_pair=2.5, r_reach=0.9, step=0.05, site_step=0.1, cap=400, log=None, tmax=300.0):
    """variants C / FC: R anywhere Top-legal near two column sites (or the first via + one site)"""
    R = board.routes[net]
    sites = board.column_sites(net, step=site_step)
    F = R['F']
    f_top = not any(b[0] < F['x'] < b[2] and b[1] < F['y'] < b[3] for b in board.proxies.values())
    ends = [None] if f_top else []
    pairs = []
    for s2 in sites:
        for s1 in ends + sites:
            a = (F['x'], F['y']) if s1 is None else s1[:2]
            d = math.hypot(a[0] - s2[0], a[1] - s2[1])
            ga = F['g0'] if s1 is None else s1[2][1]
            if s2[2][1] - ga < 0.15 or d > max_pair or (s1 is not None and d < 0.40):
                continue
            pairs.append((d, s1, s2))
    pairs.sort(key=lambda q: q[0])
    if log:
        log('  %s: %d column sites, F on Top: %s, %d site pairs' % (net, len(sites), f_top, len(pairs)))
    out = []
    t0 = time.time()
    for d, s1, s2 in pairs:
        if time.time() - t0 > tmax:
            if log:
                log('  %s: column search stopped at the %.0f s budget' % (net, tmax))
            break
        a = (F['x'], F['y']) if s1 is None else s1[:2]
        x0, x1 = min(a[0], s2[0]) - r_reach, max(a[0], s2[0]) + r_reach
        y0, y1 = min(a[1], s2[1]) - r_reach, max(a[1], s2[1]) + r_reach
        for x in frange(round(x0 / step) * step, x1, step):
            for y in frange(round(y0 / step) * step, y1, step):
                for rot in (0, 90):
                    br = body_rect(x, y, rot)
                    if any(rect_rect(br, pb) < COMP_CLEAR for pb in board.proxies.values()):
                        continue
                    if any(rect_rect(br, b) < COMP_CLEAR for _, b in board.placed_bodies):
                        continue
                    c = board.candidate_col(net, s1, s2, round(x, 4), round(y, 4), rot)
                    if c is None:
                        continue
                    ok, worst, viol = board.check(c)
                    if ok:
                        c['elec'] = electrical(R, c)
                        c['worst'] = worst
                        out.append(c)
        if len(out) > cap:
            break
    out.sort(key=lambda c: c['elec']['ps'])
    return out


def polish(board, c0, step=0.0125, span=0.05, ps_slack=3.0):
    """around a chosen placement: the legal position (fine grid) with the largest worst margin within ps_slack"""
    best, bm = c0, min(v[0] for v in c0['worst'].values())
    for dx in frange(-span, span, step):
        for dy in frange(-span, span, step):
            c = board.candidate(c0['net'], round(c0['cx'] + dx, 4), round(c0['cy'] + dy, 4), c0['rot'], c0['variant'])
            if c is None:
                continue
            ok, worst, viol = board.check(c)
            if not ok:
                continue
            c['elec'] = electrical(board.routes[c0['net']], c)
            if c['elec']['ps'] > c0['elec']['ps'] + ps_slack:
                continue
            c['worst'] = worst
            m = min(v[0] for v in worst.values())
            if m > bm + 1e-4:
                best, bm = c, m
    return best


# ======================================================================================================================
# model-format plan (tools/route/model.json conventions), router stage, exact verification
# ======================================================================================================================
import copy  # noqa: E402

import numpy as np  # noqa: E402

TOOLS = os.path.join(REV2, 'tools')
sys.path.insert(0, TOOLS)
import route_conn as RC  # noqa: E402
import router as RT  # noqa: E402

MODEL_PATH = os.path.join(TOOLS, 'route', 'model.json')
MSTACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
RT.SDRAM |= {'SDRAM-D%d' % i for i in range(16)}       # the router's SDRAM width/clearance rules cover the new nets
REFS = {'D%d' % i: 'R%d' % (119 + i) for i in range(16)}   # schematic_plan.md: R119 = D0 ... R134 = D15


def lm(L):
    return {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}.get(L, L)


def le(L):
    return {'Top Layer': 'Top', 'Bottom Layer': 'Bottom'}.get(L, L)


def tsame(t, o, tol=0.002):
    a = abs(t['x1'] - o['x1']) < tol and abs(t['y1'] - o['y1']) < tol and abs(t['x2'] - o['x2']) < tol and abs(t['y2'] - o['y2']) < tol
    b = abs(t['x1'] - o['x2']) < tol and abs(t['y1'] - o['y2']) < tol and abs(t['x2'] - o['x1']) < tol and abs(t['y2'] - o['y1']) < tol
    return a or b


def model_track_index(M0, net, ext):
    hits = [i for i, t in enumerate(M0['tracks']) if t['net'] == net and t['layer'] == lm(ext['layer']) and
            abs(t['w'] - ext['w']) < 0.002 and tsame(t, ext)]
    assert hits, (net, ext)
    return hits


def model_via_index(M0, net, x, y):
    hits = [i for i, v in enumerate(M0['vias']) if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002]
    assert len(hits) == 1, (net, x, y, hits)
    return hits[0]


def stack_vias(x, y, layer, net):
    out = []
    for a, b, (size, hole) in via_stack(le(layer)):
        out.append(dict(net=net, x=round(x, 4), y=round(y, 4), size=size, hole=hole,
                        span=MSTACK[MSTACK.index(lm(a)):MSTACK.index(lm(b)) + 1]))
    return out


def rot_and_center(pA, pB):
    cx, cy = (pA[0] + pB[0]) / 2, (pA[1] + pB[1]) / 2
    if abs(pA[1] - pB[1]) < 1e-6:
        rot = 0 if pA[0] < cx else 180
    else:
        rot = 90 if pA[1] < cy else 270
    return round(cx, 4), round(cy, 4), rot


def rpads(net, pA, pB):
    ref = REFS[net]
    mk = lambda pad, p, n: {'ref': ref, 'pad': pad, 'net': n, 'x': round(p[0], 4), 'y': round(p[1], 4), 'shape': 'rect',
                            'w': PAD, 'h': PAD, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False}
    return [mk('1', pA, 'SDRAM-' + net), mk('2', pB, net)]


def renames_for(board, M0, net, gA):
    """model objects of net Dn that end up on U3's side of the resistor (renamed SDRAM-Dn)"""
    R = board.routes[net]
    out = {'tracks': [], 'vias': [], 'pads': []}
    for c in R['chain']:
        if c['kind'] == 'track' and c['g1'] <= gA + 1e-9:
            out['tracks'] += model_track_index(M0, net, EX['tracks'][c['tix'][0]])
        if c['kind'] == 'via' and c['g0'] <= gA + 1e-9:
            out['vias'].append(model_via_index(M0, net, c['x'], c['y']))
    u3 = [i for i, p in enumerate(M0['pads']) if p['net'] == net and p['ref'] == 'U3']
    assert len(u3) == 1
    out['pads'] = u3
    out['tracks'] = sorted(set(out['tracks']))
    return out


def entry_from_candidate(board, M0, c):
    """an EX-based candidate (variants F / I / T) as a model-format plan entry"""
    net = c['net']
    rem = sorted({i for sg in c['removed'] for i in model_track_index(M0, net, EX['tracks'][sg['tix'][0]])})
    tracks = [dict(net=t['net'], layer=lm(t['layer']), w=t['w'], x1=round(t['x1'], 4), y1=round(t['y1'], 4),
                   x2=round(t['x2'], 4), y2=round(t['y2'], 4), **({'keep': True} if t.get('keep') else {}))
              for t in c['tracks_add']]
    vias = []
    for x, y, n in c['vias_add']:
        vias += stack_vias(x, y, lm(c['layer']), n)
    cx, cy, rot = rot_and_center(c['p1'], c['p2'])
    return dict(net=net, ref=REFS[net], variant=c['variant'], center=(cx, cy), rot=rot, pad_A=list(c['p1']),
                pad_B=list(c['p2']), remove_idx=rem, tracks=tracks, vias=vias, pads=rpads(net, c['p1'], c['p2']),
                renames=renames_for(board, M0, net, c['gA']), gA=c['gA'], gB=c['gB'], section=c['layer'])


def apply_plan(M0, entries):
    """M0 + every entry: renames, removals, additions (returns a new model; M0 untouched)"""
    M = copy.deepcopy(M0)
    kill = set()
    for e in entries:
        for i in e['renames']['tracks']:
            M['tracks'][i]['net'] = 'SDRAM-' + e['net']
        for i in e['renames']['vias']:
            M['vias'][i]['net'] = 'SDRAM-' + e['net']
        for i in e['renames']['pads']:
            M['pads'][i]['net'] = 'SDRAM-' + e['net']
        kill |= set(e['remove_idx'])
    M['tracks'] = [t for i, t in enumerate(M['tracks']) if i not in kill]
    for e in entries:
        M['tracks'] += [dict(t) for t in e['tracks']]
        M['vias'] += [dict(v) for v in e['vias']]
        M['pads'] += [dict(p) for p in e['pads']]
    return M


def model_objects(M, tag_new=None):
    """Obj list for a model; objects whose identity is in tag_new get key ('new', ...)"""
    objs = []
    for i, p in enumerate(M['pads']):
        ls = p['layers'] or (MSTACK if p['drill'] > 0 else [])
        for L in ls:
            g = circle(p['x'], p['y'], min(p['w'], p['h'])) if RC.pad_round(p) else rect_c(p['x'], p['y'], p['w'], p['h'])
            m = None
            if L in ('Top Layer', 'Bottom Layer'):
                e = mask_exp(p['ref'])
                m = ('r', g[1] - e, g[2] - e, g[3] + e, g[4] + e) if g[0] == 'r' else ('s', g[1], g[2], g[3], g[4], g[5] + e)
            objs.append(Obj('pad', L, p['net'], g, ref='%s-%s' % (p['ref'], p['pad']), hole=p['drill'], key=('p', i), mask=m))
    for i, t in enumerate(M['tracks']):
        objs.append(Obj('track', t['layer'], t['net'], ('s', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), key=('t', i),
                        ref='keep' if t.get('keep') else None))
    for i, v in enumerate(M['vias']):
        for L in v['span']:
            objs.append(Obj('via', L, v['net'], circle(v['x'], v['y'], v['size']), hole=v['hole'], span=v['span'],
                            key=('v', i)))
    return objs


def mclear(n1, n2, layer):
    return clearance(n1, n2, layer)


def check_objects(new, idx, skip, bodies, silk, proxies, worst=None, viol=None):
    """exact check of new copper objects against the index (all other copper) and among themselves.
    skip(e) -> True for index objects that are the new objects themselves."""
    worst = {} if worst is None else worst
    viol = [] if viol is None else viol

    def note(rule, margin, what, req=MARGIN_REQ):
        if rule not in worst or margin < worst[rule][0]:
            worst[rule] = (round(margin, 4), what)
        if margin < req - 1e-6:
            viol.append('%s %.4f %s' % (rule, margin, what))
    for o in new:
        for e in idx.near(o.layer, gbox(o.g), 0.6):
            if skip(e):
                continue
            if e.net != o.net or not e.net:
                note('clearance %s' % o.layer, gdist(o.g, e.g) - mclear(o.net, e.net, o.layer),
                     '%s %s vs %s %s %s' % (o.kind, o.net, e.kind, e.net, e.ref or ''),
                     0.0 if o.ref == 'keep' else MARGIN_REQ)
            if o.mask is not None and e.mask is not None and e.kind == 'pad':
                note('mask sliver', gdist(o.mask, e.mask) - MASK_SLIVER, '%s vs %s' % (o.ref, e.ref))
            if o.kind == 'pad' and o.mask is not None and e.kind == 'via' and len(e.span) == 6:
                note('through via in SMD pad', gdist(o.mask, e.g), '%s vs through via %s' % (o.ref, e.net), 0.0)
            if o.kind == 'via' and e.hole > 0:
                if e.kind == 'via' and not (set(o.span) & set(e.span)):
                    continue
                dc = math.hypot(e.g[1] - o.g[1], e.g[2] - o.g[2])
                if dc > 1e-6:
                    note('hole to hole', dc - o.hole / 2 - e.hole / 2 - HOLE_HOLE, '%s vs %s %s' % (o.net, e.kind, e.net))
    for i in range(len(new)):
        for j in range(i + 1, len(new)):
            a, b = new[i], new[j]
            if a.layer != b.layer:
                continue
            if a.net != b.net:
                note('clearance %s' % a.layer, gdist(a.g, b.g) - mclear(a.net, b.net, a.layer),
                     'new %s %s vs new %s %s' % (a.kind, a.net, b.kind, b.net),
                     0.0 if (a.ref == 'keep' and b.ref == 'keep') else MARGIN_REQ)
            if a.mask is not None and b.mask is not None:
                note('mask sliver', gdist(a.mask, b.mask) - MASK_SLIVER, '%s vs %s' % (a.ref, b.ref))
            if a.kind == 'via' and b.kind == 'via' and (set(a.span) & set(b.span)):
                dc = math.hypot(a.g[1] - b.g[1], a.g[2] - b.g[2])
                if dc > 1e-6:
                    note('hole to hole', dc - a.hole / 2 - b.hole / 2 - HOLE_HOLE, 'new vias %s %s' % (a.net, b.net))
    for o in new:
        if o.kind == 'pad' and o.mask is not None and o.layer == 'Top Layer':
            for s in silk:
                note('silk to mask', rect_rect(gbox(o.mask), s['box']) - SILK_MASK, '%s vs silk %r' % (o.ref, s['text']))
    for ref, br in bodies:
        for pref, pb in proxies.items():
            note('component clearance', rect_rect(br, pb) - COMP_CLEAR, '%s vs %s' % (ref, pref))
        note('edge', min(br[0], br[1], BOARD_W - br[2], BOARD_H - br[3]) - EDGE, '%s board edge' % ref)
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            note('component clearance', rect_rect(bodies[i][1], bodies[j][1]) - COMP_CLEAR,
                 '%s vs %s' % (bodies[i][0], bodies[j][0]))
    return worst, viol


def entry_body(e):
    return (e['ref'], body_rect(e['center'][0], e['center'][1], e['rot']))


def entry_new_objects(M, nstart):
    """objects of the model created by the plan: pads/tracks/vias at index >= nstart[kind]"""
    out = []
    for o in model_objects(M):
        k, i = o.key
        if i >= nstart[k]:
            out.append(o)
    return out


# ----------------------------------------------------------------------------------------------- router stage
def cut_model_entry(board, M0, net, secname, gA, gB):
    """a plan entry that only cuts the route between gA and gB (renames U3 side); pads/copper come later"""
    R = board.routes[net]
    sec = R['secs'][secname]
    removed, keepA, keepB = cut_section(sec, gA, gB)
    rem = sorted({i for sg in removed for i in model_track_index(M0, net, EX['tracks'][sg['tix'][0]])})
    tracks = [dict(net='SDRAM-' + net, layer=lm(t['layer']), w=t['w'], x1=round(t['x1'], 4), y1=round(t['y1'], 4),
                   x2=round(t['x2'], 4), y2=round(t['y2'], 4)) for t in keepA]
    tracks += [dict(net=net, layer=lm(t['layer']), w=t['w'], x1=round(t['x1'], 4), y1=round(t['y1'], 4),
                    x2=round(t['x2'], 4), y2=round(t['y2'], 4)) for t in keepB]
    eA, eB = point_at(sec, gA), point_at(sec, gB)
    return dict(net=net, ref=REFS[net], variant='R', remove_idx=rem, tracks=tracks, vias=[], pads=[],
                renames=renames_for(board, M0, net, gA), gA=gA, gB=gB, section=sec['layer'], endA=eA, endB=eB)


def disk_mask(win, x, y, r):
    i0, i1, j0, j1 = win
    yy, xx = np.mgrid[i0:i1, j0:j1]
    return (xx * RT.G - x) ** 2 + (yy * RT.G - y) ** 2 <= r * r


def pad_mask(win, p):
    i0, i1, j0, j1 = win
    yy, xx = np.mgrid[i0:i1, j0:j1]
    X, Y = xx * RT.G, yy * RT.G
    return (abs(X - p['x']) <= p['w'] / 2 * 0.8) & (abs(Y - p['y']) <= p['h'] / 2 * 0.8)


def r_positions_all(idx, net, R, bodies, silk, proxies, reach=3.0, step=0.05):
    """Top-legal 0201 positions within `reach` of the net's route (inner or Top sections): pads, body, mask, silk.
    Copper of the net itself (either side) is ignored here; the exact check after routing covers it."""
    own = {net, 'SDRAM-' + net}
    pts = [(s['x1'], s['y1']) for sec in R['secs'].values() for s in sec['segs']] +           [(s['x2'], s['y2']) for sec in R['secs'].values() for s in sec['segs']]
    x0, x1 = min(p[0] for p in pts) - reach, max(p[0] for p in pts) + reach
    y0, y1 = min(p[1] for p in pts) - reach, max(p[1] for p in pts) + reach
    out = []
    for x in frange(round(x0 / step) * step, x1, step):
        for y in frange(round(y0 / step) * step, y1, step):
            if min(project(sec, x, y)[0] for sec in R['secs'].values()) > reach:
                continue
            for rot in (0, 90):
                br = body_rect(x, y, rot)
                if any(rect_rect(br, pb) < COMP_CLEAR for pb in proxies.values()):
                    continue
                if any(rect_rect(br, b) < COMP_CLEAR for _, b in bodies):
                    continue
                if min(br[0], br[1], BOARD_W - br[2], BOARD_H - br[3]) < EDGE:
                    continue
                ux, uy = (0.3, 0.0) if rot == 0 else (0.0, 0.3)
                ok = True
                for px, py in ((x - ux, y - uy), (x + ux, y + uy)):
                    g = rect_c(px, py, PAD, PAD)
                    m = ('r', g[1] - MASK_EXP, g[2] - MASK_EXP, g[3] + MASK_EXP, g[4] + MASK_EXP)
                    for e in idx.near('Top Layer', gbox(g), 0.5):
                        if e.net in own:
                            continue
                        if gdist(g, e.g) < CLEAR - 1e-6 or (e.mask is not None and gdist(m, e.mask) < MASK_SLIVER - 1e-6):
                            ok = False
                            break
                    if ok and any(rect_rect(gbox(m), s['box']) < SILK_MASK for s in silk):
                        ok = False
                    if not ok:
                        break
                if ok:
                    out.append((round(x, 4), round(y, 4), rot))
    return out


def path_len(tracks, vias):
    L = sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in tracks)
    Z2 = {lm(k): v for k, v in Z.items()}
    V = sum(Z2[v['span'][-1]] - Z2[v['span'][0]] for v in vias)
    return L, V


STATS = defaultdict(int)


def router_stage(board, M0, entries, net, silk, proxies, max_r=3.0, n_try=40, h=0.3, log=print):
    """place the R anywhere Top-legal near a cut of the route and let tools/router.py connect both sides"""
    R = board.routes[net]
    tries = []
    for secname in ('inner', 'top'):
        sec = R['secs'][secname]
        g0, g1 = sec['segs'][0]['g0'], sec['segs'][-1]['g1']
        g = g0 + h + 0.05
        while g + h < g1 - 0.05:
            tries.append((secname, g))
            g += 0.5
    bodies = [entry_body(e) for e in entries]
    M1 = apply_plan(M0, entries)
    allpos = r_positions_all(Index(model_objects(M1)), net, R, bodies, silk, proxies, reach=max_r)
    log('  %s: %d Top-legal R positions within %.1f mm of the route' % (net, len(allpos), max_r))
    for secname, gc in tries:
        cut = cut_model_entry(board, M0, net, secname, gc - h, gc + h)
        Mc = apply_plan(M0, entries + [cut])
        cpt = point_at(R['secs'][secname], gc)
        pos = []
        for x, y, rot in allpos:
            d = math.hypot(x - cpt[0], y - cpt[1])
            if d <= max_r:
                ux, uy = (0.3, 0.0) if rot == 0 else (0.0, 0.3)
                a, b = (x - ux, y - uy), (x + ux, y + uy)
                eA = cut['endA']
                if math.hypot(b[0] - eA[0], b[1] - eA[1]) < math.hypot(a[0] - eA[0], a[1] - eA[1]):
                    a, b = b, a
                pos.append((d, x, y, rot, a, b))
        pos.sort()
        if not pos:
            continue
        B = RT.Board(Mc)
        Rt = RT.Router(B, 200000)
        tried = 0
        for d, x, y, rot, pA, pB in pos:
            if tried >= n_try:
                break
            tried += 1
            pads = rpads(net, pA, pB)
            saved = {l: a.copy() for l, a in B.r.items()}
            nv = len(B.vias)
            for p in pads:
                B.add_pad(p)
            eA, eB = cut['endA'], cut['endB']
            box = (min(eA[0], eB[0], x) - 0.5, min(eA[1], eB[1], y) - 0.5, max(eA[0], eB[0], x) + 0.5,
                   max(eA[1], eB[1], y) + 0.5)
            win = RT.window(B, [box], 1.5)
            Lc = lm(R['secs'][secname]['layer'])
            ok = True
            t0, v0 = len(Rt.out_t), len(Rt.out_v)
            for n_, src, dst in (('SDRAM-' + net, {Lc: disk_mask(win, eA[0], eA[1], 0.04)}, {'Top Layer': pad_mask(win, pads[0])}),
                                 (net, {'Top Layer': pad_mask(win, pads[1])}, {Lc: disk_mask(win, eB[0], eB[1], 0.04)})):
                r = Rt.route(n_, src, dst, win)
                if not r:
                    STATS['noroute ' + ('A' if n_.startswith('SDRAM') else 'B') + ' ' + Rt.why] += 1
                    ok = False
                    break
                Rt.commit(n_, *r)
            if ok:
                ntr = [dict(t, layer=t['layer']) for t in Rt.out_t[t0:]]
                nvi = [dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'],
                            span=MSTACK[MSTACK.index(v['from']):MSTACK.index(v['to']) + 1]) for v in Rt.out_v[v0:]]
                cx, cy, rr = rot_and_center(pA, pB)
                e = dict(cut, center=(cx, cy), rot=rr, pad_A=list(pA), pad_B=list(pB), pads=pads,
                         tracks=cut['tracks'] + ntr, vias=nvi)
                Mx = apply_plan(M0, entries + [e])
                nstart = {'p': len(Mx['pads']) - 2, 't': len(Mx['tracks']) - len(e['tracks']), 'v': len(Mx['vias']) - len(nvi)}
                new = entry_new_objects(Mx, nstart)
                idx2 = Index(model_objects(Mx))
                news = {(o.key, o.layer) for o in new}
                worst, viol = check_objects(new, idx2, lambda q: (q.key, q.layer) in news, bodies + [entry_body(e)], silk, proxies)
                isl = RC.islands(Mx)
                opens = {k: v for k, v in RC.open_count(isl).items() if v}
                if viol:
                    STATS['exact: ' + viol[0].split(' vs ')[0][:60]] += 1
                    if STATS['shown'] < 6:
                        STATS['shown'] += 1
                        log('    reject %s' % viol[:3])
                if opens:
                    STATS['opens'] += 1
                if not viol and not opens:
                    log('  %s: R at (%.3f, %.3f) rot %d, cut %s g %.2f, %d tracks %d vias' % (
                        net, cx, cy, rr, secname, gc, len(ntr), len(nvi)))
                    e['worst'] = worst
                    return e
                ok = False
            B.r = saved
            del B.vias[nv:]
            del Rt.out_t[t0:]
            del Rt.out_v[v0:]
    return None


# ======================================================================================================================
# selection, verification, outputs
# ======================================================================================================================
MOVABLE_SILK = ('ZULU A7 2.3', 'U1')     # the free title and U1's designator may move (see 'moved_parts')
CACHE = os.path.join(HERE, 'design_top_candidates.json')
SOUTH = ['D%d' % i for i in range(8)]
NORTH = ['D%d' % i for i in range(8, 16)]


def cand_params(c):
    p = dict(variant=c['variant'], cx=c['cx'], cy=c['cy'], rot=c['rot'], ps=c['elec']['ps'])
    if c['variant'] in ('C', 'FC'):
        p['s1'] = list(c['s1'][:2]) if c['s1'] else None
        p['s2'] = list(c['s2'][:2])
    return p


def rebuild(board, net, p):
    if p['variant'] in ('C', 'FC'):
        sec = board.routes[net]['secs']['inner']
        s1 = None if p['s1'] is None else (p['s1'][0], p['s1'][1], project(sec, *p['s1']))
        s2 = (p['s2'][0], p['s2'][1], project(sec, *p['s2']))
        c = board.candidate_col(net, s1, s2, p['cx'], p['cy'], p['rot'])
    else:
        c = board.candidate(net, p['cx'], p['cy'], p['rot'], p['variant'])
    ok, worst, viol = board.check(c, others=False)
    c['elec'] = electrical(board.routes[net], c)
    c['worst'] = worst
    c['ok_alone'] = ok
    return c


def all_candidates(board, fresh=False, log=print):
    if not fresh and os.path.exists(CACHE):
        P = json.load(open(CACHE))
        log('candidates from %s (delete it or pass --fresh to search again)' % os.path.basename(CACHE))
        return {n: [rebuild(board, n, p) for p in P[n]] for n in NETS}
    out = {}
    for n in NETS:
        t = time.time()
        cs = search(board, n)
        cs += search_col(board, n, max_pair=2.2, cap=300, log=log)
        cs.sort(key=lambda c: c['elec']['ps'])
        # de-duplicate near-identical placements, keep the electrically closest of each
        keep, seen = [], set()
        for c in cs:
            k = (c['variant'], round(c['cx'] / 0.1), round(c['cy'] / 0.1), c['rot'],
                 tuple(c['s1'][:2]) if c.get('s1') else None, tuple(c['s2'][:2]) if c.get('s2') else None)
            if k in seen:
                continue
            seen.add(k)
            keep.append(c)
        out[n] = keep[:150]
        log('%-4s %-6s %4d legal placements alone (%d kept), best %s  [%.0f s]' % (
            n, board.routes[n]['layer'], len(cs), len(out[n]),
            ('%s %.2f mm / %.1f ps' % (keep[0]['variant'], keep[0]['elec']['mm'], keep[0]['elec']['ps'])) if keep else '-',
            time.time() - t))
    json.dump({n: [cand_params(c) for c in cs] for n, cs in out.items()}, open(CACHE, 'w'), indent=0)
    return out


def compat(c1, c2):
    if math.hypot(c1['cx'] - c2['cx'], c1['cy'] - c2['cy']) > 6.0:
        return True
    if rect_rect(body_rect(c1['cx'], c1['cy'], c1['rot']), body_rect(c2['cx'], c2['cy'], c2['rot'])) < COMP_CLEAR + MARGIN_REQ - 1e-6:
        return False
    for o in c1['new']:
        for e in c2['new']:
            if o.layer != e.layer:
                continue
            if gdist(o.g, e.g) < clearance(o.net, e.net, o.layer) + MARGIN_REQ - 1e-6:
                return False
            if o.kind == 'rpad' and e.kind == 'rpad' and gdist(o.mask, e.mask) < MASK_SLIVER + MARGIN_REQ - 1e-6:
                return False
            if o.kind == 'via' and e.kind == 'via' and set(o.span) & set(e.span):
                dc = math.hypot(e.g[1] - o.g[1], e.g[2] - o.g[2])
                if dc > 1e-6 and dc - o.hole / 2 - e.hole / 2 < HOLE_HOLE + MARGIN_REQ - 1e-6:
                    return False
    return True


def select(cands, nets, tlimit=300.0):
    """exact cover search: at most one placement per net, all pairwise compatible; maximise the count, then
    minimise the summed electrical distance (ps)"""
    pool = {n: [c for c in cands[n] if c.get('ok_alone', True)] for n in nets}
    order = sorted([n for n in nets if pool[n]], key=lambda n: len(pool[n]))
    cache = {}
    best = [0, {}, 1e18]
    t0 = time.time()

    def okc(n, a, chosen):
        for m, b in chosen.items():
            k = (n, a, m, b)
            if k not in cache:
                cache[k] = compat(pool[n][a], pool[m][b])
            if not cache[k]:
                return False
        return True

    def dfs(k, chosen, ps):
        if time.time() - t0 > tlimit:
            return
        if len(chosen) + len(order) - k < best[0]:
            return
        if len(chosen) + len(order) - k == best[0] and ps >= best[2]:
            return
        if k == len(order):
            if len(chosen) > best[0] or ps < best[2]:
                best[:] = [len(chosen), dict(chosen), ps]
            return
        n = order[k]
        for a, c in enumerate(pool[n]):
            if okc(n, a, chosen):
                chosen[n] = a
                dfs(k + 1, chosen, ps + c['elec']['ps'])
                del chosen[n]
        dfs(k + 1, chosen, ps)
    dfs(0, {}, 0.0)
    timed_out = time.time() - t0 > tlimit
    return {n: pool[n][a] for n, a in best[1].items()}, timed_out


def plane_webs(M, new_vias):
    """L2-GND / L5 pour openings around the new via lands: the pour clears other-net copper by 0.09 mm (Clearance;
    0.175 mm for through vias, Clearance_Plane_ThruVia). Report the narrowest copper web left between a new opening
    and its neighbours (< 0.25 mm webs are the ones tools/route/rev2/judge/planeweb.py treats as non-conducting)."""
    out = []
    for layer, pnet in (('L2-GND', 'GND'), ('L5-VCC3V3', 'VCC3V3')):
        others = []
        for v in M['vias']:
            if layer in v['span'] and v['net'] != pnet:
                cl = 0.175 if len(v['span']) == 6 else 0.09
                others.append((v['x'], v['y'], v['size'] / 2 + cl))
        for p in M['pads']:
            if p['drill'] > 0 and p['net'] != pnet:
                others.append((p['x'], p['y'], max(p['w'], p['h']) / 2 + 0.09))
        for t in M['tracks']:
            pass
        for v in new_vias:
            if layer not in v['span']:
                continue
            r = v['size'] / 2 + 0.09
            web = 99.0
            for x, y, ro in others:
                if abs(x - v['x']) < 1e-6 and abs(y - v['y']) < 1e-6:
                    continue
                web = min(web, math.hypot(x - v['x'], y - v['y']) - r - ro)
            out.append(dict(layer=layer, net=v['net'], x=v['x'], y=v['y'], opening_d=round(2 * r, 3), min_web=round(web, 3)))
    return out


def run_route_check(plan_path, model_path):
    import contextlib
    import io
    import route_check as RCK
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv = ['route_check.py', plan_path, model_path]
    try:
        with contextlib.redirect_stdout(buf):
            rc = RCK.main()
    finally:
        sys.argv = argv
    return rc, buf.getvalue()


def find_title_spot(M, entries, silk, w_text, h_text, proxies=None):
    """a new anchor for the title: no Top pad opening within 0.254 mm (SilkToSolderMask), no other visible silk and no
    Top part body (proxy) or new resistor within 0.254 mm, inside the board by 0.5 mm; 0.1 mm grid, nearest to the
    old anchor (37.7, 5.0) first"""
    pads = [p for p in M['pads'] if (not p['layers']) or 'Top Layer' in p['layers']]
    boxes = []
    for p in pads:
        e = mask_exp(p['ref'])
        boxes.append((p['x'] - p['w'] / 2 - e, p['y'] - p['h'] / 2 - e, p['x'] + p['w'] / 2 + e, p['y'] + p['h'] / 2 + e))
    sboxes = [s['box'] for s in silk if s['text'] != 'ZULU A7 2.3']
    sboxes += [b for r, b in (proxies or {}).items() if not r.startswith('X2')]   # not over a Top part body
    sboxes += [body_rect(e['center'][0], e['center'][1], e['rot']) for e in entries]
    best = None
    for x in frange(0.5, BOARD_W - 0.5 - w_text, 0.1):
        for y in frange(0.5, BOARD_H - 0.5 - h_text, 0.1):
            bx = (x - 0.09, y - 0.09, x + w_text + 0.09, y + h_text + 0.09)
            if any(rect_rect(bx, b) < SILK_MASK for b in boxes):
                continue
            if any(rect_rect(bx, b) < 0.254 for b in sboxes):
                continue
            d = math.hypot(x - 37.7, y - 5.0)
            if best is None or d < best[0]:
                best = (d, round(x, 2), round(y, 2))
    return best


def plot(board, M0, Mf, entries, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    fig, axes = plt.subplots(1, 3, figsize=(27, 13))
    win = (33.0, 46.5, 3.0, 19.0)
    layers = [('Top Layer', 'Top (resistors, Top tracks, column lands)'), ('L3-SIG', 'L3-SIG'), ('L4-SIG', 'L4-SIG')]
    dnets = set(NETS) | {'SDRAM-' + n for n in NETS}
    newkeys = set()
    for ax, (L, title) in zip(axes, layers):
        ax.set_facecolor('#f7f7f2')
        for t in M0['tracks']:
            if t['layer'] != L or not (win[0] - 1 < t['x1'] < win[1] + 1 and win[2] - 1 < t['y1'] < win[3] + 1):
                continue
            col = '#e8a33a' if t['net'] in dnets else '#9a9a9a'
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col, lw=max(0.5, t['w'] * 40), solid_capstyle='round',
                    alpha=0.55, zorder=2)
        for p in M0['pads']:
            ls = p['layers'] or MSTACK
            if L not in ls or not (win[0] - 1 < p['x'] < win[1] + 1 and win[2] - 1 < p['y'] < win[3] + 1):
                continue
            if RC.pad_round(p):
                ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, color='#b0b0b0', zorder=2))
            else:
                ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color='#b0b0b0', zorder=2))
        for v in M0['vias']:
            if L in v['span'] and win[0] - 1 < v['x'] < win[1] + 1 and win[2] - 1 < v['y'] < win[3] + 1:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, ec='#777777', lw=0.5, zorder=3))
        for e in entries:
            for i in e['remove_idx']:
                t = M0['tracks'][i]
                if t['layer'] == L:
                    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='#d62728', lw=2.2, ls=(0, (2, 1.5)), zorder=5)
            for t in e['tracks']:
                if t['layer'] == L:
                    col = '#1f77b4' if t['net'].startswith('SDRAM-') else '#2ca02c'
                    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col, lw=max(1.2, t['w'] * 40), zorder=6,
                            solid_capstyle='round')
            for v in e['vias']:
                if L in v['span']:
                    col = '#1f77b4' if v['net'].startswith('SDRAM-') else '#2ca02c'
                    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color=col, alpha=0.8, zorder=7))
            if L == 'Top Layer':
                br = body_rect(e['center'][0], e['center'][1], e['rot'])
                ax.add_patch(Rectangle((br[0], br[1]), br[2] - br[0], br[3] - br[1], fill=False, ec='k', lw=1.0, zorder=8))
                for p in e['pads']:
                    col = '#1f77b4' if p['net'].startswith('SDRAM-') else '#2ca02c'
                    ax.add_patch(Rectangle((p['x'] - 0.15, p['y'] - 0.15), 0.3, 0.3, color=col, zorder=8))
                ax.text(e['center'][0], br[3] + 0.08, '%s %s' % (e['ref'], e['net']), fontsize=7, ha='center', va='bottom',
                        zorder=9, color='k')
        if L == 'Top Layer':
            for ref, b in board.proxies.items():
                if ref.startswith('X2'):
                    continue
                if b[2] < win[0] or b[0] > win[1] or b[3] < win[2] or b[1] > win[3]:
                    continue
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec='#8c564b', ls='--', lw=0.8,
                                       zorder=4))
                ax.text(max(b[0], win[0]) + 0.1, min(b[3], win[3]) - 0.3, ref, color='#8c564b', fontsize=8, zorder=4)
            for s in board.silk_all:
                b = s['box']
                if b[2] < win[0] or b[0] > win[1] or b[3] < win[2] or b[1] > win[3]:
                    continue
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec='#bcbd22', lw=0.8, zorder=4))
        ax.set_xlim(win[0], win[1])
        ax.set_ylim(win[2], win[3])
        ax.set_aspect('equal')
        ax.set_title(title)
        ax.grid(alpha=0.2)
        ax.set_xlabel('x mm')
    axes[0].set_ylabel('y mm (board origin bottom-left)')
    fig.suptitle('Zulu_a7_no_pmod Rev 2 -- DQ series resistors on TOP (design_top.py). Blue = U3 side (SDRAM-Dn), green = U1 '
                 'side (Dn), red dashed = removed, orange = existing D-net copper, brown dashed = Top part bodies, '
                 'olive = visible Top silk', fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    t0 = time.time()
    fresh = '--fresh' in sys.argv
    board = Board(movable_silk=MOVABLE_SILK)
    M0 = json.load(open(MODEL_PATH))
    cands = all_candidates(board, fresh=fresh)
    chosen = {}
    timeouts = {}
    for grp in (SOUTH, NORTH):
        sel, to = select(cands, grp)
        chosen.update(sel)
        timeouts[grp[0] + '..' + grp[-1]] = to
    print('selected %d of 16: %s' % (len(chosen), ' '.join(sorted(chosen, key=lambda n: int(n[1:])))))
    entries = []
    for n in sorted(chosen, key=lambda n: int(n[1:])):
        e = entry_from_candidate(board, M0, chosen[n])
        e['elec'] = chosen[n]['elec']
        e['cand'] = cand_params(chosen[n])
        entries.append(e)
    # ---------------- exact verification on the model (independent of the search's own check)
    Mf = apply_plan(M0, entries)
    n_new = {'p': len(M0['pads']), 't': len(M0['tracks']) - len({i for e in entries for i in e['remove_idx']}), 'v': len(M0['vias'])}
    new = entry_new_objects(Mf, n_new)
    idx = Index(model_objects(Mf))
    keys = {(o.key, o.layer) for o in new}
    bodies = [entry_body(e) for e in entries]
    worst, viol = check_objects(new, idx, lambda q: (q.key, q.layer) in keys, bodies, board.silk, board.proxies)
    worst_c, viol_c = {}, []
    court = {r: b for r, b in board.court.items()}
    for ref, br in bodies:
        for r, b in court.items():
            m = rect_rect(br, b) - COMP_CLEAR
            if r not in worst_c or m < worst_c[r]:
                worst_c[r] = round(m, 4)
    moved_silk = []
    for s in board.silk_all:
        if s['text'] in MOVABLE_SILK:
            for e in entries:
                for p in e['pads']:
                    g = rect_c(p['x'], p['y'], PAD + 2 * MASK_EXP, PAD + 2 * MASK_EXP)
                    if rect_rect(g[1:5], s['box']) < SILK_MASK:
                        moved_silk.append((s['text'], e['ref']))
    moved_silk = sorted(set(moved_silk))
    isl = RC.islands(Mf)
    opens = {k: v for k, v in RC.open_count(isl).items() if v}
    # ---------------- route_check / route_conn on the derived model (renames + R pads) and the copper plan
    Md = copy.deepcopy(M0)
    for e in entries:
        for i in e['renames']['tracks']:
            Md['tracks'][i]['net'] = 'SDRAM-' + e['net']
        for i in e['renames']['vias']:
            Md['vias'][i]['net'] = 'SDRAM-' + e['net']
        for i in e['renames']['pads']:
            Md['pads'][i]['net'] = 'SDRAM-' + e['net']
        Md['pads'] += e['pads']
    remove = []
    for e in entries:
        for i in e['remove_idx']:
            t = dict(M0['tracks'][i])
            remove.append(t)
    plan = {'remove': remove, 'tracks': [t for e in entries for t in e['tracks']],
            'vias': [dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=v['span'])
                     for e in entries for v in e['vias']]}
    plan_path = os.path.join(HERE, 'design_top_plan.json')
    model_path = os.path.join(HERE, 'design_top_model.json')
    json.dump(plan, open(plan_path, 'w'), indent=0)
    json.dump(Md, open(model_path, 'w'))
    rc, rc_out = run_route_check(plan_path, model_path)
    print(rc_out)
    webs = plane_webs(Mf, plan['vias'])
    # ---------------- report
    unplaced = [n for n in NETS if n not in chosen]
    blockers = {}
    for n in unplaced:
        blockers[n] = 'no legal Top placement alone' if not cands[n] else \
            '%d legal placements alone, none compatible with the selected set' % len(cands[n])
    out = dict(
        script=os.path.abspath(__file__), source=EX['source'], model=MODEL_PATH, runtime_s=round(time.time() - t0, 1),
        approach='TOP side 0201 resistors (R0201 footprint), via-in-pad stacked microvias where the R sits on the inner '
                 'route; see the docstring for the variants',
        feasible=len(chosen) == 16, placed=len(chosen), unplaced=unplaced, unplaced_reason=blockers,
        selection_timeouts=timeouts,
        placements={}, verification=dict(
            exact_violations=viol, exact_worst={k: v for k, v in sorted(worst.items())},
            courtyard_mech7_margin=worst_c, route_check_rc=rc, route_check_output=rc_out,
            open_connections_after=opens, movable_silk_conflicts=moved_silk),
        plane_webs=webs)
    for e in entries:
        ref = e['ref']
        out['placements'][e['net']] = dict(
            ref=ref, part='Yageo RC0201FR-0722RL (22 ohm 1 % 0201), footprint R0201', side='Top', x=e['center'][0],
            y=e['center'][1], rot=e['rot'], variant=e['variant'], center=e['center'], pad_A=e['pad_A'], pad_B=e['pad_B'],
            pad1_net='SDRAM-' + e['net'], pad2_net=e['net'], section=e['section'],
            remove_tracks=[dict(layer=le(M0['tracks'][i]['layer']), net=e['net'], w=M0['tracks'][i]['w'],
                                x1=M0['tracks'][i]['x1'], y1=M0['tracks'][i]['y1'], x2=M0['tracks'][i]['x2'],
                                y2=M0['tracks'][i]['y2']) for i in e['remove_idx']],
            add_tracks=[dict(t, layer=le(t['layer'])) for t in e['tracks']],
            add_vias=[dict(v, span=[le(L) for L in v['span']]) for v in e['vias']],
            renamed_to_SDRAM=dict(tracks=[dict(layer=le(M0['tracks'][i]['layer']), x1=M0['tracks'][i]['x1'],
                                               y1=M0['tracks'][i]['y1'], x2=M0['tracks'][i]['x2'], y2=M0['tracks'][i]['y2'])
                                          for i in e['renames']['tracks']],
                                  vias=[dict(x=M0['vias'][i]['x'], y=M0['vias'][i]['y'], span=[le(L) for L in M0['vias'][i]['span']])
                                        for i in e['renames']['vias']],
                                  pads=['U3-%s' % M0['pads'][i]['pad'] for i in e['renames']['pads']]),
            electrical=e['elec'], search_worst_margin=chosen[e['net']]['worst'])
    if moved_silk:
        titles = [s for s in board.silk_all if s['text'] == 'ZULU A7 2.3']
        if titles and any(t == 'ZULU A7 2.3' for t, _ in moved_silk):
            b = titles[0]['box']
            spots = {}
            for h in (1.3, 1.0, 0.8):
                sp = find_title_spot(Mf, entries, board.silk_all, 0.955 * h * 11, h, board.proxies)
                spots['%.1f mm' % h] = None if sp is None else dict(anchor=[sp[1], sp[2]], move_mm=round(sp[0], 2),
                                                                     box=[sp[1], sp[2], round(sp[1] + 0.955 * h * 11, 2), round(sp[2] + h, 2)])
            out['title_new_anchor'] = spots
    json.dump(out, open(os.path.join(HERE, 'design_top.json'), 'w'), indent=1, default=str)
    plot(board, M0, Mf, entries, os.path.join(HERE, 'design_top.png'))
    print('placed %d / 16; exact violations %d; route_check rc %s; opens %s; moved silk %s; %.0f s' % (
        len(chosen), len(viol), rc, opens, moved_silk, time.time() - t0))


if __name__ == '__main__':
    main()
