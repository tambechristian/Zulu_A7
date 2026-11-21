import json,sys
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools')
import route_conn as C
M0=json.load(open('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools/route/bodies/base.json'))
u2nets={p['net'] for p in M0['pads'] if p['ref']=='U2' and p['net']}
inb=lambda x,y:20<x<40 and 0<y<11
tops=[t for t in M0['tracks'] if t['layer']=='Top Layer' and t['net'] not in u2nets and (inb(t['x1'],t['y1']) or inb(t['x2'],t['y2']))]
vs=[v for v in M0['vias'] if 'Top Layer' in v['span'] and v['net'] not in u2nets and inb(v['x'],v['y'])]
X2=[p for p in M0['pads'] if p['ref']=='X2']
CY=4.9
for i in range(0,27):
  CX=29.19+0.1*i
  P=[]
  for pad,lx,ly,w,h,n in (('1',-1,-2.85,1,3.5,'VBATT'),('2',1,-2.85,1,3.5,'GND'),('MP1',-3.35,2.9,1.5,3.4,''),('MP2',3.35,2.9,1.5,3.4,'')):
    P.append({'ref':'X4','pad':pad,'net':n,'x':CX-lx,'y':CY-ly,'w':w,'h':h,'shape':'rect'})
  x2=min(C.pad_point(q,p['x'],p['y'])-p['w']/2 for q in P for p in X2)
  bad={}
  for t in tops:
    s=(t['x1'],t['y1'],t['x2'],t['y2'])
    for p in P:
      if (p['net']!=t['net'] or not p['net']) and C.pad_seg(p,s)-t['w']/2<0.11: bad[t['net']]=bad.get(t['net'],0)+1;break
  for v in vs:
    for p in P:
      if (p['net']!=v['net'] or not p['net']) and C.pad_point(p,v['x'],v['y'])-v['size']/2<0.11: bad[v['net']]=bad.get(v['net'],0)+1;break
  print('%.2f x2gap %.2f'%(CX,x2),bad)
