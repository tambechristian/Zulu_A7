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

import heapq,sys
sys.path.insert(0,'.')
idx=lambda x,y:(int(round((x-X0)/G)),int(round((y-Y0)/G)))
STEPS=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
sx,sy=59.05,21.2
LS=['Top Layer','L3-SIG','L4-SIG','Bottom Layer']
T={l:blk(l,rt) for l in LS}
V30={l:blk(l,.09+.15+.015) for l in LS}
V27={l:blk(l,.09+.135+.015) for l in LS}
V35={l:blk(l,.09+.175+.015) for l in LS}
L2l=plane_block('L2-GND',.09+.15+.015);L5l=plane_block('L5-VCC3V3',.09+.15+.015)
L2t=plane_block('L2-GND',.09+.175+.015);L5t=plane_block('L5-VCC3V3',.09+.175+.015)
# hop sites
HB=hole_block(['L4-SIG','L5-VCC3V3','Bottom Layer'])
H34=hole_block(['L3-SIG','L4-SIG'])
HT=hole_block(['Top Layer','L2-GND','L3-SIG'])
HA=hole_block(['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer'])
hop={}
hop[(2,3)]=~(V30['L4-SIG']|V30['Bottom Layer']|L5l|HB)          # L4<->Bottom
hop[(1,2)]=~(V27['L3-SIG']|V27['L4-SIG']|H34)                    # L3<->L4
hop[(0,1)]=~(V30['Top Layer']|V30['L3-SIG']|L2l|HT)              # Top<->L3
thr=~(V35['Top Layer']|V35['L3-SIG']|V35['L4-SIG']|V35['Bottom Layer']|L2t|L5t|HA)
print({k:int(v.sum()) for k,v in hop.items()},'through',int(thr.sum()))
edge=(XX>60.66)|(YY>25.05)
for l in LS: T[l]|=edge
vmask=(XX<=60.48)&(YY<=24.9)
for k in hop: hop[k]&=vmask
thr&=vmask
D=np.full((4,nx,ny),10**9,int);par={}
pq=[]
for li,l in enumerate(LS):
    for t in M['tracks']:
        if t['net']==N and t['layer']==l:
            for f in np.linspace(0,1,80):
                i,j=idx(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f)
                if 0<=i<nx and 0<=j<ny and D[li,i,j]>0:
                    D[li,i,j]=0;heapq.heappush(pq,(0,li,i,j))
tgt=[(3,)+idx(sx+dx*.025,sy+dy*.025) for dx in range(-2,3) for dy in range(-2,3)]
tset=set(tgt)
done=None
while pq:
    d,li,i,j=heapq.heappop(pq)
    if d>D[li,i,j]: continue
    if (li,i,j) in tset: done=(li,i,j);break
    for di,dj in STEPS:
        u,v=i+di,j+dj
        if 0<=u<nx and 0<=v<ny and not edge[u,v]:
            nd=d+(14 if di and dj else 10)+(300 if T[LS[li]][u,v] else 0)
            if nd<D[li,u,v]: D[li,u,v]=nd;par[(li,u,v)]=(li,i,j);heapq.heappush(pq,(nd,li,u,v))
    for (a,b),mask in hop.items():
        if li in (a,b) and mask[i,j]:
            o=b if li==a else a
            nd=d+400
            if nd<D[o,i,j]:
                D[o,i,j]=nd;par[(o,i,j)]=(li,i,j);heapq.heappush(pq,(nd,o,i,j))
    if thr[i,j]:
        for o in range(4):
            nd=d+600
            if o!=li and nd<D[o,i,j]:
                D[o,i,j]=nd;par[(o,i,j)]=(li,i,j);heapq.heappush(pq,(nd,o,i,j))
print('reached',done, None if done is None else int(D[done]))

import collections
if done:
    P=[done]
    while P[-1] in par: P.append(par[P[-1]])
    pts=[(LS[l],round(X0+a*G,3),round(Y0+b*G,3)) for l,a,b in P]
    json.dump(pts,open('route/no_pmod2/shared_soft.json','w'))
    seg=[pts[0]]
    for a,b in zip(pts,pts[1:]):
        if a[0]!=b[0]: seg+=[a,b]
    print('layer changes',[(s[0][:3],s[1],s[2]) for s in seg])
    hit=collections.Counter()
    import route_conn as C
    for l,x,y in pts:
        for t in M['tracks']:
            if t['layer']==l and t['net']!=N and C.seg_dist(t['x1'],t['y1'],t['x2'],t['y2'],x,y)<t['w']/2+.0381+.09: hit[(l[:3],t['net'])]+=1
        for v in M['vias']:
            if l in v['span'] and v['net']!=N and math.hypot(v['x']-x,v['y']-y)<v['size']/2+.0381+.09: hit[('via '+l[:3],v['net'])]+=1
    print('crosses',hit.most_common(20))
