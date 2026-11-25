"""aug.py -- B/augment.py's connector fix as a function (2026-11-11, strategy F).

prune_stubs trims a dead-ended track back to the farthest junction ON ITS CENTRELINE, but the router T-joins track
ends / via centres anywhere within a track's width (0.01-0.0125 mm off). For every new track end or via centre that
lies within a same-net, same-layer track's width but off its centreline (and not at its endpoints), a short
connector (same net / layer, width of the thinner of the two) is added from the point to its projection on the
centreline; a point within 0.02 of a track END (but not within 0.005) gets a connector to that end. Every connector
lies inside copper that is already there, so it changes no clearance."""
import math

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
EPS, JOIN = 1e-4, 0.01


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


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


def connectors(all_tracks, new_tracks, new_vias):
    by = {}
    for t in all_tracks:
        by.setdefault((t['net'], t['layer']), []).append(t)
    pts = []
    for t in new_tracks:
        for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            pts.append((t['net'], t['layer'], x, y, t['w'], 0.0))
    for v in new_vias:
        for L in span(v):
            if L in ('L2-GND', 'L5-VCC3V3'):
                continue
            pts.append((v['net'], L, v['x'], v['y'], 9.0, v['size'] / 2))
    add, seen = [], set()
    for net, L, x, y, w, tol in pts:
        for o in by.get((net, L), []):
            if any(math.hypot(x - a, y - b) <= JOIN * 0.5 for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2']))):
                continue
            near = [(a, b) for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])) if tol == 0 and math.hypot(x - a, y - b) <= 0.02]
            if near:
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
                add.append({'net': net, 'layer': L, 'w': min(w, o['w']), 'x1': round(x, 4), 'y1': round(y, 4),
                            'x2': q[0], 'y2': q[1]})
    return add
