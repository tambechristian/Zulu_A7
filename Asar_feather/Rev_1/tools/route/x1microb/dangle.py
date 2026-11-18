"""Dangling track ends and orphan vias in the touched nets of the final model (model0 + plan_raw)."""
import json, math, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
import route_conn as C
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M = json.load(open('model0.json')); P = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'plan_raw.json'))
def same(t, r): return t['net'] == r['net'] and t['layer'] == r['layer'] and {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))}
def samev(v, r): return v['net'] == r['net'] and abs(v['x'] - r['x']) < 0.002 and abs(v['y'] - r['y']) < 0.002 and abs(v['hole'] - r['hole']) < 0.002
T = [t for t in M['tracks'] if not any(same(t, r) for r in P['remove'])] + P['tracks']
V = [v for v in M['vias'] if not any(samev(v, r) for r in P['remove_vias'])] + [dict(v, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in P['vias']]
NETS = {'VU', 'USB5V0', 'USB_D_P', 'USB_D_N', 'GND', 'VCC3V3', 'FLASH-D02', 'CLK-12M-SHARED', 'FT-PWREN#'}
BOX = (-1, 5, 22, 23)
def touches(net, layer, x, y, skip):
    for j, t in enumerate(T):
        if j == skip or t['net'] != net or t['layer'] != layer: continue
        if C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) <= t['w'] / 2 + 1e-4: return True
    for v in V:
        if v['net'] == net and layer in v['span'] and math.hypot(v['x'] - x, v['y'] - y) <= v['size'] / 2 + 1e-4: return True
    for p in M['pads']:
        if p['net'] == net and (layer in p['layers'] or (p['drill'] > 0 and not p['layers'])) and C.pad_point(p, x, y) <= 1e-4: return True
    return False
n = 0
for i, t in enumerate(T):
    if t['net'] not in NETS: continue
    for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
        if not (BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]): continue
        if not touches(t['net'], t['layer'], x, y, i):
            n += 1; print('dangling end', t['net'], t['layer'], (x, y))
for v in V:
    if v['net'] not in NETS or not (BOX[0] <= v['x'] <= BOX[2] and BOX[1] <= v['y'] <= BOX[3]): continue
    hit = 0
    for l in v['span']:
        if l in ('L2-GND', 'L5-VCC3V3'):
            plane = {'L2-GND': 'GND', 'L5-VCC3V3': 'VCC3V3'}[l]
            if v['net'] == plane: hit += 1
            continue
        if any(t['net'] == v['net'] and t['layer'] == l and C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= t['w'] / 2 + v['size'] / 2 for t in T): hit += 1
        elif any(p['net'] == v['net'] and l in p['layers'] and C.pad_point(p, v['x'], v['y']) <= v['size'] / 2 for p in M['pads']): hit += 1
    # stacked neighbours count as a connection
    stack = [w for w in V if w is not v and w['net'] == v['net'] and abs(w['x'] - v['x']) < 1e-3 and abs(w['y'] - v['y']) < 1e-3]
    if hit + len(stack) < 2 and not (hit >= 1 and v['net'] in ('GND', 'VCC3V3')):
        n += 1; print('weak via', v['net'], (v['x'], v['y']), v['span'][0], v['span'][-1], 'hits', hit, 'stack', len(stack))
print('issues', n)
