import sys, numpy as np
from scipy import ndimage
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import reach, plot_layer, base
E, pads, tracks, vias, objs = reach.objs_applied()
box = (32.5, 15.6, 41.5, 21.8)
cases = [('D14', 'Bottom', (36.35, 18.05), 0.10), ('D13', 'Bottom', (35.5501, 18.05), 0.10), ('D15', 'Bottom', (37.9499, 18.05), 0.10),
         ('D14', 'Top', (36.125, 16.65), 0.0762), ('D13', 'Top', (35.625, 16.65), 0.0762), ('D15', 'Top', (38.35, 16.725), 0.0762)]
fig, axs = plt.subplots(3, 2, figsize=(22, 24))
for ax, (net, L, seed, W) in zip(axs.flat, cases):
    m, xs, ys = reach.forbid(objs, L, {net}, W, box)
    lab, n = ndimage.label(~m)
    i, j = int((seed[0] - box[0]) / 0.01), int((seed[1] - box[1]) / 0.01)
    reg = lab == lab[j, i]
    area = reg.sum() * 1e-4
    yy, xx = np.nonzero(reg)
    print(net, L, 'reachable area %.3f mm2, bbox x %.2f-%.2f y %.2f-%.2f' % (area, xs[xx.min()], xs[xx.max()], ys[yy.min()], ys[yy.max()]))
    ax.imshow(reg, origin='lower', extent=(box[0], box[2], box[1], box[3]), cmap='Greens', alpha=.5)
    plot_layer.draw(ax, L, pads, tracks, vias, (box[0], box[2], box[1], box[3]))
    ax.set_title('%s %s reachable track centre (w %.3f)' % (net, L, W))
plt.tight_layout(); plt.savefig('reach_base.png', dpi=80)
