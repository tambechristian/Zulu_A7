import geo, numpy as np, json
RELOC={'BTN','LD0','LD1','LD2','LD3','LD4','C155','C158','C159'}
def fixed_top(cx,cy=4.9):
    M,D=geo.build({},s2b=(cx,cy))
    M['pads']=[p for p in M['pads'] if p['ref'] not in RELOC]
    parts=geo.BC.build(M,D)['Top']
    bodies=[];bodiest=[];pads=[]
    for ref,P in parts.items():
        if ref=='U2': continue
        bodies+= [b for b in P['body']]; bodiest+=[b for b in P['bodyt']]
        pads+=[b for b,_ in P['pads']]
    return np.array(bodies),np.array(bodiest),np.array(pads)
U=[p for p in geo.M0['pads'] if p['ref']=='U2']
ucx,ucy=geo.centre(U)
rel=np.array([(p['x']-ucx-p['w']/2,p['y']-ucy-p['h']/2,p['x']-ucx+p['w']/2,p['y']-ucy+p['h']/2) for p in U])
def gaps(A,B):
    # A: (n,4) B:(m,4) -> min gap matrix (n,m); negative = overlap
    dx=np.maximum(A[:,None,0]-B[None,:,2],B[None,:,0]-A[:,None,2])
    dy=np.maximum(A[:,None,1]-B[None,:,3],B[None,:,1]-A[:,None,3])
    ov=(dx<0)&(dy<0)
    g=np.hypot(np.maximum(dx,0),np.maximum(dy,0))
    return np.where(ov,np.maximum(dx,dy),g)
def ok(ux,uy,FB,FBt,FP,pp=0.2,bg=0.1):
    pads=rel+np.array([ux,uy,ux,uy])
    body=np.array([[ux-5,uy-5,ux+5,uy+5]]); bodyt=np.array([[ux-5.1,uy-5.1,ux+5.1,uy+5.1]])
    if pads[:,0].min()<0.3 or pads[:,1].min()<0.3 or pads[:,2].max()>geo.W-0.3 or pads[:,3].max()>geo.H-0.3: return None
    m=[gaps(pads,FP).min(), gaps(body,FB).min(), gaps(body,FP).min(), gaps(pads,FB).min(), gaps(bodyt,FBt).min()]
    good = m[0]>=pp-1e-9 and m[1]>=bg-1e-9 and m[2]>=bg-1e-9 and m[3]>=bg-1e-9 and m[4]>=0
    return m if good else None
if __name__=='__main__':
    res={}
    for cx in [29.28,29.68,30.08,30.48,30.88,31.28,31.68]:
        FB,FBt,FP=fixed_top(cx)
        feas=[]
        for ux in np.arange(12.0,32.0,0.05):
            for uy in np.arange(6.5,19.0,0.05):
                m=ok(ux,uy,FB,FBt,FP)
                if m: feas.append((round(ux,2),round(uy,2),[round(v,3) for v in m]))
        res[cx]=feas
        if feas:
            xs=[f[0] for f in feas]; ys=[f[1] for f in feas]
            print('cx %.2f feasible %d  ux %.2f..%.2f  uy %.2f..%.2f'%(cx,len(feas),min(xs),max(xs),min(ys),max(ys)))
        else: print('cx %.2f none'%cx)
    json.dump({str(k):v for k,v in res.items()},open('u2_feasible.json','w'))
