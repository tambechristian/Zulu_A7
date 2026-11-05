"""Widen power trunks where the copper around them allows it (2026-11-05, stage 7 clean-up). No re-route: every track
keeps its centreline, and only its width changes.

    python tools/widen.py <plan.json> <model.json> <out_plan.json> <out_delta.json> [--stacks]

Each track is cut into pieces of at most 0.4 mm, so that a pinch narrows only the piece it is in. Per piece the widest
legal width is computed from the exact distance of its centreline to every other-net object on its layer (R.clearance,
floor 0.078 mm), 0.25 mm to a non-plated hole, and the board edge rule, then floored to a 0.05 step and never reduced
below the current width; equal neighbours are merged again. A piece touching a same-net SMD pad stays no wider than
that pad's short side, so a wide trunk does not pull solder or heat off a small pad. Nets go in the order of NETS, each
seeing the widths already given to the ones before. --stacks also looks for a second L4>L5 + L5>Bottom laser stack beside
each of VCC1V0's two single stacks. The delta plan (remove old tracks, add new ones) is what goes on the board; the
full plan is what route_check and verify_copper judge."""
import json
import math
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402
from route_check import span  # noqa: E402

NETS = [('VCC1V0', 0.5), ('VU', 0.5), ('VBATT', 0.5), ('USB5V0', 0.5), ('NetL1_1', 0.5), ('NetL2_1', 0.5), ('NetL3_1', 0.5)]
FLOOR = 0.078
NPTH = 0.25
STEP = 0.05
SUB = 0.4
STACKS =[(21.35, 11.275), (21.875, 12.175)]
SPAN3 = {'L4-SIG', 'L5-VCC3V3', 'Bottom Layer'}


def seg(t):
    return (t['x1'], t['y1'], t['x2'], t['y2'])


def main():
    plan_f, model_f, out_f, delta_f = sys.argv[1:5]
    P, M = json.load(open(plan_f)), json.load(open(model_f))
    W, H = M['board']['w'], M['board']['h']
    vias = [dict(v, span=span(v)) for v in M['vias'] + P['vias']]
    tracks = P['tracks']
    assert not M['tracks']
    by_layer = defaultdict(list)
    for t in tracks:
        by_layer[t['layer']].append(t)
    pads = M['pads']

    def edge_limit(x, y):
        lim = 2 * (min(x, W - x, y, H - y) - R.EDGE)
        for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
            dx, dy = abs(x - cx), abs(y - cy)
            if dx < 2.2 and dy < 2.2:                  # route_check models the corner as a 1.2 mm square
                lim = min(lim, 2 * max(dx - 1.2, dy - 1.2))
        return lim

    def clr(n1, layer, n2):
        return max(FLOOR, R.clearance(n1, layer), R.clearance(n2, layer))

    def allowed(t, target):
        s = seg(t)
        w = target
        win = target / 2 + 0.35
        x0, x1 = min(s[0], s[2]) - win, max(s[0], s[2]) + win
        y0, y1 = min(s[1], s[3]) - win, max(s[1], s[3]) + win
        for x, y in ((s[0], s[1]), (s[2], s[3])):
            w = min(w, edge_limit(x, y))
        for p in pads:
            r = max(p['w'], p['h'], p['drill'] or 0) / 2 + 0.01
            if p['x'] + r < x0 or p['x'] - r > x1 or p['y'] + r < y0 or p['y'] - r > y1:
                continue
            if p['drill'] > 0 and not p['net']:        # non-plated hole, on every layer
                d = C.seg_dist(s[0], s[1], s[2], s[3], p['x'], p['y']) - p['drill'] / 2
                w = min(w, 2 * (d - NPTH))
                continue
            ls = p['layers'] or (R.STACK if p['drill'] > 0 else [])
            if t['layer'] not in ls:
                continue
            d = C.pad_seg(p, s)
            if p['net'] == t['net']:
                if d <= t['w'] / 2 + 1e-3 and not p['drill']:
                    w = min(w, max(t['w'], min(p['w'], p['h'])))
                continue
            w = min(w, 2 * (d - clr(p['net'], t['layer'], t['net'])))
        for v in vias:
            if t['layer'] not in v['span'] or v['net'] == t['net']:
                continue
            r = v['size'] / 2
            if v['x'] + r < x0 or v['x'] - r > x1 or v['y'] + r < y0 or v['y'] - r > y1:
                continue
            d = C.seg_dist(s[0], s[1], s[2], s[3], v['x'], v['y']) - r
            w = min(w, 2 * (d - clr(v['net'], t['layer'], t['net'])))
        for o in by_layer[t['layer']]:
            if o['net'] == t['net']:
                continue
            r = o['w'] / 2
            if max(o['x1'], o['x2']) + r < x0 or min(o['x1'], o['x2']) - r > x1 or \
                    max(o['y1'], o['y2']) + r < y0 or min(o['y1'], o['y2']) - r > y1:
                continue
            d = C.seg_seg(s, seg(o)) - r
            w = min(w, 2 * (d - clr(o['net'], t['layer'], t['net'])))
        return w

    changed, added = [], []
    for net, target in NETS:
        before = defaultdict(float)
        after = defaultdict(float)
        mine = [t for t in tracks if t['net'] == net and t['w'] < target]
        for t in mine:
            L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
            before[t['w']] += L
            n = max(1, int(math.ceil(L / SUB)))        # a pinch only narrows the piece it is in
            pts = [(round(t['x1'] + (t['x2'] - t['x1']) * i / n, 4), round(t['y1'] + (t['y2'] - t['y1']) * i / n, 4))
                   for i in range(n + 1)]
            pts[0], pts[-1] = (t['x1'], t['y1']), (t['x2'], t['y2'])
            parts = []
            for i in range(n):
                q = dict(t, x1=pts[i][0], y1=pts[i][1], x2=pts[i + 1][0], y2=pts[i + 1][1])
                w = math.floor((allowed(q, target) + 1e-9) / STEP) * STEP
                q['w'] = max(t['w'], round(min(w, target), 3))
                if parts and parts[-1]['w'] == q['w']:   # equal neighbours stay one track
                    parts[-1]['x2'], parts[-1]['y2'] = q['x2'], q['y2']
                else:
                    parts.append(q)
            for q in parts:
                after[q['w']] += math.hypot(q['x2'] - q['x1'], q['y2'] - q['y1'])
            if len(parts) > 1 or parts[0]['w'] != t['w']:
                changed.append(dict(t))
                added += parts
                by_layer[t['layer']].remove(t)
                by_layer[t['layer']] += parts
                tracks.remove(t)
                tracks += parts
        print('%-8s %3d tracks below %.2f; mm by width before %s after %s' % (
            net, len(mine), target, {k: round(v, 1) for k, v in sorted(before.items())},
            {k: round(v, 1) for k, v in sorted(after.items())}))

    new_vias = []
    if '--stacks' in sys.argv:
        def on_tracks(x, y, r, layer):
            return any(t['net'] == 'VCC1V0' and t['layer'] == layer and
                       C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) <= t['w'] / 2 + r - 0.05 for t in by_layer[layer])

        def legal(x, y):
            for ly in SPAN3:
                for p in pads:
                    ls = p['layers'] or (R.STACK if p['drill'] > 0 else [])
                    if ly in ls and p['net'] != 'VCC1V0' and C.pad_point(p, x, y) < 0.15 + FLOOR:
                        return False
                    if p['drill'] > 0 and math.hypot(p['x'] - x, p['y'] - y) < p['drill'] / 2 + 0.075 + R.HOLE_HOLE:
                        return False
                for t in by_layer[ly]:
                    if t['net'] != 'VCC1V0' and C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) < \
                            0.15 + t['w'] / 2 + clr(t['net'], ly, 'VCC1V0'):
                        return False
            for v in vias:
                d = math.hypot(v['x'] - x, v['y'] - y)
                if set(v['span']) & SPAN3:
                    if d < R.HOLE_HOLE + 0.075 + v['hole'] / 2 + 0.001:
                        return False
                    if v['net'] != 'VCC1V0' and d < 0.15 + v['size'] / 2 + FLOOR:
                        return False
            return True

        for sx, sy in STACKS:
            best = None
            for i in range(-120, 121):
                for j in range(-120, 121):
                    x, y = round(sx + i * 0.025, 4), round(sy + j * 0.025, 4)
                    d = math.hypot(x - sx, y - sy)
                    if d > 3.0 or (best and d >= best[0]):
                        continue
                    if on_tracks(x, y, 0.15, 'L4-SIG') and on_tracks(x, y, 0.15, 'Bottom Layer') and legal(x, y):
                        best = (d, x, y)
            print('second stack near %.3f,%.3f: %s' % (sx, sy, best))
            if best:
                for a, b in (('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom Layer')):
                    v = {'net': 'VCC1V0', 'x': best[1], 'y': best[2], 'size': 0.3, 'hole': 0.15, 'from': a, 'to': b}
                    new_vias.append(v)
                    vias.append(dict(v, span=span(v)))

    P['vias'] = P['vias'] + new_vias
    P.setdefault('log', []).append('widen: %d tracks, %d vias added' % (len(changed), len(new_vias)))
    json.dump(P, open(out_f, 'w'), indent=0)
    json.dump({'vias': new_vias, 'tracks': added, 'remove': changed, 'log': ['delta of %s' % os.path.basename(out_f)]},
              open(delta_f, 'w'), indent=0)
    print('%d tracks replaced by %d, %d vias added; plan %d tracks; widths on the plan: %s' % (
        len(changed), len(added), len(new_vias), len(P['tracks']), sorted(Counter(t['w'] for t in P['tracks']).items())))


if __name__ == '__main__':
    main()
