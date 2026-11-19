"""Re-run bus_sim.simulate for single nets with one ibis2spice assumption changed at a time; report the measure()
numbers next to the unchanged baseline. Never writes into the spice folder."""
import sys, os, json
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np

DIAG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'u1_pkg_diag.json')))

def run(case):
    import bus_sim as B, ibis2spice as I
    net, scen, corner, variant = case
    M = json.load(open(B.MODEL))
    U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
    if variant == 'dq_ccomp0':
        for nm in ('DQ_100%',):
            U3.models[nm].kw['c_comp'] = [0.0, 0.0, 0.0]
    if variant == 'dq_ccomp2p':
        U3.models['DQ_100%'].kw['c_comp'] = [2e-12, 2e-12, 2e-12]
    if variant == 'u1_ccomp0':
        for nm in ('LVCMOS33_S_8_HR', 'LVCMOS33_F_8_HR'):
            U1.models[nm].kw['c_comp'] = [0.0, 0.0, 0.0]
    if variant == 'u1_pkgdiag':
        orig = I.pkg_for
        def pk(ib, pin, c):
            if ib is U1:
                for k, v in DIAG.items():
                    if v[0] == pin:
                        return v[1], v[2], v[3]
            return orig(ib, pin, c)
        I.pkg_for = pk
    if variant == 'settled':      # one rise and one fall, 40 ns apart: no truncation/stitching
        B.EDGES = [(1.0e-9, 'rise'), (41.0e-9, 'fall')]
        B.T_END = 80e-9
    if variant == 'nostitch':     # 4 edges, but each new edge starts from the weights the previous one reached
        orig_w = I.weights_pwl
        def wp(m, c, edges, t_end, dt=5e-12):
            tr, tf = I.switching(m, c, 'rise'), I.switching(m, c, 'fall')
            t = np.arange(0, t_end + dt, dt); ku = np.zeros_like(t); kd = np.ones_like(t)
            for te, kind in edges:
                tt, KU, KD, _ = tr if kind == 'rise' else tf
                s = t >= te; k0 = np.flatnonzero(s)[0]
                u0, d0 = ku[k0 - 1], kd[k0 - 1]
                # map the table's start state onto the current state, fading the offset out over the edge
                fu = np.interp(t[s] - te, tt, KU); fd = np.interp(t[s] - te, tt, KD)
                fade = np.clip(1 - (t[s] - te) / 3e-9, 0, 1)
                ku[s] = fu + (u0 - KU[0]) * fade; kd[s] = fd + (d0 - KD[0]) * fade
            return t, ku, kd
        I.weights_pwl = wp
    tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, scen, corner, U1, U3)
    m = B.measure(tt, vr, vcc)
    # per-edge maxima
    m['rx_pin_max'] = float(vrp.max()); m['rx_pin_min'] = float(vrp.min())
    return case, m

if __name__ == '__main__':
    from multiprocessing import Pool
    cases = json.loads(sys.argv[1])
    cases = [tuple(c) for c in cases]
    with Pool(min(2, len(cases)), maxtasksperchild=1) as p:
        for case, m in p.imap(run, cases):
            print('%-6s %-5s %-3s %-12s ovs %+.4f  uns %.4f  ringback %+.4f  t10-90 %.3f  | rx pin max %.3f min %.3f' % (
                *case, m['overshoot'], m['undershoot'], m['ringback_into_band'], m['t10_90_ns'] or -1, m['rx_pin_max'], m['rx_pin_min']), flush=True)
