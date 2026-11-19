import json,sys,math,collections
sys.path.insert(0,'.')
from scan import *
def seg_rect(t,r):
    n=max(2,int(math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])/0.02)); d=9
    for i in range(n+1):
        x=t['x1']+(t['x2']-t['x1'])*i/n; y=t['y1']+(t['y2']-t['y1'])*i/n
        dx=max(r[0]-x,0,x-r[2]); dy=max(r[1]-y,0,y-r[3]); d=min(d,math.hypot(dx,dy))
    return d-t['w']/2
def pt_rect(x,y,r):
    dx=max(r[0]-x,0,x-r[2]); dy=max(r[1]-y,0,y-r[3]); return math.hypot(dx,dy)
BT=[t for t in M['tracks'] if t['layer']=='Bottom Layer']
BV=[v for v in M['vias'] if 'Bottom Layer' in v['span']]
def copper(cx,cy,rot,clr=0.09):
    rs,body,_=u2geom(cx,cy,rot)
    e=bc.ext([r for r,_,_ in rs]); e=(e[0]-0.5,e[1]-0.5,e[2]+0.5,e[3]+0.5)
    tr=collections.defaultdict(float); vi=collections.Counter(); vspan=collections.Counter()
    for t in BT:
        if max(t['x1'],t['x2'])<e[0] or min(t['x1'],t['x2'])>e[2] or max(t['y1'],t['y2'])<e[1] or min(t['y1'],t['y2'])>e[3]: continue
        if any(seg_rect(t,r)<clr for r,_,_ in rs):
            tr[t['net']]+=math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
    for v in BV:
        if any(pt_rect(v['x'],v['y'],r)-v['size']/2<clr for r,_,_ in rs):
            vi[v['net']]+=1; vspan['through' if len(v['span'])==6 else 'L5-Bot']+=1
    return tr,vi,vspan
if __name__=='__main__':
    for cx,cy,rot in [(54.025,12.025,0),(54.025,12.275,0),(53.775,12.275,0),(53.275,12.275,90),(54.025,12.275,90)]:
        tr,vi,vs=copper(cx,cy,rot)
        print(cx,cy,rot,'tracks %.1f mm in %d nets'%(sum(tr.values()),len(tr)),'vias',sum(vi.values()),dict(vs))
        print('  nets',sorted(set(tr)|set(vi)))
