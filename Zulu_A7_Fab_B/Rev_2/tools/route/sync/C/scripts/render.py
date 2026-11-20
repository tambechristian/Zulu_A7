"""render.py <model.json> <out.png> [x0 x1] [highlight nets comma]  - per-layer picture of a model window"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

M = json.load(open(sys.argv[1]))
out = sys.argv[2]
x0, x1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (46.0, 64.0)
hl = set(sys.argv[5].split(',')) if len(sys.argv) > 5 and sys.argv[5] else set()
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
LAY = ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
fig, axs = plt.subplots(4, 1, figsize=(16, 4 * 25.4 / (x1 - x0) * 16 / 4 * 1.0 + 2))
PW = {'GND': '#3a7', 'VCC3V3': '#c33', 'VCC1V0': '#c80', 'VCC1V8': '#a5c', 'VCCADC': '#888', 'GNDADC': '#888'}


def col(net):
    if net in hl:
        return '#00f'
    return PW.get(net, '#555')


for ax, L in zip(axs, LAY):
    ax.set_title(L)
    ax.set_xlim(x0, x1)
    ax.set_ylim(0, 25.4)
    ax.set_aspect('equal')
    for p in M['pads']:
        if not (x0 - 2 < p['x'] < x1 + 2):
            continue
        ls = p['layers'] or (STACK if p['drill'] else [])
        if L not in ls:
            continue
        if p['shape'] == 'circle' or p['ref'] == 'U1':
            ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, color=col(p['net']), alpha=0.5))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=col(p['net']), alpha=0.5))
    for t in M['tracks']:
        if t['layer'] != L or max(t['x1'], t['x2']) < x0 - 1 or min(t['x1'], t['x2']) > x1 + 1:
            continue
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col(t['net']), lw=max(0.3, t['w'] * 20), solid_capstyle='round')
    for v in M['vias']:
        sp = v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
        if L not in sp or not (x0 - 1 < v['x'] < x1 + 1):
            continue
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, color=col(v['net']), lw=0.6))
    ax.axvline(49.0, color='r', lw=0.5)
    ax.axvline(61.0, color='r', lw=0.5)
plt.tight_layout()
plt.savefig(out, dpi=110)
