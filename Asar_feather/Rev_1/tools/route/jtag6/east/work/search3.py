import json,numpy as np
Z=np.load('grid.npz',allow_pickle=True); meta=json.load(open('grid_meta.json'))
padg,bodyg,bad,xs,ys=Z['padg'],Z['bodyg'],Z['bad'],Z['xs'],Z['ys']
keys=meta['keys']; padw=meta['padw']; bodyw=meta['bodyw']
S=0.05; P=1.27
NX,NY=len(xs),len(ys)
def offs(kind):
  if kind=='2x3v': return [(i*P,j*P) for i in range(2) for j in range(3)]
  if kind=='3x2h': return [(i*P,j*P) for i in range(3) for j in range(2)]
  if kind=='line_v': return [(0,j*P) for j in range(6)]
  return [(i*P,0) for i in range(6)]
out=[]
for kind in ['2x3v','3x2h','line_v','line_h']:
  O=offs(kind)
  for ix in range(NX):
    for iy in range(NY):
      cells=[]
      ok=True
      for dx,dy in O:
        x,y=xs[ix]+dx,ys[iy]+dy
        jx,jy=int(round((x-xs[0])/S)),int(round((y-ys[0])/S))
        if jx>=NX or jy>=NY: ok=False;break
        cells.append((jx,jy))
      if not ok: continue
      pg=min(padg[c] for c in cells); bg=min(bodyg[c] for c in cells)
      if pg<0.2 or bg<0.1: continue
      ks=set()
      for c in cells: ks|=set(np.nonzero(bad[:,c[0],c[1]])[0].tolist())
      nets=sorted(set(keys[k][1] for k in ks))
      out.append((kind,float(xs[ix]),float(ys[iy]),round(float(pg),3),round(float(bg),3),len(ks),nets))
for kind in ['2x3v','3x2h','line_v','line_h']:
  rr=[r for r in out if r[0]==kind]
  print(kind,len(rr))
  rr.sort(key=lambda r:(r[5],-min(r[4],0.3),abs(r[1]-17.75)+abs(r[2]-5.05)))
  for r in rr[:12]: print('  ',r)
json.dump(out,open('cands.json','w'))
