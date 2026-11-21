import json,sys
M0=json.load(open('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools/route/bodies/base.json'))
M=json.load(open('modelA_d6.json'))
S=json.load(open(sys.argv[1]))
key=lambda t:(t['layer'],round(t['x1'],3),round(t['y1'],3),round(t['x2'],3),round(t['y2'],3))
have={key(t) for t in M['tracks'] if t['net']=='VU'}
X=float(sys.argv[3]) if len(sys.argv)>3 else 35.88
ts=[]
for t in M0['tracks']:
  if t['net']!='VU' or key(t) in have: continue
  x0=min(t['x1'],t['x2']);x1=max(t['x1'],t['x2'])
  if t['layer']=='Top Layer' and x1<=24.82 and min(t['y1'],t['y2'])>4.9: ts.append(t)   # west 1.5 mm trunk
  elif t['layer']=='Top Layer' and x0>=42.19: ts.append(t)                              # east part to X2-22
T=lambda x1,y1,x2,y2,w:{'net':'VU','layer':'Top Layer','w':w,'x1':x1,'y1':y1,'x2':x2,'y2':y2}
ts+= [T(24.8101,4.9493,X,4.9493,1.0),T(X,4.9493,X,2.85,0.6),T(X,2.85,36.4,2.85,0.6),T(36.4,2.85,42.2,2.85,1.2)]
have_v={(round(v['x'],3),round(v['y'],3)) for v in M['vias'] if v['net']=='VU'}
vs=[dict({k:v for k,v in x.items() if k!='span'},**{'from':x['span'][0],'to':x['span'][-1]}) for x in M0['vias'] if x['net']=='VU' and (round(x['x'],3),round(x['y'],3)) not in have_v]
json.dump({'tracks':ts,'vias':vs,'remove':[]},open('vu_fix.json','w'),indent=0)
json.dump({'tracks':S['tracks']+ts,'vias':S['vias']+vs,'remove':[]},open(sys.argv[2],'w'))
print(len(ts),'tracks',len(vs),'vias restored',[(v['x'],v['y']) for v in vs])
