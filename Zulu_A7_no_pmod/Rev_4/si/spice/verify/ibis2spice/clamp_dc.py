"""Receiver-mode buffer (ku/kd None) as bus_sim builds it: DC-sweep the die voltage, read the current INTO the buffer
from ngspice, compare with the IBIS clamp tables (full, np.interp = clamp-at-ends) at the same voltages."""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name in ((U1, 'LVCMOS33_S_8_HR'), (U3, 'INPUT'), (U3, 'DQ_100%')):
    m = ib.model(name)
    for c in ('typ', 'max', 'min'):
        b, _ = I.buffer_netlist('R', m, c, 'die', 'pin', (0.3, 4e-9, 0.5e-12))
        lines = ['* clamp dc'] + b + ['Vd die 0 0', '.dc Vd -1.5 5.2 0.01', '.end']
        r = ngs.run(lines)
        v = r[[k for k in r if 'sweep' in k][0]]
        i_in = -r['vd#branch']
        vpu, vpd, vpc, vgc = I._rails(m, c)
        gcl, pcl = I._table(m, 'gnd clamp', c), I._table(m, 'power clamp', c)
        ref = I._interp(gcl, v - vgc) + I._interp(pcl, vpc - v)
        err = i_in - ref
        def at(x): k = np.argmin(abs(v - x)); return i_in[k], ref[k]
        print('%-16s %-3s  I_in(-1.0V)=%+.4g A (ref %+.4g)  I_in(-0.5)=%+.4g (ref %+.4g)  I_in(Vpc+0.5)=%+.4g (ref %+.4g)  I_in(Vpc+1)=%+.4g (ref %+.4g)' % (
            name, c, *at(-1.0), *at(-0.5), *at(vpc + 0.5), *at(vpc + 1.0)))
        k = np.argmax(abs(err))
        inband = (v > 0) & (v < vpc)
        print('      worst |sim-ref| over -1.5..5.2 V: %.3g A at V=%.2f (sim %.4g ref %.4g); worst in 0..Vpc: %.3g A; I_in at V=0: %.3g A, at V=Vpc: %.3g A' % (
            abs(err[k]), v[k], i_in[k], ref[k], abs(err[inband]).max(), at(0)[0], at(vpc)[0]))
