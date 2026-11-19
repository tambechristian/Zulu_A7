"""Replace the router's new VBATT through-via with the nearby existing one."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
source = os.path.join(HERE, 'route_final.json')
target = os.path.join(HERE, 'route_final_reuse_via.json')
plan = json.load(open(source))

old = (17.1, 2.75)
existing = (17.075, 3.0)
before = len(plan['vias'])
plan['vias'] = [
    via for via in plan['vias']
    if not (
        via['net'] == 'VBATT' and
        abs(via['x'] - old[0]) < 1e-6 and
        abs(via['y'] - old[1]) < 1e-6
    )
]
assert len(plan['vias']) == before - 1

changed = 0
for track in plan['tracks']:
    if track['net'] != 'VBATT':
        continue
    for suffix in ('1', '2'):
        xkey, ykey = 'x' + suffix, 'y' + suffix
        if abs(track[xkey] - old[0]) < 1e-6 and abs(track[ykey] - old[1]) < 1e-6:
            track[xkey], track[ykey] = existing
            changed += 1
assert changed == 2

json.dump(plan, open(target, 'w'), indent=1)
print('removed 1 new VBATT via and joined %d track ends to the existing via' % changed)
