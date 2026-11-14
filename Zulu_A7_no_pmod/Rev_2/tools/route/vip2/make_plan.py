"""No-PMOD Rev 2 (2026-11-13): take the 5 through vias out of SMD pads (rule of 2026-11-11, docs/ltc3556.md).

    python tools/route/vip/move_thru_vias.py <model.json> <PcbDoc> tools/route/vip2/plan1.json
    python tools/route/vip2/make_plan.py tools/route/vip2/plan1.json tools/route/vip2/plan.json

Keeps plan1's moves for R108-1, R108-2, C78-1 and R24-1. Drops plan1's 0.025 mm nudge of the GND via by C161-1: the
model treats C161's rounded pad as its bounding box and the land only meets that box's corner (Fab B accepted the same
via). TCK at R4-6 (Top) has no legal spot within 1.5 mm, so it becomes a stack at the same point, Top>L2 + L2>L3
microvias + L3>L4 buried (TCK has copper only on Top and L4), like the Fab B stacks.
"""
import json, sys
P1 = json.load(open(sys.argv[1]))
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
SKIP = {(4.8, 16.6)}
plan = {'remove': [], 'remove_vias': [], 'tracks': [], 'vias': [], 'report': []}
for v, nv in zip(P1['remove_vias'], P1['vias']):
    if (v['x'], v['y']) not in SKIP:
        plan['remove_vias'].append(v); plan['vias'].append(nv)
plan['tracks'] = [t for t in P1['tracks'] if (t['x1'], t['y1']) not in SKIP]
plan['report'] = [dict(r, action='moved') for r in P1['report'] if tuple(r['from']) not in SKIP]
tck = {'net': 'TCK', 'x': 60.4, 'y': 19.2, 'size': 0.35, 'hole': 0.2, 'span': STACK}
plan['remove_vias'].append(tck)
for a, b in zip(STACK[0:3], STACK[1:4]):
    buried = (a, b) == ('L3-SIG', 'L4-SIG')
    plan['vias'].append({'net': 'TCK', 'x': 60.4, 'y': 19.2, 'size': 0.27 if buried else 0.3, 'hole': 0.15,
                         'from': a, 'to': b, 'span': [a, b]})
for v in plan['vias']:
    v.setdefault('from', v['span'][0]); v.setdefault('to', v['span'][-1])
plan['report'].append({'net': 'TCK', 'from': [60.4, 19.2], 'action': 'stack Top..L4', 'pads': ['R4-6']})
assert len(plan['remove_vias']) == 5 and len(plan['vias']) == 7, (len(plan['remove_vias']), len(plan['vias']))
print(len(plan['remove_vias']), 'removed,', len(plan['vias']), 'vias,', len(plan['tracks']), 'tracks')
json.dump(plan, open(sys.argv[2], 'w'), indent=0)
