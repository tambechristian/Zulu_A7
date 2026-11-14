"""combine: pools of D13/D14/D15 candidates from the three strategies (u1_end, inner_run, u3_end), plan merging,
and an exact new-geometry margin evaluator built on the checker copy's own primitives (check.py in this folder,
a byte copy of d10/fold/check.py).  Nothing here writes outside d13/combine except final_plan.json (see combine.py).
"""
import json, os, sys, copy, math, collections, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
D13 = os.path.dirname(HERE)
SR = os.path.dirname(D13)
BASE_PATH = os.path.join(SR, 'dq_series_r_plan.json')

# import the checker copy as a module (it reads --plan/--tag from argv at import time)
_argv = sys.argv
sys.argv = [os.path.join(HERE, 'check.py'), '--plan', BASE_PATH, '--tag', '_lib']
sys.path.insert(0, HERE)
import check as C  # noqa: E402
sys.argv = _argv

LIN = C.LAYER_IN
CU = C.CU


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def load_base():
    assert md5(BASE_PATH) == 'f2949630ce86fb4640eb860d481d579a', 'base plan changed'
    return json.load(open(BASE_PATH))


# ------------------------------------------------------------------ delta helpers
def r4(v):
    return round(float(v) + 0.0, 4)


def polish(d):
    """identical to d13/u1_end/joint.py polish(): round to 0.1 um; merge a <0.06 mm inner attach stub into the kept
    straight piece it hangs on (the piece then ends at the column centre)."""
    d = copy.deepcopy(d)
    for t in d['tracks']:
        for k in ('x1', 'y1', 'x2', 'y2'):
            t[k] = r4(t[k])
    for v in d['vias'] + d['microvias']:
        v['x'], v['y'] = r4(v['x']), r4(v['y'])
    cols = {(v['x'], v['y']) for v in d['vias'] if v.get('why') != 'rename' and v['size'] < 0.34}
    new = [t for t in d['tracks'] if t.get('why') != 'rename']
    for st in list(new):
        L = math.hypot(st['x2'] - st['x1'], st['y2'] - st['y1'])
        if L >= 0.06 or st['layer'] not in ('L3-SIG', 'L4-SIG'):
            continue
        ends = [(st['x1'], st['y1']), (st['x2'], st['y2'])]
        col = [e for e in ends if e in cols]
        if len(col) != 1:
            continue
        other = ends[1] if col[0] == ends[0] else ends[0]
        hosts = [t for t in new if t is not st and t['net'] == st['net'] and t['layer'] == st['layer'] and
                 ((t['x2'], t['y2']) == other or (t['x1'], t['y1']) == other)]
        if len(hosts) != 1:
            continue
        h = hosts[0]
        if (h['x2'], h['y2']) == other:
            h['x2'], h['y2'] = col[0]
        else:
            h['x1'], h['y1'] = col[0]
        d['tracks'].remove(st)
        new.remove(st)
    return d


def norm_delta(d):
    d = copy.deepcopy(d)
    for k in ('remove', 'remove_vias', 'tracks', 'vias', 'microvias', 'parts', 'renet_pads'):
        d.setdefault(k, [])
    return d


def delta_stats(d):
    new_v = [v for v in d['vias'] if v.get('why') != 'rename']
    through = [v for v in new_v if {v['from'], v['to']} == {'Top Layer', 'Bottom Layer'}]
    pads = []
    for pr in d['parts']:
        pads += [(pr['side'], pr['pad1']['x'], pr['pad1']['y']), (pr['side'], pr['pad2']['x'], pr['pad2']['y'])]
    vippo = set()
    for v in new_v:
        for (sd, x, y) in pads:
            outer = 'Top Layer' if sd == 'Top' else 'Bottom Layer'
            if outer in (v['from'], v['to']) and abs(v['x'] - x) <= 0.15 and abs(v['y'] - y) <= 0.15:
                vippo.add((sd, x, y))
    ch = (len([t for t in d['remove'] if t.get('why') != 'rename']) + len([t for t in d['tracks'] if t.get('why') != 'rename'])
          + len([v for v in d['remove_vias'] if v.get('why') != 'rename']) + len(new_v))
    ren = len([t for t in d['tracks'] if t.get('why') == 'rename']) + len([v for v in d['vias'] if v.get('why') == 'rename'])
    return dict(new_vias=len(new_v), new_through=len(through), new_micro=len(new_v) - len(through), vippo=len(vippo),
                copper_changes=ch, renames=ren)


# ------------------------------------------------------------------ pools
def _u1(path):
    d = json.load(open(path))
    out = []
    for n in ('D13', 'D14', 'D15'):
        for c in d['nets'][n]['candidates']:
            if c['status'] not in ('legal', 'legal_silk_U1'):
                continue
            out.append(dict(id='u1_end:' + c['id'], src='u1_end', net=n, family=c['family'], status=c['status'],
                            part=c['part'], delta=norm_delta(c['delta']), unlock=None,
                            silk_U1=(c['status'] == 'legal_silk_U1')))
    return out


def _inner(path):
    d = json.load(open(path))
    out = []
    for n in ('D13', 'D14', 'D15'):
        for c in d['nets'][n]['candidates']:
            if not c.get('full_check', {}).get('PASS', False):
                continue
            out.append(dict(id='inner_run:' + c['id'], src='inner_run', net=n, family='inner', status='legal',
                            part=c['delta']['parts'][0], delta=norm_delta(c['delta']), unlock=None, silk_U1=False))
    return out


def _u3(path):
    d = json.load(open(path))
    out = []
    for c in d['candidates']:
        if not c.get('full_check', {}).get('pass', False):
            continue
        out.append(dict(id='u3_end:' + c['id'], src='u3_end', net=c['net'], family=c['family'], status='legal',
                        part=c['part'], delta=norm_delta(c['delta']), unlock=c.get('requires_unlock'),
                        silk_U1=any('U1' in s for s in c.get('soft_flags', []))))
    return out, d['unlocks']


def load_pools():
    u1 = _u1(os.path.join(D13, 'u1_end', 'candidates.json'))
    inn = _inner(os.path.join(D13, 'inner_run', 'candidates.json'))
    u3, unlocks = _u3(os.path.join(D13, 'u3_end', 'candidates.json'))
    pools = collections.defaultdict(list)
    for c in u1 + inn + u3:
        c['stats'] = delta_stats(c['delta'])
        pools[c['net']].append(c)
    unl = {k: norm_delta(v['rec']) for k, v in unlocks.items()}
    return pools, unl


# ------------------------------------------------------------------ merge
def _key_t(t):
    a = (r4(t['x1']), r4(t['y1'])); b = (r4(t['x2']), r4(t['y2']))
    return (LIN[t['layer']], t['net'], min(a, b), max(a, b))


def _key_v(v):
    return (r4(v['x']), r4(v['y']), v['net'])


def merge(base, deltas, note):
    """append deltas to the base plan; refuse conflicts (an object removed twice, an object removed by one delta that
    another delta re-adds/renames, two deltas adding the same part ref or re-netting the same pad)."""
    P = copy.deepcopy(base)
    seen_rm, seen_rmv, seen_ref, seen_pad = set(), set(), set(), set()
    for t in P['remove']:
        seen_rm.add(_key_t(t))
    for v in P['remove_vias']:
        seen_rmv.add(_key_v(v))
    for pr in P['parts']:
        seen_ref.add(pr['ref'])
    for p in P['renet_pads']:
        seen_pad.add((p['ref'], p['pad']))
    errs = []
    for d in deltas:
        for t in d['remove']:
            k = _key_t(t)
            if k in seen_rm:
                errs.append('track removed twice %s' % (k,))
            seen_rm.add(k)
        for v in d['remove_vias']:
            k = _key_v(v)
            if k in seen_rmv:
                errs.append('via removed twice %s' % (k,))
            seen_rmv.add(k)
        for pr in d['parts']:
            if pr['ref'] in seen_ref:
                errs.append('part twice %s' % pr['ref'])
            seen_ref.add(pr['ref'])
        for p in d['renet_pads']:
            k = (p['ref'], p['pad'])
            if k in seen_pad:
                errs.append('pad renet twice %s' % (k,))
            seen_pad.add(k)
        for k in ('remove', 'remove_vias', 'tracks', 'vias', 'microvias', 'parts', 'renet_pads'):
            P[k] = P[k] + copy.deepcopy(d[k])
        for pr in d['parts']:
            sn = 'SDRAM-D%d' % pr['net_bit']
            if sn not in P['net_class_add']['SDRAM_DATA']:
                P['net_class_add']['SDRAM_DATA'].append(sn)
    P['renamed_existing'] = dict(tracks=sum(1 for t in P['tracks'] if t.get('why') == 'rename'),
                                 vias=sum(1 for v in P['vias'] if v.get('why') == 'rename'))
    P['source'] = dict(P['source'], plan='13-resistor plan (dq_series_r_plan.json md5 f2949630) + ' + note,
                       generated_by='si/series_r/d13/combine/combine.py')
    return P, errs


# ------------------------------------------------------------------ exact new-geometry margins (checker primitives)
def margins(plan_path, new_mask=None):
    """apply the plan with the checker copy's own load_plan/apply, then measure, for every NEW object that is not a
    pure rename (added tracks/vias without why=rename, and the pads of added parts):
      clearance  = gap - C.gap_rule  vs every other-net copper object on the same layer
      h2h        = hole edge-to-edge - 0.24 vs every other drill sharing a layer (new vias only)
      mask web   = pad-opening gap - 0.10 vs every other pad on the same side (added part pads only)
    new_mask(obj_rec_dict) -> bool restricts which new objects are measured (default all).
    Returns dict with apply errors, per-category worst, and a sorted list of the 25 smallest margins."""
    C.PLAN = plan_path
    del C.SELF[:]
    E = C.load_plan()
    pads0, tracks0, vias0 = C.board_records()
    n_t0, n_v0, n_p0 = len(tracks0), len(vias0), len(pads0)
    pads, tracks, vias, newflags, errors = C.apply(E)
    objs = C.build_objs(pads, tracks, vias, newflags)
    G = C.Grid(objs)
    # which new objects are genuine geometry (not renames)
    keep = set()
    for k, t in enumerate(E['add_t']):
        if t.get('why') != 'rename':
            keep.add(('t', n_t0 + k))
    for k, v in enumerate(E['add_v']):
        if v.get('why') != 'rename':
            keep.add(('v', n_v0 + k))
    for k in range(len(E['add_p'])):
        keep.add(('p', n_p0 + k))
    res = []
    for o in objs:
        if o.uid not in keep:
            continue
        if new_mask is not None and not new_mask(o):
            continue
        bb = C.bbox(o.shape)
        for q in G.near(o.layer, bb, pad=0.6):
            if q.uid == o.uid or q.net == o.net:
                continue
            g = C.gap_rule(o, q, o.layer)
            d = C.dist(o.shape, q.shape)
            if d - g < 0.1:
                res.append((round(d - g, 4), 'clr ' + o.layer, o.tag, q.tag))
        if o.kind == 'via' and o.hole:
            for q in G.near(o.layer, bb, pad=0.6):
                if q.uid == o.uid or not q.hole or q.xy is None:
                    continue
                if not (set(o.span) & set(q.span or [])):
                    continue
                d = math.hypot(o.xy[0] - q.xy[0], o.xy[1] - q.xy[1]) - (o.hole + q.hole) / 2
                if q.net == o.net and d < 1e-6:
                    continue      # same-net stacked column member
                if d - 0.24 < 0.1:
                    res.append((round(d - 0.24, 4), 'h2h', o.tag, q.tag))
        if o.kind == 'pad' and o.layer in ('Top', 'Bottom'):
            for q in G.near(o.layer, bb, pad=0.6):
                if q.uid == o.uid or q.kind != 'pad' or q.ref == o.ref:
                    continue
                gap = C.dist(o.shape, q.shape) - C.mask_exp(o) - C.mask_exp(q)
                if gap - 0.10 < 0.1:
                    res.append((round(gap - 0.10, 4), 'mask web ' + o.layer, o.tag, q.tag))
    res = sorted(set(res))
    worst = {}
    for m, cat, a, b in res:
        if cat not in worst:
            worst[cat] = (m, a, b)
    return dict(apply_errors=errors, min=(res[0][0] if res else 1.0), worst=worst, smallest=res[:25], all=res)
