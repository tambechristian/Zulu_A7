import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name in ((U1, 'LVCMOS33_S_8_HR'), (U1, 'LVCMOS33_F_8_HR'), (U3, 'DQ_100%'), (U3, 'INPUT')):
    m = ib.model(name)
    print('==', name, m.name, m.kw.get('model_type'), 'ccomp', m.kw.get('c_comp'), 'vr', m.kw.get('voltage range'))
    for k, a in m.tables.items():
        print('  %-12s n=%3d  V %.3f..%.3f  I(typ) at ends %.4g %.4g' % (k, len(a), a[0,0], a[-1,0], a[0,1], a[-1,1]))
    for e in ('rise', 'fall'):
        for w in m.waves[e]:
            t = w['t']
            print('  %s Vf=%s n=%d t %.3g..%.3g ns  V0 %.3f Vend %.3f (typ)' % (e, w.get('v_fixture'), len(t), t[0,0]*1e9, t[-1,0]*1e9, t[0,1], t[-1,1]))
    for c in ('typ','min','max'):
        print('  rails', c, I._rails(m, c))
