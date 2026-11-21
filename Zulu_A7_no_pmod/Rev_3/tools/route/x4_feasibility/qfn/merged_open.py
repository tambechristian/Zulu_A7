import json,sys
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools')
import route_conn as C
STACK=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open(sys.argv[1]));P=json.load(open(sys.argv[2]))
M['tracks']+=P['tracks'];M['vias']+=[dict(v,span=v.get('span') or STACK[STACK.index(v['from']):STACK.index(v['to'])+1]) for v in P['vias']]
oc=C.open_count(C.islands(M));print('open',sum(oc.values()),oc)
import math
print('new tracks %d len %.1f mm, vias %d'%(len(P['tracks']),sum(math.hypot(t['x2']-t['x1'],t['y2']-t['y1']) for t in P['tracks']),len(P['vias'])))
