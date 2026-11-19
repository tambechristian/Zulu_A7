"""Why does the USB5V0 rip-up fail? Base path, its victims, and the normal-mode free space along that path after the rip.

    python diag_usb.py BASE.json SEED.json [net]
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import numpy as np  # noqa: E402
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

base_f, seed_f = sys.argv[1], sys.argv[2]
net = sys.argv[3] if len(sys.argv) > 3 else 'USB5V0'
M = json.load(open(base_f))
B = R.Board(M)
Rt = R.Router(B, 6000000)
Rt.soft = 1.0
P = json.load(open(seed_f))
Rt.out_t += P['tracks']
Rt.out_v += P['vias']
Rt.rip(set())


def cur():
    Mx = dict(M)
    Mx['tracks'] = M['tracks'] + Rt.out_t
    Mx['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in Rt.out_v]
    return Mx


Mx = cur()
groups = C.islands(Mx)[net]
print('islands', len(groups), [R.bbox(Mx, g) for g in groups])
main_g, gi = groups[0], groups[1]
mb = R.bbox(Mx, main_g)


def route(base):
    for mg in (80.0,):
        win = R.window(B, [mb, R.bbox(Mx, gi)], mg)
        r = Rt.route(net, R.island_mask(B, Mx, main_g, win), R.island_mask(B, Mx, gi, win), win, base=base)
        if r:
            return r, win
    return None, None


rb, win = route(True)
if not rb:
    print('no base path', Rt.why)
    sys.exit()
path = rb[0]
print('base path cells', len(path), 'pops', Rt.pops)
vias = [(p[3], round(p[1], 3), round(p[2], 3)) for p in path if p[3]]
print('vias on path', vias)
victims = Rt.blockers(net, rb[0], tight=True)
print('victims', sorted(victims))
Rt.rip({v for v in victims if v not in R.PLANE_VIAS})
Mx = cur()
D = Rt.dist(net, win, False)
Db = Rt.dist(net, win, True)
i0, i1, j0, j1 = win
bad = []
for l, x, y, kind in path:
    i, j = int(round(y / R.G)) - i0, int(round(x / R.G)) - j0
    need = R.width(net, l) / 2 + R.MARGIN
    if D[l][i, j] < need:
        bad.append((l, round(x, 3), round(y, 3), round(float(D[l][i, j]), 3), round(float(Db[l][i, j]), 3), round(need, 3)))
print('path cells not free after rip:', len(bad))
for b in bad[:40]:
    print(' ', b)
for vk in vias:
    ok = Rt.via_ok(net, vk[0], vk[1], vk[2], D, win, False)
    okb = Rt.via_ok(net, vk[0], vk[1], vk[2], Db, win, True)
    print('via', vk, 'ok normal', ok, 'ok base', okb)
pl = set(R.PLANE_VIAS)


def seg_dist(px, py, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * vx + (py - y1) * vy) / L))
    return math.hypot(px - x1 - t * vx, py - y1 - t * vy)


for t in Rt.out_t:
    if t['net'] in pl or t['net'] in victims:
        hit = [p for p in path if p[0] == t['layer'] and seg_dist(p[1], p[2], t['x1'], t['y1'], t['x2'], t['y2']) < 0.5]
        if hit:
            print('track', t['net'], t['layer'][:3], t['x1'], t['y1'], t['x2'], t['y2'], 'near path cells', len(hit))
for v in Rt.out_v:
    if v['net'] in pl or v['net'] in victims:
        span = R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]
        hit = [p for p in path if p[0] in span and math.hypot(p[1] - v['x'], p[2] - v['y']) < 0.7]
        if hit:
            print('via', v['net'], v['x'], v['y'], v['from'][:3], v['to'][:3], 'near path cells', len(hit))
r2, _ = route(False)
print('normal route after rip:', 'found' if r2 else 'FAILED ' + Rt.why)
