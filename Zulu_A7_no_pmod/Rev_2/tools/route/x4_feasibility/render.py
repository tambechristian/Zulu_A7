"""render.py model.json out.png side x0 y0 x1 y1 [plan.json]"""
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import body_check as BC
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

mp, out, side = sys.argv[1], sys.argv[2], sys.argv[3]
X0, Y0, X1, Y1 = map(float, sys.argv[4:8])
P = json.load(open(sys.argv[8])) if len(sys.argv) > 8 else {'tracks': [], 'vias': []}
M = json.load(open(mp))
parts = BC.load(mp)[side]
L = 'Top Layer' if side == 'Top' else 'Bottom Layer'
inner = 'L3-SIG' if side == 'Top' else 'L4-SIG'
fig, axs = plt.subplots(1, 2, figsize=(22, 11 * (Y1 - Y0) / (X1 - X0) + 1))
for ax, lay in zip(axs, (L, inner)):
    ax.set_title(lay); ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.grid(True, lw=.3)
    for p in M['pads']:
        if lay in (p['layers'] or BC.STACK) and X0 - 3 < p['x'] < X1 + 3 and Y0 - 3 < p['y'] < Y1 + 3:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color='r', alpha=.4))
            if lay == L:
                ax.text(p['x'], p['y'], '%s.%s\n%s' % (p['ref'], p['pad'], p['net'][:10]), fontsize=6, ha='center', va='center')
    for src, col in ((M, 'orange'), (P, 'k')):
        for t in src['tracks']:
            if t['layer'] == lay:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], lw=max(.4, t['w'] * 40), color=col, alpha=.6, solid_capstyle='round')
        for v in src['vias']:
            sp = v.get('span') or BC.STACK[BC.STACK.index(v['from']):BC.STACK.index(v['to']) + 1]
            if lay in sp or (lay == L and (L in sp)):
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color='g' if len(sp) == 6 else 'm', alpha=.6))
            elif L in sp:
                pass
    if lay == L:
        for v in M['vias']:
            sp = v.get('span')
            if sp and L in sp and X0 < v['x'] < X1 and Y0 < v['y'] < Y1:
                ax.text(v['x'], v['y'] + .2, v['net'][:8], fontsize=6, color='g')
        for ref, d in parts.items():
            for b in d['body']:
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec='b', lw=1))
                if X0 < (b[0] + b[2]) / 2 < X1 and Y0 < (b[1] + b[3]) / 2 < Y1:
                    ax.text((b[0] + b[2]) / 2, b[3] - .25, ref, fontsize=7, color='b', ha='center')
plt.tight_layout(); plt.savefig(out, dpi=110)
