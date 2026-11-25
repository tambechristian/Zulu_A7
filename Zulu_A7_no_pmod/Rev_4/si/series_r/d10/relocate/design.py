"""d10/relocate/design.py -- strategy "relocate": free room for a D10 series resistor in the Top bundle by moving
D8's (R127) or D11's (R130) resistor, then place D10's (R129).  PLANNING ONLY: reads si/series_r/*, writes only
into this folder.

    python design.py            -> plan.json, plan.png, design.json, design.log (this folder)

Inputs (read only): ../../board_extract.json (PcbDoc md5 2a616c1c), ../../dq_series_r_plan.json (the 12-resistor
plan), ../../design_top.json / design_top_candidates.json (the Top designer's D10 / D11 candidate lists).
The geometry and rules are dfm_check_plan.py's (a copy of the proven dfm_check.py that reads a plan JSON):
Clearance 0.09 on Top, MinimumSolderMaskSliver 0.10 with +0.05 expansion, through-via lands kept outside the new
pads' mask openings (the rule design_top.py used; the 12-resistor plan has 0.025 mm there).

What the search does
  1. Base = the 12-resistor plan with D10's Top run (38.5,14.5)-(39.9785,14.5) removed.  For the "move D11"
     branch the plan's D11 Top copper and R130 are taken out too; for "move D8" R127 and D8's Top copper.
  2. Every D10 position (R129 centre on a 0.01 mm grid, rot 0, on D10's own Top run, 45-degree jogs back to y 14.5)
     and every R130 / R127 position on its own run is scored by its worst margin against the board (copper,
     mask sliver / merged openings, via land in the opening); the R pairs are then checked against each other.
  3. ComponentClearance (0.254 mm, NOT run by the batch DRC; dfm_check reports it as advisory) is scored too,
     with design_top.py's body proxy (pads bbox U Mech3 0.40 x 0.396 = 0.90 x 0.396 mm).
The chosen plan maximises the worst copper/mask margin of the whole bundle; the proof is dfm_check_plan.py.
"""
import collections
import copy
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
_argv = sys.argv
sys.argv = [sys.argv[0]]
import dfm_check_plan as D  # noqa: E402
sys.argv = _argv

# 2026-11-13 fold: dq_series_r_plan.json now holds THIS script's 13-R output; the 12-R base it was built from is
# kept byte-identical (md5 21972745) as dq_series_r_plan_12.json.
BASE_PLAN = os.path.join(SR, 'dq_series_r_plan_12.json')
EMIT = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG',
        'L5-VCC3V3': 'L5-VCC3V3'}
W_TOP = 0.0762
CU_GAP = 0.09
MASK_SLIVER = 0.10
COMP_CLEAR = 0.254
BODY = (0.90, 0.396)          # design_top.py R_BODY proxy (along, across)
LOG = []

# the three Top runs this design touches: via (start), corner (end of the horizontal), net
RUNS = {'D8': dict(a=(38.5, 13.6), c=(39.6455, 13.6), ref='R127', bit=8),
        'D10': dict(a=(38.5, 14.5), c=(39.9785, 14.5), ref='R129', bit=10),
        'D11': dict(a=(38.5, 14.95), c=(40.145, 14.95), ref='R130', bit=11)}


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def frange(a, b, s):
    n = int(round((b - a) / s))
    return [round(a + k * s, 4) for k in range(n + 1)]


# ------------------------------------------------------------------ copper for one series R on a horizontal Top run
def r_copper(net, cx, cy):
    """R centre (cx, cy), rot 0, pad 1 west (U3 side, SDRAM-<net>), pad 2 east (<net>).  Tracks 0.0762 on Top:
    via -> (p1x-dy, y0) -> pad 1 centre ; pad 2 centre -> (p2x+dy, y0) -> corner.  Returns None if the jogs do not fit."""
    R = RUNS[net]
    (ax, y0), (ex, _) = R['a'], R['c']
    p1, p2 = (round(cx - 0.3, 4), cy), (round(cx + 0.3, 4), cy)
    dy = round(abs(cy - y0), 4)
    tr = []
    sn = 'SDRAM-' + net
    if dy < 1e-6:
        tr.append((sn, ax, y0, p1[0], y0))
        tr.append((net, p2[0], y0, ex, y0))
    elif dy <= 0.15 - W_TOP / 2 + 1e-6:
        # the run's centreline still crosses the pad: run straight on, then a short orthogonal stub to the pad centre
        # (all of the stub lies inside the pad), the way the 12-resistor plan feeds R130
        tr.append((sn, ax, y0, p1[0], y0))
        tr.append((sn, p1[0], y0, p1[0], cy))
        tr.append((net, p2[0], cy, p2[0], y0))
        tr.append((net, p2[0], y0, ex, y0))
    else:
        j1, j2 = round(p1[0] - dy, 4), round(p2[0] + dy, 4)
        if j1 < ax - 1e-6 or j2 > ex + 1e-6:
            return None
        if j1 > ax + 1e-6:
            tr.append((sn, ax, y0, j1, y0))
        tr.append((sn, j1, y0, p1[0], cy))
        tr.append((net, p2[0], cy, j2, y0))
        if j2 < ex - 1e-6:
            tr.append((net, j2, y0, ex, y0))
    pads = [dict(ref=R['ref'], pad='1', net=sn, x=p1[0], y=p1[1]), dict(ref=R['ref'], pad='2', net=net, x=p2[0], y=p2[1])]
    tracks = [dict(net=n, layer='Top', w=W_TOP, x1=a, y1=b, x2=c, y2=d) for n, a, b, c, d in tr]
    return dict(net=net, cx=cx, cy=cy, pads=pads, tracks=tracks)


def r_objs(rc):
    objs = []
    for p in rc['pads']:
        objs.append(D.O('pad', 'Top', p['net'], ('R', p['x'], p['y'], 0.15, 0.15), p, 'pad %s-%s' % (p['ref'], p['pad']),
                        ('np', p['ref'], p['pad']), new=True, xy=(p['x'], p['y']), ref=p['ref'], pad=p['pad']))
    for k, t in enumerate(rc['tracks']):
        objs.append(D.O('track', 'Top', t['net'], ('C', t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), t,
                        'track Top %s (%.3f,%.3f)-(%.3f,%.3f)' % (t['net'], t['x1'], t['y1'], t['x2'], t['y2']),
                        ('nt', rc['net'], k), new=True, w=t['w']))
    return objs


def body(rc):
    a, c = BODY
    return ('R', rc['cx'], rc['cy'], a / 2, c / 2)


def fam(net):
    return net.replace('SDRAM-', '')


def pair_margins(oa, ob, ignore_family=True):
    """copper / mask margins between two object lists (Top)"""
    cu, mk = 9.0, 9.0
    why = [None, None]
    for o in oa:
        for q in ob:
            if q.net == o.net:
                continue
            d = D.dist(o.shape, q.shape)
            if d - CU_GAP < cu:
                cu, why[0] = d - CU_GAP, (o.tag, q.tag)
            if o.kind == 'pad' and q.kind == 'pad':
                dm = D.dist(D.grow(o.shape, D.mask_exp(o)), D.grow(q.shape, D.mask_exp(q)))
                if dm - MASK_SLIVER < mk:
                    mk, why[1] = dm - MASK_SLIVER, (o.tag, q.tag)
    return cu, mk, why


class Board:
    """the base board + plan objects on Top in the bundle window, as a Grid"""

    def __init__(self, plan, drop_nets=()):
        E = D.load_plan(plan) if isinstance(plan, str) else plan
        pads, tracks, vias, newflags, errors = D.apply(E)
        assert not errors, errors
        objs = D.build_objs(pads, tracks, vias, newflags)
        keep = []
        for o in objs:
            if o.layer != 'Top':
                continue
            x0, y0, x1, y1 = D.bbox(o.shape)
            if x1 < 36.5 or x0 > 42.5 or y1 < 11.5 or y0 > 17.5:
                continue
            keep.append(o)
        self.objs = keep
        self.G = D.Grid(keep, 0.5)

    def margins(self, rc):
        """worst margins of one R (pads + its tracks) against the board: copper, mask, via land in opening"""
        new = r_objs(rc)
        cu, mk, land = 9.0, 9.0, 9.0
        why = {}
        (ax, y0), (ex, _) = RUNS[rc['net']]['a'], RUNS[rc['net']]['c']
        for o in new:
            # a piece lying on the run's ORIGINAL centreline is a sub-segment of today's track: against today's
            # copper it cannot be closer than today's track is (board DRC 0), so it is scored only against new copper
            inh = o.kind == 'track' and abs(o.shape[2] - y0) < 1e-6 and abs(o.shape[4] - y0) < 1e-6 and                 min(o.shape[1], o.shape[3]) >= ax - 1e-6 and max(o.shape[1], o.shape[3]) <= ex + 1e-6
            for q in self.G.near('Top', D.bbox(o.shape), 0.4):
                own = fam(q.net or '') == rc['net']   # the run's own copper (either side of the R): its connection
                if inh and not q.new:
                    continue
                if not own and q.net != o.net:
                    d = D.dist(o.shape, q.shape)
                    if d - CU_GAP < cu:
                        cu, why['cu'] = d - CU_GAP, q.tag + ' vs ' + o.tag
                if o.kind == 'pad':
                    op = D.grow(o.shape, D.mask_exp(o))
                    if q.kind == 'pad':
                        dm = D.dist(op, D.grow(q.shape, D.mask_exp(q)))
                        if dm - MASK_SLIVER < mk:
                            mk, why['mask'] = dm - MASK_SLIVER, q.tag + ' vs ' + o.tag
                    if q.kind == 'via' and len(q.span) == 6:
                        dl = D.dist(op, q.shape)
                        if dl < land:
                            land, why['land'] = dl, q.tag + ' vs ' + o.tag
        return dict(cu=round(cu, 4), mask=round(mk, 4), land=round(land, 4), worst=round(min(cu, mk, land), 4), why=why)


def body_gap(a, b):
    return D.dist(body(a), body(b))


# ------------------------------------------------------------------ plan surgery
def load_base():
    return json.load(open(BASE_PLAN))


def strip_r(P, net):
    """take one net's Top-run R (pads + its added Top copper) out of the plan; its Top-run removal stays"""
    R = RUNS[net]
    P['parts'] = [p for p in P['parts'] if p['ref'] != R['ref']]
    P['tracks'] = [t for t in P['tracks'] if not (fam(t['net']) == net and t['layer'] == 'Top Layer' and t.get('why') != 'rename')]
    return P


def restore_run(P, net):
    """undo the plan's edit of one Top run completely (R gone, run, renames and the U3 pad back to the original net)"""
    R = RUNS[net]
    (ax, y0), (ex, _) = R['a'], R['c']
    P = strip_r(P, net)
    P['remove'] = [t for t in P['remove'] if not (t['net'] == net and t['layer'] == 'Top Layer' and abs(t['y1'] - y0) < 1e-6 and abs(t['y2'] - y0) < 1e-6)]
    ren = [t for t in P['remove'] if t.get('why') == 'rename' and t['net'] == net]
    P['remove'] = [t for t in P['remove'] if not (t.get('why') == 'rename' and t['net'] == net)]
    P['tracks'] = [t for t in P['tracks'] if not (t.get('why') == 'rename' and t['net'] == 'SDRAM-' + net)]
    P['remove_vias'] = [v for v in P['remove_vias'] if not (v.get('why') == 'rename' and v['net'] == net)]
    P['vias'] = [v for v in P['vias'] if not (v.get('why') == 'rename' and v['net'] == 'SDRAM-' + net)]
    P['renet_pads'] = [r for r in P['renet_pads'] if r['net'] != 'SDRAM-' + net]
    P['net_class_add']['SDRAM_DATA'] = [n for n in P['net_class_add']['SDRAM_DATA'] if n != 'SDRAM-' + net]
    return P, len(ren)


def to_E(P):
    path = os.path.join(HERE, '_tmp_plan.json')
    json.dump(P, open(path, 'w'))
    E = D.load_plan(path)
    os.remove(path)
    return E


def add_r(P, rc, side='Top'):
    """add an R + its Top copper; the Top-run removal is added if the plan does not already remove it"""
    R = RUNS[rc['net']]
    (ax, y0), (ex, _) = R['a'], R['c']
    have = any(t['net'] == rc['net'] and t['layer'] == 'Top Layer' and abs(t['y1'] - y0) < 1e-6 and abs(t['y2'] - y0) < 1e-6
               and t.get('why') != 'rename' for t in P['remove'])
    if not have:
        P['remove'].append(dict(net=rc['net'], layer='Top Layer', w=W_TOP, x1=ax, y1=y0, x2=ex, y2=y0))
    for t in rc['tracks']:
        P['tracks'].append(dict(net=t['net'], layer='Top Layer', w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    p1, p2 = rc['pads']
    P['parts'].append(dict(ref=R['ref'], net_bit=R['bit'], side=side, footprint='R0201', comment='22', x=rc['cx'], y=rc['cy'],
                           rot=0, pad1=dict(net=p1['net'], x=p1['x'], y=p1['y']), pad2=dict(net=p2['net'], x=p2['x'], y=p2['y']),
                           designator_hidden=True))
    P['parts'].sort(key=lambda p: p['net_bit'])
    return P


def derive_renames(P, net):
    """rename the existing U3-side copper of <net> to SDRAM-<net> (remove + re-add), from physical connectivity,
    exactly as plan_export.py does; also renet the U3 pad and add the net to SDRAM_DATA"""
    n = int(net[1:])
    if not any(r['ref'] == 'U3' and r['pad'] == str(D.DPIN[n]) for r in P['renet_pads']):
        P['renet_pads'].append(dict(ref='U3', pad=str(D.DPIN[n]), net='SDRAM-' + net))
    if 'SDRAM-' + net not in P['net_class_add']['SDRAM_DATA']:
        P['net_class_add']['SDRAM_DATA'].append('SDRAM-' + net)
        P['net_class_add']['SDRAM_DATA'].sort(key=lambda s: int(s[7:]))
    E = to_E(P)
    pads, tracks, vias, newflags, errors = D.apply(E)
    assert not errors, errors
    n_old_t = len(D.board_records()[1])
    n_old_v = len(D.board_records()[2])
    objs = D.build_objs(pads, tracks, vias, newflags)
    sub = [o for o in objs if o.net in (net, 'SDRAM-' + net)]
    uf = D.phys_islands(sub, net_aware=False)
    isl = collections.defaultdict(list)
    for k, o in enumerate(sub):
        isl[uf.f(k)].append(o)
    u3 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U3' for o in os_)]
    u1 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U1' for o in os_)]
    assert len(isl) == 2 and len(u3) == 1 and len(u1) == 1 and u3[0] != u1[0], (net, len(isl))
    rt, rv = set(), set()
    for o in isl[u3[0]]:
        kind, i = o.uid
        if o.net == 'SDRAM-' + net:
            continue
        if kind == 't':
            assert i < n_old_t, o.tag
            rt.add(i)
        elif kind == 'v':
            assert i < n_old_v, o.tag
            rv.add(i)
    for o in isl[u1[0]]:
        assert o.net == net or (o.kind == 'pad' and o.ref == 'U3'), o.tag
    bt, bv = D.board_records()[1], D.board_records()[2]
    for i in sorted(rt):
        t = bt[i]
        P['remove'].append(dict(net=t['net'], layer=EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
        P['tracks'].append(dict(net='SDRAM-' + net, layer=EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
    for i in sorted(rv):
        v = bv[i]
        P['remove_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], hole=v['hole'], span=[v['span'][0], v['span'][-1]], why='rename'))
        P['vias'].append(dict(net='SDRAM-' + net, x=v['x'], y=v['y'], size=v['size'], hole=v['hole'],
                              **{'from': EMIT[v['span'][0]], 'to': EMIT[v['span'][-1]]}, why='rename'))
    P['renamed_existing']['tracks'] += len(rt)
    P['renamed_existing']['vias'] += len(rv)
    return P, len(rt), len(rv)


# ------------------------------------------------------------------ search
def scan(board, net, xs, ys):
    out = []
    for cx in xs:
        for cy in ys:
            rc = r_copper(net, cx, cy)
            if rc is None:
                continue
            m = board.margins(rc)
            rc['m'] = m
            out.append(rc)
    return out


def best_pair(cA, cB, others=(), need_body=False):
    """best (worst-margin) compatible pair from two candidate lists (each already scored against the board)"""
    best = None
    cA = sorted([c for c in cA if c['m']['worst'] >= -0.05], key=lambda c: -c['m']['worst'])
    cB = sorted([c for c in cB if c['m']['worst'] >= -0.05], key=lambda c: -c['m']['worst'])
    for a in cA:
        if best and a['m']['worst'] <= best[0]:
            break
        oa = r_objs(a)
        for b in cB:
            w = min(a['m']['worst'], b['m']['worst'])
            if best and w <= best[0]:
                break
            bg = body_gap(a, b)
            ext = [body_gap(a, o) for o in others] + [body_gap(b, o) for o in others]
            if need_body and min([bg] + ext) < COMP_CLEAR - 1e-9:
                continue
            cu, mk, why = pair_margins(oa, r_objs(b))
            w = min(w, cu, mk)
            if best is None or w > best[0]:
                best = (round(w, 4), a, b, dict(pair_cu=round(cu, 4), pair_mask=round(mk, 4), body_gap=round(bg, 4), why=why))
    return best


def fmt(c):
    return '(%.3f,%.3f) worst %+.4f [cu %+.4f mask %+.4f land %.4f] %s' % (c['cx'], c['cy'], c['m']['worst'], c['m']['cu'],
                                                                         c['m']['mask'], c['m']['land'], c['m']['why'])


def main():
    out = dict(source=dict(pcbdoc_md5=D.B['source']['pcbdoc_md5'], base_plan=BASE_PLAN, script=os.path.abspath(__file__)))
    base = load_base()
    rc_now = {p['net_bit']: p for p in base['parts']}
    R127 = dict(net='D8', cx=rc_now[8]['x'], cy=rc_now[8]['y'])
    R130 = dict(net='D11', cx=rc_now[11]['x'], cy=rc_now[11]['y'])
    log('==== d10/relocate/design.py  (PcbDoc md5 %s) ====' % D.B['source']['pcbdoc_md5'])
    log('12-resistor plan: R127 D8 at (%.3f,%.3f), R130 D11 at (%.3f,%.3f)' % (R127['cx'], R127['cy'], R130['cx'], R130['cy']))

    xs10, ys10 = frange(38.80, 39.70, 0.01), frange(14.30, 14.60, 0.01)
    # --- A. the Top designer's 20 D10 sites against the 12-resistor plan as it is
    P0 = strip_r(copy.deepcopy(base), 'D10')
    P0['remove'].append(dict(net='D10', layer='Top Layer', w=W_TOP, x1=38.5, y1=14.5, x2=39.9785, y2=14.5))
    b0 = Board(to_E(P0))
    td = json.load(open(os.path.join(SR, 'design_top_candidates.json')))['D10']
    rows = []
    for c in td:
        rc = r_copper('D10', c['cx'], c['cy'])
        m = b0.margins(rc)
        rc['m'] = m
        bg = {'R127': round(body_gap(rc, r_copper('D8', R127['cx'], R127['cy'])), 4),
              'R130': round(body_gap(rc, r_copper('D11', R130['cx'], R130['cy'])), 4)}
        rows.append(dict(cx=c['cx'], cy=c['cy'], cu=m['cu'], mask=m['mask'], land=m['land'], worst=m['worst'], why=m['why'], body_gap=bg))
    log('\n-- A. design_top.py\'s 20 D10 sites vs the 12-resistor plan (R127 + R130 in place) --')
    for r in rows:
        log('  (%.3f,%.3f) worst %+.4f cu %+.4f mask %+.4f land %.4f  body gap R127 %.3f R130 %.3f   %s' % (
            r['cx'], r['cy'], r['worst'], r['cu'], r['mask'], r['land'], r['body_gap']['R127'], r['body_gap']['R130'],
            r['why'].get('mask') if r['mask'] < 0 else r['why'].get('cu')))
    out['A_top_designer_sites_vs_12_plan'] = rows

    # --- B. move D8: R127 out of the bundle (D8's Top run restored); D10 alone with R130 in place
    P8, _ = restore_run(copy.deepcopy(P0), 'D8')
    b8 = Board(to_E(P8))
    c8 = scan(b8, 'D10', xs10, ys10)
    legal8 = [c for c in c8 if c['m']['worst'] >= 0]
    best8 = max(c8, key=lambda c: c['m']['worst'])
    strict8 = [c for c in legal8 if body_gap(c, r_copper('D11', R130['cx'], R130['cy'])) >= COMP_CLEAR]
    # with R127 in place (no move at all)
    cK = scan(b0, 'D10', xs10, ys10)
    legalK = [c for c in cK if c['m']['worst'] >= 0]
    bestK = max(cK, key=lambda c: c['m']['worst'])
    strictK = [c for c in legalK if min(body_gap(c, r_copper('D11', R130['cx'], R130['cy'])),
                                        body_gap(c, r_copper('D8', R127['cx'], R127['cy']))) >= COMP_CLEAR]
    log('\n-- B. D10 grid x %.2f..%.2f y %.2f..%.2f step 0.01 (%d sites) --' % (xs10[0], xs10[-1], ys10[0], ys10[-1], len(cK)))
    log('  no move (R127 + R130 in place): %d legal (copper/mask/land >= 0), best %s' % (len(legalK), fmt(bestK)))
    log('     of them with ComponentClearance >= 0.254 to R127 and R130: %d' % len(strictK))
    log('  move D8 (R127 gone, D8 run restored): %d legal, best %s' % (len(legal8), fmt(best8)))
    log('     of them with ComponentClearance >= 0.254 to R130: %d' % len(strict8))
    yK = sorted({c['cy'] for c in legalK})
    y8 = sorted({c['cy'] for c in legal8})
    log('  legal D10 rows (y): no move %s ; move D8 %s' % (yK, y8))
    out['B'] = dict(no_move=dict(legal=len(legalK), best=dict(xy=(bestK['cx'], bestK['cy']), m=bestK['m']), strict=len(strictK), rows=yK),
                    move_D8=dict(legal=len(legal8), best=dict(xy=(best8['cx'], best8['cy']), m=best8['m']), strict=len(strict8), rows=y8))

    # --- C. move D11: R130 re-sited on its own run, jointly with D10
    P11 = strip_r(copy.deepcopy(P0), 'D11')
    b11 = Board(to_E(P11))
    c10 = scan(b11, 'D10', xs10, ys10)
    c11 = scan(b11, 'D11', frange(38.90, 39.85, 0.01), frange(14.80, 15.05, 0.01))
    l11 = [c for c in c11 if c['m']['worst'] >= 0]
    log('\n-- C. move D11: R130 re-sited on D11\'s own Top run (x 38.90..39.85, y 14.80..15.05): %d legal sites alone' % len(l11))
    log('  best R130 alone: %s' % fmt(max(c11, key=lambda c: c['m']['worst'])))
    log('  R130 as planned (39.2,14.9) alone: %s' % fmt([c for c in c11 if abs(c['cx'] - 39.2) < 1e-6 and abs(c['cy'] - 14.9) < 1e-6][0]))
    r127 = r_copper('D8', R127['cx'], R127['cy'])
    bps = best_pair(c10, c11, others=[r127], need_body=True)
    log('  any joint (D10, D11) pair with ComponentClearance >= 0.254 to each other and to R127: %s' % ('none' if bps is None else '%+.4f' % bps[0]))
    keepR130 = [c for c in c11 if abs(c['cx'] - R130['cx']) < 1e-6 and abs(c['cy'] - R130['cy']) < 1e-6]
    bk = best_pair(c10, keepR130)
    log('  best D10 with R130 NOT moved: worst %+.4f  D10 %s | %s' % (bk[0], fmt(bk[1]), bk[3]))
    # selection: copper / mask / land margin first, capped at CAP (beyond that more margin buys nothing at Altium's
    # 2.54 um resolution), then the largest R-to-R body gap (ComponentClearance is advisory: it is not in the batch
    # DRC, and no pair reaches 0.254 -- see above), then the uncapped margin
    CAP = 0.03
    A_ = [c for c in c10 if c['m']['worst'] >= 0]
    B_ = [c for c in c11 if c['m']['worst'] >= 0]
    best = None
    for a in A_:
        oa = r_objs(a)
        g127 = body_gap(a, r127)
        for b in B_:
            w0 = min(a['m']['worst'], b['m']['worst'])
            if best and min(w0, CAP) < best[0][0]:
                continue
            bg = min(body_gap(a, b), g127)
            if best and min(w0, CAP) == best[0][0] and bg < best[0][1] - 1e-9:
                continue
            cu, mk, why = pair_margins(oa, r_objs(b))
            w = min(w0, cu, mk)
            k = (round(min(w, CAP), 4), round(bg, 4), round(w, 4))
            if best is None or k > best[0]:
                best = (k, a, b, dict(pair_cu=round(cu, 4), pair_mask=round(mk, 4), why=why))
    (wc, bg, w), A, Bc, pr = best
    log('  CHOSEN: R129 D10 at (%.3f,%.3f), R130 D11 moved (%.3f,%.3f) -> (%.3f,%.3f); worst copper/mask/land %+.4f; '
        'body gap R129-R130 %.3f, R129-R127 %.3f (ComponentClearance 0.254, advisory)' % (
            A['cx'], A['cy'], R130['cx'], R130['cy'], Bc['cx'], Bc['cy'], w, body_gap(A, Bc), body_gap(A, r127)))
    log('    R129 %s' % fmt(A))
    log('    R130 %s' % fmt(Bc))
    log('    pair %s' % pr)
    out['C'] = dict(r130_legal_alone=len(l11), d10_legal_with_r130_out=len(A_),
                    strict_component_clearance_pair=None if bps is None else bps[0],
                    best_with_r130_unmoved=dict(worst=bk[0], d10=(bk[1]['cx'], bk[1]['cy']), d10_m=bk[1]['m'], pair=bk[3],
                                                body_gap=round(body_gap(bk[1], keepR130[0]), 4)))
    out['chosen'] = dict(R129=dict(net='D10', x=A['cx'], y=A['cy'], m=A['m']), R130=dict(net='D11', x=Bc['cx'], y=Bc['cy'], m=Bc['m'],
                         moved_from=(R130['cx'], R130['cy'])), worst=w, pair=pr, body_gap_R129_R130=round(body_gap(A, Bc), 4),
                         body_gap_R129_R127=round(body_gap(A, r127), 4))

    # --- E. build the full plan
    P = strip_r(copy.deepcopy(base), 'D11')
    P = add_r(P, Bc)
    P = add_r(P, A)
    P, nt, nv = derive_renames(P, 'D10')
    P['source'] = dict(pcbdoc_md5=D.B['source']['pcbdoc_md5'],
                       plan='12-resistor plan (si/series_r/dq_series_r_plan.json) + R129 on D10 (Top) + R130 re-sited on D11; strategy relocate',
                       generated_by='si/series_r/d10/relocate/design.py')
    json.dump(P, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
    log('\nplan.json: remove %d tracks / %d vias, add %d tracks / %d vias, %d parts; D10 renames %d tracks + %d vias' % (
        len(P['remove']), len(P['remove_vias']), len(P['tracks']), len(P['vias']), len(P['parts']), nt, nv))
    out['plan_counts'] = dict(remove=len(P['remove']), remove_vias=len(P['remove_vias']), tracks=len(P['tracks']), vias=len(P['vias']),
                              parts=len(P['parts']), d10_renamed_tracks=nt, d10_renamed_vias=nv)
    json.dump(out, open(os.path.join(HERE, 'design.json'), 'w'), indent=1, default=str)
    open(os.path.join(HERE, 'design.log'), 'w').write('\n'.join(LOG) + '\n')
    draw(P, base)


def draw(P, base):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    from matplotlib.lines import Line2D
    col = {'Top Layer': '#c0392b', 'Bottom Layer': '#2471a3', 'L3-SIG': '#d68910', 'L4-SIG': '#7d3c98',
           'L2-GND': '#1e8449', 'L5-VCC3V3': '#a04000'}
    fig, axes = plt.subplots(1, 2, figsize=(16, 8.2), gridspec_kw=dict(width_ratios=[1.25, 1]))
    rmkey = {(r['layer'], round(r['x1'], 3), round(r['y1'], 3), round(r['x2'], 3), round(r['y2'], 3)) for r in P['remove'] if r.get('why') != 'rename'}
    base_parts = {p['ref']: p for p in base['parts']}
    views = [('Top bundle at U1 (Top view): R127 D8 kept, R129 D10 NEW, R130 D11 RE-SITED, R131 D12 kept', (37.9, 40.9, 12.7, 16.4), ('Top Layer',)),
             ('D10 route: U3-45 -> Bottom stub -> via -> L3 -> via (38.5,14.5) -> Top -> R129 -> U1-K2', (30.8, 43.0, 11.4, 18.2), None)]
    for ax, (title, (x0, x1, y0, y1), only) in zip(axes, views):
        for p in D.B['pads']:
            if not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1) or p['layer'] not in ('Top', 'Bottom', 'Multi'):
                continue
            if only and p['layer'] == 'Bottom':
                continue
            w, h = (p['w'], p['h'])
            ax.add_patch(Rectangle((p['x'] - w / 2, p['y'] - h / 2), w, h, fc='#bbbbbb' if p['layer'] == 'Bottom' else '#e8c0c0',
                                   ec='none', alpha=0.6, zorder=1))
        for t in D.B['tracks']:
            if t['layer'] not in D.CU or (only and EMIT[t['layer']] not in only):
                continue
            if not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0):
                continue
            k = (EMIT[t['layer']], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
            hl = t['net'] in ('D10',) and only is None
            if k in rmkey:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=0.9, ls=':', zorder=3)
            else:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[EMIT[t['layer']]], lw=2.2 if hl else max(0.6, t['w'] * 12),
                        alpha=0.9 if hl else (0.45 if only else 0.2), zorder=2)
            if only and x0 < (t['x1'] + t['x2']) / 2 < x1 and y0 < (t['y1'] + t['y2']) / 2 < y1 and t['net'] in ('CKE', 'D8', 'UDQM', 'D10', 'D11', 'UART_FT_CTS#') \
                    and abs(t['y1'] - t['y2']) < 1e-6 and t['x1'] < 38.6:
                ax.text(38.05, t['y1'], t['net'], fontsize=7, va='center', color='#555555')
        for v in D.B['vias']:
            if x0 < v['x'] < x1 and y0 < v['y'] < y1 and (not only or 'Top' in v['span']):
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#2471a3' if v['net'] == 'D10' and not only else '#888888',
                                    lw=1.2 if v['net'] == 'D10' and not only else 0.5, zorder=2))
        for t in P['tracks']:
            if t.get('why') == 'rename' or (only and t['layer'] not in only):
                continue
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[t['layer']], lw=max(1.2, t['w'] * 16), zorder=8, solid_capstyle='round')
        for v in P['vias']:
            if v.get('why') == 'rename' or (only and v['from'] != 'Top Layer'):
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#000000', lw=1.0, zorder=5))
        for pr in P['parts']:
            if not (x0 < pr['x'] < x1 and y0 < pr['y'] < y1):
                continue
            if only and pr['side'] != 'Top':
                continue
            new = pr['ref'] == 'R129'
            moved = pr['ref'] == 'R130'
            fc = '#2ecc71' if new else ('#f39c12' if moved else '#f1c40f')
            for pd in (pr['pad1'], pr['pad2']):
                ax.add_patch(Rectangle((pd['x'] - 0.15, pd['y'] - 0.15), 0.3, 0.3, fc=fc, ec='k', lw=0.7, zorder=6))
            ax.add_patch(Rectangle((pr['x'] - 0.45, pr['y'] - 0.198), 0.9, 0.396, fc='none', ec='#555555', lw=0.5, ls='--', zorder=6))
            ax.text(pr['x'], pr['y'] + 0.2, '%s D%d%s' % (pr['ref'], pr['net_bit'], ' NEW' if new else (' moved' if moved else '')),
                    fontsize=7 if only else 6, ha='center', va='bottom', zorder=7, fontweight='bold')
        if only and 'R130' in base_parts:
            b = base_parts['R130']
            for pd in (b['pad1'], b['pad2']):
                ax.add_patch(Rectangle((pd['x'] - 0.15, pd['y'] - 0.15), 0.3, 0.3, fc='none', ec='#f39c12', lw=1.0, ls='--', zorder=6))
            ax.text(b['x'], b['y'] - 0.25, 'R130 in the 12-R plan', fontsize=6, ha='center', color='#b9770e', zorder=7)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.2)
    h = [Line2D([], [], color=c, lw=2, label='new ' + k) for k, c in col.items() if k in ('Top Layer',)]
    h += [Line2D([], [], color='k', ls=':', label='removed'), Line2D([], [], marker='s', color='#2ecc71', ls='', label='R129 (new, D10)'),
          Line2D([], [], marker='s', color='#f39c12', ls='', label='R130 re-sited (D11)'), Line2D([], [], marker='s', color='#f1c40f', ls='', label='plan R (unchanged)'),
          Line2D([], [], color='#555555', ls='--', label='body proxy 0.90 x 0.396'),
          Line2D([], [], color='#2471a3', lw=2, label='D10 existing copper (right)')]
    axes[0].legend(handles=h, fontsize=7, loc='lower left')
    fig.suptitle('D10 series resistor, strategy "relocate" (PcbDoc md5 2a616c1c); board coords mm, y up; faint = existing copper', fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, 'plan.png'), dpi=150)


if __name__ == '__main__':
    main()
