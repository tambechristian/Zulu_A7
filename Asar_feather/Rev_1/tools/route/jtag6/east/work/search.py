import json,math,sys
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
import route_conn as C, body_check as B
J = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))).replace(chr(92), '/') + '/'   # tools/route/jtag6/ (was the session scratchpad)
M=json.load(open(J+'model.json')); D=json.load(open(J+'comps.json'))
parts=B.build(M,D)['Bottom']
bodies=[(n,b) for n,P in parts.items() if n.split('[')[0] not in ('JP3','JP4') for b in P['body']]
opads=[p for p in M['pads'] if p['ref'] not in ('JP3','JP4') and 'Bottom Layer' in (p['layers'] or B.STACK)]
JTN={'TCK','TMS','TDI','TDO'}
# own copper that will be redone: the JTAG nets' bottom copper near the pads, JP3-3/JP4-3 tie vias
own_v=[(17.475,7.275),(17.375,5.175),(7.275,2.775)]
ov=[v for v in M['vias'] if 'Bottom Layer' in v['span'] and v['net'] not in JTN and not any(abs(v['x']-a)<1e-3 and abs(v['y']-b)<1e-3 for a,b in own_v)]
ot=[t for t in M['tracks'] if t['layer']=='Bottom Layer' and t['net'] not in JTN]
def box(x,y): return (x-.5,y-.5,x+.5,y+.5)
def evalpos(cents):
  r={'pad':9,'body':9,'cu':[], 'cumin':9}
  for x,y in cents:
    if x<0.8 or y<0.8 or x>50 or y>22.06: return None
    for p in opads:
      if abs(p['x']-x)>3 or abs(p['y']-y)>3: continue
      g=B.gap(box(x,y),(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2))
      r['pad']=min(r['pad'],g)
    for n,b in bodies:
      g=B.gap(box(x,y),b); r['body']=min(r['body'],g)
    for v in ov:
      if abs(v['x']-x)>2 or abs(v['y']-y)>2: continue
      g=math.hypot(v['x']-x,v['y']-y)-.5-v['size']/2
      if g<0.09: r['cu'].append(('v',v['net'],round(g,3)))
    for t in ot:
      g=C.seg_dist(t['x1'],t['y1'],t['x2'],t['y2'],x,y)-.5-t['w']/2
      if g<0.09: r['cu'].append(('t',t['net'],round(g,3)))
  return r
