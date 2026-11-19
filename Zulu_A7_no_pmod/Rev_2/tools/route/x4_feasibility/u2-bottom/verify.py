import json,sys,math,copy,collections
sys.path.insert(0,'.')
from copper import *
cx,cy,rot=54.025,12.275,0
DISP=['C110','C111','C114','C115','C119','C121','C122','C123','C91','C95','R25','R90','R91']
M2=copy.deepcopy(M); D2=copy.deepcopy(D)
rs,body,_=u2geom(cx,cy,rot)
newpads=[]
for (r,pad,net) in rs:
    newpads.append({'ref':'U2','pad':pad,'net':net,'x':(r[0]+r[2])/2,'y':(r[1]+r[3])/2,'shape':'rect','w':r[2]-r[0],'h':r[3]-r[1],'layers':['Bottom Layer'],'drill':0,'plated':False})
M2['pads']=[p for p in M2['pads'] if p['ref']!='U2' and p['ref'] not in DISP]+newpads
for c in D2['comps']:
    if c['ref']=='U2': c['layer']='BOTTOM'
P2=bc.build(M2,D2)
res=bc.check(P2,{'U2'},0.10)
print('body_check U2 (13 displaced removed):',res)
# pad-pad gap to nearest bottom pad
mn=9;who=None
for ref,v in P2['Bottom'].items():
    if ref=='U2': continue
    for pb,p in v['pads']:
        for r,_,_ in rs:
            g=bc.gap(r,pb)
            if g<mn: mn=g;who=(ref,p['pad'])
print('min U2 pad gap to other Bottom pad %.3f'%mn,who)
# Free-site search for an 0201 keepout (pads 0.9x0.3 + 0.2 gap, body 0.6x0.3) on Bottom, x>=38
occ=[]
for ref,v in P2['Bottom'].items():
    for pb,p in v['pads']: occ.append((pb,0.2))
    for b in v['body']: occ.append((b,0.1))
def free(box):
    if box[0]<0.3 or box[1]<0.3 or box[2]>60.66 or box[3]>25.1: return False
    return all(bc.gap(box,b)>=g for b,g in occ)
sites=[]
x=38.0
while x<60.5:
    y=2.6
    while y<22.9:
        for o in ('h','v'):
            pad=(x-0.45,y-0.15,x+0.45,y+0.15) if o=='h' else (x-0.15,y-0.45,x+0.15,y+0.45)
            if free(pad): sites.append((round(x,2),round(y,2),o))
        y+=0.1
    x+=0.1
# greedy disjoint
chosen=[]
for s in sites:
    x,y,o=s; pad=(x-0.45,y-0.15,x+0.45,y+0.15) if o=='h' else (x-0.15,y-0.45,x+0.15,y+0.45)
    if all(bc.gap(pad,c)>=0.2 for c in chosen): chosen.append(pad)
print('free 0201 sites on Bottom x>=38 (greedy, disjoint, ignoring copper):',len(chosen))
for c in chosen: print('  centre (%.2f,%.2f)'%((c[0]+c[2])/2,(c[1]+c[3])/2), 'dist to U1 centre %.1f'%math.hypot((c[0]+c[2])/2-46.4,(c[1]+c[3])/2-11.9))
json.dump({'U2':{'x':cx,'y':cy,'rot':rot,'side':'BOTTOM'},'removed':DISP},open('candidate_east.json','w'))
