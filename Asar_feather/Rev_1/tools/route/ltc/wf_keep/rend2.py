"""rend2.py model plan|- x0 y0 x1 y1 out.png : per-layer, true widths, vias only on their span, net labels, y down."""
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
import numpy as np
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
x0, y0, x1, y1 = map(float, sys.argv[3:7])
out = sys.argv[7]
LAY = ['Bottom Layer', 'L3-SIG', 'L4-SIG', 'Top Layer']
COL = {'GND': '#888', 'VU': 'orange', 'USB5V0': 'magenta', 'VBATT': 'green', 'PWR_SW': 'blue'}
def col(n): return COL.get(n, '#4a8')
fig, axs = plt.subplots(2, 2, figsize=(18, 18 * (y1 - y0) / (x1 - x0) + 1))
axs = axs.flatten()
removed = set(P.get('remove', []))
def span(v):
    if 'span' in v: return v['span']
    return S[S.index(v['from']):S.index(v['to']) + 1]
for ax, L in zip(axs, LAY):
    ax.set_title(L)
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect('equal')
    ax.set_xticks(np.arange(np.ceil(x0 * 4) / 4, x1, 0.25), minor=True)
    ax.set_yticks(np.arange(np.ceil(y0 * 4) / 4, y1, 0.25), minor=True)
    ax.grid(which='both', lw=.2)
    for p in M['pads']:
        if L in p['layers'] or p['drill']:
            if x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2:
                ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=col(p['net']), alpha=.5, ec='k', lw=.3))
                ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:8]), fontsize=6, ha='center', va='center')
    for src, ls in ((M, 0), (P, 1)):
        for i, t in enumerate(src['tracks']):
            if t['layer'] != L: continue
            if src is M and i in removed: continue
            if not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0): continue
            dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']; ln = (dx * dx + dy * dy) ** .5 or 1
            nx, ny = -dy / ln * t['w'] / 2, dx / ln * t['w'] / 2
            ax.add_patch(Polygon([(t['x1'] + nx, t['y1'] + ny), (t['x2'] + nx, t['y2'] + ny), (t['x2'] - nx, t['y2'] - ny), (t['x1'] - nx, t['y1'] - ny)], fc=col(t['net']), alpha=.55 if ls == 0 else .9, ec='r' if ls else 'none', lw=.5))
            for (cx, cy) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
                ax.add_patch(Circle((cx, cy), t['w'] / 2, fc=col(t['net']), alpha=.55 if ls == 0 else .9, ec='none'))
            if ln > 0.3:
                ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2, t['net'][:10], fontsize=5, color='k')
        for v in src['vias']:
            if x0 < v['x'] < x1 and y0 < v['y'] < y1 and L in span(v):
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc=col(v['net']), ec='r' if ls else 'k', lw=.5))
                ax.add_patch(Circle((v['x'], v['y']), v['hole'] / 2, fc='w', ec='k', lw=.3))
plt.tight_layout()
plt.savefig(out, dpi=60)
