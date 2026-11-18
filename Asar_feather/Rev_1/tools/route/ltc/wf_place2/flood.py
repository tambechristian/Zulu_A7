"""flood.py <model> <layer> <net> <w> <sx> <sy> <png> [ignore_nets]: raster flood of where a track of width w of net
can go on one layer from (sx, sy) (0.025 grid), drawing reachable cells over the copper."""
import json, sys, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import deque

M = json.load(open(sys.argv[1])); L = sys.argv[2]; net = sys.argv[3]; w = float(sys.argv[4])
sx, sy = float(sys.argv[5]), float(sys.argv[6]); out = sys.argv[7]
ign = set(sys.argv[8].split(',')) if len(sys.argv) > 8 else set()
ST = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
G = 0.025
W, H = M['board']['w'], M['board']['h']
nx, ny = int(W / G) + 1, int(H / G) + 1
blk = np.zeros((ny, nx), bool)
r0 = 0.09 + w / 2
X = np.arange(nx) * G; Y = np.arange(ny) * G


def span(v):
    return v.get('span') or ST[min(ST.index(v['from']), ST.index(v['to'])):max(ST.index(v['from']), ST.index(v['to'])) + 1]


def mark_circle(x, y, r):
    i0, i1 = max(0, int((x - r) / G)), min(nx - 1, int((x + r) / G) + 1)
    j0, j1 = max(0, int((y - r) / G)), min(ny - 1, int((y + r) / G) + 1)
    xx, yy = np.meshgrid(X[i0:i1 + 1], Y[j0:j1 + 1])
    blk[j0:j1 + 1, i0:i1 + 1] |= (xx - x) ** 2 + (yy - y) ** 2 < r * r


def mark_rect(x, y, hw, hh, r):
    i0, i1 = max(0, int((x - hw - r) / G)), min(nx - 1, int((x + hw + r) / G) + 1)
    j0, j1 = max(0, int((y - hh - r) / G)), min(ny - 1, int((y + hh + r) / G) + 1)
    xx, yy = np.meshgrid(X[i0:i1 + 1], Y[j0:j1 + 1])
    dx = np.maximum(np.abs(xx - x) - hw, 0); dy = np.maximum(np.abs(yy - y) - hh, 0)
    blk[j0:j1 + 1, i0:i1 + 1] |= dx * dx + dy * dy < r * r


def mark_seg(t, r):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    rr = r + t['w'] / 2
    i0, i1 = max(0, int((min(x1, x2) - rr) / G)), min(nx - 1, int((max(x1, x2) + rr) / G) + 1)
    j0, j1 = max(0, int((min(y1, y2) - rr) / G)), min(ny - 1, int((max(y1, y2) + rr) / G) + 1)
    xx, yy = np.meshgrid(X[i0:i1 + 1], Y[j0:j1 + 1])
    dx, dy = x2 - x1, y2 - y1
    d2 = dx * dx + dy * dy or 1e-12
    u = np.clip(((xx - x1) * dx + (yy - y1) * dy) / d2, 0, 1)
    blk[j0:j1 + 1, i0:i1 + 1] |= (xx - x1 - u * dx) ** 2 + (yy - y1 - u * dy) ** 2 < rr * rr


for p in M['pads']:
    ls = p['layers'] or (ST if p['drill'] > 0 else [])
    if L in ls and p['net'] != net and p['net'] not in ign:
        mark_rect(p['x'], p['y'], p['w'] / 2, p['h'] / 2, r0)
for t in M['tracks']:
    if t['layer'] == L and t['net'] != net and t['net'] not in ign:
        mark_seg(t, r0)
for v in M['vias']:
    if L in span(v) and v['net'] != net and v['net'] not in ign:
        mark_circle(v['x'], v['y'], r0 + v['size'] / 2)
e = 0.3 + w / 2
blk[:, :int(e / G) + 1] = True; blk[:, nx - int(e / G) - 1:] = True; blk[:int(e / G) + 1, :] = True; blk[ny - int(e / G) - 1:, :] = True
seen = np.zeros_like(blk)
q = deque([(int(round(sy / G)), int(round(sx / G)))])
seen[q[0]] = True
while q:
    j, i = q.popleft()
    for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = j + dj, i + di
        if 0 <= a < ny and 0 <= b < nx and not blk[a, b] and not seen[a, b]:
            seen[a, b] = True; q.append((a, b))
img = np.zeros((ny, nx, 3)); img[blk] = (0.4, 0.4, 0.4); img[seen] = (1, 0.3, 1); img[~blk & ~seen] = (1, 1, 1)
plt.figure(figsize=(20, 9)); plt.imshow(img, origin='lower', extent=(0, W, 0, H)); plt.grid(True, lw=.3)
plt.xticks(np.arange(0, W, 1)); plt.yticks(np.arange(0, H, 1)); plt.title('%s %s w%.2f from %.2f,%.2f' % (L, net, w, sx, sy))
plt.tight_layout(); plt.savefig(out, dpi=70)
print('reachable cells', seen.sum())
