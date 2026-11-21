"""figure of the final D13-D15 delta: board copper (grey, per layer colour), removed copper (dashed black), added copper
(bold), new parts and microvias.  -> final_plan.png"""
import json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import lib
B = lib.C.B
rep = json.load(open(os.path.join(lib.HERE, 'delta_report.json')))
COL = {'Top': '#c0392b', 'L2-GND': '#7f8c8d', 'L3-SIG': '#27ae60', 'L4-SIG': '#2471a3', 'L5-VCC3V3': '#8e44ad', 'Bottom': '#d68910'}
X0, X1, Y0, Y1 = 34.5, 49.5, 14.8, 18.9
fig, ax = plt.subplots(figsize=(15, 5.2))
for t in B['tracks']:
    if t['layer'] in COL and max(t['x1'], t['x2']) > X0 and min(t['x1'], t['x2']) < X1 and max(t['y1'], t['y2']) > Y0 and min(t['y1'], t['y2']) < Y1 and t['layer'] not in ('L2-GND', 'L5-VCC3V3'):
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=COL[t['layer']], lw=max(0.5, t['w'] * 20), alpha=0.18, solid_capstyle='round')
for p in B['pads']:
    if X0 < p['x'] < X1 and Y0 < p['y'] < Y1:
        ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color='0.6', alpha=0.35, lw=0))
for v in B['vias']:
    if X0 < v['x'] < X1 and Y0 < v['y'] < Y1:
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color='0.5', alpha=0.3, lw=0))
LN = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom'}
for t in rep['remove']:
    if t.get('why') == 'rename':
        continue
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=1.0, ls='--')
for t in rep['tracks']:
    L = LN.get(t['layer'], t['layer'])
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=COL[L], lw=2.2 if t.get('why') != 'rename' else 1.0, solid_capstyle='round')
for v in rep['microvias']:
    ax.add_patch(Circle((v['x'], v['y']), 0.15, fill=False, ec='k', lw=1.4))
for pr in rep['parts']:
    for k in ('pad1', 'pad2'):
        ax.add_patch(Rectangle((pr[k]['x'] - 0.15, pr[k]['y'] - 0.15), 0.3, 0.3, fill=False, ec=COL[pr['side']], lw=2))
    ax.annotate('%s %s %s\n(%.4f, %.4f) r%d' % (pr['ref'], pr['pad2']['net'], pr['side'], pr['x'], pr['y'], pr['rot']), (pr['x'], pr['y']),
                xytext=(0, 22 if pr['side'] == 'Top' else -30), textcoords='offset points', ha='center', fontsize=8,
                arrowprops=dict(arrowstyle='-', lw=0.6))
ax.annotate('gnd47 unlock: U2-47 GND\nTop>L2 microvia', (38.22, 17.16), xytext=(-10, 30), textcoords='offset points', fontsize=7, ha='right',
            arrowprops=dict(arrowstyle='-', lw=0.6))
for L, c in COL.items():
    if L not in ('L2-GND', 'L5-VCC3V3'):
        ax.plot([], [], color=c, lw=2.2, label=L)
ax.plot([], [], color='k', ls='--', label='removed')
ax.legend(loc='lower left', fontsize=7, ncol=5)
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.grid(alpha=0.2)
ax.set_title('final_plan.json: 13-R plan + R132 (D13, Top) + R133 (D14, Bottom) + R134 (D15, Bottom) + gnd47  (md5 %s)' % lib.md5(os.path.join(lib.D13, 'final_plan.json'))[:8], fontsize=9)
fig.tight_layout(); fig.savefig(os.path.join(lib.HERE, 'final_plan.png'), dpi=130)
