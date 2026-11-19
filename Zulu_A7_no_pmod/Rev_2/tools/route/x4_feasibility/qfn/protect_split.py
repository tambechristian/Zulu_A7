"""protect_split.py BASE SEED NET[,NET...] OUT_BASE OUT_SEED

Moves the listed nets' seed copper into the base model (fixed copper) so diag_map/router treat it as hard."""
import json
import sys

sys.path.insert(0, __import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', '..', '..')))
import router as R  # noqa: E402

base_f, seed_f, nets, out_b, out_s = sys.argv[1:6]
nets = set(nets.split(','))
M = json.load(open(base_f))
P = json.load(open(seed_f))
kt = [t for t in P['tracks'] if t['net'] in nets]
kv = [v for v in P['vias'] if v['net'] in nets]
M['tracks'] = M['tracks'] + kt
M['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in kv]
P['tracks'] = [t for t in P['tracks'] if t['net'] not in nets]
P['vias'] = [v for v in P['vias'] if v['net'] not in nets]
json.dump(M, open(out_b, 'w'))
json.dump(P, open(out_s, 'w'))
print('moved', len(kt), 'tracks', len(kv), 'vias into base')
