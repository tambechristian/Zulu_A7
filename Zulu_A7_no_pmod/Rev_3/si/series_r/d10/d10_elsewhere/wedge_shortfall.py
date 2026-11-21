"""exact: best copper margin of a Bottom R0201 east of U3 that meets ComponentClearance 0.254 to U3's max body
(x0 >= 39.779), scanning the wedge x 39.94..41.2, y 13.3..15.6 on a 5 um grid, both orientations"""
import numpy as np, maze as M
D = M.D
B = M.Board()
Gd = D.Grid([o for o in B.base if o.layer == 'Bottom'], 0.5)
best = {}
for rot in (0, 90):
    dx, dy = (0.3, 0) if rot == 0 else (0, 0.3)
    hx = 0.45 if rot == 0 else 0.165
    for cx in np.arange(39.779 + hx, 41.2, 0.005):
        for cy in np.arange(13.3, 15.6, 0.005):
            worst = (9, None, None)
            for k, (px, py) in enumerate(((cx - dx, cy - dy), (cx + dx, cy + dy))):
                S = ('R', px, py, 0.15, 0.15)
                for q in Gd.near('Bottom', D.bbox(S), 0.3):
                    d = D.dist(S, q.shape) - 0.09
                    if d < worst[0]:
                        worst = (d, q.tag, k + 1)
            if rot not in best or worst[0] > best[rot][0]:
                best[rot] = (worst[0], round(cx, 4), round(cy, 4), worst[1], worst[2])
for rot, b in best.items():
    print('rot %d: best copper margin %+.4f mm at (%.4f,%.4f), limited by %s (pad %s)' % ((rot,) + b))
