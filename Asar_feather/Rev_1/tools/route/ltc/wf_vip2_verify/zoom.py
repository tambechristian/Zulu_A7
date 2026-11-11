import json, sys, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
M = json.load(open(sys.argv[1])); L = sys.argv[2]; x0, y0, x1, y1 = map(float, sys.argv[3:7]); out = sys.argv[7]
C = {'GND': '#777', 'VU': 'orange', 'USB5V0': 'magenta', 'VBATT': 'green', 'PWR_SW': 'blue', 'PWR_PROG': 'red', 'PWR_FB2': 'brown', 'VCC3V3': 'cyan'}
fig, ax = plt.subplots(figsize=(12, 12 * (y1 - y0) / (x1 - x0)))
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(L)
for p in M['pads']:
    if (L in p['layers'] or p['drill']) and x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2:
        ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=C.get(p['net'], '#4a8'), alpha=.35, ec='k', lw=.5))
        ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:8]), fontsize=6, ha='center', va='center')
for t in M['tracks']:
    if t['layer'] == L:
        lw = t['w'] * 72 * 12 / (x1 - x0) / 1.0
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=C.get(t['net'], '#4a8'), lw=lw, solid_capstyle='round', alpha=.75)
for v in M['vias']:
    if L in v['span'] and x0 - 1 < v['x'] < x1 + 1 and y0 - 1 < v['y'] < y1 + 1:
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc=C.get(v['net'], '#4a8'), ec='k', lw=.6))
        ax.add_patch(Circle((v['x'], v['y']), v['hole'] / 2, fc='white', ec='k', lw=.3))
ax.grid(True, lw=.2)
fig.savefig(out, dpi=90, bbox_inches='tight')
