"""Compose the Strategy B transplant + router plan(s) into ONE emit-ready plan vs TARGET's current copper.

    python B/scripts/compose_b.py <transplant_b.json> <router1.json[,router2.json...]> <out_plan.json>

plan = transplant removals (TARGET's own coordinates) + transplant additions + router tracks / vias; then TARGET's
prune_stubs.analyse is run on base_new - removals + additions to a fixpoint, exactly the compose_plan.py way: dead
plan items are dropped, dead board (TARGET) items are added to the removals, trimmed tracks become remove + a shorter
track. The composed plan must leave 0 dead copper on base_new.
"""
import json
import os
import sys

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, TOOLS)
import compose_plan as CP  # noqa: E402
import prune_stubs as PS  # noqa: E402
import route_conn as C  # noqa: E402

BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREP = os.path.join(os.path.dirname(BDIR), 'prep')


def clean_v(v):
    sp = CP.vspan(v)
    return {'net': v['net'], 'x': round(v['x'], 4), 'y': round(v['y'], 4), 'size': round(v['size'], 4),
            'hole': round(v['hole'], 4), 'from': sp[0], 'to': sp[-1]}


def clean_t(t):
    return {'net': t['net'], 'layer': t['layer'], 'w': round(t['w'], 4), 'x1': round(t['x1'], 4), 'y1': round(t['y1'], 4),
            'x2': round(t['x2'], 4), 'y2': round(t['y2'], 4)}


def main():
    tp = json.load(open(sys.argv[1]))
    routers = [json.load(open(f)) for f in sys.argv[2].split(',') if f]
    out = sys.argv[3]
    base = json.load(open(os.path.join(PREP, 'base_new.json')))
    plan = {'moves': [], 'remove': list(tp['remove']), 'remove_vias': list(tp['remove_vias']),
            'tracks': [clean_t(t) for t in tp['tracks']] + [clean_t(t) for r in routers for t in r['tracks']],
            'vias': [clean_v(v) for v in tp['vias']] + [clean_v(v) for r in routers for v in r['vias']]}
    n_router = (sum(len(r['tracks']) for r in routers), sum(len(r['vias']) for r in routers))
    # exact duplicates inside the additions are placed once
    seen, tr = set(), []
    for t in plan['tracks']:
        k = CP.tkey(t)
        if k not in seen:
            seen.add(k)
            tr.append(t)
    plan['tracks'] = tr
    seen, vs = set(), []
    for v in plan['vias']:
        k = CP.vkey(v)
        if k not in seen:
            seen.add(k)
            vs.append(v)
    plan['vias'] = vs
    log = []
    for it in range(8):
        M = CP.apply(base, plan)
        dt, dv, nt, nv = PS.analyse(M)
        if not dt and not dv:
            break
        ptk, pvk = {CP.tkey(t) for t in plan['tracks']}, {CP.vkey(v) for v in plan['vias']}
        trims = [t for t in nt if t.get('trimmed')]
        dtk = {CP.tkey(t) for t in dt}
        dvk = {CP.vkey(v) for v in dv}
        plan['tracks'] = [t for t in plan['tracks'] if CP.tkey(t) not in dtk]
        plan['vias'] = [v for v in plan['vias'] if CP.vkey(v) not in dvk]
        plan['remove'] += [clean_t(t) for t in dt if CP.tkey(t) not in ptk]
        plan['remove_vias'] += [{'net': v['net'], 'x': round(v['x'], 4), 'y': round(v['y'], 4), 'size': round(v['size'], 4),
                                 'hole': round(v['hole'], 4), 'span': list(CP.vspan(v))}
                                for v in dv if CP.vkey(v) not in pvk]
        plan['tracks'] += [clean_t(t) for t in trims]
        log.append('pass %d: %d dead tracks (%d trimmed), %d dead vias' % (it + 1, len(dt), len(trims), len(dv)))
        print(log[-1])
    M = CP.apply(base, plan)
    dt, dv, _, _ = PS.analyse(M)
    oc = C.open_count(C.islands(M))
    plan['_meta'] = dict(tp.get('_meta', {}))
    plan['_meta'].update({'composed_from': [os.path.basename(sys.argv[1])] + [os.path.basename(f) for f in sys.argv[2].split(',') if f],
                          'router_tracks_vias_in': list(n_router), 'compose_log': log,
                          'apply_to': 'base_new.json (TARGET after the ECO + placement); removals are TARGET 33023787 copper'})
    if 'seeded_to_router' in plan['_meta']:
        plan['_meta']['strategy'] = (
            'B: SOURCE Pmod-zone routes kept; every track/via of the JA nets that clash with them ripped (JA7 kept); '
            'the JA nets, and the seeded SOURCE zone copper the router had to move (%s east of x %.1f), re-routed with '
            'B/scripts/exact_router.py' % (', '.join(plan['_meta']['seeded_to_router']['nets']),
                                           plan['_meta']['seeded_to_router']['xmin']))
    print('composed: remove %d tracks + %d vias, add %d tracks + %d vias; dead after: %d tracks %d vias; open %d %s' % (
        len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias']), len(dt), len(dv),
        sum(oc.values()), oc))
    json.dump(plan, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
