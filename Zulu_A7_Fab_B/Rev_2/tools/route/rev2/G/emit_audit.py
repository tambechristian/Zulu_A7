"""emit_audit.py <base_moved.json> <plan.json>: emit_copper preconditions and plan hygiene.
  * every 'remove' track matches exactly one base track (net, layer, width, ends either way within 0.002 mm), and no
    two remove entries match the same track; same for 'remove_vias' (net, hole, centre, span ends);
  * no zero-length plan track, no plan track / via duplicating another plan item or a kept board item;
  * via types: through 0.35/0.20, lasers 0.30/0.15 on Top-L2 / L2-L3 / L4-L5 / L5-Bottom, buried 0.27/0.15 L3-L4."""
import json
import math
import sys
from collections import Counter

T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, T)
import compose_plan as CP  # noqa: E402

B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2]))
S = CP.STACK
bad = []


def tmatch(t, o):
    if t['net'] != o['net'] or t['layer'] != o['layer'] or abs(t['w'] - o['w']) >= 0.002:
        return False
    a = all(abs(p - q) < 0.002 for p, q in zip((t['x1'], t['y1'], t['x2'], t['y2']), (o['x1'], o['y1'], o['x2'], o['y2'])))
    b = all(abs(p - q) < 0.002 for p, q in zip((t['x1'], t['y1'], t['x2'], t['y2']), (o['x2'], o['y2'], o['x1'], o['y1'])))
    return a or b


def vmatch(v, o):
    sv, so = CP.vspan(v), CP.vspan(o)
    return v['net'] == o['net'] and abs(v['hole'] - o['hole']) < 0.002 and abs(v['x'] - o['x']) < 0.002 and \
        abs(v['y'] - o['y']) < 0.002 and sv[0] == so[0] and sv[-1] == so[-1]


hits = Counter()
for r in P['remove']:
    m = [i for i, o in enumerate(B['tracks']) if tmatch(r, o)]
    if len(m) != 1:
        bad.append('remove track matches %d board tracks: %s' % (len(m), r))
    hits.update(m)
bad += ['board track %d matched by %d remove entries' % (i, n) for i, n in hits.items() if n > 1]
hits = Counter()
for r in P['remove_vias']:
    m = [i for i, o in enumerate(B['vias']) if vmatch(r, o)]
    if len(m) != 1:
        bad.append('remove via matches %d board vias: %s' % (len(m), r))
    hits.update(m)
bad += ['board via %d matched by %d remove entries' % (i, n) for i, n in hits.items() if n > 1]
M = CP.apply(B, dict(P, tracks=[], vias=[]))
for i, t in enumerate(P['tracks']):
    if math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) < 0.001:
        bad.append('zero-length track %s' % t)
    if any(tmatch(t, o) for o in P['tracks'][:i]):
        bad.append('duplicate plan track %s' % t)
    if any(tmatch(t, o) for o in M['tracks'] if o['net'] == t['net']):
        bad.append('plan track duplicates a kept board track %s' % t)
kinds = Counter()
for i, v in enumerate(P['vias']):
    if any(vmatch(v, o) for o in P['vias'][:i]):
        bad.append('duplicate plan via %s' % v)
    if any(vmatch(v, o) for o in M['vias'] if o['net'] == v['net']):
        bad.append('plan via duplicates a kept board via %s' % v)
    k = (v['from'], v['to'], v['size'], v['hole'])
    ok = k in {('Top Layer', 'Bottom Layer', 0.35, 0.2), ('L3-SIG', 'L4-SIG', 0.27, 0.15)} or (
        (v['from'], v['to']) in {('Top Layer', 'L2-GND'), ('L2-GND', 'L3-SIG'), ('L4-SIG', 'L5-VCC3V3'),
                                 ('L5-VCC3V3', 'Bottom Layer')} and (v['size'], v['hole']) == (0.3, 0.15))
    if not ok:
        bad.append('odd via type %s' % (k,))
    kinds[k] += 1
print('via kinds added:', dict(kinds))
print('emit audit: %d problems' % len(bad))
for b in bad[:40]:
    print('  ' + b)
