"""Move base copper intersecting one or more boxes into a router seed.

Usage:
    python promote_region.py BASE.json SEED.json OUT_BASE.json OUT_SEED.json X0,Y0,X1,Y1 [...]
"""
import json
import sys
from collections import Counter

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def track_hits(t, boxes):
    tx0, tx1 = sorted((t['x1'], t['x2']))
    ty0, ty1 = sorted((t['y1'], t['y2']))
    return any(tx1 >= x0 and tx0 <= x1 and ty1 >= y0 and ty0 <= y1 for x0, y0, x1, y1 in boxes)


def via_hits(v, boxes):
    return any(x0 <= v['x'] <= x1 and y0 <= v['y'] <= y1 for x0, y0, x1, y1 in boxes)


def router_via(v):
    out = dict(v)
    span = out.pop('span', None)
    if span:
        out['from'], out['to'] = span[0], span[-1]
    elif 'from' not in out or 'to' not in out:
        raise ValueError('Via has neither span nor from/to: %r' % v)
    return out


def main():
    if len(sys.argv) < 6:
        raise SystemExit(__doc__)
    base_path, seed_path, out_base, out_seed = sys.argv[1:5]
    boxes = [tuple(map(float, arg.split(','))) for arg in sys.argv[5:]]
    if any(len(box) != 4 or box[0] > box[2] or box[1] > box[3] for box in boxes):
        raise SystemExit('Each box must be X0,Y0,X1,Y1')

    base = json.load(open(base_path))
    seed = json.load(open(seed_path))
    moved_t = [t for t in base['tracks'] if track_hits(t, boxes)]
    moved_v = [v for v in base['vias'] if via_hits(v, boxes)]
    base['tracks'] = [t for t in base['tracks'] if not track_hits(t, boxes)]
    base['vias'] = [v for v in base['vias'] if not via_hits(v, boxes)]
    seed['tracks'] += moved_t
    seed['vias'] += [router_via(v) for v in moved_v]
    seed['remove'] = []

    json.dump(base, open(out_base, 'w'), indent=0)
    json.dump(seed, open(out_seed, 'w'), indent=0)
    print('promoted %d tracks and %d vias' % (len(moved_t), len(moved_v)))
    print('track nets:', dict(Counter(t['net'] for t in moved_t)))
    print('via nets:', dict(Counter(v['net'] for v in moved_v)))


if __name__ == '__main__':
    main()
