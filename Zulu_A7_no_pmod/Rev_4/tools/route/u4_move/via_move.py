"""Move U4 pad 4's GND through via (43.175, 18.125) out of the moved pad into the space the pad left (2026-11-19).
Tries candidate sites, rewrites the two 0.3 mm GND tracks it carries (Top to the old pad-4 centre, where the jog
starts; Bottom to (42.7499, 17.85)), and keeps the first site route_check passes with no via in an SMD pad."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'd040')
P0 = json.load(open(os.path.join(D, 'plan_fix.json')))
OLD = {'net': 'GND', 'x': 43.175, 'y': 18.125, 'size': 0.35, 'hole': 0.2, 'from': 'Top Layer', 'to': 'Bottom Layer'}
T_TOP = {'net': 'GND', 'layer': 'Top Layer', 'w': 0.3, 'x1': 43.175, 'y1': 18.125, 'x2': 43.85, 'y2': 17.495}
T_BOT = {'net': 'GND', 'layer': 'Bottom Layer', 'w': 0.3, 'x1': 42.7499, 'y1': 17.85, 'x2': 43.175, 'y2': 18.125}
for (x, y) in [(43.175, 17.35), (43.25, 17.35), (43.10, 17.35), (43.175, 17.30), (43.30, 17.30), (43.0, 17.40)]:
    P = json.loads(json.dumps(P0))
    P['remove'] = P['remove'] + [T_TOP, T_BOT]
    P['remove_vias'] = P['remove_vias'] + [OLD]
    P['vias'].append(dict(OLD, x=x, y=y))
    P['tracks'] += [dict(T_TOP, x1=x, y1=y), dict(T_BOT, x2=x, y2=y)]
    f = os.path.join(D, 'plan_via.json')
    json.dump(P, open(f, 'w'), indent=1)
    r = subprocess.run([sys.executable, os.path.join(HERE, '..', '..', 'route_check.py'), f, os.path.join(D, 'base_moved.json')],
                       capture_output=True, text=True, cwd=os.path.join(HERE, '..', '..'))
    tail = r.stdout.strip().splitlines()[-4:]
    print((x, y), ' | '.join(tail))
    if tail and tail[-1] == 'PASS':
        break
