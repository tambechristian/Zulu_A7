"""Does a real 0201 (or array element) behave like the ideal resistor of the series study?

Reruns the READ case (U3 DQ full drive -> U1) for D0-D15 through si/spice/bus_sim.py's own simulate(), unchanged,
with the series R at U3's pin as in ZULU_RSER, in three variants:
  ideal   : R alone (must reproduce si/spice/results_r<R>.json -- the wrapper check)
  0201    : R + package parasitics, pessimistic for a 0201 thick-film chip on its lands:
            ESL 0.5 nH in series, 0.05 pF across the body, 0.08 pF pad-to-plane at each terminal
  heavy   : 2x those (1.0 nH, 0.10 pF, 0.16 pF) -- a bound for a badly placed part / a 0402
Writes ONLY into this folder (results json + nothing else); nothing under si/spice is touched.

    python parasitic_sim.py [--r 22] [--workers 4] [--corners typ,max]
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SPICE = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SPICE)

VARIANTS = {'ideal': None,
            '0201': dict(L=0.5e-9, Cpar=0.05e-12, Cpad=0.08e-12),
            'heavy': dict(L=1.0e-9, Cpar=0.10e-12, Cpad=0.16e-12)}


def budget(t, v, rail, D):
    rr = 0.0
    for w in D.windows(t, v, rail):
        for peak, dur, tab in ((w['peak_over'], w['t_over_ns'], D.OVER), (w['peak_under'], w['t_under_ns'], D.UNDER)):
            if peak <= 0.2:
                continue
            lim = D.allowed(tab, peak)
            rr = max(rr, (dur / 7.5 * 100) / lim if lim > 0 else 1e9)
    return rr


def run_case(task):
    net, corner, variant, rser = task
    os.environ['ZULU_RSER'] = str(rser)
    import bus_sim as B
    import ibis2spice as I
    import ds181_check as D
    B.STACK = 'fab'
    par = VARIANTS[variant]
    if par is not None:
        orig = B.net_elements

        def patched(M, n, _orig=orig, _p=par):
            el, n1, n3, rep = _orig(M, n)
            # Rser (added by simulate) goes u3pin -> rx ; then ESL rx -> n3 (board); body C across; pad C both ends
            el = el + ['Lesl rx %s %g' % (n3, _p['L']),
                       'Cpar u3pin %s %g' % (n3, _p['Cpar']),
                       'Cpda u3pin 0 %g' % _p['Cpad'],
                       'Cpdb %s 0 %g' % (n3, _p['Cpad'])]
            return el, n1, 'rx', rep
        B.net_elements = patched
    M = json.load(open(B.MODEL))
    U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
    try:
        tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, 'read', corner, U1, U3)
    except Exception as e:
        return dict(net=net, corner=corner, variant=variant, r=rser, error=str(e)[:400])
    rail = B.VRAIL[corner]
    m = B.measure(tt, vr, rail)
    mp = B.measure(tt, vrp, rail)
    return dict(net=net, corner=corner, variant=variant, r=rser,
                die_vmin=float(vr.min()), die_vmax=float(vr.max()),
                ball_vmin=float(vrp.min()), ball_vmax=float(vrp.max()),
                die_budget=budget(tt, vr, rail, D), ball_budget=budget(tt, vrp, rail, D),
                t10_90_ns=m['t10_90_ns'])


def main():
    import multiprocessing as mp
    a = sys.argv[1:]
    rser = float(a[a.index('--r') + 1]) if '--r' in a else 22.0
    workers = int(a[a.index('--workers') + 1]) if '--workers' in a else 4
    corners = a[a.index('--corners') + 1].split(',') if '--corners' in a else ['typ', 'max']
    variants = a[a.index('--variants') + 1].split(',') if '--variants' in a else list(VARIANTS)
    tasks = [('D%d' % i, c, v, rser) for v in variants for c in corners for i in range(16)]
    out = []
    with mp.Pool(min(workers, 6), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_case, tasks):
            out.append(r)
            print(json.dumps(r), flush=True)
    json.dump(out, open(os.path.join(HERE, 'parasitic_results_r%g.json' % rser), 'w'), indent=1)
    print('\nR = %g ohm, read direction, fab stack' % rser)
    for v in variants:
        for c in corners:
            g = [r for r in out if r['variant'] == v and r['corner'] == c and 'error' not in r]
            if not g:
                continue
            print('%-6s %-3s n=%2d | ball Vmin %+.3f  Vmax %.3f  budget %5.1f%% | die Vmin %+.3f budget %5.1f%% | t10-90 %.2f-%.2f ns'
                  % (v, c, len(g), min(r['ball_vmin'] for r in g), max(r['ball_vmax'] for r in g),
                     100 * max(r['ball_budget'] for r in g), min(r['die_vmin'] for r in g),
                     100 * max(r['die_budget'] for r in g), min(r['t10_90_ns'] for r in g), max(r['t10_90_ns'] for r in g)))
    print('errors:', sum('error' in r for r in out))


if __name__ == '__main__':
    main()
