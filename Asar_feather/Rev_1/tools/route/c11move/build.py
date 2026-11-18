"""C11 back beside U4 pin 8 (2026-11-17, docs/c11_move.md).

The schematic draws C11 (0.1 uF 0402) as the SPI boot flash U4's VCC bypass, but the board had it under U3 on the
bottom with C3-C9: U4 (WSON-8, top) had no capacitor within 11.5 mm of its VCC pin. C11 moves to the TOP, horizontal,
VCC3V3 pad 2 at (48.30, 17.505) 0.30 mm east of U4-8 (47.15, 17.505), GND pad 1 at (49.60, 17.505).

  remove  C11's old copper under U3: VCC3V3 laser L5>Bottom (33.95, 6.875) in pad 2, GND through via (32.675, 6.85)
          and its 0.025 mm Bottom stub to pad 1
  add     VCC3V3 Top 0.40 U4-8 centre -> C11-2 centre (the pin-8 via-in-pad already reaches the L5 plane);
          GND Top 0.40 C11-1 centre -> Top>L2 laser 0.30/0.15 at (49.60, 18.35) into the L2 GND plane

model0.json = the saved board (MD5 295cdfc5) from route_model.py; writes model1.json (C11 moved, copper unchanged),
plan.json (emit_copper format) and model_final.json (model1 + plan) for the gates.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M0 = json.load(open(os.path.join(HERE, 'model0.json')))
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
PAD2, PAD1 = (48.30, 17.505), (49.60, 17.505)
VIA = (49.60, 18.35)

M1 = copy.deepcopy(M0)
c11 = [p for p in M1['pads'] if p['ref'] == 'C11']
assert sorted((p['pad'], p['net'], p['x'], p['y'], p['layers'][0]) for p in c11) == [
    ('1', 'GND', 32.93, 7.23, 'Bottom Layer'), ('2', 'VCC3V3', 34.23, 7.23, 'Bottom Layer')], c11
for p in c11:
    p['x'], p['y'] = PAD1 if p['pad'] == '1' else PAD2
    p['layers'] = ['Top Layer']
json.dump(M1, open(os.path.join(HERE, 'model1.json'), 'w'))


def find_v(net, x, y, hole):
    c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002 and abs(v['hole'] - hole) < 0.002]
    assert len(c) == 1, (net, x, y, len(c))
    return c[0]


def find_t(net, layer, x1, y1, x2, y2):
    k = lambda a, b: (round(a, 3), round(b, 3))
    c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) == 1, (net, layer, len(c))
    return c[0]


rmv = [find_v('VCC3V3', 33.95, 6.875, 0.15), find_v('GND', 32.675, 6.85, 0.20)]
rm = [find_t('GND', 'Bottom Layer', 32.675, 6.85, 32.675, 6.875)]
vias = [dict(net='GND', x=VIA[0], y=VIA[1], size=0.30, hole=0.15, **{'from': 'Top Layer', 'to': 'L2-GND'})]
tracks = [dict(net='VCC3V3', layer='Top Layer', w=0.40, x1=47.15, y1=17.505, x2=PAD2[0], y2=PAD2[1]),
          dict(net='GND', layer='Top Layer', w=0.40, x1=PAD1[0], y1=PAD1[1], x2=VIA[0], y2=VIA[1])]
plan = dict(remove=[dict(t) for t in rm], remove_vias=[dict(v) for v in rmv], tracks=tracks, vias=vias)
json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)

ids_t, ids_v = {id(t) for t in rm}, {id(v) for v in rmv}
MF = copy.deepcopy(M1)
MF['tracks'] = [t for t, t0 in zip(MF['tracks'], M0['tracks']) if id(t0) not in ids_t] + tracks
MF['vias'] = [v for v, v0 in zip(MF['vias'], M0['vias']) if id(v0) not in ids_v] + [
    dict({k: v[k] for k in v if k not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in vias]
json.dump(MF, open(os.path.join(HERE, 'model_final.json'), 'w'))
print('plan: remove %d tracks + %d vias, add %d tracks + %d vias; model_final %d tracks %d vias' % (
    len(rm), len(rmv), len(tracks), len(vias), len(MF['tracks']), len(MF['vias'])))
