"""Compose the strategy-C plan: transplant<variant> + zone rip + router copper, pruned to a fixpoint on base_new.

    python scripts/compose.py <variant> <router_plan.json> <out_plan.json>

remove      = transplant.remove + the zone rip's TARGET (base_cur) objects
remove_vias = transplant.remove_vias + the zone rip's TARGET vias
tracks/vias = transplant additions minus those the zone rip took back + the router's copper
then compose_plan's loop (prune_stubs.analyse on base_new - remove + add): dead plan items leave the plan, dead TARGET
items join the removals, trimmed tracks become remove + shorter track. Every list entry is checked against base_cur.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.dirname(HERE)
PREP = os.path.join(os.path.dirname(CDIR), 'prep')
sys.path.insert(0, os.path.join(CDIR, 'tools'))
import compose_plan as CP  # noqa: E402  (C/tools: TARGET's compose_plan + SOURCE's prune_stubs trim snap)
import prune_stubs as PS  # noqa: E402
import route_conn as RC  # noqa: E402
from zone import tkey, vkey, span  # noqa: E402


def take(lst, gone, key):
    c = Counter(key(o) for o in gone)
    out = []
    for o in lst:
        k = key(o)
        if c[k] > 0:
            c[k] -= 1
            continue
        out.append(o)
    assert not +c, ('not found in the plan', +c)
    return out


def pvia(v):
    s = span(v)
    return {'net': v['net'], 'x': round(v['x'], 4), 'y': round(v['y'], 4), 'size': round(v['size'], 4),
            'hole': round(v['hole'], 4), 'from': s[0], 'to': s[-1]}


def rvia(v):
    return {'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'], 'span': list(span(v))}


def ptrack(t):
    return {k: t[k] for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')}


def main():
    var, rp_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    T = json.load(open(os.path.join(PREP, 'transplant%s.json' % var)))
    Z = json.load(open(os.path.join(CDIR, 'work', 'rip%s.json' % var)))
    RP = json.load(open(rp_path))
    base = json.load(open(os.path.join(PREP, 'base_new.json')))
    for v in base['vias']:
        v['span'] = span(v)
    plan = {'moves': [],
            'remove': [ptrack(t) for t in T['remove']] + [ptrack(t) for t in Z['ripped_base_tracks']],
            'remove_vias': [rvia(v) for v in T['remove_vias']] + [rvia(v) for v in Z['ripped_base_vias']],
            'tracks': [ptrack(t) for t in take(T['tracks'], Z['ripped_add_tracks'], tkey)] + [ptrack(t) for t in RP['tracks']],
            'vias': [pvia(v) for v in take(T['vias'], Z['ripped_add_vias'], vkey)] + [pvia(v) for v in RP['vias']]}
    print('raw: remove %d/%d add %d/%d' % (len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias'])))
    for it in range(8):
        M = CP.apply(base, plan)
        dt, dv, nt, nv = PS.analyse(M)
        if not dt and not dv:
            break
        ptk, pvk = Counter(CP.tkey(t) for t in plan['tracks']), Counter(CP.vkey(v) for v in plan['vias'])
        trims = [t for t in nt if t.get('trimmed')]
        dtk = {CP.tkey(t) for t in dt}
        dvk = {CP.vkey(v) for v in dv}
        plan['tracks'] = [t for t in plan['tracks'] if CP.tkey(t) not in dtk]
        plan['vias'] = [v for v in plan['vias'] if CP.vkey(v) not in dvk]
        plan['remove'] += [ptrack(t) for t in dt if CP.tkey(t) not in ptk]
        plan['remove_vias'] += [rvia(v) for v in dv if CP.vkey(v) not in pvk]
        plan['tracks'] += [ptrack(t) for t in trims]
        print('pass %d: %d dead tracks (%d trimmed), %d dead vias' % (it + 1, len(dt), len(trims), len(dv)), flush=True)
    M = CP.apply(base, plan)
    dt, dv, _, _ = PS.analyse(M)
    oc = RC.open_count(RC.islands(M))
    # a plan item identical to a removal cancels out: keep both off the lists (emit would delete + re-add the same)
    rk = Counter(CP.tkey(t) for t in plan['remove'])
    ak = Counter(CP.tkey(t) for t in plan['tracks'])
    both = rk & ak
    if both:
        c1, c2 = Counter(both), Counter(both)
        nr, na = [], []
        for t in plan['remove']:
            if c1[CP.tkey(t)] > 0:
                c1[CP.tkey(t)] -= 1
                continue
            nr.append(t)
        for t in plan['tracks']:
            if c2[CP.tkey(t)] > 0:
                c2[CP.tkey(t)] -= 1
                continue
            na.append(t)
        plan['remove'], plan['tracks'] = nr, na
    rvk = Counter(CP.vkey(v) for v in plan['remove_vias'])
    avk = Counter(CP.vkey(v) for v in plan['vias'])
    bothv = rvk & avk
    if bothv:
        c1, c2 = Counter(bothv), Counter(bothv)
        nr, na = [], []
        for v in plan['remove_vias']:
            if c1[CP.vkey(v)] > 0:
                c1[CP.vkey(v)] -= 1
                continue
            nr.append(v)
        for v in plan['vias']:
            if c2[CP.vkey(v)] > 0:
                c2[CP.vkey(v)] -= 1
                continue
            na.append(v)
        plan['remove_vias'], plan['vias'] = nr, na
    print('cancelled identical remove+add: %d tracks, %d vias' % (sum(both.values()), sum(bothv.values())))
    M2 = CP.apply(base, plan)
    oc2 = RC.open_count(RC.islands(M2))
    print('composed: remove %d tracks + %d vias, add %d tracks + %d vias; dead after: %d tracks %d vias; open %d %s' % (
        len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias']), len(dt), len(dv),
        sum(oc2.values()), dict(sorted(oc2.items()))))
    assert sum(oc.values()) == sum(oc2.values())
    plan['_meta'] = {'strategy': 'C regional reroute x 49.0-61.0', 'transplant': 'prep/transplant%s.json' % var,
                     'router': os.path.relpath(rp_path, CDIR).replace('\\', '/'), 'base': 'prep/base_new.json (pads) / base_cur (copper)'}
    json.dump(plan, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
