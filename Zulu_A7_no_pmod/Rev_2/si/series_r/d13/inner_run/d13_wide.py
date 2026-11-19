"""D13 wide probe: legal column-site PAIRS (0.6 mm apart, any rotation) within 2.0 mm of the L3 run whose R0201 box
clears every same-side component box by 0.254 (Altium) and every body (section 10) -- before any connector routing.
If this is empty, no inner-run R exists for D13 whatever the connector shape."""
import json, math, collections
import search as S
net = 'D13'
runL, segs, used = S.run_poly(net)
allx = [v for s in segs for v in (s[0], s[2])]; ally = [v for s in segs for v in (s[1], s[3])]
STEP = 0.025
sites = {}
for side in ('Top', 'Bottom'):
    x0, y0 = min(allx) - 2.0, min(ally) - 2.0
    nx, ny = int((max(allx) + 2.0 - x0) / STEP) + 1, int((max(ally) + 2.0 - y0) / STEP) + 1
    for i in range(nx):
        x = round(x0 + i * STEP, 4)
        for j in range(ny):
            y = round(y0 + j * STEP, 4)
            if S.proj(segs, x, y)[0] > 2.0:
                continue
            # body pre-filter on the pad alone (cheap): a pad inside a body box can never be part of a legal R
            pb = [x - 0.15, y - 0.15, x + 0.15, y + 0.15]
            if any(s_ == side and S.rr(pb, b) < 0.254 for r, (s_, b) in S.ABOX.items()):
                continue
            ok, m = S.site_eval(net, side, runL, x, y)
            if ok:
                sites[(side, i, j)] = (x, y)
pairs = []
for (side, i, j), (x, y) in sites.items():
    for rot, (dx, dy) in S.ROT.items():
        if rot in (180, 270):
            continue
        k2 = (side, i + int(round(dx / STEP)), j + int(round(dy / STEP)))
        if k2 in sites:
            x2, y2 = sites[k2]
            bb = [min(x, x2) - 0.15, min(y, y2) - 0.15, max(x, x2) + 0.15, max(y, y2) + 0.15]
            a14 = min((S.rr(bb, b), r) for r, (s_, b) in S.ABOX.items() if s_ == side)
            a10 = min((min(S.rr(bb, b) for b in bx), r) for r, (s_, bx) in S.BBOX10.items() if s_ == side)
            if a14[0] >= 0.254 and a10[0] >= 0.254:
                pairs.append(dict(side=side, p1=[x, y], p2=[x2, y2], dist_to_run=[round(S.proj(segs, x, y)[0], 3), round(S.proj(segs, x2, y2)[0], 3)], cc=[a14, a10]))
print('legal sites outside bodies within 2.0 mm:', collections.Counter(k[0] for k in sites))
print('R positions (site pairs) clear of every component box:', len(pairs))
for p in sorted(pairs, key=lambda p: max(p['dist_to_run']))[:30]:
    print('  ', p)
json.dump(dict(sites=[[k[0], v[0], v[1]] for k, v in sites.items()], pairs=pairs), open('d13_wide.json', 'w'))
