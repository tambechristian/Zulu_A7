import json, copy, math, sys, collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0,T)
import body_check as BC
M0=json.load(open(T+'/route/bodies/base.json'))
D0=json.load(open(T+'/route/bodies/comps.json'))
W,H=60.96,25.4
STACK=BC.STACK
def pads_of(M,ref): return [p for p in M['pads'] if p['ref']==ref]
def ext(ps): return (min(p['x']-p['w']/2 for p in ps),min(p['y']-p['h']/2 for p in ps),max(p['x']+p['w']/2 for p in ps),max(p['y']+p['h']/2 for p in ps))
# X1 local frame: origin = mating centre on board edge (30.48, 25.4), +v = outward
X1_ORIG=(30.48,25.4)
def x1_east(M,D,yc):
    """X1 rotated so the opening faces +x, centred on y=yc at the east edge."""
    ps=pads_of(M0,'X1')
    new=[]
    for p in ps:
        dx,dy=p['x']-X1_ORIG[0],p['y']-X1_ORIG[1]
        q=dict(p); q['x']=W+dy; q['y']=yc-dx; q['w'],q['h']=p['h'],p['w']; new.append(q)
    M['pads']=[p for p in M['pads'] if p['ref']!='X1']+new
    b=D0['mech']['X1']['body']  # x0,y0,x1,y1 at rot0
    bx=(W+(b[1]-25.4), yc-(b[2]-30.48), W+(b[3]-25.4), yc-(b[0]-30.48))
    e=ext(new)
    D['mech']['X1']={'off':[bx[0]-e[0],bx[1]-e[1],bx[2]-e[2],bx[3]-e[3]],'body':list(bx)}
    for c in D['comps']:
        if c['ref']=='X1': c['rot']=270.0
    return new,bx
def s2b(M,D,cx,cy=4.9,ref='X4'):
    """JST S2B-PH-SM4-TB rotated 180 (mating face toward -y)."""
    loc=[('1',-1,-2.85,1.0,3.5,'VBATT'),('2',1,-2.85,1.0,3.5,'GND'),('MP1',-3.35,2.9,1.5,3.4,''),('MP2',3.35,2.9,1.5,3.4,'')]
    # rot180: (x,y)->(-x,-y)
    new=[{'ref':ref,'pad':n,'net':net,'x':cx-x,'y':cy-y,'shape':'rect','w':w,'h':h,'layers':['Top Layer'],'drill':0.0,'plated':False} for n,x,y,w,h,net in loc]
    M['pads']=[p for p in M['pads'] if p['ref']!=ref]+new
    bx=(cx-3.95,cy-4.4,cx+3.95,cy+3.2)
    e=ext(new)
    D['mech'][ref]={'off':[bx[0]-e[0],bx[1]-e[1],bx[2]-e[2],bx[3]-e[3]],'body':list(bx)}
    return new,bx
def move(M,ref,dx,dy):
    out=[]
    for p in M['pads']:
        if p['ref']==ref: p['x']+=dx; p['y']+=dy; out.append(p)
    return out
def place(M,D,ref,x,y,rot=None):
    """move part so its pad-extent centre is at (x,y); rot 0/90 swap for 2-pad parts about the centre."""
    ps=pads_of(M,ref); e=ext(ps); cx,cy=(e[0]+e[2])/2,(e[1]+e[3])/2
    c=[c for c in D['comps'] if c['ref']==ref][0]
    if rot is not None and (round(rot)-round(c['rot']))%180==90:
        for p in ps:
            dx,dy=p['x']-cx,p['y']-cy; p['x'],p['y']=cx-dy,cy+dx; p['w'],p['h']=p['h'],p['w']
        c['rot']=rot
    for p in ps: p['x']+=x-cx; p['y']+=y-cy
    return ps
def seg_box_dist(x1,y1,x2,y2,b):
    # distance from segment to box (approx by sampling)
    n=max(2,int(math.hypot(x2-x1,y2-y1)/0.02)+1); best=9e9
    for i in range(n+1):
        t=i/n; x=x1+(x2-x1)*t; y=y1+(y2-y1)*t
        dx=max(b[0]-x,0,x-b[2]); dy=max(b[1]-y,0,y-b[3]); best=min(best,math.hypot(dx,dy))
    return best
def pad_box(p):
    return (p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2)
def copper_conflicts(M,newpads,clr=0.10,skip_same_net=True):
    """other-net tracks/vias on the layers of the new pads within clr of the pad (track edge)."""
    out=[]
    for p in newpads:
        L=p['layers'] or STACK; b=pad_box(p)
        for t in M['tracks']:
            if t['layer'] not in L: continue
            if skip_same_net and p['net'] and t['net']==p['net']: continue
            d=seg_box_dist(t['x1'],t['y1'],t['x2'],t['y2'],b)-t['w']/2
            if d<clr: out.append(('track',p['ref'],p['pad'],t['net'],t['layer'],round(d,3),t))
        for v in M['vias']:
            sp=v['span']; i0,i1=STACK.index(sp[0]),STACK.index(sp[-1])
            vl=STACK[min(i0,i1):max(i0,i1)+1]
            if not set(vl)&set(L): continue
            if skip_same_net and p['net'] and v['net']==p['net']: continue
            dx=max(b[0]-v['x'],0,v['x']-b[2]); dy=max(b[1]-v['y'],0,v['y']-b[3]); d=math.hypot(dx,dy)-v['size']/2
            if d<clr: out.append(('via',p['ref'],p['pad'],v['net'],'/'.join(sp),round(d,3),v))
    return out
def tlen(t): return math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
def pad_pad(M,refs,clr=0.15):
    out=[]
    mine=[p for p in M['pads'] if p['ref'] in refs]
    for p in mine:
        L=set(p['layers'] or STACK); b=pad_box(p)
        for q in M['pads']:
            if q['ref']==p['ref'] or (q['ref'] in refs and q['ref']<p['ref']): continue
            if not L&set(q['layers'] or STACK): continue
            g=BC.gap(b,pad_box(q))
            if g<clr: out.append((p['ref'],p['pad'],q['ref'],q['pad'],round(g,3)))
    return out
def edge_clear(ps,clr=0.3):
    return [(p['ref'],p['pad'],round(min(pad_box(p)[0],pad_box(p)[1],W-pad_box(p)[2],H-pad_box(p)[3]),3)) for p in ps if min(pad_box(p)[0],pad_box(p)[1],W-pad_box(p)[2],H-pad_box(p)[3])<clr]
