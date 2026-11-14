import sys, os, numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import ibis2spice as I, bus_sim as B
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for ib, name in ((U1,'LVCMOS33_F_8_HR'),(U1,'LVCMOS33_S_8_HR'),(U3,'DQ_100%'),(U3,'Input')):
    m = ib.model(name)
    c='typ'
    vpu,vpd,vpc,vgc = I._rails(m,c)
    print('==',name,'type',m.kw.get('model_type'),'Ccomp',m.kw.get('c_comp'),'rails',vpu,vpd,vpc,vgc, 'ramp', m.ramp)
    pu,pd = I._table(m,'pullup',c), I._table(m,'pulldown',c)
    gc,pc = I._table(m,'gnd clamp',c), I._table(m,'power clamp',c)
    if pu is not None:
        # output R near the rail: pull-up I(Vpu - V) is current into pin; R = dV/dI at small Vtable
        for vt in (0.1,0.3,0.6,1.0,1.65):
            dv=0.05
            Ru = dv/abs(I._interp(pu,vt+dv)-I._interp(pu,vt)) 
            Rd = dv/abs(I._interp(pd,vt+dv)-I._interp(pd,vt))
            print('  Vfrom-rail %.2f  Rpu %.1f  Rpd %.1f   Ipu %.4f Ipd %.4f' % (vt,Ru,Rd,I._interp(pu,vt),I._interp(pd,vt)))
        # Thevenin into 49 ohm to mid? solve DC: pullup driving 50 ohm to ground
    for V in (-1.0,-0.8,-0.6,-0.5,-0.4,-0.3,-0.2,0, 3.3,3.5,3.6,3.7,3.8,3.9,4.1,4.3):
        print('   V=%.2f  Igc %.5f  Ipc %.5f' % (V, I._interp(gc,V-vgc) if gc else 0, I._interp(pc,vpc-V) if pc else 0))
    for edge in ('rise','fall'):
        if m.waves[edge] or m.ramp:
            try:
                t,ku,kd,src = I.switching(m,c,edge)
                print('  %s %s: T=%.2f ns, Ku[0,-1]=%.3f %.3f Kd=%.3f %.3f  Ku range %.3f..%.3f Kd range %.3f..%.3f' % (edge,src,t[-1]*1e9,ku[0],ku[-1],kd[0],kd[-1],ku.min(),ku.max(),kd.min(),kd.max()))
            except Exception as e: print(' ',edge,'ERR',e)
