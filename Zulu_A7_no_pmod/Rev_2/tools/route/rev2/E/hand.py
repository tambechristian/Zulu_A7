"""hand.py <model.json> <state_plan.json> <hand.json> [--drop NET@x0,y0,x1,y1;...]
Exact legality (route_check rules, elib.Checker) of hand items {tracks, vias, remove, remove_vias} against model +
state plan (router copper) minus the hand plan's removals. Prints each blocked item with its blockers and gaps, the
vias whose land overlaps an SMD pad, and the open count with the hand items merged."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
M0 = E.load(sys.argv[1]); S = E.load(sys.argv[2]); H = E.load(sys.argv[3])
rt = {E.tkey(t) for t in H.get('remove', [])}
rv = {E.vkey(v) for v in H.get('remove_vias', [])}
st = [t for t in S['tracks'] if E.tkey(t) not in rt]
sv = [v for v in S['vias'] if E.vkey(v) not in rv]
M = E.apply(M0, H.get('remove', []), H.get('remove_vias', []), st, sv)
ck = E.Checker(M)
bad = 0
for v in H.get('vias', []):
    b = ck.via_bad(v)
    ip = E.via_in_pads(M, dict(v, span=E.span(v)))
    if b or ip:
        bad += 1
        print('VIA %s %.3f,%.3f %s>%s %.2f:' % (v['net'], v['x'], v['y'], E.span(v)[0], E.span(v)[-1], v['size']),
              sorted({'%s %s %s g%.3f' % (k, (o or {}).get('net', ''), (o or {}).get('ref', '') + ('%.2f,%.2f' % ((o or {}).get('x', (o or {}).get('x1', 0)), (o or {}).get('y', (o or {}).get('y1', 0)))), g) for k, o, g in b})[:6],
              'IN PAD' if ip else '', ['%s-%s' % (p['ref'], p['pad']) for l, p in ip])
    ck.add_via(v)
for t in H.get('tracks', []):
    b = ck.track_bad(t)
    if b:
        bad += 1
        print('TRK %s %s %.3f,%.3f-%.3f,%.3f w%.3f:' % (t['net'], t['layer'][:3], t['x1'], t['y1'], t['x2'], t['y2'], t['w']),
              sorted({'%s %s %s g%.3f' % (k, (o or {}).get('net', ''), (o or {}).get('ref', '') + ('%.2f,%.2f' % ((o or {}).get('x', (o or {}).get('x1', 0)), (o or {}).get('y', (o or {}).get('y1', 0)))), g) for k, o, g in b})[:6])
    ck.add_track(t)
print('blocked items', bad)
M2 = E.apply(M, (), (), H.get('tracks', []), H.get('vias', []))
oc = E.C.open_count(E.C.islands(M2))
print('open', sum(oc.values()), {k: v for k, v in oc.items() if v})
