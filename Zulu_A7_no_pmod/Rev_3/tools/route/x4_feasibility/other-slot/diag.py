import json, sys, numpy as np
from scipy import ndimage
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0, T)
import router as R
M = json.load(open(sys.argv[1]))
B = R.Board(M)
v = B.nid['VBATT']
for layer in ('Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer'):
    a = B.r[layer]
    free = (a == 0) | (a == v)
    # clearance for a 0.0762 track: erode free by (w/2+clear)/G cells
    k = int(np.ceil((0.0381 + 0.09) / R.G))
    st = np.zeros((2 * k + 1, 2 * k + 1), bool); yy, xx = np.mgrid[-k:k + 1, -k:k + 1]; st[xx * xx + yy * yy <= k * k] = True
    ok = ~ndimage.binary_dilation(~free, structure=st) | (a == v)
    lab, n = ndimage.label(ok)
    # connected component(s) containing VBATT cells
    ids = set(np.unique(lab[a == v])) - {0}
    for i in ids:
        cells = np.argwhere(lab == i)
        x0, y0 = cells[:, 1].min() * R.G, cells[:, 0].min() * R.G; x1, y1 = cells[:, 1].max() * R.G, cells[:, 0].max() * R.G
        print(layer, 'component', i, 'cells', len(cells), 'bbox x %.2f..%.2f y %.2f..%.2f' % (x0, x1, y0, y1))
print('--- components on each layer that overlap the connector-side Top region (x>=50.2, 3.5<=y<=16), size>2000 cells')
for layer in ('L3-SIG', 'L4-SIG', 'Bottom Layer'):
    a = B.r[layer]
    free = (a == 0) | (a == v)
    k = int(np.ceil((0.0381 + 0.09) / R.G))
    st = np.zeros((2 * k + 1, 2 * k + 1), bool); yy, xx = np.mgrid[-k:k + 1, -k:k + 1]; st[xx * xx + yy * yy <= k * k] = True
    ok = ~ndimage.binary_dilation(~free, structure=st) | (a == v)
    lab, n = ndimage.label(ok)
    sub = lab[int(3.5 / R.G):int(16 / R.G), int(50.2 / R.G):]
    for i in set(np.unique(sub)) - {0}:
        cells = np.argwhere(lab == i)
        if len(cells) < 2000: continue
        x0, x1 = cells[:, 1].min() * R.G, cells[:, 1].max() * R.G; y0, y1 = cells[:, 0].min() * R.G, cells[:, 0].max() * R.G
        print(layer, i, len(cells), 'x %.2f..%.2f y %.2f..%.2f' % (x0, x1, y0, y1))
