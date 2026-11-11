import json, math, sys
sys.path.insert(0, '..')
import place_check as PC
M = json.load(open('m1.json'))
nets = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
others = [p for p in M['pads'] if p['ref'] != 'C167']
def ok(side, x, y, rot):
    pads = PC.pads_of('C167', side, x, y, rot, nets)
    worst = 9
    for p in pads:
        L = p['layers'][0]
        for q in others:
            if L in q['layers'] or q.get('drill', 0) > 0:
                if abs(q['x']-p['x']) > 4 or abs(q['y']-p['y']) > 4: continue
                g = PC.rect_gap(p, q); worst = min(worst, g - 0.2)
        for t in M['tracks']:
            if t['layer'] == L and t['net'] != p['net'] and min(abs(t['x1']-p['x']), abs(t['x2']-p['x'])) < 5 and min(abs(t['y1']-p['y']), abs(t['y2']-p['y'])) < 5:
                worst = min(worst, PC.seg_rect_gap(t, p) - 0.1)
        for v in M['vias']:
            if L in v['span'] and v['net'] != p['net'] and abs(v['x']-p['x']) < 3 and abs(v['y']-p['y']) < 3:
                dx = max(abs(v['x']-p['x'])-p['w']/2, 0); dy = max(abs(v['y']-p['y'])-p['h']/2, 0)
                worst = min(worst, math.hypot(dx, dy) - v['size']/2 - 0.1)
        if p['x'] < 0.6 or p['y'] < 0.6: worst = -1
    return worst
res = []
for i in range(0, 121):
    for j in range(0, 45):
        x = 0.8 + i * 0.2; y = 0.8 + j * 0.5
        for rot in (0, 90, 180, 270):
            w = ok('B', x, y, rot)
            if w >= 0: res.append((x, y, rot, round(w, 3)))
print(len(res))
for r in res: print(r)
