"""render one layer big: python rl.py model plan|- layer x0 y0 x1 y1 out.png [hl nets]"""
import json, sys, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

M = json.load(open(sys.argv[1]))
plan = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
layer = sys.argv[3]
x0, y0, x1, y1 = map(float, sys.argv[4:8])
out = sys.argv[8]
hl = sys.argv[9:]
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
rm = plan.get('remove', [])
def key(t):
    return (t['net'], t['layer'], frozenset({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}))
rk = {key(r) for r in rm}
tracks = [t for t in M['tracks'] if key(t) not in rk] + plan['tracks']
vias = M['vias'] + [dict(v, span=v.get('span') or STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]) for v in plan['vias']]
COL = {'PWR_SW': 'red', 'USB5V0': 'magenta', 'VBATT': 'green', 'VU': 'orange', 'GND': '0.6', 'VCC3V3': 'cyan'}
def col(n):
    if n in hl:
        return COL.get(n, 'blue')
    return '0.75' if n == 'GND' else '#9cc'
s = 1.6
fig, ax = plt.subplots(figsize=((x1 - x0) * s, (y1 - y0) * s))
ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_aspect('equal')
ax.set_title(layer)
for p in M['pads']:
    ls = p['layers'] or (STACK if p['drill'] > 0 else [])
    if layer not in ls or not (x0 - 3 < p['x'] < x1 + 3 and y0 - 3 < p['y'] < y1 + 3):
        continue
    ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=col(p['net']), alpha=0.8))
    ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:10]), fontsize=5, ha='center', va='center')
for t in tracks:
    if t['layer'] != layer:
        continue
    if not (x0 - 3 < t['x1'] < x1 + 3 and y0 - 3 < t['y1'] < y1 + 3):
        continue
    lw = t['w'] * 72 * s / 25.4 * 25.4 / 1  # approx points per mm
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col(t['net']), lw=t['w'] * s * 72 / 1.0 / 1.0 * 0.0 + max(0.5, t['w'] * s * 72 / 1), solid_capstyle='round', alpha=0.8)
    if t['w'] > 0.1 or t['net'] in hl:
        pass
for v in vias:
    if layer not in v['span'] or not (x0 - 1 < v['x'] < x1 + 1 and y0 - 1 < v['y'] < y1 + 1):
        continue
    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color=col(v['net']), ec='k', lw=0.3))
    ax.text(v['x'], v['y'], v['net'][:6] + ('' if len(v['span']) == 6 else '*'), fontsize=4, ha='center')
ax.grid(True, lw=0.2)
ax.set_xticks([x0 + 0.5 * i for i in range(int((x1 - x0) / 0.5) + 1)])
ax.set_yticks([y0 + 0.5 * i for i in range(int((y1 - y0) / 0.5) + 1)])
ax.tick_params(labelsize=5)
plt.savefig(out, dpi=110, bbox_inches='tight')
