"""snap.py <base_moved> <rip> <plan_in> <plan_out> [extra plans...]
Router T-junctions land within half a width of the target track's centreline; prune_stubs trims a one-free-end
track back only to junctions ON its centreline (1e-4), so off-centre T's get trimmed away and whole live chains
cascade dead. Move every such plan track end (and every plan end coincident with it) onto the exact projection."""
import json, math, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as C
B = json.load(open(sys.argv[1])); R = json.load(open(sys.argv[2])); P = json.load(open(sys.argv[3]))
X = [json.load(open(a)) for a in sys.argv[5:]]
A = C.apply(B, dict(R, tracks=sum((x['tracks'] for x in X), []), vias=sum((x['vias'] for x in X), [])))
def proj(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']; dx, dy = x2 - x1, y2 - y1; L2 = dx*dx + dy*dy
    if L2 == 0: return None
    k = ((px - x1)*dx + (py - y1)*dy)/L2
    if k <= 0.001 or k >= 0.999: return None
    qx, qy = x1 + k*dx, y1 + k*dy
    return (qx, qy, math.hypot(px - qx, py - qy))
targets = A['tracks']
snap = {}
for t in P['tracks']:
    for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
        best = None
        for o in targets:
            if o is t or o['net'] != t['net'] or o['layer'] != t['layer']: continue
            if any(math.hypot(x - a, y - b) <= 0.01 for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2']))): best = None; break
            r = proj(x, y, o)
            for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])):
                d = math.hypot(x - a, y - b)
                if d <= o['w'] / 2 and (best is None or d < best[2]) and not r: r = (a, b, d)
            if r and 1e-4 < r[2] <= o['w']/2 + 1e-4 and (best is None or r[2] < best[2]): best = r
        if best: snap[(t['net'], t['layer'], round(x, 4), round(y, 4))] = (round(best[0], 5), round(best[1], 5))
n = 0
for t in P['tracks']:
    for a, b in (('x1', 'y1'), ('x2', 'y2')):
        k = (t['net'], t['layer'], round(t[a], 4), round(t[b], 4))
        if k in snap: t[a], t[b] = snap[k]; n += 1
for k, v in snap.items(): print('snap', k, '->', v)
json.dump(P, open(sys.argv[4], 'w'))
print('snapped %d ends' % n)
