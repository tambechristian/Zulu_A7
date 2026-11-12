"""trim_pads.py <model.json> <out_extra.json>
A moved land can sit on the BODY of its own net's old track while the track's ends dangle beyond it. route_conn
counts that as connected, prune_stubs (Altium's Net Antennae) does not: it trims only back to track / via junctions,
so the whole chain dies and the connection reopens after compose. This trims every such track back to the point of
its centreline nearest the pad centre (inside the pad), so the kept part ends ON the pad.
Writes {remove: [...], tracks: [trimmed copies]}."""
import json
import math
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

M = json.load(open(sys.argv[1]))
STACK = PS.STACK
by = {}
for t in M['tracks']:
    by.setdefault((t['net'], t['layer']), []).append(t)
vias = {}
for v in M['vias']:
    for L in PS.span(v):
        vias.setdefault((v['net'], L), []).append(v)
pads = {}
for p in M['pads']:
    if p['net']:
        for L in (p['layers'] or (STACK if p['drill'] else [])):
            pads.setdefault((p['net'], L), []).append(p)


def live(t, x, y):
    k = (t['net'], t['layer'])
    if any(C.pad_point(p, x, y) <= PS.EPS for p in pads.get(k, [])):
        return True
    if any(math.hypot(v['x'] - x, v['y'] - y) <= v['size'] / 2 + PS.EPS for v in vias.get(k, [])):
        return True
    return any(o is not t and PS.joins(x, y, o, t) for o in by.get(k, []))


rm, add = [], []
for t in M['tracks']:
    ends = [(t['x1'], t['y1']), (t['x2'], t['y2'])]
    lv = [live(t, *e) for e in ends]
    if all(lv):
        continue
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L2 = dx * dx + dy * dy
    if L2 == 0:
        continue
    ks = [0.0] if lv[0] else []
    ks += [1.0] if lv[1] else []
    n = max(2, int(math.sqrt(L2) / 0.002))
    for p in pads.get((t['net'], t['layer']), []):
        inside = [i / n for i in range(n + 1) if C.pad_point(p, t['x1'] + dx * i / n, t['y1'] + dy * i / n) <= 0]
        if inside:                                   # the middle of the stretch of centreline inside the pad
            ks.append((min(inside) + max(inside)) / 2)
    if len(ks) < 2 or math.sqrt(L2) * (max(ks) - min(ks)) < 0.005:
        continue
    k0, k1 = min(ks), max(ks)
    nt = dict(t, x1=round(t['x1'] + k0 * dx, 4), y1=round(t['y1'] + k0 * dy, 4), x2=round(t['x1'] + k1 * dx, 4),
              y2=round(t['y1'] + k1 * dy, 4))
    rm.append(t)
    add.append(nt)
    print('trim %-10s %-12s (%.3f,%.3f)-(%.3f,%.3f) -> (%.4f,%.4f)-(%.4f,%.4f)' % (
        t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], nt['x1'], nt['y1'], nt['x2'], nt['y2']))
json.dump({'remove': rm, 'remove_vias': [], 'tracks': add, 'vias': []}, open(sys.argv[2], 'w'), indent=1)
print('%d tracks trimmed onto pads' % len(add))
