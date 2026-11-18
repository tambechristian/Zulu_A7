import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
M = json.load(open(sys.argv[1]))
x0, y0, x1, y1 = map(float, sys.argv[2].split(','))
layers = sys.argv[3].split(',')
out = sys.argv[4]
col = {'Top Layer': 'red', 'L3-SIG': 'orange', 'L4-SIG': 'cyan', 'Bottom Layer': 'blue'}
fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0)))
for t in M['tracks']:
    if t['layer'] not in layers: continue
    if max(t['x1'], t['x2']) < x0 or min(t['x1'], t['x2']) > x1 or max(t['y1'], t['y2']) < y0 or min(t['y1'], t['y2']) > y1: continue
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[t['layer']], lw=max(0.5, t['w'] * 72 * 16 / (x1 - x0) / 25.4), alpha=0.6, solid_capstyle='round')
    mx, my = (t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2
    if t['net'] not in ('GND',) and abs(t['x1'] - t['x2']) + abs(t['y1'] - t['y2']) > 0.6:
        ax.text(mx, my, t['net'], fontsize=6, color='k')
for p in M['pads']:
    if not (x0 <= p['x'] <= x1 and y0 <= p['y'] <= y1): continue
    on = [l for l in p['layers'] if l in layers] or (['Top Layer'] if p.get('drill') else [])
    if not on and p['layers']: continue
    c = 'darkred' if 'Top Layer' in p['layers'] else 'navy'
    ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fill=False, ec=c, lw=1))
    ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net'][:10]), fontsize=5, ha='center', va='center', color=c)
for v in M['vias']:
    if not (x0 <= v['x'] <= x1 and y0 <= v['y'] <= y1): continue
    if not set(v['span']) & set(layers): continue
    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, ec='green', lw=1))
    ax.text(v['x'], v['y'] + 0.2, v['net'][:8], fontsize=5, color='green', ha='center')
for poly in json.loads(sys.argv[5]) if len(sys.argv) > 5 else []:
    xs = [q[0] for q in poly] + [poly[0][0]]; ys = [q[1] for q in poly] + [poly[0][1]]
    ax.plot(xs, ys, 'm--', lw=1.5)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(True, lw=0.3)
ax.set_xticks([x0 + k * 0.5 for k in range(int((x1 - x0) / 0.5) + 1)]); ax.tick_params(labelsize=6)
plt.savefig(out, dpi=110, bbox_inches='tight')
