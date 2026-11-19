"""widen.py <plan.json> <out_plan.json> [nets]: widen the plan's power tracks (default VBATT, USB5V0, VU on Top /
Bottom) to the widest of 1.0/0.8/0.6/0.5/0.4/0.3 mm that stays legal (elib.Checker: route_check clearances, board
edge) against everything on base_moved - remove + plan, the other widened tracks included. Endpoints unchanged."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
import compose_plan as CP
P = E.load(sys.argv[1])
nets = set((sys.argv[3] if len(sys.argv) > 3 else 'VBATT,USB5V0,VU').split(','))
B = E.load(os.path.join(E.PREP, 'base_moved.json'))
M = CP.apply(B, P)
ck = E.Checker(M)
plan_keys = {E.tkey(t) for t in P['tracks']}
cand = [t for t in M['tracks'] if t['net'] in nets and E.tkey(t) in plan_keys and t['layer'] in ('Top Layer', 'Bottom Layer')]
cand.sort(key=lambda t: -((t['x2'] - t['x1']) ** 2 + (t['y2'] - t['y1']) ** 2))
changed = {}
for t in cand:
    for w in (1.0, 0.8, 0.6, 0.5, 0.4, 0.3):
        if w <= t['w'] + 1e-9:
            break
        nt = dict(t, w=w)
        if not ck.track_bad(nt, skip={id(t)}):
            changed[E.tkey(t)] = w
            t['w'] = w            # the checker's index holds this dict: later tests see the new width
            break
out = dict(P)
out['tracks'] = [dict(t, w=changed[E.tkey(t)]) if E.tkey(t) in changed else t for t in P['tracks']]
json.dump(out, open(sys.argv[2], 'w'), indent=1)
from collections import Counter
print('widened %d of %d tracks:' % (len(changed), len(cand)), dict(Counter((k[0], v) for k, v in changed.items())))
for n in sorted(nets):
    ts = [t for t in out['tracks'] if t['net'] == n]
    print(' %s widths %s' % (n, dict(Counter(t['w'] for t in ts))))
