"""Corner experiment (2026-10-29): move the stage-1 stubs of U1's north-east corner balls from the model (fixed) into a seed
(rippable), so the router may move the walls that seal A5 / A7 / D1 / D3 / LDQM at the fan-out.

    python tools/corner_seed.py <src model.json> <model_stage1.json> <outdir> [xmin ymin]

writes <outdir>/model.json (stubs stripped), <outdir>/stubs.json (the stubs as a rippable plan) and
<outdir>/dropped.json (what left the model, for the board chain)."""
import json
import os
import sys

PROJ = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/tools'
sys.path.insert(0, PROJ)
from swap_eval import fanout  # noqa: E402
from swap_apply import tkey, vkey  # noqa: E402

src, s1, outdir = sys.argv[1:4]
xmin = float(sys.argv[4]) if len(sys.argv) > 4 else 25.6
ymin = float(sys.argv[5]) if len(sys.argv) > 5 else 12.6
M = json.load(open(src))
S1 = json.load(open(s1))
fan = fanout(S1)
pads = {p['pad']: p for p in M['pads'] if p['ref'] == 'U1'}
corner = sorted(b for b, p in pads.items() if p['x'] >= xmin and p['y'] >= ymin)
keys = set()
for b in corner:
    if b in fan:
        keys |= {tkey(t) for t in fan[b][0]}
        keys |= {vkey(v) for v in fan[b][1]}
keep_t, keep_v, stub_t, stub_v = [], [], [], []
for t in M['tracks']:
    (stub_t if tkey(t) in keys else keep_t).append(t)
for v in M['vias']:
    (stub_v if vkey(v) in keys else keep_v).append(v)
out = dict(M, tracks=keep_t, vias=keep_v)
os.makedirs(outdir, exist_ok=True)
json.dump(out, open(os.path.join(outdir, 'model.json'), 'w'))
plan_v = [dict({k: v[k] for k in ('net', 'x', 'y', 'size', 'hole')}, **{'from': v['span'][0], 'to': v['span'][-1]}) for v in stub_v]
json.dump({'vias': plan_v, 'tracks': stub_t, 'remove': [], 'log': ['corner stubs of %s' % ' '.join(corner)]},
          open(os.path.join(outdir, 'stubs.json'), 'w'), indent=0)
json.dump({'balls': corner, 'tracks': stub_t, 'vias': stub_v}, open(os.path.join(outdir, 'dropped.json'), 'w'), indent=0)
nets = sorted({t['net'] for t in stub_t} | {v['net'] for v in stub_v})
print('%d corner balls (%d with stubs): %s' % (len(corner), sum(b in fan for b in corner), ' '.join(corner)))
print('moved %d tracks, %d vias of %d nets to the seed: %s' % (len(stub_t), len(stub_v), len(nets), ' '.join(nets)))
print('model: %d -> %d tracks, %d -> %d vias' % (len(M['tracks']), len(keep_t), len(M['vias']), len(keep_v)))
