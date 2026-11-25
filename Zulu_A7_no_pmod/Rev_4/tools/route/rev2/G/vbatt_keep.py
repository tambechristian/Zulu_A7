"""vbatt_keep.py <in_plan> <out_plan>: keep the Rev 1 VBATT Bottom stub (12.0,2.44)-(12.7,2.3) w0.4 that prune_stubs
calls dead (its free end overlaps the end of (9.975,3.325)-(12.0,2.625) by 0.185 mm, which Altium accepts but
prune_stubs' 0.01 mm join does not). Instead of removing pre-existing copper far from the change, a 0.185 mm connector
(12.0,2.44)-(12.0,2.625) w0.4, entirely inside existing VBATT copper, makes the junction explicit."""
import json
import sys

P = json.load(open(sys.argv[1]))
n = len(P['remove'])
P['remove'] = [t for t in P['remove'] if not (t['net'] == 'VBATT' and abs(t['x1'] - 12.0) < 1e-6 and abs(t['y1'] - 2.44) < 1e-6
                                              and abs(t['x2'] - 12.7) < 1e-6 and abs(t['y2'] - 2.3) < 1e-6)]
assert len(P['remove']) == n - 1
P['tracks'].append({'net': 'VBATT', 'layer': 'Bottom Layer', 'w': 0.4, 'x1': 12.0, 'y1': 2.44, 'x2': 12.0, 'y2': 2.625})
json.dump(P, open(sys.argv[2], 'w'), indent=1)
print('VBATT stub kept, connector added')
