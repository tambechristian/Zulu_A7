"""Pull tracks back from the non-plated holes (2026-11-16, after PCBWay's answer: through hole to trace >= 5 mil).

Three NPTH had copper closer than 0.127 mm (fab_facts / rule check of 2026-11-16, md5 e214e57b):
  X1 peg (6.2495, 8.54)   Top USB-CC1 0.0864, L3 PWR_CHRG 0.1114
  X1 peg (6.2495, 14.32)  L4 EN 0.1169, Bottom VCC1V0 (0.4 mm) 0.1194
  X2 hole (2.54, 20.32)   Bottom VU (0.4 mm) 0.1198
This plan removes those track runs and lays new ones, then checks on the board model:
  - hole wall to every track near the three holes (target >= 0.15, floor 0.127),
  - every new segment against all copper of other nets on its layer (>= 3 mil, the board rule),
  - every new run starts and ends exactly on the endpoints it replaces (connectivity unchanged),
  - board edge (>= 0.3 mm).
    python tools/npth_clearance_plan.py            # checks and writes tools/route/npth_clearance/plan.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fab_facts as FF  # noqa: E402

TARGET, FLOOR, CLEAR, EDGE = 0.15, 0.127, 0.0762, 0.30
BOARD = (0.0, 0.0, 50.8, 22.86)
HOLES = [dict(ref='X1', x=6.2495, y=8.54, d=0.65), dict(ref='X1', x=6.2495, y=14.32, d=0.65),
         dict(ref='X2', x=2.54, y=20.32, d=2.5)]


def arc(cx, cy, r, a0, a1, step):
    n = max(1, int(math.ceil(abs(a1 - a0) / step)))
    return [(round(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)), 3),
             round(cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n)), 3)) for k in range(n + 1)]


# Each edit: layer, net, width, the existing polyline (ordered vertices; its segments are removed) and the new one.
EDITS = [
    dict(name='USB-CC1 Top at X1 peg 8.54', layer='Top', net='USB-CC1', width=0.0762,
         old=[(5.55, 7.725), (5.80, 7.975), (5.80, 8.70), (5.825, 8.75), (5.875, 8.80), (5.875, 8.825), (6.60, 9.55)],
         new=[(5.55, 7.725), (5.70, 7.875), (5.70, 8.90), (6.35, 9.55), (6.60, 9.55)]),
    dict(name='PWR_CHRG L3 at X1 peg 8.54', layer='L3-SIG', net='PWR_CHRG', width=0.0762,
         old=[(5.525, 7.75), (5.775, 8.00), (5.775, 8.725), (5.80, 8.75), (5.80, 8.775), (5.85, 8.825), (5.85, 8.85)],
         new=[(5.525, 7.75), (5.735, 7.96), (5.735, 8.735), (5.80, 8.80), (5.85, 8.85)]),
    dict(name='EN L4 at X1 peg 14.32', layer='L4-SIG', net='EN', width=0.0762,
         old=[(5.275, 14.80), (6.40, 14.80), (9.275, 14.775)],
         new=[(5.275, 14.80), (5.325, 14.85), (9.20, 14.85), (9.275, 14.775)]),
    dict(name='VCC1V0 Bottom at X1 peg 14.32', layer='Bottom', net='VCC1V0', width=0.4,
         old=[(5.725, 13.05), (6.35, 13.675), (6.425, 13.675), (6.45, 13.70), (6.475, 13.70), (6.50, 13.725), (6.525, 13.725),
              (6.55, 13.75), (6.575, 13.75), (6.60, 13.775), (6.625, 13.775), (6.80, 13.95), (6.80, 13.975), (6.825, 14.0),
              (6.85, 14.05), (6.85, 14.075), (6.875, 14.10), (6.90, 14.15), (6.925, 14.425)],
         # stays above NetL3_1 (y 12.775, 0.4 mm) and U7-5, bends right before the hole, climbs at x 6.95 to U7-4
         new=[(5.725, 13.05), (5.975, 13.30), (6.55, 13.30), (6.95, 13.70), (6.95, 14.40), (6.925, 14.425)]),
]
VU_OLD = [(1.425, 15.125), (1.30, 19.325), (1.30, 19.35), (1.225, 19.425), (1.225, 19.45), (1.175, 19.50), (1.15, 19.55),
          (1.15, 19.575), (1.125, 19.60), (1.10, 19.65), (1.075, 19.70), (1.05, 19.75), (1.05, 19.80), (1.025, 19.825),
          (1.025, 19.875), (1.00, 19.90), (0.975, 20.00), (0.95, 20.175), (0.95, 20.475), (0.975, 20.65), (1.00, 20.75),
          (1.025, 20.825), (1.05, 20.85), (1.05, 20.875), (1.075, 20.90), (1.075, 20.925), (1.10, 20.95), (1.10, 20.975),
          (1.125, 21.025), (1.15, 21.05), (1.15, 21.075), (1.175, 21.10), (1.175, 21.125), (1.20, 21.15), (1.20, 21.175),
          (1.25, 21.225), (1.25, 21.25), (1.60, 21.60), (1.625, 21.60), (1.675, 21.65), (1.70, 21.65), (1.75, 21.70),
          (1.775, 21.70), (1.80, 21.725), (1.85, 21.75), (1.90, 21.775), (1.95, 21.80), (2.00, 21.80), (2.025, 21.825),
          (2.05, 21.825), (2.075, 21.85), (2.175, 21.875), (2.30, 21.90), (2.775, 21.90), (2.90, 21.875), (3.00, 21.85),
          (3.025, 21.825), (6.575, 21.825)]
VU_ARC = arc(2.54, 20.32, 1.68, 200.0, 78.0, 12.2)
EDITS.append(dict(name='VU Bottom around X2 hole 20.32', layer='Bottom', net='VU', width=0.4,
                  old=VU_OLD, new=[(1.425, 15.125)] + VU_ARC + [(3.40, 21.825), (6.575, 21.825)]))


def segs(poly):
    return [(a, b) for a, b in zip(poly, poly[1:]) if a != b]


def same(a, b, tol=2e-3):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def seg_seg(a, b, c, d):
    return FF.seg_seg_dist((a[0], a[1], b[0], b[1]), (c[0], c[1], d[0], d[1]))


def main():
    B = FF.read_board()
    tracks = B['tracks']
    rep, ok = {'edits': []}, True
    removed = []
    for e in EDITS:
        found = []
        for a, b in segs(e['old']):
            hit = [i for i, t in enumerate(tracks) if t['layer'] == e['layer'] and t['net'] == e['net'] and
                   ((same((t['x1'], t['y1']), a) and same((t['x2'], t['y2']), b)) or (same((t['x1'], t['y1']), b) and same((t['x2'], t['y2']), a)))]
            if len(hit) != 1:
                ok = False
                print('  !! %s: segment %s-%s found %d times' % (e['name'], a, b, len(hit)))
            found += hit
        widths = {round(tracks[i]['width'], 4) for i in found}
        if widths != {round(e['width'], 4)}:
            ok = False
            print('  !! %s: old widths %s' % (e['name'], widths))
        removed += found
        e['found'] = len(found)
    keep = [t for i, t in enumerate(tracks) if i not in set(removed)]

    for e in EDITS:
        L, w, new = e['layer'], e['width'], e['new']
        # ends must be the old ends (the rest of the net is untouched)
        ends_ok = same(new[0], e['old'][0]) and same(new[-1], e['old'][-1])
        # other-net copper on the layer
        worst = (9, None)
        for a, b in segs(new):
            for t in keep:
                if t['layer'] != L or t['net'] == e['net']:
                    continue
                g = seg_seg(a, b, (t['x1'], t['y1']), (t['x2'], t['y2'])) - w / 2 - t['width'] / 2
                if g < worst[0]:
                    worst = (g, 'track %s' % t['net'])
            for v in B['vias']:
                if v['net'] == e['net'] or not FF.span_has(v['span'], L):
                    continue
                g = FF.seg_point_dist(a[0], a[1], b[0], b[1], v['x'], v['y']) - w / 2 - v['size'] / 2
                if g < worst[0]:
                    worst = (g, 'via %s %s' % (v['net'], v['span']))
            for p in B['pads']:
                if p['net'] == e['net'] or not FF.pad_on_layer(p, L):
                    continue
                if p['net'] is None and p['hole'] > 0:
                    continue  # the NPTH themselves are judged below
                pv = FF.pad_view(p, L)
                g = FF.seg_pad_dist(dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], width=w), pv)
                if g < worst[0]:
                    worst = (g, 'pad %s-%s %s' % (p['ref'], p['pad'], p['net']))
        # board edge
        edge = min(min(x - BOARD[0], y - BOARD[1], BOARD[2] - x, BOARD[3] - y) for x, y in new) - w / 2
        e.update(ends_ok=ends_ok, other_net_min=round(worst[0], 4), other_net_near=worst[1], edge_min=round(edge, 3))
        bad = not ends_ok or worst[0] < CLEAR - 1e-4 or edge < EDGE
        ok = ok and not bad
        rep['edits'].append({k: e[k] for k in ('name', 'layer', 'net', 'width', 'found', 'ends_ok', 'other_net_min', 'other_net_near', 'edge_min')}
                            | {'new': e['new'], 'old_segments': len(segs(e['old']))})

    # hole wall to every track (kept + new) on every layer
    allnew = [dict(layer=e['layer'], net=e['net'], width=e['width'], x1=a[0], y1=a[1], x2=b[0], y2=b[1], new=True)
              for e in EDITS for a, b in segs(e['new'])]
    holes = []
    for h in HOLES:
        r = h['d'] / 2
        best = {}
        for t in keep + allnew:
            g = FF.seg_point_dist(t['x1'], t['y1'], t['x2'], t['y2'], h['x'], h['y']) - t['width'] / 2 - r
            key = (t['layer'], t['net'])
            if g < 0.3 and g < best.get(key, (9,))[0]:
                best[key] = (round(g, 4), bool(t.get('new')))
        hm = min([v[0] for v in best.values()] or [9])
        holes.append(dict(hole='%s (%.4f, %.2f)' % (h['ref'], h['x'], h['y']), min_track=hm,
                          near=sorted(((k[0], k[1]) + v for k, v in best.items()), key=lambda z: z[2])[:6]))
        if hm < FLOOR:
            ok = False
    rep['holes'] = holes
    rep['ok'] = ok
    out = os.path.join(HERE, 'route', 'npth_clearance')
    os.makedirs(out, exist_ok=True)
    json.dump(dict(edits=[dict(name=e['name'], layer=e['layer'], net=e['net'], width=e['width'], old=e['old'], new=e['new'])
                          for e in EDITS], report=rep), open(os.path.join(out, 'plan.json'), 'w'), indent=1)
    for e in rep['edits']:
        print('%-34s found %2d/%2d  ends %s  other-net min %.4f (%s)  edge %.3f' % (
            e['name'], e['found'], e['old_segments'], e['ends_ok'], e['other_net_min'], e['other_net_near'], e['edge_min']))
    for h in holes:
        print('%-22s min track %.4f  %s' % (h['hole'], h['min_track'], h['near']))
    print('PLAN OK' if ok else 'PLAN NOT OK')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
