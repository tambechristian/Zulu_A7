"""Golden-fixture check for DQ_100% and LVCMOS33_S_8_HR with C_comp forced to 0 in BOTH extraction and netlist:
if it also reproduces the IBIS V-T tables, the golden test cannot tell the two C_comp choices apart."""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name in ((U3, 'DQ_100%'), (U1, 'LVCMOS33_S_8_HR')):
    m = ib.model(name); m.kw['c_comp'] = [0.0, 0.0, 0.0]
    worst = 0
    for corner in ('typ', 'max'):
        for edge in ('rise', 'fall'):
            t, KU, KD, _ = I.switching(m, corner, edge)
            print('  %s %s %s Ku %.3f..%.3f Kd %.3f..%.3f' % (name, corner, edge, KU.min(), KU.max(), KD.min(), KD.max()))
            for w in m.waves[edge]:
                vf = w.get('v_fixture') if corner == 'typ' else w.get('v_fixture_' + corner, w.get('v_fixture'))
                te = 1e-9; tw = w['t'][:, 0]; vw = w['t'][:, 1 + I.COL[corner]]
                tt = np.concatenate([[0], te + t]); ku = np.concatenate([[KU[0]], KU]); kd = np.concatenate([[KD[0]], KD])
                lines = ['* g'] + B.pwl_source('ku', 'ku', tt, ku) + B.pwl_source('kd', 'kd', tt, kd)
                b, _ = I.buffer_netlist('D', m, corner, 'die', 'pin', (1e-4, 1e-15, 1e-18), 'ku', 'kd')
                lines += b + ['Rf die fx %g' % w.get('r_fixture', 50), 'Vf fx 0 %g' % vf, '.ic V(die)=%g' % vw[0],
                              '.options reltol=1e-5 method=gear', '.tran 2p %g 0 2p' % (te + tw[-1]), '.end']
                r = ngs.run(lines)
                dev = np.max(np.abs(np.interp(te + tw, r['time'], r['die']) - vw)); worst = max(worst, dev)
    print('%s with C_comp=0: worst |sim-IBIS| = %.4f V' % (name, worst))
