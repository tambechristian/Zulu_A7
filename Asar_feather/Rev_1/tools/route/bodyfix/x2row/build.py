"""x2row fix (Asar A7 Feather, 2026-11-19): the twelve bottom 0201s under the edge of X2's south header housing move
north together, R18 nudges to open the TDI lane, and the copper the move makes illegal is rebuilt.

Inputs: Rev_1/tools/route/body_gate/model.json (the saved board, md5 c4bf0b71), read-only.
Outputs (this folder): model1.json (parts moved, copper unchanged), plan.json (emit_copper format incl. 'moves'),
model_final.json (model1 + plan, vias with 'span').

MOVES
  C40 C41 C152 C153 C154 R19 C155 C156 C157 C158 C159 C38   (0, +0.125)  pads y 2.670 -> 2.795, body 0.105 clear of X2
  R18 (0402, FT-REF 12k)                                     (+0.02, +0.05) widens the Bottom lane over C41 for TDI
COPPER
  jogs     21 Bottom tracks, via centre -> moved pad centre (GND/VCC3V3/FT-VPLL 0.20, FT-VPHY/FT-VCORE 0.15): the vias
           stay (the GND ones are through vias under U2's south pad row on Top, they cannot follow)
  FT-VCORE stack 45+5B (14.500, 2.900) -> (14.470, 2.920) and its two tracks: C153-1 had moved to 0.070 of it
  FT-RESETN the Bottom run (14.725,3.425) -> R19-1 under C153/C154 and its 45+5B stack go; L4 carries on from
           (14.725,3.425) at y 3.60 to a stack_bot (L4>L5>Bottom 0.30/0.15) in R19-1's pad
  TDI      the through via under U2-17 (9.825,3.075) -> (9.825,3.200) and the Bottom run over C41 is re-laid at
           y 3.0875, centred in the C41 / R18-2 lane, back onto the old track at (11.05, 3.275)
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REV = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1'
M0 = json.load(open(REV + '/tools/route/body_gate/model.json'))
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
AB = {'Top Layer': 'T', 'L2-GND': '2', 'L3-SIG': '3', 'L4-SIG': '4', 'L5-VCC3V3': '5', 'Bottom Layer': 'B'}
ROW = ['C40', 'C41', 'C152', 'C153', 'C154', 'R19', 'C155', 'C156', 'C157', 'C158', 'C159', 'C38']
DY = 0.125
MOVES = [dict(ref=r, dx=0.0, dy=DY) for r in ROW] + [dict(ref='R18', dx=0.02, dy=0.05)]

M1 = copy.deepcopy(M0)
mv = {m['ref']: m for m in MOVES}
for p in M1['pads']:
    if p['ref'] in mv:
        p['x'] = round(p['x'] + mv[p['ref']]['dx'], 4)
        p['y'] = round(p['y'] + mv[p['ref']]['dy'], 4)


def padc(ref, pad):
    c = [p for p in M1['pads'] if p['ref'] == ref and p['pad'] == pad]
    assert len(c) == 1, (ref, pad)
    return c[0]['x'], c[0]['y']


def find_v(net, x, y, span=None):
    c = [v for v in M0['vias'] if v['net'] == net and abs(v['x'] - x) < 0.002 and abs(v['y'] - y) < 0.002 and
         (span is None or ''.join(AB[l] for l in v['span']) == span)]
    assert len(c) == 1, (net, x, y, span, len(c))
    return c[0]


def find_t(net, layer, x1, y1, x2, y2):
    k = lambda a, b: (round(a, 3), round(b, 3))
    c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and
         {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
    return c[0]


def via(net, x, y, f, t, size=0.30, hole=0.15):
    return {'net': net, 'x': x, 'y': y, 'size': size, 'hole': hole, 'from': f, 'to': t}


def trk(net, layer, w, a, b):
    return dict(net=net, layer=layer, w=w, x1=a[0], y1=a[1], x2=b[0], y2=b[1])


rm_t, rm_v, add_t, add_v = [], [], [], []

# 1. jogs: (net, via centre that stays, pad, width)
JOGS = [
    ('GND', (8.750, 2.525), ('C40', '1'), 0.20), ('FT-VPHY', (9.675, 2.500), ('C40', '2'), 0.15),
    ('GND', (10.175, 2.350), ('C41', '1'), 0.20), ('FT-VPLL', (10.675, 2.350), ('C41', '2'), 0.20),
    ('GND', (13.550, 2.325), ('C152', '1'), 0.20), ('GND', (14.725, 2.350), ('C153', '1'), 0.20),
    ('FT-VCORE', (15.675, 2.475), ('C153', '2'), 0.15), ('GND', (16.175, 2.350), ('C154', '1'), 0.20),
    ('VCC3V3', (17.775, 2.550), ('R19', '2'), 0.20),
    ('GND', (19.350, 2.525), ('C155', '1'), 0.20), ('VCC3V3', (19.950, 2.550), ('C155', '2'), 0.20),
    ('GND', (20.575, 2.300), ('C156', '1'), 0.20), ('VCC3V3', (21.150, 2.550), ('C156', '2'), 0.20),
    ('GND', (21.775, 2.525), ('C157', '1'), 0.20), ('VCC3V3', (22.350, 2.550), ('C157', '2'), 0.20),
    ('GND', (22.950, 2.525), ('C158', '1'), 0.20), ('VCC3V3', (23.575, 2.550), ('C158', '2'), 0.20),
    ('GND', (24.150, 2.525), ('C159', '1'), 0.20), ('VCC3V3', (24.775, 2.550), ('C159', '2'), 0.20),
    ('GND', (25.350, 2.525), ('C38', '1'), 0.20), ('VCC3V3', (25.950, 2.550), ('C38', '2'), 0.20),
]
for net, c, (ref, pad), w in JOGS:
    assert any(v['net'] == net and abs(v['x'] - c[0]) < 0.002 and abs(v['y'] - c[1]) < 0.002 and 'Bottom Layer' in v['span']
               for v in M0['vias']), (net, c)
    add_t.append(trk(net, 'Bottom Layer', w, c, padc(ref, pad)))

# 2. FT-VCORE stack beside C153-1
OLD, NEW = (14.5, 2.9), (14.47, 2.92)
for sp in ('45', '5B'):
    v = find_v('FT-VCORE', OLD[0], OLD[1], sp)
    rm_v.append(v)
    add_v.append(via('FT-VCORE', NEW[0], NEW[1], v['span'][0], v['span'][-1], v['size'], v['hole']))
for layer, other in (('Bottom Layer', (14.375, 2.775)), ('L4-SIG', (15.35, 2.7))):
    t = find_t('FT-VCORE', layer, OLD[0], OLD[1], *other)
    rm_t.append(t)
    add_t.append(trk('FT-VCORE', layer, t['w'], other, NEW))

# 3. FT-RESETN: Bottom run -> L4 + stack_bot in R19-1
for seg in [(14.725, 3.425, 15.15, 3.0), (15.15, 3.0, 16.675, 3.0), (16.675, 3.0, 16.725, 2.975),
            (16.725, 2.975, 16.75, 2.95), (16.75, 2.95, 16.875, 2.95), (16.875, 2.95, 16.975, 2.85),
            (16.975, 2.85, 17.15, 2.775)]:
    rm_t.append(find_t('FT-RESETN', 'Bottom Layer', *seg))
for sp in ('45', '5B'):
    rm_v.append(find_v('FT-RESETN', 14.725, 3.425, sp))
R19 = padc('R19', '1')
YL4 = 3.60
for a, b in [((14.725, 3.425), (14.9, YL4)), ((14.9, YL4), (R19[0], YL4)), ((R19[0], YL4), R19)]:
    add_t.append(trk('FT-RESETN', 'L4-SIG', 0.0762, a, b))
add_v += [via('FT-RESETN', R19[0], R19[1], 'L4-SIG', 'L5-VCC3V3'), via('FT-RESETN', R19[0], R19[1], 'L5-VCC3V3', 'Bottom Layer')]

# 4. TDI: via under U2-17 north with the row, Bottom run re-laid in the C41 / R18-2 lane
TV_OLD, TV_NEW = (9.825, 3.075), (9.825, 3.200)
v = find_v('TDI', *TV_OLD)
rm_v.append(v)
add_v.append(via('TDI', TV_NEW[0], TV_NEW[1], 'Top Layer', 'Bottom Layer', v['size'], v['hole']))
for layer, *seg in [('Top Layer', 9.825, 3.075, 9.85, 3.075), ('Bottom Layer', 9.825, 3.075, 10.025, 3.05),
                    ('Bottom Layer', 10.025, 3.05, 10.825, 3.05), ('Bottom Layer', 10.825, 3.05, 11.05, 3.275)]:
    rm_t.append(find_t('TDI', layer, *seg))
c41 = padc('C41', '1')[1] + 0.15                                       # C41 pad tops 2.945
r18 = [p for p in M1['pads'] if p['ref'] == 'R18' and p['pad'] == '2'][0]
r18b = r18['y'] - r18['h'] / 2                                         # R18-2 bottom 3.230
YT = round((c41 + r18b) / 2, 4)                                        # 3.0875
XE = round(11.05 - (3.275 - YT), 4)                                    # 45 degrees back onto (11.05, 3.275)
for a, b in [(TV_NEW, (9.95, YT)), ((9.95, YT), (XE, YT)), ((XE, YT), (11.05, 3.275))]:
    add_t.append(trk('TDI', 'Bottom Layer', 0.0762, a, b))

plan = dict(moves=MOVES, remove=[dict(t) for t in rm_t], remove_vias=[dict(v) for v in rm_v], tracks=add_t, vias=add_v)

it, iv = {id(t) for t in rm_t}, {id(v) for v in rm_v}
MF = copy.deepcopy(M1)
MF['tracks'] = [t2 for t2, t0 in zip(MF['tracks'], M0['tracks']) if id(t0) not in it] + [dict(t) for t in add_t]
MF['vias'] = [v2 for v2, v0 in zip(MF['vias'], M0['vias']) if id(v0) not in iv] + [
    dict({k: v[k] for k in v if k not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in add_v]

if __name__ == '__main__':
    json.dump(M1, open(os.path.join(HERE, 'model1.json'), 'w'))
    json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
    json.dump(MF, open(os.path.join(HERE, 'model_final.json'), 'w'))
    print('moves %d parts; remove %d tracks + %d vias; add %d tracks + %d vias; model_final %d tracks %d vias' % (
        len(MOVES), len(rm_t), len(rm_v), len(add_t), len(add_v), len(MF['tracks']), len(MF['vias'])))
    print('TDI lane y %.4f (C41 top %.3f, R18-2 bottom %.3f), diagonal from x %.4f' % (YT, c41, r18b, XE))
