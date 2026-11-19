"""aug_h.py -- strategy H joint fixer (F/aug.py generalised, 2026-11-11).

prune_stubs counts a track end live only if its CENTRE lies on a same-net pad, inside a via land, on another track's
centreline band (or within 0.01 of its end). route_conn (and Altium's connectivity) join by copper overlap. Router
and seed ends that join only by overlap (and old copper whose pad moved under its body) get pruned by compose_plan
and the net reopens. fix_all() simulates the prune on the whole board and repairs every free track end, preferring
changes that only shrink copper:
  1. TRIM: walk the track's own centreline from the free end; at the first point that sits inside a same-net pad,
     via land, or another same-net track's band (a joint prune accepts), cut the track there (if that point is
     within 0.02 of the far end the track is deleted instead);
  2. CONNECTOR: if the centreline never gets inside anything but the end disc overlaps a same-net pad / via land /
     track, a short track (same net / layer / width) from the end to the nearest point inside the pad, to the via
     centre, to the other track's end (<= 0.03 away) or to its centreline;
  3. DELETE: a track whose free end overlaps nothing is a dead tail and is deleted (the prune would do it).
Repeated to a fixpoint. Returns the edits as {remove: board tracks, tracks: new tracks}; route_check re-proves them."""
import math
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import route_conn as C  # noqa: E402
import prune_stubs as PS  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
EPS = 1e-4
IN = 0.006           # how far inside a pad / land / band a trimmed end must sit


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def seg_proj(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    k = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return x1 + k * dx, y1 + k * dy, k


def pad_inside(p, x, y, m):
    if C.pad_round(p):
        return math.hypot(x - p['x'], y - p['y']) <= min(p['w'], p['h']) / 2 - m
    return abs(x - p['x']) <= p['w'] / 2 - m and abs(y - p['y']) <= p['h'] / 2 - m


def pad_inner(p, x, y):
    if C.pad_round(p):
        r = max(min(p['w'], p['h']) / 2 - 0.01, 0)
        d = math.hypot(x - p['x'], y - p['y'])
        if d <= r:
            return x, y
        return p['x'] + (x - p['x']) * r / d, p['y'] + (y - p['y']) * r / d
    hx, hy = max(p['w'] / 2 - 0.01, 0), max(p['h'] / 2 - 0.01, 0)
    return min(max(x, p['x'] - hx), p['x'] + hx), min(max(y, p['y'] - hy), p['y'] + hy)


def in_band(px, py, o):
    qx, qy, k = seg_proj(px, py, o)
    Lo = math.hypot(o['x2'] - o['x1'], o['y2'] - o['y1'])
    if math.hypot(qx - px, qy - py) > o['w'] / 2 - IN:
        return False
    if k * Lo > 0.012 and (1 - k) * Lo > 0.012:
        return True
    return any(math.hypot(px - a, py - b) <= 0.008 for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])))


def fix_all(tracks, pads, vias, nets=None, log=None):
    """tracks: the whole board's track list. Returns (removed: list of original track dicts, added: new tracks)."""
    pad_by, via_by = {}, {}
    for p in pads:
        if p['net']:
            for L in (p['layers'] or (STACK if p['drill'] > 0 else [])):
                pad_by.setdefault((p['net'], L), []).append(p)
    for v in vias:
        for L in span(v):
            via_by.setdefault((v['net'], L), []).append(v)
    cur = [dict(t, _o=i) for i, t in enumerate(tracks)]      # _o: index of the original track (None: added)
    changed_o = set()
    for it in range(30):
        by = {}
        for t in cur:
            by.setdefault((t['net'], t['layer']), []).append(t)
        changed = 0
        dead = set()
        add = []
        for t in cur:
            if id(t) in dead:
                continue
            net, L, w = t['net'], t['layer'], t['w']
            if nets is not None and net not in nets:
                continue
            for end in (0, 1):
                x, y = (t['x1'], t['y1']) if end == 0 else (t['x2'], t['y2'])
                ox, oy = (t['x2'], t['y2']) if end == 0 else (t['x1'], t['y1'])
                if any(pad_inside(p, x, y, -EPS) for p in pad_by.get((net, L), [])):
                    continue
                if any(math.hypot(v['x'] - x, v['y'] - y) <= v['size'] / 2 + EPS for v in via_by.get((net, L), [])):
                    continue
                if any(o is not t and id(o) not in dead and PS.joins(x, y, o, t) for o in by.get((net, L), [])):
                    continue
                Lt = math.hypot(ox - x, oy - y)
                n = max(1, int(Lt / 0.002))
                others = [o for o in by.get((net, L), []) if o is not t and id(o) not in dead]
                pads_l = pad_by.get((net, L), [])
                vias_l = via_by.get((net, L), [])
                # objects holding the far end: they do not count as junctions on the body
                fp = [p for p in pads_l if C.pad_point(p, ox, oy) < w / 2]
                fv = [v for v in vias_l if math.hypot(v['x'] - ox, v['y'] - oy) < v['size'] / 2 + w / 2]
                tends = [(o, a, b) for o in others for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2']))
                         if math.hypot(a - ox, b - oy) > w / 2 + o['w'] / 2]
                act = None
                for i in range(0, n + 1):
                    f = i / n
                    px, py = x + (ox - x) * f, y + (oy - y) * f
                    if i > 0 and (any(pad_inside(p, px, py, IN) for p in pads_l) or
                                  any(math.hypot(v['x'] - px, v['y'] - py) <= v['size'] / 2 - IN for v in vias_l) or
                                  any(in_band(px, py, o) for o in others)):
                        act = ('cut', (px, py), None)
                        break
                    q = None
                    for p in pads_l:
                        if p not in fp and C.pad_point(p, px, py) < w / 2 - 0.001:
                            q = pad_inner(p, px, py)
                            break
                    if q is None:
                        for v in vias_l:
                            if v not in fv and math.hypot(v['x'] - px, v['y'] - py) < v['size'] / 2 + w / 2 - 0.001:
                                q = (v['x'], v['y'])
                                break
                    if q is None:
                        for o, a, b in tends:
                            if math.hypot(a - px, b - py) < w / 2 + o['w'] / 2 - 0.001:
                                q = (a, b)
                                break
                    if q is not None:
                        act = ('conn', (px, py), q)
                        break
                if act is None or math.hypot(act[1][0] - ox, act[1][1] - oy) < 0.02:
                    dead.add(id(t))
                    if t['_o'] is not None:
                        changed_o.add(t['_o'])
                    if log is not None:
                        log.append('dead %s %s (%.4f,%.4f)-(%.4f,%.4f)' % (net, L, t['x1'], t['y1'], t['x2'], t['y2']))
                    changed += 1
                    break
                kind, (px, py), q = act
                cut = (round(px, 4), round(py, 4))
                if math.hypot(cut[0] - x, cut[1] - y) > 1e-4:
                    if end == 0:
                        t['x1'], t['y1'] = cut
                    else:
                        t['x2'], t['y2'] = cut
                    if t['_o'] is not None:
                        changed_o.add(t['_o'])
                if q is not None:
                    q = (round(q[0], 4), round(q[1], 4))
                    if math.hypot(q[0] - cut[0], q[1] - cut[1]) >= 1e-4:
                        add.append({'net': net, 'layer': L, 'w': w, 'x1': cut[0], 'y1': cut[1], 'x2': q[0], 'y2': q[1], '_o': None})
                if log is not None:
                    log.append('%s %s %s end (%.4f,%.4f) -> (%.4f,%.4f)%s' % (kind, net, L, x, y, cut[0], cut[1],
                               ' + conn to (%.4f,%.4f)' % q if q else ''))
                changed += 1
                break
        cur = [t for t in cur if id(t) not in dead] + add
        if not changed:
            break
    removed = [tracks[i] for i in sorted(changed_o)]
    added = [{k: v for k, v in t.items() if k != '_o'} for t in cur if t['_o'] is None or t['_o'] in changed_o]
    return removed, added
