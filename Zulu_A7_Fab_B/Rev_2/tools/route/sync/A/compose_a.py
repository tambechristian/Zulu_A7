"""compose_a.py <transplant.json> <out_plan.json> [route_plan.json ...] [--rip rip.json ...]

ONE emit-ready Strategy-A plan relative to TARGET's current copper: the transplant's removals (+ any extra rips of TARGET
copper, each a {remove, remove_vias} json whose entries carry base_cur coordinates) and the transplant's additions +
every routing plan's tracks / vias, composed exactly as tools/compose_plan.py does (prune_stubs.analyse to a fixpoint on
base_new - removals + additions: dead plan items dropped, dead board items added to the removals, trimmed tracks
become remove + a shorter track). Plan additions that duplicate an addition already in the plan are placed once.
"""
import json
import os
import sys

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, TOOLS)
import compose_plan as CP  # noqa: E402
import route_conn as C  # noqa: E402
import importlib.util  # noqa: E402

# SOURCE's prune_stubs (2026-11-13): a one-free-end track is trimmed back to a junction anywhere within its half width
# and its new end snaps exactly onto the other track's end (TARGET's version only sees junctions on the centre line, so
# a router track that joins a stub off-centre loses the stub and then dies itself). route_conn is identical in both.
_spec = importlib.util.spec_from_file_location(
    'prune_stubs_src', 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/prune_stubs.py')
PS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PS)

A = os.path.dirname(os.path.abspath(__file__))
PREP = os.path.join(os.path.dirname(A), 'prep')


def main():
    args = sys.argv[1:]
    rips = []
    if '--rip' in args:
        k = args.index('--rip')
        rips = args[k + 1:]
        args = args[:k]
    tp, out, routes = args[0], args[1], args[2:]
    T = json.load(open(tp))
    base = json.load(open(os.path.join(PREP, 'base_new.json')))
    plan = {'moves': [], 'remove': list(T['remove']), 'remove_vias': list(T['remove_vias']),
            'tracks': list(T['tracks']), 'vias': list(T['vias'])}
    rk = {CP.tkey(t) for t in plan['remove']}
    rvk = {CP.vkey(v) for v in plan['remove_vias']}
    for f in rips:
        Rp = json.load(open(f))
        for t in Rp.get('remove', []):
            if CP.tkey(t) not in rk:
                rk.add(CP.tkey(t))
                plan['remove'].append(t)
        for v in Rp.get('remove_vias', []):
            if CP.vkey(v) not in rvk:
                rvk.add(CP.vkey(v))
                plan['remove_vias'].append(v)
    tk = {CP.tkey(t) for t in plan['tracks']}
    vk = {CP.vkey(v) for v in plan['vias']}
    for f in routes:
        P = json.load(open(f))
        for t in P['tracks']:
            t = {k: t[k] for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')}
            if CP.tkey(t) not in tk:
                tk.add(CP.tkey(t))
                plan['tracks'].append(t)
        for v in P['vias']:
            sp = CP.vspan(v)
            v = {'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'], 'from': sp[0], 'to': sp[-1]}
            if CP.vkey(v) not in vk:
                vk.add(CP.vkey(v))
                plan['vias'].append(v)
    import leafprune as LP
    import deadbranch as DB
    DB.SKIP_LOOPS = True
    bc = json.load(open(os.path.join(PREP, 'base_cur.json')))
    d0t, d0v, _ = DB.analyse(bc)                      # TARGET's own (model-artefact) branches are never touched
    k0t = {CP.tkey(t) for t in d0t}
    k0v = {CP.vkey(v) for v in d0v}
    for it in range(30):
        M = CP.apply(base, plan)
        dt, dv, nt, nv = PS.analyse(M)
        if not dt and not dv:
            cr = LP.crumbs(M)                         # tracks inside one via land that touch nothing else
            if cr:
                dt, nt = cr, []
                print('pass %d: %d crumbs inside a via land: %s' % (it + 1, len(cr), ' '.join(sorted({t['net'] for t in cr}))))
            else:
                bt, bv, _ = DB.analyse(M)             # dead branches on the endpoint graph
                bt = [t for t in bt if CP.tkey(t) not in k0t]
                bv = [v for v in bv if CP.vkey(v) not in k0v]
                if not bt and not bv:
                    break
                dt, dv, nt = bt, bv, []
                print('pass %d: dead branches %d tracks %d vias: %s' % (it + 1, len(bt), len(bv),
                                                                        ' '.join(sorted({o['net'] for o in bt + bv}))))
        ptk, pvk = {CP.tkey(t) for t in plan['tracks']}, {CP.vkey(v) for v in plan['vias']}
        trims = [t for t in nt if t.get('trimmed')]
        dtk = {CP.tkey(t) for t in dt}
        dvk = {CP.vkey(v) for v in dv}
        plan['tracks'] = [t for t in plan['tracks'] if CP.tkey(t) not in dtk]
        plan['vias'] = [v for v in plan['vias'] if CP.vkey(v) not in dvk]
        plan['remove'] += [t for t in dt if CP.tkey(t) not in ptk]
        plan['remove_vias'] += [dict(v) for v in dv if CP.vkey(v) not in pvk]
        plan['tracks'] += [{k: v for k, v in t.items() if k != 'trimmed'} for t in trims]
        print('pass %d: %d dead tracks (%d trimmed), %d dead vias' % (it + 1, len(dt), len(trims), len(dv)))
    M = CP.apply(base, plan)
    dt, dv, _, _ = PS.analyse(M)
    dt += LP.crumbs(M)
    bt, bv, _ = DB.analyse(M)
    dt += [t for t in bt if CP.tkey(t) not in k0t]
    dv += [v for v in bv if CP.vkey(v) not in k0v]
    oc = C.open_count(C.islands(M))
    # removal entries: plain route-model fields only (span for vias, as the transplant writes them)
    plan['remove'] = [{k: t[k] for k in ('net', 'layer', 'w', 'x1', 'y1', 'x2', 'y2')} for t in plan['remove']]
    plan['remove_vias'] = [{'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'],
                            'span': list(CP.vspan(v))} for v in plan['remove_vias']]
    plan['_meta'] = {'transplant': os.path.basename(tp), 'routes': [os.path.basename(f) for f in routes],
                     'rips': [os.path.basename(f) for f in rips], 'apply_to': 'base_new.json (TARGET after ECO + placement)',
                     'relative_to': 'zulu_a7_fab_b.PcbDoc md5 33023787 copper (base_cur.json)'}
    print('composed: remove %d tracks + %d vias, add %d tracks + %d vias; dead after: %d tracks %d vias; open %d %s' % (
        len(plan['remove']), len(plan['remove_vias']), len(plan['tracks']), len(plan['vias']), len(dt), len(dv),
        sum(oc.values()), oc))
    json.dump(plan, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
