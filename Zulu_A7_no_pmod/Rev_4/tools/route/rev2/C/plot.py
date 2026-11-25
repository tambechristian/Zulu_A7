"""python plot.py <base> <plan or -> <x0,y0,x1,y1> <out.png> [layer]  -- draw copper of one layer (default Top)"""
import json, sys, math
SP = lambda v: v['span'] if 'span' in v else [v['from'], v['to']]
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
B = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {}
x0, y0, x1, y1 = map(float, sys.argv[3].split(',')); lay = sys.argv[5] if len(sys.argv) > 5 else 'Top Layer'
key = lambda t: (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))
vk = lambda v: (v['net'], round(v['x'], 4), round(v['y'], 4), tuple(SP(v)))
rem = set(map(key, P.get('remove', []))); rv = set(map(vk, P.get('remove_vias', [])))
T = [(t, 0) for t in B['tracks'] if key(t) not in rem] + [(t, 1) for t in P.get('tracks', [])]
V = [(v, 0) for v in B['vias'] if vk(v) not in rv] + [(v, 1) for v in P.get('vias', [])]
fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0)))
nets = {}
col = lambda n: 'red' if n.startswith('USB_D') else ('green' if n == 'GND' else ('orange' if n == 'VCC3V3' else 'C%d' % (hash(n) % 10)))
for p in B['pads']:
    if lay not in p['layers'] and not p['drill']: continue
    if not (x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2): continue
    if p['shape'] in ('circle', 'round') : ax.add_patch(Circle((p['x'], p['y']), p['w'] / 2, color=col(p['net'] or 'x'), alpha=.4))
    else: ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=col(p['net'] or 'x'), alpha=.4))
    ax.text(p['x'], p['y'], '%s.%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=5, ha='center')
for t, new in T:
    if t['layer'] != lay: continue
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col(t['net']), lw=t['w'] * 72 * 16 / (x1 - x0) / 25.4 * 25.4 / 1, alpha=.9 if new else .5, solid_capstyle='round', ls='-' )
    if new: ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2, t['net'], fontsize=4)
for v, new in V:
    i, j = STACK.index(SP(v)[0]), STACK.index(SP(v)[-1])
    if lay not in STACK[i:j + 1]: continue
    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, color=col(v['net']), lw=1.5 if new else .7))
ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect('equal'); ax.grid(lw=.2); ax.set_title(lay)
plt.savefig(sys.argv[4], dpi=110, bbox_inches='tight')
