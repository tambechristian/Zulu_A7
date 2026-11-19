"""Diff the router's final board against the moved-pad baseline and write the rip + route plans for compose_plan.py.

    python final_plan.py <base_moved.json> <router_base.json> <router_plan.json> <out_rip.json> <out_route.json>

final board = router_base + router_plan; removals are the baseline copper that is not in it, additions the copper that
is not in the baseline.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
import compose_plan as CP  # noqa: E402

moved, rbase, plan, out_rip, out_route = sys.argv[1:6]
B, RB, P = json.load(open(moved)), json.load(open(rbase)), json.load(open(plan))
if [(p['ref'], p['pad'], p['x'], p['y']) for p in B['pads']] != [(p['ref'], p['pad'], p['x'], p['y']) for p in RB['pads']]:
    sys.exit('pad lists differ between the baseline and the router model')
final_t = RB['tracks'] + P['tracks']
final_v = [dict(v, span=CP.vspan(v)) for v in RB['vias'] + P['vias']]
ft, fv = {CP.tkey(t) for t in final_t}, {CP.vkey(v) for v in final_v}
bt, bv = {CP.tkey(t) for t in B['tracks']}, {CP.vkey(v) for v in B['vias']}
rem_t = [t for t in B['tracks'] if CP.tkey(t) not in ft]
rem_v = [dict(v, span=CP.vspan(v)) for v in B['vias'] if CP.vkey(v) not in fv]
add_t = [t for t in final_t if CP.tkey(t) not in bt]
add_v = [v for v in final_v if CP.vkey(v) not in bv]
print('final: %d tracks, %d vias; remove %d tracks + %d vias; add %d tracks + %d vias' %
      (len(final_t), len(final_v), len(rem_t), len(rem_v), len(add_t), len(add_v)))
json.dump({'moves': [], 'remove': rem_t, 'remove_vias': rem_v}, open(out_rip, 'w'))
json.dump({'tracks': add_t, 'vias': add_v}, open(out_route, 'w'))
