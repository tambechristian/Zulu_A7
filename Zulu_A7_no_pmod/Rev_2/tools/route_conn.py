"""Connectivity of tools/route/model.json, the way Altium judges it: copper that overlaps on a shared layer is
joined; a via joins every layer of its span; the L2 pour joins every GND via or through-hole pad that reaches L2,
and the L5 pour every VCC3V3 one that reaches L5.

    python tools/route_conn.py [model.json]        prints the open connections per net (islands with a pad - 1)

As a module: islands(model) -> {net: [island, ...]}, each island a dict {pads, tracks, vias, plane} of indexes
into the model lists (plane True when it reaches the net's pour). Pads of U1 and U3 (BGA lands) are circles.
"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROUND = ('U1',)            # Zulu Fab B: U3 is the TSOP-54 SDRAM (rectangular lands)
EPS = 1e-4


def seg_dist(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def seg_seg(a, b):
    """distance between two segments (x1, y1, x2, y2)"""
    def inter(p, q):
        def cr(o, a_, b_):
            return (a_[0] - o[0]) * (b_[1] - o[1]) - (a_[1] - o[1]) * (b_[0] - o[0])
        p1, p2, q1, q2 = (p[0], p[1]), (p[2], p[3]), (q[0], q[1]), (q[2], q[3])
        d1, d2, d3, d4 = cr(q1, q2, p1), cr(q1, q2, p2), cr(p1, p2, q1), cr(p1, p2, q2)
        return d1 * d2 < 0 and d3 * d4 < 0
    if inter(a, b):
        return 0.0
    return min(seg_dist(b[0], b[1], b[2], b[3], a[0], a[1]), seg_dist(b[0], b[1], b[2], b[3], a[2], a[3]),
               seg_dist(a[0], a[1], a[2], a[3], b[0], b[1]), seg_dist(a[0], a[1], a[2], a[3], b[2], b[3]))


def pad_round(p):
    return p['shape'] == 'circle' or p['ref'] in ROUND


def pad_point(p, x, y):
    """distance from a point to pad copper (0 inside)"""
    if pad_round(p):
        return max(0.0, math.hypot(x - p['x'], y - p['y']) - min(p['w'], p['h']) / 2)
    return math.hypot(max(abs(x - p['x']) - p['w'] / 2, 0), max(abs(y - p['y']) - p['h'] / 2, 0))


def pad_seg(p, s):
    """distance from a segment to pad copper (0 if touching)"""
    if pad_round(p):
        return max(0.0, seg_dist(s[0], s[1], s[2], s[3], p['x'], p['y']) - min(p['w'], p['h']) / 2)
    lx, ly, hx, hy = p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2
    if lx <= s[0] <= hx and ly <= s[1] <= hy or lx <= s[2] <= hx and ly <= s[3] <= hy:
        return 0.0
    edges = [(lx, ly, hx, ly), (hx, ly, hx, hy), (hx, hy, lx, hy), (lx, hy, lx, ly)]
    return min(seg_seg(s, e) for e in edges)


def islands(M):
    pads, tracks, vias = M['pads'], M['tracks'], M['vias']
    plane_of = {net: lay for lay, net in M['planes'].items()}
    by = defaultdict(lambda: ([], [], []))
    for i, p in enumerate(pads):
        if p['net']:
            by[p['net']][0].append(i)
    for i, t in enumerate(tracks):
        by[t['net']][1].append(i)
    for i, v in enumerate(vias):
        by[v['net']][2].append(i)
    out = {}
    for net, (P, T, V) in by.items():
        nodes = [('p', i) for i in P] + [('t', i) for i in T] + [('v', i) for i in V]
        parent = list(range(len(nodes) + 1))          # last node = the net's pour
        PLANE = len(nodes)

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def union(a, b):
            parent[find(a)] = find(b)

        def layers(n):
            k, i = n
            if k == 'p':
                return set(pads[i]['layers'])
            if k == 't':
                return {tracks[i]['layer']}
            return set(vias[i]['span'])

        def touch(a, b):
            if not (layers(a) & layers(b)):
                return False
            (ka, ia), (kb, ib) = a, b
            if ka > kb:
                (ka, ia), (kb, ib) = (kb, ib), (ka, ia)
            if ka == 'p' and kb == 'p':
                pa, pb = pads[ia], pads[ib]
                return abs(pa['x'] - pb['x']) < (pa['w'] + pb['w']) / 2 and abs(pa['y'] - pb['y']) < (pa['h'] + pb['h']) / 2
            if ka == 'p' and kb == 't':
                t = tracks[ib]
                return pad_seg(pads[ia], (t['x1'], t['y1'], t['x2'], t['y2'])) <= t['w'] / 2 + EPS
            if ka == 'p' and kb == 'v':
                v = vias[ib]
                return pad_point(pads[ia], v['x'], v['y']) <= v['size'] / 2 + EPS
            if ka == 't' and kb == 't':
                a_, b_ = tracks[ia], tracks[ib]
                return seg_seg((a_['x1'], a_['y1'], a_['x2'], a_['y2']),
                               (b_['x1'], b_['y1'], b_['x2'], b_['y2'])) <= (a_['w'] + b_['w']) / 2 + EPS
            if ka == 't' and kb == 'v':
                t, v = tracks[ia], vias[ib]
                return seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= (t['w'] + v['size']) / 2 + EPS
            v1, v2 = vias[ia], vias[ib]
            return math.hypot(v1['x'] - v2['x'], v1['y'] - v2['y']) <= (v1['size'] + v2['size']) / 2 + EPS

        # bucket by 1 mm cells to limit pair tests
        def bbox(n):
            k, i = n
            if k == 'p':
                p = pads[i]
                return p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2
            if k == 't':
                t = tracks[i]
                r = t['w'] / 2
                return min(t['x1'], t['x2']) - r, min(t['y1'], t['y2']) - r, max(t['x1'], t['x2']) + r, max(t['y1'], t['y2']) + r
            v = vias[i]
            r = v['size'] / 2
            return v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r
        grid = defaultdict(list)
        for j, n in enumerate(nodes):
            x0, y0, x1, y1 = bbox(n)
            for gx in range(int(math.floor(x0)), int(math.floor(x1)) + 1):
                for gy in range(int(math.floor(y0)), int(math.floor(y1)) + 1):
                    grid[(gx, gy)].append(j)
        seen = set()
        for cell in grid.values():
            for a in range(len(cell)):
                for b in range(a + 1, len(cell)):
                    ja, jb = cell[a], cell[b]
                    key = (ja, jb) if ja < jb else (jb, ja)
                    if key in seen:
                        continue
                    seen.add(key)
                    if touch(nodes[ja], nodes[jb]):
                        union(ja, jb)
        pl = plane_of.get(net)
        if pl:
            for j, n in enumerate(nodes):
                if pl in layers(n) and (n[0] == 'v' or (n[0] == 'p' and len(pads[n[1]]['layers']) > 2)):
                    union(j, PLANE)
        groups = defaultdict(lambda: {'pads': [], 'tracks': [], 'vias': [], 'plane': False})
        for j, n in enumerate(nodes):
            g = groups[find(j)]
            g[{'p': 'pads', 't': 'tracks', 'v': 'vias'}[n[0]]].append(n[1])
        if pl:
            groups[find(PLANE)]['plane'] = True
        out[net] = [g for g in groups.values() if g['pads'] or g['plane']]
    return out


def open_count(isl):
    return {net: len(gs) - 1 for net, gs in isl.items() if len(gs) > 1}


def main():
    M = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'route', 'model.json')))
    oc = open_count(islands(M))
    print('open connections %d on %d nets' % (sum(oc.values()), len(oc)))
    print(', '.join('%s %d' % kv for kv in sorted(oc.items(), key=lambda kv: -kv[1])))


if __name__ == '__main__':
    main()
