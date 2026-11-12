"""plot.py <model.json> <plan.json or -> <x0,y0,x1,y1> <out.png> [layer ...]: copper of the given layers (default all
four routing layers, one panel each); plan items drawn bold, plan removals dropped."""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
SP = lambda v: v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]  # noqa: E731
B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {}
x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
lays = sys.argv[5:] or ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
key = lambda t: (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))  # noqa: E731
vk = lambda v: (v['net'], round(v['x'], 4), round(v['y'], 4), SP(v)[0], SP(v)[-1])  # noqa: E731
rem = set(map(key, P.get('remove', [])))
rv = set(map(vk, P.get('remove_vias', [])))
T = [(t, 0) for t in B['tracks'] if key(t) not in rem] + [(t, 1) for t in P.get('tracks', [])]
V = [(v, 0) for v in B['vias'] if vk(v) not in rv] + [(v, 1) for v in P.get('vias', [])]
pal = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#7f7f7f']


def col(n):
    if n == 'GND':
        return '#2ca02c'
    if n == 'VCC3V3':
        return '#ff7f0e'
    if n.startswith('USB_D'):
        return 'red'
    return pal[sum(map(ord, n)) % len(pal)]


fig, axs = plt.subplots(len(lays), 1, figsize=(16, 16 * (y1 - y0) / (x1 - x0) * len(lays)))
axs = [axs] if len(lays) == 1 else axs
sc = 16 * 72 / (x1 - x0)                     # points per mm
for ax, lay in zip(axs, lays):
    for p in B['pads']:
        if lay not in (p['layers'] or []) and not p['drill']:
            continue
        if not (x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2):
            continue
        c = col(p['net'] or 'x')
        if p['shape'] in ('circle', 'round') or p['ref'] == 'U1':
            ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, color=c, alpha=.35))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=c, alpha=.35))
        if p['drill']:
            ax.add_patch(Circle((p['x'], p['y']), p['drill'] / 2, fill=False, color='k', lw=.5))
        ax.text(p['x'], p['y'], '%s.%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=4, ha='center', va='center')
    for t, new in T:
        if t['layer'] != lay or max(t['x1'], t['x2']) < x0 - 1 or min(t['x1'], t['x2']) > x1 + 1:
            continue
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col(t['net']), lw=max(.3, t['w'] * sc),
                alpha=.95 if new else .45, solid_capstyle='round')
        if new:
            ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2, t['net'], fontsize=4)
    for v, new in V:
        if lay not in SP(v) or not (x0 - 1 < v['x'] < x1 + 1):
            continue
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, color=col(v['net']), lw=1.4 if new else .6))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_aspect('equal')
    ax.grid(lw=.2)
    ax.set_title(lay, fontsize=8)
plt.savefig(sys.argv[4], dpi=120, bbox_inches='tight')
