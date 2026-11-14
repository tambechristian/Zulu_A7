import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name in ((U1, 'LVCMOS33_S_8_HR'), (U1, 'LVCMOS33_F_8_HR'), (U3, 'DQ_100%')):
    m = ib.model(name)
    for c in ('typ', 'max', 'min'):
        for e in ('rise', 'fall'):
            t, ku, kd, src = I.switching(m, c, e)
            i75 = np.searchsorted(t, 7.5e-9)
            i75 = min(i75, len(t)-1)
            print('%-16s %-3s %-4s %s  T=%.1fns  Ku/Kd @7.5ns %.4f %.4f   end %.4f %.4f   Ku range %.3f..%.3f Kd range %.3f..%.3f' % (
                name, c, e, src, t[-1]*1e9, ku[i75], kd[i75], ku[-1], kd[-1], ku.min(), ku.max(), kd.min(), kd.max()))
