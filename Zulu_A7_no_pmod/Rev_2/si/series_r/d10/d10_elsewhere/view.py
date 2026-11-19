"""Per-layer view of a window of the board (existing copper + the 12-R plan added), for site hunting."""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.abspath(os.path.join(HERE, '..', '..'))
B = json.load(open(os.path.join(SR, 'board_extract.json')))
P = json.load(open(os.path.join(SR, 'dq_series_r_plan.json')))
x0, x1, y0, y1 = [float(v) for v in sys.argv[1:5]]
out = sys.argv[5]
LAY = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
EM = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom'}
rm = {(EM.get(r['layer'], r['layer']), round(r['x1'], 3), round(r['y1'], 3), round(r['x2'], 3), round(r['y2'], 3)) for r in P['remove']}
rmv = {(round(v['x'], 3), round(v['y'], 3), v['span'][0]) for v in P['remove_vias']}
fig, axes = plt.subplots(3, 2, figsize=(22, 24))
HL = set(sys.argv[6].split(',')) if len(sys.argv) > 6 else {'D10'}
for ax, L in zip(axes.flat, LAY):
    for p in B['pads']:
        if not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1):
            continue
        if p['layer'] != 'Multi' and p['layer'] != L:
            continue
        c = 'red' if p['net'] in HL else '#999999'
        if p['shape'] == 'round':
            ax.add_patch(Circle((p['x'], p['y']), p['w'] / 2, fc=c, alpha=.5))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=c, alpha=.5))
        ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], (p['net'] or '')[:8]), fontsize=4.5, ha='center', va='center', clip_on=True)
    for t in B['tracks']:
        if t['layer'] != L:
            continue
        if not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0):
            continue
        k = (L, round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
        c = 'red' if t['net'] in HL else ('#3060c0' if t['net'] not in ('GND', 'VCC3V3') else '#40a040')
        ls = ':' if k in rm else '-'
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=c, lw=max(0.5, t['w'] * 40), alpha=0.5, ls=ls, solid_capstyle='round')
        mx, my = (t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2
        if x0 < mx < x1 and y0 < my < y1 and t['net'] not in ('GND', 'VCC3V3'):
            ax.text(mx, my, t['net'][:10], fontsize=4, color='k', clip_on=True)
    for v in B['vias']:
        if L not in v['span'] or not (x0 < v['x'] < x1 and y0 < v['y'] < y1):
            continue
        c = 'red' if v['net'] in HL else 'k'
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec=c, lw=0.8, ls=':' if (round(v['x'], 3), round(v['y'], 3), v['span'][0]) in rmv else '-'))
        ax.text(v['x'], v['y'] - 0.05, v['net'][:8], fontsize=3.5, ha='center', clip_on=True)
    for t in P['tracks']:
        if EM.get(t['layer'], t['layer']) != L or t.get('why'):
            continue
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='orange', lw=max(0.5, t['w'] * 40), alpha=0.8)
    for v in P['vias']:
        sp = LAY[LAY.index(EM.get(v['from'], v['from'])):LAY.index(EM.get(v['to'], v['to'])) + 1]
        if L in sp and not v.get('why'):
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='orange', ec='k', alpha=.6))
    for pr in P['parts']:
        if pr['side'] == L:
            for pd in (pr['pad1'], pr['pad2']):
                ax.add_patch(Rectangle((pd['x'] - .15, pd['y'] - .15), .3, .3, fc='yellow', ec='k'))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(L); ax.grid(alpha=.3)
    ax.set_xticks([x0 + 0.5 * i for i in range(int((x1 - x0) / 0.5) + 1)])
    ax.tick_params(labelsize=6)
fig.tight_layout()
fig.savefig(out, dpi=110)
