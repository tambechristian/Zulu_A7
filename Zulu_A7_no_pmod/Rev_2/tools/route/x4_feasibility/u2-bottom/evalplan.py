import json,sys,math
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0,T)
import route_conn as RC
STACK=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('model_u2bot.json')); P=json.load(open(sys.argv[1]))
print({k:(len(v) if isinstance(v,list) else v) for k,v in P.items()})
M['tracks']=M['tracks']+P.get('tracks',[])
M['vias']=M['vias']+[dict(v,span=v.get('span') or STACK[STACK.index(v['from']):STACK.index(v['to'])+1]) for v in P.get('vias',[])]
oc=RC.open_count(RC.islands(M))
print('open',sum(oc.values()),oc)
L={}
for t in P.get('tracks',[]): L[t['net']]=L.get(t['net'],0)+math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
print('new copper %.1f mm'%sum(L.values()))
for n in ('USB_D_P','USB_D_N'): print(n,round(L.get(n,0),1))
