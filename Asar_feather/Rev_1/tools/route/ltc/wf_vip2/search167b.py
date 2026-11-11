import json, math, sys
sys.path.insert(0, '..')
import place_check as PC
M = json.load(open(sys.argv[1]))
X0, X1, Y0, Y1, ST = map(float, sys.argv[2:7]); side = sys.argv[7]
L = 'Bottom Layer' if side == 'B' else 'Top Layer'
nets = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
inb = lambda x, y: X0 - 2 < x < X1 + 2 and Y0 - 2 < y < Y1 + 2
pads = [q for q in M['pads'] if q['ref'] != 'C167' and (L in q['layers'] or q.get('drill', 0) > 0) and inb(q['x'], q['y'])]
trs = [t for t in M['tracks'] if t['layer'] == L and (inb(t['x1'], t['y1']) or inb(t['x2'], t['y2']))]
vis = [v for v in M['vias'] if L in v['span'] and inb(v['x'], v['y'])]
def segd(t, p):
    # exact distance segment to rect
    best = 9e9
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.02))
    for k in range(n + 1):
        x = t['x1'] + (t['x2'] - t['x1']) * k / n; y = t['y1'] + (t['y2'] - t['y1']) * k / n
        best = min(best, math.hypot(max(abs(x - p['x']) - p['w'] / 2, 0), max(abs(y - p['y']) - p['h'] / 2, 0)))
    return best - t['w'] / 2
def ok(x, y, rot):
    worst = 9
    for p in PC.pads_of('C167', side, x, y, rot, nets):
        for q in pads:
            if abs(q['x'] - p['x']) > 2.5 or abs(q['y'] - p['y']) > 3.5: continue
            lim = 0.1 if q['net'] == p['net'] and q['net'] else 0.2
            worst = min(worst, PC.rect_gap(p, q) - lim)
            if worst < 0: return worst
        for t in trs:
            if t['net'] == p['net']: continue
            if max(t['x1'], t['x2']) < p['x'] - 1.5 or min(t['x1'], t['x2']) > p['x'] + 1.5 or max(t['y1'], t['y2']) < p['y'] - 1.5 or min(t['y1'], t['y2']) > p['y'] + 1.5: continue
            worst = min(worst, segd(t, p) - 0.1)
            if worst < 0: return worst
        for v in vis:
            if v['net'] == p['net'] or abs(v['x'] - p['x']) > 1.5 or abs(v['y'] - p['y']) > 1.5: continue
            worst = min(worst, math.hypot(max(abs(v['x'] - p['x']) - p['w'] / 2, 0), max(abs(v['y'] - p['y']) - p['h'] / 2, 0)) - v['size'] / 2 - 0.1)
            if worst < 0: return worst
    return worst
x = X0
while x <= X1:
    y = Y0
    while y <= Y1:
        for rot in (0, 90):
            w = ok(x, y, rot)
            if w >= 0: print(round(x, 3), round(y, 3), rot, round(w, 3), flush=True)
        y += ST
    x += ST
