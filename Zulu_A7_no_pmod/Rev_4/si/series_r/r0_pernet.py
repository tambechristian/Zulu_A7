"""Per-net DS181 Table 4 budget at R = 0 (read, fab stack), using parasitic_sim.run_case unchanged (variant 'ideal').
Writes r0_pernet.json here.  Part of the 'arrays' plan: tells which DQ nets fail without a series R."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parasitic_sim as PS

if __name__ == '__main__':
    import multiprocessing as mp
    tasks = [('D%d' % i, c, 'ideal', 0.0) for c in ('typ', 'max') for i in range(16)]
    out = []
    with mp.Pool(6, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(PS.run_case, tasks):
            out.append(r)
            print(json.dumps(r), flush=True)
    json.dump(sorted(out, key=lambda r: (r['corner'], int(r['net'][1:]))), open(os.path.join(HERE, 'r0_pernet.json'), 'w'), indent=1)
