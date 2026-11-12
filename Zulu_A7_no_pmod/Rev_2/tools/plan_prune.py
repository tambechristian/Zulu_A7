"""Remove the dead ends of a plan (2026-11-05): finish.py cuts tracks where a new path crosses them and re-joins the
net locally, which leaves stub tails (net antennae) and now and then a via nothing uses. Per net, repeatedly:
  - a plan track with a free end (no pad, via or other track of the net at that end) is trimmed back to the last
    point where something of the net sits on it, or removed when nothing does
  - a plan via that meets copper of its net (pad, track, stacked via, its plane) on fewer than two layers is removed
The net's islands are counted before and after; a net whose count changed keeps its original copper.

    python tools/plan_prune.py <plan.json> <model.json> <out.json>"""
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
from route_check import span  # noqa: E402

EPS = 1e-3


def prune_net(net, pads, ftracks, fvias, tracks, vias, plane_layer):
    """returns (tracks, vias) of the plan for one net with the dead ends gone"""
    tracks = [dict(t) for t in tracks]
    vias = [dict(v, span=span(v)) for v in vias]
    fv = [dict(v) for v in fvias]
    changed = True
    while changed:
        changed = False
        allv = fv + vias
        allt = ftracks + tracks
        for t in list(tracks):
            L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
            if L < 1e-6:
                tracks.remove(t)
                changed = True
                continue
            anchors = []                               # parameters 0..1 along t where something of the net sits

            def par(x, y):
                return ((x - t['x1']) * (t['x2'] - t['x1']) + (y - t['y1']) * (t['y2'] - t['y1'])) / (L * L)
            for p in pads:
                if t['layer'] in p['layers'] and C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) <= t['w'] / 2 + EPS:
                    # the stretch of t over the pad: sample it
                    n = max(2, int(L / 0.02) + 1)
                    ss = [k / (n - 1) for k in range(n)]
                    on = [s for s in ss if C.pad_point(p, t['x1'] + s * (t['x2'] - t['x1']),
                                                         t['y1'] + s * (t['y2'] - t['y1'])) <= t['w'] / 2 + EPS]
                    anchors += [min(on), max(on)] if on else []
            for v in allv:
                if t['layer'] in v['span'] and \
                        C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= (t['w'] + v['size']) / 2 + EPS:
                    anchors.append(min(1.0, max(0.0, par(v['x'], v['y']))))
            for o in allt:
                if o is t or o['layer'] != t['layer']:
                    continue
                if C.seg_seg((t['x1'], t['y1'], t['x2'], t['y2']), (o['x1'], o['y1'], o['x2'], o['y2'])) > \
                        (t['w'] + o['w']) / 2 + EPS:
                    continue
                hit = False
                for x, y in ((o['x1'], o['y1']), (o['x2'], o['y2'])):
                    if C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) <= (t['w'] + o['w']) / 2 + EPS:
                        anchors.append(min(1.0, max(0.0, par(x, y))))
                        hit = True
                for s, (x, y) in ((0.0, (t['x1'], t['y1'])), (1.0, (t['x2'], t['y2']))):
                    if C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) <= (t['w'] + o['w']) / 2 + EPS:
                        anchors.append(s)
                        hit = True
                if not hit:                            # the two cross in mid-span: keep all of t
                    anchors += [0.0, 1.0]
            if not anchors:
                tracks.remove(t)
                changed = True
                continue
            lo, hi = min(anchors), max(anchors)
            tol = 0.03 / L                             # a tail shorter than 0.03 mm is not worth a cut
            if hi - lo < 1e-9:                          # touches the net at one point only: all of it is a tail
                tracks.remove(t)
                changed = True
                continue
            if lo > tol or hi < 1 - tol:
                x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
                if lo > tol:
                    t['x1'], t['y1'] = round(x1 + lo * (x2 - x1), 4), round(y1 + lo * (y2 - y1), 4)
                if hi < 1 - tol:
                    t['x2'], t['y2'] = round(x1 + hi * (x2 - x1), 4), round(y1 + hi * (y2 - y1), 4)
                changed = True
        for v in list(vias):
            on = set()                                 # layers of the via's span on which something of the net meets it
            for p in pads:
                if C.pad_point(p, v['x'], v['y']) <= v['size'] / 2 + EPS:
                    on |= set(p['layers']) & set(v['span'])
            for t in ftracks + tracks:
                if t['layer'] in v['span'] and \
                        C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= (t['w'] + v['size']) / 2 + EPS:
                    on.add(t['layer'])
            for o in fv + vias:
                if o is not v and math.hypot(o['x'] - v['x'], o['y'] - v['y']) <= (o['size'] + v['size']) / 2 + EPS:
                    on |= set(o['span']) & set(v['span'])
            if plane_layer and plane_layer in v['span']:
                on.add(plane_layer)
            if len(on) < 2:                            # it joins nothing: a dead via (unused column end, cut leftover)
                vias.remove(v)
                changed = True
    return tracks, [{k: v[k] for k in v if k != 'span'} for v in vias]


def main():
    plan_f, model_f, out_f = sys.argv[1:4]
    P = json.load(open(plan_f))
    M = json.load(open(model_f))
    plane_of = {net: lay for lay, net in M['planes'].items()}
    nets = sorted({t['net'] for t in P['tracks']} | {v['net'] for v in P['vias']})
    bt, bv = defaultdict(list), defaultdict(list)
    for t in P['tracks']:
        bt[t['net']].append(t)
    for v in P['vias']:
        bv[v['net']].append(v)
    out_t, out_v, log = [], [], []
    cut_t = cut_v = kept = 0
    for net in nets:
        pads = [p for p in M['pads'] if p['net'] == net]
        ft = [t for t in M['tracks'] if t['net'] == net]
        fv = [v for v in M['vias'] if v['net'] == net]

        def count(tr, vi):
            Mn = {'pads': pads, 'tracks': ft + tr, 'vias': fv + [dict(v, span=span(v)) for v in vi], 'planes': M['planes']}
            return len(C.islands(Mn).get(net, []))
        nt, nv = prune_net(net, pads, ft, fv, bt[net], bv[net], plane_of.get(net))
        same = len(nt) == len(bt[net]) and len(nv) == len(bv[net]) and \
            all(a == b for a, b in zip(nt, bt[net]))
        if same:
            out_t += bt[net]
            out_v += bv[net]
            continue
        if count(nt, nv) != count(bt[net], bv[net]):
            kept += 1
            log.append('prune: %s left alone (its islands would change)' % net)
            out_t += bt[net]
            out_v += bv[net]
            continue
        len0 = sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in bt[net])
        len1 = sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in nt)
        cut_t += len(bt[net]) - len(nt)
        cut_v += len(bv[net]) - len(nv)
        log.append('prune: %s %d -> %d tracks (%.2f mm less), %d -> %d vias' % (net, len(bt[net]), len(nt), len0 - len1,
                                                                             len(bv[net]), len(nv)))
        out_t += nt
        out_v += nv
    Q = dict(P, tracks=out_t, vias=out_v, log=P.get('log', []) + log)
    json.dump(Q, open(out_f, 'w'), indent=0)
    for l in log:
        print(l)
    print('%s: %d -> %d tracks, %d -> %d vias; %d nets left alone' % (out_f, len(P['tracks']), len(out_t),
                                                                     len(P['vias']), len(out_v), kept))


if __name__ == '__main__':
    main()
