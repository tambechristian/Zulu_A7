"""rb.py <model> <plan|-> x0 y0 x1 y1 out.png layer [hil nets comma]: one layer, labelled pads, big."""
import json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
M = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
x0, y0, x1, y1 = map(float, sys.argv[3:7]); out = sys.argv[7]; lay = sys.argv[8]
hil = sys.argv[9].split(',') if len(sys.argv) > 9 else []
cols = ['red', 'blue', 'orange', 'purple', 'brown', 'magenta']
def col(n):
    return cols[hil.index(n)] if n in hil else ('#777' if n == 'GND' else '#3a8')
rem = set(json.dumps(r, sort_keys=True) for r in P.get('remove', []))
fig, ax = plt.subplots(figsize=(14, 14 * (y1 - y0) / (x1 - x0)))
inb = lambda x, y: x0 - 1 < x < x1 + 1 and y0 - 1 < y < y1 + 1
for p in M['pads']:
    if not inb(p['x'], p['y']): continue
    if lay not in p['layers'] and not p.get('drill'): continue
    ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=col(p['net']), alpha=0.5))
    ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:8]), fontsize=6, ha='center', va='center')
for t in M['tracks'] + P['tracks']:
    if t['layer'] != lay or not (inb(t['x1'], t['y1']) or inb(t['x2'], t['y2'])): continue
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col(t['net']), lw=t['w'] * 72 * 14 / (x1 - x0) / 1.0, alpha=0.6, solid_capstyle='round')
for v in M['vias'] + P['vias']:
    sp = v.get('span') or S[S.index(v['from']):S.index(v['to']) + 1]
    if lay not in sp or not inb(v['x'], v['y']): continue
    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color=col(v['net']), alpha=0.8, ec='k'))
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_title(lay)
import numpy as np
ax.set_xticks(np.arange(round(x0), x1, 0.5)); ax.set_yticks(np.arange(round(y0), y1, 0.5)); ax.tick_params(labelsize=6)
plt.savefig(out, dpi=80, bbox_inches='tight')
