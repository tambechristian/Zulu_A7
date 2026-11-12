"""pieces.py <base_moved.json> <model.json> <rip.json> [--prune out_rip_leaf.json] [--verbose]
Strategy F: after a minimal rip, a net's copper falls into pieces: pad islands (route_conn islands: they reach a pad
or the pour) and ORPHAN pieces (copper with no pad), which route_conn / router.py ignore. An orphan piece between
two cuts still carries most of an old long route, so it is worth re-joining; an orphan piece that only led to a
moved pad's OLD position (or to a removed via) is a dead leaf.
Cut adjacency: the removed copper (rip['remove'] tracks at their original length, rip['remove_vias']), grouped into
clusters of mutually touching items of one net; every piece a cluster touches is adjacent to every other piece it
touches. Orphan pieces of degree <= 1 are pruned iteratively; the rest are 'useful'.
--prune writes the useless orphan copper as a rip step {remove, remove_vias}."""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import route_conn as C  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
EPS = 1e-4


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def all_groups(M):
    """every connected copper group per net (with or without a pad): list of {pads, tracks, vias, plane}"""
    M2 = dict(M)
    # route_conn drops pad-less groups; give every track/via a fake pad-less marker by re-running its union-find
    pads, tracks, vias = M['pads'], M['tracks'], M['vias']
    out = {}
    isl = C.islands(M)
    # pad islands from route_conn, orphans = items not in any of them
    for net, gs in isl.items():
        out[net] = [dict(g, orphan=False) for g in gs]
    used_t = {i for gs in isl.values() for g in gs for i in g['tracks']}
    used_v = {i for gs in isl.values() for g in gs for i in g['vias']}
    ot = [i for i in range(len(tracks)) if i not in used_t]
    ov = [i for i in range(len(vias)) if i not in used_v]
    # group the orphans by touch (same net)
    nodes = [('t', i) for i in ot] + [('v', i) for i in ov]
    parent = list(range(len(nodes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    by_net = defaultdict(list)
    for k, n in enumerate(nodes):
        by_net[(tracks if n[0] == 't' else vias)[n[1]]['net']].append(k)
    for net, ks in by_net.items():
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                if touch_items(M, nodes[ks[a]], nodes[ks[b]]):
                    parent[find(ks[a])] = find(ks[b])
    grp = defaultdict(lambda: {'pads': [], 'tracks': [], 'vias': [], 'plane': False, 'orphan': True})
    for k, n in enumerate(nodes):
        g = grp[find(k)]
        g['tracks' if n[0] == 't' else 'vias'].append(n[1])
    for g in grp.values():
        it = g['tracks'][0] if g['tracks'] else None
        net = tracks[it]['net'] if it is not None else vias[g['vias'][0]]['net']
        out.setdefault(net, []).append(g)
    return out


def item_layers(M, n):
    k, i = n
    if k == 't':
        return {M['tracks'][i]['layer']}
    if k == 'v':
        return set(span(M['vias'][i]))
    p = M['pads'][i]
    return set(p['layers'] or (STACK if p['drill'] else []))


def touch_items(M, a, b):
    if not (item_layers(M, a) & item_layers(M, b)):
        return False
    (ka, ia), (kb, ib) = sorted([a, b])
    if ka == 't' and kb == 't':
        s, o = M['tracks'][ia], M['tracks'][ib]
        return C.seg_seg((s['x1'], s['y1'], s['x2'], s['y2']), (o['x1'], o['y1'], o['x2'], o['y2'])) <= (s['w'] + o['w']) / 2 + EPS
    if ka == 't' and kb == 'v':
        t, v = M['tracks'][ia], M['vias'][ib]
        return C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= (t['w'] + v['size']) / 2 + EPS
    if ka == 'v' and kb == 'v':
        v1, v2 = M['vias'][ia], M['vias'][ib]
        return math.hypot(v1['x'] - v2['x'], v1['y'] - v2['y']) <= (v1['size'] + v2['size']) / 2 + EPS
    raise ValueError


def touch_geom(a, b):
    """a, b: ('t', track dict) / ('v', via dict) / ('p', pad dict)"""
    la = {a[1]['layer']} if a[0] == 't' else set(span(a[1])) if a[0] == 'v' else set(a[1]['layers'] or (STACK if a[1]['drill'] else []))
    lb = {b[1]['layer']} if b[0] == 't' else set(span(b[1])) if b[0] == 'v' else set(b[1]['layers'] or (STACK if b[1]['drill'] else []))
    if not la & lb:
        return False
    (ka, x), (kb, y) = sorted([a, b], key=lambda q: q[0])
    if ka == 'p' and kb == 'p':
        return False
    if ka == 'p' and kb == 't':
        return C.pad_seg(x, (y['x1'], y['y1'], y['x2'], y['y2'])) <= y['w'] / 2 + EPS
    if ka == 'p' and kb == 'v':
        return C.pad_point(x, y['x'], y['y']) <= y['size'] / 2 + EPS
    if ka == 't' and kb == 't':
        return C.seg_seg((x['x1'], x['y1'], x['x2'], x['y2']), (y['x1'], y['y1'], y['x2'], y['y2'])) <= (x['w'] + y['w']) / 2 + EPS
    if ka == 't' and kb == 'v':
        return C.seg_dist(x['x1'], x['y1'], x['x2'], x['y2'], y['x'], y['y']) <= (x['w'] + y['size']) / 2 + EPS
    return math.hypot(x['x'] - y['x'], x['y'] - y['y']) <= (x['size'] + y['size']) / 2 + EPS


def analyse(B, M, rip, verbose=False):
    groups = all_groups(M)
    removed = [('t', t) for t in rip['remove']] + [('v', dict(v, span=span(v))) for v in rip['remove_vias']]
    by_net = defaultdict(list)
    for r in removed:
        by_net[r[1]['net']].append(r)
    result = {}
    for net, rs in by_net.items():
        gs = groups.get(net, [])
        # clusters of removed items
        par = list(range(len(rs)))

        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for a in range(len(rs)):
            for b in range(a + 1, len(rs)):
                if touch_geom(rs[a], rs[b]):
                    par[find(a)] = find(b)
        cl = defaultdict(list)
        for a in range(len(rs)):
            cl[find(a)].append(rs[a])
        adj = defaultdict(set)
        for items in cl.values():
            touched = set()
            for gi, g in enumerate(gs):
                objs = [('t', M['tracks'][i]) for i in g['tracks']] + [('v', M['vias'][i]) for i in g['vias']] + \
                       [('p', M['pads'][i]) for i in g['pads']]
                if any(touch_geom(r, o) for r in items for o in objs):
                    touched.add(gi)
            for a in touched:
                adj[a] |= touched - {a}
        alive = set(range(len(gs)))
        changed = True
        while changed:
            changed = False
            for gi in list(alive):
                if gs[gi]['orphan'] and len(adj[gi] & alive) <= 1:
                    alive.discard(gi)
                    changed = True
        result[net] = (gs, alive, adj)
        if verbose:
            print('=== %s: %d pieces' % (net, len(gs)))
            for gi, g in enumerate(gs):
                pads = ' '.join('%s.%s' % (M['pads'][i]['ref'], M['pads'][i]['pad']) for i in g['pads'][:4])
                pts = [(M['tracks'][i]['x1'], M['tracks'][i]['y1']) for i in g['tracks'][:1]] + \
                      [(M['vias'][i]['x'], M['vias'][i]['y']) for i in g['vias'][:1]]
                print('  piece %d %s %s T%d V%d adj %s %s at %s' % (
                    gi, 'ORPHAN' if g['orphan'] else 'pads[%s]%s' % (pads, ' plane' if g['plane'] else ''),
                    'useful' if gi in alive else 'DEAD', len(g['tracks']), len(g['vias']), sorted(adj[gi]),
                    '', pts[:1]))
    return result, groups


def main():
    args = sys.argv[1:]
    verbose = '--verbose' in args
    if verbose:
        args.remove('--verbose')
    out = None
    if '--prune' in args:
        k = args.index('--prune')
        out = args[k + 1]
        del args[k:k + 2]
    B, M, rip = (json.load(open(a)) for a in args[:3])
    res, groups = analyse(B, M, rip, verbose)
    dead_t, dead_v = [], []
    for net, gs in groups.items():
        alive = res[net][1] if net in res else set(i for i, g in enumerate(gs) if not g['orphan'])
        for gi, g in enumerate(gs):
            if g['orphan'] and gi not in alive:
                dead_t += [M['tracks'][i] for i in g['tracks']]
                dead_v += [M['vias'][i] for i in g['vias']]
    useful = {net: [gi for gi in r[1] if r[0][gi]['orphan']] for net, r in res.items()}
    print('useful orphan pieces:', {k: len(v) for k, v in useful.items() if v})
    print('dead orphan copper: %d tracks %d vias' % (len(dead_t), len(dead_v)))
    if out:
        json.dump({'remove': dead_t, 'remove_vias': [dict({k: v for k, v in d.items() if k != 'span'},
                                                         **{'from': span(d)[0], 'to': span(d)[-1]}) for d in dead_v],
                   'tracks': [], 'vias': []}, open(out, 'w'), indent=0)


if __name__ == '__main__':
    main()
