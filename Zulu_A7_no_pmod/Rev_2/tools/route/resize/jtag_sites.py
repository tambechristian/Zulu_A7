import json,math
import numpy as np
M=json.load(open('route/resize/stage1.json'))
G=.025;W,H=60.96,25.4
nx,ny=int(W/G)+1,int(H/G)+1
xs=np.arange(nx)*G;ys=np.arange(ny)*G
R=.762;CL=.09
def masks(net):
    a=np.zeros((nx,ny),bool)
    def disk(x,y,r):
        i0=max(0,int((x-r)/G));i1=min(nx,int((x+r)/G)+2);j0=max(0,int((y-r)/G));j1=min(ny,int((y+r)/G)+2)
        if i0>=i1 or j0>=j1: return
        X,Y=np.meshgrid(xs[i0:i1],ys[j0:j1],indexing='ij')
        a[i0:i1,j0:j1]|=np.hypot(X-x,Y-y)<=r
    for t in M['tracks']:
        if t['net']==net: continue
        r=t['w']/2+R+CL
        i0=max(0,int((min(t['x1'],t['x2'])-r)/G));i1=min(nx,int((max(t['x1'],t['x2'])+r)/G)+2)
        j0=max(0,int((min(t['y1'],t['y2'])-r)/G));j1=min(ny,int((max(t['y1'],t['y2'])+r)/G)+2)
        if i0>=i1 or j0>=j1: continue
        X,Y=np.meshgrid(xs[i0:i1],ys[j0:j1],indexing='ij')
        dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];L2=dx*dx+dy*dy
        k=np.clip(((X-t['x1'])*dx+(Y-t['y1'])*dy)/max(L2,1e-12),0,1) if L2 else 0*X
        a[i0:i1,j0:j1]|=np.hypot(X-t['x1']-k*dx,Y-t['y1']-k*dy)<=r
    for v in M['vias']:
        if v['net']!=net: disk(v['x'],v['y'],v['size']/2+R+CL)
        else: disk(v['x'],v['y'],v['hole']/2+.508+.25)      # own-net hole spacing
    for p in M['pads']:
        if p['ref'] in('JP3','JP4'): continue
        if p['net']!=net or p['drill']:
            m=R+CL if p['net']!=net else .508+.25
            i0=max(0,int((p['x']-p['w']/2-m)/G));i1=min(nx,int((p['x']+p['w']/2+m)/G)+2)
            j0=max(0,int((p['y']-p['h']/2-m)/G));j1=min(ny,int((p['y']+p['h']/2+m)/G)+2)
            X,Y=np.meshgrid(xs[i0:i1],ys[j0:j1],indexing='ij')
            dx=np.maximum(np.abs(X-p['x'])-p['w']/2,0);dy=np.maximum(np.abs(Y-p['y'])-p['h']/2,0)
            a[i0:i1,j0:j1]|=np.hypot(dx,dy)<=m
    e=R+.3
    a|=(xs[:,None]<e)|(xs[:,None]>W-e)|(ys[None,:]<e)|(ys[None,:]>H-e)
    return a
nets={'JP3':['TCK','TMS','GND'],'JP4':['TDI','TDO','VCC3V3']}
step=int(round(2.54/G))
res={}
for jp,nn in nets.items():
    A=[~masks(n) for n in nn]
    for orient in ('h','v'):
        ok=np.zeros((nx,ny),bool)
        if orient=='h':
            ok[:nx-2*step,:]=A[0][:nx-2*step,:]&A[1][step:nx-step,:]&A[2][2*step:,:]
        else:
            ok[:,:ny-2*step]=A[0][:,:ny-2*step]&A[1][:,step:ny-step]&A[2][:,2*step:]
        ii,jj=np.nonzero(ok)
        res[(jp,orient)]=list(zip((ii*G).round(3),(jj*G).round(3)))
        print(jp,orient,'pad-1 sites',len(ii))
json.dump({'%s_%s'%k:v for k,v in res.items()},open('route/resize/jtag_sites.json','w'))
# cluster sites into regions (1 mm cells) and list a representative per region
for k,v in res.items():
    cells={}
    for x,y in v: cells.setdefault((int(x//3),int(y//3)),[]).append((x,y))
    reps=[]
    for c,pts in cells.items():
        cx=np.mean([p[0] for p in pts]);cy=np.mean([p[1] for p in pts])
        best=min(pts,key=lambda p:(p[0]-cx)**2+(p[1]-cy)**2)
        reps.append((len(pts),best))
    reps.sort(reverse=True)
    print(k,[(n,(float(b[0]),float(b[1]))) for n,b in reps[:12]])
