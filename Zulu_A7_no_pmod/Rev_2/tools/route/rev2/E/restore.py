"""restore.py <model.json> <seed_plan.json> <rip.json> <nets|ALL> <out_seed.json>
Put back every ripped item (rip.json) of the given nets that is legal (exact route_check clearance, elib.Checker)
against the model + the seed's router copper; repeat to a fixpoint. Writes seed + restored items as one seed plan
(vias as from/to objects). Prints open counts before and after."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
from collections import Counter
M0 = E.load(sys.argv[1]); S = E.load(sys.argv[2]); rip = E.load(sys.argv[3])
nets = None if sys.argv[4] == 'ALL' else set(sys.argv[4].split(','))
NO = {'USB_D_P', 'USB_D_N'}
M = E.apply(M0, (), (), S['tracks'], S['vias'])
oc = E.C.open_count(E.C.islands(M))
print('before: open', sum(oc.values()), {k: v for k, v in oc.items() if v})
ck = E.Checker(M)
sk = {E.tkey(t) for t in M['tracks']}
svk = {E.vkey(v) for v in M['vias']}
cand_t = [t for t in rip['remove'] if t['net'] not in NO and (nets is None or t['net'] in nets) and E.tkey(t) not in sk]
cand_v = [v for v in rip['remove_vias'] if v['net'] not in NO and (nets is None or v['net'] in nets) and E.vkey(v) not in svk]
rt, rv = [], []
changed = True
while changed:
    changed = False
    for v in list(cand_v):
        if not ck.via_bad(v):
            ck.add_via(v); rv.append(v); cand_v.remove(v); changed = True
    for t in list(cand_t):
        if not ck.track_bad(t):
            ck.add_track(t); rt.append(t); cand_t.remove(t); changed = True
print('restored', len(rt), 'tracks', len(rv), 'vias', dict(Counter(t['net'] for t in rt) + Counter(v['net'] for v in rv)))
print('not restorable', dict(Counter(t['net'] for t in cand_t) + Counter(v['net'] for v in cand_v)))
for t in cand_t:
    bad = ck.track_bad(t)
    print('  T %s %s %.3f,%.3f-%.3f,%.3f blocked by %s' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'],
          sorted({(k, (o or {}).get('net', ''), (o or {}).get('ref', '')) for k, o, g in bad})[:4]))
for v in cand_v:
    bad = ck.via_bad(v)
    print('  V %s %.3f,%.3f %s>%s blocked by %s' % (v['net'], v['x'], v['y'], E.span(v)[0], E.span(v)[-1],
          sorted({(k, (o or {}).get('net', ''), (o or {}).get('ref', '')) for k, o, g in bad})[:4]))
M2 = E.apply(M, (), (), rt, rv)
oc = E.C.open_count(E.C.islands(M2))
print('after: open', sum(oc.values()), {k: v for k, v in oc.items() if v})
out = {'tracks': S['tracks'] + rt, 'vias': S['vias'] + [{'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'],
       'from': E.span(v)[0], 'to': E.span(v)[-1]} for v in rv], 'remove': []}
E.dump(out, sys.argv[5], 0)
