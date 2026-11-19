import geo, impact, json, numpy as np, math
from search_u2 import gaps
UX,UY,UROT=21.75,15.75,270.0; CX,CY=30.48,4.9
SMALL=['LD0','LD1','LD2','LD3','LD4','BTN','C155','C158','C159']
MOVED=set(SMALL)|{'U2','X4'}
M,D=geo.build({'U2':(UX,UY,UROT)},s2b=(CX,CY))
per,why,rt,rv=impact.impact(M,MOVED)          # rip set without zones
T,V=geo.M0['tracks'],geo.M0['vias']
keepT=[t for i,t in enumerate(T) if i not in rt and t['layer']=='Top Layer']
keepV=[v for j,v in enumerate(V) if j not in rv and 'Top Layer' in v['span']]
Mf={'pads':[p for p in M['pads'] if p['ref'] not in SMALL]}
parts=geo.BC.build(Mf,D)['Top']
FB=np.array([b for P in parts.values() for b in P['body']]); FBt=np.array([b for P in parts.values() for b in P['bodyt']])
FP=np.array([b for P in parts.values() for b,_ in P['pads']])
# small-part templates (pads rel to centre, body)
tmpl={}
for r in SMALL:
    ps=[p for p in geo.M0['pads'] if p['ref']==r]; cx,cy=geo.centre(ps)
    c=[c for c in D['comps'] if c['ref']==r][0]
    L,W,Lt,Wt=geo.BC.BODY[c['pattern']]
    if round(c['rot'])%180==90: L,W,Lt,Wt=W,L,Wt,Lt
    tmpl[r]=([(p['x']-cx,p['y']-cy,p['w'],p['h'],p['net']) for p in ps],(L,W,Lt,Wt))
def boxes(r,x,y):
    pads,(L,W,Lt,Wt)=tmpl[r]
    P=np.array([(x+dx-w/2,y+dy-h/2,x+dx+w/2,y+dy+h/2) for dx,dy,w,h,n in pads])
    return P,np.array([[x-L/2,y-W/2,x+L/2,y+W/2]]),np.array([[x-Lt/2,y-Wt/2,x+Lt/2,y+Wt/2]])
def copper_ok(r,x,y):
    pads,_=tmpl[r]
    for dx,dy,w,h,n in pads:
        p={'x':x+dx,'y':y+dy,'w':w,'h':h,'shape':'rect','ref':r}
        for v in keepV:
            if v['net']!=n and abs(v['x']-p['x'])<1.5 and abs(v['y']-p['y'])<1.5 and geo.RC.pad_point(p,v['x'],v['y'])<v['size']/2+geo.CLEAR: return False
        for t in keepT:
            if t['net']!=n and min(t['x1'],t['x2'])-3<p['x']<max(t['x1'],t['x2'])+3 and min(t['y1'],t['y2'])-3<p['y']<max(t['y1'],t['y2'])+3 and geo.RC.pad_seg(p,(t['x1'],t['y1'],t['x2'],t['y2']))<t['w']/2+geo.CLEAR: return False
    return True
def fits(r,x,y,extraP,extraB,extraBt):
    P,B,Bt=boxes(r,x,y)
    if P[:,0].min()<0.3 or P[:,1].min()<0.3 or P[:,2].max()>geo.W-0.3 or P[:,3].max()>geo.H-0.3: return False
    fp=np.vstack([FP]+extraP) ; fb=np.vstack([FB]+extraB); fbt=np.vstack([FBt]+extraBt)
    if gaps(P,fp).min()<0.2 or gaps(B,fb).min()<0.1 or gaps(B,fp).min()<0.1 or gaps(P,fb).min()<0.1 or gaps(Bt,fbt).min()<0: return False
    return copper_ok(r,x,y)
def greedy(order, xs, y0, ymax, pitch):
    best=None
    for x in xs:
        eP,eB,eBt=[],[],[]; pos={}; y=y0
        for r in order:
            while y<ymax and not fits(r,x,y,eP,eB,eBt): y=round(y+0.05,3)
            if y>=ymax: break
            pos[r]=(x,y); P,B,Bt=boxes(r,x,y); eP.append(P); eB.append(B); eBt.append(Bt); y=round(y+pitch,3)
        if len(pos)==len(order):
            span=pos[order[-1]][1]-pos[order[0]][1]
            if best is None or span<best[0]: best=(span,pos)
    return best
if __name__=='__main__':
    xs=[round(29.0+0.1*i,2) for i in range(90)]
    b=greedy(['LD0','LD1','LD2','LD3','LD4'],xs,9.8,20.2,1.6)
    print('LED column', b)
    json.dump(b,open('led_col.json','w'))
