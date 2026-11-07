"""STEMMA QT, 2026-11-06: turn the finished trial into the files that go on the board.

    python stemma_delta.py <pruned_plan.json> <trial_model.json>

Writes, next to this file:
  model.stemma.json  the trial model with the connector named X5 (pads 1 2 3 4 MP1 MP2)
  plan.stemma.json   the full plan, judged by route_check and verify_copper
  delta_stemma.json  what changes against plan.clean.json: 'remove' + 'remove_vias' + new tracks and vias, for emit_copper
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
plan_f, model_f = sys.argv[1:3]
P, M = json.load(open(plan_f)), json.load(open(model_f))
B = json.load(open(os.path.join(HERE, 'plan.clean.json')))

mp = 0
for p in sorted([p for p in M['pads'] if p['ref'] == 'J9'], key=lambda q: q['y']):
    p['ref'] = 'X5'
    if p['pad'] == 'MP':
        mp += 1
        p['pad'] = 'MP%d' % mp
assert sorted(p['pad'] for p in M['pads'] if p['ref'] == 'X5') == ['1', '2', '3', '4', 'MP1', 'MP2']


def kt(t):
    return (t['net'], t['layer'], round(t['w'], 3),
            tuple(sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))])))


def kv(v):
    return (v['net'], round(v['x'], 3), round(v['y'], 3), v['from'], v['to'], round(v['hole'], 3), round(v['size'], 3))


pt, bt = {kt(t): t for t in P['tracks']}, {kt(t): t for t in B['tracks']}
pv, bv = {kv(v): v for v in P['vias']}, {kv(v): v for v in B['vias']}
assert len(pt) == len(P['tracks']) and len(pv) == len(P['vias'])
rem_t = [bt[k] for k in bt if k not in pt]
add_t = [pt[k] for k in pt if k not in bt]
rem_v = [bv[k] for k in bv if k not in pv]
add_v = [pv[k] for k in pv if k not in bv]

# emit_copper removes a via by net, hole and centre: a removal must not catch a via of the same stack that stays
stay = Counter((k[0], k[1], k[2], k[5]) for k in pv if k in bv)
clash = [v for v in rem_v if stay[(v['net'], round(v['x'], 3), round(v['y'], 3), round(v['hole'], 3))]]
if clash:
    sys.exit('REFUSED: removing %d vias would also catch stack members that stay: %s' % (len(clash), clash[:4]))

json.dump(M, open(os.path.join(HERE, 'model.stemma.json'), 'w'))
json.dump(dict(P, log=P.get('log', [])[-20:] + ['stemma: X5 SM04B-SRSS-TB']), open(os.path.join(HERE, 'plan.stemma.json'), 'w'), indent=0)
json.dump({'vias': add_v, 'tracks': add_t, 'remove': rem_t, 'remove_vias': rem_v, 'log': ['delta plan.clean -> plan.stemma']},
          open(os.path.join(HERE, 'delta_stemma.json'), 'w'), indent=0)
LAS = {('Top Layer', 'L2-GND'), ('L2-GND', 'L3-SIG'), ('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom Layer')}
vip = json.load(open(os.path.join(HERE, 'vip.final.json')))
print('delta: tracks -%d +%d, vias -%d +%d' % (len(rem_t), len(add_t), len(rem_v), len(add_v)))
print('nets touched:', sorted({o['net'] for o in rem_t + add_t + rem_v + add_v}))
print('NV %d  NT %d  NE %d' % (len(P['vias']) + len(vip['vias']), len(P['tracks']),
                               sum((v['from'], v['to']) in LAS for v in P['vias'] + vip['vias'])))
print('first new via:', add_v[0]['net'], add_v[0]['x'], add_v[0]['y'])
