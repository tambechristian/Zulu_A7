"""Extra series-R values for the READ direction (D0-D15, fab stack, typ + max), reusing si/spice/bus_sim.py unchanged.
Output goes ONLY to this folder: wave/*.npz and sweep_results.json (bus_sim.HERE is redirected here).
python sweep.py [R1,R2,...]   (default 6,10,22,47; 22 re-runs the existing case as a wrapper check)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SP)


def work(task):
    r, net, corner = task
    os.environ['ZULU_RSER'] = str(r)
    os.environ['ZULU_WAVE_TAG'] = '_r%g' % r
    import bus_sim
    bus_sim.HERE = HERE                      # waves land in series_r/wave, never in si/spice/wave
    m = bus_sim.run_case((net, 'read', corner, 'fab'))
    m['rser'] = r
    return m


def main():
    import multiprocessing as mp
    rs = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [6, 10, 22, 47]
    os.makedirs(os.path.join(HERE, 'wave'), exist_ok=True)
    tasks = [(r, 'D%d' % d, c) for r in rs for c in ('typ', 'max') for d in range(16)]
    out = []
    with mp.Pool(6, maxtasksperchild=1) as pool:          # <= 6 workers (memory budget)
        for m in pool.imap_unordered(work, tasks):
            out.append(m)
            print(m.get('rser'), m['net'], m['corner'], m.get('error', '')[:120] or 'ok %.3f %.3f' % (m['undershoot'], m['pin_undershoot']), flush=True)
    path = os.path.join(HERE, 'sweep_results.json')
    old = json.load(open(path)) if os.path.exists(path) else []
    keep = [o for o in old if o.get('rser') not in rs]
    json.dump(keep + out, open(path, 'w'), indent=1)


if __name__ == '__main__':
    main()
