"""Run this folder's byte copy of d10/fold/check.py (md5 b2520429) on a plan, with the plan's 'designator_moves'
applied to the extract's overlay texts first (check.py section 9 reads B['texts'] directly; nothing else in check.py
reads texts).  check.py itself is imported unchanged.
    python run_check.py --plan plan_fixed.json --tag fixed      -> check_fixed.json / .log here
"""
import json, sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check as C
P = json.load(open(C.PLAN))
for m in P.get('designator_moves', []):
    hit = [t for t in C.B['texts'] if t['comp'] == m['ref'] and t['designator'] and t['layer'] == m['layer']
           and abs(t['x'] - m['x_from']) < 1e-3 and abs(t['y'] - m['y_from']) < 1e-3]
    assert len(hit) == 1, m
    hit[0]['x'], hit[0]['y'], hit[0]['rot'] = m['x'], m['y'], m['rot']
    print('designator %s moved (%.4f,%.4f) -> (%.4f,%.4f)' % (m['ref'], m['x_from'], m['y_from'], m['x'], m['y']))
C.main()
