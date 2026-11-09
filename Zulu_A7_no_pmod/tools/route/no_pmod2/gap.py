import json,math,sys
from collections import deque
import numpy as np
SP=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('route/no_pmod2/model.json'));N='CLK-12M-SHARED'
G=.025;X0,X1,Y0,Y1=38,60.66,10,25.1
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
r0=.09+.0381+.012
LS=['Top Layer','L3-SIG','L4-SIG','Bottom Layer']
L={l:blk(l,r0) for l in LS}
idx=lambda x,y:(int(round((x-X0)/G)),int(round((y-Y0)/G)))
def flood(a,seeds):
    D=np.zeros((nx,ny),bool);q=deque()
    for s in seeds:
        if 0<=s[0]<nx and 0<=s[1]<ny and not a[s] and not D[s]: D[s]=True;q.append(s)
    while q:
        i,j=q.popleft()
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            u,v=i+di,j+dj
            if 0<=u<nx and 0<=v<ny and not D[u,v] and not a[u,v]: D[u,v]=True;q.append((u,v))
    return D
# region reachable from R24-1 on each layer (Bottom pad; hop layers wherever a via could stand)
rv=.09+.15+.012
Lv={l:blk(l,rv) for l in LS}
sx,sy=59.05,21.2
R={l:np.zeros((nx,ny),bool) for l in LS}
R['Bottom Layer']=flood(L['Bottom Layer'],[idx(sx+dx*.05,sy+dy*.05) for dx in range(-3,4) for dy in range(-3,4)])
for it in range(6):
    n0=sum(int(v.sum()) for v in R.values())
    for a,b in (('Top Layer','L3-SIG'),('L3-SIG','L4-SIG'),('L4-SIG','Bottom Layer')):
        hop=R[a]&~Lv[a]&~Lv[b]
        R[b]|=flood(L[b],list(zip(*np.nonzero(hop&~R[b]))))
        hop=R[b]&~Lv[a]&~Lv[b]
        R[a]|=flood(L[a],list(zip(*np.nonzero(hop&~R[a]))))
    n1=sum(int(v.sum()) for v in R.values())
    if n1==n0: break
for l in LS:
    ii,jj=np.nonzero(R[l]); print(l,int(R[l].sum()),'x %.2f-%.2f y %.2f-%.2f'%(xs[ii].min(),xs[ii].max(),ys[jj].min(),ys[jj].max()))
# nearest approach to the SHARED island
pts={l:[] for l in LS}
for t in M['tracks']:
    if t['net']==N and t['layer'] in pts:
        pts[t['layer']]+=[(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f) for f in np.linspace(0,1,50)]
for l in LS:
    if not pts[l]: print(l,'no island copper'); continue
    ii,jj=np.nonzero(R[l]);fx=xs[ii];fy=ys[jj]
    best=(9,)
    for px,py in pts[l]:
        d=np.hypot(fx-px,fy-py);k=int(d.argmin())
        if d[k]<best[0]: best=(round(float(d[k]),3),(round(float(fx[k]),2),round(float(fy[k]),2)),(round(px,2),round(py,2)))
    print(l,'gap',best)
    if best[0]<9:
        mx,my=(best[1][0]+best[2][0])/2,(best[1][1]+best[2][1])/2
        near=sorted({t['net'] for t in M['tracks'] if t['layer']==l and t['net']!=N and math.hypot((t['x1']+t['x2'])/2-mx,(t['y1']+t['y2'])/2-my)<1.5})
        print('   nets near the gap',near[:12])
