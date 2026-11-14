import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freemap as F
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
objs, recs = F.plan_objs()
res = {}
holes = [(o.xy, o.hole, set(o.span)) for o in objs if o.kind == 'via' and o.layer == o.span[0] and o.net not in F.FAM]
holes += [((p['x'], p['y']), p['hole'], set(F.D.CU)) for p in recs[0] if p.get('hole', 0) > 0]
Xg, Yg = np.meshgrid(F.XS, F.YS)
for name, r, hole in (('through', 0.175, 0.2), ('stack', 0.15, 0.15)):
    free = np.ones((F.NY, F.NX), bool)
    per = {}
    for L in F.D.CU:
        b = F.blocked(objs, L, r)
        per[L] = ~b
        free &= ~b
    hh = np.zeros_like(free)
    for (x, y), h, sp in holes:
        hh |= np.hypot(Xg - x, Yg - y) < 0.24 + h / 2 + hole / 2
    free &= ~hh
    res[name] = (free, per)
    print(name, 'free cells', free.sum())
    # list connected blobs
    from scipy import ndimage
    lab, n = ndimage.label(free)
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        ys, xs = np.nonzero(lab == k)
        print('  blob %d: %d cells, x %.2f..%.2f y %.2f..%.2f' % (k, len(xs), F.XS[xs.min()], F.XS[xs.max()], F.YS[ys.min()], F.YS[ys.max()]))
np.savez_compressed(os.path.join(F.HERE, 'v2_free.npz'), through=res['through'][0], stack=res['stack'][0])
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
for ax, name in zip(axes, res):
    free, per = res[name]
    img = np.zeros((F.NY, F.NX, 3))
    for k, L in enumerate(['Top', 'L3-SIG', 'L4-SIG']):
        img[..., k] = per[L] * 0.5
    img[free] = [1, 1, 0]
    ax.imshow(img, origin='lower', extent=[F.X0, F.X1, F.Y0, F.Y1])
    ax.set_title(name + ' via centre free (yellow=all layers; R=Top free,G=L3 free,B=L4 free)')
    ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(os.path.join(F.HERE, 'scan_v2.png'), dpi=90)
