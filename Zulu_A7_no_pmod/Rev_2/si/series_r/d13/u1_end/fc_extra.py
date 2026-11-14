"""full check.py runs for the D15 F5 / F3T2 candidates on the 0.1 mm sub-grid (2 workers; the rest stay
fast_pass_unchecked).  Same job() as fc_all.py."""
import json, os, sys, glob
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_all

if __name__ == '__main__':
    todo = []
    for fam in ('F3T2', 'F5'):
        S = json.load(open(os.path.join(HERE, 'search', 'search_D15_%s.json' % fam)))
        for c in S['cands']:
            x, y, r = c['pose']
            if round(x * 1000) % 100 or round(y * 1000) % 100 or fc_all.body_conflict(S['side'], x, y, r):
                continue
            tag = 'D15_%s_%s_%s_%d' % (fam, ('%.3f' % x).replace('.', 'p'), ('%.3f' % y).replace('.', 'p'), r)
            todo.append((tag, c['delta']))
    print(len(todo), flush=True)
    with Pool(2) as p:
        for i, (tag, v) in enumerate(p.imap_unordered(fc_all.job, todo)):
            if i % 10 == 0:
                print(i, tag, v['ok'], flush=True)
    print('done')
