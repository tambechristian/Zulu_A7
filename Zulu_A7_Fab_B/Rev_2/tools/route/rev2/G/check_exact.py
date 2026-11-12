"""check_exact.py <base_moved.json> <plan.json>: route_check with compose_plan.apply's exact (span-aware) removals.
route_check.py removes every via at a removed via's point with the same net and hole, whatever its span, so a kept
via of a partly removed column vanishes from its model. Here the board is base - plan removals (exact keys), and the
plan's new tracks / vias are checked against it."""
import json
import os
import subprocess
import sys

T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, T)
import compose_plan as CP  # noqa: E402

B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2]))
M = CP.apply(B, dict(P, tracks=[], vias=[]))
d = os.path.dirname(os.path.abspath(sys.argv[2]))
json.dump(M, open(os.path.join(d, '_exact_base.json'), 'w'))
json.dump({'tracks': P['tracks'], 'vias': P['vias']}, open(os.path.join(d, '_exact_plan.json'), 'w'))
lost = [v for v in M['vias'] if any(v['net'] == r['net'] and abs(v['x'] - r['x']) < 0.002 and abs(v['y'] - r['y']) < 0.002
                                    and abs(v['hole'] - r['hole']) < 0.002 for r in P['remove_vias'])]
print('kept vias route_check would drop:', [(v['net'], v['x'], v['y'], v['span'][0], v['span'][-1]) for v in lost])
print(subprocess.run([sys.executable, T + '/route_check.py', os.path.join(d, '_exact_plan.json'), os.path.join(d, '_exact_base.json')],
                     capture_output=True, text=True).stdout)
