"""Post-process a complete stage-7 plan into the files that go on the board (2026-11-05).

    python tools/plan_final.py <plan.json> <vip.json> <model_bare.json> <outdir>

The plan was routed on model = model_bare + vip (the via-in-pad fan-out as fixed vias). Here the fan-out and the plan
are treated as ONE set of copper on the bare model, then:
  1. exact duplicates dropped (plan_dedupe keys)
  2. every via that shares its point with a same-net through via dropped (Altium flags the pair as Hole To Hole)
  3. dead ends pruned (plan_prune): stub tails and vias that touch at most one other thing of their net -- this is
     what removes the unused fan-out columns, which Altium would list as Net Antennae
  4. split back into <outdir>/vip.final.json (what is left of the fan-out) and <outdir>/plan.final.json, and
     <outdir>/model.final.json = model_bare + vip.final, the model the final plan must pass route_check on
Refuses if the plan has 'remove' entries, a via with from/to out of order, or a laser pair that is neither 0.30/0.15
nor 0.25/0.10. Prints NV / NT / NE (vias, tracks, laser vias to mark) for the board guards."""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import plan_prune as PP  # noqa: E402
from route_check import span, STACK  # noqa: E402

LASER_PAIRS = {('Top Layer', 'L2-GND'), ('L2-GND', 'L3-SIG'), ('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom Layer')}


def vkey(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4), v['from'], v['to'])


def main():
    plan_f, vip_f, bare_f, outdir = sys.argv[1:5]
    P, V, M = json.load(open(plan_f)), json.load(open(vip_f)), json.load(open(bare_f))
    if P.get('remove') or P.get('remove_vias') or M['tracks'] or M['vias']:
        sys.exit('REFUSED: the plan has remove entries or the bare model is not bare')
    os.makedirs(outdir, exist_ok=True)
    vip_keys = {vkey(v) for v in V['vias']}
    log = []
    # 1. dedupe
    seen, vias, tracks = set(), [], []
    for v in V['vias'] + P['vias']:
        if STACK.index(v['from']) >= STACK.index(v['to']):
            sys.exit('REFUSED: via from/to out of order: %s' % v)
        pair = (v['from'], v['to'])
        if pair in LASER_PAIRS and (round(v['size'], 3), round(v['hole'], 3)) not in ((0.3, 0.15), (0.25, 0.1)):
            sys.exit('REFUSED: laser via of an unknown family: %s' % v)
        k = vkey(v)
        if k not in seen:
            seen.add(k)
            vias.append(v)
    for t in P['tracks']:
        k = (t['net'], t['layer'], round(t['w'], 3),
             tuple(sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))])))
        if k not in seen:
            seen.add(k)
            tracks.append(t)
    log.append('dedupe: %d -> %d vias, %d -> %d tracks' % (len(V['vias']) + len(P['vias']), len(vias),
                                                           len(P['tracks']), len(tracks)))
    nets = {p['net'] for p in M['pads'] if p['net']}
    bad = sorted({o['net'] for o in vias + tracks} - nets)
    if bad:
        sys.exit('REFUSED: nets not on the board: %s' % ' '.join(bad))
    # 2. stacks on a through via
    thr = {(v['net'], round(v['x'], 4), round(v['y'], 4)) for v in vias
           if v['from'] == 'Top Layer' and v['to'] == 'Bottom Layer'}
    keep = [v for v in vias if (v['from'] == 'Top Layer' and v['to'] == 'Bottom Layer') or
            (v['net'], round(v['x'], 4), round(v['y'], 4)) not in thr]
    for v in vias:
        if v not in keep:
            log.append('through-stack: dropped %s %s>%s at %.4f,%.4f' % (v['net'], v['from'], v['to'], v['x'], v['y']))
    vias = keep
    # 3. prune, net by net, with the island count as the guard
    plane_of = {net: lay for lay, net in M['planes'].items()}
    bt, bv = defaultdict(list), defaultdict(list)
    for t in tracks:
        bt[t['net']].append(t)
    for v in vias:
        bv[v['net']].append(v)
    out_t, out_v = [], []
    for net in sorted(set(bt) | set(bv)):
        pads = [p for p in M['pads'] if p['net'] == net]

        def count(tr, vi):
            Mn = {'pads': pads, 'tracks': tr, 'vias': [dict(v, span=span(v)) for v in vi], 'planes': M['planes']}
            return len(C.islands(Mn).get(net, []))
        nt, nv = PP.prune_net(net, pads, [], [], bt[net], bv[net], plane_of.get(net))
        if count(nt, nv) != count(bt[net], bv[net]):
            log.append('prune: %s left alone (its islands would change)' % net)
            nt, nv = bt[net], bv[net]
        elif len(nt) != len(bt[net]) or len(nv) != len(bv[net]) or any(a != b for a, b in zip(nt, bt[net])):
            log.append('prune: %s %d -> %d tracks, %d -> %d vias' % (net, len(bt[net]), len(nt), len(bv[net]), len(nv)))
        out_t += nt
        out_v += nv
    vip_final = [v for v in out_v if vkey(v) in vip_keys]
    plan_v = [v for v in out_v if vkey(v) not in vip_keys]
    lasers = sum(1 for v in out_v if (v['from'], v['to']) in LASER_PAIRS)
    json.dump({'vias': vip_final, 'tracks': [], 'remove': [],
               'log': ['fan-out of %s after plan_final: %d of %d vias kept' % (os.path.basename(vip_f), len(vip_final),
                                                                            len(V['vias']))]},
              open(os.path.join(outdir, 'vip.final.json'), 'w'), indent=0)
    json.dump({'vias': plan_v, 'tracks': out_t, 'remove': [], 'log': P.get('log', []) + log},
              open(os.path.join(outdir, 'plan.final.json'), 'w'), indent=0)
    json.dump(dict(M, vias=[dict(v, span=span(v)) for v in vip_final]),
              open(os.path.join(outdir, 'model.final.json'), 'w'))
    for l in log:
        print(l)
    print('vip.final %d vias (of %d); plan.final %d vias, %d tracks' % (len(vip_final), len(V['vias']), len(plan_v),
                                                                       len(out_t)))
    print('NV %d  NT %d  NE %d' % (len(out_v), len(out_t), lasers))


if __name__ == '__main__':
    main()
