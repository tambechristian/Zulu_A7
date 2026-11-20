"""(c) transplant.json + dropped.json: every applicable SOURCE 22ee1dc -> HEAD copper change, made emit-ready for TARGET.

    python scripts/build_transplant.py [--mode clean|stubs] [--rip-ja]      (after build_base.py, delta.py)

Rules (all modes)
  * all of 04819de (R108 move + vias-out-of-pad on SOURCE-only parts) is skipped, removals and additions;
  * a removal is kept only if it selects exactly one base_cur object by emit_copper's rule (the plan carries TARGET's own
    coordinates); SOURCE objects absent on TARGET are listed in dropped.json (nothing to remove);
  * TARGET's GND through vias that land inside U2-EP / X4-2 of the new footprints are removed and replaced by laser
    microvia stacks to L2-GND (U2-EP: the via also ties U3-46 on Bottom, so a full column Top>L2>L3, L3-L4 buried,
    L4>L5>Bottom; X4-2: Top>L2 only) - no through via in any SMD pad;
  * an addition that breaks clearance / hole-to-hole / edge / width against TARGET copper or pads that stay is left out;
  * an addition that touches SOURCE-only copper (on SOURCE HEAD, not on TARGET, not transplanted) is left out.
Modes
  clean    (default) dead copper is then pruned to a fixpoint (prune_stubs.analyse, the compose_plan way): dead
           additions are left out, dead TARGET copper is added to the removals, trimmed tracks become remove + shorter
           track.  0 dead copper after it.            -> transplant.json, dropped.json, transplant_log.json
  stubs    only FLOATING fragments (copper in no island with a pad or a plane) are pruned; dead-ended copper that hangs
           off a pad island is KEPT as a partial route for the router (compose_plan prunes what stays unused).
                                                      -> transplant_stubs.json, dropped_stubs.json, ...
  (a 'restore' mode - put back TARGET objects SOURCE removed on the open nets where they clash with nothing - was
   tried on 2026-11-20 and dropped: it closed 0 of the 10 opens and brought back TARGET's GND through via that sits
   in the moved U4-4 pad.)
  --rip-ja additionally rips every JA1..JA10 track / via (rip_ja.json, U1 east balls -> R26..R33) before the
           conflict test, so more SOURCE copper fits; the JA nets become open.   -> *_ripja.json
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F403
import geo  # noqa: E402
import delta as DL  # noqa: E402

PMOD_X = 49.6           # the Pmod JA fan-out zone starts here (fullcheck: every transplant conflict at x 49.6-60.5)
JTAG = {'TMS', 'TCK', 'TDI', 'TDO'}
JA = ['JA1', 'JA2', 'JA3', 'JA4', 'JA7', 'JA8', 'JA9', 'JA10']
IN_PAD = [  # (x, y, pad, replacement spans)
    (32.35, 16.575, 'U2-EP (+ U3-46 on Bottom)', [('Top Layer', 'L2-GND'), ('L2-GND', 'L3-SIG'), ('L3-SIG', 'L4-SIG'),
                                                  ('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom Layer')]),
    (32.475, 9.025, 'X4-2', [('Top Layer', 'L2-GND')]),
]
VSIZE = {('L3-SIG', 'L4-SIG'): (0.27, 0.15)}


def strip(o):
    return {k: v for k, v in o.items() if not k.startswith('_')}


def jdesc(k, o):
    return geo.J.desc(k, o) if o is not None else ''


def zone(k, o):
    return 'pmod_zone' if centre(k, o)[0] >= PMOD_X else 'outside_pmod_zone'


def write_rip_ja(T):
    rip = {'remove': [plan_track(t) for t in T['tracks'] if t['net'] in JA],
           'remove_vias': [plan_rvia(v) for v in T['vias'] if v['net'] in JA],
           '_meta': {'what': 'every track / via of the Pmod JA nets (U1 east balls -> R26..R33), TARGET 33023787',
                     'nets': JA}}
    dump(rip, 'rip_ja.json')
    return rip


def build(mode, rip_ja, T, H, BN, D):
    board = BN['board']
    dropped, log = [], {'mode': mode, 'rip_ja': rip_ja}
    # ---------------------------------------------------------------- removals (TARGET's own dicts)
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
    rm = {}                      # id -> (kind, TARGET obj, why)
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
    if rip_ja:
        for t in T['tracks']:
            if t['net'] in JA:
                rm[id(t)] = ('T', t, 'rip_ja')
        for v in T['vias']:
            if v['net'] in JA:
                rm[id(v)] = ('V', v, 'rip_ja')
    # ---------------------------------------------------------------- additions
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
    for x, y, pad, spans in IN_PAD:
        hit = [v for v in T['vias'] if abs(v['x'] - x) < 1e-3 and abs(v['y'] - y) < 1e-3 and v['span'] == STACK]
        assert len(hit) == 1, (x, y, hit)
        rm[id(hit[0])] = ('V', hit[0], 'through_in_new_smd_pad')
        for a_, b_ in spans:
            sz, hl = VSIZE.get((a_, b_), (0.30, 0.15))
            adds.append(('V', {'net': hit[0]['net'], 'x': x, 'y': y, 'size': sz, 'hole': hl,
                               'span': STACK[STACK.index(a_):STACK.index(b_) + 1], '_c': 'fabb',
                               '_f': 'through_in_pad_to_uvia'}))
        vip.append({'pad': pad, 'removed': desc('V', hit[0]), 'replaced_by': ['%s>%s' % s for s in spans]})
    log['through_in_pad_replaced'] = vip
    # ---------------------------------------------------------------- conflicts against what stays on TARGET
    H_keys = {k for _, k, _ in objs(H)}
    T_keys = {k for _, k, _ in objs(T)}
    hp = {(p['ref'], p['pad']): p for p in H['pads']}

    def world(extra_skip=()):
        idx = geo.Index()
        for p in BN['pads']:
            q = hp.get((p['ref'], p['pad']))
            same = q is not None and all(abs(p[f] - q[f]) < 1e-4 for f in ('x', 'y', 'w', 'h'))
            idx.add('p', p, 'pad' if same else 'pad_target_only')
        for kd, k, o in objs(T):
            if id(o) not in rm:
                idx.add('t' if kd == 'T' else 'v', o, 'tgt' if k in H_keys else 'tgt_only')
        return idx
    fixed = world()
    kept, confl = [], []
    for k, o in adds:
        kk = 't' if k == 'T' else 'v'
        pr = geo.problems(kk, o, fixed, board)
        (confl.append((k, o, pr)) if pr else kept.append((k, o)))
    for k, o, pr in confl:
        others = ['%s %s gap %s need %s: %s %s (%s)' % (p[0], p[1], p[2], p[3], p[4], jdesc(p[4], p[5]), p[6]) for p in pr]
        dropped.append({'what': 'addition', 'desc': desc(k, o), 'commit': o['_c'], 'feature': o['_f'], 'zone': zone(k, o),
                        'reason': 'conflict with TARGET copper/pad that stays', 'against': others,
                        'against_nets': sorted({p[5].get('net') or '' for p in pr if p[5] is not None}), 'obj': strip(o)})
    log['conflict_drops'] = len(confl)
    # SOURCE-only copper: on SOURCE HEAD, not on TARGET, not transplanted
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
            jt = o['net'] in JTAG
            dropped.append({'what': 'addition', 'desc': desc(k, o), 'commit': o['_c'], 'feature': o['_f'], 'zone': zone(k, o),
                            'reason': ('SOURCE-only JTAG/TMS trunk piece (ends on SOURCE-only copper)' if jt else
                                       'ends on SOURCE-only copper'), 'obj': strip(o)})
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
            dead = [(o, 'T') for i, o in enumerate(tr) if i not in live_t] + [(o, 'V') for i, o in enumerate(vs) if i not in live_v]
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
                                   'zone': zone(k, o),
                                   'reason': ('SOURCE-only JTAG/TMS trunk piece (dead once its SOURCE-only end is out)'
                                              if o['net'] in JTAG and o['_c'] in ('06d9f27', '3b1817d') else
                                              'dangling after another drop (dead on TARGET)' if mode == 'clean' else
                                              'floating after another drop (no pad / plane island)'), 'obj': strip(o)})
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
    # SOURCE HEAD carries a few exact duplicates (two identical copies); place each copper object once
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
    log['removals_by_reason'] = dict(Counter(w.split(':')[0] + ('' if ':' not in w else ':' + w.split(':')[1])
                                             for kd, o, w in rm.values()))
    plan = {'remove': [plan_track(t) for t in rm_t], 'remove_vias': [plan_rvia(v) for v in rm_v],
            'tracks': [plan_track(o) for k, o in kept if k == 'T'], 'vias': [plan_via(o) for k, o in kept if k == 'V'],
            'moves': [],
            '_meta': {'source': 'Zulu_A7_no_pmod Rev_2 22ee1dc -> 427960e (04819de skipped)',
                      'target_base': 'zulu_a7_fab_b.PcbDoc md5 33023787 (base_cur.json)',
                      'apply_to': 'base_new.json (TARGET after the ECO + placement)', 'mode': mode, 'rip_ja': rip_ja,
                      'features_added': dict(Counter(o['_f'] for k, o in kept)),
                      'removals_by_reason': log['removals_by_reason']}}
    return plan, dropped, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='clean', choices=['clean', 'stubs'])
    ap.add_argument('--rip-ja', action='store_true')
    a = ap.parse_args()
    T = load('tgt_33023787')
    H = load('src_427960e')
    BN = json.load(open(os.path.join(PREP, 'base_new.json')))
    D = json.load(open(os.path.join(PREP, 'delta.json')))
    write_rip_ja(T)
    plan, dropped, log = build(a.mode, a.rip_ja, T, H, BN, D)
    sfx = ('' if a.mode == 'clean' else '_' + a.mode) + ('_ripja' if a.rip_ja else '')
    dump(plan, 'transplant%s.json' % sfx)
    dump(dropped, 'dropped%s.json' % sfx)
    dump(log, 'transplant_log%s.json' % sfx)
    print('transplant%s: remove %d tracks + %d vias, add %d tracks + %d vias' % (
        sfx, len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias'])))
    for k, v in sorted(Counter((d['what'], d['reason'], d.get('zone', '')) for d in dropped).items()):
        print('  dropped %4d  %s' % (v, k))
    print('log:', {k: (v if not isinstance(v, list) else len(v)) for k, v in log.items()})


if __name__ == '__main__':
    main()
