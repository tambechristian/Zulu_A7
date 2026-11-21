from common import *
import fast, common
seg_box_dist=fast.seg_box
import numpy as np
import os
YC=float(os.environ.get("YC","7.75")); DY=2.6; CX=30.48
def base_scenario():
    M=copy.deepcopy(M0); D=copy.deepcopy(D0)
    x1_east(M,D,YC)
    s2b(M,D,CX)
    for c in D['comps']:
        if c['ref']=='X4': c['pattern']='JST-S2B-PH-SM4-TB'; c['rot']=180.0
    move(M,'U2',0,DY)
    return M,D
def free_spots(M,D,ref,region,rots=(0,90),step=0.25,clr=0.10,exclude=()):
    """positions where ref has no body/pad collision and no other-net copper on its layers"""
    out=[]
    c=[c for c in D['comps'] if c['ref']==ref][0]
    for rot in rots:
        for x in np.arange(region[0],region[2]+1e-9,step):
            for y in np.arange(region[1],region[3]+1e-9,step):
                Mt=dict(M); Mt['pads']=[dict(p) for p in M['pads']]; Dt=copy.deepcopy(D)
                ps=place(Mt,Dt,ref,x,y,rot)
                if any(min(pad_box(p)[0],pad_box(p)[1],W-pad_box(p)[2],H-pad_box(p)[3])<0.3 for p in ps): continue
                if pad_pad(Mt,{ref},0.15): continue
                if BC.check(BC.build(Mt,Dt),{ref},0.10): continue
                cc=[k for k in copper_conflicts(Mt,ps,clr) if k[3] not in exclude]
                out.append((len(cc),round(math.hypot(x-region[4],y-region[5]),2),x,y,rot,sorted(set(k[3] for k in cc))))
    out.sort(key=lambda t:(t[0],t[1]))
    return out
if __name__=='__main__':
    M,D=base_scenario()
    r=BC.check(BC.build(M,D),{'X1','X4','U2'},0.10)
    print('collisions after X1/X4/U2 moves:'); [print(' ',x) for x in sorted(set(r))]
    print('pad-pad:',pad_pad(M,{'X1','X4','U2'},0.15))
    print('edge:',edge_clear([p for p in M['pads'] if p['ref'] in ('X1','X4','U2')]))
