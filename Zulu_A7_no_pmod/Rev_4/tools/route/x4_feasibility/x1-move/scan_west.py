from common import *
import numpy as np
def x1_west(M,D,yc):
    ps=pads_of(M0,'X1'); new=[]
    for p in ps:
        dx,dy=p['x']-X1_ORIG[0],p['y']-X1_ORIG[1]
        q=dict(p); q['x']=-dy; q['y']=yc+dx; q['w'],q['h']=p['h'],p['w']; new.append(q)   # rot 90: outward +y -> -x
    M['pads']=[p for p in M['pads'] if p['ref']!='X1']+new
    b=D0['mech']['X1']['body']
    bx=(-(b[3]-25.4), yc+(b[0]-30.48), -(b[1]-25.4), yc+(b[2]-30.48))
    e=ext(new); D['mech']['X1']={'off':[bx[0]-e[0],bx[1]-e[1],bx[2]-e[2],bx[3]-e[3]]}
    for c in D['comps']:
        if c['ref']=='X1': c['rot']=90.0
    return new
for yc in np.arange(4.5,21.01,0.5):
    M=copy.deepcopy(M0); D=copy.deepcopy(D0)
    new=x1_west(M,D,yc)
    r=BC.check(BC.build(M,D),{'X1'},0.10); pp=pad_pad(M,{'X1'},0.15)
    hit=sorted(set((s,b if a.startswith('X1') else a) for s,k,a,b,_,g in r)|set(('pad',q) for _,_,q,_,_ in pp))
    print('yc %.1f'%yc,' '.join('%s:%s'%h for h in hit))
