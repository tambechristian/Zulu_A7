from common import *
import numpy as np
for yc in np.arange(5.5,20.01,0.25):
    M=copy.deepcopy(M0); D=copy.deepcopy(D0)
    new,bx=x1_east(M,D,yc)
    parts=BC.build(M,D)
    r=BC.check(parts,{'X1'},0.10)
    hit=sorted(set((s,b if a.startswith('X1') else a) for s,k,a,b,_,g in r))
    pp=pad_pad(M,{'X1'},0.15)
    hp=sorted(set((q,s) for _,_,q,s,g in pp))
    print('yc %.2f pads y %.2f..%.2f'%(yc,ext(new)[1],ext(new)[3]), 'BODY:',' '.join('%s:%s'%h for h in hit),'| PAD:',' '.join('%s.%s'%h for h in hp))
