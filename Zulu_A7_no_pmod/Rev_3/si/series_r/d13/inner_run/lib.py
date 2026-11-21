"""Shared helpers for the d13/inner_run designer.  Imports the exact geometry + plan-apply code from the local COPY
of d10/fold/check.py (check.py in this folder), so the fast pre-filter uses the same distance functions, rules
and apply logic as the proof run.  Nothing outside this folder is written."""
import os, sys, json, math, copy, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_PLAN = os.environ.get('INNER_BASE_PLAN', os.path.join(HERE, 'base_plan_13.json'))
_argv = sys.argv
sys.argv = [_argv[0], '--plan', BASE_PLAN, '--tag', '_lib']
sys.path.insert(0, HERE)
import check as C   # noqa: E402
sys.argv = _argv

B = C.B
CU = C.CU


def load_plan(path):
    return json.load(open(path))


def apply_plan(plan_path):
    """board + plan -> (objs, pads, tracks, vias, E) with the SDRAM-Dn relabel derived exactly as check.py does."""
    C.PLAN = plan_path
    E = C.load_plan()
    pads, tracks, vias, newflags, errors = C.apply(E)
    assert not errors, errors
    objs = C.build_objs(pads, tracks, vias, newflags)
    # derive the U3-side relabel for every net that has a part (same as check.py section 1)
    for n in sorted(E['parts']):
        fam = {'D%d' % n, 'SDRAM-D%d' % n}
        sub = [o for o in objs if o.net in fam]
        uf = C.phys_islands(sub, net_aware=False)
        isl = collections.defaultdict(list)
        for k, o in enumerate(sub):
            isl[uf.f(k)].append(o)
        u3 = [r for r, os_ in isl.items() if any(o.kind == 'pad' and o.ref == 'U3' for o in os_)]
        for r in u3:
            for o in isl[r]:
                o.net = 'SDRAM-D%d' % n
    lab = {}
    for o in objs:
        lab.setdefault(o.uid, o.net)
    for o in objs:
        o.net = lab[o.uid]
    return objs, pads, tracks, vias, E


LAYER_OUT = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}


def lay_out(L):
    return LAYER_OUT.get(L, L)
