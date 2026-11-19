"""show_net.py FILE NET[,NET...] [xmin] -- print pads, tracks, vias of nets with x >= xmin."""
import json
import sys

fn = sys.argv[1]
nets = sys.argv[2].split(',')
x0 = float(sys.argv[3]) if len(sys.argv) > 3 else -1e9
p = json.load(open(fn))
print('==', fn)
for n in nets:
    print(' --', n)
    for q in p.get('pads', []):
        if q['net'] == n:
            print('  P', q['ref'], q['pad'], q['x'], q['y'])
    for t in p['tracks']:
        if t['net'] == n and max(t['x1'], t['x2']) >= x0:
            print('  T', t['layer'][:6], t['w'], t['x1'], t['y1'], t['x2'], t['y2'])
    for v in p['vias']:
        if v['net'] == n and v['x'] >= x0:
            sp = v.get('span') or [v.get('from'), v.get('to')]
            print('  V', sp, v['x'], v['y'], v['size'], v['hole'])
