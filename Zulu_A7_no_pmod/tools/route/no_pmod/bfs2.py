import json,math,sys
from collections import deque
import numpy as np
sys.path.insert(0,'.')
import route_conn as C
SP=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('route/no_pmod/model.json'));P=json.load(open(sys.argv[1]))
NET='TDI'
G=0.025; X0,X1,Y0,Y1=56.3,60.65,8.5,18.5
nx,ny=int((X1-X0)/G)+1,int((Y1-Y0)/G)+1
xs=X0+np.arange(nx)*G; ys=Y0+np.arange(ny)*G
XX,YY=np.meshgrid(xs,ys,indexing='ij')
def blk(layer):
    a=np.zeros((nx,ny),bool)
    clr=0.09+0.0381+0.012
    for src in (M['tracks'],P['tracks']):
        for t in src:
            if t['layer']!=layer or t['net']==NET: continue
            r=t['w']/2+clr
            if max(t['x1'],t['x2'])<X0-r or min(t['x1'],t['x2'])>X1+r or max(t['y1'],t['y2'])<Y0-r or min(t['y1'],t['y2'])>Y1+r: continue
            dx,dy=t['x2']-t['x1'],t['y2']-t['y1']; L2=dx*dx+dy*dy
            if L2==0: k=np.zeros_like(XX)
            else: k=np.clip(((XX-t['x1'])*dx+(YY-t['y1'])*dy)/L2,0,1)
            a|=np.hypot(XX-t['x1']-k*dx,YY-t['y1']-k*dy)<=r
    for src in (M['vias'],P['vias']):
        for v in src:
            sp=v.get('span') or SP[SP.index(v['from']):SP.index(v['to'])+1]
            if layer not in sp or v['net']==NET: continue
            a|=np.hypot(XX-v['x'],YY-v['y'])<=v['size']/2+clr
    for p in M['pads']:
        if layer in p['layers'] and p['net']!=NET:
            a|=(np.abs(XX-p['x'])<=p['w']/2+clr)&(np.abs(YY-p['y'])<=p['h']/2+clr)
    return a
def seg_pts(net_layer):
    return [t for src in (M['tracks'],P['tracks']) for t in src if t['net']==NET and t['layer']==net_layer]
def bfs(a,s,tgt):
    D=np.full((nx,ny),-1);q=deque()
    i,j=int(round((s[0]-X0)/G)),int(round((s[1]-Y0)/G)); D[i,j]=0;q.append((i,j))
    par={}
    while q:
        i,j=q.popleft()
        if tgt[i,j]: 
            path=[(i,j)]
            while path[-1] in par: path.append(par[path[-1]])
            return [(round(X0+a*G,3),round(Y0+b*G,3)) for a,b in path]
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            u,v=i+di,j+dj
            if 0<=u<nx and 0<=v<ny and D[u,v]<0 and not a[u,v]:
                D[u,v]=D[i,j]+1; par[(u,v)]=(i,j); q.append((u,v))
    return None

def flood(a,tgt):
    D=np.full((nx,ny),-1);q=deque()
    for i,j in zip(*np.nonzero(tgt)): D[i,j]=0;q.append((i,j))
    while q:
        i,j=q.popleft()
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            u,v=i+di,j+dj
            if 0<=u<nx and 0<=v<ny and D[u,v]<0 and not a[u,v]:
                D[u,v]=D[i,j]+1;q.append((u,v))
    return D
for layer in ('L3-SIG','L4-SIG'):
    a=blk(layer)
    tgt=np.zeros((nx,ny),bool)
    for t in seg_pts(layer):
        if abs(t['x1']-59.45)<1e-3: continue
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((XX-t['x1'])*dx+(YY-t['y1'])*dy)/max(L2,1e-9),0,1) if L2 else np.zeros_like(XX)
        tgt|=np.hypot(XX-t['x1']-k*dx,YY-t['y1']-k*dy)<=.03
    tgt&=~a
    D=flood(a,tgt)
    box=(XX>=58.95)&(XX<=59.6)&(YY>=16.2)&(YY<=17.8)
    print(layer,'reach in R4 core:',int(((D>=0)&box).sum()),'of',int(box.sum()))
    cc=[(D[i,j],round(float(xs[i]),3),round(float(ys[j]),3)) for i,j in zip(*np.nonzero((D>=0)&box))]
    cc.sort(); print(cc[:8])
