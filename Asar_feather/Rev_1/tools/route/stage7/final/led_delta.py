"""LED row and pin labels, 2026-11-06: turn the finished trial into the files that go on the board.

    python led_delta.py <final_plan.json> <trial_model.json> <labels.json>

Writes, next to this file:
  model.led.json   the trial model
  plan.led.json    the full plan, judged by route_check and verify_copper
  labels.led.json  the silk texts (anchor, rotation, size, stroke, full box)
  delta_led.json   what changes against plan.stemma.json: 'remove' + 'remove_vias' + new tracks and vias, for emit_copper
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
plan_f, model_f, labels_f = sys.argv[1:4]
P, M, L = json.load(open(plan_f)), json.load(open(model_f)), json.load(open(labels_f))
B = json.load(open(os.path.join(HERE, 'plan.stemma.json')))
M0 = json.load(open(os.path.join(HERE, 'model.stemma.json')))

MOVED = {'LD0', 'LD1', 'LD2', 'LD5', 'R78', 'R83', 'R84'}
k0 = {(p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3)): p for p in M0['pads']}
for p in M['pads']:
    if p['ref'] not in MOVED and (p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3)) not in k0:
        sys.exit('REFUSED: %s-%s moved and is not on the list' % (p['ref'], p['pad']))
assert Counter((p['ref'], p['pad'], p['net']) for p in M['pads']) == Counter((p['ref'], p['pad'], p['net']) for p in M0['pads']), 'pads or nets differ'


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
print('removals sharing net, centre and hole with a via that stays: %d' % len(clash))
for v in clash:
    print('   ', v['net'], v['x'], v['y'], v['from'], v['to'], v['hole'])

json.dump(M, open(os.path.join(HERE, 'model.led.json'), 'w'))
json.dump(dict(P, log=P.get('log', [])[-20:] + ['led row + pin labels']), open(os.path.join(HERE, 'plan.led.json'), 'w'), indent=0)
json.dump(L, open(os.path.join(HERE, 'labels.led.json'), 'w'), indent=0)
json.dump({'vias': add_v, 'tracks': add_t, 'remove': rem_t, 'remove_vias': rem_v, 'log': ['delta plan.stemma -> plan.led']},
          open(os.path.join(HERE, 'delta_led.json'), 'w'), indent=0)
LAS = {('Top Layer', 'L2-GND'), ('L2-GND', 'L3-SIG'), ('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom Layer')}
vip = json.load(open(os.path.join(HERE, 'vip.final.json')))
print('delta: tracks -%d +%d, vias -%d +%d' % (len(rem_t), len(add_t), len(rem_v), len(add_v)))
print('nets touched:', sorted({o['net'] for o in rem_t + add_t + rem_v + add_v}))
print('NV %d  NT %d  NE %d' % (len(P['vias']) + len(vip['vias']), len(P['tracks']),
                               sum((v['from'], v['to']) in LAS for v in P['vias'] + vip['vias'])))
print('first new via:', add_v[0]['net'], add_v[0]['x'], add_v[0]['y'])
print('labels:', ' '.join(l['text'] for l in L))
