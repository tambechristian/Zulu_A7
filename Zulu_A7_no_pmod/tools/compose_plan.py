"""Compose rip + router plan + stub prune into one emit_copper plan, and prove it on the untouched board model.

    python tools/compose_plan.py <base_model.json> <rip.json> <route_plan.json> <out_plan.json>

The router joins new copper onto whatever survives the rip, so tails the rip clipped can be left dangling (Altium
'Net Antennae'). prune_stubs.analyse() is run on base - rip + plan; dead plan items are dropped from the plan, dead
board items are added to the removals, and trimmed tracks become remove + a shorter new track. The composed plan is
then applied to the base model and must leave 0 dead copper.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

STACK = PS.STACK


def vspan(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def tkey(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4), round(t['w'], 4))


def vkey(v):
    sp = vspan(v)
    return (v['net'], round(v['x'], 4), round(v['y'], 4), sp[0], sp[-1])


def apply(base, plan):
    M = dict(base)
    rt, rv = {tkey(t) for t in plan.get('remove', [])}, {vkey(v) for v in plan.get('remove_vias', [])}
    M['tracks'] = [t for t in base['tracks'] if tkey(t) not in rt] + [dict(t) for t in plan['tracks']]
    M['vias'] = [v for v in base['vias'] if vkey(v) not in rv] + [dict(v, span=vspan(v)) for v in plan['vias']]
    if 'moves' in plan:
        M['pads'] = [dict(p) for p in base['pads']]
        for m in plan['moves']:
            for p in M['pads']:
                if p['ref'] == m['ref']:
                    p['x'] = round(p['x'] + m.get('dx', 0), 4)
                    p['y'] = round(p['y'] + m.get('dy', 0), 4)
    return M


def main():
    base, rip, rp, out = [json.load(open(a)) for a in sys.argv[1:4]] + [sys.argv[4]]
    plan = {'moves': rip.get('moves', []), 'remove': list(rip['remove']), 'remove_vias': list(rip['remove_vias']),
            'tracks': list(rp['tracks']), 'vias': list(rp['vias'])}
    for it in range(5):
        M = apply(base, plan)
        dt, dv, nt, nv = PS.analyse(M)
        if not dt and not dv:
            break
        ptk, pvk = {tkey(t) for t in plan['tracks']}, {vkey(v) for v in plan['vias']}
        trims = [t for t in nt if t.get('trimmed')]
        dtk = {tkey(t) for t in dt}
        dvk = {vkey(v) for v in dv}
        plan['tracks'] = [t for t in plan['tracks'] if tkey(t) not in dtk]
        plan['vias'] = [v for v in plan['vias'] if vkey(v) not in dvk]
        plan['remove'] += [t for t in dt if tkey(t) not in ptk]
        plan['remove_vias'] += [v for v in dv if vkey(v) not in pvk]
        plan['tracks'] += [{k: v for k, v in t.items() if k != 'trimmed'} for t in trims]
        print('pass %d: %d dead tracks (%d trimmed), %d dead vias' % (it + 1, len(dt), len(trims), len(dv)))
    M = apply(base, plan)
    dt, dv, _, _ = PS.analyse(M)
    oc = C.open_count(C.islands(M))
    print('composed: remove %d tracks + %d vias, add %d tracks + %d vias, %d moves; dead after: %d tracks %d vias; open %d %s' % (
        len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias']), len(plan['moves']),
        len(dt), len(dv), sum(oc.values()), oc))
    json.dump(plan, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
