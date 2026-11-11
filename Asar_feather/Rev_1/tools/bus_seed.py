"""move a placed plan's copper (the SDRAM bus) out of a router model into a rippable seed, so a pass may move it

    python tools/bus_seed.py <model.json> <plan.json> <outdir>

writes <outdir>/model.json (the plan's copper stripped), <outdir>/bus.json (that copper as a plan, vias from/to)
and <outdir>/dropped.json (what left the model, keyed like the model, for the board chain)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from swap_apply import tkey, vkey  # noqa: E402


def main():
    src, plan, outdir = sys.argv[1:4]
    M = json.load(open(src))
    P = json.load(open(plan))
    keys = {tkey(t) for t in P['tracks']} | {vkey(v) for v in P['vias']}
    keep_t, keep_v, bus_t, bus_v = [], [], [], []
    for t in M['tracks']:
        (bus_t if tkey(t) in keys else keep_t).append(t)
    for v in M['vias']:
        (bus_v if vkey(v) in keys else keep_v).append(v)
    os.makedirs(outdir, exist_ok=True)
    json.dump(dict(M, tracks=keep_t, vias=keep_v), open(os.path.join(outdir, 'model.json'), 'w'))
    plan_v = [dict({k: v[k] for k in ('net', 'x', 'y', 'size', 'hole')}, **{'from': v['span'][0], 'to': v['span'][-1]})
              for v in bus_v]
    json.dump({'vias': plan_v, 'tracks': bus_t, 'remove': [], 'log': ['bus copper of %s as a seed' % os.path.basename(plan)]},
              open(os.path.join(outdir, 'bus.json'), 'w'), indent=0)
    json.dump({'tracks': bus_t, 'vias': bus_v}, open(os.path.join(outdir, 'dropped.json'), 'w'), indent=0)
    nets = sorted({t['net'] for t in bus_t} | {v['net'] for v in bus_v})
    print('plan: %d tracks, %d vias; matched in the model: %d tracks, %d vias of %d nets' % (
        len(P['tracks']), len(P['vias']), len(bus_t), len(bus_v), len(nets)))
    print('model: %d -> %d tracks, %d -> %d vias' % (len(M['tracks']), len(keep_t), len(M['vias']), len(keep_v)))


if __name__ == '__main__':
    main()
