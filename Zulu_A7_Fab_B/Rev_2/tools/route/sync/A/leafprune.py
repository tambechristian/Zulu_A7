"""leafprune.py: dead BRANCHES that prune_stubs cannot see.

prune_stubs judges every track end and via on its own: a 0.035 mm track that lies inside a via land is 'live' (its end
is on the via), and the via is 'live' (it touches two tracks), so a whole unterminated branch that ends in such a
via + crumb survives (a 25 mm UART_FT_TXD tail did). Here each net is a graph: pads and the net's plane are terminals,
tracks and via stacks (coincident vias of one net) are nodes, an edge is galvanic contact on a shared layer
(exact gap <= 1e-4). Non-terminal nodes of degree <= 1 are removed to a fixpoint: every branch that does not lead
from a terminal to another terminal goes, cycles stay.

    python leafprune.py <model.json> [nets,comma,separated]     prints the leaves (the dead branches)
    as a module: leaves(M, nets=None) -> (dead_tracks, dead_vias)
"""
import json
import math
import os
import sys
from collections import defaultdict

A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(A), 'prep', 'scripts'))
import geo  # noqa: E402

J = geo.J
CELL = 0.5


def leaves(M, nets=None):
    planes = M.get('planes', {})
    by = defaultdict(lambda: {'p': [], 't': [], 'v': []})
    for p in M['pads']:
        if p['net'] and (nets is None or p['net'] in nets):
            by[p['net']]['p'].append(p)
    for t in M['tracks']:
        if nets is None or t['net'] in nets:
            by[t['net']]['t'].append(t)
    for v in M['vias']:
        if nets is None or v['net'] in nets:
            by[v['net']]['v'].append(v)
    dead_t, dead_v = [], []
    for net, d in by.items():
        if not d['t'] and not d['v']:
            continue
        nodes = []                                    # (kind, obj or list of vias, layers, terminal)
        for p in d['p']:
            nodes.append(('p', p, set(J.pad_layers(p)), True))
        for t in d['t']:
            nodes.append(('t', t, {t['layer']}, False))
        stacks = defaultdict(list)
        for v in d['v']:
            stacks[(round(v['x'], 4), round(v['y'], 4))].append(v)
        for vs in stacks.values():
            ls = set(l for v in vs for l in J.span(v))
            nodes.append(('s', vs, ls, False))
        plane_layers = {l for l, n in planes.items() if n == net}
        grid = defaultdict(list)

        def box(n):
            k, o = n[0], n[1]
            if k == 's':
                r = max(v['size'] for v in o) / 2
                return o[0]['x'] - r, o[0]['y'] - r, o[0]['x'] + r, o[0]['y'] + r
            return J.bbox(k, o)
        for i, n in enumerate(nodes):
            x0, y0, x1, y1 = box(n)
            for gx in range(int(math.floor((x0 - 0.01) / CELL)), int(math.floor((x1 + 0.01) / CELL)) + 1):
                for gy in range(int(math.floor((y0 - 0.01) / CELL)), int(math.floor((y1 + 0.01) / CELL)) + 1):
                    grid[(gx, gy)].append(i)
        adj = defaultdict(set)

        def gap(a, b):
            ka, oa = a[0], a[1]
            kb, ob = b[0], b[1]
            best = 9e9
            la = oa if ka == 's' else [oa]
            lb = ob if kb == 's' else [ob]
            for x in la:
                for y in lb:
                    kx = 'v' if ka == 's' else ka
                    ky = 'v' if kb == 's' else kb
                    lx = set(J.span(x)) if kx == 'v' else a[2]
                    ly = set(J.span(y)) if ky == 'v' else b[2]
                    if not lx & ly:
                        continue
                    best = min(best, J.gap(kx, x, ky, y))
            return best
        seen = set()
        for cell in grid.values():
            for ai in range(len(cell)):
                for bi in range(ai + 1, len(cell)):
                    i, j = cell[ai], cell[bi]
                    if (i, j) in seen:
                        continue
                    seen.add((i, j))
                    if not nodes[i][2] & nodes[j][2]:
                        continue
                    if nodes[i][0] == 'p' and nodes[j][0] == 'p':
                        continue
                    if gap(nodes[i], nodes[j]) <= 1e-4:
                        adj[i].add(j)
                        adj[j].add(i)
        alive = set(range(len(nodes)))
        term = {i for i, n in enumerate(nodes) if n[3] or (n[0] == 's' and n[2] & plane_layers)}
        changed = True
        while changed:
            changed = False
            for i in list(alive):
                if i in term:
                    continue
                if len(adj[i] & alive) <= 1:
                    alive.discard(i)
                    changed = True
        for i, n in enumerate(nodes):
            if i in alive:
                continue
            if n[0] == 't':
                dead_t.append(n[1])
            elif n[0] == 's':
                dead_v.extend(n[1])
    return dead_t, dead_v


def main():
    M = json.load(open(sys.argv[1]))
    nets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
    dt, dv = leaves(M, nets)
    for t in dt:
        print('T', J.desc('t', t))
    for v in dv:
        print('V', J.desc('v', dict(v, span=J.span(v))))
    print('%d dead tracks, %d dead vias (leaf branches)' % (len(dt), len(dv)))


if __name__ == '__main__':
    main()


def crumbs(M, nets=None):
    """tracks whose both ends lie inside ONE same-net via land (on the track's layer) and which touch no other same-net
    object on that layer: copper that connects nothing (prune_stubs calls both ends 'live' because they are on the via)"""
    vias = defaultdict(list)
    for v in M['vias']:
        if nets is None or v['net'] in nets:
            vias[v['net']].append(v)
    tr = defaultdict(list)
    for t in M['tracks']:
        tr[(t['net'], t['layer'])].append(t)
    pads = defaultdict(list)
    for p in M['pads']:
        pads[p['net']].append(p)
    out = []
    for t in M['tracks']:
        if nets is not None and t['net'] not in nets:
            continue
        host = None
        for v in vias.get(t['net'], ()):
            if t['layer'] not in J.span(v):
                continue
            r = v['size'] / 2 + 1e-4
            if all(math.hypot(x - v['x'], y - v['y']) <= r for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2']))):
                host = v
                break
        if host is None:
            continue
        others = [o for o in tr[(t['net'], t['layer'])] if o is not t and J.gap('t', t, 't', o) <= 1e-4]
        others += [p for p in pads.get(t['net'], ()) if t['layer'] in J.pad_layers(p) and J.gap('p', p, 't', t) <= 1e-4]
        if not others:
            out.append(t)
    return out
