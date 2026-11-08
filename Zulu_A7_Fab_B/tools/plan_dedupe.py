"""Drop exact duplicate tracks and vias from a routing plan (2026-10-28).

    python tools/plan_dedupe.py <plan.json> <out.json>

A plan assembled from seeds can hold the same track twice (short_r3_p400000 carries 12 such pairs, so every plan
seeded from it does); the board wants each object once, and count-based guards (FeatherClearCopper's via/track
counts, verify_copper) must see the same number the model holds. Keys are end-order-free like verify_copper's.
"""
import json
import sys


def main():
    src, dst = sys.argv[1:3]
    P = json.load(open(src))
    seen = set()
    out = dict(P, vias=[], tracks=[])
    for v in P['vias']:
        k = ('v', v['net'], round(v['x'], 3), round(v['y'], 3), v.get('from'), v.get('to'), tuple(v.get('span', ())))
        if k not in seen:
            seen.add(k)
            out['vias'].append(v)
    for t in P['tracks']:
        k = ('t', t['net'], t['layer'], round(t['w'], 3),
             tuple(sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))])))
        if k not in seen:
            seen.add(k)
            out['tracks'].append(t)
    json.dump(out, open(dst, 'w'), indent=0)
    print('%s: %d -> %d vias, %d -> %d tracks' % (src, len(P['vias']), len(out['vias']), len(P['tracks']),
                                                  len(out['tracks'])))


if __name__ == '__main__':
    main()
