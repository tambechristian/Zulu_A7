import sys, os, numpy as np
ARGV = list(sys.argv)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freemap as F
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
objs, recs = F.plan_objs()
x0, x1, y0, y1 = [float(v) for v in ARGV[1:5]]
out = ARGV[5]
fig, axes = plt.subplots(2, 2, figsize=(22, 18))
for ax, L in zip(axes.flat, ['Top', 'L3-SIG', 'L4-SIG', 'Bottom']):
    tr = {'Top': 0.0381, 'L3-SIG': 0.0625, 'L4-SIG': 0.0625, 'Bottom': 0.05}[L]
    bt = F.blocked(objs, L, tr)
    bl = F.blocked(objs, L, 0.15)
    img = np.zeros((F.NY, F.NX, 3))
    img[~bt] = [0.55, 0.55, 0.9]      # track centre ok
    img[~bl] = [0.4, 0.9, 0.4]        # 0.30 land centre ok
    ax.imshow(img, origin='lower', extent=[F.X0, F.X1, F.Y0, F.Y1], interpolation='nearest')
    for o in objs:
        if o.layer != L or not (x0 - 1 < o.shape[1] < x1 + 1 and y0 - 1 < o.shape[2] < y1 + 1):
            continue
        S = o.shape
        c = 'red' if o.net in F.FAM else 'k'
        if S[0] == 'C':
            if S[1] == S[3] and S[2] == S[4]:
                ax.add_patch(plt.Circle((S[1], S[2]), S[5], fc='none', ec=c, lw=.7))
            else:
                ax.plot([S[1], S[3]], [S[2], S[4]], color=c, lw=.7)
        else:
            ax.add_patch(plt.Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], fc='none', ec=c, lw=.7))
        if o.kind != 'track' or True:
            ax.text((S[1] + (S[3] if S[0] == 'C' else S[1])) / 2, (S[2] + (S[4] if S[0] == 'C' else S[2])) / 2, (o.net or '')[:9], fontsize=5, clip_on=True)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(L + '  blue: 0.10/0.125/0.0762 track centre ok; green: 0.30 land centre ok (D10 family not an obstacle)')
    ax.set_xticks(np.arange(x0, x1 + 1e-6, 0.25)); ax.set_yticks(np.arange(y0, y1 + 1e-6, 0.25)); ax.tick_params(labelsize=6, rotation=90); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig(out, dpi=100)
