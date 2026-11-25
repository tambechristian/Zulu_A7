import sys, os
sys.path.insert(0, '../..')
import ibis2spice as I, bus_sim as B
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, pins in ((U1, ['M1','V8','N2','V4']), (U3, ['38','2','34','16'])):
    for p in pins:
        mn = ib.pins[p][1]; m = ib.model(mn)
        print(p, ib.pins[p], mn, {c: I._rails(m, c) for c in ('typ','min','max')}, 'ccomp', m.kw['c_comp'], 'pkg', {c: I.pkg_for(ib,p,c) for c in ('typ','max')})
