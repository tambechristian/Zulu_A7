"""Golden-waveform check: each driver model, loaded by its own IBIS fixture (R_fixture to V_fixture, no package),
must reproduce the IBIS V-T tables it was extracted from. Reports the worst deviation per waveform."""
import numpy as np, ngs, ibis2spice as I, bus_sim as B
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
worst = 0
for ib, name in ((U1, 'LVCMOS33_S_8_HR'), (U1, 'LVCMOS33_F_8_HR'), (U3, 'DQ_100%')):
    m = ib.model(name)
    for corner in ('typ', 'max', 'min'):
        for edge in ('rise', 'fall'):
            for w in m.waves[edge]:
                vf = w.get('v_fixture') if corner == 'typ' else w.get('v_fixture_' + corner, w.get('v_fixture'))
                R = w.get('r_fixture', 50)
                te = 1e-9
                tw = w['t'][:, 0]; vw = w['t'][:, 1 + I.COL[corner]]
                T = te + tw[-1]
                start = 'rise' if edge == 'rise' else 'fall'
                # start from the opposite steady state: a fall needs a preceding rise long ago -> emulate with K values
                t, KU, KD, _ = I.switching(m, corner, edge)
                tt = np.concatenate([[0], te + t]); ku = np.concatenate([[KU[0]], KU]); kd = np.concatenate([[KD[0]], KD])
                lines = ['* golden'] + B.pwl_source('ku', 'ku', tt, ku) + B.pwl_source('kd', 'kd', tt, kd)
                b, _ = I.buffer_netlist('D', m, corner, 'die', 'pin', (1e-4, 1e-15, 1e-18), 'ku', 'kd')
                lines += b + ['Rf die fx %g' % R, 'Vf fx 0 %g' % vf, '.ic V(die)=%g' % vw[0],
                              '.options reltol=1e-5 method=gear', '.tran 2p %g 0 2p' % T, '.end']
                r = ngs.run(lines)
                sim = np.interp(te + tw, r['time'], r['die'])
                dev = np.max(np.abs(sim - vw))
                worst = max(worst, dev)
                print('%-16s %-3s %-4s Vf=%.2f  max |sim - IBIS| = %.3f V  (swing %.2f V)' % (name, corner, edge, vf, dev, vw.max() - vw.min()))
print('WORST %.3f V' % worst)
