"""Strategy B transplant: keep SOURCE's Pmod-zone routes, rip the TARGET JA copper that conflicts with them.

    python B/scripts/build_b.py --rip minimal|nets|all [--mode stubs|clean] [--tag NAME]

Same rules as prep/scripts/build_transplant.py (04819de skipped, emit-ready removals in TARGET's own coordinates,
through vias in the new U2-EP / X4-2 pads -> laser stacks, conflict / SOURCE-only drops, duplicate placed once), with
the JA rip chosen by --rip:
  minimal  only the TARGET JA1..JA10 tracks / vias that a SOURCE addition actually clashes with (one pass; ripping
           never creates a new clash); the rest of each JA route stays (stubs mode keeps it as a partial route)
  nets     every track / via of each JA net that has at least one clashing object (JA7 has none)
  all      every JA1..JA10 track / via (= prep's rip_ja.json)
Writes B/transplant_b_<tag>.json (plan vs base_cur/base_new), B/after_b_<tag>.json (router model),
B/dropped_b_<tag>.json, B/log_b_<tag>.json.
"""
import argparse
import json
import os
import sys
from collections import Counter

BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREP_SCRIPTS = os.path.join(os.path.dirname(BDIR), 'prep', 'scripts')
sys.path.insert(0, PREP_SCRIPTS)
from common import *  # noqa: E402,F403
import geo  # noqa: E402
import delta as DL  # noqa: E402
import build_transplant as BT  # noqa: E402

JA = BT.JA


def bdump(obj, name):
    json.dump(obj, open(os.path.join(BDIR, name), 'w'), indent=1)


def build(rip_mode, mode, T, H, BN, D):
    board = BN['board']
    dropped, log = [], {'mode': mode, 'rip': rip_mode}
    tgrid = {}
    for kd, k, o in objs(T):
        x, y = centre(kd, o)
        tgrid.setdefault((kd, int(x), int(y)), []).append(o)

    def tobj(kd, o):
        x, y = centre(kd, o)
        hits = [q for i in (-1, 0, 1) for j in (-1, 0, 1) for q in tgrid.get((kd, int(x) + i, int(y) + j), ())
                if (DL.tmatch(q, o) if kd == 'T' else DL.vmatch(q, o))]
        assert len(hits) == 1, (kd, o, hits)
        return hits[0]
    rm = {}
    for r in D['removed']:
        if r['commit'] == '04819de':
            dropped.append({'what': 'removal', 'desc': r['desc'], 'commit': r['commit'], 'feature': r['feature'],
                            'reason': 'commit 04819de (Pmod-specific vias-out-of-pad / R108 move) is not transplanted'})
            continue
        if r['target_hits'] != 1:
            dropped.append({'what': 'removal', 'desc': r['desc'], 'commit': r['commit'], 'feature': r['feature'],
                            'reason': 'SOURCE-only object (absent on TARGET): nothing to remove'})
            continue
        o = tobj(r['kind'], r['target_obj'])
        rm[id(o)] = (r['kind'], o, 'delta:' + r['commit'])
    adds = []
    for a in D['added']:
        if a['commit'] == '04819de':
            dropped.append({'what': 'addition', 'desc': a['desc'], 'commit': a['commit'], 'feature': a['feature'],
                            'reason': 'commit 04819de (Pmod-specific vias-out-of-pad / R108 move) is not transplanted'})
            continue
        o = dict(a['obj'])
        o['_c'], o['_f'] = a['commit'], a['feature']
        adds.append((a['kind'], o))
    vip = []
    for x, y, pad, spans in BT.IN_PAD:
        hit = [v for v in T['vias'] if abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3 and v['span'] == STACK]
        assert len(hit) == 1, (x, y, hit)
        rm[id(hit[0])] = ('V', hit[0], 'through_in_new_smd_pad')
        for a_, b_ in spans:
            sz, hl = BT.VSIZE.get((a_, b_), (0.30, 0.15))
            adds.append(('V', {'net': hit[0]['net'], 'x': x, 'y': y, 'size': sz, 'hole': hl,
                               'span': STACK[STACK.index(a_):STACK.index(b_) + 1], '_c': 'fabb',
                               '_f': 'through_in_pad_to_uvia'}))
        vip.append({'pad': pad, 'removed': desc('V', hit[0]), 'replaced_by': ['%s>%s' % s for s in spans]})
    log['through_in_pad_replaced'] = vip
    H_keys = {k for _, k, _ in objs(H)}
    T_keys = {k for _, k, _ in objs(T)}
    hp = {(p['ref'], p['pad']): p for p in H['pads']}

    def world():
        idx = geo.Index()
        for p in BN['pads']:
            q = hp.get((p['ref'], p['pad']))
            same = q is not None and all(abs(p[f] - q[f]) < 1e-4 for f in ('x', 'y', 'w', 'h'))
            idx.add('p', p, 'pad' if same else 'pad_target_only')
        for kd, k, o in objs(T):
            if id(o) not in rm:
                idx.add('t' if kd == 'T' else 'v', o, 'tgt' if k in H_keys else 'tgt_only')
        return idx
    # ---------------------------------------------------------------- the JA rip
    ja_objs = [('T', t) for t in T['tracks'] if t['net'] in JA] + [('V', v) for v in T['vias'] if v['net'] in JA]
    if rip_mode == 'all':
        rip = {id(o) for _, o in ja_objs}
    else:
        fixed = world()
        hit_ids, hit_nets = set(), set()
        for k, o in adds:
            for p in geo.problems('t' if k == 'T' else 'v', o, fixed, board):
                q = p[5]
                if q is not None and q.get('net') in JA and 'ref' not in q:
                    hit_ids.add(id(q))
                    hit_nets.add(q['net'])
        rip = hit_ids if rip_mode == 'minimal' else {id(o) for _, o in ja_objs if o['net'] in hit_nets}
        log['ja_nets_with_clashes'] = sorted(hit_nets)
    for kd, o in ja_objs:
        if id(o) in rip:
            rm[id(o)] = (kd, o, 'rip_ja_%s' % rip_mode)
    log['ja_ripped'] = dict(Counter(o['net'] for kd, o in ja_objs if id(o) in rip))
    log['ja_kept'] = dict(Counter(o['net'] for kd, o in ja_objs if id(o) not in rip))
    # ---------------------------------------------------------------- conflicts against what stays
    fixed = world()
    kept, confl = [], []
    for k, o in adds:
        pr = geo.problems('t' if k == 'T' else 'v', o, fixed, board)
        (confl.append((k, o, pr)) if pr else kept.append((k, o)))
    for k, o, pr in confl:
        others = ['%s %s gap %s need %s: %s %s (%s)' % (p[0], p[1], p[2], p[3], p[4],
                                                        geo.J.desc(p[4], p[5]) if p[5] is not None else '', p[6])
                  for p in pr]
        dropped.append({'what': 'addition', 'desc': desc(k, o), 'commit': o['_c'], 'feature': o['_f'],
                        'zone': BT.zone(k, o), 'reason': 'conflict with TARGET copper/pad that stays',
                        'against': others,
                        'against_nets': sorted({p[5].get('net') or '' for p in pr if p[5] is not None}),
                        'obj': BT.strip(o)})
    log['conflict_drops'] = len(confl)
    S_only = geo.Index()
    add_keys = {(tkey(o) if k == 'T' else vkey(o)) for k, o in adds}
    for kd, key, o in objs(H):
        if key not in T_keys and key not in add_keys:
            S_only.add('t' if kd == 'T' else 'v', o, 'source_only')

    def on_s_only(k, o):
        kk = 't' if k == 'T' else 'v'
        return any(q.get('net') == o['net'] and geo.touches(kk, o, k2, q)
                   for l in geo.layers_of(kk, o) for k2, q, _ in S_only.near(kk, o, l))
    nk = []
    for k, o in kept:
        if on_s_only(k, o):
            dropped.append({'what': 'addition', 'desc': desc(k, o), 'commit': o['_c'], 'feature': o['_f'],
                            'zone': BT.zone(k, o), 'reason': 'ends on SOURCE-only copper', 'obj': BT.strip(o)})
        else:
            nk.append((k, o))
    kept = nk
    # ---------------------------------------------------------------- dead copper
    pruned_add, pruned_tgt, trimmed = [], [], []
    for it in range(10):
        tmap, tr, vs = {}, [], []
        for kd, k, o in objs(T):
            if id(o) not in rm:
                c = dict(o)
                tmap[id(c)] = ('tgt', kd, o)
                (tr if kd == 'T' else vs).append(c)
        for k, o in kept:
            c = dict(o)
            tmap[id(c)] = ('add', k, o)
            (tr if k == 'T' else vs).append(c)
        M = {'board': board, 'planes': BN['planes'], 'pads': BN['pads'], 'tracks': tr, 'vias': vs}
        if mode == 'clean':
            dt, dv, nt, nv = geo.PS.analyse(M)
            dead = [(o, 'T') for o in dt] + [(o, 'V') for o in dv]
        else:
            isl = geo.C.islands(M)
            live_t = {i for gs in isl.values() for g in gs for i in g['tracks']}
            live_v = {i for gs in isl.values() for g in gs for i in g['vias']}
            dead = [(o, 'T') for i, o in enumerate(tr) if i not in live_t] + \
                   [(o, 'V') for i, o in enumerate(vs) if i not in live_v]
            nt = []
        log['dead_pass_%d' % (it + 1)] = len(dead)
        if not dead:
            break
        dead_add = set()
        for o, kd in dead:
            src = tmap.get(id(o))
            if src is None:
                continue
            if src[0] == 'add':
                dead_add.add(id(src[2]))
            else:
                rm[id(src[2])] = (kd, src[2], 'dead_after_transplant' if mode == 'clean' else 'floating_after_transplant')
                pruned_tgt.append(desc(kd, src[2]))
        nk = []
        for k, o in kept:
            if id(o) in dead_add:
                pruned_add.append({'what': 'addition', 'desc': desc(k, o), 'commit': o['_c'], 'feature': o['_f'],
                                   'zone': BT.zone(k, o),
                                   'reason': 'dangling after another drop' if mode == 'clean' else
                                   'floating after another drop (no pad / plane island)', 'obj': BT.strip(o)})
            else:
                nk.append((k, o))
        kept = nk
        for t in nt:
            if t.get('trimmed'):
                c2 = {k: v for k, v in t.items() if k != 'trimmed'}
                c2['_c'], c2['_f'] = 'fabb', 'trimmed_stub'
                kept.append(('T', c2))
                trimmed.append(desc('T', c2))
    dropped += pruned_add
    log['pruned_additions'] = len(pruned_add)
    log['pruned_target_objects_added_to_removals'] = pruned_tgt
    log['trimmed_tracks_added'] = trimmed
    seen, nk, dups = set(), [], []
    for k, o in kept:
        key = tkey(o) if k == 'T' else vkey(o)
        if key in seen:
            dups.append(desc(k, o))
            continue
        seen.add(key)
        nk.append((k, o))
    kept = nk
    log['duplicate_additions_placed_once'] = dups
    rm_t = [o for kd, o, w in rm.values() if kd == 'T']
    rm_v = [o for kd, o, w in rm.values() if kd == 'V']
    log['removals_by_reason'] = dict(Counter(w for kd, o, w in rm.values()))
    plan = {'remove': [plan_track(t) for t in rm_t], 'remove_vias': [plan_rvia(v) for v in rm_v],
            'tracks': [plan_track(o) for k, o in kept if k == 'T'], 'vias': [plan_via(o) for k, o in kept if k == 'V'],
            'moves': [],
            '_meta': {'source': 'Zulu_A7_no_pmod Rev_2 22ee1dc -> 427960e (04819de skipped)',
                      'target_base': 'zulu_a7_fab_b.PcbDoc md5 33023787 (base_cur.json)',
                      'apply_to': 'base_new.json (TARGET after the ECO + placement)', 'mode': mode,
                      'strategy': 'B: SOURCE Pmod-zone routes kept, conflicting TARGET JA copper ripped (%s)' % rip_mode,
                      'features_added': dict(Counter(o['_f'] for k, o in kept)),
                      'removals_by_reason': log['removals_by_reason']}}
    # router model: base_new - removals + additions
    rmk_t = Counter(tkey(t) for t in rm_t)
    rmk_v = Counter(vkey(v) for v in rm_v)
    tr = []
    for t in BN['tracks']:
        k = tkey(t)
        if rmk_t[k] > 0:
            rmk_t[k] -= 1
            continue
        tr.append(t)
    vs = []
    for v in BN['vias']:
        v = dict(v, span=span(v))
        k = vkey(v)
        if rmk_v[k] > 0:
            rmk_v[k] -= 1
            continue
        vs.append(v)
    assert not +rmk_t and not +rmk_v, ('removal not on base_new', +rmk_t, +rmk_v)
    model = {'board': board, 'planes': BN['planes'], 'pads': BN['pads'],
             'tracks': tr + [{k: o[k] for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')} for k_, o in kept if k_ == 'T'],
             'vias': vs + [dict(BT.strip(o), span=span(o)) for k_, o in kept if k_ == 'V']}
    return plan, dropped, log, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rip', default='minimal', choices=['minimal', 'nets', 'all'])
    ap.add_argument('--mode', default='stubs', choices=['clean', 'stubs'])
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    tag = a.tag or '%s_%s' % (a.rip, a.mode)
    T = load('tgt_33023787')
    H = load('src_427960e')
    BN = json.load(open(os.path.join(PREP, 'base_new.json')))
    D = json.load(open(os.path.join(PREP, 'delta.json')))
    plan, dropped, log, model = build(a.rip, a.mode, T, H, BN, D)
    bdump(plan, 'transplant_b_%s.json' % tag)
    bdump(dropped, 'dropped_b_%s.json' % tag)
    bdump(log, 'log_b_%s.json' % tag)
    json.dump(model, open(os.path.join(BDIR, 'after_b_%s.json' % tag), 'w'))
    oc = geo.C.open_count(geo.C.islands(model))
    print('transplant_b_%s: remove %d tracks + %d vias, add %d tracks + %d vias; opens %d %s' % (
        tag, len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias']), sum(oc.values()),
        dict(sorted(oc.items()))))
    for k, v in sorted(Counter((d['what'], d['reason'], d.get('zone', '')) for d in dropped).items()):
        print('  dropped %4d  %s' % (v, k))
    print('log:', {k: (v if not isinstance(v, list) else len(v)) for k, v in log.items()})


if __name__ == '__main__':
    main()
