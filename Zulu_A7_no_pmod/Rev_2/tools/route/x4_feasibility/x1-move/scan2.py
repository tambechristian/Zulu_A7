from common import *
import numpy as np
for yc in np.arange(6.5,9.01,0.25):
    M=copy.deepcopy(M0); D=copy.deepcopy(D0)
    new,bx=x1_east(M,D,yc)
    cc=copper_conflicts(M,new,0.10)
    nets=collections.defaultdict(set)
    for k,ref,pad,net,lay,d,o in cc: nets[net].add(lay.split()[0] if k=='track' else 'via:'+lay)
    print('yc %.2f'%yc, '; '.join('%s[%s]'%(n,','.join(sorted(l))) for n,l in sorted(nets.items())))
