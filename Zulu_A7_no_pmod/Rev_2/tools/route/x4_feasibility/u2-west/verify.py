import geo, impact, json, math, collections
sm=json.load(open('small_fast.json'))
pl={'U2':(21.75,15.75,270.0)}
pl.update({r:(x,y,0.0) for r,(x,y) in sm.items()})
CX,CY=30.48,4.9
M,D=geo.build(pl,s2b=(CX,CY))
moved=set(pl)|{'X4'}
fb=geo.body_findings(M,D,moved); pc=geo.pad_checks(M,moved)
print('body findings involving moved parts (gap 0.10):',sorted(set(fb)))
print('pad findings (pad-pad 0.20, edge 0.30):',pc)
key=lambda r:r[:4]
allf=set(map(key,geo.body_findings(M,D,None))); base=set(map(key,geo.body_findings(*geo.build({},s2b=None),None)))
print('whole board body findings: before %d after %d; new %s; removed %s'%(len(base),len(allf),sorted(allf-base),sorted(base-allf)))
# min clearances of each moved part
parts=geo.BC.build(M,D)
def mind(ref):
    best=(9,None)
    for s,P in parts.items():
        if ref not in P: continue
        A=P[ref]
        for o,B in P.items():
            if o.split('[')[0]==ref: continue
            for x in A['body']+[b for b,_ in A['pads']]:
                for y in B['body']+[b for b,_ in B['pads']]:
                    g=geo.BC.gap(x,y)
                    if g<best[0]: best=(round(g,3),o)
    return best
for r in sorted(moved): print('  min gap %-5s'%r, mind(r))
# positions report
for r in sorted(moved):
    ps=[p for p in M['pads'] if p['ref']==r]; c=geo.centre(ps); e=geo.ext(ps)
    rot=[x['rot'] for x in D['comps'] if x['ref']==r][0]
    print('%-5s centre (%.3f, %.3f) rot %.0f Top  pad-ext x %.3f..%.3f y %.3f..%.3f'%(r,c[0],c[1],rot,e[0],e[2],e[1],e[3]))
json.dump({'placements':pl,'s2b':[CX,CY]},open('final_placement.json','w'),indent=1)
# impact
U=[p for p in M['pads'] if p['ref']=='U2']; e=geo.ext(U)
per,why,rt,rv=impact.impact(M,moved)
T,V=geo.M0['tracks'],geo.M0['vias']
own=set(p['net'] for p in geo.M0['pads'] if p['ref'] in moved and p['net'])-impact.PLANES
def toptr(v): return any(t['net']==v['net'] and t['layer']=='Top Layer' and min(math.hypot(t['x1']-v['x'],t['y1']-v['y']),math.hypot(t['x2']-v['x'],t['y2']-v['y']))<0.2 for t in T)
conv=[j for j in rv if V[j]['net'] not in own and V[j]['net'] not in impact.PLANES and not toptr(V[j])]
convp=[j for j in rv if V[j]['net'] in impact.PLANES and not any(True for _ in []) and j not in conv and 'stub' not in ' '.join(why[V[j]['net']])]
rip_v=[j for j in rv if j not in conv]
L=lambda idx: sum(impact.tlen(T[i]) for i in idx)
own_t=[i for i in rt if T[i]['net'] in own]; plane_t=[i for i in rt if T[i]['net'] in impact.PLANES]; for_t=[i for i in rt if T[i]['net'] not in own and T[i]['net'] not in impact.PLANES]
print('\nRIP: own-net tracks %d (%.1f mm) on %d nets; plane stubs %d (%.1f mm); foreign tracks %d (%.1f mm)'%(len(own_t),L(own_t),len(own),len(plane_t),L(plane_t),len(for_t),L(for_t)))
print('vias ripped %d (own %d, plane %d, foreign %d); foreign vias kept in place but re-spanned to drop the Top land: %d'%(len(rip_v),sum(1 for j in rip_v if V[j]['net'] in own),sum(1 for j in rip_v if V[j]['net'] in impact.PLANES),sum(1 for j in rip_v if V[j]['net'] not in own and V[j]['net'] not in impact.PLANES),len(conv)))
fn=collections.defaultdict(lambda:[0,0.0])
for i in for_t: fn[T[i]['net']][0]+=1; fn[T[i]['net']][1]+=impact.tlen(T[i])
print('foreign nets ripped:',{n:(a,round(b,2)) for n,(a,b) in fn.items()}, 'why:',{n:sorted(why[n]) for n in fn})
print('foreign rip vias:',[(V[j]['net'],V[j]['x'],V[j]['y'],V[j]['span'][0][:3]+'-'+V[j]['span'][-1][:3]) for j in rip_v if V[j]['net'] not in own and V[j]['net'] not in impact.PLANES])
print('re-span vias:',[(V[j]['net'],V[j]['x'],V[j]['y'],sorted(set(t['layer'][:3] for t in T if t['net']==V[j]['net'] and min(math.hypot(t['x1']-V[j]['x'],t['y1']-V[j]['y']),math.hypot(t['x2']-V[j]['x'],t['y2']-V[j]['y']))<0.2))) for j in conv])
print('SDRAM nets touched:',sorted(set(V[j]['net'] for j in rv if V[j]['net'] in geo.SDRAM)|set(T[i]['net'] for i in rt if T[i]['net'] in geo.SDRAM)))
own_rows=sorted(((n,round(sum(impact.tlen(T[i]) for i in own_t if T[i]['net']==n),1)) for n in own),key=lambda x:-x[1])
print('own nets:',own_rows)
json.dump({'rip_tracks':sorted(rt),'rip_vias':sorted(rip_v),'respan_vias':sorted(conv)},open('final_rip.json','w'))
