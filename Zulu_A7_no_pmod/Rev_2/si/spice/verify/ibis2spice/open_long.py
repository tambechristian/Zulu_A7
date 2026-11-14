"""Single rise into an open pin (package + 1 Mohm), 60 ns: is the high level Vcc, and when does it settle?"""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name, pin in ((U1, 'LVCMOS33_S_8_HR', 'V8'), (U3, 'DQ_100%', '2')):
    m = ib.model(name)
    for c in ('typ', 'max'):
        t, ku, kd = I.weights_pwl(m, c, [(1e-9, 'rise')], 60e-9)
        lines = ['* open'] + B.pwl_source('ku', 'ku', t, ku) + B.pwl_source('kd', 'kd', t, kd)
        b, (vcc, _) = I.buffer_netlist('D', m, c, 'die', 'pin', I.pkg_for(ib, pin, c), 'ku', 'kd')
        lines += b + ['Rl pin 0 1Meg', '.options reltol=1e-5 method=gear', '.ic V(die)=0', '.tran 5p 60n 0 5p', '.end']
        r = ngs.run(lines); tt, v = r['time'], r['pin']
        print('%-16s %-3s Vcc %.3f  V(pin) at 3/5/8.4/20/59 ns: %s  max %.3f' % (name, c, vcc,
              ' '.join('%.4f' % np.interp(x * 1e-9, tt, v) for x in (3, 5, 8.4, 20, 59)), v.max()))
