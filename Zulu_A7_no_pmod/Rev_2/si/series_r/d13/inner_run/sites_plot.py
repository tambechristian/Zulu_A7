import sys, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import lib
from lib import C, B
net, side = sys.argv[1], sys.argv[2]
X0, X1, Y0, Y1 = [float(v) for v in sys.argv[3:7]]
layers = sys.argv[7].split(',')
objs, *_ = lib.apply_plan(lib.BASE_PLAN)
pf = json.load(open('prefilter_%s.json' % net))
fig, ax = plt.subplots(figsize=(20, 20 * (Y1 - Y0) / (X1 - X0) + 1))
cols = {'Top': 'red', 'L3-SIG': 'orange', 'L4-SIG': 'purple', 'Bottom': 'blue', 'L2-GND': 'green', 'L5-VCC3V3': 'brown'}
for o in objs:
    if o.layer not in layers: continue
    S = o.shape; bb = C.bbox(S)
    if bb[2] < X0 - 1 or bb[0] > X1 + 1 or bb[3] < Y0 - 1 or bb[1] > Y1 + 1: continue
    col = cols[o.layer]; a = 0.9 if o.net in ('D13','D14','D15') else 0.25
    if o.kind == 'track':
        ax.plot([S[1], S[3]], [S[2], S[4]], color=col, lw=S[5] * 2 * 20 * 72 / (X1 - X0), solid_capstyle='round', alpha=a)
    elif S[0] == 'R':
        ax.add_patch(Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], color=col, alpha=a))
    else:
        if S[1] == S[3] and S[2] == S[4]: ax.add_patch(Circle((S[1], S[2]), S[5], color=col, alpha=a))
        else: ax.plot([S[1], S[3]], [S[2], S[4]], color=col, lw=S[5]*2*20*72/(X1-X0), alpha=a)
    if o.kind in ('via','pad') and X0 < S[1] < X1 and Y0 < S[2] < Y1:
        ax.text(S[1], S[2], (o.ref+'-'+o.pad+' ' if o.kind=='pad' else '') + (o.net or '')[:9], fontsize=5, ha='center', va='center')
for sd, x, y in pf['legal_sites']:
    if sd == side: ax.plot(x, y, '.', color='k', ms=2)
side_of = {c['ref']: c['side'] for c in B['components']}
for ref, v in B['component_outlines'].items():
    if side_of.get(ref) != side: continue
    for k in ('Mech3','Mech4','Mech8','pads','Mech7'):
        if k in v:
            b = v[k]
            if b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1: continue
            ax.add_patch(Rectangle((b[0], b[1]), b[2]-b[0], b[3]-b[1], fill=False, ec='k', lw=0.8, ls='--' if k!='Mech7' else ':'))
            ax.text(max(b[0],X0)+0.05, min(b[3],Y1)-0.15, ref+' '+k, fontsize=7, clip_on=True)
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.grid(True, lw=0.2)
ax.set_xticks([x * 0.25 for x in range(int(X0 * 4), int(X1 * 4) + 1)]); ax.tick_params(labelsize=6)
ax.set_title('%s legal %s column sites (black dots); layers %s' % (net, side, layers))
plt.tight_layout(); plt.savefig(sys.argv[8], dpi=150)
