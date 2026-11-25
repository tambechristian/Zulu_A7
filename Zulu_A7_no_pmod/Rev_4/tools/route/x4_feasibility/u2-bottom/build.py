"""Build the U2-on-Bottom model: U2 rot 90 (mirror + CCW 90) at (54.025,12.275) Bottom, 13 displaced 0201s moved to the
nearest copper-free sites, S2B in place of X4, conflicting copper removed."""
import json,sys,math,copy,collections,io,contextlib
sys.path.insert(0,'.')
with contextlib.redirect_stdout(io.StringIO()):
    import sites as S
from copper import seg_rect, pt_rect
import s2b as SB
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0,T)
import route_conn as RC
M=json.load(open(T+'/route/bodies/base.json'))
CX,CY,ROT=54.025,12.275,90
rs,body,_=S.V.u2geom(CX,CY,ROT)
DISP=S.V.DISP
U2N=sorted({p['net'] for p in M['pads'] if p['ref']=='U2' and p['net'] and p['net'] not in('GND','VCC3V3')})
log=collections.OrderedDict()
# 1. relocate displaced parts
sites=[((c[0]+c[2])/2,(c[1]+c[3])/2,'h' if c[2]-c[0]>c[3]-c[1] else 'v') for c in S.chosen]
used=set(); moves={}
newpads=[]
for ref in DISP:
    ps=[p for p in M['pads'] if p['ref']==ref]
    ox=sum(p['x'] for p in ps)/2; oy=sum(p['y'] for p in ps)/2
    horiz=abs(ps[0]['x']-ps[1]['x'])>abs(ps[0]['y']-ps[1]['y'])
    best=None
    for i,(x,y,o) in enumerate(sites):
        if i in used or (o=='h')!=horiz: continue
        # keep out of U2's pad ring + 0.2
        d=math.hypot(x-ox,y-oy)
        if best is None or d<best[0]: best=(d,i)
    d,i=best; used.add(i); x,y,o=sites[i]
    moves[ref]=(round(ox,3),round(oy,3),round(x,3),round(y,3),round(d,2))
    for p in ps:
        q=dict(p); q['x']=round(x+(p['x']-ox),4); q['y']=round(y+(p['y']-oy),4); newpads.append(q)
# 2. U2 pads
u2p=[]
for r,pad,net in rs:
    u2p.append({'ref':'U2','pad':pad,'net':net,'x':round((r[0]+r[2])/2,4),'y':round((r[1]+r[3])/2,4),'shape':'rect',
                'w':round(r[2]-r[0],4),'h':round(r[3]-r[1],4),'layers':['Bottom Layer'],'drill':0.0,'plated':False})
# 3. S2B pads replace X4
R,sbody=SB.s2b(30.48,4.9)
nets={'1':'VBATT','2':'GND','MP':''}
sbp=[]
for k,(n,r) in enumerate(R):
    sbp.append({'ref':'X4','pad':n if n!='MP' else 'MP%d'%k,'net':nets[n],'x':(r[0]+r[2])/2,'y':(r[1]+r[3])/2,'shape':'rect',
                'w':r[2]-r[0],'h':r[3]-r[1],'layers':['Top Layer'],'drill':0.0,'plated':False})
oldpads=[p for p in M['pads'] if p['ref'] in DISP]
M['pads']=[p for p in M['pads'] if p['ref'] not in DISP and p['ref'] not in ('U2','X4')]+newpads+u2p+sbp
# 4. copper removal
def near_old(x,y,net):
    return any(p['net']==net and math.hypot(p['x']-x,p['y']-y)<0.9 for p in oldpads)
u2rects=[r for r,_,_ in rs]
sbrects=[r for _,r in R]
newsm=[( (p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2),p['net']) for p in newpads]
def conflict_track(t):
    if t['layer']=='Bottom Layer':
        if any(seg_rect(t,r)<0.09 for r in u2rects): return 'U2pad'
        if any(n!=t['net'] and seg_rect(t,r)<0.09 for r,n in newsm): return 'newpart'
    if t['layer']=='Top Layer' and any(seg_rect(t,r)<0.09 for r in sbrects): return 'S2B'
    return ''
def conflict_via(v):
    if 'Bottom Layer' in v['span']:
        if any(pt_rect(v['x'],v['y'],r)-v['size']/2<0.09 for r in u2rects): return 'U2pad'
        if any(n!=v['net'] and pt_rect(v['x'],v['y'],r)-v['size']/2<0.09 for r,n in newsm): return 'newpart'
    if 'Top Layer' in v['span'] and any(pt_rect(v['x'],v['y'],r)-v['size']/2<0.09 for r in sbrects): return 'S2B'
    return ''
rip=collections.defaultdict(lambda:[0.0,0,set()])
kt=[];kv=[]
for t in M['tracks']:
    why='U2net' if t['net'] in U2N else ('dispstub' if near_old(t['x1'],t['y1'],t['net']) or near_old(t['x2'],t['y2'],t['net']) else conflict_track(t))
    if why:
        L=math.hypot(t['x2']-t['x1'],t['y2']-t['y1']); rip[t['net']][0]+=L; rip[t['net']][2].add(why)
    else: kt.append(t)
for v in M['vias']:
    why='U2net' if v['net'] in U2N else ('dispstub' if near_old(v['x'],v['y'],v['net']) else conflict_via(v))
    if why: rip[v['net']][1]+=1; rip[v['net']][2].add(why)
    else: kv.append(v)
M['tracks']=kt; M['vias']=kv
json.dump(M,open('model_u2bot.json','w'))
print('moves of displaced 0201s (old centre -> new centre, distance):')
for k,v in moves.items(): print(' ',k,v)
tot=sum(v[0] for v in rip.values()); nv=sum(v[1] for v in rip.values())
print('ripped: %.1f mm of track, %d vias, %d nets'%(tot,nv,len(rip)))
for n,(L,c,w) in sorted(rip.items(),key=lambda kv:-kv[1][0]): print('  %-16s %6.1f mm %3d vias %s'%(n,L,c,','.join(sorted(w))))
oc=RC.open_count(RC.islands(M))
print('open connections in the model:',sum(oc.values()),'in',len(oc),'nets')
print(oc)
json.dump({'moves':moves,'rip':{k:[v[0],v[1],sorted(v[2])] for k,v in rip.items()},'open':oc},open('build_summary.json','w'))
