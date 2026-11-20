"""seed_orig.py <variant>: the zone rip of work/rip<variant>.json as a router seed plan (work/seed_orig<variant>.json).

Loaded with router.py --seed, the ripped zone copper comes back as ROUTER copper: every non-power zone net stays
rippable (--rip / --soft can tear any of them out, and a torn net is re-routed from scratch from its live islands),
while nets nobody has to disturb keep their proven copper."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.dirname(HERE)
var = sys.argv[1] if len(sys.argv) > 1 else ''
Z = json.load(open(os.path.join(CDIR, 'work', 'rip%s.json' % var)))


def tr(t):
    return {k: t[k] for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')}


def vi(v):
    return {'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'], 'from': v['span'][0],
            'to': v['span'][-1]}


P = {'tracks': [tr(t) for t in Z['ripped_base_tracks'] + Z['ripped_add_tracks']],
     'vias': [vi(v) for v in Z['ripped_base_vias'] + Z['ripped_add_vias']], 'remove': [], 'log': ['seed: zone rip']}
json.dump(P, open(os.path.join(CDIR, 'work', 'seed_orig%s.json' % var), 'w'), indent=0)
print('seed: %d tracks, %d vias' % (len(P['tracks']), len(P['vias'])))
