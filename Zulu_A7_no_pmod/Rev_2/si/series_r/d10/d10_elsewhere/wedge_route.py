"""Stage-2 routing of the U3-body-end ('wedge') R sites: copper-legal Bottom R0201 sites whose only rule problem is
the U3 body (max-tolerance outline x1 = 39.525).  Sites are kept when the R footprint/body overlaps that outline by
at most --overlap mm (default 0.05).  Writes wedge_route.json."""
import sys, json, os
ARGV = list(sys.argv)
import numpy as np
import maze as M
D = M.D
ov = float(ARGV[ARGV.index('--overlap') + 1]) if '--overlap' in ARGV else 0.05
B = M.Board()
Gd = D.Grid([o for o in B.base if o.layer == 'Bottom'], 0.5)
Gp = D.Grid([o for o in B.objs if o.kind == 'pad' and o.layer == 'Bottom'], 0.5)
sites = []
for cx in np.arange(39.45, 40.6, M.G):
    for cy in np.arange(13.3, 15.3, M.G):
        for rot in (0, 90):
            dx, dy = (0.3, 0) if rot == 0 else (0, 0.3)
            worst = 9
            okm = True
            for px, py in ((cx - dx, cy - dy), (cx + dx, cy + dy)):
                S = ('R', px, py, 0.15, 0.15)
                for q in Gd.near('Bottom', D.bbox(S), 0.3):
                    worst = min(worst, D.dist(S, q.shape) - 0.09)
                Sm = ('R', px, py, 0.2, 0.2)
                for q in Gp.near('Bottom', D.bbox(Sm), 0.3):
                    if q.net not in M.F.FAM and D.dist(Sm, D.grow(q.shape, D.mask_exp(q))) < 0.102:
                        okm = False
            x0 = min(cx - (0.315 if rot == 0 else 0.165), cx - abs(dx) - 0.15)
            gapU3 = x0 - 39.525
            if worst >= 0.003 and okm and gapU3 >= -ov:
                sites.append(dict(side='Bottom', x=round(float(cx), 4), y=round(float(cy), 4), rot=rot, cu_margin=round(worst, 4), comp_gap=round(gapU3, 4)))
print('wedge sites', len(sites))
res = []
for mode in ('A', 'B'):
    sc, r = M.run_mode(B, mode, sites, 12)
    res += r
json.dump(dict(overlap=ov, sites=sites, results=res), open(os.path.join(M.HERE, 'wedge_route.json'), 'w'), indent=1)
