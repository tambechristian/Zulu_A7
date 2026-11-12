import json,math,sys
sys.path.insert(0,'.')
M=json.load(open('route/jtag/after_title.json'))
mov={'C78','R108'}
rip=lambda t: t['net']=='VU' and max(t['x1'],t['x2'])<3.7 and t['layer']=='Bottom Layer'
pads=[p for p in M['pads'] if p['ref'] not in mov and p['ref'] not in ('JP3','JP4') and 'Bottom Layer' in p['layers']]
# the new JTAG column as square keep-outs on Bottom
for y in (6.35,8.89,11.43,13.97,16.51,19.05): pads.append({'x':1.10,'y':y,'w':1.524,'h':1.524})
trk=[t for t in M['tracks'] if t['layer']=='Bottom Layer' and not rip(t)]
via=[v for v in M['vias'] if 'Bottom Layer' in v['span'] and not (v['net']=='GND' and abs(v['x']-0.575)<.01)]
def ok_rect(cx,cy,w,h,m,extra=()):
    if cx-w/2<0.4 or cy-h/2<0.4: return False
    for p in list(pads)+list(extra):
        if abs(cx-p['x'])<(w+p['w'])/2+m and abs(cy-p['y'])<(h+p['h'])/2+m: return False
    for t in trk:
        n=max(2,int(math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])/.05))
        for k in range(n+1):
            x=t['x1']+(t['x2']-t['x1'])*k/n;y=t['y1']+(t['y2']-t['y1'])*k/n
            if abs(x-cx)<w/2+t['w']/2+m and abs(y-cy)<h/2+t['w']/2+m: return False
    for v in via:
        if abs(v['x']-cx)<w/2+v['size']/2+m and abs(v['y']-cy)<h/2+v['size']/2+m: return False
    return True
best=None
for i in range(0,140):
    for j in range(0,300):
        cx=2.0+i*.05;cy=4.0+j*.05
        if ok_rect(cx,cy-.85,1.5,1.3,.15) and ok_rect(cx,cy+.85,1.5,1.3,.15):
            d=math.hypot(cx-1.14,cy-7.9)
            if best is None or d<best[0]: best=(d,round(cx,2),round(cy,2))
print('C78 centre',best)
cx,cy=best[1],best[2]
c78=[{'x':cx,'y':cy-.85,'w':1.5,'h':1.3},{'x':cx,'y':cy+.85,'w':1.5,'h':1.3}]
bestr=None
for i in range(0,140):
    for j in range(0,300):
        x=2.0+i*.05;y=4.0+j*.05
        if ok_rect(x-.65,y,.7,.9,.15,c78) and ok_rect(x+.65,y,.7,.9,.15,c78):
            d=math.hypot(x-2.525,y-13.475)
            if bestr is None or d<bestr[0]: bestr=(d,round(x,2),round(y,2))
print('R108 centre',bestr)
json.dump({'C78':[cx,cy],'R108':[bestr[1],bestr[2]]},open('route/jtag2/sites.json','w'))
