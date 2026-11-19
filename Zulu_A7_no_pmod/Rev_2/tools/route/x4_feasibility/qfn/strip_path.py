"""Find the cheapest path for a net (seed copper rippable), then strip only the seed objects that path overlaps.

    python strip_path.py BASE.json SEED.json NET OUT_SEED.json [margin_mm]

The nets that lose copper are re-joined afterwards by router.py (rip 0), which only has to heal the cut.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

base_f, seed_f, net, out_f = sys.argv[1:5]
extra = float(sys.argv[5]) if len(sys.argv) > 5 else 0.03
M = json.load(open(base_f))
P = json.load(open(seed_f))
# PROTECT=NET1,NET2: those nets' seed copper is treated as fixed model copper during the search
protect = {n for n in os.environ.get('PROTECT', '').split(',') if n}
keep_t = [t for t in P['tracks'] if t['net'] in protect]
keep_v = [v for v in P['vias'] if v['net'] in protect]
P['tracks'] = [t for t in P['tracks'] if t['net'] not in protect]
P['vias'] = [v for v in P['vias'] if v['net'] not in protect]
M['tracks'] = M['tracks'] + keep_t
M['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in keep_v]
B = R.Board(M)
Rt = R.Router(B, 6000000)
Rt.soft = 1.0
Rt.out_t += P['tracks']
Rt.out_v += P['vias']
Rt.rip(set())
Mx = dict(M)
Mx['tracks'] = M['tracks'] + Rt.out_t
Mx['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in Rt.out_v]
groups = C.islands(Mx)[net]
print('islands', len(groups), [R.bbox(Mx, g) for g in groups])
win = R.window(B, [R.bbox(Mx, groups[0]), R.bbox(Mx, groups[1])], 80.0)
rb = Rt.route(net, R.island_mask(B, Mx, groups[0], win), R.island_mask(B, Mx, groups[1], win), win, base=True)
if not rb:
    sys.exit('no base path ' + str(Rt.why))
path = rb[0]
print('path cells', len(path))


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


bad_t, bad_v = set(), set()
for l, x, y, kind in path:
    if kind:
        objs, occ, _ = R.VIAS[kind]
        rad = max(o[2] for o in objs) / 2 + R.CLEAR + R.MARGIN + extra
        hole = max(o[3] for o in objs) / 2
        layers = set(occ)
    else:
        rad = R.width(net, l) / 2 + R.clearance(net, l) + R.MARGIN + extra
        layers = {l}
    for k, t in enumerate(Rt.out_t):
        if t['net'] == net or t['layer'] not in layers:
            continue
        if seg_dist(x, y, t['x1'], t['y1'], t['x2'], t['y2']) < rad + t['w'] / 2:
            bad_t.add(k)
    for k, v in enumerate(Rt.out_v):
        if v['net'] == net:
            continue
        span = set(R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1])
        if not span & layers:
            continue
        lim = rad + v['size'] / 2
        if kind:
            lim = max(lim, R.HOLE_HOLE + hole + v['hole'] / 2 + 0.001)
        if math.hypot(v['x'] - x, v['y'] - y) < lim:
            bad_v.add(k)
nets = sorted({Rt.out_t[k]['net'] for k in bad_t} | {Rt.out_v[k]['net'] for k in bad_v})
print('conflicts: %d tracks, %d vias; nets %s' % (len(bad_t), len(bad_v), nets))
print('path vias', [(p[3], round(p[1], 3), round(p[2], 3)) for p in path if p[3]])
json.dump({'vias': [v for k, v in enumerate(Rt.out_v) if k not in bad_v] + keep_v,
           'tracks': [t for k, t in enumerate(Rt.out_t) if k not in bad_t] + keep_t, 'remove': [], 'log': []}, open(out_f, 'w'))
