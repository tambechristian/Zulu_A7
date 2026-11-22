import json,math,sys
import numpy as np
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
import body_check as B
J = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))).replace(chr(92), '/') + '/'   # tools/route/jtag6/ (was the session scratchpad)
M=json.load(open(J+'model.json')); D=json.load(open(J+'comps.json'))
parts=B.build(M,D)['Bottom']
X0,X1,Y0,Y1,S=12.0,27.0,2.5,11.5,0.05
xs=np.round(np.arange(X0,X1+1e-9,S),3); ys=np.round(np.arange(Y0,Y1+1e-9,S),3)
GX,GY=np.meshgrid(xs,ys,indexing='ij')
def rectgap(b):   # JP square 1x1 at grid vs rect b
  dx=np.maximum(np.maximum(b[0]-(GX+.5),(GX-.5)-b[2]),0); dy=np.maximum(np.maximum(b[1]-(GY+.5),(GY-.5)-b[3]),0)
  ox=np.maximum(b[0]-(GX+.5),(GX-.5)-b[2]); oy=np.maximum(b[1]-(GY+.5),(GY-.5)-b[3])
  g=np.hypot(dx,dy); return np.where((ox<0)&(oy<0),np.maximum(ox,oy),g)
padg=np.full(GX.shape,9.0); bodyg=np.full(GX.shape,9.0); padw=np.full(GX.shape,'',dtype=object); bodyw=np.full(GX.shape,'',dtype=object)
for p in M['pads']:
  if p['ref'] in ('JP3','JP4') or 'Bottom Layer' not in (p['layers'] or B.STACK): continue
  if p['x']<X0-3 or p['x']>X1+3 or p['y']<Y0-3 or p['y']>Y1+3: continue
  g=rectgap((p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2))
  m=g<padg; padg=np.where(m,g,padg); padw[m]='%s-%s'%(p['ref'],p['pad'])
for n,P in parts.items():
  if n.split('[')[0] in ('JP3','JP4'): continue
  for b in P['body']:
    g=rectgap(b); m=g<bodyg; bodyg=np.where(m,g,bodyg); bodyw[m]=n
JTN={'TCK','TMS','TDI','TDO'}
own_v=[(17.475,7.275),(17.375,5.175),(7.275,2.775)]
cu={}   # (kind,net,idx) -> clearance grid (round pad r=0.5)
def segd(x1,y1,x2,y2):
  vx,vy=x2-x1,y2-y1; L=vx*vx+vy*vy
  t=np.zeros(GX.shape) if L==0 else np.clip(((GX-x1)*vx+(GY-y1)*vy)/L,0,1)
  return np.hypot(GX-x1-t*vx,GY-y1-t*vy)
for i,v in enumerate(M['vias']):
  if 'Bottom Layer' not in v['span'] or v['net'] in JTN: continue
  if any(abs(v['x']-a)<1e-3 and abs(v['y']-b)<1e-3 for a,b in own_v): continue
  if v['x']<X0-2 or v['x']>X1+2 or v['y']<Y0-2 or v['y']>Y1+2: continue
  cu[('v',v['net'],i)]=np.hypot(GX-v['x'],GY-v['y'])-.5-v['size']/2
for i,t in enumerate(M['tracks']):
  if t['layer']!='Bottom Layer' or t['net'] in JTN: continue
  if max(t['x1'],t['x2'])<X0-2 or min(t['x1'],t['x2'])>X1+2 or max(t['y1'],t['y2'])<Y0-2 or min(t['y1'],t['y2'])>Y1+2: continue
  cu[('t',t['net'],i)]=segd(t['x1'],t['y1'],t['x2'],t['y2'])-.5-t['w']/2
keys=list(cu); A=np.stack([cu[k] for k in keys])   # K x NX x NY
bad=A<0.09
np.savez('grid.npz',padg=padg,bodyg=bodyg,bad=bad,xs=xs,ys=ys)
json.dump({'keys':[list(k) for k in keys],'padw':padw.tolist(),'bodyw':bodyw.tolist()},open('grid_meta.json','w'))
print(A.shape)
