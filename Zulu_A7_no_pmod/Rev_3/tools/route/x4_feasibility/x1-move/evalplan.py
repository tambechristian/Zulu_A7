import sys,json,math
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools')
import route_conn as RC
STACK=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
M=json.load(open('model_ripped.json')); P=json.load(open(sys.argv[1]))
M['tracks']=M['tracks']+P['tracks']
M['vias']=M['vias']+[dict(v,span=STACK[STACK.index(v['from']):STACK.index(v['to'])+1]) for v in P['vias']]
oc=RC.open_count(RC.islands(M)); print(sys.argv[1],'open',sum(oc.values()),oc)
L={}
for t in P['tracks']: L[t['net']]=L.get(t['net'],0)+math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
print('new track mm %.1f, vias %d'%(sum(L.values()),len(P['vias'])))
for n in ('USB_D_P','USB_D_N','USB5V0','VBATT','D5','D6','D7','SDRAM-D13'): print('  %s %.2f mm'%(n,L.get(n,0)), {k:sum(1 for t in P['tracks'] if t['net']==n and t['layer']==k) for k in STACK if any(t['net']==n and t['layer']==k for t in P['tracks'])})
