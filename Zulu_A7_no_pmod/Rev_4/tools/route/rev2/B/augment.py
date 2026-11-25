"""augment.py <base_moved.json> <rip.json> <route.json> <out_route.json>
compose_plan trims a dead-ended track back to the farthest junction ON ITS CENTRELINE (seg_d <= 1e-4), but the
router T-joins track ends / via centres anywhere within a track's width. The trim then cuts the joint away and the
connection reopens. For every plan track end or via centre that lies within a same-net, same-layer track's width but
off its centreline (and not at its endpoints), add a short connector track (same net / layer / width as the plan
item's track) from that point to its projection on the centreline. The connector lies inside existing copper."""
import json
import math
import sys

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
EPS, JOIN = 1e-4, 0.01


def tkey(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4), round(t['w'], 4))


def proj(px, py, t, tol=0.0):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return None
    k = ((px - x1) * dx + (py - y1) * dy) / L2
    L = math.sqrt(L2)
    if not (JOIN / L < k < 1 - JOIN / L):
        return None
    qx, qy = x1 + k * dx, y1 + k * dy
    d = math.hypot(px - qx, py - qy)
    if d <= EPS or d > t['w'] / 2 + tol + EPS:
        return None
    return round(qx, 4), round(qy, 4)


B, R, P = (json.load(open(a)) for a in sys.argv[1:4])
rk = {tkey(t) for t in R['remove']}
tracks = [t for t in B['tracks'] if tkey(t) not in rk] + P['tracks']
by = {}
for t in tracks:
    by.setdefault((t['net'], t['layer']), []).append(t)
add = []
pts = []
for t in P['tracks']:
    for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
        pts.append((t['net'], t['layer'], x, y, t['w'], 0.0))
for v in P['vias']:
    sp = STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
    for L in sp:
        if L in ('L2-GND', 'L5-VCC3V3'):
            continue
        pts.append((v['net'], L, v['x'], v['y'], 9.0, v['size'] / 2))
seen = set()
for net, L, x, y, w, tol in pts:
    for o in by.get((net, L), []):
        # skip if the point is already an endpoint of o
        if any(math.hypot(x - a, y - b) <= JOIN * 0.5 for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2']))):
            continue
        near = [(a, b) for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])) if tol == 0 and math.hypot(x - a, y - b) <= 0.02]
        if near:                                   # near (not on) o's endpoint: prune's 0.01 join is float-fragile
            a, b = near[0]
            key = (net, L, round(x, 4), round(y, 4), (round(a, 4), round(b, 4)))
            if key not in seen:
                seen.add(key)
                add.append({'net': net, 'layer': L, 'w': min(w, o['w']), 'x1': round(x, 4), 'y1': round(y, 4),
                            'x2': round(a, 4), 'y2': round(b, 4)})
            continue
        q = proj(x, y, o, tol)
        if q and (net, L, round(x, 4), round(y, 4), q) not in seen:
            seen.add((net, L, round(x, 4), round(y, 4), q))
            add.append({'net': net, 'layer': L, 'w': min(w, o['w']), 'x1': round(x, 4), 'y1': round(y, 4), 'x2': q[0], 'y2': q[1]})
print('connectors added: %d' % len(add))
for a in add:
    print('  %s %s %.4f,%.4f -> %.4f,%.4f' % (a['net'], a['layer'], a['x1'], a['y1'], a['x2'], a['y2']))
P = dict(P)
P['tracks'] = P['tracks'] + add
json.dump(P, open(sys.argv[4], 'w'), indent=1)
