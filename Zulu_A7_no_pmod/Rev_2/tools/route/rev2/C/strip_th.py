"""python strip_th.py <model> <plan> <out_seed>: drop router-plan through vias whose land overlaps any SMD pad, and the
plan tracks ending on them (the router re-routes those connections)."""
import json, math, sys
M = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
smd = [p for p in M['pads'] if not p['drill']]
def hit(v):
    for p in smd:
        if p['shape'] in ('circle', 'round') and abs(p['w'] - p['h']) < 1e-6:
            if math.hypot(v['x'] - p['x'], v['y'] - p['y']) < v['size'] / 2 + p['w'] / 2: return p
        elif math.hypot(max(abs(v['x'] - p['x']) - p['w'] / 2, 0), max(abs(v['y'] - p['y']) - p['h'] / 2, 0)) < v['size'] / 2: return p
bad = [v for v in P['vias'] if v.get('from') == 'Top Layer' and v.get('to') == 'Bottom Layer' and hit(v)]
on = lambda t, v: any(math.hypot(e[0] - v['x'], e[1] - v['y']) < 1e-3 for e in ((t['x1'], t['y1']), (t['x2'], t['y2'])))
bt = [t for t in P['tracks'] if any(t['net'] == v['net'] and on(t, v) for v in bad)]
S = {'tracks': [t for t in P['tracks'] if t not in bt], 'vias': [v for v in P['vias'] if v not in bad]}
json.dump(S, open(sys.argv[3], 'w'))
print('dropped %d through vias, %d tracks' % (len(bad), len(bt)), [(v['net'], v['x'], v['y'], hit(v)['ref'] + '.' + hit(v)['pad']) for v in bad])
