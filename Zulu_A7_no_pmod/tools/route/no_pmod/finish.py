import json,math,sys
from collections import deque
import numpy as np
sys.path.insert(0,'.')
SP=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('route/no_pmod/model.json'));P=json.load(open('route/no_pmod/s3_c.json'))
span=lambda v: v.get('span') or SP[SP.index(v['from']):SP.index(v['to'])+1]
G=.0125;X0,X1,Y0,Y1=54.5,58.0,16.3,21.6
nx,ny=int((X1-X0)/G)+1,int((Y1-Y0)/G)+1
xs=X0+np.arange(nx)*G;ys=Y0+np.arange(ny)*G
XX,YY=np.meshgrid(xs,ys,indexing='ij')
def blk(layer,net,r0):
    a=np.zeros((nx,ny),bool)
    for t in M['tracks']+P['tracks']:
        if t['layer']!=layer or t['net']==net: continue
        r=t['w']/2+r0
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((XX-t['x1'])*dx+(YY-t['y1'])*dy)/max(L2,1e-9),0,1) if L2 else 0*XX
        a|=np.hypot(XX-t['x1']-k*dx,YY-t['y1']-k*dy)<=r
    for v in M['vias']+P['vias']:
        if layer in span(v) and v['net']!=net:
            a|=np.hypot(XX-v['x'],YY-v['y'])<=v['size']/2+r0
    for p in M['pads']:
        if layer in p['layers'] and p['net']!=net:
            a|=(np.abs(XX-p['x'])<=p['w']/2+r0)&(np.abs(YY-p['y'])<=p['h']/2+r0)
    return a
print('GND vias near R5-1:',[(v['x'],v['y'],span(v)[0][:3],span(v)[-1][:3],v['size']) for v in M['vias']+P['vias'] if v['net']=='GND' and math.hypot(v['x']-56,v['y']-20.3)<1.3 and 'Bottom Layer' in span(v)])
print('CLK stub vias',[(v['x'],v['y'],span(v)[0][:3],span(v)[-1][:3]) for v in M['vias']+P['vias'] if v['net']=='CLK-12M-FT' and v['x']>53])
# candidate stack points on the L3 stub (55.1,20.3)-(56.3,19.1)
N='CLK-12M-FT'
rt=.09+.0381+.012      # track clearance radius
Lb=blk('Bottom Layer',N,rt)
print('Bottom free',round(1-Lb.mean(),3))
def idx(x,y): return int(round((x-X0)/G)),int(round((y-Y0)/G))
D=np.full((nx,ny),-1);q=deque();par={}
s=idx(56.2499,17.2);D[s]=0;q.append(s)
print('start blocked',Lb[s])
while q:
    i,j=q.popleft()
    for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
        u,v=i+di,j+dj
        if 0<=u<nx and 0<=v<ny and D[u,v]<0 and not Lb[u,v]:
            D[u,v]=D[i,j]+1;par[(u,v)]=(i,j);q.append((u,v))
rv=.09+.15+.012
ok=[]
L3=blk('L3-SIG',N,rv);L4=blk('L4-SIG',N,rv);Bb=blk('Bottom Layer',N,rv)
for k in range(0,41):
    f=k/40; x=55.1+1.2*f; y=20.3-1.2*f
    i,j=idx(x,y)
    if not(L3[i,j] or L4[i,j] or Bb[i,j]) and D[i,j]>=0: ok.append((D[i,j],round(x,3),round(y,3)))
print('stack points reachable on Bottom:',len(ok),sorted(ok)[:6])
if ok:
    d,x,y=sorted(ok)[0];c=idx(x,y);path=[c]
    while path[-1] in par: path.append(par[path[-1]])
    pts=[(round(X0+a*G,4),round(Y0+b*G,4)) for a,b in path]
    # simplify collinear
    sim=[pts[0]]
    for a,b,c2 in zip(pts,pts[1:],pts[2:]):
        if (b[0]-a[0])*(c2[1]-b[1])!=(b[1]-a[1])*(c2[0]-b[0]): sim.append(b)
    sim.append(pts[-1])
    json.dump({'via':(x,y),'pts':sim},open('route/no_pmod/clk_ft.json','w'));print(len(sim),sim[:30])
