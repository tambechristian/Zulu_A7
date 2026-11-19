"""Strip the seed copper of other nets that conflicts with a net's seed copper (geometry, no routing).

    python strip_conflicts.py SEED.json NET OUT_SEED.json [extra_mm]
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import router as R  # noqa: E402

seed_f, net, out_f = sys.argv[1:4]
extra = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
S = json.load(open(seed_f))
T, V = S['tracks'], S['vias']


def pseg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def sseg(a, b):
    p1, p2, p3, p4 = (a['x1'], a['y1']), (a['x2'], a['y2']), (b['x1'], b['y1']), (b['x2'], b['y2'])
    if ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4):
        return 0.0
    return min(pseg(*p1, *p3, *p4), pseg(*p2, *p3, *p4), pseg(*p3, *p1, *p2), pseg(*p4, *p1, *p2))


def span(v):
    return set(R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1])


mt = [t for t in T if t['net'] == net]
mv = [v for v in V if v['net'] == net]
bad_t, bad_v = set(), set()
for k, t in enumerate(T):
    if t['net'] == net:
        continue
    for m in mt:
        if m['layer'] == t['layer'] and sseg(m, t) < (m['w'] + t['w']) / 2 + R.clearance(t['net'], t['layer']) + extra:
            bad_t.add(k)
            break
    else:
        for v in mv:
            if t['layer'] in span(v) and pseg(v['x'], v['y'], t['x1'], t['y1'], t['x2'], t['y2']) < \
                    v['size'] / 2 + t['w'] / 2 + R.clearance(t['net'], t['layer']) + extra:
                bad_t.add(k)
                break
for k, v in enumerate(V):
    if v['net'] == net:
        continue
    sv = span(v)
    for m in mt:
        if m['layer'] in sv and pseg(v['x'], v['y'], m['x1'], m['y1'], m['x2'], m['y2']) < \
                v['size'] / 2 + m['w'] / 2 + R.clearance(net, m['layer']) + extra:
            bad_v.add(k)
            break
    else:
        for m in mv:
            if span(m) & sv:
                d = math.hypot(v['x'] - m['x'], v['y'] - m['y'])
                if d < (v['size'] + m['size']) / 2 + R.CLEAR + extra or d < R.HOLE_HOLE + (v['hole'] + m['hole']) / 2 + 0.001:
                    bad_v.add(k)
                    break
nets = {}
for k in bad_t:
    nets[T[k]['net']] = nets.get(T[k]['net'], 0) + 1
for k in bad_v:
    nets[V[k]['net']] = nets.get(V[k]['net'], 0) + 1
print('stripped %d tracks, %d vias; per net %s' % (len(bad_t), len(bad_v), nets))
json.dump({'vias': [v for k, v in enumerate(V) if k not in bad_v], 'tracks': [t for k, t in enumerate(T) if k not in bad_t],
           'remove': [], 'log': []}, open(out_f, 'w'))
