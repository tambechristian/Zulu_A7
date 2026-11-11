"""SDRAM bus layer plan (2026-10-25): give every two-ended SDRAM net a layer so that no two nets on the same layer
must cross, judged by their order across the U1-U3 corridor.

    python tools/sdram_layers.py          reads tools/route/model.json, writes tools/route/sdram_layers.json

Each net's U1-side end is the easternmost point of its U1 island (the stage-1 escape), its U3 end the U3 ball.
Two nets cross if their y order at U1 differs from their y order at U3. Nets are coloured most-constrained first
onto L3-SIG, L4-SIG, then Top Layer (Bottom is crowded with decaps under U3). The router then routes each net
with its layer cost 1.0, Top 4.0 when Top is not its layer (the stubs and balls are on Top), the other inner
layer 8.0 and Bottom 12.0 (router.py --layers).
"""
import collections
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402


def main():
    M = json.load(open(os.path.join(HERE, 'route', 'model.json')))
    I = C.islands(M)
    nets = []
    for n in sorted(R.SDRAM):
        gs = I.get(n, [])
        if len(gs) != 2:
            continue
        g3 = [g for g in gs if any(M['pads'][i]['ref'] == 'U3' for i in g['pads'])]
        if not g3:
            continue
        g3 = g3[0]
        g1 = [g for g in gs if g is not g3][0]
        pts = [(M['tracks'][i]['x1'], M['tracks'][i]['y1']) for i in g1['tracks']]
        pts += [(M['tracks'][i]['x2'], M['tracks'][i]['y2']) for i in g1['tracks']]
        pts += [(M['vias'][i]['x'], M['vias'][i]['y']) for i in g1['vias']]
        pts += [(M['pads'][i]['x'], M['pads'][i]['y']) for i in g1['pads']]
        e = max(pts)
        p3 = M['pads'][g3['pads'][0]]
        nets.append((n, e[0], e[1], p3['x'], p3['y']))
    cross = collections.defaultdict(set)
    for a, b in itertools.combinations(nets, 2):
        if (a[2] - b[2]) * (a[4] - b[4]) < 0:
            cross[a[0]].add(b[0])
            cross[b[0]].add(a[0])
    col = {}
    for t in sorted(nets, key=lambda t: -len(cross[t[0]])):
        used = {col[o] for o in cross[t[0]] if o in col}
        col[t[0]] = next((l for l in ('L3-SIG', 'L4-SIG', 'Top Layer', 'Bottom Layer') if l not in used), None)
    same = sum(1 for a in col for b in cross[a] if col[a] == col[b]) // 2
    cost = {}
    for n, l in col.items():
        c = {'Top Layer': 4.0, 'L3-SIG': 8.0, 'L4-SIG': 8.0, 'Bottom Layer': 12.0}
        if l:
            c[l] = 1.0
        if l == 'L3-SIG':
            c['L4-SIG'] = 8.0
        cost[n] = c
    out = {'crossing_pairs': sum(len(v) for v in cross.values()) // 2, 'same_layer_crossings': same,
           'layer': col, 'cost': cost,
           'ends': {n: {'u1': [x1, y1], 'u3': [x3, y3]} for n, x1, y1, x3, y3 in nets}}
    json.dump(out, open(os.path.join(HERE, 'route', 'sdram_layers.json'), 'w'), indent=1)
    print('%d nets, %d crossing pairs, %d same-layer crossings left; %s' % (
        len(nets), out['crossing_pairs'], same, dict(collections.Counter(col.values()))))


if __name__ == '__main__':
    main()
