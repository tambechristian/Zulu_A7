"""finish_e2.py <router_out.json> <tag> <rip.json> <hand1.json,hand2.json,...>   (finish_e.py with hand plans)

Like finish_e.py, but every hand plan's tracks / vias are fixed copper of the final plan (their removals are already
in rip.json): merge (router copper identical to a ripped item cancels that rip), augment, compose on
prep/base_moved.json -> plan_<tag>.json, then the gates (route_check, widthcheck, prune_stubs dead copper, vias in
SMD pads over the whole board and for the plan, USB pair metrics, counts)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E  # noqa: E402
import finish_e as FE  # noqa: E402
import compose_plan as CP  # noqa: E402


def main():
    rout = E.load(sys.argv[1])
    tag = sys.argv[2]
    rip = E.load(sys.argv[3])
    hands = [E.load(p) for p in sys.argv[4].split(',') if p]
    base = E.load(FE.BASE)
    hand = {'tracks': [t for h in hands for t in h['tracks']], 'vias': [v for h in hands for v in h['vias']]}
    rip2, route = FE.merge(rout, rip, hand)
    M0 = CP.apply(base, {'remove': rip2['remove'], 'remove_vias': rip2['remove_vias'], 'tracks': route['tracks'],
                         'vias': route['vias']})
    oc0 = E.C.open_count(E.C.islands(M0))
    print('before compose: open %d %s' % (sum(oc0.values()), {k: v for k, v in oc0.items() if v}))
    route = FE.augment(base, rip2, route)
    E.dump(route, os.path.join(E.EDIR, 'route_%s.json' % tag), 0)
    E.dump(rip2, os.path.join(E.EDIR, 'rip_%s.json' % tag), 0)
    plan = FE.compose(base, rip2, route)
    E.dump(plan, os.path.join(E.EDIR, 'plan_%s.json' % tag), 1)
    g = FE.gates(plan, base, tag)
    M = CP.apply(base, plan)
    th, uv = [], []
    for v in M['vias']:
        hits = E.via_in_pads(M, v)
        if hits:
            d = '%s %.3f,%.3f %s>%s %s' % (v['net'], v['x'], v['y'], E.span(v)[0][:3], E.span(v)[-1][:3],
                                          ['%s-%s(%s)' % (p['ref'], p['pad'], p['net']) for l, p in hits])
            (th if v['size'] >= 0.349 else uv).append(d)
    g['board_through_vias_in_smd_pads'] = th
    g['board_microvias_in_smd_pads_count'] = len(uv)
    print(json.dumps(g, indent=1))


if __name__ == '__main__':
    main()
