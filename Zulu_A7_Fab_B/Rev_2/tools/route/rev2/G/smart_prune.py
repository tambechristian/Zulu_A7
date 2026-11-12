"""smart_prune.py <base_moved.json> <rip.json> <route.json> <out_rip.json> <out_route.json>
prune_stubs.analyse trims a dead-ended track back only to track / via junctions on its centreline. A moved land
sitting on the BODY of its own net's old track (or a router end a hair off a centreline) is not such a junction, so
whole chains die and connections reopen. This runs the same fixpoint with one more trim target:
  * the middle of every stretch of the track's centreline that lies inside a same-net pad on its layer;
A track with both ends free is kept between its outermost targets when they are two different features.
(Off-centreline T-junctions are B/augment.py's job: it adds a connector to the centreline before this runs.)
Dead board copper goes to the rip, dead plan copper leaves the plan, trimmed tracks are re-added; compose_plan.py's
own prune then has nothing left to do, and every kept end lies on a pad, a via or another track."""
import json
import math
import sys

T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, T)
import compose_plan as CP  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

EPS = PS.EPS


def pad_ks(t, pads):
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L = math.hypot(dx, dy)
    n = max(2, int(L / 0.002))
    out = []
    for p in pads:
        inside = [i / n for i in range(n + 1) if C.pad_point(p, t['x1'] + dx * i / n, t['y1'] + dy * i / n) <= 0]
        if inside:
            out.append(((min(inside) + max(inside)) / 2, ('p', id(p))))
    return out


def body_ks(t, others, stk):
    """junction parameters on t's centreline (as prune_stubs: other track ends / via centres ON it)"""
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L2 = dx * dx + dy * dy
    out = []
    for o in others:
        if o is t:
            continue
        for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])):
            if PS.seg_d(a, b, t) <= EPS:
                out.append((((a - t['x1']) * dx + (b - t['y1']) * dy) / L2, ('t', id(o))))
    for k, vs, ls, sz in stk:
        if k[0] == t['net'] and t['layer'] in ls and PS.seg_d(k[1], k[2], t) <= EPS:
            out.append((((k[1] - t['x1']) * dx + (k[2] - t['y1']) * dy) / L2, ('v', k)))
    return [(max(0.0, min(1.0, k)), f) for k, f in out]


def analyse(M):
    planes = M.get('planes', {})
    pads_by = {}
    for p in M['pads']:
        if p['net']:
            for L in (p['layers'] or (PS.STACK if p['drill'] else [])):
                pads_by.setdefault((p['net'], L), []).append(p)
    tracks, vias = list(M['tracks']), list(M['vias'])
    dead_t, dead_v = [], []
    while True:
        stacks = {}
        for v in vias:
            stacks.setdefault((v['net'], round(v['x'], 4), round(v['y'], 4)), []).append(v)
        stk = [(k, vs, set(L for v in vs for L in PS.span(v)), max(v['size'] for v in vs)) for k, vs in stacks.items()]
        by = {}
        for t in tracks:
            by.setdefault((t['net'], t['layer']), []).append(t)

        def on_pad(net, L, x, y):
            return any(C.pad_point(p, x, y) <= EPS for p in pads_by.get((net, L), []))

        def on_via(net, L, x, y):
            return any(k[0] == net and L in ls and math.hypot(k[1] - x, k[2] - y) <= sz / 2 + EPS for k, vs, ls, sz in stk)

        nt = []
        changed = False
        for t in tracks:
            free = [i for i, (x, y) in enumerate(((t['x1'], t['y1']), (t['x2'], t['y2'])))
                    if not (on_pad(t['net'], t['layer'], x, y) or on_via(t['net'], t['layer'], x, y) or
                            any(o is not t and PS.joins(x, y, o, t) for o in by[(t['net'], t['layer'])]))]
            if not free:
                nt.append(t)
                continue
            changed = True
            dead_t.append(t)
            dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
            if dx * dx + dy * dy == 0:
                continue
            cand = pad_ks(t, pads_by.get((t['net'], t['layer']), [])) + body_ks(t, by[(t['net'], t['layer'])], stk)
            ks = [k for k, f in cand]
            if len(free) == 1:
                ks.append(1.0 if free[0] == 0 else 0.0)         # the live end
                feats = 2
            else:
                feats = len({f for k, f in cand})
            if not ks or feats < 2:
                continue
            k0, k1 = min(ks), max(ks)
            if math.hypot(dx, dy) * (k1 - k0) < 0.002:
                continue
            nt.append(dict(t, x1=round(t['x1'] + k0 * dx, 5), y1=round(t['y1'] + k0 * dy, 5),
                           x2=round(t['x1'] + k1 * dx, 5), y2=round(t['y1'] + k1 * dy, 5), trimmed=True))
        nv = []
        for k, vs, ls, sz in stk:
            net, x, y = k
            n = 0
            for L in ls:
                n += (planes.get(L) == net) + on_pad(net, L, x, y) + sum(
                    1 for o in by.get((net, L), []) if PS.seg_d(x, y, o) <= sz / 2 + o['w'] / 2 + EPS)
            if n < 2:
                dead_v.extend(vs)
                changed = True
                continue
            for e in vs:
                ne = sum(1 for o in vs if o is not e and set(PS.span(o)) & set(PS.span(e)))
                for L in PS.span(e):
                    ne += (planes.get(L) == net) + on_pad(net, L, x, y) + sum(
                        1 for o in by.get((net, L), []) if PS.seg_d(x, y, o) <= sz / 2 + o['w'] / 2 + EPS)
                if ne >= 2 or len(vs) == 1:
                    nv.append(e)
                else:
                    dead_v.append(e)
                    changed = True
        tracks, vias = nt, nv
        if not changed:
            return dead_t, dead_v, tracks, vias


def main():
    base, rip, rt = (json.load(open(a)) for a in sys.argv[1:4])
    M = CP.apply(base, dict(rip, tracks=rt['tracks'], vias=rt['vias']))
    bt = {id(t) for t in M['tracks'][:len(M['tracks']) - len(rt['tracks'])]}      # board-origin objects
    bv = {id(v) for v in M['vias'][:len(M['vias']) - len(rt['vias'])]}
    dt, dv, nt, nv = analyse(M)
    plan_t = [t for t in nt if id(t) not in bt]                                  # plan tracks + trimmed copies
    rip2 = dict(rip)
    rip2['remove'] = rip['remove'] + [t for t in dt if id(t) in bt]
    rip2['remove_vias'] = rip['remove_vias'] + [v for v in dv if id(v) in bv]
    keep_v = [v for v in nv if id(v) not in bv]
    out = {'tracks': [{k: v for k, v in t.items() if k not in ('trimmed',)} for t in plan_t],
           'vias': [{k: v for k, v in v.items() if k != 'span'} | {'from': PS.span(v)[0], 'to': PS.span(v)[-1]} for v in keep_v],
           'remove': [], 'remove_vias': []}
    json.dump(rip2, open(sys.argv[4], 'w'))
    json.dump(out, open(sys.argv[5], 'w'))
    ntrim = sum(1 for t in nt if t.get('trimmed'))
    print('smart_prune: %d dead tracks, %d dead vias, %d trimmed; rip %d+%d, plan %d tracks %d vias' % (
        len(dt), len(dv), ntrim, len(rip2['remove']), len(rip2['remove_vias']), len(out['tracks']), len(out['vias'])))


if __name__ == '__main__':
    main()
