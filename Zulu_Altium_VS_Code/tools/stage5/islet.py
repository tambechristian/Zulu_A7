# -*- coding: utf-8 -*-
"""Exact-ish 4-connected island test of a plane, at a fine step, with NO snapping.
   python islet.py <plan.json|-> <NET>"""
import io, json, os, sys, math
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
TOOLS='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools'
sys.path.insert(0,TOOLS); sys.path.insert(0,os.path.join(TOOLS,'stage5'))
import route_emit as RE
inp=json.load(io.open(os.path.join(TOOLS,'route_inputs.json'),encoding='utf-8'))
plan={'vias':[],'tracks':[]}
if sys.argv[1]!='-':
    plan=json.load(io.open(sys.argv[1],encoding='utf-8'))
    if plan.get('remove'):
        inp,missing=RE.apply_removals(inp,plan); assert not missing,missing
NET=sys.argv[2]; STEP=float(sys.argv[3]) if len(sys.argv)>3 else 0.02
PB,CLR=0.508,0.25
o=inp['outline']
x0,y0,x1,y1=o['x0']+PB,o['y0']+PB,o['x1']-PB,o['y1']-PB
nx=int(round((x1-x0)/STEP))+1; ny=int(round((y1-y0)/STEP))+1
X,Y=np.meshgrid(x0+np.arange(nx)*STEP,y0+np.arange(ny)*STEP,indexing='ij')
cop=np.ones((nx,ny),bool)
holes=[(v['x'],v['y'],v.get('hole',0.2)/2.0+CLR) for v in inp['vias']+plan.get('vias',[]) if v['net']!=NET]
holes+=[(p['x'],p['y'],p['hole']/2.0+CLR) for p in inp['th_pads'] if p.get('net')!=NET]
for hx,hy,r in holes:
    cop&=~(((X-hx)**2+(Y-hy)**2)<=r*r)
idx=-np.ones((nx,ny),np.int64); cells=np.argwhere(cop)
idx[cells[:,0],cells[:,1]]=np.arange(len(cells)); NPc=len(cells)
ai=[];aj=[]
ii,jj=np.where(cop[:-1,:]&cop[1:,:]); ai+=list(idx[ii,jj]);aj+=list(idx[ii+1,jj])
ii,jj=np.where(cop[:,:-1]&cop[:,1:]);  ai+=list(idx[ii,jj]);aj+=list(idx[ii,jj+1])
n,lab=connected_components(sparse.coo_matrix((np.ones(len(ai)),(np.array(ai),np.array(aj))),shape=(NPc,NPc)),directed=False)
sz=np.bincount(lab); main=int(np.argmax(sz))
A=STEP*STEP
print('%s plane at step %.3f: %d 4-connected region(s); main %.3f mm2'%(NET,STEP,n,sz[main]*A))
order=np.argsort(sz)[::-1]
for r in order[1:]:
    if sz[r]*A<0.002: continue
    c=cells[lab==r]
    xs=x0+c[:,0]*STEP; ys=y0+c[:,1]*STEP
    print('   stray %8.4f mm2  x %.3f..%.3f  y %.3f..%.3f  centroid (%.3f,%.3f)'%(sz[r]*A,xs.min(),xs.max(),ys.min(),ys.max(),xs.mean(),ys.mean()))
print('   total stray area %.4f mm2 over %d region(s)'%((sz.sum()-sz[main])*A,n-1))
