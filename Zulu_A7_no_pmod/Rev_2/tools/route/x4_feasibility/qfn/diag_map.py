"""ASCII free-space map of one layer for a net (base mode: seed copper rippable).

    python diag_map.py BASE.json SEED.json NET LAYER x0 x1 y0 y1
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

base_f, seed_f, net, lay = sys.argv[1:5]
x0, x1, y0, y1 = map(float, sys.argv[5:9])
M = json.load(open(base_f))
B = R.Board(M)
Rt = R.Router(B, 6000000)
Rt.soft = 1.0
P = json.load(open(seed_f))
Rt.out_t += P['tracks']
Rt.out_v += P['vias']
Rt.rip(set())
Mx = dict(M)
Mx['tracks'] = M['tracks'] + Rt.out_t
Mx['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in Rt.out_v]
groups = C.islands(Mx)[net]
win = R.window(B, [R.bbox(Mx, g) for g in groups], 5.0)
Db = Rt.dist(net, win, True)
li = {'T': 0, 'B': len(R.STACK) - 1}.get(lay, None)
if li is None:
    li = R.STACK.index(lay)
i0, i1, j0, j1 = win
D = Db[li] if not isinstance(Db, dict) else Db[R.STACK[li]]
need = R.width(net, R.STACK[li]) / 2 + R.MARGIN
print('need', need, 'G', R.G, 'layers', R.STACK)
step = int(os.environ.get('STEP', 4))
for y in [y0 + k * R.G * step for k in range(int((y1 - y0) / (R.G * step)) + 1)]:
    row = ''
    for x in [x0 + k * R.G * step for k in range(int((x1 - x0) / (R.G * step)) + 1)]:
        i, j = int(round(y / R.G)) - i0, int(round(x / R.G)) - j0
        try:
            d = float(D[i, j])
        except IndexError:
            row += '?'
            continue
        row += '.' if d >= need else ('+' if d >= need - 0.1 else '#')
    print('%6.2f %s' % (y, row))
