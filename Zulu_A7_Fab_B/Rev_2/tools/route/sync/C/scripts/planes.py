"""planes.py <tag> [<tag> ...]: L2-GND / L5-VCC3V3 plane web (route/rev2/judge/planeweb.run) of base_cur and of
C/out/<tag>/result.json; writes C/out/planeweb.json and prints components / plane-net objects off the main pour."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.dirname(HERE)
PREP = os.path.join(os.path.dirname(CDIR), 'prep')
sys.path.insert(0, os.path.join(PREP, 'scripts'))
import geo  # noqa: E402,F401
import planeweb as PW  # noqa: E402  (on sys.path through geo: route/rev2/judge)

R = {}
for name, path in [('base_cur', os.path.join(PREP, 'base_cur.json'))] + \
        [(k, os.path.join(CDIR, 'out', k, 'result.json')) for k in sys.argv[1:]]:
    M = json.load(open(path))
    for v in M['vias']:
        v['span'] = PW.J.span(v)
    R[name] = PW.run(M, name)
json.dump(R, open(os.path.join(CDIR, 'out', 'planeweb.json'), 'w'), indent=1)
for k, d in R.items():
    for layer, res in d.items():
        for mode, r in res.items():
            print(k, layer, mode, 'comps', r['components'], 'comps w/ net objs', r['components_with_net_objects'],
                  'main mm2', r['main_area_mm2'], 'objs', r['objects'], 'off-main', len(r['objects_off_main']),
                  r['objects_off_main'][:6])
