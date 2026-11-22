"""scan via sites around a pad: python scan_via.py model.json NET X Y kind [rmin rmax]"""
import json
import math
import sys
sys.path.insert(0, '.')
import geo

KIND = {'through': (0.35, 0.20, geo.STACK),
        'uvia_bot': (0.30, 0.15, geo.STACK[4:6]),
        'stack_bot': (0.30, 0.15, geo.STACK[3:6]),
        'gnd_stack': (0.30, 0.15, geo.STACK[1:6])}
M = json.load(open(sys.argv[1]))
net, px, py, kind = sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
W = 3.5
M['pads'] = [p for p in M['pads'] if abs(p['x'] - px) < W + 3 and abs(p['y'] - py) < W + 3]
M['vias'] = [v for v in M['vias'] if abs(v['x'] - px) < W and abs(v['y'] - py) < W]
M['tracks'] = [t for t in M['tracks'] if min(t['x1'], t['x2']) < px + W and max(t['x1'], t['x2']) > px - W and min(t['y1'], t['y2']) < py + W and max(t['y1'], t['y2']) > py - W]
rmin = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
rmax = float(sys.argv[7]) if len(sys.argv) > 7 else 1.6
size, hole, span = KIND[kind]
res = []
for ix in range(-32, 33):
    for iy in range(-32, 33):
        x, y = round(px + ix * 0.025, 4), round(py + iy * 0.025, 4)
        d = math.hypot(x - px, y - py)
        if d < rmin or d > rmax:
            continue
        r = geo.via_report(M, net, x, y, size, hole, span, 1)
        g = r[0][0] if r else 9
        if g >= 0.09 + 0.01:
            res.append((round(d, 3), round(g, 4), x, y, r[0][1:] if r else None))
res.sort()
for r in res[:int(__import__("os").environ.get("NSHOW", "15"))]:
    print(r)
print(len(res), 'sites')
