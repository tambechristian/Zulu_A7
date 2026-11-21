import geo, numpy as np, math, json, sys
from search_u2 import fixed_top, ok, rel, gaps
T=geo.M0['tracks'];V=geo.M0['vias']
U2NETS=set(p['net'] for p in geo.M0['pads'] if p['ref']=='U2' and p['net'])
# foreign Top copper (nets not on U2): tracks on Top as capsules approximated by boxes, Top-reaching vias
topT=[t for t in T if t['layer']=='Top Layer' and t['net'] not in U2NETS]
def toptrack_at_via(v):
    return any(t['net']==v['net'] and min(math.hypot(t['x1']-v['x'],t['y1']-v['y']),math.hypot(t['x2']-v['x'],t['y2']-v['y']))<0.2 for t in topT)
topV=[v for v in V if 'Top Layer' in v['span'] and v['net'] not in U2NETS]
conv=np.array([0 if toptrack_at_via(v) else 1 for v in topV])
VB=np.array([(v['x']-v['size']/2,v['y']-v['size']/2,v['x']+v['size']/2,v['y']+v['size']/2) for v in topV])
def seg_box_hits(pads,clear):
    hits=set()
    for i,t in enumerate(topT):
        x0,x1=sorted((t['x1'],t['x2']));y0,y1=sorted((t['y1'],t['y2']))
        if x1<pads[:,0].min()-1 or x0>pads[:,2].max()+1 or y1<pads[:,1].min()-1 or y0>pads[:,3].max()+1: continue
        for p in pads:
            pd={'x':(p[0]+p[2])/2,'y':(p[1]+p[3])/2,'w':p[2]-p[0],'h':p[3]-p[1],'shape':'rect','ref':''}
            if geo.RC.pad_seg(pd,(t['x1'],t['y1'],t['x2'],t['y2']))<t['w']/2+clear: hits.add(i);break
    return hits
def cost(ux,uy):
    pads=rel+np.array([ux,uy,ux,uy])
    g=gaps(pads,VB).min(axis=0)  # per via
    hitv=np.where(g<geo.CLEAR)[0]
    body=np.array([[ux-5,uy-5,ux+5,uy+5]])
    under=np.where(gaps(body,VB)[0]<0)[0]
    rip_v=[topV[i]['net'] for i in hitv if not conv[i]]
    conv_v=[topV[i]['net'] for i in hitv if conv[i]]
    under_only=[topV[i]['net'] for i in under if i not in set(hitv)]
    ht=seg_box_hits(pads,geo.CLEAR)
    return {'rip_vias':rip_v,'convert_vias':conv_v,'vias_under_body_only':under_only,'tracks_hit':sorted(set(topT[i]['net'] for i in ht)),'n_tracks_hit':len(ht)}
if __name__=='__main__':
    out=[]
    for cx in [float(sys.argv[1])]:
        FB,FBt,FP=fixed_top(cx)
        for ux in np.arange(21.7,22.75,0.1):
            for uy in np.arange(12.1,16.0,0.05):
                m=ok(ux,uy,FB,FBt,FP)
                if not m: continue
                c=cost(ux,uy)
                out.append((round(ux,2),round(uy,2),len(c['rip_vias']),c['n_tracks_hit'],len(c['convert_vias']),min(m)))
    print('feasible',len(out))
    out.sort(key=lambda r:(r[2]*5+r[3],r[4],-r[5]))
    for r in out[:15]: print(r)
    xs=[r[0] for r in out];ys=[r[1] for r in out]; print('ux',min(xs),max(xs),'uy',min(ys),max(ys))
    json.dump(out,open('refine_%s.json'%sys.argv[1],'w'))
