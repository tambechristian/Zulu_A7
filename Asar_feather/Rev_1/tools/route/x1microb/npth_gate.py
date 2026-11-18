import json, math, sys
sys.path.insert(0, "C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools")
import route_conn as C
M = json.load(open('model0.json')); P = json.load(open(sys.argv[1]))
holes = [p for p in M['pads'] if p['drill'] > 0 and not p['plated']]
best = []
for h in holes:
    for t in P['tracks']:
        best.append((C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], h['x'], h['y']) - h['drill'] / 2 - t['w'] / 2, t['net'], t['layer'], h['ref'], h['x'], h['y']))
    for v in P['vias']:
        best.append((math.hypot(v['x'] - h['x'], v['y'] - h['y']) - h['drill'] / 2 - v['size'] / 2, v['net'], 'via', h['ref'], h['x'], h['y']))
b = min(best)
print('NPTH min %.3f %s' % (b[0], b[1:]), 'PASS' if b[0] >= 0.127 else 'FAIL')
