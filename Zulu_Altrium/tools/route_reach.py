# -*- coding: utf-8 -*-
"""Global routability: does a plan wall off any connection that is not routed yet?

    python tools/route_reach.py                               the board as saved
    python tools/route_reach.py <plan.json> [...]             the board plus plan(s)
    python tools/route_reach.py --inputs I.json --drc R.drc <plan.json>
                                                              another board state

route_foreclosure.py asks a LOCAL question -- does each U1 escape, and each pad near
a plan, keep a via slot?  A long trunk can pass that and still cut the board in
two.  This asks the global one, for every un-routed connection of a net the plans
do not own (GND/GNDADC excepted -- they join through vias to the L2/L5 planes, and
the pad audit already keeps every GND pad a via slot):

  The four signal layers (Top, L3-SIG, L4-SIG, Bottom) are rasterised at CELL mm.
  A cell is free for a 3 mil track centreline on a layer if no foreign object on
  that layer comes within (its clearance + half the track width): pads on their
  layer, through-hole pads and vias on every layer, tracks on their layer, keep-out
  fills, and a band EDGE mm inside the board outline.  SDRAM copper keeps 0.10 on
  L3/L4 (0.20 for SDRAM-CLK), everything else 0.09.
  A cell is via-legal if a 0.35 mm via land centred there keeps 0.09 from every
  object on every layer (SMD pads of any net: no via-in-pad), 0.44 centre-to-centre
  from every via, stays outside U1's land field (interstices are forbidden) and the
  board-edge band.
  For the connection's own net, its existing copper is carved free, its tracks
  stop blocking vias, and its existing vias and through-hole pads join all four
  layers wherever they stand.  Each layer is labelled into 8-connected regions;
  regions on different layers are joined wherever a via-legal cell is free on all
  four.  The connection is routable iff its two end objects touch one joined region.

  SPANS (2026-09-29, HDI): a via occupies only the layers of its span (route_inputs.json 'span',
  default through).  It blocks and joins only the signal layers in that span, and the via raster
  is built once per candidate span tools/hdi.json allows (pitch per pair of spans, land per span,
  the land-field ban only for spans that reach Bottom or are not via-in-pad spans, an own-net SMD
  pad's centre legal for a via-in-pad span).  With hdi.json at its through-only default this is
  exactly the model above.

The connection list comes from a DRC report (the Un-Routed Net Constraint entries);
by default Altium's latest report, which must describe the same board state as the
inputs.  Exit 1 if any connection routable on the board is not routable with the
plan(s).  Necessary, not sufficient: it proves a corridor exists for one net at a
time, not that all of them fit together.
"""
import argparse
import io
import json
import math
import os
import re
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hdi

RI = os.path.join(HERE, 'route_inputs.json')
DRC = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb', 'Project Outputs for zulu_a7', 'Design Rule Check - zulu_a7.drc')
LAYERS = ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')
DRC_LAYER = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'Multi-Layer': 'Multi',
             'L2-GND': 'L2-GND', 'L5-VCC3V3': 'L5-VCC3V3'}
CELL = 0.025
HALF_W = 0.0381           # half a 3 mil track
# the THROUGH via as every gate modelled it before 2026-09-29; kept by name for the modules that import
# them (stage6/capacity, corr, route_width, stage7/escape_audit).  Per-span values come from hdi.json:
# a via blocks only the signal layers in its span, and the via raster is built per candidate span.
VIA_R = 0.175
PITCH = 0.44
C = 0.09
SKIP = {'GND', 'GNDADC'}


class Raster:
    def __init__(self, ol):
        self.x0, self.y0 = ol['x0'], ol['y0']
        self.nx = int(math.ceil((ol['x1'] - ol['x0']) / CELL)) + 1
        self.ny = int(math.ceil((ol['y1'] - ol['y0']) / CELL)) + 1

    def window(self, xa, ya, xb, yb):
        i0 = max(int(math.floor((xa - self.x0) / CELL)), 0)
        i1 = min(int(math.ceil((xb - self.x0) / CELL)) + 1, self.nx)
        j0 = max(int(math.floor((ya - self.y0) / CELL)), 0)
        j1 = min(int(math.ceil((yb - self.y0) / CELL)) + 1, self.ny)
        if i0 >= i1 or j0 >= j1:
            return None
        xs = self.x0 + np.arange(i0, i1) * CELL
        ys = self.y0 + np.arange(j0, j1) * CELL
        X, Y = np.meshgrid(xs, ys)
        return (slice(j0, j1), slice(i0, i1)), X, Y


def shape_mask(R, obj, grow):
    """(slices, bool mask) of the cells within `grow` of the object's copper"""
    k = obj['kind']
    if k == 'rect':
        hx, hy = obj['sx'] / 2 + grow, obj['sy'] / 2 + grow
        w = R.window(obj['x'] - hx, obj['y'] - hy, obj['x'] + hx, obj['y'] + hy)
        if w is None:
            return None
        sl, X, Y = w
        dx = np.maximum(np.abs(X - obj['x']) - obj['sx'] / 2, 0)
        dy = np.maximum(np.abs(Y - obj['y']) - obj['sy'] / 2, 0)
        return sl, np.hypot(dx, dy) <= grow + 1e-9
    if k == 'circle':
        r = obj['r'] + grow
        w = R.window(obj['x'] - r, obj['y'] - r, obj['x'] + r, obj['y'] + r)
        if w is None:
            return None
        sl, X, Y = w
        return sl, np.hypot(X - obj['x'], Y - obj['y']) <= r + 1e-9
    if k == 'seg':
        r = obj['w'] / 2 + grow
        w = R.window(min(obj['x1'], obj['x2']) - r, min(obj['y1'], obj['y2']) - r, max(obj['x1'], obj['x2']) + r, max(obj['y1'], obj['y2']) + r)
        if w is None:
            return None
        sl, X, Y = w
        dx, dy = obj['x2'] - obj['x1'], obj['y2'] - obj['y1']
        L2 = dx * dx + dy * dy
        if L2 == 0:
            d = np.hypot(X - obj['x1'], Y - obj['y1'])
        else:
            t = np.clip(((X - obj['x1']) * dx + (Y - obj['y1']) * dy) / L2, 0, 1)
            d = np.hypot(X - (obj['x1'] + t * dx), Y - (obj['y1'] + t * dy))
        return sl, d <= r + 1e-9
    raise ValueError(k)


def world(inp, plans):
    """list of copper objects: dict(kind, geometry, net, layers, clr_inner, is_pad)"""
    sdram = {n for n, v in inp['nets'].items() if v.get('cls', '').startswith('SDRAM')}
    H = hdi.load(inp)
    vias = [dict(v) for v in inp['vias']]
    tracks = [dict(t) for t in inp['tracks']]
    for p in plans:
        rem = p.get('remove') or {}
        kv = lambda v: (v['net'], round(v['x'], 4), round(v['y'], 4), hdi.span_of(v))
        rv = {kv(v) for v in rem.get('vias', [])}
        key = lambda t: (t['net'], t['layer']) + tuple(sorted(((round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4)))))
        rt = {key(t) for t in rem.get('tracks', [])}
        vias = [v for v in vias if kv(v) not in rv]
        tracks = [t for t in tracks if key(t) not in rt]
        vias += [dict(x=v['x'], y=v['y'], size=H.land(hdi.span_of(v)), hole=H.hole(hdi.span_of(v)), net=v['net'],
                      span=list(hdi.span_of(v))) for v in p.get('vias', [])]
        tracks += [dict(t) for t in p.get('tracks', [])]

    def inner_clr(net):
        if net == 'SDRAM-CLK':
            return 0.20
        return 0.10 if net in sdram else C
    objs = []
    for q in inp['top_pads']:
        objs.append(dict(kind='rect', x=q['x'], y=q['y'], sx=q['sx'], sy=q['sy'], net=q['net'], layers=('Top',), pad=True, ref=q['ref'], name=q['pad']))
    for q in inp['bottom_pads']:
        objs.append(dict(kind='rect', x=q['x'], y=q['y'], sx=q['sx'], sy=q['sy'], net=q['net'], layers=('Bottom',), pad=True, ref=q['ref'], name=q['pad']))
    for q in inp['th_pads']:
        objs.append(dict(kind='rect', x=q['x'], y=q['y'], sx=q['sx'], sy=q['sy'], net=q['net'], layers=LAYERS, pad=True, ref=q['ref'], name=q['pad']))
    for v in vias:
        sp = hdi.span_of(v)                 # a via blocks / joins only the signal layers in its span
        objs.append(dict(kind='circle', x=v['x'], y=v['y'], r=v.get('size', 0.35) / 2, net=v['net'], layers=hdi.signal_layers(sp),
                         pad=False, via=True, span=sp, inner=inner_clr(v['net'])))
    for t in tracks:
        objs.append(dict(kind='seg', x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], w=t['width'], net=t['net'], layers=(t['layer'],),
                         pad=False, inner=inner_clr(t['net'])))
    for k in inp.get('keepouts', []):
        objs.append(dict(kind='rect', x=(k['x0'] + k['x1']) / 2, y=(k['y0'] + k['y1']) / 2, sx=k['x1'] - k['x0'], sy=k['y1'] - k['y0'],
                         net='__keepout__', layers=(k['layer'],), pad=False, keepout=True))
    return objs


def clr_on(obj, layer):
    if layer in ('L3-SIG', 'L4-SIG') and 'inner' in obj:
        return obj['inner']
    return C


def _centre_cells(R, sl, x, y):
    """within the window sl: the cells within 0.75 CELL of (x, y) -- one via centre.  For a via-in-pad
    this frees the raster cell nearest the pad centre, which can sit up to 0.0177 mm (half a cell
    diagonal) off the centre where route_emit demands the via (PAD_CENTRE 1 um): the cell only FLAGS
    that the centre is legal; a site proposer must return the pad's exact centre (corr.via_sites does)"""
    X = R.x0 + np.arange(sl[1].start, sl[1].stop) * CELL
    Y = R.y0 + np.arange(sl[0].start, sl[0].stop) * CELL
    return (np.abs(Y - y) <= CELL * 0.75)[:, None] & (np.abs(X - x) <= CELL * 0.75)[None, :]


def accumulate(R, objs, sign, track_cov, via_cov, own_net=None, H=None):
    """add (sign=+1) or remove (sign=-1) objects' cover.  With own_net set, only that net's
    tracks and vias are touched in via_cov (own pads still forbid a via-in-pad, own vias still
    set the pitch).

    via_cov is one raster per CANDIDATE via span ({span: raster}); a plain array is the through
    raster, as before 2026-09-29.  An object contributes to a span's raster only where it meets the
    span: a via if the two spans share a layer, grown by hdi's pitch for the pair; a pad, track or
    keep-out if it lies on a signal layer of the span, grown by its clearance + that span's land
    radius.  With own_net set, an own SMD pad on the outer layer of a via-in-pad span (and, when
    hdi.json allows stacking, an own via of an adjacent span) stops blocking at its centre cell."""
    H = H or hdi.default()
    covs = via_cov if isinstance(via_cov, dict) else {hdi.THROUGH: via_cov}
    for o in objs:
        for L in o['layers']:
            li = LAYERS.index(L)
            m = shape_mask(R, o, clr_on(o, L) + HALF_W)
            if m is not None:
                sl, mask = m
                track_cov[li][sl] += sign * mask.astype(np.int16)
        for S, cov in covs.items():
            if o.get('via'):
                need = H.pitch_between(o['span'], S)
                if need is None:
                    continue
                g = need - o['r']
                free_centre = (own_net is not None and o['net'] == own_net and H.stacking and hdi.adjacent(o['span'], S))
            else:
                Ls = [L for L in o['layers'] if L in S]
                if not Ls:
                    continue
                g = max(clr_on(o, L) for L in Ls) + H.land(S) / 2
                free_centre = (own_net is not None and o.get('pad') and o['net'] == own_net and len(o['layers']) == 1 and
                               H.via_in_pad(S) and o['layers'][0] in H.outer(S))
            if own_net is not None and (o.get('pad') or o.get('via')):
                if free_centre:                 # via-in-pad / stack: only the centre cell is given back
                    m = shape_mask(R, o, g)
                    if m is not None:
                        sl, mask = m
                        cov[sl] += sign * (mask & _centre_cells(R, sl, o['x'], o['y'])).astype(np.int16)
                continue
            m = shape_mask(R, o, g)
            if m is not None:
                sl, mask = m
                cov[sl] += sign * mask.astype(np.int16)


def base_rasters(R, inp, objs, spans=None):
    """(track_cov per layer, via_cov, edge_t, edge_v).  With `spans` (candidate via spans) via_cov
    and edge_v are dicts keyed by span; without, they are the through raster as before."""
    H = hdi.load(inp)
    single = spans is None
    spans = [hdi.THROUGH] if single else [tuple(S) for S in spans]
    track_cov = [np.zeros((R.ny, R.nx), np.int16) for _ in LAYERS]
    via_cov = {S: np.zeros((R.ny, R.nx), np.int16) for S in spans}
    accumulate(R, objs, +1, track_cov, via_cov, H=H)
    X = R.x0 + np.arange(R.nx) * CELL
    Y = R.y0 + np.arange(R.ny) * CELL
    ol = inp['outline']
    e = inp.get('edge_clearance', 0.25)
    ex = (X < ol['x0'] + e + HALF_W) | (X > ol['x1'] - e - HALF_W)
    ey = (Y < ol['y0'] + e + HALF_W) | (Y > ol['y1'] - e - HALF_W)
    edge_t = ey[:, None] | ex[None, :]
    lf = inp['land_field']
    field = ((Y[:, None] >= lf['y0']) & (Y[:, None] <= lf['y1'])) & ((X[None, :] >= lf['x0']) & (X[None, :] <= lf['x1']))
    edge_v = {}
    for S in spans:
        r = H.land(S) / 2
        exv = (X < ol['x0'] + e + r) | (X > ol['x1'] - e - r)
        eyv = (Y < ol['y0'] + e + r) | (Y > ol['y1'] - e - r)
        ev = eyv[:, None] | exv[None, :]
        # U1's land field is banned for a via that reaches Bottom or is not a via-in-pad span
        edge_v[S] = (ev | field) if H.field_ban(S) else ev
    if single:
        return track_cov, via_cov[hdi.THROUGH], edge_t, edge_v[hdi.THROUGH]
    return track_cov, via_cov, edge_t, edge_v


def own_cells(R, objs):
    """per layer: cells covered by the net's own copper (no growth)"""
    out = [np.zeros((R.ny, R.nx), bool) for _ in LAYERS]
    for o in objs:
        if o.get('keepout'):
            continue
        for L in o['layers']:
            m = shape_mask(R, o, 0.0)
            if m is not None:
                sl, mask = m
                out[LAYERS.index(L)][sl] |= mask
    return out


def endpoint_cells(R, ep, inp_objs):
    """per layer: cells of the connection end object (a pad, a via or a track)"""
    out = [np.zeros((R.ny, R.nx), bool) for _ in LAYERS]
    o = ep['obj']
    m = shape_mask(R, o, CELL * 0.75)
    if m is not None:
        sl, mask = m
        for L in o['layers']:
            out[LAYERS.index(L)][sl] |= mask
    return out


def reachable_for_net(R, net, conns, base, objs, H=None):
    track_cov, via_cov, edge_t, edge_v = base
    if not isinstance(via_cov, dict):
        via_cov, edge_v = {hdi.THROUGH: via_cov}, {hdi.THROUGH: edge_v}
    H = H or hdi.default()
    own = [o for o in objs if o['net'] == net]
    tc = [c.copy() for c in track_cov]
    vc = {S: c.copy() for S, c in via_cov.items()}
    accumulate(R, own, -1, tc, vc, own_net=net, H=H)
    oc = own_cells(R, own)
    free = [((tc[i] <= 0) & ~edge_t) | oc[i] for i in range(4)]
    # a layer change is legal for a span where its raster is clear and every signal layer of the
    # span is free; it joins only those layers (a Top..L3 microvia never joins Bottom)
    via_ok = {}
    for S in vc:
        idx = [LAYERS.index(L) for L in hdi.signal_layers(S)]
        if len(idx) < 2:
            continue
        ok = (vc[S] <= 0) & ~edge_v[S]
        for i in idx:
            ok &= free[i]
        via_ok[S] = (idx, ok)
    st = np.ones((3, 3), int)
    labels = []
    offset = 0
    for i in range(4):
        lab, n = ndimage.label(free[i], structure=st)
        lab = lab.astype(np.int64)
        lab[lab > 0] += offset
        labels.append(lab)
        offset += n
    parent = np.arange(offset + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for S, (idx, ok) in via_ok.items():
        ys, xs = np.nonzero(ok)
        if ys.size:
            quad = np.stack([labels[i][ys, xs] for i in idx], axis=1)
            quad = np.unique(quad, axis=0)
            for row in quad:
                r0 = find(int(row[0]))
                for v in row[1:]:
                    rv = find(int(v))
                    if rv != r0:
                        parent[rv] = r0
    # the net's EXISTING vias and through-hole pads join their layers unconditionally: they are
    # copper through the board already, wherever a new via would or would not be legal (a moat
    # via inside U1's land field was once reported as a dead end).  A via joins only the signal
    # layers of its span.
    for o in own:
        if (o.get('via') or len(o['layers']) == 4) and not o.get('keepout'):
            m = shape_mask(R, o, 0.0)
            if m is None:
                continue
            sl, mask = m
            ids = set()
            for i in [LAYERS.index(L) for L in o['layers']]:
                ids |= {int(l) for l in np.unique(labels[i][sl][mask]) if l > 0}
            ids = sorted(ids)
            if ids:
                r0 = find(ids[0])
                for v in ids[1:]:
                    rv = find(v)
                    if rv != r0:
                        parent[rv] = r0
    out = []
    for c in conns:
        roots = []
        for ep in (c['a'], c['b']):
            cells = endpoint_cells(R, ep, objs)
            rs = set()
            for i in range(4):
                ls = labels[i][cells[i]]
                rs |= {find(int(l)) for l in np.unique(ls) if l > 0}
            roots.append(rs)
        out.append(bool(roots[0] & roots[1]))
    return out


def parse_connections(inp, drc_path, owned):
    h = io.open(drc_path, encoding='latin-1').read()
    seg = h[h.index('Processing Rule : Un-Routed Net Constraint'):]
    seg = seg[:seg.find('Rule Violations :')]
    pads = {}
    for q in inp['top_pads']:
        pads[(q['ref'] + '-' + q['pad'], 'Top')] = dict(kind='rect', x=q['x'], y=q['y'], sx=q['sx'], sy=q['sy'], layers=('Top',))
    for q in inp['bottom_pads']:
        pads[(q['ref'] + '-' + q['pad'], 'Bottom')] = dict(kind='rect', x=q['x'], y=q['y'], sx=q['sx'], sy=q['sy'], layers=('Bottom',))
    for q in inp['th_pads']:
        pads[(q['ref'] + '-' + q['pad'], 'Multi')] = dict(kind='rect', x=q['x'], y=q['y'], sx=q['sx'], sy=q['sy'], layers=LAYERS)
    obj_re = re.compile(r"(Pad ([^\s(]+)\(([-\d.]+)mm,([-\d.]+)mm\) on ([A-Za-z0-9 -]+?)(?= And |\s*$))|"
                        r"(Track \(([-\d.]+)mm,([-\d.]+)mm\)\(([-\d.]+)mm,([-\d.]+)mm\) on ([A-Za-z0-9 -]+?)(?= And |\s*$))|"
                        r"(Via \(([-\d.]+)mm,([-\d.]+)mm\) from ([A-Za-z0-9 -]+?) to ([A-Za-z0-9 -]+?)(?= And |\s*$))")
    conns = []
    bad = 0
    unknown = set()
    for net, body in re.findall(r'Un-Routed Net Constraint: Net (\S+) Between (.*?)\n', seg):
        if net in owned or net in SKIP:
            continue
        eps = []
        for m in obj_re.finditer(body.strip()):
            if m.group(1):
                layer = DRC_LAYER.get(m.group(5).strip(), m.group(5).strip())
                o = pads.get((m.group(2), layer))
                if o is None:
                    o = dict(kind='rect', x=float(m.group(3)), y=float(m.group(4)), sx=0.2, sy=0.2, layers=(layer,) if layer != 'Multi' else LAYERS)
                eps.append(dict(desc=m.group(2), obj=o))
            elif m.group(6):
                layer = DRC_LAYER.get(m.group(11).strip(), m.group(11).strip())
                eps.append(dict(desc='track', obj=dict(kind='seg', x1=float(m.group(7)), y1=float(m.group(8)), x2=float(m.group(9)), y2=float(m.group(10)), w=0.0762, layers=(layer,))))
            elif m.group(12):
                # 'from Top Layer to Bottom Layer' round-trips to the through span; a microvia's span is
                # the stack between its two layer names, and it joins only the signal layers in it.  A
                # layer name the stack does not know (a plane printed under another name?) leaves the
                # entry unparsed, like every other malformed endpoint, and is named on stderr
                lo, hi = (DRC_LAYER.get(m.group(k).strip(), m.group(k).strip()) for k in (15, 16))
                try:
                    sp = hdi.span_between(lo, hi)
                except ValueError:
                    unknown.update(L for L in (lo, hi) if L not in hdi.STACK)
                    eps = None
                    break
                eps.append(dict(desc='via', obj=dict(kind='circle', x=float(m.group(13)), y=float(m.group(14)), r=0.175,
                                                     layers=hdi.signal_layers(sp), span=sp)))
        if eps is None or len(eps) != 2:
            bad += 1
            continue
        conns.append(dict(net=net, a=eps[0], b=eps[1]))
    if unknown:
        sys.stderr.write('route_reach: DRC via endpoints on layer(s) %s are not on hdi.STACK %s; those entries are unparsed\n'
                         % (', '.join(sorted(unknown)), '/'.join(hdi.STACK)))
    return conns, bad


def evaluate(R, inp, plans, conns):
    objs = world(inp, plans)
    H = hdi.load(inp)
    # one via raster per candidate span hdi.json allows that can join two signal layers
    spans = [S for S in H.allowed() if len(hdi.signal_layers(S)) >= 2]
    base = base_rasters(R, inp, objs, spans)
    by = {}
    for i, c in enumerate(conns):
        by.setdefault(c['net'], []).append(i)
    res = [None] * len(conns)
    for net, idx in by.items():
        ok = reachable_for_net(R, net, [conns[i] for i in idx], base, objs, H)
        for i, v in zip(idx, ok):
            res[i] = v
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plans', nargs='*')
    ap.add_argument('--inputs', default=RI)
    ap.add_argument('--drc', default=DRC)
    a = ap.parse_args()
    inp = json.load(io.open(a.inputs, encoding='utf-8'))
    plans = [json.load(io.open(p, encoding='utf-8')) for p in a.plans]
    # 2026-09-15: the nets the plans TOUCH are theirs to finish; every other net must stay routable
    owned = set()
    for p in plans:
        owned |= {v['net'] for v in p.get('vias', [])} | {t['net'] for t in p.get('tracks', [])}
    R = Raster(inp['outline'])
    conns, bad = parse_connections(inp, a.drc, owned)
    print('%d un-routed connections of nets the plan(s) do not touch (GND/GNDADC excepted) from %s%s' % (
        len(conns), os.path.basename(a.drc), (', %d entries unparsed' % bad) if bad else ''))
    import hashlib, tempfile
    h = hashlib.md5()
    for pth in (a.inputs, a.drc, os.path.abspath(__file__), hdi.PATH, os.path.join(HERE, 'hdi.py')):
        if os.path.exists(pth):
            h.update(io.open(pth, 'rb').read())
    h.update(json.dumps(inp.get('hdi'), sort_keys=True).encode('utf-8'))   # the span model in force
    cache = os.path.join(tempfile.gettempdir(), 'route_reach_board_%s.json' % h.hexdigest())
    keyc = lambda c: '%s|%s|%s' % (c['net'], c['a']['desc'], c['b']['desc'])
    known = json.load(io.open(cache, encoding='utf-8')) if os.path.exists(cache) else {}
    todo = [c for c in conns if keyc(c) not in known]
    if todo:
        for c, ok in zip(todo, evaluate(R, inp, [], todo)):
            known[keyc(c)] = ok
        io.open(cache, 'w', encoding='utf-8').write(json.dumps(known))
    r0 = [known[keyc(c)] for c in conns]
    blocked0 = [c for c, ok in zip(conns, r0) if not ok]
    print('routable on the board: %d / %d' % (len(conns) - len(blocked0), len(conns)))
    for c in blocked0:
        print('   already NOT routable: %-14s %s <-> %s' % (c['net'], c['a']['desc'], c['b']['desc']))
    if not plans:
        return 0
    r1 = evaluate(R, inp, plans, conns)
    lost = [c for c, ok0, ok1 in zip(conns, r0, r1) if ok0 and not ok1]
    print('routable with the plan(s): %d / %d' % (sum(1 for v in r1 if v), len(conns)))
    for c in lost:
        print('   WALLED OFF BY THE PLAN: %-14s %s <-> %s' % (c['net'], c['a']['desc'], c['b']['desc']))
    print('connections walled off by the plan(s): %s' % (len(lost) if lost else 'none'))
    return 1 if lost else 0


if __name__ == '__main__':
    sys.exit(main())
