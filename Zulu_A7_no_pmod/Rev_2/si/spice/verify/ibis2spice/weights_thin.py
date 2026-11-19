"""weights_pwl thinning: rebuild Ku/Kd by linear interpolation of the kept points (what the PWL source does) and
compare with the unthinned stitched arrays."""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name in ((U1, 'LVCMOS33_S_8_HR'), (U1, 'LVCMOS33_F_8_HR'), (U3, 'DQ_100%')):
    m = ib.model(name)
    for c in ('typ', 'max'):
        tk, ku, kd = I.weights_pwl(m, c, B.EDGES, B.T_END)
        # full
        tr, tf = I.switching(m, c, 'rise'), I.switching(m, c, 'fall')
        t = np.arange(0, B.T_END + 5e-12, 5e-12); KU = np.zeros_like(t); KD = np.ones_like(t)
        for te, kind in B.EDGES:
            tt, a, b, _ = tr if kind == 'rise' else tf
            s = t >= te; KU[s] = np.interp(t[s] - te, tt, a); KD[s] = np.interp(t[s] - te, tt, b)
        eu = np.abs(np.interp(t, tk, ku) - KU); ed = np.abs(np.interp(t, tk, kd) - KD)
        # jumps at edge starts (stitching)
        jumps = []
        for te, kind in B.EDGES[1:]:
            k = np.searchsorted(t, te)
            jumps.append('%s@%.1fns dKu=%+.3f dKd=%+.3f' % (kind, te*1e9, KU[k]-KU[k-1], KD[k]-KD[k-1]))
        print('%-16s %-3s kept %4d/%d  max|thin-full| Ku %.4f at %.2f ns, Kd %.4f at %.2f ns' % (name, c, len(tk), len(t),
              eu.max(), t[eu.argmax()]*1e9, ed.max(), t[ed.argmax()]*1e9))
        print('      stitch jumps:', '; '.join(jumps))
