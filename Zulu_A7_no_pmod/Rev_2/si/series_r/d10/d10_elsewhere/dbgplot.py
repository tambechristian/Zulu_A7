import numpy as np, json, maze as M
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
s = json.load(open('maze_candidates.json'))['sites']
for mode in 'AB':
    z = np.load('dbg_%s.npz' % mode)
    fig, axes = plt.subplots(2, 4, figsize=(28, 13))
    for r, key in enumerate(('dU', 'dS')):
        d = z[key]
        for k in range(4):
            ax = axes[r, k]
            ax.imshow(np.isfinite(d[k]), origin='lower', extent=[M.X0, M.X1, M.Y0, M.Y1], cmap='Greens')
            for x in s:
                if x['side'] == M.RL[k]:
                    ax.plot(x['x'], x['y'], 'r.', ms=1)
            ax.set_title('%s %s %s' % (mode, key, M.RL[k])); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig('dbg_%s.png' % mode, dpi=70)
