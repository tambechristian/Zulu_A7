"""mk_tdi.py: hand re-route around the moved X2.30 (CHAN20) so TDI can pass: CHAN25 to the Top edge band north of
X2.30, TDO's west part re-joined at 39.0,2.2 along y 2.62, TDI L3 -> buried via 37.55,2.3 -> L4 up the X2.30/X2.29
gap -> L4 edge band y 0.35 -> TDI via 43.4,1.0 (replacing the old y 0.30 band). Writes hand_tdi.json."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
M = E.load('model_E3.json'); S = E.load('f1_s1.json')
W = 0.0762


def T(net, pts, layer, w=W):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]} for a, b in zip(pts, pts[1:])]


def V(net, x, y, objs):
    return [{'net': net, 'x': x, 'y': y, 'size': s, 'hole': 0.15, 'from': f, 'to': t} for f, t, s in objs]


STK = (('Top Layer', 'L2-GND', 0.3), ('L2-GND', 'L3-SIG', 0.3))
BUR = (('L3-SIG', 'L4-SIG', 0.27),)
rm_t, rm_v = [], []
# CHAN25 router detour (seed)
for t in S['tracks']:
    if t['net'] == 'CHAN25' and min(t['x1'], t['x2']) >= 35.27 and max(t['x1'], t['x2']) <= 38.21 and max(t['y1'], t['y2']) <= 2.2 \
            and t['layer'] in ('L3-SIG', 'L4-SIG'):
        rm_t.append(t)
    if t['net'] == 'TDO' and t['layer'] == 'L4-SIG' and min(t['x1'], t['x2']) >= 36.39 and max(t['x1'], t['x2']) <= 38.26:
        rm_t.append(t)
    if t['net'] == 'CHAN20' and t['layer'] == 'L3-SIG' and abs(t['x1'] - 37.0) < 1e-6 and abs(t['y1'] - 2.475) < 1e-6:
        rm_t.append(t)
for v in S['vias']:
    if v['net'] == 'CHAN25' and ((abs(v['x'] - 35.35) < 1e-6 and abs(v['y'] - 1.1) < 1e-6) or (abs(v['x'] - 37.8) < 1e-6 and abs(v['y'] - 0.95) < 1e-6)):
        rm_v.append(v)
# board copper
for t in M['tracks']:
    k = (t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
    if k in {('TDO', 'L4-SIG', 38.15, 1.35, 39.0, 2.2), ('TDI', 'L4-SIG', 38.8, 0.3, 42.7, 0.3), ('TDI', 'L4-SIG', 42.7, 0.3, 43.4, 1.0)}:
        rm_t.append(t)
for v in M['vias']:
    if (v['net'] == 'TDO' and abs(v['x'] - 38.15) < 1e-6 and abs(v['y'] - 1.35) < 1e-6) or \
            (v['net'] == 'CHAN25' and abs(v['x'] - 38.2) < 1e-6 and abs(v['y'] - 1.0) < 1e-6):
        rm_v.append(v)
add_t = (T('CHAN25', [(35.3, 1.0), (35.55, 0.75)], 'L3-SIG') +
         T('CHAN25', [(35.55, 0.75), (35.94, 0.36), (37.6, 0.36), (38.2, 0.96), (38.2, 1.0)], 'Top Layer') +
         T('TDO', [(36.4, 2.325), (36.695, 2.62), (38.6, 2.62), (39.0, 2.22), (39.0, 2.2)], 'L4-SIG') +
         T('CHAN20', [(37.9, 2.475), (38.825, 2.475)], 'L3-SIG') +
         T('TDI', [(35.1, 4.0), (35.75, 3.35), (36.15, 2.95), (37.0, 2.95), (37.55, 2.3)], 'L3-SIG') +
         T('TDI', [(37.55, 2.3), (38.1, 1.75), (38.1, 0.7), (38.45, 0.35), (42.7, 0.35), (43.4, 1.0)], 'L4-SIG'))
add_v = V('CHAN25', 35.55, 0.75, STK) + V('TDI', 37.55, 2.3, BUR)
print('remove %d tracks %d vias; add %d tracks %d vias' % (len(rm_t), len(rm_v), len(add_t), len(add_v)))
from collections import Counter
print(Counter(t['net'] for t in rm_t), Counter(v['net'] for v in rm_v))
json.dump({'tracks': add_t, 'vias': add_v, 'remove': rm_t, 'remove_vias': rm_v}, open('hand_tdi.json', 'w'), indent=1)
