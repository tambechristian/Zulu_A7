"""plot2.py <model.json> <plan.json|-> <x0,y0,x1,y1> <out.png> [layer ...]: like plot.py, every item labelled by net,
only items inside the box; plan items bold."""
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
SP = lambda v: v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
B = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {}
x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
lays = sys.argv[5:] or ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
key = lambda t: (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))
vk = lambda v: (v['net'], round(v['x'], 4), round(v['y'], 4), SP(v)[0], SP(v)[-1])
rem = set(map(key, P.get('remove', []))); rv = set(map(vk, P.get('remove_vias', [])))
T = [(t, 0) for t in B['tracks'] if key(t) not in rem] + [(t, 1) for t in P.get('tracks', [])]
V = [(v, 0) for v in B['vias'] if vk(v) not in rv] + [(v, 1) for v in P.get('vias', [])]
pal = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#7f7f7f']
col = lambda n: '#2ca02c' if n == 'GND' else '#ff7f0e' if n == 'VCC3V3' else pal[sum(map(ord, n or 'x')) % len(pal)]
inb = lambda x, y, m=0: x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m
W = 22
fig, axs = plt.subplots(len(lays), 1, figsize=(W, W * (y1 - y0) / (x1 - x0) * len(lays) * 1.1))
axs = [axs] if len(lays) == 1 else axs
sc = W * 72 / (x1 - x0)
for ax, lay in zip(axs, lays):
    for p in B['pads']:
        if lay not in (p['layers'] or []) and not p['drill']: continue
        if not inb(p['x'], p['y'], 0.5): continue
        c = col(p['net'])
        if p['shape'] in ('circle', 'round') or p['ref'] == 'U1':
            ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, color=c, alpha=.3))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=c, alpha=.3))
        ax.text(p['x'], p['y'], '%s.%s %s' % (p['ref'], p['pad'], p['net']), fontsize=5, ha='center', va='center')
    for t, new in T:
        if t['layer'] != lay: continue
        mx, my = (t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2
        if not (inb(t['x1'], t['y1']) or inb(t['x2'], t['y2']) or inb(mx, my)): continue
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col(t['net']), lw=max(.4, t['w'] * sc), alpha=.9 if new else .5, solid_capstyle='round')
        if ((t['x2'] - t['x1']) ** 2 + (t['y2'] - t['y1']) ** 2) > 0.09 and inb(mx, my):
            ax.text(mx, my, t['net'], fontsize=5, color='k')
    for v, new in V:
        if lay not in SP(v) or not inb(v['x'], v['y']): continue
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, color=col(v['net']), lw=1.5 if new else .8))
        ax.text(v['x'], v['y'] + 0.12, v['net'] + ('*' if v['size'] > 0.34 else ''), fontsize=4)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect('equal'); ax.grid(lw=.2)
    ax.set_xticks([x0 + i * 0.5 for i in range(int((x1 - x0) / 0.5) + 1)]); ax.tick_params(labelsize=5)
    ax.set_title(lay, fontsize=8)
plt.savefig(sys.argv[4], dpi=110, bbox_inches='tight')
