"""Move every track and via of the given nets out of a router model into a rippable seed plan (2026-10-31), so a
tie_cut.py cut and a --rip 0 pass can re-join them locally while everything else stays fixed.

    python tools/net_seed.py <model.json> <net[,net...]> <outdir>

Writes <outdir>/model.json (those nets' copper stripped), <outdir>/seed.json (that copper as a plan, vias with
from/to) and <outdir>/dropped.json (what left the model, keyed like the model, for the board chain)."""
import json
import os
import sys


def main():
    src, nets, outdir = sys.argv[1:4]
    nets = set(nets.split(','))
    M = json.load(open(src))
    keep_t = [t for t in M['tracks'] if t['net'] not in nets]
    move_t = [t for t in M['tracks'] if t['net'] in nets]
    keep_v = [v for v in M['vias'] if v['net'] not in nets]
    move_v = [v for v in M['vias'] if v['net'] in nets]
    os.makedirs(outdir, exist_ok=True)
    json.dump(dict(M, tracks=keep_t, vias=keep_v), open(os.path.join(outdir, 'model.json'), 'w'))
    plan_v = [dict({k: v[k] for k in ('net', 'x', 'y', 'size', 'hole')}, **{'from': v['span'][0], 'to': v['span'][-1]})
              for v in move_v]
    json.dump({'vias': plan_v, 'tracks': move_t, 'remove': [],
               'log': ['copper of %s moved out of %s as a seed' % (','.join(sorted(nets)), os.path.basename(src))]},
              open(os.path.join(outdir, 'seed.json'), 'w'), indent=0)
    json.dump({'tracks': move_t, 'vias': move_v}, open(os.path.join(outdir, 'dropped.json'), 'w'), indent=0)
    print('%s: moved %d tracks, %d vias of %s; model %d -> %d tracks, %d -> %d vias' % (
        outdir, len(move_t), len(move_v), ','.join(sorted(nets)), len(M['tracks']), len(keep_t), len(M['vias']),
        len(keep_v)))


if __name__ == '__main__':
    main()
