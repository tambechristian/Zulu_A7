"""Stage A of the X4 side-entry conversion: hand removals + additions on the router model.
Writes hand_plan.json (remove / remove_vias / tracks / vias), model1.json (new pads, M0 copper) and route_in.json
(model1 with the hand plan applied: the router's input)."""
import json, sys
sys.argv = [sys.argv[0], '5.45', '19.0', '0']
import geom
M0 = json.load(open('model0.json'))
M1 = geom.new_model(M0)
json.dump(M1, open('model1.json', 'w'))

def find_t(net, layer, x1, y1, x2, y2):
    k = {(round(x1, 3), round(y1, 3)), (round(x2, 3), round(y2, 3))}
    c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == k]
    assert len(c) >= 1, (net, layer, x1, y1, x2, y2)
    return c
def find_v(net, x, y):
    c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002]
    assert c, (net, x, y)
    return c
TOP, L3, L4, BOT = 'Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer'
rm, rmv = [], []
rm += find_t('VBATT', TOP, 10.25, 14.725, 10.25, 15.3) + find_t('VBATT', TOP, 10.25, 14.725, 11.6, 14.725)
rmv += find_v('GND', 11.425, 16.925)
rm += find_t('EE-DATA', TOP, 12.325, 13.875, 12.325, 13.9); rmv += find_v('EE-DATA', 12.325, 13.875)
rm += find_t('EE-CLK', TOP, 11.775, 13.05, 12.125, 13.4)
rm += find_t('VU', TOP, 6.575, 21.825, 14.775, 21.825); rmv += find_v('VU', 6.575, 21.825) + find_v('VU', 14.775, 21.825)
rmv += find_v('GND', 5.65, 20.35); rm += find_t('GND', BOT, 5.65, 20.35, 5.65, 20.375)
# de-duplicate (find_t may return twins of a duplicated track: each board twin needs its own entry)
def tk(t): return (t['net'], t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
seen, rm2 = set(), []
for t in rm:
    if id(t) not in seen:
        seen.add(id(t)); rm2.append(t)
rm = rm2
seen, rmv2 = set(), []
for v in rmv:
    if id(v) not in seen:
        seen.add(id(v)); rmv2.append(v)
rmv = rmv2
W = lambda net, layer, w, x1, y1, x2, y2: dict(net=net, layer=layer, w=w, x1=x1, y1=y1, x2=x2, y2=y2)
V = lambda net, x, y, size, hole, a, b: dict(net=net, x=x, y=y, size=size, hole=hole, **{'from': a, 'to': b})
add_t = [W('VU', TOP, 0.4, 8.8, 17.5, 12.775, 17.5)]
add_v = [V('GND', 5.95, 21.13, 0.35, 0.20, TOP, BOT)]
for y in (14.0, 15.05, 16.1):
    add_v.append(V('GND', 9.8, y, 0.30, 0.15, TOP, 'L2-GND'))
plan = dict(remove=rm, remove_vias=rmv, tracks=add_t, vias=add_v)
json.dump(plan, open('hand_plan.json', 'w'), indent=0)
# router input: model1 minus removals plus additions
ids_t = {id(t) for t in rm}; ids_v = {id(v) for v in rmv}
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
R = dict(M1)
R['tracks'] = [t for t in M0['tracks'] if id(t) not in ids_t] + add_t
R['vias'] = [v for v in M0['vias'] if id(v) not in ids_v] + [dict({k: v[k] for k in v if k not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in add_v]
json.dump(R, open('route_in.json', 'w'))
print('remove %d tracks, %d vias; add %d tracks, %d vias' % (len(rm), len(rmv), len(add_t), len(add_v)))
