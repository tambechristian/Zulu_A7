"""flatten.py <base.json> <out_rip.json> <out_route.json> step1.json [step2.json ...]
Applies edit steps (each {remove, remove_vias, tracks, vias}, any key optional) to the base model IN ORDER and
writes the net effect as compose_plan.py inputs: out_rip = the base items removed, out_route = the added items
that survive. A step's remove must match exactly one live item (base or added earlier)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import compose_plan as CP  # noqa: E402


def vrec(v):
    sp = CP.vspan(v)
    return {'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'], 'from': sp[0], 'to': sp[-1]}


def main():
    base = json.load(open(sys.argv[1]))
    live_t = [('b', t) for t in base['tracks']]
    live_v = [('b', vrec(v)) for v in base['vias']]
    rm_t, rm_v = [], []
    for f in sys.argv[4:]:
        P = json.load(open(f))
        for r in P.get('remove', []):
            k = [i for i, (o, t) in enumerate(live_t) if CP.tkey(t) == CP.tkey(r)]
            assert len(k) == 1, ('track', f, r, len(k))
            o, t = live_t.pop(k[0])
            if o == 'b':
                rm_t.append(t)
        for r in P.get('remove_vias', []):
            rk = CP.vkey(vrec(r))
            k = [i for i, (o, v) in enumerate(live_v) if CP.vkey(v) == rk]
            assert len(k) == 1, ('via', f, r, len(k))
            o, v = live_v.pop(k[0])
            if o == 'b':
                rm_v.append(v)
        live_t += [('a', dict(t)) for t in P.get('tracks', [])]
        live_v += [('a', vrec(v)) for v in P.get('vias', [])]
        print('%-28s -%d/%d +%d/%d' % (os.path.basename(f), len(P.get('remove', [])), len(P.get('remove_vias', [])),
                                       len(P.get('tracks', [])), len(P.get('vias', []))))
    add_t = [t for o, t in live_t if o == 'a']
    add_v = [v for o, v in live_v if o == 'a']
    json.dump({'remove': rm_t, 'remove_vias': rm_v}, open(sys.argv[2], 'w'), indent=0)
    json.dump({'tracks': add_t, 'vias': add_v, 'remove': [], 'remove_vias': []}, open(sys.argv[3], 'w'), indent=0)
    print('net: remove %d tracks %d vias; add %d tracks %d vias' % (len(rm_t), len(rm_v), len(add_t), len(add_v)))


if __name__ == '__main__':
    main()
