"""Full checker (copy of d10/fold/check.py) on every alone candidate: 13-R plan + that candidate's delta."""
import json, os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor
import planio
jobs = []
for f, net in (('cands_14_XF-Top_gnd47.json', 14), ('cands_13_XF-Top_gnd47.json', 13), ('cands_15_XF-Top_none.json', 15)):
    for c in json.load(open(f))['cands']:
        cid = 'D%d_%s_%s_%g_%g_r%d' % (net, c['family'], c['unlock'], c['x'], c['y'], c['rot'])
        P = planio.merge([c['rec']], note=cid)
        p = os.path.join('fcplans', cid + '.json')
        planio.write(P, p)
        jobs.append((cid, p))

def run(j):
    cid, p = j
    try:
        s = planio.run_check(p, 'fc/' + cid)
    except Exception as e:
        s = dict(error=repr(e), **{'pass': False})
    return cid, s

res = {}
with ThreadPoolExecutor(6) as ex:
    for cid, s in ex.map(run, jobs):
        res[cid] = s
json.dump(res, open('fullcheck_results.json', 'w'), indent=0)
print(len(res), 'checked;', sum(1 for s in res.values() if s.get('pass')), 'pass')
for k, s in res.items():
    if not s.get('pass'):
        print('FAIL', k, {a: b for a, b in s.items() if a not in ('sdram_new_islands',)})
