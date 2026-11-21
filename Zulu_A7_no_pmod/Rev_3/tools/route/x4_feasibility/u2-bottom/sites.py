import json,sys,math,copy
sys.path.insert(0,'.')
import verify as V
from copper import seg_rect, pt_rect, BT, BV
DISP=set(V.DISP)
# copper owned only by displaced parts: tracks/vias touching their pads are approximated as removable if net in their nets AND within 1.0 mm of the part
dpads=[p for p in V.M['pads'] if p['ref'] in DISP]
def owned(x,y,net):
    return any(p['net']==net and math.hypot(p['x']-x,p['y']-y)<0.9 for p in dpads)
TR=[t for t in BT if not (owned(t['x1'],t['y1'],t['net']) or owned(t['x2'],t['y2'],t['net']))]
VI=[v for v in BV if not owned(v['x'],v['y'],v['net'])]
def copper_free(box):
    for t in TR:
        if max(t['x1'],t['x2'])<box[0]-0.3 or min(t['x1'],t['x2'])>box[2]+0.3 or max(t['y1'],t['y2'])<box[1]-0.3 or min(t['y1'],t['y2'])>box[3]+0.3: continue
        if seg_rect(t,box)<0.09: return False
    for v in VI:
        if pt_rect(v['x'],v['y'],box)-v['size']/2<0.09: return False
    return True
U2c=(54.025,12.275)
good=[]
chosen=[]
for x,y,o in V.sites:
    pad=(x-0.45,y-0.15,x+0.45,y+0.15) if o=='h' else (x-0.15,y-0.45,x+0.15,y+0.45)
    if not copper_free(pad): continue
    if all(V.bc.gap(pad,c)>=0.2 for c in chosen):
        chosen.append(pad)
for c in chosen:
    cx,cy=(c[0]+c[2])/2,(c[1]+c[3])/2
    print('(%.2f,%.2f) dU1 %.1f dU2 %.1f'%(cx,cy,math.hypot(cx-46.4,cy-11.9),math.hypot(cx-U2c[0],cy-U2c[1])))
print('copper-free disjoint 0201 sites x>=38:',len(chosen),' within 5 mm of U1 centre:',sum(1 for c in chosen if math.hypot((c[0]+c[2])/2-46.4,(c[1]+c[3])/2-11.9)<5))
