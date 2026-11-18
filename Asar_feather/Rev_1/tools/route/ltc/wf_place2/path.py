"""path.py <model> <layer> <net> <w> <sx> <sy> <tx> <ty> <out.json> [tol]
Max-clearance raster path on one layer (8-connected Dijkstra, cost = step * (1 + 2/(clearance)) ), simplified (RDP)."""
import json, sys, math, heapq
import numpy as np
exec(open('flood.py').read().split('seen = np.zeros_like(blk)')[0].replace("out = sys.argv[7]", "out = None").replace(
    "ign = set(sys.argv[8].split(',')) if len(sys.argv) > 8 else set()", "ign = set()"))
tx, ty = float(sys.argv[7]), float(sys.argv[8]); outp = sys.argv[9]
tol = float(sys.argv[10]) if len(sys.argv) > 10 else 0.03
# clearance field: distance (cells) to blocked, via repeated dilation (cheap BFS)
from collections import deque
dist = np.full(blk.shape, 1e9); q = deque()
for j, i in zip(*np.nonzero(blk)):
    dist[j, i] = 0; q.append((j, i))
ny_, nx_ = blk.shape
while q:
    j, i = q.popleft()
    for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = j + dj, i + di
        if 0 <= a < ny_ and 0 <= b < nx_ and dist[a, b] > dist[j, i] + 1:
            dist[a, b] = dist[j, i] + 1; q.append((a, b))
s = (int(round(sy / G)), int(round(sx / G))); t = (int(round(ty / G)), int(round(tx / G)))
assert not blk[s] and not blk[t], (blk[s], blk[t])
D = {s: 0.0}; prev = {}; pq = [(0.0, s)]
while pq:
    d, u = heapq.heappop(pq)
    if u == t:
        break
    if d > D.get(u, 1e18):
        continue
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            if not dj and not di:
                continue
            v = (u[0] + dj, u[1] + di)
            if not (0 <= v[0] < ny_ and 0 <= v[1] < nx_) or blk[v]:
                continue
            c = math.hypot(dj, di) * (1 + 3.0 / min(dist[v], 12))
            if d + c < D.get(v, 1e18):
                D[v] = d + c; prev[v] = u; heapq.heappush(pq, (d + c, v))
pts = [t]
while pts[-1] != s:
    pts.append(prev[pts[-1]])
pts = [(p[1] * G, p[0] * G) for p in reversed(pts)]


def rdp(P, e):
    if len(P) < 3:
        return P
    (x1, y1), (x2, y2) = P[0], P[-1]
    dx, dy = x2 - x1, y2 - y1; n = math.hypot(dx, dy) or 1e-9
    ds = [abs(dy * (x - x1) - dx * (y - y1)) / n for x, y in P[1:-1]]
    k = int(np.argmax(ds)) + 1
    if ds[k - 1] > e:
        return rdp(P[:k + 1], e)[:-1] + rdp(P[k:], e)
    return [P[0], P[-1]]


sp = rdp(pts, tol)
sp = [(round(x, 3), round(y, 3)) for x, y in sp]
sp[0] = (sx, sy); sp[-1] = (tx, ty)
json.dump(sp, open(outp, 'w'))
print(len(pts), '->', len(sp), sp)
