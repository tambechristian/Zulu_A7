"""q.py <board.json> <plan.json|-> <layer> x0 x1 y0 y1 : copper on a layer inside a box (board with plan applied)"""
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as CP
B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
L = {'T': 'Top Layer', '3': 'L3-SIG', '4': 'L4-SIG', 'B': 'Bottom Layer', '2': 'L2-GND', '5': 'L5-VCC3V3'}.get(sys.argv[3], sys.argv[3])
x0, x1, y0, y1 = map(float, sys.argv[4:8])
M = CP.apply(B, P)
pk = {CP.tkey(t) for t in P['tracks']}
pv = {CP.vkey(v) for v in P['vias']}
for p in M['pads']:
    ls = p['layers'] if p['layers'] else (CP.STACK if p['drill'] else [])
    if L in ls and x0 - p['w'] / 2 <= p['x'] <= x1 + p['w'] / 2 and y0 - p['h'] / 2 <= p['y'] <= y1 + p['h'] / 2:
        print('PAD %-5s %-4s %-12s (%.4f,%.4f) %s %.3fx%.3f drill %.3f' % (p['ref'], p['pad'], p['net'], p['x'], p['y'], p['shape'], p['w'], p['h'], p['drill']))
for t in M['tracks']:
    if t['layer'] != L:
        continue
    if max(t['x1'], t['x2']) < x0 or min(t['x1'], t['x2']) > x1 or max(t['y1'], t['y2']) < y0 or min(t['y1'], t['y2']) > y1:
        continue
    print('TRK%s %-12s w%.4f (%.4f,%.4f)-(%.4f,%.4f)' % ('*' if CP.tkey(t) in pk else ' ', t['net'], t['w'], t['x1'], t['y1'], t['x2'], t['y2']))
for v in M['vias']:
    if L in v['span'] and x0 <= v['x'] <= x1 and y0 <= v['y'] <= y1:
        print('VIA%s %-12s (%.4f,%.4f) %.2f/%.2f %s' % ('*' if CP.vkey(v) in pv else ' ', v['net'], v['x'], v['y'], v['size'], v['hole'], '>'.join(s[:2] for s in v['span'])))
