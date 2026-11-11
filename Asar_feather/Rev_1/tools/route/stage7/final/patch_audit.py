"""Stage 7, 2026-11-05: the fixes the independent audit validated, applied to plan.final.json -> plan.patched.json.
    python tools/route/stage7/final/patch_audit.py <dead_copper.json>
  1. dead copper: 48 tracks + 3 vias (kill list; includes the 4-track floating GND island route_conn cannot see)
  2. overhangs trimmed: CHAN22 L4 to 30.15,20.05; SD-CMD Top to 20.65,15.675; A12 L3 to 34.9,9.4
  3. C113-2: the GND Bottom track that grazes the pad corner by 12.8 um ends at the pad centre instead
  4. A13: GNDADC through via off the ball land, 22.95,7.025 -> 23.03,7.121 (tracks still end inside its land)
  5. power: VCC3V3 L5>Bottom lasers on L1-2 (3), C80-2 (2), U5-4 (1); GND through vias on U8-17 (2), U5-2, U6-2
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, 'plan.final.json')))
dead = json.load(open(sys.argv[1]))


def kt(t):
    return (t['net'], t['layer'], tuple(sorted([(round(t['x1'], 4), round(t['y1'], 4)), (round(t['x2'], 4), round(t['y2'], 4))])))


def kv(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4), v['from'], v['to'])


kill_t = {kt(o) for o in dead if 'x1' in o}
kill_v = {kv(o) for o in dead if 'x1' not in o}
nt, nv = len(P['tracks']), len(P['vias'])
P['tracks'] = [t for t in P['tracks'] if kt(t) not in kill_t]
P['vias'] = [v for v in P['vias'] if kv(v) not in kill_v]
assert nt - len(P['tracks']) == len(kill_t) == 48 and nv - len(P['vias']) == len(kill_v) == 3


def move_end(net, layer, a, b, frm, to):
    """the track a-b of the net: its end frm goes to the point to"""
    hit = [t for t in P['tracks'] if kt(t) == (net, layer, tuple(sorted([a, b])))]
    assert len(hit) == 1, (net, a, b, hit)
    t = hit[0]
    if (round(t['x1'], 4), round(t['y1'], 4)) == frm:
        t['x1'], t['y1'] = to
    else:
        assert (round(t['x2'], 4), round(t['y2'], 4)) == frm
        t['x2'], t['y2'] = to


move_end('CHAN22', 'L4-SIG', (30.65, 20.55), (29.35, 19.25), (29.35, 19.25), (30.15, 20.05))
move_end('SD-CMD', 'Top Layer', (20.65, 14.325), (20.65, 16.025), (20.65, 16.025), (20.65, 15.675))
move_end('A12', 'L3-SIG', (35.375, 8.975), (34.65, 9.65), (34.65, 9.65), (34.9, 9.4))
move_end('GND', 'Bottom Layer', (27.8855, 15.5093), (26.7, 14.3), (27.8855, 15.5093), (28.05, 15.68))

# found by re-running the audit on the patched plan: the kill list left an unused stack (the two L3 tracks already
# meet at its centre) and a track that lies wholly inside C116-2
gone = {('AIN15_N', 25.075, 11.6, 'Top Layer', 'L2-GND'), ('AIN15_N', 25.075, 11.6, 'L2-GND', 'L3-SIG')}
n = len(P['vias'])
P['vias'] = [v for v in P['vias'] if kv(v) not in gone]
assert n - len(P['vias']) == 2
n = len(P['tracks'])
P['tracks'] = [t for t in P['tracks'] if kt(t) != ('GND', 'Bottom Layer', ((29.15, 17.125), (29.15, 17.15)))]
assert n - len(P['tracks']) == 1

hit = [v for v in P['vias'] if kv(v) == ('GNDADC', 22.95, 7.025, 'Top Layer', 'Bottom Layer')]
assert len(hit) == 1
hit[0]['x'], hit[0]['y'] = 23.03, 7.121

for x, y in ((14.175, 19.35), (14.575, 19.35), (14.975, 19.35), (16.53, 18.9), (16.93, 18.9), (12.925, 16.9)):
    P['vias'].append({'net': 'VCC3V3', 'x': x, 'y': y, 'size': 0.3, 'hole': 0.15, 'from': 'L5-VCC3V3', 'to': 'Bottom Layer'})
for x, y in ((2.335, 9.235), (2.56, 10.16), (11.975, 15.6), (11.975, 19.6)):
    P['vias'].append({'net': 'GND', 'x': x, 'y': y, 'size': 0.35, 'hole': 0.2, 'from': 'Top Layer', 'to': 'Bottom Layer'})
P.setdefault('log', []).append('patch_audit: dead copper, overhangs, C113-2, A13, 10 power vias')
json.dump(P, open(os.path.join(HERE, 'plan.patched.json'), 'w'), indent=0)
print('plan.patched.json: %d vias, %d tracks' % (len(P['vias']), len(P['tracks'])))
