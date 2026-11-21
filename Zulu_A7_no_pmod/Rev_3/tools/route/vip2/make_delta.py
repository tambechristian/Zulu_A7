"""No-PMOD Rev 2 (2026-11-13), second pass: the first plan (plan.json, applied, PcbDoc 36f559b4) put four moved vias
exactly tangent to their pads (R108-1 and R108-2 even overlapped by tens of nanometres; independent check). Re-planned
from the same pre-move board with VIP_PAD_GAP=0.025 (land >= 0.025 mm from every SMD pad):

    VIP_PAD_GAP=0.025 python tools/route/vip/move_thru_vias.py <model c88d7ac6> <PcbDoc> tools/route/vip2/plan1b.json
    python tools/route/vip2/make_delta.py tools/route/vip2/plan.json tools/route/vip2/plan1b.json tools/route/vip2/delta.json

delta.json removes plan.json's four moved vias and their seven jumper tracks from the current board and places
plan1b's (same vias, same jumper layers and widths, each from the original in-pad point). The TCK stack and the
C161-1 skip are unchanged.
"""
import json, sys
P0, P1 = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
SKIP = {(4.8, 16.6)}
moved0 = [v for v in P0['vias'] if 'span' in v and len(v['span']) == 6]
tr0 = P0['tracks']
nv = [dict(v, **{'from': v['span'][0], 'to': v['span'][-1]}) for r, v in zip(P1['remove_vias'], P1['vias'])
      if (r['x'], r['y']) not in SKIP]
nt = [t for t in P1['tracks'] if (t['x1'], t['y1']) not in SKIP]
assert len(moved0) == 4 and len(tr0) == 7 and len(nv) == 4 and len(nt) == 7, (len(moved0), len(tr0), len(nv), len(nt))
assert {v['net'] for v in moved0} == {v['net'] for v in nv}
delta = {'remove': tr0, 'remove_vias': moved0, 'tracks': nt, 'vias': nv,
         'report': [r for r in P1['report'] if tuple(r['from']) not in SKIP]}
json.dump(delta, open(sys.argv[3], 'w'), indent=0)
for a, b in zip(sorted(moved0, key=lambda v: v['net']), sorted(nv, key=lambda v: v['net'])):
    print('%-15s (%.3f,%.3f) -> (%.3f,%.3f)' % (a['net'], a['x'], a['y'], b['x'], b['y']))
