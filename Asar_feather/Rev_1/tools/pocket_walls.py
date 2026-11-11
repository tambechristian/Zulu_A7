"""What walls a U1 ball's island in (2026-10-28): flood the router's free cells from the island (vias where the
router's via test passes), then list the foreign copper touching the reached region per layer and net, and which
plan file owns it (stage1_u1 / stage3_sdram / stage4 in tools/route, or the given plan).

    python tools/pocket_walls.py <model.json> <plan.json> <stage1_model.json> <ball> [swaps a>b,c>d] [margin mm]
"""
import json, os, sys, math
from collections import defaultdict, deque
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import router as R, route_conn as C, swap_eval as E
from diagnose_open import with_plan
model, plan, stage1, ball = sys.argv[1:5]
swaps = [tuple(s.split('>')) for s in sys.argv[5].split(',')] if len(sys.argv) > 5 and sys.argv[5] else []
margin = float(sys.argv[6]) if len(sys.argv) > 6 else 6.0
Mx = with_plan(json.load(open(model)), json.load(open(plan)))
fan = E.fanout(json.load(open(stage1)))
Ms, nets = E.swapped(Mx, fan, swaps) if swaps else (Mx, set())
B = R.Board(Ms); Rt = R.Router(B, 10)
isl = C.islands(Ms)
net = [p['net'] for p in Ms['pads'] if p['ref'] == 'U1' and p['pad'] == ball][0]
g = [g for g in isl[net] if any(Ms['pads'][i]['ref'] == 'U1' and Ms['pads'][i]['pad'] == ball for i in g['pads'])][0]
win = R.window(B, [R.bbox(Ms, g)], margin)
i0, i1, j0, j1 = win
Dd = Rt.dist(net, win)
L = {l: k for k, l in enumerate(R.ROUTE)}
free = {l: Dd[l] >= R.width(net, l) / 2 + R.MARGIN for l in R.ROUTE}
src = R.island_mask(B, Ms, g, win)
seen = {l: np.zeros_like(free[l]) for l in R.ROUTE}
q = deque()
for l, m in src.items():
    if l in L:
        for i, j in np.argwhere(m & free[l]):
            seen[l][i, j] = True; q.append((l, int(i), int(j)))
h, w = i1 - i0, j1 - j0
vias_ok = defaultdict(int)
while q:
    l, i, j = q.popleft()
    for di, dj in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
        ni, nj = i + di, j + dj
        if 0 <= ni < h and 0 <= nj < w and free[l][ni, nj] and not seen[l][ni, nj]:
            seen[l][ni, nj] = True; q.append((l, ni, nj))
    x, y = (j + j0) * R.G, (i + i0) * R.G
    for kind, (objs, occ, joins) in R.VIAS.items():
        if l not in joins:
            continue
        for l2 in joins:
            if l2 != l and free[l2][i, j] and not seen[l2][i, j] and Rt.via_ok(net, kind, x, y, Dd, win):
                vias_ok[kind] += 1
                seen[l2][i, j] = True; q.append((l2, i, j))
print('net %s island at U1.%s: reached cells %s; via sites used %s' % (
    net, ball, {l: int(seen[l].sum()) for l in R.ROUTE}, dict(vias_ok)))
# the wall: foreign copper within (clearance + width/2 + 2 cells) of the reached region, per layer and net
from scipy import ndimage
origin = {}
for name in ('stage1_u1', 'stage3_sdram', 'stage4'):
    f = os.path.join(HERE, 'route', name + '.json')
    if os.path.exists(f):
        Pp = json.load(open(f))
        for t in Pp['tracks']:
            origin[('t', t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))] = name
        for v in Pp['vias']:
            origin[('v', round(v['x'], 3), round(v['y'], 3))] = name
for f, name in ((plan, 'plan'),):
    Pp = json.load(open(f))
    for t in Pp['tracks']:
        origin.setdefault(('t', t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3)), name)
    for v in Pp['vias']:
        origin.setdefault(('v', round(v['x'], 3), round(v['y'], 3)), name)
inv = {v: k for k, v in B.nid.items()}
for l in R.ROUTE:
    if not seen[l].any():
        continue
    rad = int(math.ceil((R.width(net, l) / 2 + R.clearance(net, l) + R.MARGIN) / R.G)) + 2
    ring = ndimage.binary_dilation(seen[l], iterations=rad) & ~seen[l]
    sub = B.r[l][i0:i1, j0:j1]
    ids, cnt = np.unique(sub[ring & (sub != 0) & (sub != B.nid[net])], return_counts=True)
    walls = sorted(zip(cnt, ids), reverse=True)[:12]
    print('  %-12s wall: %s' % (l, '  '.join('%s:%d' % (inv.get(int(k), 'BLOCK' if k == -1 else k), c) for c, k in walls)))
# which plan owns the wall copper on this layer: tracks/vias of the top wall nets whose cells touch the ring
    top = {inv.get(int(k)) for c, k in walls if int(k) in inv}
    own = defaultdict(int)
    for t in Ms['tracks']:
        if t['net'] in top and t['layer'] == l:
            jj, ii = int(round(t['x1'] / R.G)) - j0, int(round(t['y1'] / R.G)) - i0
            if 0 <= ii < h and 0 <= jj < w and ring[max(0, ii - 3):ii + 4, max(0, jj - 3):jj + 4].any():
                own[(t['net'], origin.get(('t', t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3)), 'model?'))] += 1
    for v in Ms['vias']:
        if v['net'] in top and l in v['span']:
            jj, ii = int(round(v['x'] / R.G)) - j0, int(round(v['y'] / R.G)) - i0
            if 0 <= ii < h and 0 <= jj < w and ring[max(0, ii - 3):ii + 4, max(0, jj - 3):jj + 4].any():
                own[(v['net'], 'via:' + origin.get(('v', round(v['x'], 3), round(v['y'], 3)), 'model?'))] += 1
    print('               owners: %s' % '  '.join('%s/%s:%d' % (k[0], k[1], c) for k, c in sorted(own.items(), key=lambda kv: -kv[1])[:14]))
