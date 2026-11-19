"""Render a router model (+ optional plan) around the LED pocket on the four signal layers.

    python tools/led_spread_render.py <model.json> [plan.json|-] <out.png> [x0 y0 x1 y1]
"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
out = sys.argv[3]
X0, Y0, X1, Y1 = [float(v) for v in sys.argv[4:8]] if len(sys.argv) > 7 else (17.0, 6.5, 27.0, 19.5)
fig, axs = plt.subplots(2, 2, figsize=(16, 18))
scale = 72 * 16 / 2 * 0.8 / (X1 - X0)          # points per mm, roughly


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


for ax, L in zip(axs.flat, ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']):
    ax.set_title(L)
    ax.set_xlim(X0, X1)
    ax.set_ylim(Y0, Y1)
    ax.set_aspect('equal')
    ax.grid(True, lw=.3)
    for p in M['pads']:
        if L in (p['layers'] or STACK):
            hl = p['ref'] in ('LD0', 'LD1', 'LD2', 'LD3', 'LD4', 'LD5')
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'],
                                   color='b' if hl else 'r', alpha=.45))
            if X0 < p['x'] < X1 and Y0 < p['y'] < Y1 and L in ('Top Layer', 'Bottom Layer'):
                ax.text(p['x'], p['y'], '%s.%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=4.5, ha='center',
                        va='center')
    for src, col, a in ((M, 'orange', .55), (P, 'k', .9)):
        for t in src['tracks']:
            if t['layer'] == L:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], lw=max(.5, t['w'] * scale), color=col, alpha=a,
                        solid_capstyle='round')
        for v in src['vias']:
            sp = span(v)
            if L in sp:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color=('g' if len(sp) == 6 else 'm') if src is M
                                    else 'c', alpha=.6))
                if src is P and X0 < v['x'] < X1 and Y0 < v['y'] < Y1:
                    ax.text(v['x'], v['y'], v['net'][:8], fontsize=4.5)
plt.tight_layout()
plt.savefig(out, dpi=100)
