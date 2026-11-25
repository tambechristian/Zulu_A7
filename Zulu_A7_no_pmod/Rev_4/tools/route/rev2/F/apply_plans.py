"""apply_plans.py <model_in.json> <model_out.json> plan1.json [plan2.json ...] [--drop-orphans orphans.json]
Bakes plans (remove / remove_vias / tracks / vias) into a model; every remove must match exactly one item.
--drop-orphans: also removes copper islands that reach no pad and no pour (they are dead copper in the final
plan anyway, and only block routing) and writes them as a rip {remove, remove_vias}."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import compose_plan as CP  # noqa: E402
import route_conn as C  # noqa: E402

STACK = CP.STACK


def orphans(M):
    """tracks / vias of copper groups with no pad and no pour"""
    pads = M['pads']
    keep_t, keep_v = set(), set()
    for net, gs in C.islands(M).items():
        for g in gs:
            keep_t |= set(g['tracks'])
            keep_v |= set(g['vias'])
    return [i for i in range(len(M['tracks'])) if i not in keep_t], [i for i in range(len(M['vias'])) if i not in keep_v]


def main():
    args = sys.argv[1:]
    orph = None
    if '--drop-orphans' in args:
        k = args.index('--drop-orphans')
        orph = args[k + 1]
        del args[k:k + 2]
    M = json.load(open(args[0]))
    for v in M['vias']:
        if 'span' not in v:
            v['span'] = CP.vspan(v)
    for f in args[2:]:
        P = json.load(open(f))
        for r in P.get('remove', []):
            k = [i for i, t in enumerate(M['tracks']) if CP.tkey(t) == CP.tkey(r)]
            assert len(k) == 1, ('remove track', f, r, len(k))
            del M['tracks'][k[0]]
        for r in P.get('remove_vias', []):
            rr = dict(r, span=CP.vspan(r))
            k = [i for i, v in enumerate(M['vias']) if CP.vkey(v) == CP.vkey(rr)]
            assert len(k) == 1, ('remove via', f, r, len(k))
            del M['vias'][k[0]]
        M['tracks'] += [dict(t) for t in P['tracks']]
        M['vias'] += [dict(v, span=CP.vspan(v)) for v in P['vias']]
        print('%s: -%d tracks -%d vias +%d tracks +%d vias' % (f, len(P.get('remove', [])), len(P.get('remove_vias', [])),
                                                              len(P['tracks']), len(P['vias'])))
    if orph:
        ot, ov = orphans(M)
        rip = {'remove': [M['tracks'][i] for i in ot], 'remove_vias': [M['vias'][i] for i in ov]}
        for t in rip['remove']:
            print('orphan T %-12s %-12s (%.3f,%.3f)-(%.3f,%.3f)' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']))
        for v in rip['remove_vias']:
            print('orphan V %-12s (%.3f,%.3f) %s>%s' % (v['net'], v['x'], v['y'], v['span'][0], v['span'][-1]))
        M['tracks'] = [t for i, t in enumerate(M['tracks']) if i not in set(ot)]
        M['vias'] = [v for i, v in enumerate(M['vias']) if i not in set(ov)]
        json.dump(rip, open(orph, 'w'), indent=0)
    json.dump(M, open(args[1], 'w'))
    oc = C.open_count(C.islands(M))
    print('model %s: %d tracks %d vias; open %d on %d nets' % (args[1], len(M['tracks']), len(M['vias']), sum(oc.values()),
                                                            len(oc)))


if __name__ == '__main__':
    main()
