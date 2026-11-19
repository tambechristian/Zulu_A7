import json,math,sys
from collections import deque
import numpy as np
sys.path.insert(0,'.')
SP=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('route/no_pmod/model.json'));P=json.load(open('route/no_pmod/seed_d.json'))
span=lambda v: v.get('span') or SP[SP.index(v['from']):SP.index(v['to'])+1]
G=.025;X0,X1,Y0,Y1=52.5,60.6,12.0,22.9
nx,ny=int((X1-X0)/G)+1,int((Y1-Y0)/G)+1
xs=X0+np.arange(nx)*G;ys=Y0+np.arange(ny)*G
XX,YY=np.meshgrid(xs,ys,indexing='ij')
def blk(layer,net,r0,skipnets=()):
    a=np.zeros((nx,ny),bool)
    for t in M['tracks']+P['tracks']:
        if t['layer']!=layer or t['net']==net or t['net'] in skipnets: continue
        r=t['w']/2+r0
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((XX-t['x1'])*dx+(YY-t['y1'])*dy)/max(L2,1e-9),0,1) if L2 else 0*XX
        a|=np.hypot(XX-t['x1']-k*dx,YY-t['y1']-k*dy)<=r
    for v in M['vias']+P['vias']:
        if layer in span(v) and v['net']!=net and v['net'] not in skipnets:
            a|=np.hypot(XX-v['x'],YY-v['y'])<=v['size']/2+r0
    for p in M['pads']:
        if layer in p['layers'] and p['net']!=net and p['ref'] not in ('R24','R5'):
            a|=(np.abs(XX-p['x'])<=p['w']/2+r0)&(np.abs(YY-p['y'])<=p['h']/2+r0)
    return a
idx=lambda x,y:(int(round((x-X0)/G)),int(round((y-Y0)/G)))
# --- R5-1 GND tie: a Top>Bottom through via 0.35 near the pad, joined by a short Bottom track
rv=.09+.175+.012
A=[blk(l,'GND',rv) for l in ('Top Layer','L3-SIG','L4-SIG','Bottom Layer')]
free=~(A[0]|A[1]|A[2]|A[3])
skipR=('FPGA-TCK',)
B5=blk('Bottom Layer','GND',.09+.15+.15*.42,skipR)
res=[]
for i in range(nx):
  for j in range(ny):
    x=float(xs[i]);y=float(ys[j])
    for dx in (-.3,.3):
        pass
    i1,j1=idx(x+.6,y)
    if not(0<=i1<nx and 0<=j1<ny) or B5[i,j] or B5[i1,j1]: continue
    near=free[max(0,i-20):i+21,max(0,j-20):j+21]
    if near.any(): res.append((round(math.hypot(x+.3-55.4,y-20.1),2),round(x+.3,3),round(y,3)))
res.sort();print('R5 centres with a GND tie:',len(res),res[:6])
# --- CLK-12M-FT: through via reachable on Top from the Top stub (54.6,20.6)-(55.1,20.3); R24 beside it
N='CLK-12M-FT'
rt=.09+.0381+.012;rv3=.09+.15+.012
TOPt=blk('Top Layer',N,rt)
V=~(blk('Top Layer',N,rv3)|blk('L3-SIG',N,rv3)|blk('L4-SIG',N,rv3)|blk('Bottom Layer',N,rv3))
D=np.full((nx,ny),-1);q=deque()
for t in M['tracks']:
    if t['net']==N and t['layer']=='Top Layer' and max(t['x1'],t['x2'])>54:
        for f in np.linspace(0,1,12):
            i,j=idx(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f)
            if 0<=i<nx and 0<=j<ny: D[i,j]=0;q.append((i,j))
while q:
    i,j=q.popleft()
    for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
        u,v=i+di,j+dj
        if 0<=u<nx and 0<=v<ny and D[u,v]<0 and not TOPt[u,v]:
            D[u,v]=D[i,j]+1;q.append((u,v))
Bp=blk('Bottom Layer',N,.09+.15+.15*.42,('CLK-12M-SHARED',))
res=[]
for i,j in zip(*np.nonzero((D>=0)&V)):
    x=float(xs[i]);y=float(ys[j])
    # R24 centred so pad 2 (east) is 0.45 mm from the via, on either side
    for cx,cy in ((x-.75,y),(x+.15,y-.45),(x+.15,y+.45)):
        i0,j0=idx(cx-.3,cy);i1,j1=idx(cx+.3,cy)
        if 0<=i0<nx and 0<=j0<ny and 0<=i1<nx and 0<=j1<ny and not Bp[i0,j0] and not Bp[i1,j1]:
            res.append((int(D[i,j]),round(x,3),round(y,3),round(cx,3),round(cy,3)))
SH='CLK-12M-SHARED'
Bs=blk('Bottom Layer',SH,rt)
DS=np.full((nx,ny),-1);q=deque()
for t in M['tracks']:
    if t['net']==SH and t['layer']=='Bottom Layer':
        for f in np.linspace(0,1,30):
            i,j=idx(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f)
            if 0<=i<nx and 0<=j<ny and not Bs[i,j] and DS[i,j]<0: DS[i,j]=0;q.append((i,j))
print('SHARED bottom seeds',len(q))
while q:
    i,j=q.popleft()
    for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
        u,v=i+di,j+dj
        if 0<=u<nx and 0<=v<ny and DS[u,v]<0 and not Bs[u,v]:
            DS[u,v]=DS[i,j]+1;q.append((u,v))
print('SHARED Bottom reach cells',int((DS>=0).sum()),'x range',float(xs[np.nonzero(DS>=0)[0]].min()),float(xs[np.nonzero(DS>=0)[0]].max()))
good=[]
for d,x,y,cx,cy in res:
    i0,j0=idx(cx-.3,cy)
    if DS[i0,j0]>=0: good.append((d,int(DS[i0,j0]),x,y,cx,cy))
good.sort(key=lambda a:a[0]+a[1]);print('both reachable:',len(good),good[:8])
