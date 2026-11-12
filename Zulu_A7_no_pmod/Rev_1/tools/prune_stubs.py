"""Find dead-end copper (Altium 'Net Antennae' + orphan islands) in a router model and prune it to a fixpoint.

    python tools/prune_stubs.py <model.json> [out_plan.json]

A track end is live if it lies on another object of the same net and layer (pad, via, another track's body).
A via (coincident vias of one net are merged into one stack) is live if it touches at least two objects, or one
object plus a plane layer of its own net. Dead tracks / vias are removed and the test repeated until nothing changes.
With out_plan.json, writes {'remove': tracks, 'remove_vias': vias, 'tracks': [], 'vias': []} for emit_copper.
"""
import json
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_conn as C  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
EPS = 1e-4


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def seg_d(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    k = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - x1 - k * dx, py - y1 - k * dy)


JOIN = 0.01     # endpoints closer than this are one junction (router jogs are 0.025 mm; old hand copper is off by 0.005)


def joins(x, y, o, t):
    """Is the end (x, y) of track t joined to track o?  Either o has an endpoint there, or (x, y) lands on o's
    interior (a T-junction).  Merely lying within half a width of o's END is not a join: a 0.025 mm jog segment
    would otherwise make every free end look connected, while Altium flags such a pair as a Net Antenna."""
    if any(math.hypot(x - a, y - b) <= JOIN for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2']))):
        return True
    if seg_d(x, y, o) > o['w'] / 2 + EPS:
        return False
    dx, dy = o['x2'] - o['x1'], o['y2'] - o['y1']
    L = math.hypot(dx, dy)
    if L == 0:
        return False
    k = ((x - o['x1']) * dx + (y - o['y1']) * dy) / L
    return JOIN < k < L - JOIN


def analyse(M):
    planes = M.get('planes', {})
    pads = [p for p in M['pads']]
    tracks = list(M['tracks'])
    vias = list(M['vias'])
    dead_t, dead_v = [], []
    while True:
        stacks = {}
        for v in vias:
            stacks.setdefault((v['net'], round(v['x'], 4), round(v['y'], 4)), []).append(v)
        stk = [(k, vs, set(L for v in vs for L in span(v)), max(v['size'] for v in vs)) for k, vs in stacks.items()]
        by_net_layer = {}
        for t in tracks:
            by_net_layer.setdefault((t['net'], t['layer']), []).append(t)

        def on_pad(net, L, x, y):
            return any(p['net'] == net and (not p['layers'] or L in p['layers']) and C.pad_point(p, x, y) <= EPS
                       for p in pads)

        def on_via(net, L, x, y):
            return any(k[0] == net and L in ls and math.hypot(k[1] - x, k[2] - y) <= sz / 2 + EPS for k, vs, ls, sz in stk)

        nt = []
        for t in tracks:
            free = []
            for i, (x, y) in enumerate(((t['x1'], t['y1']), (t['x2'], t['y2']))):
                live = on_pad(t['net'], t['layer'], x, y) or on_via(t['net'], t['layer'], x, y) or any(
                    o is not t and joins(x, y, o, t) for o in by_net_layer[(t['net'], t['layer'])])
                if not live:
                    free.append(i)
            if not free:
                nt.append(t)
                continue
            dead_t.append(t)
            if len(free) == 2:
                continue
            # one free end: trim back to the farthest junction on the body (other track ends, vias)
            fx, fy = (t['x2'], t['y2']) if free[0] == 0 else (t['x1'], t['y1'])      # live end
            ex, ey = (t['x1'], t['y1']) if free[0] == 0 else (t['x2'], t['y2'])      # free end
            dx, dy = ex - fx, ey - fy
            L2 = dx * dx + dy * dy
            best = 0.0
            cand = [(a, b) for o in by_net_layer[(t['net'], t['layer'])] if o is not t
                    for a, b in ((o['x1'], o['y1']), (o['x2'], o['y2'])) if seg_d(a, b, t) <= t['w'] / 2 + EPS]
            cand += [(k[1], k[2]) for k, vs, ls, sz in stk if k[0] == t['net'] and t['layer'] in ls and seg_d(k[1], k[2], t) <= sz / 2 + EPS]
            snap = None
            ntrk = len(cand) - sum(1 for k in stk if k[0][0] == t['net'] and t['layer'] in k[2] and seg_d(k[0][1], k[0][2], t) <= k[3] / 2 + EPS)
            for ci, (a, b) in enumerate(cand):
                k = ((a - fx) * dx + (b - fy) * dy) / L2
                if 0 < k < 1 and k > best:
                    best = k
                    snap = (a, b) if ci < ntrk else None      # end exactly on the other track's end, or joins() fails
            if best > 0:
                ex2, ey2 = snap if snap else (fx + best * dx, fy + best * dy)
                nt.append(dict(t, x1=round(fx, 4), y1=round(fy, 4), x2=round(ex2, 4), y2=round(ey2, 4), trimmed=True))
        nv = []
        for k, vs, ls, sz in stk:
            net, x, y = k
            n = 0
            for L in ls:
                if planes.get(L) == net:
                    n += 1
                if on_pad(net, L, x, y):
                    n += 1
                n += sum(1 for o in by_net_layer.get((net, L), []) if seg_d(x, y, o) <= sz / 2 + o['w'] / 2 + EPS)
            if n < 2:
                dead_v.extend(vs)
                continue
            # Altium's antenna test per element: stack neighbours + copper on its own layers must reach two
            for e in vs:
                ne = sum(1 for o in vs if o is not e and set(span(o)) & set(span(e)))
                for L in span(e):
                    ne += (planes.get(L) == net) + on_pad(net, L, x, y) + sum(
                        1 for o in by_net_layer.get((net, L), []) if seg_d(x, y, o) <= sz / 2 + o['w'] / 2 + EPS)
                (nv if ne >= 2 or len(vs) == 1 else dead_v).append(e)
        if len(nt) == len(tracks) and len(nv) == len(vias):
            return dead_t, dead_v, nt, nv
        tracks, vias = nt, nv


def main():
    M = json.load(open(sys.argv[1]))
    dt, dv, nt, nv = analyse(M)
    orig = {id(t) for t in M['tracks']}
    added = [t for t in nt if t.get('trimmed')]
    dt = [t for t in dt if id(t) in orig]          # trimmed replacements that later died never reached the board
    for t in added:
        print('trim  %-10s %-10s now (%.3f,%.3f)-(%.3f,%.3f)' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']))
    for t in dt:
        print('track %-10s %-10s (%.3f,%.3f)-(%.3f,%.3f) w%.4f' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], t['w']))
    for v in dv:
        sp = span(v)
        print('via   %-10s (%.3f,%.3f) %s>%s' % (v['net'], v['x'], v['y'], sp[0], sp[-1]))
    M2 = dict(M, tracks=nt, vias=nv)
    oc = C.open_count(C.islands(M2))
    print('%d tracks, %d vias dead; open after prune: %d %s' % (len(dt), len(dv), sum(oc.values()), oc))
    if len(sys.argv) > 2:
        json.dump({'remove': dt, 'remove_vias': dv, 'tracks': [{k: v for k, v in t.items() if k != 'trimmed'} for t in added], 'vias': []}, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
