import json,sys,math,copy
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0,T)
import body_check as bc
from copper import seg_rect, pt_rect
M=json.load(open('model_u2bot.json')); D=copy.deepcopy(json.load(open(T+'/route/bodies/comps.json')))
for c in D['comps']:
    if c['ref']=='U2': c['layer']='BOTTOM'
P=bc.build(M,D)['Bottom']
occ=[]
for ref,v in P.items():
    for pb,p in v['pads']: occ.append((pb,0.2))
    for b in v['body']: occ.append((b,0.1))
BT=[t for t in M['tracks'] if t['layer']=='Bottom Layer']; BV=[v for v in M['vias'] if 'Bottom Layer' in v['span']]
def ok(box):
    if box[0]<0.3 or box[1]<0.3 or box[2]>60.66 or box[3]>25.1: return False
    if not all(bc.gap(box,b)>=g for b,g in occ): return False
    for t in BT:
        if max(t['x1'],t['x2'])<box[0]-0.3 or min(t['x1'],t['x2'])>box[2]+0.3 or max(t['y1'],t['y2'])<box[1]-0.3 or min(t['y1'],t['y2'])>box[3]+0.3: continue
        if seg_rect(t,box)<0.09: return False
    return all(pt_rect(v['x'],v['y'],box)-v['size']/2>=0.09 for v in BV)
U2c=(54.025,12.275)
for name,(L,W) in {'0201':(0.9,0.3),'0402':(1.5,0.6),'0603':(2.5,0.9)}.items():
    ch=[]
    x=44.0
    while x<60.7:
        y=2.6
        while y<23:
            if math.hypot(x-U2c[0],y-U2c[1])<9.5:
                for (a,b) in ((L,W),(W,L)):
                    box=(x-a/2,y-b/2,x+a/2,y+b/2)
                    if ok(box) and all(bc.gap(box,c)>=0.2 for c in ch): ch.append(box)
            y+=0.1
        x+=0.1
    print(name,'disjoint copper-free sites within 9.5 mm of new U2 centre (after U2-net copper ripped):',len(ch))
