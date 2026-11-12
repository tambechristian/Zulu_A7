"""f2_router.py --orphans keys.json [--inpad-micro] <router.py args...>
f_router.py (no via in SMD pads, GND Bottom ties by microvia column) plus ORPHAN ISLANDS: route_conn.islands()
ignores copper that reaches no pad, so the router never re-joins the middle of an old route that a minimal rip
cut on both sides. Every orphan copper group of the model that holds one of the listed track keys
([net, layer, x1, y1, x2, y2], rounded to 1e-4; from pieces.py) is returned as an island of its net too, so the
router joins it like any pad island. Dead-end leftovers are pruned afterwards by compose_plan."""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if '--orphans' in sys.argv:
    k = sys.argv.index('--orphans')
    KEYS = {tuple(x) for x in json.load(open(sys.argv[k + 1]))}
    del sys.argv[k:k + 2]
else:
    KEYS = set()
import f_router  # noqa: E402,F401  (applies the via-in-pad / GND tie patches)
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

EPS = 1e-4
_orig = C.islands


def tkey(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))


def _touch(M, a, b):
    ka, ia = a
    kb, ib = b
    la = {M['tracks'][ia]['layer']} if ka == 't' else set(M['vias'][ia]['span'])
    lb = {M['tracks'][ib]['layer']} if kb == 't' else set(M['vias'][ib]['span'])
    if not la & lb:
        return False
    if ka == 'v' and kb == 't':
        a, b = b, a
        ka, ia, kb, ib = kb, ib, ka, ia
    if ka == 't' and kb == 't':
        s, o = M['tracks'][ia], M['tracks'][ib]
        return C.seg_seg((s['x1'], s['y1'], s['x2'], s['y2']), (o['x1'], o['y1'], o['x2'], o['y2'])) <= (s['w'] + o['w']) / 2 + EPS
    if ka == 't':
        t, v = M['tracks'][ia], M['vias'][ib]
        return C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= (t['w'] + v['size']) / 2 + EPS
    v1, v2 = M['vias'][ia], M['vias'][ib]
    return math.hypot(v1['x'] - v2['x'], v1['y'] - v2['y']) <= (v1['size'] + v2['size']) / 2 + EPS


def islands(M):
    out = _orig(M)
    if not KEYS:
        return out
    used_t = {i for gs in out.values() for g in gs for i in g['tracks']}
    used_v = {i for gs in out.values() for g in gs for i in g['vias']}
    knets = {k[0] for k in KEYS}
    nodes = [('t', i) for i, t in enumerate(M['tracks']) if i not in used_t and t['net'] in knets] + \
            [('v', i) for i, v in enumerate(M['vias']) if i not in used_v and v['net'] in knets]
    par = list(range(len(nodes)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            na = (M['tracks'] if nodes[a][0] == 't' else M['vias'])[nodes[a][1]]['net']
            nb = (M['tracks'] if nodes[b][0] == 't' else M['vias'])[nodes[b][1]]['net']
            if na == nb and _touch(M, nodes[a], nodes[b]):
                par[find(a)] = find(b)
    grp = defaultdict(lambda: {'pads': [], 'tracks': [], 'vias': [], 'plane': False})
    for k, n in enumerate(nodes):
        grp[find(k)]['tracks' if n[0] == 't' else 'vias'].append(n[1])
    for g in grp.values():
        if any(tkey(M['tracks'][i]) in KEYS for i in g['tracks']):
            net = M['tracks'][g['tracks'][0]]['net']
            out.setdefault(net, []).append(g)
    return out


C.islands = islands

if __name__ == '__main__':
    print('f2_router: %d orphan keys' % len(KEYS), flush=True)
    R.main()
