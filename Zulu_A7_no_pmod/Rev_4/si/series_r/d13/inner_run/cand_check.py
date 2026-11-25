"""Batch proof: for each candidate (net, index) build base 13-R plan + that one candidate and run the UNCHANGED
check.py (local copy) main() on it; write a verdict line per candidate to proof_<worker>.jsonl.
usage: python cand_check.py <worker> <nworkers> [nets]"""
import sys, os, json, time, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
W, NW = int(sys.argv[1]), int(sys.argv[2])
NETS = sys.argv[3].split(',') if len(sys.argv) > 3 else ['D13', 'D14', 'D15']
sys.argv = [sys.argv[0], '--plan', os.path.join(HERE, 'base_plan_13.json'), '--tag', 'x']
sys.path.insert(0, HERE)
import check as C
import plan_tools as PT
import io, contextlib
base = json.load(open(os.path.join(HERE, 'base_plan_13.json')))
# --- speed-up only: memoise pour() and phys_islands() on the exact object content (the 'before' board is identical
#     for every candidate, so its pours/islands/shorts are computed once).  Results are bit-identical by construction.
_pour, _isl = C.pour, C.phys_islands
_PC, _IC = {}, {}
def _sig(objs):
    return hash(tuple((o.layer, o.net, o.shape, o.uid, o.kind) for o in objs))
def pour_m(objs, L):
    k = (_sig([o for o in objs if o.layer == L]), L)
    if k not in _PC:
        if len(_PC) > 8:
            _PC.clear()
        _PC[k] = _pour(objs, L)
    return _PC[k]
def isl_m(objs, net_aware=True, plane_join=None):
    k = (_sig(objs), net_aware, None if not plane_join else tuple((L, id(v[0]), v[1]) for L, v in sorted(plane_join.items())))
    if k not in _IC:
        if len(_IC) > 8:
            _IC.clear()
        _IC[k] = _isl(objs, net_aware, plane_join)
    return _IC[k]
C.pour, C.phys_islands = pour_m, isl_m
tmp = tempfile.mkdtemp(prefix='cc%d_' % W, dir=os.path.join(HERE, 'tmp'))
C.HERE = tmp
jobs = []
for net in NETS:
    pf = json.load(open(os.path.join(HERE, 'prefilter_%s.json' % net)))
    for i, c in enumerate(pf['candidates']):
        jobs.append((net, i, c))
jobs = jobs[W::NW]
done = set()
outp = os.path.join(HERE, 'proofs', 'proof_%d.jsonl' % W)
import glob
for fp in glob.glob(os.path.join(HERE, 'proofs', 'proof_*.jsonl')):
    for line in open(fp):
        try:
            r = json.loads(line)
            if 'error' not in r:
                done.add((r['net'], r['i']))
        except Exception:
            pass
f = open(outp, 'a')


def verdict(out, net, ref):
    v = {}
    v['apply_errors'] = len(out['apply_errors'])
    v['split_ok'] = all(r['ok'] for r in out['split'].values())
    v['split_net_ok'] = out['split'].get(net, {}).get('ok')
    v['new_shorts'] = len(out['shorts']['new'])
    pl = out['planes']
    v['pour_islands'] = {L: pl[L]['live_islands_after'] for L in pl}
    v['pour_off_main_new'] = {L: len(set(pl[L]['objects_off_main_after']) - set(pl[L]['objects_off_main_before'])) for L in pl}
    v['pour_neck_new'] = {L: len(set(pl[L]['off_main_through_necks_lt_0p10_after']) - set(pl[L]['off_main_through_necks_lt_0p10_before'])) for L in pl}
    v['pour_slivers'] = {L: len(pl[L]['new_sub_0p10_slivers']) for L in pl}
    v['worse_islands'] = out['net_islands']['worse']
    v['antennae'] = len(out['antennae'])
    v['clearance_viol'] = len(out['clearance']['violations'])
    v['h2h_viol'] = len(out['hole_to_hole']['violations'])
    v['width_viol'] = len(out['width'])
    v['mask_viol'] = len(out['mask']['violations'])
    v['acid'] = len(out['acid_traps'])
    v['silk_bad'] = len([s for s in out['silk'] if not s['ok']])
    alt = [a for a in out['altium_component_clearance'] if a['ref'] == ref]
    v['compclear'] = alt[0]['nearest'][:2] if alt else None
    v['compclear_ok'] = alt[0]['ok'] if alt else None
    tb = [t for t in out['tombstone'] if t['ref'] == ref]
    v['tomb_asym'] = tb[0]['area_asym'] if tb else None
    v['refx_new_voids'] = len(out['reference_plane_new_voids'])
    v['worst_clear'] = {k: w[0] for k, w in out['clearance']['worst'].items()}
    v['u3_side_len'] = out['split'].get(net, {}).get('u3_side_len_mm')
    v['PASS'] = (v['apply_errors'] == 0 and v['split_ok'] and v['new_shorts'] == 0 and all(x == 1 for x in v['pour_islands'].values())
                 and not any(v['pour_off_main_new'].values()) and not any(v['pour_neck_new'].values()) and not v['worse_islands']
                 and v['antennae'] == 0 and v['clearance_viol'] == 0 and v['h2h_viol'] == 0 and v['width_viol'] == 0
                 and v['mask_viol'] == 0 and v['acid'] == 0 and v['silk_bad'] == 0)
    return v


for net, i, c in jobs:
    if (net, i) in done:
        continue
    t0 = time.time()
    P = PT.merge(base, [PT.delta(c)], 'cand %s #%d' % (net, i))
    pp = os.path.join(tmp, 'plan.json')
    json.dump(P, open(pp, 'w'))
    C.PLAN = pp
    C.TAG = 'c'
    C.LOG.clear(); C.SELF.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            C.main()
            out = json.load(open(os.path.join(tmp, 'check_c.json')))
            v = verdict(out, net, PT.REF[net])
        except Exception as e:
            v = dict(PASS=False, error=repr(e))
    v.update(net=net, i=i, s=round(time.time() - t0, 1))
    f.write(json.dumps(v) + '\n'); f.flush()
shutil.rmtree(tmp, ignore_errors=True)
