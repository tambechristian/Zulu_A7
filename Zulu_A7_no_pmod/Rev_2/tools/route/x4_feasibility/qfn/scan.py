import json,sys,math
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import route_conn as C
M0=json.load(open('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/route/bodies/base.json'))
u2=[p for p in M0['pads'] if p['ref']=='U2']
u2nets={p['net'] for p in u2 if p['net']}
SD=set(['D%d' % i for i in range(16)]+['SDRAM-D%d'%i for i in range(16)]+['A%d' % i for i in range(13)]+['BS0','BS1','CAS#','RAS#','WE#','CKE','LDQM','UDQM','SDRAM-CS#','SDRAM-CLK'])
def pads(XC,YC,ep):
  out=[]
  for p in u2:
    n=int(p['pad']);k=(n-1)%16;off=-3.75+0.5*k;s=(n-1)//16
    x,y,w,h=[(XC-4.425,YC-off,.75,.28),(XC+off,YC-4.425,.28,.75),
             (XC+4.425,YC+off,.75,.28),(XC-off,YC+4.425,.28,.75)][s]
    out.append(dict(p,x=x,y=y,w=w,h=h))
  if ep: out.append(dict(u2[0],pad='65',net='GND',x=XC,y=YC,w=ep,h=ep))
  return out
inb=lambda x,y:23.5<x<39.5 and 9<y<21.5
tops=[t for t in M0['tracks'] if t['layer']=='Top Layer' and t['net'] not in u2nets and t['net'] not in('VU','VBATT','CHAN19') and (inb(t['x1'],t['y1']) or inb(t['x2'],t['y2']) or inb((t['x1']+t['x2'])/2,(t['y1']+t['y2'])/2))]
vs=[v for v in M0['vias'] if 'Top Layer' in v['span'] and v['net'] not in u2nets and inb(v['x'],v['y'])]
print(len(tops),len(vs))
X1=[p for p in M0['pads'] if p['ref']=='X1']
res=[]
for ep in (4.20,):
 for XC in [29.5+0.25*i for i in range(17)]:
  for YC in [14.55+0.125*i for i in range(8)]:
    P=pads(XC,YC,ep)
    # X1 clearance
    if min(C.pad_point(q,p['x'],p['y'])-p['w']/2 if p['shape']=='circle' else 9 for q in P for p in X1)<0.2: continue
    bad=set();nets=set()
    for t in tops:
      s=(t['x1'],t['y1'],t['x2'],t['y2'])
      for p in P:
        if p['net']!=t['net'] and C.pad_seg(p,s)-t['w']/2<0.11: bad.add(('t',id(t)));nets.add(t['net']);break
    for v in vs:
      for p in P:
        if p['net']!=v['net'] and C.pad_point(p,v['x'],v['y'])-v['size']/2<0.11: bad.add(('v',id(v)));nets.add(v['net']);break
    res.append((len(nets&SD),len(nets),len(bad),ep,XC,YC,sorted(nets)))
res.sort(key=lambda r:r[:3])
for ep in (4.20,):
  rr=[r for r in res if r[3]==ep][:6]
  for r in rr: print(r)
