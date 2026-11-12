import json,math,sys
from collections import deque
import numpy as np
sys.path.insert(0,'.')
SP=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('route/no_pmod/model.json'));P=json.load(open('route/no_pmod/s3_c.json'))
span=lambda v: v.get('span') or SP[SP.index(v['from']):SP.index(v['to'])+1]
G=.0125;X0,X1,Y0,Y1=54.8,58.2,17.3,21.8
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
        if layer in p['layers'] and p['net']!=net and p['ref'] not in ('R24',):
            a|=(np.abs(XX-p['x'])<=p['w']/2+r0)&(np.abs(YY-p['y'])<=p['h']/2+r0)
    return a
idx=lambda x,y:(int(round((x-X0)/G)),int(round((y-Y0)/G)))
# --- R5-1 GND tie: a Top>Bottom through via 0.35 near the pad, joined by a short Bottom track
rv=.09+.175+.012
A=[blk(l,'GND',rv) for l in ('Top Layer','L3-SIG','L4-SIG','Bottom Layer')]
free=~(A[0]|A[1]|A[2]|A[3])
px,py=56.0,20.3
cand=[(round(math.hypot(xs[i]-px,ys[j]-py),3),round(float(xs[i]),3),round(float(ys[j]),3)) for i,j in zip(*np.nonzero(free)) if math.hypot(xs[i]-px,ys[j]-py)<1.0]
cand.sort();print('GND through-via spots near R5-1:',len(cand),cand[:5])
# --- R24: pad 2 via-in-pad (L3>L4>L5>Bottom) reachable from the CLK-12M-FT L3 stub
N='CLK-12M-FT';rt=.09+.0381+.012;rv2=.09+.15+.012
L3t=blk('L3-SIG',N,rt);L3v=blk('L3-SIG',N,rv2);L4v=blk('L4-SIG',N,rv2)
skip=('CLK-12M-SHARED',)
Bp=blk('Bottom Layer',N,.09+.15+.15*.42,skip)   # 0201 pad body clearance (conservative square ~)
stub=np.zeros((nx,ny),bool)
for t in M['tracks']:
    if t['net']==N and t['layer']=='L3-SIG':
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((XX-t['x1'])*dx+(YY-t['y1'])*dy)/max(L2,1e-9),0,1)
        stub|=np.hypot(XX-t['x1']-k*dx,YY-t['y1']-k*dy)<=.02
print('stub cells',int(stub.sum()))
D=np.full((nx,ny),-1);q=deque()
for i,j in zip(*np.nonzero(stub&~L3t)): D[i,j]=0;q.append((i,j))
while q:
    i,j=q.popleft()
    for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
        u,v=i+di,j+dj
        if 0<=u<nx and 0<=v<ny and D[u,v]<0 and not L3t[u,v]:
            D[u,v]=D[i,j]+1;q.append((u,v))
ok=[]
for i,j in zip(*np.nonzero((D>=0)&~L3v&~L4v&~Bp)):
    x=float(xs[i]);y=float(ys[j])
    i1,j1=idx(x-.6,y)
    if 0<=i1<nx and 0<=j1<ny and not Bp[i1,j1]: ok.append((int(D[i,j]),round(x,3),round(y,3)))
ok.sort();print('R24 pad-2 centres:',len(ok),ok[:8])
