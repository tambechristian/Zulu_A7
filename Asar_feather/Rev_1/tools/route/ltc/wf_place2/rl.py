"""rl.py <model> <plan|-> x0 y0 x1 y1 <png> LAYER[,LAYER..]  true-scale render of chosen layers (one panel each)"""
import json, sys, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

M = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
x0, y0, x1, y1 = map(float, sys.argv[3:7])
out = sys.argv[7]
LAY = sys.argv[8].split(',')
ST = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def same(t, r):
    return t['net'] == r['net'] and t['layer'] == r['layer'] and \
        {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == \
        {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))}


rm = P.get('remove', [])
tracks = [t for t in M['tracks'] if not any(same(t, r) for r in rm)]
rv = P.get('remove_vias', [])
vias = [v for v in M['vias'] if not any(v['net'] == r['net'] and abs(v['x'] - r['x']) < 2e-3 and abs(v['y'] - r['y']) < 2e-3 and abs(v['hole'] - r['hole']) < 2e-3 for r in rv)]


def span(v):
    if 'span' in v:
        return v['span']
    a, b = sorted((ST.index(v['from']), ST.index(v['to'])))
    return ST[a:b + 1]


COL = {'GND': '#999', 'VU': 'orange', 'USB5V0': 'magenta', 'VBATT': 'green', 'PWR_SW': 'blue', 'VCC3V3': '#c66'}
n = len(LAY)
import numpy as np
nc = 2 if n > 1 else 1
nr = (n + 1) // 2 if n > 1 else 1
fig, axs = plt.subplots(nr, nc, figsize=(9 * nc, 9 * nr * (y1 - y0) / (x1 - x0)))
axs = np.array(axs).flatten()
for ax, L in zip(axs, LAY):
    ax.set_title(L)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    ax.grid(True, lw=.2)
    for p in M['pads']:
        if L in p['layers']:
            if x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2:
                ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=COL.get(p['net'], '#4a8'), alpha=.45, ec='k', lw=.3))
                ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:9]), fontsize=5, ha='center', va='center')
    for src, new in ((tracks, False), (P['tracks'], True)):
        for t in src:
            if t['layer'] != L:
                continue
            dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
            d = math.hypot(dx, dy) or 1e-9
            nx, ny = -dy / d * t['w'] / 2, dx / d * t['w'] / 2
            c = COL.get(t['net'], '#4a8')
            ax.add_patch(Polygon([(t['x1'] + nx, t['y1'] + ny), (t['x2'] + nx, t['y2'] + ny), (t['x2'] - nx, t['y2'] - ny), (t['x1'] - nx, t['y1'] - ny)], fc=c, alpha=.8 if new else .5, ec='k' if new else 'none', lw=.4))
            for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
                ax.add_patch(Circle((x, y), t['w'] / 2, fc=c, alpha=.8 if new else .5, ec='none'))
            if not new and t['net'] not in COL and x0 < (t['x1'] + t['x2']) / 2 < x1 and y0 < (t['y1'] + t['y2']) / 2 < y1:
                ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2, t['net'][:10], fontsize=4, color='k')
    for src, new in ((vias, False), (P['vias'], True)):
        for v in src:
            if L in span(v) and x0 < v['x'] < x1 and y0 < v['y'] < y1:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc=COL.get(v['net'], '#4a8'), ec='r' if new else 'k', lw=1 if new else .4))
                ax.add_patch(Circle((v['x'], v['y']), v['hole'] / 2, fc='w', ec='k', lw=.3))
                ax.text(v['x'], v['y'] + v['size'] / 2, '%s %s-%s' % (v['net'][:8], span(v)[0][:2], span(v)[-1][:2]), fontsize=4)
plt.tight_layout()
plt.savefig(out, dpi=80)
