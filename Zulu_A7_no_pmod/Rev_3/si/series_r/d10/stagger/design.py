"""design.py -- D10 series resistor, strategy "stagger" (Zulu_a7_no_pmod Rev 2).  PLANNING ONLY.

Keeps R127 (D8), R130 (D11) and a NEW R129 (D10) all on TOP, on their own Top runs at the U1 end, and re-positions
them JOINTLY so they no longer collide.  The five nets of the Top staircase between the through-via column at
x = 38.5 and U1 (CKE, D8, UDQM, D10, D11: via (38.5, y) -> horizontal east -> vertical south to U1) are treated as
re-routable above y = YC; everything else on the board (and every other edit of the 12-resistor plan) is fixed.

Search (exhaustive at the grid below, exact geometry, exact-cover style like design_top.select()):
  * per resistor net: every centre on a 0.025 mm grid in the window, rotations 0/90/180/270, pad 1 (SDRAM-Dn) fed
    from the net's via by a 1-3 segment octilinear path (A), pad 2 (Dn) joined to the net's OWN vertical by a 1-2
    segment octilinear path (B); the vertical is shortened (or extended) to the attach point; every candidate is
    checked alone against the fixed copper (Clearance 0.09 + 5 um), through-via land outside the pad mask openings,
    ComponentClearance 0.254 + 5 um (R0201 body proxy 0.90 x 0.396, Top-side part proxies as design_top.py),
    MinimumSolderMaskSliver 0.10 + 5 um, silk-to-mask 0.254 + 5 um, no acute joints;
  * per non-resistor net (CKE, UDQM): its original copper, or a local jog via -> octilinear path -> its vertical;
  * joint: one candidate per net, all pairwise compatible (copper 0.095, bodies 0.259, mask 0.105), searched by
    backtracking over D10 -> D11 -> D8 -> UDQM -> CKE with vectorised compatibility.  Objective (lexicographic):
    fewest non-resistor nets changed, then the largest worst margin, then the least new copper.
The winner is merged into the 12-resistor plan (dq_series_r_plan.json minus its R127/R130 Top edits) and exported in
the same format (renames derived from connectivity exactly like plan_export.py).

Copper rule: 0.090 + 5 um for every new gap, EXCEPT the staircase's own 0.1665 mm pitch (a track end at its vertical
sits 0.0903 from the next vertical, exactly like every existing corner on the DRC-0 board): those gaps must be >= 0.0902
and are left out of the margin objective.  Two stages: the exhaustive search on a 0.05 mm grid over the whole window,
then the same exhaustive search on a 0.01 mm grid within +-0.08 mm of the coarse winner (same rotations).  The objective
counts copper, pad, body (ComponentClearance), mask-web, silk and via-land margins.

Writes ONLY into this folder: plan.json, plan.png, design.json (search statistics), design.log, coarse_cache.json.

    python design.py                  full run (~20 min, <= 6 worker processes)
    python design.py --reuse-coarse   re-run only the refinement, reusing the coarse stage's result from coarse_cache.json
"""
import collections
import itertools
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.dirname(os.path.dirname(HERE))          # si/series_r
sys.path.insert(0, SR)
_argv = sys.argv
sys.argv = [sys.argv[0]]
import dfm_check as D  # noqa: E402  (read-only use of its geometry / apply helpers)
sys.argv = _argv

LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


# ------------------------------------------------------------------------------------------------ rules / constants
CLR = 0.09
MARGIN = 0.005                 # Altium rounds to 2.54 um; new copper keeps >= 5 um beyond every rule ...
CU_REQ = CLR + 0.0002          # ... except the staircase's own pitch: a track end at its vertical sits 0.1665 - 0.0762 =
PITCH = (0.0902, 0.09035)      # 0.0903 from the next vertical, exactly as every existing corner (board DRC 0). Hard
                               # copper rule = 0.0902; gaps in PITCH are 'inherited pitch' and excluded from the margin
                               # objective; every other new copper gap must keep the 5 um margin (0.095).
COMP = 0.254
MASK_SLIVER = 0.10
MASK_EXP = 0.05
SILK = 0.254
W = 0.0762                     # Top width (Width_SDRAM Top min 0.0762, the existing runs' width)
HW = W / 2
PAD = 0.30
BODY = (0.90, 0.396)           # design_top.py R0201 body proxy (pads bbox U Mech3 0.40 x 0.396)
YC = 12.55                     # below this the five verticals are fixed
GRID = float(os.environ.get("STAGGER_GRID", "0.05"))
WIN = (38.55, 40.75, 12.75, 15.60)   # resistor-centre window
NA, NB = int(os.environ.get("STAGGER_NA", "2")), int(os.environ.get("STAGGER_NB", "3"))                  # feed / return variants kept per placement (shortest first)
GEN_ONLY = '--gen-only' in sys.argv

# the Top staircase (from board_extract.json, PcbDoc md5 2a616c1c)
NET5 = collections.OrderedDict([
    ('CKE', dict(via=(38.5, 13.15), x=39.4790, top=13.15, low=11.13, R=None)),
    ('D8', dict(via=(38.5, 13.60), x=39.6455, top=13.60, low=11.36, R='R127')),
    ('UDQM', dict(via=(38.5, 14.05), x=39.8120, top=14.05, low=11.59, R=None)),
    ('D10', dict(via=(38.5, 14.50), x=39.9785, top=14.50, low=12.21, R='R129')),
    ('D11', dict(via=(38.5, 14.95), x=40.1450, top=14.95, low=12.38, R='R130')),
])
RNETS = [n for n, v in NET5.items() if v['R']]
DPIN = D.DPIN


def snet(n):
    return 'SDRAM-' + n


# ------------------------------------------------------------------------------------------------ plan <-> edit list
def full_span(a, b):
    a, b = D.LN.get(a, a), D.LN.get(b, b)
    i, j = D.CU.index(a), D.CU.index(b)
    return D.CU[min(i, j):max(i, j) + 1]


def plan_to_E(P, drop_top_nets=(), drop_refs=()):
    """emit_copper plan -> dfm_check edit list; 'rename' entries are skipped (they are re-derived)"""
    E = dict(rm_t=[], add_t=[], rm_v=[], add_v=[], renet=[], add_p=[], parts={}, designer_renames=collections.defaultdict(list))
    dn = set(drop_top_nets) | {snet(n) for n in drop_top_nets}
    for t in P['remove']:
        if t.get('why') == 'rename' or (t['layer'] == 'Top Layer' and t['net'] in dn):
            continue
        E['rm_t'].append(dict(t, layer=D.LN[t['layer']]))
    for t in P['tracks']:
        if t.get('why') == 'rename' or (t['layer'] == 'Top Layer' and t['net'] in dn):
            continue
        E['add_t'].append(dict(net=t['net'], layer=D.LN[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    bv = D.board_records()[2]
    for v in P['remove_vias']:
        if v.get('why') == 'rename':
            continue
        m = [b for b in bv if D.same((b['x'], b['y']), (v['x'], v['y'])) and b['span'][0] == D.LN.get(v['span'][0], v['span'][0])
             and b['span'][-1] == D.LN.get(v['span'][-1], v['span'][-1])]
        assert len(m) == 1, v
        E['rm_v'].append(dict(x=v['x'], y=v['y'], span=list(m[0]['span'])))
    for v in P['vias']:
        if v.get('why') == 'rename':
            continue
        sp = full_span(v['from'], v['to'])
        E['add_v'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=sp,
                               kind='through' if len(sp) == 6 else 'micro'))
    E['renet'] = [dict(r) for r in P['renet_pads']]
    for pr in P['parts']:
        if pr['ref'] in drop_refs:
            continue
        n = pr['net_bit']
        for k, pd in (('1', pr['pad1']), ('2', pr['pad2'])):
            E['add_p'].append(dict(ref=pr['ref'], pad=k, layer=pr['side'], net=pd['net'], x=pd['x'], y=pd['y'],
                                   w=0.3, h=0.3, shape='rect', hole=0.0))
        E['parts'][n] = dict(ref=pr['ref'], side=pr['side'], x=pr['x'], y=pr['y'], rot=pr['rot'])
    return E


# ------------------------------------------------------------------------------------------------ vector geometry
def _pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    with np.errstate(invalid='ignore', divide='ignore'):
        t = np.where(L2 > 0, ((px - x1) * dx + (py - y1) * dy) / np.where(L2 > 0, L2, 1), 0.0)
    t = np.clip(t, 0, 1)
    return np.hypot(px - x1 - t * dx, py - y1 - t * dy)


def _orient(ax, ay, bx, by, cx, cy):
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def seg_seg(A, B):
    """A (...,4), B (...,4) broadcastable -> distance"""
    a1, a2, a3, a4 = A[..., 0], A[..., 1], A[..., 2], A[..., 3]
    b1, b2, b3, b4 = B[..., 0], B[..., 1], B[..., 2], B[..., 3]
    o1 = _orient(a1, a2, a3, a4, b1, b2); o2 = _orient(a1, a2, a3, a4, b3, b4)
    o3 = _orient(b1, b2, b3, b4, a1, a2); o4 = _orient(b1, b2, b3, b4, a3, a4)
    cross = (o1 * o2 < 0) & (o3 * o4 < 0)
    d = np.minimum(np.minimum(_pt_seg(b1, b2, a1, a2, a3, a4), _pt_seg(b3, b4, a1, a2, a3, a4)),
                   np.minimum(_pt_seg(a1, a2, b1, b2, b3, b4), _pt_seg(a3, a4, b1, b2, b3, b4)))
    return np.where(cross, 0.0, d)


def seg_rect(S, R):
    """S (...,4) segments, R (...,4) rects (cx, cy, hw, hh) -> distance (0 if touching/inside)"""
    cx, cy, hw, hh = R[..., 0], R[..., 1], R[..., 2], R[..., 3]
    x0, x1, y0, y1 = cx - hw, cx + hw, cy - hh, cy + hh
    inside = ((np.abs(S[..., 0] - cx) <= hw) & (np.abs(S[..., 1] - cy) <= hh)) | \
             ((np.abs(S[..., 2] - cx) <= hw) & (np.abs(S[..., 3] - cy) <= hh))
    edges = [np.stack(np.broadcast_arrays(x0, y0, x1, y0), -1), np.stack(np.broadcast_arrays(x1, y0, x1, y1), -1),
             np.stack(np.broadcast_arrays(x1, y1, x0, y1), -1), np.stack(np.broadcast_arrays(x0, y1, x0, y0), -1)]
    d = np.minimum(np.minimum(seg_seg(S, edges[0]), seg_seg(S, edges[1])), np.minimum(seg_seg(S, edges[2]), seg_seg(S, edges[3])))
    return np.where(inside, 0.0, d)


def rect_rect(A, B):
    dx = np.maximum(0.0, np.abs(A[..., 0] - B[..., 0]) - A[..., 2] - B[..., 2])
    dy = np.maximum(0.0, np.abs(A[..., 1] - B[..., 1]) - A[..., 3] - B[..., 3])
    return np.hypot(dx, dy)


class Shapes:
    """a flat set of copper shapes with per-shape net id / 'new' flag / owner candidate index"""

    def __init__(self):
        self.C, self.Cr, self.Cn, self.Cnew, self.Co = [], [], [], [], []
        self.R, self.Rn, self.Rnew, self.Ro = [], [], [], []

    def cap(self, x1, y1, x2, y2, r, net, new, owner=0):
        self.C.append((x1, y1, x2, y2)); self.Cr.append(r); self.Cn.append(net); self.Cnew.append(new); self.Co.append(owner)

    def rect(self, cx, cy, hw, hh, net, new, owner=0):
        self.R.append((cx, cy, hw, hh)); self.Rn.append(net); self.Rnew.append(new); self.Ro.append(owner)

    def freeze(self):
        self.C = np.array(self.C, float).reshape(-1, 4); self.Cr = np.array(self.Cr, float)
        self.Cn = np.array(self.Cn, object); self.Cnew = np.array(self.Cnew, bool); self.Co = np.array(self.Co, int)
        self.R = np.array(self.R, float).reshape(-1, 4); self.Rn = np.array(self.Rn, object)
        self.Rnew = np.array(self.Rnew, bool); self.Ro = np.array(self.Ro, int)
        return self


def min_gap(a, b, same_net_ok=True):
    """smallest copper gap between two frozen Shapes sets over pairs on DIFFERENT nets where at least one is new.
    returns (gap, (kind, i, j))"""
    best = (9.0, None)
    if len(a.C) and len(b.C):
        d = seg_seg(a.C[:, None, :], b.C[None, :, :]) - a.Cr[:, None] - b.Cr[None, :]
        m = (a.Cn[:, None] != b.Cn[None, :]) & (a.Cnew[:, None] | b.Cnew[None, :])
        d = np.where(m, d, 9.0)
        k = np.unravel_index(np.argmin(d), d.shape)
        if d[k] < best[0]:
            best = (float(d[k]), ('cc', int(k[0]), int(k[1])))
    for X, Y, sw in ((a, b, False), (b, a, True)):
        if len(X.C) and len(Y.R):
            d = seg_rect(X.C[:, None, :], Y.R[None, :, :]) - X.Cr[:, None]
            m = (X.Cn[:, None] != Y.Rn[None, :]) & (X.Cnew[:, None] | Y.Rnew[None, :])
            d = np.where(m, d, 9.0)
            k = np.unravel_index(np.argmin(d), d.shape)
            if d[k] < best[0]:
                best = (float(d[k]), ('cr' if not sw else 'rc', int(k[0]), int(k[1])))
    if len(a.R) and len(b.R):
        d = rect_rect(a.R[:, None, :], b.R[None, :, :])
        m = (a.Rn[:, None] != b.Rn[None, :]) & (a.Rnew[:, None] | b.Rnew[None, :])
        d = np.where(m, d, 9.0)
        k = np.unravel_index(np.argmin(d), d.shape)
        if d[k] < best[0]:
            best = (float(d[k]), ('rr', int(k[0]), int(k[1])))
    return best


def with_rect(S, p, net):
    """S plus one new pad rect (frozen copy)"""
    T = Shapes()
    T.C, T.Cr, T.Cn, T.Cnew, T.Co = S.C, S.Cr, S.Cn, S.Cnew, S.Co
    T.R = np.vstack([S.R, [[p[0], p[1], PAD / 2, PAD / 2]]])
    T.Rn = np.append(S.Rn, np.array([net], object))
    T.Rnew = np.append(S.Rnew, True)
    T.Ro = np.append(S.Ro, 0)
    return T


def _hard_obj(d, owners, gap, gobj):
    np.minimum.at(gap, owners, d)
    np.minimum.at(gobj, owners, np.where((d >= PITCH[0]) & (d <= PITCH[1]), 9.0, d))


def owner_gaps(bt, other, n_owner):
    """per-owner smallest gap between a batch of shapes (owner ids in Co/Ro) and another set (different nets only;
    pairs where neither shape is new are ignored).  Returns (gap, gap excluding the inherited-pitch band)."""
    gap = np.full(n_owner, 9.0)
    gobj = np.full(n_owner, 9.0)
    if len(bt.C):
        if len(other.C):
            d = seg_seg(bt.C[:, None, :], other.C[None, :, :]) - bt.Cr[:, None] - other.Cr[None, :]
            d = np.where((bt.Cn[:, None] != other.Cn[None, :]) & (bt.Cnew[:, None] | other.Cnew[None, :]), d, 9.0)
            _hard_obj(d.min(1), bt.Co, gap, gobj)
            _hard_obj(np.where((d >= PITCH[0]) & (d <= PITCH[1]), 9.0, d).min(1), bt.Co, np.full(n_owner, 9.0), gobj)
        if len(other.R):
            d = seg_rect(bt.C[:, None, :], other.R[None, :, :]) - bt.Cr[:, None]
            d = np.where((bt.Cn[:, None] != other.Rn[None, :]) & (bt.Cnew[:, None] | other.Rnew[None, :]), d, 9.0).min(1)
            _hard_obj(d, bt.Co, gap, gobj)
    if len(bt.R):
        if len(other.C):
            d = seg_rect(other.C[None, :, :], bt.R[:, None, :]) - other.Cr[None, :]
            d = np.where((bt.Rn[:, None] != other.Cn[None, :]) & (bt.Rnew[:, None] | other.Cnew[None, :]), d, 9.0).min(1)
            _hard_obj(d, bt.Ro, gap, gobj)
        if len(other.R):
            d = rect_rect(bt.R[:, None, :], other.R[None, :, :])
            d = np.where((bt.Rn[:, None] != other.Rn[None, :]) & (bt.Rnew[:, None] | other.Rnew[None, :]), d, 9.0).min(1)
            _hard_obj(d, bt.Ro, gap, gobj)
    return gap, gobj


# ------------------------------------------------------------------------------------------------ context board
def build_context(P0):
    E = plan_to_E(P0, drop_top_nets=('D8', 'D11'), drop_refs=('R127', 'R130'))
    pads, tracks, vias, newflags, errors = D.apply(E)
    assert not errors, errors
    return E, pads, tracks, vias


def is_zone_track(t):
    """the horizontal and vertical Top runs of the five staircase nets (re-routable)"""
    if t['layer'] != 'Top' or t['net'] not in NET5:
        return False
    z = NET5[t['net']]
    hor = abs(t['y1'] - z['top']) < 1e-3 and abs(t['y2'] - z['top']) < 1e-3 and {round(t['x1'], 3), round(t['x2'], 3)} == {38.5, round(z['x'], 3)}
    ver = abs(t['x1'] - z['x']) < 1e-3 and abs(t['x2'] - z['x']) < 1e-3 and {round(t['y1'], 3), round(t['y2'], 3)} == {round(z['low'], 3), round(z['top'], 3)}
    return hor or ver


def static_shapes(pads, tracks, vias):
    """fixed Top copper near the staircase (net labels as after the edit: the five vias of the resistor nets are
    SDRAM-Dn), the lower fixed piece of each vertical, Top pad mask openings, through-via lands, proxies, silk"""
    X0, X1, Y0, Y1 = 36.6, 41.9, 11.6, 17.2
    S = Shapes()
    zone_found = collections.Counter()
    for t in tracks:
        if t is None or t['layer'] != 'Top':
            continue
        if is_zone_track(t):
            zone_found[t['net']] += 1
            continue
        if max(t['x1'], t['x2']) < X0 or min(t['x1'], t['x2']) > X1 or max(t['y1'], t['y2']) < Y0 or min(t['y1'], t['y2']) > Y1:
            continue
        S.cap(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2, t['net'], False)
    assert all(zone_found[n] == 2 for n in NET5), zone_found
    for n, z in NET5.items():
        S.cap(z['x'], z['low'], z['x'], YC, HW, n, False)          # fixed lower piece of each vertical
    thru = []
    for v in vias:
        if v is None or 'Top' not in v['span'] or not (X0 < v['x'] < X1 and Y0 < v['y'] < Y1):
            continue
        net = v['net']
        for n, z in NET5.items():
            if z['R'] and D.same((v['x'], v['y']), z['via']):
                net = snet(n)
        S.cap(v['x'], v['y'], v['x'], v['y'], v['size'] / 2, net, False)
        if len(v['span']) == 6:
            thru.append((v['x'], v['y'], v['size'] / 2))
    openings = []
    for p in pads:
        if p['layer'] not in ('Top', 'Multi') or not (X0 - 1.0 < p['x'] < X1 + 1.0 and Y0 - 1.0 < p['y'] < Y1 + 1.0):
            continue
        sh = D.pad_shape(p, 'Top')
        if sh[0] == 'R':
            S.rect(sh[1], sh[2], sh[3], sh[4], p['net'], False)
        else:
            S.cap(sh[1], sh[2], sh[3], sh[4], sh[5], p['net'], False)
        e = 0.0 if p['ref'] == 'U1' else (0.04 if p['ref'] == 'X3' else MASK_EXP)
        openings.append((D.grow(sh, e), p['ref'], p['pad'], p['net']))
    return S.freeze(), thru, openings


def proxies(P0):
    """Top-side body proxies exactly as design_top.comp_proxies() + the plan's other Top resistors (R131)"""
    out = {}
    side = {c['ref']: c['side'] for c in D.B['components']}
    for ref, o in D.B['component_outlines'].items():
        if side.get(ref) != 'Top' or ref == 'X2':
            continue
        bs = [o[k] for k in o if k == 'pads' or k.startswith('Mech3') or k.startswith('Mech4')]
        if bs:
            out[ref] = [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]
    p = D.B['component_outlines']['U1']['pads']
    cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
    b = out['U1']
    out['U1'] = [min(b[0], cx - 5.0), min(b[1], cy - 5.0), max(b[2], cx + 5.0), max(b[3], cy + 5.0)]
    for q in D.B['pads']:
        if q['ref'] == 'X2' and q['layer'] in ('Top', 'Multi'):
            out['X2-%s' % q['pad']] = [q['x'] - q['w'] / 2, q['y'] - q['h'] / 2, q['x'] + q['w'] / 2, q['y'] + q['h'] / 2]
    for pr in P0['parts']:
        if pr['side'] == 'Top' and pr['ref'] not in ('R127', 'R130'):
            out[pr['ref']] = body_rect(pr['x'], pr['y'], pr['rot'])
    return out


def silk_boxes():
    """visible Top Overlay texts, the larger of design_top.py's (0.955 x h per char, measured) and dfm_check's box"""
    out = []
    for t in D.B['texts']:
        if t['layer'] != 'TopOverlay' or t['hidden']:
            continue
        txt = t['text']
        w = 0.955 * t['height'] * len(txt)
        h = t['height']
        s = t['stroke'] / 2
        r = round(t['rot']) % 360
        x, y = t['x'], t['y']
        b = {0: [x, y, x + w, y + h], 90: [x - h, y, x, y + w], 180: [x - w, y - h, x, y]}.get(r, [x, y - w, x + h, y])
        out.append(dict(text=txt, box=[b[0] - s, b[1] - s, b[2] + s, b[3] + s]))
    return out


def body_rect(cx, cy, rot):
    a, c = BODY
    return [cx - a / 2, cy - c / 2, cx + a / 2, cy + c / 2] if rot % 180 == 0 else [cx - c / 2, cy - a / 2, cx + c / 2, cy + a / 2]


def r4(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, (b[2] - b[0]) / 2, (b[3] - b[1]) / 2)


def rr(a, b):
    return float(rect_rect(np.array(r4(a)), np.array(r4(b))))


# ------------------------------------------------------------------------------------------------ path families
def octi2(a, b):
    """all 1-2 segment octilinear paths a -> b (lists of points)"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    out = []
    if abs(dx) < 1e-9 or abs(dy) < 1e-9 or abs(abs(dx) - abs(dy)) < 1e-9:
        out.append([a, b])
        return out
    m = min(abs(dx), abs(dy))
    sx, sy = math.copysign(1, dx), math.copysign(1, dy)
    out.append([a, (a[0] + sx * m, a[1] + sy * m), b])          # diagonal first
    out.append([a, (b[0] - sx * m, b[1] - sy * m), b])          # straight first
    out.append([a, (b[0], a[1]), b])                             # H then V
    out.append([a, (a[0], b[1]), b])                             # V then H
    return out


def clean(pts):
    q = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - q[-1][0], p[1] - q[-1][1]) > 1e-6:
            q.append(p)
    # merge colinear
    r = [q[0]]
    for i in range(1, len(q) - 1):
        a, b, c = r[-1], q[i], q[i + 1]
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) < 1e-9:
            continue
        r.append(b)
    if len(q) > 1:
        r.append(q[-1])
    return r


def acute(pts, end_dir=None):
    """True if any joint of the polyline (or its joint with a continuing direction end_dir) is < 90 deg"""
    segs = [(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    if end_dir is not None:
        segs.append(end_dir)
    for u, v in zip(segs, segs[1:]):
        lu, lv = math.hypot(*u), math.hypot(*v)
        if lu < 1e-9 or lv < 1e-9:
            continue
        # angle between the reversed incoming and the outgoing direction
        c = (-u[0] * v[0] - u[1] * v[1]) / lu / lv
        if c > math.cos(math.radians(90 - 0.5)):
            return True
    return False


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def paths_A(V, P1):
    """via -> pad 1: 1-2 segment octilinear, plus 3-segment H-D-H / V-D-V detours"""
    out = [clean(p) for p in octi2(V, P1)]
    dx, dy = P1[0] - V[0], P1[1] - V[1]
    if abs(dy) > 1e-9 and abs(dx) > abs(dy) + 1e-9:
        sx, sy = math.copysign(1, dx), math.copysign(1, dy)
        for k in range(1, 80):
            x1 = V[0] + sx * k * GRID
            x2 = x1 + sx * abs(dy)
            if (x2 - P1[0]) * sx > -1e-9:
                break
            out.append(clean([V, (x1, V[1]), (x2, P1[1]), P1]))
    return out


def paths_B(P2, xv):
    """pad 2 -> its vertical at x = xv: returns (points, attach_y); the vertical continues SOUTH from the attach"""
    out = []
    dx = xv - P2[0]
    sx = math.copysign(1, dx) if abs(dx) > 1e-9 else 1.0
    out.append(([P2, (xv, P2[1])], P2[1]))                                    # straight across
    if abs(dx) > 1e-9:
        out.append(([P2, (xv, P2[1] - abs(dx))], P2[1] - abs(dx)))           # 45 deg down onto it
        for k in range(1, 40):                                                # across, then 45 deg down
            d = k * GRID
            if d >= abs(dx) - 1e-9:
                break
            out.append(([P2, (xv - sx * d, P2[1]), (xv, P2[1] - d)], P2[1] - d))
        for k in range(1, 40):                                                # 45 deg up/down, then across
            d = k * GRID
            if d >= abs(dx) - 1e-9:
                break
            for sy in (1, -1):
                out.append(([P2, (P2[0] + sx * d, P2[1] + sy * d), (xv, P2[1] + sy * d)], P2[1] + sy * d))
    for k in range(-40, 41):                                                  # vertical, then across
        if k == 0:
            continue
        yk = P2[1] + k * GRID
        out.append(([P2, (P2[0], yk), (xv, yk)], yk))
    res = []
    for pts, ya in out:
        pts = clean(pts)
        if ya < YC + 0.05 or ya > 15.6:
            continue
        if acute(pts, (0.0, -1.0)):
            continue
        res.append((pts, ya))
    return res


def paths_J(V, xv):
    """non-resistor net jog: via -> its vertical (attach y free); 2-3 segment octilinear"""
    out = []
    for k in range(-60, 61):
        ya = round(V[1] + k * 0.01, 4)
        if ya < YC + 0.05 or ya > 15.6:
            continue
        A = (xv, ya)
        for p in octi2(V, A):
            out.append((clean(p), ya))
        dy = ya - V[1]
        if abs(dy) > 1e-9:
            for j in range(1, 80):
                x1 = V[0] + j * GRID
                x2 = x1 + abs(dy)
                if x2 > xv - 1e-9:
                    break
                out.append((clean([V, (x1, V[1]), (x2, ya), A]), ya))
    return [(p, ya) for p, ya in out if not acute(p, (0.0, -1.0))]


# ------------------------------------------------------------------------------------------------ candidates
class Cand:
    __slots__ = ('net', 'kind', 'place', 'A', 'B', 'ya', 'shapes', 'body', 'open', 'new_len', 'static_margin', 'key')


def vertical_piece(n, ya, sh, owner=0):
    z = NET5[n]
    if ya <= z['top'] + 1e-9:
        sh.cap(z['x'], YC, z['x'], ya, HW, n, False, owner)
    else:
        sh.cap(z['x'], YC, z['x'], z['top'], HW, n, False, owner)
        sh.cap(z['x'], z['top'], z['x'], ya, HW, n, True, owner)


def pads_of(cx, cy, rot):
    o = {0: (-0.3, 0.0), 90: (0.0, -0.3), 180: (0.3, 0.0), 270: (0.0, 0.3)}[rot]
    return (round(cx + o[0], 5), round(cy + o[1], 5)), (round(cx - o[0], 5), round(cy - o[1], 5))


class Ctx:
    def __init__(self, P0):
        self.P0 = P0
        self.E, self.pads, self.tracks, self.vias = build_context(P0)
        self.S, self.thru, self.openings = static_shapes(self.pads, self.tracks, self.vias)
        self.prox = proxies(P0)
        self.silk = silk_boxes()
        self.open_arr = []
        for sh, ref, pad, net in self.openings:
            if sh[0] == 'R':
                self.open_arr.append((sh[1], sh[2], sh[3], sh[4]))
            else:     # capsule opening -> its bbox (conservative)
                b = D.bbox(sh)
                self.open_arr.append(r4(b))
        self.open_arr = np.array(self.open_arr, float).reshape(-1, 4)
        self.thru_arr = np.array(self.thru, float).reshape(-1, 3)

    def static_gap(self, sh):
        g, w = min_gap(sh, self.S)
        return g, w


def build_shapes(n, place, A, B, ya, owner=0):
    sh = Shapes()
    z = NET5[n]
    if place is not None:
        p1, p2 = pads_of(*place)
        sh.rect(p1[0], p1[1], PAD / 2, PAD / 2, snet(n), True, owner)
        sh.rect(p2[0], p2[1], PAD / 2, PAD / 2, n, True, owner)
        for a, b in zip(A, A[1:]):
            sh.cap(a[0], a[1], b[0], b[1], HW, snet(n), True, owner)
        for a, b in zip(B, B[1:]):
            sh.cap(a[0], a[1], b[0], b[1], HW, n, True, owner)
    else:
        for a, b in zip(A, A[1:]):
            sh.cap(a[0], a[1], b[0], b[1], HW, n, B, owner)       # B carries the 'new' flag for jog/orig
    vertical_piece(n, ya, sh, owner)
    return sh


def gen_rnet(ctx, n, stats, win=None, rots=(0, 90, 180, 270)):
    z = NET5[n]
    V = z['via']
    win = win or WIN
    xs = np.round(np.arange(win[0], win[1] + 1e-9, GRID), 4)
    ys = np.round(np.arange(win[2], win[3] + 1e-9, GRID), 4)
    cands = []
    t0 = time.time()
    npl = nlegal = 0
    prox = np.array([r4(b) for b in ctx.prox.values()])
    silk = np.array([r4(sb['box']) for sb in ctx.silk])
    pts = np.concatenate([ctx.thru_arr[:, :2], ctx.thru_arr[:, :2]], 1)
    survivors = []
    for rot in rots:
        CX, CY = np.meshgrid(xs, ys, indexing='ij')
        CX, CY = CX.ravel(), CY.ravel()
        npl += len(CX)
        o = {0: (-0.3, 0.0), 90: (0.0, -0.3), 180: (0.3, 0.0), 270: (0.0, 0.3)}[rot]
        P1 = np.stack([CX + o[0], CY + o[1]], 1)
        P2 = np.stack([CX - o[0], CY - o[1]], 1)
        a_, c_ = BODY if rot % 180 == 0 else BODY[::-1]
        body = np.stack([CX, CY, np.full_like(CX, a_ / 2), np.full_like(CX, c_ / 2)], 1)
        ok = rect_rect(body[:, None, :], prox[None, :, :]).min(1) >= COMP + MARGIN - 1e-9
        for P, net in ((P1, snet(n)), (P2, n)):
            pr = np.concatenate([P, np.full((len(P), 2), PAD / 2)], 1)
            op = np.concatenate([P, np.full((len(P), 2), PAD / 2 + MASK_EXP)], 1)
            if len(ctx.open_arr):
                ok &= rect_rect(op[:, None, :], ctx.open_arr[None, :, :]).min(1) >= MASK_SLIVER + MARGIN - 1e-9
            ok &= rect_rect(op[:, None, :], silk[None, :, :]).min(1) >= SILK + MARGIN - 1e-9
            ok &= (seg_rect(pts[None, :, :], op[:, None, :]) - ctx.thru_arr[None, :, 2]).min(1) >= MARGIN - 1e-9
            dc = seg_rect(ctx.S.C[None, :, :], pr[:, None, :]) - ctx.S.Cr[None, :]
            dc = np.where((ctx.S.Cn != net)[None, :], dc, 9.0).min(1)
            ok &= dc >= CLR + MARGIN - 1e-9
            if len(ctx.S.R):
                dr = rect_rect(pr[:, None, :], ctx.S.R[None, :, :])
                dr = np.where((ctx.S.Rn != net)[None, :], dr, 9.0).min(1)
                ok &= dr >= CLR + MARGIN - 1e-9
        for k in np.flatnonzero(ok):
            survivors.append((rot, float(CX[k]), float(CY[k])))
    nlegal = len(survivors)
    proxa = np.array([r4(b) for b in ctx.prox.values()])
    for rot, cx, cy in survivors:
                p1, p2 = pads_of(cx, cy, rot)
                body = body_rect(cx, cy, rot)
                op = np.array([[p1[0], p1[1], PAD / 2 + MASK_EXP, PAD / 2 + MASK_EXP], [p2[0], p2[1], PAD / 2 + MASK_EXP, PAD / 2 + MASK_EXP]])
                # placement margins (all as 'mm beyond the rule'): pads vs fixed copper, body vs part proxies, mask web,
                # silk, through-via land vs opening -- folded into the candidate's margin for the objective
                psh = Shapes()
                psh.rect(p1[0], p1[1], PAD / 2, PAD / 2, snet(n), True)
                psh.rect(p2[0], p2[1], PAD / 2, PAD / 2, n, True)
                pm = [owner_gaps(psh.freeze(), ctx.S, 1)[1][0] - CLR,
                      float(rect_rect(np.array(r4(body))[None, :], proxa).min()) - COMP,
                      float(rect_rect(op[:, None, :], ctx.open_arr[None, :, :]).min()) - MASK_SLIVER if len(ctx.open_arr) else 9.0,
                      float(rect_rect(op[:, None, :], silk[None, :, :]).min()) - SILK,
                      float((seg_rect(pts[None, :, :], op[:, None, :]) - ctx.thru_arr[None, :, 2]).min())]
                place_margin = min(pm)
                sp1 = Shapes(); sp1.rect(p1[0], p1[1], PAD / 2, PAD / 2, snet(n), True); sp1.freeze()
                sp2 = Shapes(); sp2.rect(p2[0], p2[1], PAD / 2, PAD / 2, n, True); sp2.freeze()
                As = []
                pa = [A for A in paths_A(V, p1) if not acute(A)]
                if pa:
                    bt = Shapes()
                    for k, A in enumerate(pa):
                        for a, b in zip(A, A[1:]):
                            bt.cap(a[0], a[1], b[0], b[1], HW, snet(n), True, k)
                    g, go = owner_gaps(bt.freeze(), with_rect(ctx.S, p2, n), len(pa))
                    As = [(A, float(oo)) for A, gg, oo in zip(pa, g, go) if gg >= CU_REQ - 1e-9 and oo >= CLR + MARGIN - 1e-9]
                if not As:
                    continue
                pb = paths_B(p2, z['x'])
                bt = Shapes()
                for k, (B, ya) in enumerate(pb):
                    for a, b in zip(B, B[1:]):
                        bt.cap(a[0], a[1], b[0], b[1], HW, n, True, k)
                    vertical_piece(n, ya, bt, k)
                g, go = owner_gaps(bt.freeze(), with_rect(ctx.S, p1, snet(n)), len(pb))
                Bs = [(B, ya, float(oo)) for (B, ya), gg, oo in zip(pb, g, go) if gg >= CU_REQ - 1e-9 and oo >= CLR + MARGIN - 1e-9]
                if not Bs:
                    continue
                # keep the shortest few of each (diverse by attach / mid point) -- exhaustive over placements
                As.sort(key=lambda a: (plen(a[0]), len(a[0])))
                Bs.sort(key=lambda b: (plen(b[0]), len(b[0])))
                for A, ga in As[:NA]:
                    for B, ya, gb in Bs[:NB]:
                        sA = Shapes()
                        for a, b in zip(A, A[1:]):
                            sA.cap(a[0], a[1], b[0], b[1], HW, snet(n), True)
                        sB = Shapes()
                        for a, b in zip(B, B[1:]):
                            sB.cap(a[0], a[1], b[0], b[1], HW, n, True)
                        vertical_piece(n, ya, sB)
                        gi, goi = owner_gaps(sA.freeze(), sB.freeze(), 1)
                        g_int = float(goi[0])
                        if gi[0] < CU_REQ - 1e-9 or g_int < CLR + MARGIN - 1e-9:
                            continue
                        c = Cand()
                        c.net, c.kind, c.place, c.A, c.B, c.ya = n, 'R', (cx, cy, rot), A, B, ya
                        c.shapes = build_shapes(n, (cx, cy, rot), A, B, ya).freeze()
                        c.body = body
                        c.open = op
                        c.new_len = plen(A) + plen(B) + max(0.0, ya - z['top'])
                        c.static_margin = min(min(ga, gb, g_int) - CLR, place_margin)
                        c.key = (n, rot, cx, cy, tuple(map(tuple, A)), tuple(map(tuple, B)))
                        cands.append(c)
    stats[n if win is WIN else n + '_refine'] = dict(placements_tried=npl, pads_legal_alone=nlegal, candidates=len(cands),
                    placements_with_candidates=len({c.place for c in cands}), seconds=round(time.time() - t0, 1))
    log('  %-4s placements tried %d, pad-legal %d, with a legal feed+return %d, candidates %d  [%.0f s]' % (
        n, npl, nlegal, len({c.place for c in cands}), len(cands), time.time() - t0))
    return cands


def gen_jog(ctx, n, stats):
    z = NET5[n]
    V = z['via']
    cands = []
    c = Cand()
    c.net, c.kind, c.place, c.A, c.B, c.ya = n, 'orig', None, [V, (z['x'], z['top'])], None, z['top']
    c.shapes = build_shapes(n, None, c.A, False, z['top']).freeze()
    c.body, c.open, c.new_len, c.static_margin, c.key = None, None, 0.0, 0.0, (n, 'orig')
    cands.append(c)
    pj = paths_J(V, z['x'])
    bt = Shapes()
    for k, (A, ya) in enumerate(pj):
        for a, b in zip(A, A[1:]):
            bt.cap(a[0], a[1], b[0], b[1], HW, n, True, k)
        vertical_piece(n, ya, bt, k)
    g, go = owner_gaps(bt.freeze(), ctx.S, len(pj))
    for (A, ya), gh, gg in zip(pj, g, go):
        if gh < CU_REQ - 1e-9 or gg < CLR + MARGIN - 1e-9:
            continue
        c = Cand()
        c.net, c.kind, c.place, c.A, c.B, c.ya = n, 'jog', None, A, None, ya
        c.shapes = build_shapes(n, None, A, True, ya).freeze()
        c.body, c.open = None, None
        c.new_len = plen(A) + max(0.0, ya - z['top'])
        c.static_margin = float(gg) - CLR
        c.key = (n, tuple(map(tuple, A)))
        cands.append(c)
    stats[n] = dict(candidates=len(cands))
    log('  %-4s original + %d legal jogs' % (n, len(cands) - 1))
    return cands


# ------------------------------------------------------------------------------------------------ joint search
def pack(cands):
    """concatenate all candidates' shapes (owner = candidate index, contiguous) for vectorised pair tests"""
    S = Shapes()
    for i, c in enumerate(cands):
        s = c.shapes
        for k in range(len(s.C)):
            S.cap(*s.C[k], s.Cr[k], s.Cn[k], s.Cnew[k], i)
        for k in range(len(s.R)):
            S.rect(*s.R[k], s.Rn[k], s.Rnew[k], i)
    return S.freeze()


def side_arrays(cands):
    n = len(cands)
    bodies = np.zeros((n, 4))
    has = np.zeros(n, bool)
    op = np.full((n, 2, 4), [100.0, 100.0, 0.0, 0.0])
    for i, c in enumerate(cands):
        if c.body is not None:
            bodies[i] = r4(c.body)
            has[i] = True
            op[i] = c.open
    return dict(bodies=bodies, has=has, open=op)


def net_arrays(cands):
    pk = pack(cands)
    n = len(cands)
    Cb = np.stack([np.minimum(pk.C[:, 0], pk.C[:, 2]) - pk.Cr, np.minimum(pk.C[:, 1], pk.C[:, 3]) - pk.Cr,
                   np.maximum(pk.C[:, 0], pk.C[:, 2]) + pk.Cr, np.maximum(pk.C[:, 1], pk.C[:, 3]) + pk.Cr], 1) if len(pk.C) else np.zeros((0, 4))
    Rb = np.stack([pk.R[:, 0] - pk.R[:, 2], pk.R[:, 1] - pk.R[:, 3], pk.R[:, 0] + pk.R[:, 2], pk.R[:, 1] + pk.R[:, 3]], 1) if len(pk.R) else np.zeros((0, 4))
    ar = np.arange(n)
    d = dict(pk=pk, n=n, Cb=Cb, Rb=Rb, cs=np.searchsorted(pk.Co, ar, 'left'), ce=np.searchsorted(pk.Co, ar, 'right'),
             rs=np.searchsorted(pk.Ro, ar, 'left'), re=np.searchsorted(pk.Ro, ar, 'right'),
             sm=np.array([c.static_margin for c in cands], float))
    d.update(side_arrays(cands))
    return d


def compat_row(a, i, b):
    """uint8 vector over b's candidates: 0 = incompatible with a's candidate i, else the worst copper margin over the
    pair in um above 0.090 (capped 255).  Copper pairs on different nets where at least one shape is new must keep
    0.095; bodies 0.259; mask openings 0.105."""
    pa, pb = a['pk'], b['pk']
    c0, c1, r0, r1 = a['cs'][i], a['ce'][i], a['rs'][i], a['re'][i]
    AC, ACr, ACn, ACnew = pa.C[c0:c1], pa.Cr[c0:c1], pa.Cn[c0:c1], pa.Cnew[c0:c1]
    AR, ARn, ARnew = pa.R[r0:r1], pa.Rn[r0:r1], pa.Rnew[r0:r1]
    boxes = []
    if len(AC):
        boxes.append([np.minimum(AC[:, 0], AC[:, 2]).min() - ACr.max(), np.minimum(AC[:, 1], AC[:, 3]).min() - ACr.max(),
                      np.maximum(AC[:, 0], AC[:, 2]).max() + ACr.max(), np.maximum(AC[:, 1], AC[:, 3]).max() + ACr.max()])
    if len(AR):
        boxes.append([(AR[:, 0] - AR[:, 2]).min(), (AR[:, 1] - AR[:, 3]).min(), (AR[:, 0] + AR[:, 2]).max(), (AR[:, 1] + AR[:, 3]).max()])
    bx = np.array(boxes)
    reach = CLR + MARGIN + 0.02
    X0, Y0, X1, Y1 = bx[:, 0].min() - reach, bx[:, 1].min() - reach, bx[:, 2].max() + reach, bx[:, 3].max() + reach
    gap = np.full(b['n'], 9.0)
    gobj = np.full(b['n'], 9.0)
    sc = np.flatnonzero((b['Cb'][:, 0] <= X1) & (b['Cb'][:, 2] >= X0) & (b['Cb'][:, 1] <= Y1) & (b['Cb'][:, 3] >= Y0)) if len(b['Cb']) else np.zeros(0, int)
    sr = np.flatnonzero((b['Rb'][:, 0] <= X1) & (b['Rb'][:, 2] >= X0) & (b['Rb'][:, 1] <= Y1) & (b['Rb'][:, 3] >= Y0)) if len(b['Rb']) else np.zeros(0, int)
    BC, BCr, BCn, BCnew, BCo = pb.C[sc], pb.Cr[sc], pb.Cn[sc], pb.Cnew[sc], pb.Co[sc]
    BR, BRn, BRnew, BRo = pb.R[sr], pb.Rn[sr], pb.Rnew[sr], pb.Ro[sr]
    if len(AC) and len(BC):
        d = seg_seg(AC[:, None, :], BC[None, :, :]) - ACr[:, None] - BCr[None, :]
        d = np.where((ACn[:, None] != BCn[None, :]) & (ACnew[:, None] | BCnew[None, :]), d, 9.0)
        np.minimum.at(gap, BCo, d.min(0))
        np.minimum.at(gobj, BCo, np.where((d >= PITCH[0]) & (d <= PITCH[1]), 9.0, d).min(0))
    if len(AC) and len(BR):
        d = seg_rect(AC[:, None, :], BR[None, :, :]) - ACr[:, None]
        d = np.where((ACn[:, None] != BRn[None, :]) & (ACnew[:, None] | BRnew[None, :]), d, 9.0).min(0)
        _hard_obj(d, BRo, gap, gobj)
    if len(AR) and len(BC):
        d = seg_rect(BC[None, :, :], AR[:, None, :]) - BCr[None, :]
        d = np.where((ARn[:, None] != BCn[None, :]) & (ARnew[:, None] | BCnew[None, :]), d, 9.0).min(0)
        _hard_obj(d, BCo, gap, gobj)
    if len(AR) and len(BR):
        d = rect_rect(AR[:, None, :], BR[None, :, :])
        d = np.where((ARn[:, None] != BRn[None, :]) & (ARnew[:, None] | BRnew[None, :]), d, 9.0).min(0)
        _hard_obj(d, BRo, gap, gobj)
    val = np.clip(np.round((gobj - CLR) * 1000.0), 1, 255)
    val[(gap < CU_REQ - 1e-9) | (gobj < CLR + MARGIN - 1e-9)] = 0
    if a['has'][i] and b['has'].any():
        bd = rect_rect(a['bodies'][i][None, :], b['bodies'])
        md = rect_rect(a['open'][i][:, None, None, :], b['open'][None, :, :, :]).min(axis=(0, 2))
        bad = b['has'] & ((bd < COMP + MARGIN - 1e-9) | (md < MASK_SLIVER + MARGIN - 1e-9))
        bm = np.clip(np.round(np.minimum(bd - COMP, md - MASK_SLIVER) * 1000.0), 1, 255)
        val = np.where(b['has'], np.minimum(val, bm), val)
        val[bad] = 0
    return val.astype(np.uint8)


_W = {}


def _winit(arrs):
    _W.update(arrs)


def _wrows(task):
    na, nb, idx = task
    return na, nb, idx, np.stack([compat_row(_W[na], int(i), _W[nb]) for i in idx]) if len(idx) else np.zeros((0, _W[nb]['n']), np.uint8)


def matrices(arrs, pairs, workers=6):
    """dense uint8 compatibility/margin matrices for the listed net pairs, rows computed in <= 6 worker processes"""
    import multiprocessing as mp
    tasks = []
    for na, nb in pairs:
        n = arrs[na]['n']
        for s in range(0, n, 200):
            tasks.append((na, nb, np.arange(s, min(n, s + 200))))
    M = {p: np.zeros((arrs[p[0]]['n'], arrs[p[1]]['n']), np.uint8) for p in pairs}
    with mp.Pool(min(6, workers), initializer=_winit, initargs=(arrs,)) as pool:
        for na, nb, idx, rows in pool.imap_unordered(_wrows, tasks, chunksize=1):
            M[(na, nb)][idx] = rows
    return M


def search(ctx, C, stats):
    """exact cover over (D10, D11, D8, UDQM, CKE): one candidate each, all pairwise compatible.
    Pass 0 keeps UDQM and CKE on their original copper; pass 1 allows UDQM jogs (CKE original); pass 2 allows both.
    Each pass is exhaustive over its candidate sets; the first pass with a solution is used, and within it the triple
    with the largest worst copper margin (then the least new copper) wins.  Solutions are counted per pass."""
    t0 = time.time()
    R = ['D10', 'D11', 'D8']
    arrs = {n: net_arrays(C[n]) for n in NET5}
    pairs = [('D10', 'D11'), ('D10', 'D8'), ('D11', 'D8')] + [(r, u) for r in R for u in ('UDQM', 'CKE')] + [('UDQM', 'CKE')]
    M = matrices(arrs, pairs)
    stats['matrices'] = {'%s-%s' % p: dict(shape=list(M[p].shape), compatible_fraction=round(float((M[p] > 0).mean()), 4)) for p in pairs}
    log('  compatibility matrices [%.0f s]: %s' % (time.time() - t0, {k: v['compatible_fraction'] for k, v in stats['matrices'].items()}))
    sm = {n: np.clip(np.round(arrs[n]['sm'] * 1000), 0, 255).astype(np.int16) for n in NET5}
    sm['UDQM'][0] = 255
    sm['CKE'][0] = 255                                   # original copper: no new gap
    newlen = {n: np.array([c.new_len for c in C[n]]) for n in NET5}
    result = None
    stats['passes'] = []
    for pas, (Uset, Cset) in enumerate(((np.array([0]), np.array([0])),
                                         (np.arange(len(C['UDQM'])), np.array([0])),
                                         (np.arange(len(C['UDQM'])), np.arange(len(C['CKE']))))):
        tp = time.time()
        # each R candidate's best completion margin is handled per triple below; first restrict to R candidates that
        # are compatible with at least one allowed UDQM and one allowed CKE candidate
        okR = {}
        for r in R:
            okR[r] = (M[(r, 'UDQM')][:, Uset] > 0).any(1) & (M[(r, 'CKE')][:, Cset] > 0).any(1)
        n_triples = 0
        n_place = set()
        best = None
        i10s = np.flatnonzero(okR['D10'])
        for i in i10s:
            js = np.flatnonzero((M[('D10', 'D11')][i] > 0) & okR['D11'])
            if not len(js):
                continue
            ks_ok = (M[('D10', 'D8')][i] > 0) & okR['D8']
            if not ks_ok.any():
                continue
            ks = np.flatnonzero(ks_ok)
            U_i = M[('D10', 'UDQM')][i, Uset] > 0
            C_i = M[('D10', 'CKE')][i, Cset] > 0
            for j in js:
                kk = ks[M[('D11', 'D8')][j, ks] > 0]
                if not len(kk):
                    continue
                U_ij = U_i & (M[('D11', 'UDQM')][j, Uset] > 0)
                C_ij = C_i & (M[('D11', 'CKE')][j, Cset] > 0)
                if not U_ij.any() or not C_ij.any():
                    continue
                # UDQM / CKE completion for every k at once (vectorised; margin-maximising choice)
                Us, Cs = Uset[U_ij], Cset[C_ij]
                MU = np.minimum.reduce([M[('D10', 'UDQM')][i, Us].astype(int), M[('D11', 'UDQM')][j, Us].astype(int),
                                        sm['UDQM'][Us].astype(int)])                           # |U'|
                MC = np.minimum.reduce([M[('D10', 'CKE')][i, Cs].astype(int), M[('D11', 'CKE')][j, Cs].astype(int),
                                        sm['CKE'][Cs].astype(int)])
                MUk = np.minimum(MU[None, :], M[('D8', 'UDQM')][np.ix_(kk, Us)].astype(int))        # |kk| x |U'|
                MCk = np.minimum(MC[None, :], M[('D8', 'CKE')][np.ix_(kk, Cs)].astype(int))        # |kk| x |C'|
                UC = M[('UDQM', 'CKE')][np.ix_(Us, Cs)].astype(int)                                # |U'| x |C'|
                if len(Cs) == 1:
                    tot = np.minimum(MUk, np.minimum(MCk[:, 0:1], UC[None, :, 0]))                  # |kk| x |U|
                    bu = tot.argmax(1)
                    bval = tot[np.arange(len(kk)), bu]
                    bc = np.zeros(len(kk), int)
                else:
                    bval = np.zeros(len(kk), int); bu = np.zeros(len(kk), int); bc = np.zeros(len(kk), int)
                    for t in range(len(kk)):
                        tt = np.minimum(np.minimum(MUk[t][:, None], MCk[t][None, :]), UC)
                        if tt.max() > 0:
                            u_, c_ = np.unravel_index(tt.argmax(), tt.shape)
                            bval[t], bu[t], bc[t] = tt[u_, c_], u_, c_
                feas = bval > 0
                if not feas.any():
                    continue
                kf = kk[feas]
                n_triples += len(kf)
                for k in kf:
                    n_place.add((C['D10'][i].place, C['D11'][j].place, C['D8'][k].place))
                marg = np.minimum.reduce([np.full(len(kf), int(M[('D10', 'D11')][i, j])), M[('D10', 'D8')][i, kf].astype(int),
                                          M[('D11', 'D8')][j, kf].astype(int), np.full(len(kf), int(sm['D10'][i])),
                                          np.full(len(kf), int(sm['D11'][j])), sm['D8'][kf].astype(int), bval[feas]])
                us, cs_ = Us[bu[feas]], Cs[bc[feas]]
                L = newlen['D10'][i] + newlen['D11'][j] + newlen['D8'][kf] + newlen['UDQM'][us] + newlen['CKE'][cs_]
                # best: largest worst margin, then (fewer UDQM/CKE changes), then least new copper
                key = np.stack([marg, -((us != 0).astype(int) + (cs_ != 0).astype(int)), -np.round(L * 1000)], 1)
                o = np.lexsort((key[:, 2], key[:, 1], key[:, 0]))[-1]
                kb = (int(key[o, 0]), int(key[o, 1]), int(key[o, 2]))
                if best is None or kb > best[0]:
                    best = (kb, (int(i), int(j), int(kf[o]), int(us[o]), int(cs_[o])))
        rec = dict(pass_=pas, udqm_candidates=len(Uset), cke_candidates=len(Cset),
                   r_candidates_compatible_with_some_completion={r: int(okR[r].sum()) for r in R},
                   feasible_candidate_triples=n_triples, feasible_placement_triples=len(n_place),
                   best_worst_copper_margin_um=None if best is None else best[0][0], seconds=round(time.time() - tp, 1))
        stats['passes'].append(rec)
        log('  pass %d (%s): %d feasible candidate triples, %d distinct placement triples, best worst margin %s um [%.0f s]' % (
            pas, ['UDQM+CKE original', 'UDQM may jog', 'UDQM+CKE may jog'][pas], n_triples, len(n_place),
            None if best is None else best[0][0], time.time() - tp))
        if best is not None:
            result = best[1]
            stats['placement_triples'] = sorted([list(map(list, t)) for t in n_place])
            break
    stats['search_seconds'] = round(time.time() - t0, 1)
    return result


# ------------------------------------------------------------------------------------------------ plan assembly
def zone_removals(n):
    z = NET5[n]
    return [dict(net=n, layer='Top', x1=38.5, y1=z['top'], x2=z['x'], y2=z['top']),
            dict(net=n, layer='Top', x1=z['x'], y1=z['low'], x2=z['x'], y2=z['top'])]


def apply_choice(ctx, choice):
    """the 12-resistor edit list (minus R127/R130 Top edits) + the chosen D8/D10/D11(/UDQM/CKE) copper"""
    E = plan_to_E(ctx.P0, drop_top_nets=('D8', 'D11'), drop_refs=('R127', 'R130'))
    # the 12-R plan already removed the D8/D11 horizontals; with drop_top_nets those removals are gone too -> re-add
    for n, c in choice.items():
        if c.kind == 'orig':
            continue
        z = NET5[n]
        E['rm_t'] += zone_removals(n)
        if c.kind == 'R':
            for a, b in zip(c.A, c.A[1:]):
                E['add_t'].append(dict(net=snet(n), layer='Top', w=W, x1=round(a[0], 4), y1=round(a[1], 4), x2=round(b[0], 4), y2=round(b[1], 4)))
            for a, b in zip(c.B, c.B[1:]):
                E['add_t'].append(dict(net=n, layer='Top', w=W, x1=round(a[0], 4), y1=round(a[1], 4), x2=round(b[0], 4), y2=round(b[1], 4)))
            p1, p2 = pads_of(*c.place)
            ref = z['R']
            E['add_p'].append(dict(ref=ref, pad='1', layer='Top', net=snet(n), x=p1[0], y=p1[1], w=0.3, h=0.3, shape='rect', hole=0.0))
            E['add_p'].append(dict(ref=ref, pad='2', layer='Top', net=n, x=p2[0], y=p2[1], w=0.3, h=0.3, shape='rect', hole=0.0))
            bit = int(n[1:])
            E['parts'][bit] = dict(ref=ref, side='Top', x=c.place[0], y=c.place[1], rot=c.place[2])
            if not any(r['ref'] == 'U3' and r['pad'] == str(DPIN[bit]) for r in E['renet']):
                E['renet'].append(dict(ref='U3', pad=str(DPIN[bit]), net=snet(n)))
        else:
            for a, b in zip(c.A, c.A[1:]):
                E['add_t'].append(dict(net=n, layer='Top', w=W, x1=round(a[0], 4), y1=round(a[1], 4), x2=round(b[0], 4), y2=round(b[1], 4)))
        E['add_t'].append(dict(net=n, layer='Top', w=W, x1=z['x'], y1=z['low'], x2=z['x'], y2=round(c.ya, 4)))
    return E


def export(E, path_json):
    """plan_export.py's main(), applied to edit list E (renames derived from connectivity)"""
    pads, tracks, vias, newflags, errors = D.apply(E)
    assert not errors, errors
    n_old_t = len(D.board_records()[1])
    n_old_v = len(D.board_records()[2])
    objs = D.build_objs(pads, tracks, vias, newflags)
    renames_t, renames_v, problems = {}, {}, []
    for n in sorted(E['parts']):
        fam = {'D%d' % n, 'SDRAM-D%d' % n}
        sub = [o for o in objs if o.net in fam]
        uf = D.phys_islands(sub, net_aware=False)
        isl = collections.defaultdict(list)
        for k, o in enumerate(sub):
            isl[uf.f(k)].append(o)
        u3 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U3' for o in os_)]
        u1 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U1' for o in os_)]
        if len(isl) != 2 or len(u3) != 1 or len(u1) != 1 or u3[0] == u1[0]:
            problems.append('D%d: %d islands' % (n, len(isl)))
            continue
        for o in isl[u3[0]]:
            kind, i = o.uid
            if o.net == 'SDRAM-D%d' % n:
                continue
            if kind == 't':
                if i < n_old_t:
                    renames_t[i] = 'SDRAM-D%d' % n
                else:
                    tracks[i]['net'] = 'SDRAM-D%d' % n
            elif kind == 'v':
                if i < n_old_v:
                    renames_v[i] = 'SDRAM-D%d' % n
                else:
                    vias[i]['net'] = 'SDRAM-D%d' % n
        for o in isl[u1[0]]:
            if o.net != 'D%d' % n:
                problems.append('D%d: U1-side object on %s: %s' % (n, o.net, o.tag))
    assert not problems, problems
    EMIT = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}
    P = dict(source=dict(pcbdoc_md5=D.B['source']['pcbdoc_md5'],
                         plan='dq_series_r_plan.json (FIXED, 12 R) with the R127/R130 Top edits replaced by the d10/stagger '
                              'joint placement of R127 (D8), R129 (D10, new) and R130 (D11)',
                         generated_by='si/series_r/d10/stagger/design.py'),
             remove=[], remove_vias=[], tracks=[], vias=[], parts=[], renet_pads=E['renet'],
             net_class_add=dict(SDRAM_DATA=sorted({'SDRAM-D%d' % n for n in E['parts']}, key=lambda s: int(s[7:]))),
             microvias=[], renamed_existing=dict(tracks=0, vias=0))
    base_t = D.board_records()[1]
    base_v = D.board_records()[2]
    for t in E['rm_t']:
        m = [b for b in base_t if b['layer'] == t['layer'] and (not t.get('net') or b['net'] == t['net']) and (
            (D.same((t['x1'], t['y1']), (b['x1'], b['y1'])) and D.same((t['x2'], t['y2']), (b['x2'], b['y2']))) or
            (D.same((t['x1'], t['y1']), (b['x2'], b['y2'])) and D.same((t['x2'], t['y2']), (b['x1'], b['y1']))))]
        assert m, t
        b = m[0]
        P['remove'].append(dict(net=b['net'], layer=EMIT[b['layer']], w=b['w'], x1=b['x1'], y1=b['y1'], x2=b['x2'], y2=b['y2']))
    for v in E['rm_v']:
        m = [b for b in base_v if D.same((b['x'], b['y']), (v['x'], v['y'])) and b['span'] == v['span']]
        assert len(m) == 1, (v, m)
        b = m[0]
        P['remove_vias'].append(dict(net=b['net'], x=b['x'], y=b['y'], hole=b['hole'], span=[b['span'][0], b['span'][-1]]))
    for i, new in sorted(renames_t.items()):
        t = base_t[i]
        P['remove'].append(dict(net=t['net'], layer=EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
        P['tracks'].append(dict(net=new, layer=EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
        P['renamed_existing']['tracks'] += 1
    for i, new in sorted(renames_v.items()):
        v = base_v[i]
        P['remove_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], hole=v['hole'], span=[v['span'][0], v['span'][-1]], why='rename'))
        P['vias'].append(dict(net=new, x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': EMIT[v['span'][0]], 'to': EMIT[v['span'][-1]]}, why='rename'))
        P['renamed_existing']['vias'] += 1
    for i in range(n_old_t, len(tracks)):
        t = tracks[i]
        P['tracks'].append(dict(net=t['net'], layer=EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for i in range(n_old_v, len(vias)):
        v = vias[i]
        rec = dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': EMIT[v['span'][0]], 'to': EMIT[v['span'][-1]]})
        P['vias'].append(rec)
        P['microvias'].append(dict(rec, type='buried 0.27/0.15' if v['size'] < 0.29 else 'microvia 0.30/0.15'))
    byref = collections.defaultdict(dict)
    for p in E['add_p']:
        byref[p['ref']][p['pad']] = p
    for n in sorted(E['parts']):
        pr = E['parts'][n]
        p1, p2 = byref[pr['ref']]['1'], byref[pr['ref']]['2']
        P['parts'].append(dict(ref=pr['ref'], net_bit=n, side=pr['side'], footprint='R0201', comment='22',
                               x=round((p1['x'] + p2['x']) / 2, 5), y=round((p1['y'] + p2['y']) / 2, 5), rot=pr['rot'],
                               pad1=dict(net=p1['net'], x=p1['x'], y=p1['y']), pad2=dict(net=p2['net'], x=p2['x'], y=p2['y']),
                               designator_hidden=True))
    json.dump(P, open(path_json, 'w'), indent=1)
    return P


def selfcheck_reproduce(ctx):
    """the pipeline must reproduce dq_series_r_plan.json exactly when R127/R130 are put back where the 12-R plan has them"""
    E = plan_to_E(ctx.P0)
    tmp = os.path.join(HERE, '_reproduce_12R.json')
    P = export(E, tmp)
    os.remove(tmp)
    key = lambda d: json.dumps(d, sort_keys=True)
    out = {}
    for k in ('remove', 'remove_vias', 'tracks', 'vias', 'parts', 'microvias'):
        a = sorted(key(x) for x in ctx.P0[k])
        b = sorted(key(x) for x in P[k])
        out[k] = 'identical' if a == b else 'DIFFERENT (%d vs %d)' % (len(a), len(b))
    return out


# ------------------------------------------------------------------------------------------------ figure
def draw(ctx, P, choice, path_png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    col = {'Top Layer': '#c0392b', 'Bottom Layer': '#2471a3', 'L3-SIG': '#d68910', 'L4-SIG': '#7d3c98', 'L2-GND': '#1e8449', 'L5-VCC3V3': '#a04000'}
    fig, axes = plt.subplots(1, 2, figsize=(17, 9), gridspec_kw=dict(width_ratios=[1.0, 1.0]))
    rmkey = {(r['layer'], round(r['x1'], 3), round(r['y1'], 3), round(r['x2'], 3), round(r['y2'], 3)) for r in P['remove']}
    base_t = D.board_records()[1]
    base_v = D.board_records()[2]
    netcol = {'CKE': '#7f8c8d', 'D8': '#1f77b4', 'SDRAM-D8': '#1f77b4', 'UDQM': '#9467bd', 'D10': '#d62728', 'SDRAM-D10': '#d62728',
              'D11': '#2ca02c', 'SDRAM-D11': '#2ca02c'}
    for ax, (title, (x0, x1, y0, y1), after) in zip(axes, (
            ('BEFORE (12-R plan): R127 / R130 on Top, D10 has no R; Top copper only', (38.0, 41.0, 12.4, 16.4), False),
            ('AFTER (d10/stagger): R127 D8, R129 D10, R130 D11 staggered; Top copper only', (38.0, 41.0, 12.4, 16.4), True))):
        for p in D.B['pads']:
            if p['layer'] not in ('Top', 'Multi') or not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1):
                continue
            w, h = (p['w'], p['h'])
            ax.add_patch(Rectangle((p['x'] - w / 2, p['y'] - h / 2), w, h, fc='#e8c0c0', ec='none', alpha=0.7, zorder=1))
        tr = [t for t in base_t if t['layer'] == 'Top']
        for t in tr:
            if not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0):
                continue
            k = ('Top Layer', round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
            if after and k in rmkey:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=0.8, ls=':', zorder=3)
                continue
            c = netcol.get(t['net'], '#999999')
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=c, lw=max(1.0, t['w'] * 14), alpha=0.9 if t['net'] in netcol else 0.35,
                    zorder=2, solid_capstyle='round')
        for v in base_v:
            if x0 < v['x'] < x1 and y0 < v['y'] < y1 and 'Top' in v['span']:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#555555', lw=0.6, zorder=2))
        parts = P['parts'] if after else ctx.P0['parts']
        plan = P if after else ctx.P0
        for t in plan['tracks']:
            if t.get('why') == 'rename' or t['layer'] != 'Top Layer':
                continue
            c = netcol.get(t['net'], '#000000')
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=c, lw=2.2, zorder=4, solid_capstyle='round')
        if not after:
            for r in ctx.P0['remove']:
                if r['layer'] == 'Top Layer' and r.get('why') != 'rename':
                    ax.plot([r['x1'], r['x2']], [r['y1'], r['y2']], color='k', lw=0.8, ls=':', zorder=3)
        for v in plan['vias']:
            if v.get('why') == 'rename' or v['from'] != 'Top Layer':
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#000000', lw=1.2, zorder=5))
        for pr in parts:
            if pr['side'] != 'Top':
                continue
            b = body_rect(pr['x'], pr['y'], pr['rot'])
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc='none', ec='#f39c12', lw=0.8, ls='--', zorder=6))
            for pd in (pr['pad1'], pr['pad2']):
                ax.add_patch(Rectangle((pd['x'] - 0.15, pd['y'] - 0.15), 0.3, 0.3, fc='#f1c40f', ec='k', lw=0.6, zorder=6))
            ax.text(b[0] - 0.05, pr['y'], '%s D%d' % (pr['ref'], pr['net_bit']), fontsize=8, ha='right', va='center', zorder=7, fontweight='bold')
        if not after:
            ax.text(39.2, 14.25, 'no room for R129 (D10):\nbody gap to R130 0.004 mm', fontsize=7, ha='center', color='#d62728')
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.2)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=netcol[k], lw=2, label=k) for k in ('CKE', 'D8', 'UDQM', 'D10', 'D11')]
    h += [Line2D([], [], color='k', ls=':', label='removed'), Line2D([], [], marker='s', color='#f1c40f', ls='', label='R pad (0201)'),
          Line2D([], [], color='#f39c12', ls='--', label='body proxy 0.90 x 0.396')]
    axes[1].legend(handles=h, fontsize=7, loc='upper right')
    fig.suptitle('D10 series resistor, strategy "stagger": three Top 0201s re-positioned jointly (board coords mm, y up, viewed from Top)', fontsize=10)
    fig.tight_layout()
    fig.savefig(path_png, dpi=150)


# ------------------------------------------------------------------------------------------------ main
def main():
    global GRID
    t0 = time.time()
    P0 = json.load(open(os.path.join(SR, 'dq_series_r_plan.json')))
    log('==== d10/stagger design.py  (PcbDoc md5 %s, base plan %s) ====' % (D.B['source']['pcbdoc_md5'], 'dq_series_r_plan.json'))
    log('grid %.3f mm, window %s, feed/return variants kept per placement %d/%d' % (GRID, WIN, NA, NB))
    ctx = Ctx(P0)
    rep = selfcheck_reproduce(ctx)
    log('pipeline self-check (re-export the 12-R plan from its own edit list): %s' % rep)
    assert all(v == 'identical' for v in rep.values()), rep
    log('static Top copper near the staircase: %d capsules, %d rects; %d through-via lands; %d pad openings; %d proxies' % (
        len(ctx.S.C), len(ctx.S.R), len(ctx.thru), len(ctx.openings), len(ctx.prox)))
    stats = {}
    C = {}
    log('\n-- candidates (each legal alone, exact geometry, margin %.3f) --' % MARGIN)
    for n in NET5:
        C[n] = gen_rnet(ctx, n, stats) if NET5[n]['R'] else gen_jog(ctx, n, stats)
    out = dict(script=os.path.abspath(__file__), source=D.B['source'], rules=dict(
        clearance=CLR, margin=MARGIN, component_clearance=COMP, body_proxy=BODY, mask_expansion=MASK_EXP, mask_sliver=MASK_SLIVER,
        silk_to_mask=SILK, width_top=W, grid=GRID, window=WIN, yc=YC, variants_kept=(NA, NB)), stats=stats)
    if GEN_ONLY:
        json.dump(out, open(os.path.join(HERE, 'design_gen.json'), 'w'), indent=1, default=str)
        return
    cache = os.path.join(HERE, 'coarse_cache.json')
    if '--reuse-coarse' in sys.argv and os.path.exists(cache):
        cc = json.load(open(cache))
        log('\n-- joint exact-cover search: REUSED from coarse_cache.json (written by the full run of %s) --' % cc['written'])
        for ln in cc['log']:
            log(ln)
        stats.update(cc['stats'])
        res = tuple(cc['res'])                    # candidate generation is deterministic, indices are stable
    else:
        log('\n-- joint exact-cover search --')
        n0 = len(LOG)
        res = search(ctx, C, stats)
        if res is not None:
            json.dump(dict(written=time.strftime('%Y-%m-%d %H:%M:%S'), log=LOG[n0:], stats=stats, res=list(res),
                           winner={n: list(C[n][i].place) for n, i in (('D10', res[0]), ('D11', res[1]), ('D8', res[2]))}),
                      open(cache, 'w'), indent=1, default=str)
    if res is None:
        log('NO joint solution')
        out['d10_placed'] = False
        json.dump(out, open(os.path.join(HERE, 'design.json'), 'w'), indent=1, default=str)
        open(os.path.join(HERE, 'design.log'), 'w').write('\n'.join(LOG) + '\n')
        return
    i10, i11, i8, iU, iC = res
    coarse = {n: C[n][i].place for n, i in (('D8', i8), ('D10', i10), ('D11', i11))}
    out['coarse_winner'] = coarse
    out['coarse_stats'] = json.loads(json.dumps(stats, default=str))
    # ---- refinement: the same exhaustive search on a 0.01 mm grid, +-RF mm around the coarse winner's three centres
    GRID = 0.01
    RF = 0.08
    log('\n-- refinement: grid %.3f mm, +-%.2f mm around %s (same rotations) --' % (GRID, RF, coarse))
    stats2 = {}
    C2 = dict(C)
    for n, (cx, cy, rot) in coarse.items():
        C2[n] = gen_rnet(ctx, n, stats2, win=(cx - RF, cx + RF, cy - RF, cy + RF), rots=(rot,))
    res2 = search(ctx, C2, stats2)
    out['refine_stats'] = json.loads(json.dumps(stats2, default=str))
    if res2 is not None:
        C, stats, res = C2, stats2, res2
    i10, i11, i8, iU, iC = res
    choice = collections.OrderedDict([('CKE', C['CKE'][iC]), ('D8', C['D8'][i8]), ('UDQM', C['UDQM'][iU]),
                                      ('D10', C['D10'][i10]), ('D11', C['D11'][i11])])
    log('\n-- chosen --')
    for n, c in choice.items():
        log('  %-4s %-4s place=%s A=%s B=%s attach y=%.4f new copper %.3f mm static margin %+.4f' % (
            n, c.kind, c.place, [tuple(round(v, 4) for v in p) for p in c.A] if c.A else None,
            [tuple(round(v, 4) for v in p) for p in c.B] if c.B else None, c.ya, c.new_len, c.static_margin))
    out['chosen'] = {n: dict(kind=c.kind, place=c.place, A=c.A, B=c.B, attach_y=c.ya, new_copper_mm=round(c.new_len, 4),
                             static_margin=round(c.static_margin, 4)) for n, c in choice.items()}
    E = apply_choice(ctx, choice)
    P = export(E, os.path.join(HERE, 'plan.json'))
    log('\nplan.json: remove %d tracks (%d renames), remove %d vias (%d renames), add %d tracks, add %d vias (%d new), %d parts' % (
        len(P['remove']), P['renamed_existing']['tracks'], len(P['remove_vias']), P['renamed_existing']['vias'],
        len(P['tracks']), len(P['vias']), len(P['microvias']), len(P['parts'])))
    draw(ctx, P, choice, os.path.join(HERE, 'plan.png'))
    out['d10_placed'] = True
    out['runtime_s'] = round(time.time() - t0, 1)
    json.dump(out, open(os.path.join(HERE, 'design.json'), 'w'), indent=1, default=str)
    open(os.path.join(HERE, 'design.log'), 'w').write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
