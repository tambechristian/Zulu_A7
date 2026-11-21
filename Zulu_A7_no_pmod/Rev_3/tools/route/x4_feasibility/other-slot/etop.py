from scan import *
import itertools
best=None
for c10 in range(63,108):
    c=c10/10
    o,cu,pb,bb=evaluate('E','Top',c)
    tl=sum(v[1] for v in cu.values()); nv=sum(v[2] for v in cu.values())
    print(c, sorted(o), 'cu nets',len(cu),'len %.1f vias %d'%(tl,nv))
