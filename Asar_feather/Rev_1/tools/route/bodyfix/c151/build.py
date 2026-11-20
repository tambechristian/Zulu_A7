"""C151 off U8's body corner (2026-11-19, body gate fix "c151").

C151 (VBATT bypass of U8 pin 23, 0603, Bottom, rot 180) moves +0.50 mm east (dy 0): pad 2 VBATT (12.7502, 14.45) ->
(13.2502, 14.45), pad 1 GND (14.45, 14.45) -> (14.95, 14.45). Pad 2's west edge goes from 12.20 to 12.70: 0.20 mm from
U8's nominal body (x <= 12.5), 0.15 from its maximum-tolerance body (x <= 12.55). It cannot move north or south: L8-2 /
C147-2 (VU) below and C82 above already sit at the 0.2 mm pad gap (0.1 mask web), so east is the only way out.

Moving east puts pad 1 over the VU through via (15.55, 14.225) that joins the L8/C147 VOUT copper on Bottom to the Top
VU feed (VIN1/VIN2/VIN3). No 0.35/0.20 through-via site outside a pad is legal anywhere near it (Q1 on Top, L4 USB5V0,
the L3/L4 PWR_FB2 via, the VCC1V8 lasers, C93), so the via moves INTO C147 pad 2 (VU), hole fully in the pad -- the
board's standing practice (108 through vias in SMD pads, resin-plugged and capped):
  remove  VU through via (15.55, 14.225); VU Bottom 0.4 (15.2, 13.5)-(15.55, 14.225) and its 0.025 stub
          (15.525, 14.225)-(15.55, 14.225); VU Top 0.4 (14.475, 14.55)-(15.55, 14.225)
  add     VU through via 0.35/0.20 at (14.60, 13.45) in C147-2; VU Top 0.4 (14.60, 13.45)-(14.475, 14.55) onto the
          existing Top VU spine (14.475, 14.55)-(14.475, 17.5)
          VBATT Bottom 0.4 (12.75, 14.9)-(13.2502, 14.45): the existing U8-23 track end now sits only 0.05 mm inside
          pad 2, so this keeps a full 0.4 mm junction into the pad centre
The GND stack in pad 1 (14.75, 14.6, L2..Bottom) stays inside the moved pad (pad 1 x 14.40..15.50).

model0 = Asar_feather/Rev_1/tools/route/body_gate/model.json (saved board md5 c4bf0b71), read only.
Writes model1.json (C151 moved, copper unchanged), plan.json (emit_copper format incl. 'moves'), model_final.json.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools/route/body_gate/model.json'
M0 = json.load(open(SRC))
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
DX, DY = 0.50, 0.0
VIA = (14.60, 13.45)

M1 = copy.deepcopy(M0)
c151 = [p for p in M1['pads'] if p['ref'] == 'C151']
assert sorted((p['pad'], p['net'], round(p['x'], 4), round(p['y'], 4), p['layers'][0]) for p in c151) == [
    ('1', 'GND', 14.45, 14.45, 'Bottom Layer'), ('2', 'VBATT', 12.7502, 14.45, 'Bottom Layer')], c151
for p in c151:
    p['x'] = round(p['x'] + DX, 6)
    p['y'] = round(p['y'] + DY, 6)
P2 = [(p['x'], p['y']) for p in c151 if p['pad'] == '2'][0]
json.dump(M1, open(os.path.join(HERE, 'model1.json'), 'w'))


def find_v(net, x, y, hole):
    c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002 and abs(v['hole'] - hole) < 0.002]
    assert len(c) == 1, (net, x, y, len(c))
    return c[0]


def find_t(net, layer, x1, y1, x2, y2):
    k = lambda a, b: (round(a, 3), round(b, 3))
    c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
    return c[0]


rmv = [find_v('VU', 15.55, 14.225, 0.20)]
rm = [find_t('VU', 'Bottom Layer', 15.2, 13.5, 15.55, 14.225),
      find_t('VU', 'Bottom Layer', 15.525, 14.225, 15.55, 14.225),
      find_t('VU', 'Top Layer', 14.475, 14.55, 15.55, 14.225)]
vias = [dict(net='VU', x=VIA[0], y=VIA[1], size=0.35, hole=0.20, **{'from': 'Top Layer', 'to': 'Bottom Layer'})]
tracks = [dict(net='VU', layer='Top Layer', w=0.40, x1=VIA[0], y1=VIA[1], x2=14.475, y2=14.55),
          dict(net='VBATT', layer='Bottom Layer', w=0.40, x1=12.75, y1=14.9, x2=P2[0], y2=P2[1])]
plan = dict(moves=[dict(ref='C151', dx=DX, dy=DY)], remove=[dict(t) for t in rm], remove_vias=[dict(v) for v in rmv],
            tracks=tracks, vias=vias)
json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)

ids_t, ids_v = {id(t) for t in rm}, {id(v) for v in rmv}
MF = copy.deepcopy(M1)
MF['tracks'] = [t for t, t0 in zip(MF['tracks'], M0['tracks']) if id(t0) not in ids_t] + tracks
MF['vias'] = [v for v, v0 in zip(MF['vias'], M0['vias']) if id(v0) not in ids_v] + [
    dict({k: v[k] for k in v if k not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in vias]
json.dump(MF, open(os.path.join(HERE, 'model_final.json'), 'w'))
print('plan: move C151 (%+.2f, %+.2f); remove %d tracks + %d vias, add %d tracks + %d vias; model_final %d tracks %d vias' % (
    DX, DY, len(rm), len(rmv), len(tracks), len(vias), len(MF['tracks']), len(MF['vias'])))
