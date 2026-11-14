import sys, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import base
C = base.C
E, pads, tracks, vias, nf = base.applied()
X0, X1, Y0, Y1 = [float(v) for v in sys.argv[1:5]] if len(sys.argv) > 4 else (31.5, 42, 15.0, 22.5)
out = sys.argv[5] if len(sys.argv) > 5 else 'region_layers.png'
layers = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
fig, axs = plt.subplots(3, 2, figsize=(22, 24))
HL = {'D13', 'D14', 'D15'}
for ax, L in zip(axs.flat, layers):
    ax.set_title(L); ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.grid(alpha=.3)
    for p in pads:
        lay = C.CU if p['layer'] == 'Multi' else [p['layer']]
        if L not in lay: continue
        if not (X0-2 < p['x'] < X1+2 and Y0-2 < p['y'] < Y1+2): continue
        col = 'red' if p['net'] in HL else ('gold' if (p['ref'].startswith('R') and p['ref'][1:].isdigit() and int(p['ref'][1:]) >= 119) else 'grey')
        S = C.pad_shape(p, L)
        if S[0] == 'R':
            ax.add_patch(Rectangle((S[1]-S[3], S[2]-S[4]), 2*S[3], 2*S[4], fc=col, alpha=.5, ec='k', lw=.5))
        else:
            ax.add_patch(Circle((S[1], S[2]), S[5], fc=col, alpha=.5))
        ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=5, ha='center', va='center')
    for t in tracks:
        if t is None or t['layer'] != L: continue
        if max(t['x1'], t['x2']) < X0-1 or min(t['x1'], t['x2']) > X1+1 or max(t['y1'], t['y2']) < Y0-1 or min(t['y1'], t['y2']) > Y1+1: continue
        col = 'red' if t['net'] in HL else ('blue' if t['net'] and t['net'].startswith('SDRAM') else 'k')
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col, lw=max(.5, t['w']*72/ ((X1-X0)/22*1.0) * 0.9), alpha=.45, solid_capstyle='round')
        mx, my = (t['x1']+t['x2'])/2, (t['y1']+t['y2'])/2
        if X0 < mx < X1 and Y0 < my < Y1:
            ax.text(mx, my, '%s %.3g' % (t['net'], t['w']), fontsize=4, color='darkgreen')
    for v in vias:
        if v is None or L not in v['span']: continue
        if not (X0-1 < v['x'] < X1+1 and Y0-1 < v['y'] < Y1+1): continue
        col = 'red' if v['net'] in HL else 'c'
        ax.add_patch(Circle((v['x'], v['y']), v['size']/2, fc=col, alpha=.5, ec='k', lw=.3))
        ax.text(v['x'], v['y'], '%s\n%s>%s' % (v['net'], v['span'][0][:3], v['span'][-1][:3]), fontsize=4, ha='center')
plt.tight_layout(); plt.savefig(out, dpi=110)
