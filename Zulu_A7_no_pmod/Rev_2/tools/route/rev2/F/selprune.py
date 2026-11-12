"""selprune.py <model.json> <plan.json> <out_model.json> <out_rip.json>
Bakes a router plan into the model, then prunes dead copper (prune_stubs.analyse) ONLY on nets that are fully
connected (0 open connections); open nets keep their dangling copper (it is what the router still joins onto).
Writes the pruned model and the pruning as a step {remove, remove_vias, tracks (trimmed replacements)}."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import compose_plan as CP  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402
import aug  # noqa: E402


def main():
    M = json.load(open(sys.argv[1]))
    P = json.load(open(sys.argv[2]))
    for v in M['vias']:
        v['span'] = CP.vspan(v)
    con = aug.connectors(M['tracks'] + P['tracks'], P['tracks'], P['vias'])
    print('connectors added: %d' % len(con))
    P = dict(P, tracks=P['tracks'] + con)
    json.dump(P, open(sys.argv[2].replace('.json', '_aug.json'), 'w'), indent=0)
    M['tracks'] = M['tracks'] + [dict(t) for t in P['tracks']]
    M['vias'] = M['vias'] + [dict(v, span=CP.vspan(v)) for v in P['vias']]
    oc = C.open_count(C.islands(M))
    closed = {t['net'] for t in M['tracks']} | {v['net'] for v in M['vias']}
    closed -= set(oc)
    sub = dict(M, tracks=[t for t in M['tracks'] if t['net'] in closed], vias=[v for v in M['vias'] if v['net'] in closed])
    dt, dv, nt, nv = PS.analyse(sub)
    trims = [{k: v for k, v in t.items() if k != 'trimmed'} for t in nt if t.get('trimmed')]
    dtk, dvk = {CP.tkey(t) for t in dt}, {CP.vkey(v) for v in dv}
    out = dict(M, tracks=[t for t in M['tracks'] if CP.tkey(t) not in dtk] + trims,
               vias=[v for v in M['vias'] if CP.vkey(v) not in dvk])
    # the removals as a step on the baked model: dead tracks / vias (trimmed ones are removed and re-added shorter)
    step = {'remove': dt, 'remove_vias': [dict(v, **{'from': v['span'][0], 'to': v['span'][-1]}) for v in dv],
            'tracks': trims, 'vias': []}
    json.dump(out, open(sys.argv[3], 'w'))
    json.dump(step, open(sys.argv[4], 'w'), indent=0)
    nets = {}
    for t in dt:
        nets[t['net']] = nets.get(t['net'], 0) + 1
    oc2 = C.open_count(C.islands(out))
    print('pruned %d tracks (%d trimmed), %d vias on closed nets %s; open before %d after %d' % (
        len(dt), len(trims), len(dv), nets, sum(oc.values()), sum(oc2.values())))


if __name__ == '__main__':
    main()
