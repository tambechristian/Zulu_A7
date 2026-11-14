"""fine (2.5 um) scan of the U3-body-end R0201 site, rot 90 (vertical), exact copper margin vs every non-D10 Bottom
object and the gap to U3's body outline (max 39.525 / nominal 39.46)"""
import numpy as np, maze as M
D = M.D
B = M.Board()
Gd = D.Grid([o for o in B.base if o.layer == 'Bottom'], 0.5)
rows = []
for cx in np.arange(39.62, 39.75, 0.0025):
    for cy in np.arange(14.45, 14.80, 0.0025):
        worst = (9, None)
        for px, py in ((cx, cy - 0.3), (cx, cy + 0.3)):
            S = ('R', px, py, 0.15, 0.15)
            for q in Gd.near('Bottom', D.bbox(S), 0.3):
                d = D.dist(S, q.shape) - 0.09
                if d < worst[0]:
                    worst = (d, q.tag)
        if worst[0] < 0:
            continue
        rows.append((round(cx - 0.165 - 39.525, 4), round(cx - 0.165 - 39.46, 4), round(worst[0], 4), round(cx, 4), round(cy, 4), worst[1]))
rows.sort(key=lambda r: (-min(r[0] + 0.01, r[2] - 0.005), ))
for r in rows[:5]:
    print('gap to U3 max %+.4f nominal %+.4f  cu margin %+.4f  centre (%.4f,%.4f)  %s' % r)
for m in (0.002, 0.005, 0.0075, 0.010):
    c = [r for r in rows if r[2] >= m]
    b = max(c, key=lambda r: (r[0], r[2]))
    print('cu margin >= %.4f: best gap to U3 max %+.4f (nominal %+.4f) at (%.4f,%.4f), cu %+.4f, limit %s' % (m, b[0], b[1], b[3], b[4], b[2], b[5]))
