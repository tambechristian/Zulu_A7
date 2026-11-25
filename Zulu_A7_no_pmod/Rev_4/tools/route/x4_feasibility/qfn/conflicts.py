import json,sys,math
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools')
import route_conn as C
M0=json.load(open('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools/route/bodies/base.json'))
yc=sys.argv[1]
NP=json.load(open('newpads_%s.json'%yc)); newpads=NP['u2']+NP['x4']
CLR=0.11
u2nets={p['net'] for p in M0['pads'] if p['ref']=='U2' and p['net']}
for t in M0['tracks']:
  if t['layer']!='Top Layer' or t['net'] in u2nets: continue
  s=(t['x1'],t['y1'],t['x2'],t['y2'])
  for p in newpads:
    if p['net']!=t['net'] or not p['net']:
      g=C.pad_seg(p,s)-t['w']/2
      if g<CLR: print('T %-12s (%.2f,%.2f)-(%.2f,%.2f) w%.3f vs %s-%s gap %.3f'%(t['net'],*s,t['w'],p['ref'],p['pad'],g)); break
for v in M0['vias']:
  if 'Top Layer' not in v['span'] : continue
  for p in newpads:
    if p['net']!=v['net'] or not p['net']:
      g=C.pad_point(p,v['x'],v['y'])-v['size']/2
      if g<CLR: print('V %-12s (%.2f,%.2f) %s>%s vs %s-%s gap %.3f'%(v['net'],v['x'],v['y'],v['span'][0],v['span'][-1],p['ref'],p['pad'],g)); break
