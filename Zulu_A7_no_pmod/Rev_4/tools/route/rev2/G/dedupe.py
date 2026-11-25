"""dedupe.py <in_plan> <out_plan>: drop plan tracks that duplicate an earlier plan track (net, layer, width, ends
either way round within 0.002 mm; augment / trim copies). Re-gate afterwards (final_gate.sh)."""
import json
import sys

P = json.load(open(sys.argv[1]))


def same(t, o):
    a = (t['x1'], t['y1'], t['x2'], t['y2'])
    b = (o['x1'], o['y1'], o['x2'], o['y2'])
    return t['net'] == o['net'] and t['layer'] == o['layer'] and abs(t['w'] - o['w']) < 0.002 and (
        all(abs(p - q) < 0.002 for p, q in zip(a, b)) or all(abs(p - q) < 0.002 for p, q in zip(a, b[2:] + b[:2])))


out = []
for t in P['tracks']:
    if not any(same(t, o) for o in out):
        out.append(t)
print('dropped %d duplicate tracks' % (len(P['tracks']) - len(out)))
P['tracks'] = out
json.dump(P, open(sys.argv[2], 'w'), indent=1)
