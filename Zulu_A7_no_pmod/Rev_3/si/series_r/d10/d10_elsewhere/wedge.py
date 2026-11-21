"""best R0201 sites (Bottom) in the free wedge east of U3's body, ignoring the 0.254 component clearance: what blocks"""
import maze as M, numpy as np
D = M.D
B = M.Board()
Gd = D.Grid([o for o in B.base if o.layer == 'Bottom'], 0.5)
best = []
for cx in np.arange(39.6, 40.8, 0.0125):
    for cy in np.arange(13.6, 15.4, 0.0125):
        for rot in (0, 90):
            dx, dy = (0.3, 0) if rot == 0 else (0, 0.3)
            worst = (9, None)
            for px, py in ((cx - dx, cy - dy), (cx + dx, cy + dy)):
                S = ('R', px, py, 0.15, 0.15)
                for q in Gd.near('Bottom', D.bbox(S), 0.3):
                    d = D.dist(S, q.shape) - 0.09
                    if d < worst[0]:
                        worst = (d, q.tag)
            body_x0 = cx - (0.315 if rot == 0 else 0.165)
            pad_x0 = cx - abs(dx) - 0.15
            u3gap = min(body_x0, pad_x0) - 39.525
            best.append((worst[0], u3gap, round(cx, 4), round(cy, 4), rot, worst[1]))
best.sort(key=lambda t: -t[0])
for b in best[:15]:
    print('cu margin %+.4f  gap to U3 body(max) %.3f  R at (%.4f,%.4f) rot %d  limiting %s' % b)
ok = [b for b in best if b[0] >= 0]
print('copper-legal sites in the wedge:', len(ok), ' of which comp gap >= 0.254:', sum(1 for b in ok if b[1] >= 0.254))
for b in sorted(ok, key=lambda t: -t[1])[:8]:
    print('  max-U3-gap legal: cu %+.4f gap %.3f (%.4f,%.4f) rot %d %s' % b)
