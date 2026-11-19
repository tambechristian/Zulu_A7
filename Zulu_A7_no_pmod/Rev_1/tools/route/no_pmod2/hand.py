import json,math,sys
from collections import deque
import numpy as np
M=json.load(open('route/no_pmod2/model.json'));N='CLK-12M-SHARED'
G=.025;X0,X1,Y0,Y1=44,60.66,11,25.1
nx,ny=int((X1-X0)/G)+1,int((Y1-Y0)/G)+1
xs=X0+np.arange(nx)*G;ys=Y0+np.arange(ny)*G
XX,YY=np.meshgrid(xs,ys,indexing='ij')
def blk(layer,r0):
    a=np.zeros((nx,ny),bool)
    for t in M['tracks']:
        if t['layer']!=layer or t['net']==N: continue
        r=t['w']/2+r0
        lo=max(0,int((min(t['x1'],t['x2'])-r-X0)/G));hi=min(nx,int((max(t['x1'],t['x2'])+r-X0)/G)+2)
        lo2=max(0,int((min(t['y1'],t['y2'])-r-Y0)/G));hi2=min(ny,int((max(t['y1'],t['y2'])+r-Y0)/G)+2)
        if lo>=hi or lo2>=hi2: continue
        X=XX[lo:hi,lo2:hi2];Y=YY[lo:hi,lo2:hi2]
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((X-t['x1'])*dx+(Y-t['y1'])*dy)/max(L2,1e-9),0,1) if L2 else 0*X
        a[lo:hi,lo2:hi2]|=np.hypot(X-t['x1']-k*dx,Y-t['y1']-k*dy)<=r
    for v in M['vias']:
        if layer in v['span'] and v['net']!=N: a|=np.hypot(XX-v['x'],YY-v['y'])<=v['size']/2+r0
    for p in M['pads']:
        if layer in p['layers'] and p['net']!=N: a|=(np.abs(XX-p['x'])<=p['w']/2+r0)&(np.abs(YY-p['y'])<=p['h']/2+r0)
    return a
rt=.09+.0381+.015;rv=.09+.15+.015
def hole_block(span):
    a=np.zeros((nx,ny),bool)
    for v in M['vias']:
        if set(v['span'])&set(span): a|=np.hypot(XX-v['x'],YY-v['y'])<v['hole']/2+.075+.24+.015
    for p in M['pads']:
        if p['drill']: a|=np.hypot(XX-p['x'],YY-p['y'])<p['drill']/2+.075+.25
    return a
def plane_block(layer,r0):   # other nets' via lands on the plane layer of a stack
    a=np.zeros((nx,ny),bool)
    for v in M['vias']:
        if layer in v['span'] and v['net']!=N: a|=np.hypot(XX-v['x'],YY-v['y'])<=v['size']/2+r0
    return a
B=blk('Bottom Layer',rt);L4=blk('L4-SIG',rt);L3=blk('L3-SIG',rt)
Bv=blk('Bottom Layer',rv);L4v=blk('L4-SIG',rv);L3v=blk('L3-SIG',rv);L5v=plane_block('L5-VCC3V3',rv)
idx=lambda x,y:(int(round((x-X0)/G)),int(round((y-Y0)/G)))
STEPS=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
def flood(a,seeds):
    D=-np.ones((nx,ny),int);q=deque();par={}
    for s in seeds:
        if 0<=s[0]<nx and 0<=s[1]<ny and not a[s] and D[s]<0: D[s]=0;q.append(s)
    while q:
        c=q.popleft()
        for di,dj in STEPS:
            u=(c[0]+di,c[1]+dj)
            if 0<=u[0]<nx and 0<=u[1]<ny and D[u]<0 and not a[u]: D[u]=D[c]+1;par[u]=c;q.append(u)
    return D,par
# Bottom reach from R24-1
sx,sy=59.05,21.2
Db,pb=flood(B,[idx(sx+dx*.025,sy+dy*.025) for dx in range(-4,5) for dy in range(-4,5)])
# island seeds per layer
def seeds(l):
    o=[]
    for t in M['tracks']:
        if t['net']==N and t['layer']==l:
            for f in np.linspace(0,1,60): o.append(idx(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f))
    return o
print('Bottom reach',int((Db>=0).sum()),'touch island on Bottom:',any(0<=s[0]<nx and 0<=s[1]<ny and Db[s]>=0 for s in seeds('Bottom Layer')))
Hb=hole_block(['L4-SIG','L5-VCC3V3','Bottom Layer'])
for l,Lt,Lvv,hopname in (('L4-SIG',L4,L4v,'L4-Bottom stack'),):
    Dl,pl=flood(Lt,seeds(l))
    print(l,'island reach',int((Dl>=0).sum()))
    site=(Db>=0)&(Dl>=0)&~Bv&~L4v&~L5v&~Hb
    print('stack sites',int(site.sum()))
    if site.any():
        cost=np.where(site,Db+Dl,10**9);k=np.unravel_index(cost.argmin(),cost.shape)
        print('best',float(xs[k[0]]),float(ys[k[1]]),'Bottom steps',int(Db[k]),'L4 steps',int(Dl[k]))
        def path(par,c):
            P=[c]
            while P[-1] in par: P.append(par[P[-1]])
            return [(round(X0+a*G,3),round(Y0+b*G,3)) for a,b in P]
        def simp(P):
            S=[P[0]]
            for a,b,c in zip(P,P[1:],P[2:]):
                if abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))>1e-9: S.append(b)
            S.append(P[-1]);return S
        out={'via':(float(xs[k[0]]),float(ys[k[1]])),'bottom':simp(path(pb,k)),'l4':simp(path(pl,k))}
        json.dump(out,open('route/no_pmod2/shared_hand.json','w'));print(len(out['bottom']),len(out['l4']),out['bottom'][:3],out['bottom'][-3:],out['l4'][:3],out['l4'][-3:])
