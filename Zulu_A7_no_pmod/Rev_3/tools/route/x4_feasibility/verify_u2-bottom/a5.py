import json,sys,math,collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
B=json.load(open(T+'/route/bodies/base.json')); D=json.load(open(T+'/route/bodies/comps.json'))
C={c['ref']:c for c in D['comps']}
by=collections.defaultdict(list)
for p in B['pads']: by[p['ref']].append(p)
def cen(r): ps=by[r]; return (sum(p['x'] for p in ps)/len(ps),sum(p['y'] for p in ps)/len(ps))
u2n={p['net'] for p in by['U2'] if p['net']}
print('U2 nets',sorted(u2n))
for n in ('D5','D6','D7','VU','VBATT','CHAN19'):
    print(n,[(p['ref'],p['pad']) for p in B['pads'] if p['net']==n])
print()
NEW=(54.025,12.275)
for r in sorted(by):
    if r=='U2': continue
    nets={p['net'] for p in by[r]}
    sh=nets&(u2n-{'GND','VCC3V3'})
    if sh or (r.startswith('C') and math.hypot(cen(r)[0]-31.475,cen(r)[1]-13.6)<9 and nets&{'VCC3V3'}):
        c=cen(r); print('%-5s %-6s %-14s (%.2f,%.2f) dOld %.1f dNew %.1f %s'%(r,C.get(r,{}).get('layer'),C.get(r,{}).get('pattern'),c[0],c[1],math.hypot(c[0]-31.475,c[1]-13.6),math.hypot(c[0]-NEW[0],c[1]-NEW[1]),sorted(nets)))
