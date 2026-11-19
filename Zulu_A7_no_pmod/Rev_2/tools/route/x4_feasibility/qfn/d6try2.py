import json,sys
M0=json.load(open('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/route/bodies/base.json'))
S=json.load(open(sys.argv[3]))
NX,NY=float(sys.argv[1]),float(sys.argv[2])
ts=[];vs=[]
for t in M0['tracks']:
  if t['net']!='D6': continue
  t=dict(t)
  for a,b in (('x1','y1'),('x2','y2')):
    if abs(t[a]-30.975)<1e-3 and abs(t[b]-8.925)<1e-3: t[a],t[b]=NX,NY
  if t['layer']=='L3-SIG' and abs(t['x1']-NX)<1e-6 and abs(t['y1']-NY)<1e-6:
    ts.append(dict(t,x2=NX,y2=7.0)); ts.append(dict(t,x1=NX,y1=7.0)); continue
  ts.append(t)
for v in M0['vias']:
  if v['net']!='D6': continue
  v=dict(v)
  if abs(v['x']-30.975)<1e-3: v['x'],v['y']=NX,NY
  v['from'],v['to']=v['span'][0],v['span'][-1]; del v['span']
  vs.append(v)
json.dump({'tracks':ts,'vias':vs,'remove':[]},open('d6_fix.json','w'),indent=0)
json.dump({'tracks':S['tracks']+ts,'vias':S['vias']+vs,'remove':[]},open(sys.argv[4],'w'))
