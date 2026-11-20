"""smooth.py <plan.json> <routing_only.json> <out_plan.json>

String-pull the Strategy-A routing (router + hand) tracks with EXACT checks: the grid router leaves 0.025 mm
staircases where its raster was tight. Per net and layer, the routing tracks form chains between anchors (a point
is interior only when exactly two chain segments meet there and no pad, via land or other same-net track touches it).
Each chain is replaced greedily by the fewest straight segments between its own points whose exact clearance to every
other-net object (geo.problems: router.clearance with SDRAM-D0..15, edge, width) is at least the rule + 0.001 mm.
Chain ends never move, so connectivity is unchanged. Transplant copper is never touched.
"""
import json
import math
import os
import sys
from collections import defaultdict

A = os.path.dirname(os.path.abspath(__file__))
PREP = os.path.join(os.path.dirname(A), 'prep')
sys.path.insert(0, os.path.join(PREP, 'scripts'))
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import geo  # noqa: E402
import compose_plan as CP  # noqa: E402

J, C, R = geo.J, geo.C, geo.R
MARGIN = 0.001


def pk(x, y):
    return (round(x, 4), round(y, 4))


def ok(t, idx, board):
    if geo.problems('t', t, idx, board):
        return False
    # margin: re-test with the clearance bumped
    net = t['net']
    for k2, q, _ in idx.near('t', t, t['layer']):
        n2 = q.get('net') or ''
        if net and n2 == net:
            continue
        clr = max(R.clearance(net, t['layer']), R.clearance(n2, t['layer']))
        if J.gap('t', t, k2, q) < clr + MARGIN:
            return False
    return True


def main():
    P = json.load(open(sys.argv[1]))
    RO = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    base = json.load(open(os.path.join(PREP, 'base_new.json')))
    M = CP.apply(base, P)
    for v in M['vias']:
        v['span'] = J.span(v)
    rk = {CP.tkey(t) for t in RO['tracks']}
    group = [t for t in P['tracks'] if CP.tkey(t) in rk]
    others = [t for t in M['tracks'] if CP.tkey(t) not in rk]
    idx = geo.Index()
    for p in M['pads']:
        idx.add('p', p)
    for t in others:
        idx.add('t', t)
    for v in M['vias']:
        idx.add('v', v)
    by = defaultdict(list)
    for t in group:
        by[(t['net'], t['layer'], round(t['w'], 4))].append(t)
    new_tracks, n_before, n_after, L_before, L_after = [], 0, 0, 0.0, 0.0
    for (net, layer, w), ts in sorted(by.items()):
        adj = defaultdict(list)
        for i, t in enumerate(ts):
            a, b = pk(t['x1'], t['y1']), pk(t['x2'], t['y2'])
            adj[a].append((i, b))
            adj[b].append((i, a))

        def anchored(p):
            if len(adj[p]) != 2:
                return True
            x, y = p
            for v in M['vias']:
                if v['net'] == net and layer in v['span'] and math.hypot(v['x'] - x, v['y'] - y) <= v['size'] / 2 + 1e-4:
                    return True
            for q in M['pads']:
                if q['net'] == net and layer in J.pad_layers(q) and C.pad_point(q, x, y) <= w / 2 + 1e-4:
                    return True
            for o in others:
                if o['net'] == net and o['layer'] == layer and C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) <= o['w'] / 2 + w / 2 + 1e-4:
                    return True
            return False
        anchors = {p for p in adj if anchored(p)}
        used = set()
        chains = []
        for s in sorted(anchors):
            for i, nb in adj[s]:
                if i in used:
                    continue
                pts, segs = [s], [i]
                used.add(i)
                cur = nb
                while cur not in anchors:
                    pts.append(cur)
                    nxt = [(j, q) for j, q in adj[cur] if j not in used]
                    if not nxt:
                        break
                    j, q = nxt[0]
                    used.add(j)
                    segs.append(j)
                    cur = q
                pts.append(cur)
                chains.append((pts, segs))
        for i, t in enumerate(ts):                    # closed loops without an anchor: keep as they are
            if i not in used:
                new_tracks.append(t)
        for pts, segs in chains:
            n_before += len(segs)
            L_before += sum(J.tlen(ts[j]) for j in segs)
            keep = [pts[0]]
            i = 0
            while i < len(pts) - 1:
                best = i + 1
                for j in range(len(pts) - 1, i + 1, -1):
                    t = {'net': net, 'layer': layer, 'w': w, 'x1': pts[i][0], 'y1': pts[i][1], 'x2': pts[j][0],
                         'y2': pts[j][1]}
                    if ok(t, idx, M['board']):
                        best = j
                        break
                keep.append(pts[best])
                i = best
            if len(keep) - 1 >= len(segs):
                for j in segs:
                    new_tracks.append(ts[j])
                n_after += len(segs)
                L_after += sum(J.tlen(ts[j]) for j in segs)
                continue
            for a, b in zip(keep, keep[1:]):
                t = {'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
                new_tracks.append(t)
                n_after += 1
                L_after += J.tlen(t)
    P2 = dict(P)
    P2['tracks'] = [t for t in P['tracks'] if CP.tkey(t) not in rk] + new_tracks
    json.dump(P2, open(out, 'w'), indent=1)
    print('smoothed routing tracks: %d -> %d segments, %.2f -> %.2f mm' % (n_before, n_after, L_before, L_after))


if __name__ == '__main__':
    main()
