"""Driver into an open circuit (package + 1 Mohm), bus_sim's 4-edge weights: high/low steady levels and the
overshoot that the driver produces by itself (no line), plus the same with weights forced to ideal (1,0)/(0,1) ends."""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name, pin in ((U1, 'LVCMOS33_S_8_HR', 'V8'), (U1, 'LVCMOS33_F_8_HR', 'M1'), (U3, 'DQ_100%', '2')):
    m = ib.model(name)
    for c in ('typ', 'max'):
        t, ku, kd = I.weights_pwl(m, c, B.EDGES, B.T_END)
        res = []
        for label, KU, KD in (('as-built', ku, kd), ('const 1/0', ku, kd)):
            if label != 'as-built':
                # DC-only check: hold the steady state of a long rise with ideal weights
                KU = np.where(t > 0, 1.0, 0.0); KD = 1 - KU
            lines = ['* open'] + B.pwl_source('ku', 'ku', t, KU) + B.pwl_source('kd', 'kd', t, KD)
            b, (vcc, _) = I.buffer_netlist('D', m, c, 'die', 'pin', I.pkg_for(ib, pin, c), 'ku', 'kd')
            lines += b + ['Rl pin 0 1Meg', '.options reltol=1e-5 method=gear', '.ic V(die)=0', '.tran 5p 32n 0 5p', '.end']
            r = ngs.run(lines)
            tt, v = r['time'], r['pin']
            at = lambda x: float(np.interp(x, tt, v))
            res.append((label, vcc, at(8.4e-9), at(15.9e-9), at(23.4e-9), at(31.9e-9), v.max(), v.min()))
        for rr in res:
            print('%-16s %-3s %-9s Vcc %.3f  V(8.4ns high)=%.4f  V(15.9 low)=%.4f  V(23.4 high)=%.4f  V(31.9 low)=%.4f  max %.4f min %.4f' % ((name, c) + rr))
