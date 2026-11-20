"""deadbranch.py: dead branches on an endpoint graph (what prune_stubs misses).

prune_stubs judges each track end / via alone, so a dead branch survives when it ends in a via whose land holds two
short segments of the branch itself (the via 'touches two tracks', each segment end is 'on the via'). A 25 mm
UART_FT_TXD tail of the transplant stubs did exactly that. Here every net is a graph:

  nodes  pads (terminals); via stacks (coincident vias of one net; terminal when a layer of the stack is the net's
         plane); junctions (track ends that coincide within JOIN, or that land on another track's interior, which
         splits that track there)
  edges  each track (or piece of a split track) between the nodes of its two ends; a track end that lies inside a
         via land (on a layer of the stack) or a pad belongs to that via / pad node; a via land overlapping a pad of
         its net, or another stack's land, on a shared layer, is an attachment edge
  prune  self-loops (a segment with both ends on one node) and every edge at a non-terminal node of degree <= 1, to a
         fixpoint; a via stack left with degree 0 is dead. A track is dead when all its pieces are; when only some
         are, it is reported as a trim (kept span between the outermost live pieces).

    python deadbranch.py <model.json> [net,net]     prints dead tracks / vias / trims
    module: analyse(M, nets=None) -> (dead_tracks, dead_vias, trims[(track, new_track)])
"""
import json
import math
import os
import sys
from collections import defaultdict

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(A), 'prep', 'scripts'))
import geo  # noqa: E402

J, C = geo.J, geo.C
JOIN = 0.01
SKIP_LOOPS = False                  # True: report only branches, not segments lying inside one pad / via land
EPS = 1e-4


def seg_param(px, py, t):
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L = math.hypot(dx, dy)
    if L == 0:
        return 0.0, math.hypot(px - t['x1'], py - t['y1']), 0.0
    k = ((px - t['x1']) * dx + (py - t['y1']) * dy) / L
    kc = max(0.0, min(L, k))
    return kc, math.hypot(px - t['x1'] - kc * dx / L, py - t['y1'] - kc * dy / L), L


def analyse_net(net, pads, tracks, vias, plane_layers):
    stacks = defaultdict(list)
    for v in vias:
        stacks[(round(v['x'], 4), round(v['y'], 4))].append(v)
    S = []                                            # (x, y, r, layers, vias)
    for (x, y), vs in stacks.items():
        S.append((x, y, max(v['size'] for v in vs) / 2, set(l for v in vs for l in J.span(v)), vs))
    nid = {}
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    def node(key):
        if key not in parent:
            parent[key] = key
        return key
    term = set()
    for i, p in enumerate(pads):
        term.add(node(('p', i)))
    for i, s in enumerate(S):
        node(('s', i))
        if s[3] & plane_layers:
            term.add(('s', i))
    # endpoints
    ends = []                                         # (track index, which end, x, y, layer)
    for ti, t in enumerate(tracks):
        for e, (x, y) in enumerate(((t['x1'], t['y1']), (t['x2'], t['y2']))):
            ends.append((ti, e, x, y, t['layer']))
            node(('e', ti, e))
    by_layer = defaultdict(list)
    for ti, t in enumerate(tracks):
        by_layer[t['layer']].append(ti)
    splits = defaultdict(list)                        # track index -> [(param, node key)]
    attach = set()                                    # attachment edges between distinct base nodes (via-pad, via-via)
    for ti, e, x, y, l in ends:
        me = ('e', ti, e)
        # inside a via land on this layer -> that stack
        best = None
        for si, s in enumerate(S):
            if l in s[3]:
                d = math.hypot(x - s[0], y - s[1])
                if d <= s[2] + EPS and (best is None or d < best[0]):
                    best = (d, si)
        if best:
            union(('s', best[1]), me)
            continue
        hit = None
        for pi, p in enumerate(pads):
            if l in J.pad_layers(p) and C.pad_point(p, x, y) <= EPS:
                hit = pi
                break
        if hit is not None:
            union(('p', hit), me)
            continue
        for tj in by_layer[l]:
            if tj == ti:
                continue
            o = tracks[tj]
            for e2, (a, b) in enumerate(((o['x1'], o['y1']), (o['x2'], o['y2']))):
                if math.hypot(x - a, y - b) <= JOIN:
                    union(('e', tj, e2), me)
            k, d, L = seg_param(x, y, o)
            if d <= o['w'] / 2 + EPS and JOIN < k < L - JOIN:
                key = ('j', tj, round(k, 5))
                node(key)
                union(key, me)
                splits[tj].append((k, key))
    # a via land overlapping a pad of the net / another stack, on a shared layer
    for si, s in enumerate(S):
        for pi, p in enumerate(pads):
            if s[3] & set(J.pad_layers(p)) and C.pad_point(p, s[0], s[1]) <= s[2] + EPS:
                attach.add((('s', si), ('p', pi)))
        for sj in range(si + 1, len(S)):
            o = S[sj]
            if s[3] & o[3] and math.hypot(s[0] - o[0], s[1] - o[1]) <= s[2] + o[2] + EPS:
                attach.add((('s', si), ('s', sj)))
        # a track passing over a via land (no end there): split the track at the via
        for tj in range(len(tracks)):
            o = tracks[tj]
            if o['layer'] not in s[3]:
                continue
            k, d, L = seg_param(s[0], s[1], o)
            if d <= s[2] + o['w'] / 2 + EPS and JOIN < k < L - JOIN:
                key = ('j', tj, round(k, 5))
                node(key)
                union(key, ('s', si))
                splits[tj].append((k, key))
    # edges
    edges = []                                        # (u, v, track index or None, k0, k1)
    for ti, t in enumerate(tracks):
        pts = [(0.0, ('e', ti, 0))] + sorted(splits[ti]) + [(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']), ('e', ti, 1))]
        for (k0, a), (k1, b) in zip(pts, pts[1:]):
            edges.append((a, b, ti, k0, k1))
    for a, b in attach:
        edges.append((a, b, None, 0, 0))
    roots_term = {find(x) for x in term}
    alive = [True] * len(edges)
    loop = [False] * len(edges)
    for i, (a, b, ti, k0, k1) in enumerate(edges):
        if find(a) == find(b):
            alive[i] = False                          # self-loop: connects a node to itself
            loop[i] = True
    changed = True
    while changed:
        changed = False
        deg = defaultdict(int)
        for i, (a, b, ti, k0, k1) in enumerate(edges):
            if alive[i]:
                deg[find(a)] += 1
                deg[find(b)] += 1
        for i, (a, b, ti, k0, k1) in enumerate(edges):
            if not alive[i]:
                continue
            fa, fb = find(a), find(b)
            if (fa not in roots_term and deg[fa] <= 1) or (fb not in roots_term and deg[fb] <= 1):
                alive[i] = False
                deg[fa] -= 1
                deg[fb] -= 1
                changed = True
    deg = defaultdict(int)
    for i, (a, b, ti, k0, k1) in enumerate(edges):
        if alive[i]:
            deg[find(a)] += 1
            deg[find(b)] += 1
    dead_t, trims, dead_v = [], [], []
    per = defaultdict(list)
    for i, (a, b, ti, k0, k1) in enumerate(edges):
        if ti is not None:
            per[ti].append((alive[i], k0, k1, loop[i]))
    for ti, pcs in per.items():
        if not any(p[0] for p in pcs):
            if SKIP_LOOPS and all(p[3] for p in pcs):
                continue                              # only a self-loop (inside one pad / via land): harmless
            dead_t.append(tracks[ti])
        elif not all(p[0] for p in pcs):
            t = tracks[ti]
            lo = min(p[1] for p in pcs if p[0])
            hi = max(p[2] for p in pcs if p[0])
            L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
            ux, uy = (t['x2'] - t['x1']) / L, (t['y2'] - t['y1']) / L
            nt = dict(t, x1=round(t['x1'] + lo * ux, 4), y1=round(t['y1'] + lo * uy, 4),
                      x2=round(t['x1'] + hi * ux, 4), y2=round(t['y1'] + hi * uy, 4))
            trims.append((t, nt))
    for si, s in enumerate(S):
        r = find(('s', si))
        if r in roots_term and ('s', si) in term:
            continue
        if deg[r] == 0 and r not in roots_term:
            dead_v.extend(s[4])
        elif deg[r] == 0 and r in roots_term and ('s', si) not in term:
            # joined to a terminal only through contraction (track ends inside it) with no live edge: dead
            dead_v.extend(s[4])
    return dead_t, dead_v, trims


def analyse(M, nets=None):
    planes = M.get('planes', {})
    P, T, V = defaultdict(list), defaultdict(list), defaultdict(list)
    for p in M['pads']:
        if p['net']:
            P[p['net']].append(p)
    for t in M['tracks']:
        T[t['net']].append(t)
    for v in M['vias']:
        V[v['net']].append(v)
    dt, dv, tr = [], [], []
    for net in sorted(set(T) | set(V)):
        if nets is not None and net not in nets:
            continue
        a, b, c = analyse_net(net, P[net], T[net], V[net], {l for l, n in planes.items() if n == net})
        dt += a
        dv += b
        tr += c
    return dt, dv, tr


def main():
    M = json.load(open(sys.argv[1]))
    nets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
    dt, dv, tr = analyse(M, nets)
    for t in dt:
        print('T', J.desc('t', t))
    for v in dv:
        print('V', J.desc('v', dict(v, span=J.span(v))))
    for t, nt in tr:
        print('TRIM', J.desc('t', t), '->', J.desc('t', nt))
    print('%d dead tracks, %d dead vias, %d trims' % (len(dt), len(dv), len(tr)))


if __name__ == '__main__':
    main()
