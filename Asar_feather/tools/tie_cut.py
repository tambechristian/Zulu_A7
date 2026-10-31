"""local repair around plane-tie columns: add the columns to a plan, cut the copper of the nets they collide with
within a radius of each site, and let a no-rip router pass re-join those nets locally.

    python tools/tie_cut.py <model.json> <plan.json> <sites.json> <radius> <out.json>

sites.json: [{"net": "VCC3V3", "x": .., "y": .., "kind": "stack_tie"|"uvia_top", "cut": ["D4", "RAS#:2.5", ...]}, ...]
(a net may carry its own cut radius after a colon; a site with "kind": null only cuts)
The column's vias are added as plan vias; every plan track or via of a 'cut' net that comes within <radius> of the
site is removed (tracks are clipped at the circle, the parts outside stay). Prints the nets for router.py --nets."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402


def clip(t, cx, cy, r):
    """the parts of track t outside the circle (cx, cy, r), as tracks (0, 1 or 2 of them)"""
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    a = dx * dx + dy * dy
    if a < 1e-12:
        return []
    b = 2 * (dx * (x1 - cx) + dy * (y1 - cy))
    c = (x1 - cx) ** 2 + (y1 - cy) ** 2 - r * r
    disc = b * b - 4 * a * c
    if disc <= 0:
        return [t]                                     # does not reach the circle (seg_dist said it does: endpoint case)
    sq = math.sqrt(disc)
    ta, tb = (-b - sq) / (2 * a), (-b + sq) / (2 * a)
    out = []
    if ta > 0.02:
        out.append(dict(t, x2=round(x1 + ta * dx, 4), y2=round(y1 + ta * dy, 4)))
    if tb < 0.98:
        out.append(dict(t, x1=round(x1 + tb * dx, 4), y1=round(y1 + tb * dy, 4)))
    return out


def main():
    model, plan, sites, radius, out = sys.argv[1:6]
    radius = float(radius)
    P = json.load(open(plan))
    sites = json.load(open(sites))
    cut_nets = set()
    gone_t, gone_v = [], []
    for s in sites:
        if s.get('kind'):                              # a site without a kind only cuts
            objs, _, _ = R.VIAS[s['kind']]
            for fr, to, size, hole in objs:
                P['vias'].append({'net': s['net'], 'x': s['x'], 'y': s['y'], 'size': size, 'hole': hole, 'from': fr, 'to': to})
        cut = {c.split(':')[0]: float(c.split(':')[1]) if ':' in c else radius for c in s.get('cut', [])}
        cut_nets |= set(cut)
        keep = []
        for t in P['tracks']:
            if t['net'] in cut and C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], s['x'], s['y']) < cut[t['net']]:
                gone_t.append(t)
                keep += clip(t, s['x'], s['y'], cut[t['net']])
            else:
                keep.append(t)
        P['tracks'] = keep
        keep = []
        for v in P['vias']:
            if v['net'] in cut and math.hypot(v['x'] - s['x'], v['y'] - s['y']) < cut[v['net']]:
                gone_v.append(v)
            else:
                keep.append(v)
        P['vias'] = keep
    P.setdefault('log', []).append('tie_cut: %d columns, radius %.2f, cut %d tracks %d vias of %s' % (
        len(sites), radius, len(gone_t), len(gone_v), ' '.join(sorted(cut_nets))))
    json.dump(P, open(out, 'w'), indent=0)
    print('cut %d tracks, %d vias; nets: %s' % (len(gone_t), len(gone_v), ','.join(sorted(cut_nets))))


if __name__ == '__main__':
    main()
