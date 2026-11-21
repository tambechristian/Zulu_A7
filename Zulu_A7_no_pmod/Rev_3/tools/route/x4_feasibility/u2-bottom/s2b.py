import json,sys,math
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0,T)
import body_check as bc
M=json.load(open(T+'/route/bodies/base.json')); D=json.load(open(T+'/route/bodies/comps.json'))
print([ (p['pad'],p['net'],p['x'],p['y'],p['w'],p['h']) for p in M['pads'] if p['ref']=='X4'])
def s2b(cx,cy0):
    # rot 180: local (x,y)->(cx-x, cy0-y)
    pads=[('1',-1,-2.85,1.0,3.5),('2',1,-2.85,1.0,3.5),('MP',-3.35,2.9,1.5,3.4),('MP',3.35,2.9,1.5,3.4)]
    R=[]
    for n,x,y,w,h in pads:
        X,Y=cx-x,cy0-y; R.append((n,(X-w/2,Y-h/2,X+w/2,Y+h/2)))
    body=(cx-3.95,cy0-4.4,cx+3.95,cy0+3.2)
    return R,body
cx,cy0=30.48,4.9
R,body=s2b(cx,cy0)
print('S2B pads',R,'body',body)
P=bc.build(M,D)['Top']
for ref,v in P.items():
    if ref in ('X4','U2'): continue
    g=9
    for _,r in R:
        for pb,p in v['pads']: g=min(g,bc.gap(r,pb)-0.1)
        for b in v['body']: g=min(g,bc.gap(r,b))
    for pb,p in v['pads']: g=min(g,bc.gap(body,pb))
    for b in v['body']: g=min(g,bc.gap(body,b))
    if g<0.5: print('near',ref,round(g,3))
# allowed cx range vs X2 pads
# Top copper conflicts
def segbox_dist(t,r):
    # distance from segment to rect (sampled)
    n=max(2,int(math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])/0.02))
    d=9
    for i in range(n+1):
        x=t['x1']+(t['x2']-t['x1'])*i/n; y=t['y1']+(t['y2']-t['y1'])*i/n
        dx=max(r[0]-x,0,x-r[2]); dy=max(r[1]-y,0,y-r[3]); d=min(d,math.hypot(dx,dy))
    return d-t['w']/2
hit={}
for t in M['tracks']:
    if t['layer']!='Top Layer': continue
    for n,r in R:
        if segbox_dist(t,r)<0.09:
            L=math.hypot(t['x2']-t['x1'],t['y2']-t['y1']); hit.setdefault(t['net'],[0,0]); hit[t['net']][0]+=1; hit[t['net']][1]+=L; break
for v in M['vias']:
    if 'Top Layer' not in v['span']: continue
    for n,r in R:
        dx=max(r[0]-v['x'],0,v['x']-r[2]); dy=max(r[1]-v['y'],0,v['y']-r[3])
        if math.hypot(dx,dy)-v['size']/2<0.09: hit.setdefault(v['net'],[0,0]); hit[v['net']].append(('via',v['x'],v['y'],v['span'][-1])); break
print('Top copper under S2B pads:',hit)
