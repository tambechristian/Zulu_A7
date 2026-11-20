import json, math, sys
from collections import defaultdict
TOOLS='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'; SYNC=TOOLS+'/route/sync'
sys.path.insert(0,TOOLS); sys.path.insert(0,TOOLS+'/route/rev2/judge')
import router as R, judge as J
R.SDRAM |= {'SDRAM-D%d'%i for i in range(16)}
def tk(t): return (t['net'],t['layer'],round(t['w'],4),)+tuple(sorted([(round(t['x1'],4),round(t['y1'],4)),(round(t['x2'],4),round(t['y2'],4))]))
def vk(v): s=J.span(v); return (v['net'],round(v['x'],4),round(v['y'],4),s[0],s[-1])
T0=json.load(open(SYNC+'/prep/transplant.json')); TS=json.load(open(SYNC+'/prep/transplant_stubs.json'))
tr={tk(t) for t in T0['tracks']+TS['tracks']}|{vk(v) for v in T0['vias']+TS['vias']}
def layers(k,o): return J.pad_layers(o) if k=='p' else [o['layer']] if k=='t' else o['span']
for key in sys.argv[1:]:
    P=json.load(open('%s/%s/plan_%s.json'%(SYNC,key,key))); Rz=json.load(open('%s/judge/%s/result.json'%(SYNC,key)))
    own=[('t',t) for t in P['tracks'] if tk(t) not in tr]+[('v',dict(v,span=J.span(v))) for v in P['vias'] if vk(v) not in tr]
    allo=[('p',p) for p in Rz['pads']]+[('t',t) for t in Rz['tracks']]+[('v',v) for v in Rz['vias']]
    res=[]
    for k,o in own:
        best=None
        for k2,q in allo:
            if not set(layers(k,o))&set(layers(k2,q)): continue
            n1,n2=o.get('net') or '',q.get('net') or ''
            if n1 and n1==n2: continue
            if k2!='p':
                if k2=='t' and tk(q)==tk(o) if k=='t' else False: continue
            for l in set(layers(k,o))&set(layers(k2,q)):
                m=J.gap(k,o,k2,q)-max(R.clearance(n1,l),R.clearance(n2,l))
                if best is None or m<best[0]: best=(m,l,J.desc(k,o),J.desc(k2,q))
        res.append(best)
    res.sort(key=lambda r:r[0])
    print('== %s own routing objects (not in transplant/transplant_stubs): %d; margin <0.0005: %d, <0.002: %d, <0.005: %d'%(key,len(own),sum(r[0]<0.0005 for r in res),sum(r[0]<0.002 for r in res),sum(r[0]<0.005 for r in res)))
    for r in res[:8]: print('   %.5f %s | %s | %s'%r)
