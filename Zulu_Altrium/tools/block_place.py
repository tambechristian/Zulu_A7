# -*- coding: utf-8 -*-
"""Re-place the regulator/charger block on the Bottom side, prove it legal, measure its power loops.

    python tools/block_place.py <placement.json>                          check + metrics
    python tools/block_place.py <placement.json> --plan <route.json>      also: the block's own
                                                                          copper makes every loop
    python tools/block_place.py <placement.json> --write-inputs <out.json>
                                                  route_inputs.json with the parts moved, for
                                                  route_emit / route_foreclosure / route_reach --inputs
    python tools/block_place.py <placement.json> --plan <route.json> --write-inputs <out.json> --merge-plan
                                                  the same with the plan copper added as board copper:
                                                  route_reach --inputs <out.json> then tests every net
    python tools/block_place.py <placement.json> <Name> --write           Place<Name> / Restore<Name>
                                                                          into tools/ZuluSetup.pas

WHY (2026-09-15, power feeds).  tools/place_board.py shelf-packed the PWR block by size, not by
circuit.  On the saved board each SC189's LX pin (y 4.55) faces AWAY from its inductor (y 9.05)
across its own VIN/GND/EN row, with 0.30 mm pin gaps a 0.20 mm track cannot pass; the shortest
Bottom-only LX routes are 8.3 / 20.1 / 13.6 mm.  The input caps sit 2.9-3.1 mm (pad edge) from
VIN and the output caps' GND pads 6-10 mm from the IC GND pin; the bq24232's IN, OUT and BAT caps
are 5-8 mm from their pins.  SC189 datasheet p21 (layout considerations 1 and 2) and bq24232
SLUS821J section 11.1 both require all of these as close to the IC as possible.

placement.json
    {"moves": [{"ref": "U5", "rot": 180, "pad": "1", "x": 3.40, "y": 4.55}, ...],
     "roles": {"U5": {"l": "L1", "cin": "C147", "cout": "C80"}, ...,
               "U8": {"cin": "C150", "cout": "C78", "cbat": "C151"}},
     "net_fixes": [{"ref": "R78", "pad": "1", "net": "GND"}],
     "hide_designators": ["U5"]}      designators with no room clear of pads (Silk To Solder Mask)
  rot is the counter-clockwise turn of the part's copper as seen from the Top (board axes,
  multiple of 90) applied to its CURRENT pads; the named pad's centre lands on (x, y).  Parts not
  listed stay where they are.  Only the PWR block may move, plus any ref the placement names in an
  explicit "movable" list (2026-09-16: C124 moving under U1).

LEGALITY (the conventions tools/place_board.py placed the board with)
    land to land between different components >= 0.30 mm (Bottom SMD and every through-hole pad)
    pad copper to the board outline >= 0.30 mm
    courtyard-lite: the pad-extent box of each part -- widened to the 3.10 x 1.75 mm maximum
    moulded body of a SOT23-5 (SC189 p23: D 2.80-3.10, E1 1.50-1.75), which runs up to 0.30 mm
    past its end pads -- overlaps no other part's box.  On the saved board U5/U6/U7 sit end to end
    with 0.30 mm pad gaps, so their bodies touch at minimum D and overlap 0.30 mm at maximum.
    moved copper >= 0.09 mm from every existing Bottom track and via
"""
import copy
import io
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(HERE, 'route_inputs.json')
SETUP = os.path.join(HERE, 'ZuluSetup.pas')

BLOCK = ('U5 U6 U7 U8 L1 L2 L3 C78 C80 C82 C84 C147 C148 C149 C150 C151 '
         'R78 R102 R103 R104 R105 R106 R107 R108').split()
SC189 = ('U5', 'U6', 'U7')
LAND_CLEAR = 0.30
EDGE = 0.30
SOT_BODY = (3.10, 1.75)          # SC189 p23 SOT23-5 outline, MAX D along the pin rows and MAX E1
                                 # across them (both exclude mould flash)
VIA_LAND, VIA_PITCH, C = 0.35, 0.44, 0.09
EPS = 1e-6


# ------------------------------------------------------------------ geometry
def rect_gap(a, b):
    dx = max(abs(a['x'] - b['x']) - (a['sx'] + b['sx']) / 2, 0.0)
    dy = max(abs(a['y'] - b['y']) - (a['sy'] + b['sy']) / 2, 0.0)
    return math.hypot(dx, dy)


def box_overlap(a, b):
    return (min(a[2], b[2]) - max(a[0], b[0]) > EPS) and (min(a[3], b[3]) - max(a[1], b[1]) > EPS)


def pt_rect(px, py, cx, cy, sx, sy):
    return math.hypot(max(abs(px - cx) - sx / 2, 0.0), max(abs(py - cy) - sy / 2, 0.0))


def seg_rect_gap(t, p):
    """lower-bound-free exact distance from a track's centreline to a pad rectangle"""
    sys.path.insert(0, HERE)
    from route_emit import seg_rect
    return seg_rect((t['x1'], t['y1'], t['x2'], t['y2']), p['x'], p['y'], p['sx'], p['sy'])


def rot_vec(dx, dy, rot):
    r = rot % 360
    if r == 0:
        return dx, dy
    if r == 90:
        return -dy, dx
    if r == 180:
        return -dx, -dy
    if r == 270:
        return dy, -dx
    raise ValueError('rotation must be a multiple of 90, got %r' % rot)


# ------------------------------------------------------------------ the move
def apply_moves(inp, placement):
    """a deep copy of inp with the placement's moves and net fixes applied; returns (out, problems)"""
    out = copy.deepcopy(inp)
    problems = []
    by_ref = {}
    for p in out['bottom_pads']:
        by_ref.setdefault(p['ref'], []).append(p)
    seen = set()
    for m in placement.get('moves', []):
        ref = m['ref']
        if ref in seen:
            problems.append('%s moved twice' % ref)
            continue
        seen.add(ref)
        if ref not in BLOCK and ref not in placement.get('movable', []):
            problems.append("%s is not in the PWR block (nor in the placement's movable list) and may not move" % ref)
            continue
        pads = by_ref.get(ref)
        if not pads:
            problems.append('%s has no Bottom pads' % ref)
            continue
        piv = [p for p in pads if p['pad'] == str(m['pad'])]
        if len(piv) != 1:
            problems.append('%s has no single pad %r' % (ref, m['pad']))
            continue
        px, py = piv[0]['x'], piv[0]['y']
        rot = int(m.get('rot', 0))
        for p in pads:
            dx, dy = rot_vec(p['x'] - px, p['y'] - py, rot)
            p['x'] = round(m['x'] + dx, 4)
            p['y'] = round(m['y'] + dy, 4)
            if rot % 180 == 90:
                p['sx'], p['sy'] = p['sy'], p['sx']
    for fx in placement.get('net_fixes', []):
        hit = [p for p in out['bottom_pads'] + out['top_pads'] if p['ref'] == fx['ref'] and p['pad'] == str(fx['pad'])]
        if len(hit) != 1:
            problems.append('net fix %s-%s matches %d pads' % (fx['ref'], fx['pad'], len(hit)))
        for p in hit:
            p['net'] = fx['net']
    # nets[*].pads carry their own copies of pad centres
    now = {(p['ref'], p['pad']): p for p in out['bottom_pads']}
    for v in out['nets'].values():
        for q in v.get('pads', []):
            k = (q['ref'], q['pad'])
            if q.get('layer') == 'Bottom' and k in now:
                q['x'], q['y'], q['sx'], q['sy'] = now[k]['x'], now[k]['y'], now[k]['sx'], now[k]['sy']
    return out, problems


def part_box(ref, pads):
    x0 = min(p['x'] - p['sx'] / 2 for p in pads)
    x1 = max(p['x'] + p['sx'] / 2 for p in pads)
    y0 = min(p['y'] - p['sy'] / 2 for p in pads)
    y1 = max(p['y'] + p['sy'] / 2 for p in pads)
    if ref in SC189:
        d = {p['pad']: p for p in pads}
        cx = (d['1']['x'] + d['3']['x'] + d['4']['x'] + d['5']['x']) / 4
        cy = (d['1']['y'] + d['3']['y'] + d['4']['y'] + d['5']['y']) / 4
        along_x = abs(d['3']['x'] - d['1']['x']) > abs(d['3']['y'] - d['1']['y'])
        bw, bh = SOT_BODY if along_x else SOT_BODY[::-1]
        x0, x1 = min(x0, cx - bw / 2), max(x1, cx + bw / 2)
        y0, y1 = min(y0, cy - bh / 2), max(y1, cy + bh / 2)
    return (x0, y0, x1, y1)


def legality(inp, moved, placement):
    problems = []
    movers = {m['ref'] for m in placement.get('moves', [])}
    bottom = moved['bottom_pads']
    ol = moved['outline']
    by_ref = {}
    for p in bottom:
        by_ref.setdefault(p['ref'], []).append(p)
    boxes = {r: part_box(r, ps) for r, ps in by_ref.items()}
    for r in sorted(movers):
        for p in by_ref.get(r, []):
            m = min(p['x'] - p['sx'] / 2 - ol['x0'], ol['x1'] - p['x'] - p['sx'] / 2,
                    p['y'] - p['sy'] / 2 - ol['y0'], ol['y1'] - p['y'] - p['sy'] / 2)
            if m < EDGE - EPS:
                problems.append('%s-%s %.3f mm from the board edge (min %.2f)' % (r, p['pad'], m, EDGE))
        for q in bottom:
            if q['ref'] == r or (q['ref'] in movers and q['ref'] < r):
                continue
            for p in by_ref[r]:
                g = rect_gap(p, q)
                if g < LAND_CLEAR - EPS:
                    problems.append('%s-%s to %s-%s land gap %.3f (min %.2f)' % (r, p['pad'], q['ref'], q['pad'], g, LAND_CLEAR))
        for q in moved['th_pads']:
            for p in by_ref[r]:
                g = rect_gap(p, q)
                if g < LAND_CLEAR - EPS:
                    problems.append('%s-%s to through-hole %s-%s land gap %.3f (min %.2f)' % (r, p['pad'], q['ref'], q['pad'], g, LAND_CLEAR))
        for o, b in boxes.items():
            if o == r or (o in movers and o < r):
                continue
            if box_overlap(boxes[r], b):
                problems.append('%s courtyard-lite box overlaps %s' % (r, o))
        for t in moved['tracks']:
            if t['layer'] != 'Bottom':
                continue
            for p in by_ref[r]:
                if p['net'] == t['net'] and p['net'] is not None:
                    continue
                g = seg_rect_gap(t, p) - t['width'] / 2
                if g < C - EPS:
                    problems.append('%s-%s %.3f from an existing Bottom %s track' % (r, p['pad'], g, t['net']))
        for v in moved['vias']:
            for p in by_ref[r]:
                g = pt_rect(v['x'], v['y'], p['x'], p['y'], p['sx'], p['sy']) - v['size'] / 2
                if g < C - EPS:
                    problems.append('%s-%s %.3f from an existing %s via' % (r, p['pad'], g, v['net']))
    return problems


# ------------------------------------------------------------------ metrics
def via_sites(moved, pad, reach=1.2, limit=6):
    """greedy count of legal 0.20/0.35 via positions within `reach` of a pad's edge, 0.44 apart"""
    cands = []
    step = 0.05
    nx = int((pad['sx'] / 2 + reach) / step)
    ny = int((pad['sy'] / 2 + reach) / step)
    top, bot, th = moved['top_pads'], moved['bottom_pads'], moved['th_pads']
    ol = moved['outline']
    for i in range(-nx, nx + 1):
        for j in range(-ny, ny + 1):
            x, y = pad['x'] + i * step, pad['y'] + j * step
            d = pt_rect(x, y, pad['x'], pad['y'], pad['sx'], pad['sy'])
            if d > reach:
                continue
            if min(x - ol['x0'], ol['x1'] - x, y - ol['y0'], ol['y1'] - y) - VIA_LAND / 2 < moved.get('edge_clearance', 0.25):
                continue
            bad = False
            for q in bot + top:
                if pt_rect(x, y, q['x'], q['y'], q['sx'], q['sy']) - VIA_LAND / 2 < C - EPS:
                    bad = True
                    break
            if not bad:
                for q in th:
                    if pt_rect(x, y, q['x'], q['y'], q['sx'], q['sy']) - VIA_LAND / 2 < C - EPS:
                        bad = True
                        break
            if not bad:
                for k in moved.get('keepouts', []):
                    if pt_rect(x, y, (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2, k['x1'] - k['x0'], k['y1'] - k['y0']) - VIA_LAND / 2 < C - EPS:
                        bad = True
                        break
            if not bad:
                for v in moved['vias']:
                    if math.hypot(x - v['x'], y - v['y']) < VIA_PITCH - EPS:
                        bad = True
                        break
            if not bad:
                cands.append((d, x, y))
    cands.sort()
    got = []
    for d, x, y in cands:
        if all(math.hypot(x - a, y - b) >= VIA_PITCH - EPS for a, b in got):
            got.append((x, y))
            if len(got) >= limit:
                break
    return len(got)


def area(pts):
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def metrics(moved, roles):
    P = {(p['ref'], p['pad']): p for p in moved['bottom_pads']}
    pads_of = {}
    for p in moved['bottom_pads']:
        pads_of.setdefault(p['ref'], []).append(p)

    def on(ref, net):
        return [p for p in pads_of[ref] if p['net'] == net]

    def c(p):
        return (p['x'], p['y'])
    rows = []
    worst = {}
    for ic in SC189:
        r = roles.get(ic, {})
        sw = P[(ic, '5')]['net']
        rail = P[(ic, '4')]['net']
        L, cin, cout = r.get('l'), r.get('cin'), r.get('cout')
        lsw, lout = on(L, sw)[0], on(L, rail)[0]
        cvu, cgnd = on(cin, 'VU')[0], on(cin, 'GND')[0]
        oout, ognd = on(cout, rail)[0], on(cout, 'GND')[0]
        vin, gnd, en, vout, lx = (P[(ic, k)] for k in '12345')
        m = dict(ic=ic, rail=rail, L=L, cin=cin, cout=cout,
                 lx_to_L=rect_gap(lx, lsw),
                 vin_to_cin=rect_gap(vin, cvu), gnd_to_cin=rect_gap(gnd, cgnd),
                 L_to_cout=rect_gap(lout, oout), cout_gnd_to_ic_gnd=rect_gap(ognd, gnd),
                 sense_to_out=min(rect_gap(vout, lout), rect_gap(vout, oout)),
                 en_to_vu=min(rect_gap(en, vin), rect_gap(en, cvu)),
                 hot_loop_mm2=area([c(vin), c(cvu), c(cgnd), c(gnd)]),
                 out_loop_mm2=area([c(lx), c(lsw), c(lout), c(oout), c(ognd), c(gnd)]),
                 gnd_via_sites=via_sites(moved, gnd))
        rows.append(m)
    u8 = roles.get('U8', {})
    b = {}
    if u8:
        ep = P[('U8', '17')]
        u8gnd = [P[('U8', k)] for k in ('4', '6', '8', '17')]
        cin, cout, cbat = u8.get('cin'), u8.get('cout'), u8.get('cbat')
        b = dict(in_to_cin=rect_gap(P[('U8', '13')], on(cin, 'USB5V0')[0]),
                 out_to_cout=min(rect_gap(P[('U8', k)], on(cout, 'VU')[0]) for k in ('10', '11')),
                 bat_to_cbat=min(rect_gap(P[('U8', k)], on(cbat, 'VBATT')[0]) for k in ('2', '3')),
                 cin_gnd=min(rect_gap(on(cin, 'GND')[0], g) for g in u8gnd),
                 cout_gnd=min(rect_gap(on(cout, 'GND')[0], g) for g in u8gnd),
                 cbat_gnd=min(rect_gap(on(cbat, 'GND')[0], g) for g in u8gnd),
                 ep_via_sites=via_sites(moved, ep, reach=1.0))
        for rr in ('R102', 'R103', 'R104', 'R105', 'R106'):
            net = [p['net'] for p in pads_of[rr] if p['net'] != 'GND'][0]
            pin = [p for p in pads_of['U8'] if p['net'] == net][0]
            b[rr + '_to_U8-' + pin['pad']] = rect_gap(on(rr, net)[0], pin)
    return rows, b


# ------------------------------------------------------------------ the block's own copper
def islands(moved, plan, net):
    """connected components of one net's copper: plan + existing tracks, vias, and its pads.
    Returns (list of sets of 'ref-pad' / 'via' labels)."""
    layers = ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')
    segs = [t for t in plan.get('tracks', []) + moved['tracks'] if t['net'] == net]
    vias = [v for v in plan.get('vias', []) + moved['vias'] if v['net'] == net]
    pads = [dict(p, layer='Bottom') for p in moved['bottom_pads'] if p['net'] == net]
    pads += [dict(p, layer='Top') for p in moved['top_pads'] if p['net'] == net]
    pads += [dict(p, layer='Multi') for p in moved['th_pads'] if p['net'] == net]
    nodes, adj, label = [], {}, {}
    tol = 0.0015

    def node(x, y, L):
        for i, (a, b2, cc) in enumerate(nodes):
            if cc == L and abs(a - x) <= tol and abs(b2 - y) <= tol:
                return i
        nodes.append((x, y, L))
        return len(nodes) - 1

    def link(i, j):
        adj.setdefault(i, set()).add(j)
        adj.setdefault(j, set()).add(i)
    for t in segs:
        link(node(t['x1'], t['y1'], t['layer']), node(t['x2'], t['y2'], t['layer']))
    for k, v in enumerate(vias):
        ids = [node(v['x'], v['y'], L) for L in layers]
        for j in ids[1:]:
            link(ids[0], j)
        label.setdefault(ids[0], set()).add('via@%.3f,%.3f' % (v['x'], v['y']))
    for p in pads:
        pls = layers if p['layer'] == 'Multi' else (p['layer'],)
        ids = [node(p['x'], p['y'], L) for L in pls]
        for j in ids[1:]:
            link(ids[0], j)
        for i, (x, y, L) in enumerate(list(nodes)):
            if L in pls and abs(x - p['x']) <= p['sx'] / 2 + 1e-9 and abs(y - p['y']) <= p['sy'] / 2 + 1e-9:
                link(ids[0], i)
        label.setdefault(ids[0], set()).add('%s-%s' % (p['ref'], p['pad']))
    seen, comps = set(), []
    for s in range(len(nodes)):
        if s in seen:
            continue
        comp, stack = set(), [s]
        seen.add(s)
        while stack:
            n = stack.pop()
            comp |= label.get(n, set())
            for m in adj.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        if comp:
            comps.append(comp)
    return comps


def loop_joins(moved, plan, roles):
    """the connections the two datasheets ask for, each made by DIRECT copper (a GND via counts
    only where a pad must reach the plane)"""
    P = {(p['ref'], p['pad']): p for p in moved['bottom_pads']}
    pads_of = {}
    for p in moved['bottom_pads']:
        pads_of.setdefault(p['ref'], []).append(p)

    def name(ref, net):
        return ['%s-%s' % (ref, p['pad']) for p in pads_of[ref] if p['net'] == net]
    need = []          # (net, [labels that must share one island], why)
    gnd_to_plane = []  # labels that must share an island with at least `n` GND vias
    for ic in SC189:
        r = roles[ic]
        sw = P[(ic, '5')]['net']
        rail = P[(ic, '4')]['net']
        need.append((sw, ['%s-5' % ic] + name(r['l'], sw), 'LX to the inductor'))
        need.append(('VU', ['%s-1' % ic, '%s-3' % ic] + name(r['cin'], 'VU'), 'VIN, EN and CIN'))
        need.append(('GND', ['%s-2' % ic] + name(r['cin'], 'GND') + name(r['cout'], 'GND'), 'IC GND, CIN GND, COUT GND direct'))
        need.append((rail, name(r['l'], rail) + name(r['cout'], rail) + ['%s-4' % ic], 'L out, COUT and the VOUT sense pin'))
        gnd_to_plane.append(('%s-2' % ic, 2))
    if 'U8' in roles:
        r = roles['U8']
        need.append(('USB5V0', ['U8-13'] + name(r['cin'], 'USB5V0'), 'bq24232 IN to its cap'))
        need.append(('VU', ['U8-10', 'U8-11', 'U8-5'] + name(r['cout'], 'VU'), 'bq24232 OUT, EN2 and the OUT cap'))
        need.append(('VBATT', ['U8-2', 'U8-3'] + name(r['cbat'], 'VBATT'), 'bq24232 BAT to its cap'))
        need.append(('GND', ['U8-4', 'U8-6', 'U8-8', 'U8-17'] + name(r['cin'], 'GND') + name(r['cout'], 'GND') + name(r['cbat'], 'GND'),
                     'bq24232 thermal pad, GND pins and its three caps'))
        gnd_to_plane.append(('U8-17', 3))
        for rr in ('R102', 'R103', 'R104', 'R105', 'R106'):
            net = [p['net'] for p in pads_of[rr] if p['net'] != 'GND'][0]
            need.append((net, ['%s-%s' % (p['ref'], p['pad']) for p in moved['bottom_pads'] if p['net'] == net], rr + ' to its U8 pin'))
            gnd_to_plane.append((name(rr, 'GND')[0], 1))
    # every VU pad of the block on one island: the charger output reaches all three VINs
    need.append(('VU', ['%s-%s' % (p['ref'], p['pad']) for p in moved['bottom_pads'] if p['net'] == 'VU' and p['ref'] in BLOCK],
                 'every VU pad of the block'))
    cache, out = {}, []
    for net, labels, why in need:
        if net not in cache:
            cache[net] = islands(moved, plan, net)
        ok = any(set(labels) <= comp for comp in cache[net])
        out.append((ok, net, why, labels))
    if 'GND' not in cache:
        cache['GND'] = islands(moved, plan, 'GND')
    for lab, n in gnd_to_plane:
        comp = [cc for cc in cache['GND'] if lab in cc]
        nv = len([x for x in comp[0] if x.startswith('via@')]) if comp else 0
        out.append((nv >= n, 'GND', '%s reaches %d GND via(s) through its own copper (has %d)' % (lab, n, nv), [lab]))
    return out


# ------------------------------------------------------------------ DelphiScript
PAS_HELPERS_B = '{ ==== BLOCK-PLACE HELPERS, generated by tools/block_place.py -- do not edit by hand ==== }'
PAS_HELPERS_E = '{ ==== END BLOCK-PLACE HELPERS ==== }'
PAS_HELPERS = PAS_HELPERS_B + r"""

Function BlkPadXY(C : IPCB_Component; PN : String; Var PX, PY : TCoord) : Boolean;
Var
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
Begin
    Result := False;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While (P <> Nil) And (Not Result) Do
    Begin
        If P.Name = PN Then
        Begin
            PX := P.X; PY := P.Y;
            Result := True;
        End;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
End;


Function BlkAt(C : IPCB_Component; PN : String; X, Y : Double) : Boolean;
Var
    FX, FY : TCoord;
Begin
    Result := False;
    If BlkPadXY(C, PN, FX, FY) Then
        Result := (Abs(CoordToMMs(FX) - X) < 0.002) And (Abs(CoordToMMs(FY) - Y) < 0.002);
End;


{ Move part D so pad PN lands on (TX, TY) and pad QN on (UX, UY), starting from PN on (AX, AY) and
  QN on (BX, BY).  The turn is tried as +DRot and as -DRot (a Bottom part's Rotation property
  may run either way); whichever puts QN on its target within 2 um is kept, otherwise the part is
  put back exactly.  A part already at the target is left alone.  Returns '' or a reason. }
Function BlkMove(D, PN, QN : String; DRot, AX, AY, BX, BY, TX, TY, UX, UY : Double) : String;
Var
    C      : IPCB_Component;
    R0, R1 : Double;
    X0, Y0, FX, FY : TCoord;
    K      : Integer;
    Ok     : Boolean;
Begin
    Result := '';
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then
    Begin
        Result := D + ' not found';
        Exit;
    End;
    If BlkAt(C, PN, TX, TY) And BlkAt(C, QN, UX, UY) Then Exit;
    If Not (BlkAt(C, PN, AX, AY) And BlkAt(C, QN, BX, BY)) Then
    Begin
        Result := D + ' is neither where the plan starts nor where it ends';
        Exit;
    End;
    R0 := C.Rotation; X0 := C.X; Y0 := C.Y;
    Ok := False;
    K := 0;
    While (K < 2) And (Not Ok) Do
    Begin
        If K = 0 Then R1 := R0 + DRot Else R1 := R0 - DRot;
        While R1 >= 360 Do R1 := R1 - 360;
        While R1 < 0 Do R1 := R1 + 360;
        C.BeginModify;
        C.Rotation := R1;
        C.EndModify;
        BlkPadXY(C, PN, FX, FY);
        C.BeginModify;
        C.X := C.X + (MMsToCoord(TX) - FX);
        C.Y := C.Y + (MMsToCoord(TY) - FY);
        C.EndModify;
        If BlkAt(C, PN, TX, TY) And BlkAt(C, QN, UX, UY) Then
            Ok := True
        Else
        Begin
            C.BeginModify;
            C.Rotation := R0;
            C.X := X0;
            C.Y := Y0;
            C.EndModify;
        End;
        K := K + 1;
    End;
    If Not Ok Then Result := D + ': no rotation put pad ' + QN + ' on its target';
End;


{ Put pad PN of part D on net NetName (an ECO the saved file never received). }
Function BlkPadNet(D, PN, NetName : String) : String;
Var
    C  : IPCB_Component;
    It : IPCB_GroupIterator;
    P  : IPCB_Pad;
    N  : IPCB_Net;
    Hit : IPCB_Pad;
Begin
    Result := '';
    C := Brd.GetPcbComponentByRefDes(D);
    N := NetByName(NetName);
    If (C = Nil) Or (N = Nil) Then
    Begin
        Result := D + '-' + PN + ': part or net ' + NetName + ' not found';
        Exit;
    End;
    Hit := Nil;
    It := C.GroupIterator_Create;
    It.AddFilter_ObjectSet(MkSet(ePadObject));
    P := It.FirstPCBObject;
    While P <> Nil Do
    Begin
        If P.Name = PN Then Hit := P;
        P := It.NextPCBObject;
    End;
    C.GroupIterator_Destroy(It);
    If Hit = Nil Then
    Begin
        Result := D + '-' + PN + ' not found';
        Exit;
    End;
    If Hit.Net <> Nil Then
        If Hit.Net.Name = NetName Then Exit;
    { Net := alone is NOT enough: the pad reads the new net in memory, but the save writes -1 unless
      the pad is also on the net's member list (proven 2026-09-15 on R78-1, after TieR78ToGnd, the
      Import Changes ECO and this function without AddPCBObject had each failed to persist). }
    Try
        Hit.BeginModify;
        Hit.Net := N;
        N.AddPCBObject(Hit);
        Hit.EndModify;
    Except
        Result := D + '-' + PN + ': the net write was refused';
    End;
End;


{ Switch a part's designator off (C.NameOn, as HideCrowdedDesignators in ZuluFixDrc.pas). }
Function BlkHideName(D : String) : String;
Var
    C : IPCB_Component;
Begin
    Result := '';
    C := Brd.GetPcbComponentByRefDes(D);
    If C = Nil Then
    Begin
        Result := D + ' not found';
        Exit;
    End;
    If C.NameOn Then
    Begin
        C.BeginModify;
        C.NameOn := False;
        C.EndModify;
    End;
End;

""" + PAS_HELPERS_E + '\n'


def emit(inp, moved, placement, name):
    B = '{ ==== %s BLOCK, generated by tools/block_place.py -- do not edit by hand ==== }' % name.upper()
    E = '{ ==== END %s BLOCK ==== }' % name.upper()
    old = {(p['ref'], p['pad']): p for p in inp['bottom_pads']}
    new = {(p['ref'], p['pad']): p for p in moved['bottom_pads']}
    calls_fwd, calls_back = [], []
    for m in placement.get('moves', []):
        ref = m['ref']
        names = sorted(p for (r, p) in old if r == ref)
        pn = str(m['pad'])
        qn = max((p for p in names if p != pn), key=lambda q: math.hypot(old[(ref, q)]['x'] - old[(ref, pn)]['x'], old[(ref, q)]['y'] - old[(ref, pn)]['y']))
        a, b = old[(ref, pn)], old[(ref, qn)]
        t, u = new[(ref, pn)], new[(ref, qn)]
        rot = int(m.get('rot', 0)) % 360
        calls_fwd.append("    S := BlkMove('%s', '%s', '%s', %d, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f); If S <> '' Then Log := Log + #13#10 + S;"
                         % (ref, pn, qn, rot, a['x'], a['y'], b['x'], b['y'], t['x'], t['y'], u['x'], u['y']))
        calls_back.append("    S := BlkMove('%s', '%s', '%s', %d, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f, %.4f); If S <> '' Then Log := Log + #13#10 + S;"
                          % (ref, pn, qn, (360 - rot) % 360, t['x'], t['y'], u['x'], u['y'], a['x'], a['y'], b['x'], b['y']))
    fixes = ["    S := BlkPadNet('%s', '%s', '%s'); If S <> '' Then Log := Log + #13#10 + S;" % (f['ref'], f['pad'], f['net'])
             for f in placement.get('net_fixes', [])]
    fixes += ["    S := BlkHideName('%s'); If S <> '' Then Log := Log + #13#10 + S;" % r for r in placement.get('hide_designators', [])]
    n = len(calls_fwd)
    L = [B, '', 'Procedure Place%s;' % name, 'Var', '    S, Log : String;', 'Begin', '    Brd := BoardOrNil;', '    If Brd = Nil Then Exit;',
         "    Log := '';", '    PCBServer.PreProcess;', '    Try'] + ['    ' + c for c in calls_fwd + fixes] + [
         '    Finally', '        PCBServer.PostProcess;', '    End;', '    Brd.ViewManager_FullUpdate;',
         "    If Log = '' Then",
         "        ShowMessage('Zulu A7 - %s: %d parts on their targets%s%s.' + #13#10 + 'Now Tools > Design Rule Check > Run, then Ctrl+S if it is clean.')"
         % (name, n, (', %d pad net(s) set' % len(placement.get('net_fixes', []))) if placement.get('net_fixes') else '',
            (', %d designator(s) hidden' % len(placement.get('hide_designators', []))) if placement.get('hide_designators') else ''),
         '    Else',
         "        ShowMessage('Zulu A7 - %s: NOT all parts moved -- do not save:' + Log);" % name,
         'End;', '', '',
         'Procedure Restore%s;' % name, 'Var', '    S, Log : String;', 'Begin', '    Brd := BoardOrNil;', '    If Brd = Nil Then Exit;',
         "    Log := '';", '    PCBServer.PreProcess;', '    Try'] + ['    ' + c for c in calls_back] + [
         '    Finally', '        PCBServer.PostProcess;', '    End;', '    Brd.ViewManager_FullUpdate;',
         "    If Log = '' Then ShowMessage('Zulu A7 - %s: %d parts back where they were (pad nets left as set).')" % (name, n),
         "    Else ShowMessage('Zulu A7 - Restore%s problems:' + Log);" % name,
         'End;', '', E]
    return '\n'.join(L) + '\n', B, E


def write_setup(block, B, E):
    s = io.open(SETUP, encoding='utf-8', errors='replace').read()
    tail = "End.\n\n{ End of ZuluSetup.pas }\n"
    assert s.endswith(tail)
    if PAS_HELPERS_B not in s:
        s = s[:-len(tail)] + '\n' + PAS_HELPERS + '\n' + tail
    else:                               # keep the helpers current (2026-09-15: BlkPadNet gained AddPCBObject)
        a = s.index(PAS_HELPERS_B)
        b = s.index(PAS_HELPERS_E) + len(PAS_HELPERS_E) + 1
        s = s[:a] + PAS_HELPERS + s[b:]
    if B in s:
        a = s.index(B)
        b = s.index(E) + len(E) + 1
        s = s[:a] + block + s[b:]
    else:
        s = s[:-len(tail)] + '\n' + block + '\n' + tail
    io.open(SETUP, 'w', encoding='utf-8').write(s)


# ------------------------------------------------------------------ main
def main():
    args = sys.argv[1:]
    if not args or not args[0].endswith('.json'):
        print(__doc__)
        return 2
    placement = json.load(io.open(args[0], encoding='utf-8'))
    inputs = INPUTS
    if '--inputs' in args:
        inputs = args[args.index('--inputs') + 1]
    inp = json.load(io.open(inputs, encoding='utf-8'))
    moved, problems = apply_moves(inp, placement)
    problems += legality(inp, moved, placement)
    roles = placement.get('roles', {})
    print('placement: %d part(s) moved, %d pad net fix(es)' % (len(placement.get('moves', [])), len(placement.get('net_fixes', []))))
    if problems:
        print('%d PLACEMENT PROBLEM(S):' % len(problems))
        for p in problems[:60]:
            print('   ', p)
        if len(problems) > 60:
            print('    ... and %d more' % (len(problems) - 60))
    else:
        print('legal: land gaps >= %.2f, edge >= %.2f, no courtyard-lite overlap, clear of existing copper' % (LAND_CLEAR, EDGE))
    failed = bool(problems)
    if all(k in roles for k in SC189):
        rows, u8 = metrics(moved, roles)
        print('\n%-3s %-7s %-4s %-5s %-4s | %6s %6s %6s %6s %6s %6s | %7s %7s | %s' % (
            'ic', 'rail', 'L', 'CIN', 'COUT', 'LX-L', 'VIN-Ci', 'GND-Ci', 'L-Co', 'CoG-G', 'sense', 'hot mm2', 'out mm2', 'GND via sites'))
        for m in rows:
            print('%-3s %-7s %-4s %-5s %-4s | %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f | %7.2f %7.2f | %d' % (
                m['ic'], m['rail'], m['L'], m['cin'], m['cout'], m['lx_to_L'], m['vin_to_cin'], m['gnd_to_cin'],
                m['L_to_cout'], m['cout_gnd_to_ic_gnd'], m['sense_to_out'], m['hot_loop_mm2'], m['out_loop_mm2'], m['gnd_via_sites']))
        if u8:
            print('U8 (pad edge gaps, mm): ' + ', '.join('%s %.2f' % (k, v) if isinstance(v, float) else '%s %s' % (k, v) for k, v in u8.items()))
        if '--json' in args:
            io.open(args[args.index('--json') + 1], 'w', encoding='utf-8').write(json.dumps(dict(sc189=rows, u8=u8, problems=problems), indent=1))
    if '--plan' in args and all(k in roles for k in SC189):     # the regulator-block loop checks need its roles
        plan = json.load(io.open(args[args.index('--plan') + 1], encoding='utf-8'))
        res = loop_joins(moved, plan, roles)
        bad = [r for r in res if not r[0]]
        print('\nblock connections made by the plan: %d/%d' % (len(res) - len(bad), len(res)))
        for ok, net, why, labels in bad:
            print('   MISSING  %-9s %s  (%s)' % (net, why, ' '.join(labels)))
        failed = failed or bool(bad)
    if '--write-inputs' in args:
        path = args[args.index('--write-inputs') + 1]
        out = moved
        if '--merge-plan' in args:
            # the plan's copper as if already on the board: route_reach --inputs <this> with no plan
            # then asks whether every net -- the block's own power nets included -- can still leave
            plan = json.load(io.open(args[args.index('--plan') + 1], encoding='utf-8'))
            out = copy.deepcopy(moved)
            out['vias'] = out['vias'] + [dict(x=v['x'], y=v['y'], size=VIA_LAND, hole=0.20, net=v['net']) for v in plan.get('vias', [])]
            out['tracks'] = out['tracks'] + [dict(t) for t in plan.get('tracks', [])]
        io.open(path, 'w', encoding='utf-8').write(json.dumps(out, indent=1))
        print('wrote', path, '(plan copper merged)' if out is not moved else '')
    if '--write' in args and not failed:
        name = [a for a in args[1:] if not a.startswith('--') and not a.endswith('.json')][0]
        block, B, E = emit(inp, moved, placement, name)
        write_setup(block, B, E)
        print('wrote Place%s / Restore%s into %s' % (name, name, os.path.normpath(SETUP)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
