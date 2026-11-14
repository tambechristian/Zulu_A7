import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, bus_sim as B, ibis2spice as I
U3 = I.Ibis(B.U3_IBS); m = U3.model('DQ_100%')
for e in ('rise', 'fall'):
    t, ku, kd, _ = I.switching(m, 'typ', e)
    ws = sorted(m.waves[e], key=lambda w: w['v_fixture'])
    V1 = np.interp(t, ws[0]['t'][:,0], ws[0]['t'][:,1]); V2 = np.interp(t, ws[1]['t'][:,0], ws[1]['t'][:,1])
    print(e)
    for x in np.arange(0, 2.01e-9, 0.1e-9):
        k = np.searchsorted(t, x)
        print('  t=%.2f ns  V(Vf=0)=%.3f V(Vf=3.3)=%.3f  Ku=%+.3f Kd=%+.3f' % (x*1e9, V1[k], V2[k], ku[k], kd[k]))
    # alt C_comp extraction
    for cc in (0.0, 2e-12, 4.71e-12, 6e-12):
        m.kw['c_comp'] = [cc, cc, cc]
        t2, a, b, _ = I.switching(m, 'typ', e)
        print('  C_comp %.2f pF -> Ku %.3f..%.3f  Kd %.3f..%.3f' % (cc*1e12, a.min(), a.max(), b.min(), b.max()))
    m.kw['c_comp'] = [4.71e-12, 4.02e-12, 5.59e-12]
