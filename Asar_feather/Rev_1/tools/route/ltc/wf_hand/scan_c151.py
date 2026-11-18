"""scan valid Bottom placements of a C0603 (C151) and report whether pad2 can take a full Bottom->Top stack"""
import json, math, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/tools/route/ltc')
import place_check as PC
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/tools')
import route_conn as C

M = json.load(open(sys.argv[1]))
REF = sys.argv[2] if len(sys.argv) > 2 else 'C151'
x0, x1, y0, y1 = [float(v) for v in sys.argv[3:7]] if len(sys.argv) > 6 else (6, 22, 8, 22.5)
# drop the moved part and PWR_FB2 Bottom run near U8 north
M['pads'] = [p for p in M['pads'] if p['ref'] != REF]
nets = {('C151', '1'): 'GND', ('C151', '2'): 'VBATT', ('C150', '1'): 'GND', ('C150', '2'): 'USB5V0'}
W, H = M['board']['w'], M['board']['h']
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def ok_pad(p):
    L = p['layers'][0]
    e = min(p['x'] - p['w'] / 2, W - p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, H - p['y'] - p['h'] / 2)
    if e < 0.3:
        return False
    for q in M['pads']:
        if L in q['layers'] or q.get('drill', 0) > 0:
            if abs(q['x'] - p['x']) > 4 or abs(q['y'] - p['y']) > 4:
                continue
            if PC.rect_gap(p, q) < 0.199:
                return False
    for t in M['tracks']:
        if t['layer'] == L and t['net'] != p['net'] and abs(t['x1'] - p['x']) < 3 and abs(t['y1'] - p['y']) < 3:
            if PC.seg_rect_gap(t, p) < 0.099:
                return False
    for v in M['vias']:
        if L in v['span'] and v['net'] != p['net'] and abs(v['x'] - p['x']) < 2 and abs(v['y'] - p['y']) < 2:
            dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0)
            dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
            if math.hypot(dx, dy) - v['size'] / 2 < 0.099:
                return False
    return True

def via_free(x, y, r, layers, net):
    for L in layers:
        for p in M['pads']:
            if (L in p['layers'] or p.get('drill', 0) > 0) and p['net'] != net and abs(p['x'] - x) < 3 and abs(p['y'] - y) < 3:
                if C.pad_point(p, x, y) - r < 0.09:
                    return False
        for t in M['tracks']:
            if t['layer'] == L and t['net'] != net and abs(t['x1'] - x) < 4 and abs(t['y1'] - y) < 4:
                if C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) - r - t['w'] / 2 < 0.09:
                    return False
        for v in M['vias']:
            if L in v['span'] and v['net'] != net and abs(v['x'] - x) < 2 and abs(v['y'] - y) < 2:
                if math.hypot(v['x'] - x, v['y'] - y) - r - v['size'] / 2 < 0.09:
                    return False
    for v in M['vias']:
        if abs(v['x'] - x) < 1 and abs(v['y'] - y) < 1 and math.hypot(v['x'] - x, v['y'] - y) - v['hole'] / 2 - 0.075 < 0.24:
            return False
    return True

res = []
x = x0
while x <= x1:
    y = y0
    while y <= y1:
        for rot in (0, 90, 180, 270):
            pads = PC.pads_of('C151', 'B', x, y, rot, nets)
            if all(ok_pad(p) for p in pads):
                p2 = [p for p in pads if p['pad'] == '2'][0]
                full = via_free(p2['x'], p2['y'], 0.15, STACK[:-1], 'VBATT')
                res.append((round(x, 3), round(y, 3), rot, full))
                break
        y += 0.1
    x += 0.1
for r in res:
    print(r)
print(len(res))
