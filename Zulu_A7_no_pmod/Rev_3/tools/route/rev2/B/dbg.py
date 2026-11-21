import json,sys
sys.path.insert(0,'../../..')
import compose_plan as CP, prune_stubs as PS
base=json.load(open('../prep/base_moved.json'));rip=json.load(open(sys.argv[1]));rp=json.load(open(sys.argv[2]))
nets=sys.argv[3].split(',')
plan={'remove':rip['remove'],'remove_vias':rip['remove_vias'],'tracks':rp['tracks'],'vias':rp['vias']}
M=CP.apply(base,plan)
dt,dv,nt,nv=PS.analyse(M)
pk={CP.tkey(t) for t in rp['tracks']}
for t in dt:
  if t['net'] in nets: print('T','plan' if CP.tkey(t) in pk else 'board',t['layer'],t['w'],t['x1'],t['y1'],t['x2'],t['y2'])
for v in dv:
  if v['net'] in nets: print('V',v['x'],v['y'],v.get('span'))
for t in nt:
  if t.get('trimmed') and t['net'] in nets: print('TRIM',t)
