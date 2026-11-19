import geo, impact, json, math
pl={k:tuple(v) for k,v in json.load(open('final_placement.json'))['placements'].items()}
M,D=geo.build(pl,s2b=(30.48,4.9))
moved=set(pl)|{'X4'}
F=json.load(open('final_rip.json')); own=json.load(open('minrip_own.json'))
T,V=geo.M0['tracks'],geo.M0['vias']
ownnets=set(p['net'] for p in geo.M0['pads'] if p['ref'] in moved and p['net'])-impact.PLANES
# whole-net rip from final_rip restricted to non-own (plane stubs + foreign), plus min own rip
rt=set(i for i in F['rip_tracks'] if T[i]['net'] not in ownnets)|set(own['t'])
rv=set(j for j in F['rip_vias'] if V[j]['net'] not in ownnets)|set(own['v'])
resp=set(F['respan_vias'])
STACK=geo.BC.STACK
def lay_at(v):
    return sorted(set(t['layer'] for t in T if t['net']==v['net'] and min(math.hypot(t['x1']-v['x'],t['y1']-v['y']),math.hypot(t['x2']-v['x'],t['y2']-v['y']))<0.2),key=STACK.index)
vias=[]
for j,v in enumerate(V):
    if j in rv: continue
    if j in resp:
        L=lay_at(v); lo=min(STACK.index(l) for l in L)
        v=dict(v, span=STACK[lo:], size=0.30, hole=0.15)
    vias.append(v)
Mx={'board':M['board'],'planes':M['planes'],'pads':M['pads'],'tracks':[t for i,t in enumerate(T) if i not in rt],'vias':vias}
json.dump(Mx,open('model_u2west.json','w'))
oc=geo.RC.open_count(geo.RC.islands(Mx))
print('open connections:',sum(oc.values()),'nets',len(oc)); print(sorted(oc.items()))
print('tracks removed',len(rt),'%.1f mm'%sum(impact.tlen(T[i]) for i in rt),'vias removed',len(rv),'respanned',len(resp))
