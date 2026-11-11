"""python rip_model.py <model in> <model out> x0 y0 x1 y1 -- drop power-block copper (tracks with an end in the box,
vias in the box) on the power nets, PWR_* nets, the U7 LX net and no-net copper, as the 2026-11-10 rip did."""
import json, sys
from collections import Counter
M = json.load(open(sys.argv[1])); out = sys.argv[2]; B = [float(v) for v in sys.argv[3:7]]
nets = {t['net'] for t in M['tracks']} | {v['net'] for v in M['vias']} | {p['net'] for p in M['pads']}
P = {'VU', 'USB5V0', 'VBATT', 'EN', 'VCC1V0', 'VCC1V8', 'VCC3V3', 'GND', 'LD4_A', '', 'NetL3_1'} | {n for n in nets if n.startswith('PWR_')}
inb = lambda x, y: B[0] <= x <= B[2] and B[1] <= y <= B[3]
rt = [t for t in M['tracks'] if t['net'] in P and (inb(t['x1'], t['y1']) or inb(t['x2'], t['y2']))]
rv = [v for v in M['vias'] if v['net'] in P and inb(v['x'], v['y'])]
M['tracks'] = [t for t in M['tracks'] if t not in rt]
M['vias'] = [v for v in M['vias'] if v not in rv]
json.dump(M, open(out, 'w'))
print('ripped tracks', len(rt), Counter(t['net'] for t in rt).most_common(8), 'vias', len(rv))
