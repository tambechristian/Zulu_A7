import json,math,sys
from collections import deque
import numpy as np
sys.path.insert(0,'.')
SP=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('route/no_pmod/model.json'));P=json.load(open(sys.argv[1]));N=sys.argv[2]
span=lambda v:v.get('span') or SP[SP.index(v['from']):SP.index(v['to'])+1]
G=.025;X0,X1,Y0,Y1=50,60.66,10,25.1
nx,ny=int((X1-X0)/G)+1,int((Y1-Y0)/G)+1
xs=X0+np.arange(nx)*G;ys=Y0+np.arange(ny)*G
XX,YY=np.meshgrid(xs,ys,indexing='ij')
def blk(layer,r0):
    a=np.zeros((nx,ny),bool)
    for t in M['tracks']+P['tracks']:
        if t['layer']!=layer or t['net']==N: continue
        r=t['w']/2+r0
        if max(t['x1'],t['x2'])<X0-r or min(t['x1'],t['x2'])>X1+r or max(t['y1'],t['y2'])<Y0-r or min(t['y1'],t['y2'])>Y1+r: continue
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((XX-t['x1'])*dx+(YY-t['y1'])*dy)/max(L2,1e-9),0,1) if L2 else 0*XX
        a|=np.hypot(XX-t['x1']-k*dx,YY-t['y1']-k*dy)<=r
    for v in M['vias']+P['vias']:
        if layer in span(v) and v['net']!=N: a|=np.hypot(XX-v['x'],YY-v['y'])<=v['size']/2+r0
    for p in M['pads']:
        if layer in p['layers'] and p['net']!=N: a|=(np.abs(XX-p['x'])<=p['w']/2+r0)&(np.abs(YY-p['y'])<=p['h']/2+r0)
    return a
r0=.09+.0381+.012
L={l:blk(l,r0) for l in ('Top Layer','L3-SIG','L4-SIG','Bottom Layer')}
idx=lambda x,y:(int(round((x-X0)/G)),int(round((y-Y0)/G)))
def flood(a,seeds):
    D=np.zeros((nx,ny),bool);q=deque()
    for s in seeds:
        if 0<=s[0]<nx and 0<=s[1]<ny and not a[s]: D[s]=True;q.append(s)
    while q:
        i,j=q.popleft()
        for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
            u,v=i+di,j+dj
            if 0<=u<nx and 0<=v<ny and not D[u,v] and not a[u,v]: D[u,v]=True;q.append((u,v))
    return D
sx,sy=float(sys.argv[3]),float(sys.argv[4])
for l,a in L.items():
    seeds=[idx(sx+dx*.05,sy+dy*.05) for dx in range(-3,4) for dy in range(-3,4)]
    F=flood(a,seeds)
    # net's copper on this layer
    own=[t for t in M['tracks']+P['tracks'] if t['net']==N and t['layer']==l]
    hit=0
    for t in own:
        for f in np.linspace(0,1,20):
            i,j=idx(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f)
            if 0<=i<nx and 0<=j<ny and F[max(0,i-3):i+4,max(0,j-3):j+4].any(): hit+=1;break
    area=F.mean()
    ii,jj=np.nonzero(F)
    print(l,'reach %.4f'%area,'x %.2f-%.2f y %.2f-%.2f'%(xs[ii].min(),xs[ii].max(),ys[jj].min(),ys[jj].max()) if len(ii) else '-', 'own tracks',len(own),'touching',hit)
print('--- nearest approach of the reach to the net copper')
for l,a in L.items():
    seeds=[idx(sx+dx*.05,sy+dy*.05) for dx in range(-3,4) for dy in range(-3,4)]
    F=flood(a,seeds)
    own=[t for t in M['tracks']+P['tracks'] if t['net']==N and t['layer']==l]
    vs=[v for v in M['vias']+P['vias'] if v['net']==N and l in span(v)]
    pts=[(t['x1']+(t['x2']-t['x1'])*f,t['y1']+(t['y2']-t['y1'])*f) for t in own for f in np.linspace(0,1,40)]+[(v['x'],v['y']) for v in vs]
    ii,jj=np.nonzero(F)
    if not len(ii) or not pts: print(l,'none'); continue
    fx=xs[ii];fy=ys[jj]
    best=(9,None,None)
    for px,py in pts:
        d=np.hypot(fx-px,fy-py);k=int(d.argmin())
        if d[k]<best[0]: best=(float(d[k]),(round(float(fx[k]),3),round(float(fy[k]),3)),(round(px,3),round(py,3)))
    print(l,best)
    if best[1] is None: continue
    # what blocks between them
    (qx,qy),(px,py)=best[1],best[2]
    near=[]
    for t in M['tracks']+P['tracks']:
        if t['layer']==l and t['net']!=N:
            import route_conn as C
            d1=C.seg_dist(t['x1'],t['y1'],t['x2'],t['y2'],(qx+px)/2,(qy+py)/2)
            if d1<.35: near.append((t['net'],round(d1,3)))
    for v in M['vias']+P['vias']:
        if l in span(v) and v['net']!=N:
            d1=math.hypot(v['x']-(qx+px)/2,v['y']-(qy+py)/2)
            if d1<.45: near.append(('V',v['net'],round(d1,3)))
    print('   blockers',near[:10])
