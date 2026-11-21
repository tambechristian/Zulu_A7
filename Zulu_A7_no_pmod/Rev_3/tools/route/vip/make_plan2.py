"""plan1 moves (<= 0.6 mm) + stacked microvias in place for the rest (no legal spot, or a long jumper).
    python route/vip/make_plan2.py model_now.json plan1.json plan2.json"""
import json, sys
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M = json.load(open(sys.argv[1])); P1 = json.load(open(sys.argv[2]))
MAXMOVE = 0.6
keep = [r for r in P1['report'] if r['moved'] <= MAXMOVE]
kept_from = {tuple(r['from']) for r in keep}
plan = {'remove': [], 'remove_vias': [], 'tracks': [], 'vias': [], 'report': []}
for v, nv in zip(P1['remove_vias'], P1['vias']):
    if (v['x'], v['y']) in kept_from:
        plan['remove_vias'].append(v); plan['vias'].append(nv)
for t in P1['tracks']:
    if (t['x1'], t['y1']) in kept_from:
        plan['tracks'].append(t)
for r in keep:
    r['action'] = 'moved'; plan['report'].append(r)
# every other through via in an SMD pad becomes a stack at the same point
smd = [p for p in M['pads'] if not p['drill'] and p['layers'][0] in ('Top Layer', 'Bottom Layer')]
def gap(p, x, y, r):
    dx = max(abs(x - p['x']) - p['w'] / 2, 0); dy = max(abs(y - p['y']) - p['h'] / 2, 0)
    return (dx * dx + dy * dy) ** .5 - r
for v in M['vias']:
    if len(v['span']) != 6 or (v['x'], v['y']) in kept_from:
        continue
    hit = [p for p in smd if gap(p, v['x'], v['y'], v['size'] / 2) < 0]
    if not hit:
        continue
    side = {p['layers'][0] for p in hit}
    assert side == {'Bottom Layer'}, (v, side)
    top = 'L2-GND' if v['net'] == 'GND' else 'Top Layer'     # GND only needs the L2 plane; VU/USB5V0 need Top
    lo = STACK.index(top)
    plan['remove_vias'].append(v)
    for a, b in zip(STACK[lo:-1], STACK[lo + 1:]):
        buried = (a, b) == ('L3-SIG', 'L4-SIG')
        plan['vias'].append({'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': 0.27 if buried else 0.3, 'hole': 0.15,
                             'from': a, 'to': b, 'span': [a, b]})
    plan['report'].append({'net': v['net'], 'from': [v['x'], v['y']], 'action': 'stack %s..Bottom' % top,
                           'pads': [p['ref'] + '-' + p['pad'] for p in hit]})
print(len(plan['report']), 'sites:', sum(r['action'] == 'moved' for r in plan['report']), 'moved,',
      sum(r['action'] != 'moved' for r in plan['report']), 'stacked;', len(plan['vias']), 'new vias,', len(plan['tracks']), 'tracks')
for r in plan['report']:
    if r['action'] != 'moved': print(r['net'], r['from'], r['action'], r['pads'])
json.dump(plan, open(sys.argv[3], 'w'), indent=0)
