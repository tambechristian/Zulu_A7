import json,sys,math
sys.path.insert(0,'.')
import route_conn as C
M=json.load(open('route/no_pmod/model.json'));P=json.load(open('route/no_pmod/d_f2.json'))
sp=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
span=lambda v:v.get('span') or sp[sp.index(v['from']):sp.index(v['to'])+1]
# the GND tie the router placed for the old R5-1 goes away
Pt=[t for t in P['tracks']]
gt=[t for t in Pt if t['net']=='GND' and max(t['x1'],t['x2'])<55 and min(t['x1'],t['x2'])>53.5 and 19.5<t['y1']<20.8]
print('old tie tracks',gt)
gv=[v for v in P['vias'] if v['net']=='GND' and 53.5<v['x']<55 and 19.5<v['y']<20.8]
print('old tie vias',gv)
T=[t for t in M['tracks']+Pt if t not in gt]
Va=[v for v in M['vias']+P['vias'] if v not in gv]
pads=[p for p in M['pads'] if p['ref']!='R5']
def dpt(layer,x,y,net):
    b=9
    for t in T:
        if t['layer']==layer and t['net']!=net and abs(t['x1']-x)<4 and abs(t['y1']-y)<4: b=min(b,C.seg_dist(t['x1'],t['y1'],t['x2'],t['y2'],x,y)-t['w']/2)
    for v in Va:
        if layer in span(v) and v['net']!=net and abs(v['x']-x)<2: b=min(b,math.hypot(v['x']-x,v['y']-y)-v['size']/2)
    for p in pads:
        if layer in p['layers'] and p['net']!=net and abs(p['x']-x)<3: b=min(b,C.pad_point(p,x,y))
    return b
def dseg(layer,a,b,c,d,net,w=.0762):
    n=max(2,int(math.hypot(c-a,d-b)/.04))
    return min(dpt(layer,a+(c-a)*i/n,b+(d-b)*i/n,net) for i in range(n+1))-w/2
LS=['Top Layer','L3-SIG','L4-SIG','Bottom Layer']
def thru_ok(x,y,net):
    return min(dpt(l,x,y,net) for l in LS)-.175>=.095
ends=[(55.4,20.1)]
res=[]
for rot in (0,180):
  s=1 if rot==0 else -1
  for i in range(-36,37):
    for j in range(-36,37):
        cx=round(55.4+i*.05,2);cy=round(20.1+j*.05,2)
        p2=(cx+.3*s,cy);p1=(cx-.3*s,cy)
        # pads clear (0.3 square -> 0.15 radius + 0.09 on the corners, approximately 0.24)
        if dpt('Bottom Layer',p2[0],p2[1],'FPGA-TCK')<.15*1.42+.09: continue
        if dpt('Bottom Layer',p1[0],p1[1],'GND')<.15*1.42+.09: continue
        if math.hypot(p1[0]-55.4,p1[1]-20.1)<.15+.15+.09: continue
        if dseg('Bottom Layer',55.4,20.1,p2[0],p2[1],'FPGA-TCK')<.09: continue
        # GND through via within 0.5 of pad 1
        tie=None
        for a in range(-12,13):
            for b in range(-12,13):
                vx=round(p1[0]+a*.05,2);vy=round(p1[1]+b*.05,2)
                if not .33<=math.hypot(vx-p1[0],vy-p1[1])<=.6: continue
                if thru_ok(vx,vy,'GND') and dseg('Bottom Layer',vx,vy,p1[0],p1[1],'GND')>=.09:
                    tie=(vx,vy);break
            if tie: break
        if tie: res.append((round(math.hypot(p2[0]-55.4,p2[1]-20.1),2),rot,cx,cy,tie))
res.sort();print(len(res),res[:6])
json.dump(res[:1],open('route/no_pmod/r5site.json','w'))
