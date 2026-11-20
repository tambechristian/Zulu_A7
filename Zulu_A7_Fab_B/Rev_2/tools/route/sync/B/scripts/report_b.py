"""report_b.py <final_plan.json> <router_out.json,...> <out.json>  -- the figures of a composed Strategy B plan:
counts by span, the difference against prep/transplant.json, Pmod nets touched, added lengths, routed-net facts."""
import json
import math
import os
import sys
from collections import Counter, defaultdict

BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREP = os.path.join(os.path.dirname(BDIR), 'prep')
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def kind(v):
    s = span(v)
    if s == STACK:
        return 'through'
    if s == ['L3-SIG', 'L4-SIG']:
        return 'buried L3-L4'
    return 'laser %s-%s' % (s[0].split('-')[0].replace(' Layer', ''), s[-1].split('-')[0].replace(' Layer', ''))


def tk(t):
    e = sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))])
    return (t['net'], t['layer'], round(t['w'], 3)) + e[0] + e[1]


def vk(v):
    s = span(v)
    return (v['net'], round(v['x'], 3), round(v['y'], 3), s[0], s[-1])


def L(t):
    return math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])


def main():
    P = json.load(open(sys.argv[1]))
    routers = [json.load(open(f)) for f in sys.argv[2].split(',') if f]
    T0 = json.load(open(os.path.join(PREP, 'transplant.json')))
    rep = {'plan': sys.argv[1]}
    rep['counts'] = {
        'remove_tracks': len(P['remove']), 'remove_vias': len(P['remove_vias']),
        'add_tracks': len(P['tracks']), 'add_vias': len(P['vias']),
        'vias_added_by_span': dict(sorted(Counter(kind(v) for v in P['vias']).items())),
        'vias_removed_by_span': dict(sorted(Counter(kind(v) for v in P['remove_vias']).items())),
        'tracks_added_by_layer': dict(sorted(Counter(t['layer'] for t in P['tracks']).items())),
        'tracks_removed_by_layer': dict(sorted(Counter(t['layer'] for t in P['remove']).items())),
        'added_track_mm': round(sum(map(L, P['tracks'])), 2),
        'removed_track_mm': round(sum(map(L, P['remove'])), 2),
    }
    a, r = Counter(kind(v) for v in P['vias']), Counter(kind(v) for v in P['remove_vias'])
    rep['counts']['net_via_change_by_span'] = {k: a[k] - r[k] for k in sorted(set(a) | set(r))}
    # against prep/transplant.json
    sets = {}
    for name, key, A, B in (('remove', tk, P['remove'], T0['remove']), ('remove_vias', vk, P['remove_vias'], T0['remove_vias']),
                            ('tracks', tk, P['tracks'], T0['tracks']), ('vias', vk, P['vias'], T0['vias'])):
        ka, kb = Counter(key(o) for o in A), Counter(key(o) for o in B)
        only_p, only_t = ka - kb, kb - ka
        nets_p = Counter(k[0] for k in only_p.elements())
        nets_t = Counter(k[0] for k in only_t.elements())
        sets[name] = {'in_plan_not_transplant': sum(only_p.values()), 'in_transplant_not_plan': sum(only_t.values()),
                      'by_net_plan_only': dict(sorted(nets_p.items())), 'by_net_transplant_only': dict(sorted(nets_t.items()))}
    rep['vs_prep_transplant'] = sets
    # Pmod nets touched
    pm = lambda n: n.startswith('JA') or n.startswith('PMOD')  # noqa: E731
    touched = defaultdict(lambda: Counter())
    for t in P['remove']:
        if pm(t['net']):
            touched[t['net']]['tracks_removed'] += 1
    for v in P['remove_vias']:
        if pm(v['net']):
            touched[v['net']]['vias_removed'] += 1
    for t in P['tracks']:
        if pm(t['net']):
            touched[t['net']]['tracks_added'] += 1
            touched[t['net']]['mm_added'] += round(L(t), 4)
    for v in P['vias']:
        if pm(v['net']):
            touched[v['net']]['vias_added'] += 1
            touched[v['net']]['via_' + kind(v)] += 1
    rep['pmod_nets_touched'] = {k: dict(v) for k, v in sorted(touched.items())}
    rep['pmod_nets_mm_added_total'] = round(sum(v['mm_added'] for v in touched.values()), 3)
    # router facts (what survived in the plan)
    pk_t, pk_v = Counter(tk(t) for t in P['tracks']), Counter(vk(v) for v in P['vias'])
    rt = [t for r in routers for t in r['tracks'] if pk_t[tk(t)] > 0]
    rv = [v for r in routers for v in r['vias'] if pk_v[vk(v)] > 0]
    per = defaultdict(lambda: Counter())
    for t in rt:
        per[t['net']]['tracks'] += 1
        per[t['net']]['mm'] += round(L(t), 4)
        per[t['net']]['layer ' + t['layer']] += 1
    for v in rv:
        per[v['net']]['vias'] += 1
        per[v['net']]['via ' + kind(v)] += 1
    rep['router_copper_in_plan'] = {'tracks': len(rt), 'vias': len(rv), 'mm': round(sum(map(L, rt)), 2),
                                    'vias_by_span': dict(Counter(kind(v) for v in rv)),
                                    'by_net': {k: dict(v) for k, v in sorted(per.items())}}
    # every plan line by origin: prep/transplant.json, other SOURCE copper (delta.json 'added'), new routing
    D = json.load(open(os.path.join(PREP, 'delta.json')))
    src_t = Counter(tk(a['obj']) for a in D['added'] if a['kind'] == 'T')
    src_v = Counter(vk(a['obj']) for a in D['added'] if a['kind'] == 'V')
    t0_t, t0_v = Counter(tk(t) for t in T0['tracks']), Counter(vk(v) for v in T0['vias'])
    t0_rt, t0_rv = Counter(tk(t) for t in T0['remove']), Counter(vk(v) for v in T0['remove_vias'])
    org = {'tracks': Counter(), 'vias': Counter(), 'tracks_mm': Counter()}
    new_t, new_v = [], []
    for t in P['tracks']:
        k = tk(t)
        o = 'prep_transplant' if t0_t[k] else ('source_restored' if src_t[k] else 'new_routing')
        org['tracks'][o] += 1
        org['tracks_mm'][o] += L(t)
        if o == 'new_routing':
            new_t.append(t)
    for v in P['vias']:
        k = vk(v)
        o = 'prep_transplant' if t0_v[k] else ('source_restored' if src_v[k] else 'new_routing')
        org['vias'][o] += 1
        if o == 'new_routing':
            new_v.append(v)
    rorg = {'tracks': Counter(), 'vias': Counter()}
    for t in P['remove']:
        rorg['tracks']['prep_transplant' if t0_rt[tk(t)] else ('ja_rip' if pm(t['net']) else 'other (seeded SOURCE '
                                                                 'net re-routed / dead after routing)')] += 1
    for v in P['remove_vias']:
        rorg['vias']['prep_transplant' if t0_rv[vk(v)] else ('ja_rip' if pm(v['net']) else 'other (seeded SOURCE '
                                                                'net re-routed / dead after routing)')] += 1
    nper = defaultdict(lambda: Counter())
    for t in new_t:
        nper[t['net']]['tracks'] += 1
        nper[t['net']]['mm'] += L(t)
    for v in new_v:
        nper[v['net']]['vias'] += 1
        nper[v['net']]['via ' + kind(v)] += 1
    rep['additions_by_origin'] = {'tracks': dict(org['tracks']), 'vias': dict(org['vias']),
                                  'tracks_mm': {k: round(v, 2) for k, v in org['tracks_mm'].items()}}
    rep['removals_by_origin'] = {k: dict(v) for k, v in rorg.items()}
    rep['new_routing'] = {'tracks': len(new_t), 'vias': len(new_v), 'mm': round(sum(map(L, new_t)), 2),
                          'vias_by_span': dict(sorted(Counter(kind(v) for v in new_v).items())),
                          'tracks_by_layer': dict(sorted(Counter(t['layer'] for t in new_t).items())),
                          'by_net': {k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                                     for k, v in sorted(nper.items())}}
    json.dump(rep, open(sys.argv[3], 'w'), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
