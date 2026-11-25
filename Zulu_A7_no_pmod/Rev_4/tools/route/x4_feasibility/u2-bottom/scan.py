import json, sys, math, collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0,T)
import body_check as bc
M=json.load(open(T+'/route/bodies/base.json')); D=json.load(open(T+'/route/bodies/comps.json'))
C={c['ref']:c for c in D['comps']}
P=bc.build(M,D)
W,H=60.96,25.4
U2=[p for p in M['pads'] if p['ref']=='U2']
ux=(min(p['x']-p['w']/2 for p in U2)+max(p['x']+p['w']/2 for p in U2))/2
uy=(min(p['y']-p['h']/2 for p in U2)+max(p['y']+p['h']/2 for p in U2))/2
# relative pad rects, mirrored in x for bottom
rel=[(-(p['x']-ux), p['y']-uy, p['w'], p['h'], p['pad'], p['net']) for p in U2]
def u2geom(cx,cy,rot):
    rs=[]
    for x,y,w,h,pad,net in rel:
        if rot==90: x,y,w,h=-y,x,h,w
        rs.append(((cx+x-w/2,cy+y-h/2,cx+x+w/2,cy+y+h/2),pad,net))
    body=(cx-5,cy-5,cx+5,cy+5); bodyt=(cx-5.1,cy-5.1,cx+5.1,cy+5.1)
    return rs,body,bodyt
B=P['Bottom']
SMALL={'R0201','C0201','R0402','C0402'}
def classify(ref):
    r=ref.split('[')[0]
    if r not in C: return 'fixed'
    pat=C[r]['pattern']
    if r in ('X2','JP3','JP4','X1'): return 'fixed'
    if pat in SMALL: return 'small'
    if pat in ('C0603','C0805','IND0603','R0603'): return 'medium'
    return 'large'
PADGAP=0.20; BODYGAP=0.10; EDGE=0.30
def conflicts(cx,cy,rot):
    rs,body,bodyt=u2geom(cx,cy,rot)
    # edge
    e=bc.ext([r for r,_,_ in rs])
    if e[0]<EDGE or e[1]<EDGE or e[2]>W-EDGE or e[3]>H-EDGE or body[0]<0 or body[1]<0 or body[2]>W or body[3]>H: return None
    hits={}
    for ref,v in B.items():
        if ref.split('[')[0]=='U2': continue
        g=9
        for pb,p in v['pads']:
            for r,_,_ in rs: g=min(g,bc.gap(r,pb)-PADGAP+BODYGAP)
            g=min(g,bc.gap(body,pb))
        for b in v['body']:
            g=min(g,bc.gap(body,b))
            for r,_,_ in rs: g=min(g,bc.gap(r,b))
        for b in v['bodyt']: g=min(g,bc.gap(bodyt,b)+BODYGAP)
        if g<BODYGAP: hits[ref]=round(g-BODYGAP,3)
    return hits
if __name__=='__main__':
    print('U2 pad-extent centre',ux,uy)
    res=[]
    step=0.25
    for rot in (0,90):
        cy=6.775
        while cy<=18.63:
            cx=6.775
            while cx<=W-6.775:
                h=conflicts(cx,cy,rot)
                if h is not None:
                    cls=collections.Counter(classify(r) for r in h)
                    res.append((cls['fixed'],cls['large'],cls['medium'],cls['small'],rot,round(cx,3),round(cy,3),sorted(h)))
                cx+=step
            cy+=step
    res.sort()
    json.dump(res,open('scan.json','w'))
    print(len(res),'candidates')
    for r in res[:25]: print(r)
    # best per (fixed,large) bucket
    seen=set()
    for r in res:
        k=(r[0],r[1])
        if k in seen: continue
        seen.add(k); print('BUCKET',k,r)
