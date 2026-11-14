import sys, os, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
import lib
from lib import C, B

objs, pads, tracks, vias, E = lib.apply_plan(lib.BASE_PLAN)
X0, X1, Y0, Y1 = [float(v) for v in (sys.argv[1:5] if len(sys.argv) > 4 else (34, 50, 11.5, 19.5))]
out = sys.argv[5] if len(sys.argv) > 5 else 'explore.png'
layers = sys.argv[6].split(',') if len(sys.argv) > 6 else ['Top', 'L3-SIG', 'L4-SIG', 'Bottom']
HL = {'D13': 'red', 'SDRAM-D13': 'red', 'D14': 'blue', 'D15': 'green', 'SDRAM-D14': 'blue', 'SDRAM-D15': 'green'}
fig, axs = plt.subplots(len(layers), 1, figsize=(20, 20 * len(layers) * (Y1 - Y0) / (X1 - X0) + 1), squeeze=False); axs = axs[:, 0]
side_of = {c['ref']: c['side'] for c in B['components']}
for ax, L in zip(axs, layers):
    for o in objs:
        if o.layer != L:
            continue
        S = o.shape
        bb = C.bbox(S)
        if bb[2] < X0 - 1 or bb[0] > X1 + 1 or bb[3] < Y0 - 1 or bb[1] > Y1 + 1:
            continue
        col = HL.get(o.net, '0.6' if o.net not in ('GND', 'VCC3V3') else ('0.3' if o.net == 'GND' else 'orange'))
        if o.kind == 'track':
            ax.plot([S[1], S[3]], [S[2], S[4]], color=col, lw=max(0.5, S[5] * 2 * 20 * 72 / (X1 - X0)), solid_capstyle='round', alpha=0.6)
        elif S[0] == 'R':
            ax.add_patch(Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], color=col, alpha=0.5))
        else:
            if S[1] == S[3] and S[2] == S[4]:
                ax.add_patch(Circle((S[1], S[2]), S[5], color=col, alpha=0.5))
            else:
                ax.plot([S[1], S[3]], [S[2], S[4]], color=col, lw=6, alpha=0.5)
        if o.kind in ('via',) and (X0 < S[1] < X1 and Y0 < S[2] < Y1):
            ax.text(S[1], S[2], '%s\n%s' % ((o.net or '')[:10], ''.join(l[1] if l.startswith('L') else l[0] for l in o.span)), fontsize=4, ha='center', va='center')
        if o.kind == 'pad' and (X0 < S[1] < X1 and Y0 < S[2] < Y1):
            ax.text(S[1], S[2], '%s-%s\n%s' % (o.ref, o.pad, (o.net or '')[:8]), fontsize=4, ha='center', va='center')
    sd = 'Top' if L != 'Bottom' else 'Bottom'
    for ref, v in B['component_outlines'].items():
        if side_of.get(ref) != sd and not (L in ('L3-SIG', 'L4-SIG')):
            continue
        if L in ('L3-SIG', 'L4-SIG'):
            continue
        for k in ('Mech3', 'Mech4', 'pads'):
            if k in v:
                b = v[k]
                if b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1:
                    continue
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec='purple', lw=0.6, ls='--'))
                ax.text(max(b[0],X0), min(b[3],Y1), ref, fontsize=6, color='purple', clip_on=True)
                break
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.set_title(L)
    ax.grid(True, lw=0.2)
    ax.set_xticks([x * 0.5 for x in range(int(X0 * 2), int(X1 * 2) + 1)])
    ax.tick_params(labelsize=5)
plt.tight_layout()
plt.savefig(os.path.join(lib.HERE, out), dpi=170)
