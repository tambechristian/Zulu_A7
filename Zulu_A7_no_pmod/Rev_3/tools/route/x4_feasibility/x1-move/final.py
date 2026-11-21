from pipeline import *
import route_conn as RC
PL={'C142':(46.25,12.5,0,'BOTTOM'),'C145':(59.75,8.0,90,'BOTTOM'),'R1':(57.0,3.5,90,'BOTTOM'),'C155':(25.9,20.6,180,'TOP')}
M,D,Mr,rt,rv,why=run(PL)
print('YC',YC,'DY',DY,'CX',CX)
# geometry proof
r=BC.check(BC.build(M,D),set(MOVED),0.10)
print('body_check (moved refs, gap 0.10):',len(r)); [print('  ',x) for x in sorted(set(r))]
r_all=BC.check(BC.build(M,D),None,0.10); r0=BC.check(BC.build(M0,D0),None,0.10)
k=lambda L:set((a,b,c,d) for a,b,c,d,_,__ in L)
print('board-wide body_check findings: before %d after %d; new:'%(len(k(r0)),len(k(r_all))),sorted(k(r_all)-k(r0)))
pp=pad_pad(M,set(MOVED),0.15); print('pad-pad <0.15:',pp)
print('edge <0.30:',edge_clear([p for p in M['pads'] if p['ref'] in MOVED]))
cc=copper_conflicts(Mr,[p for p in M['pads'] if p['ref'] in MOVED],0.10); print('copper conflicts left after rip:',len(cc))
# positions
for ref in MOVED:
    ps=pads_of(M,ref); e=ext(ps); c=[c for c in D['comps'] if c['ref']==ref][0]
    print('POS %-5s %-6s rot %5.1f  pad-extent centre (%.3f, %.3f)  extent x %.3f..%.3f y %.3f..%.3f'%(ref,c['layer'],c['rot'],(e[0]+e[2])/2,(e[1]+e[3])/2,e[0],e[2],e[1],e[3]))
for p in pads_of(M,'X1')+pads_of(M,'X4'): print('   ',p['ref'],p['pad'],p['net'],round(p['x'],3),round(p['y'],3),p['w'],p['h'],'THT' if p['drill'] else '')
# rip stats
per=collections.defaultdict(lambda:[0.0,0,0])
for t in rt: per[t['net']][0]+=tlen(t); per[t['net']][1]+=1
for v in rv: per[v['net']][2]+=1
tot=sum(v[0] for v in per.values())
print('RIPPED total track %.1f mm, %d tracks, %d vias, %d nets'%(tot,len(rt),len(rv),len(per)))
for n,(L,nt,nv) in sorted(per.items(),key=lambda kv:-kv[1][0]): print('  %-16s %7.2f mm %4d trk %3d via  %s'%(n,L,nt,nv,'; '.join(sorted(why.get(n,{'dead copper'})))))
oc=RC.open_count(RC.islands(Mr)); print('open connections after rip:',sum(oc.values()),oc)
json.dump(Mr,open('model_ripped.json','w'))
json.dump(D,open('comps_new.json','w'))
json.dump({'tracks':rt,'vias':rv},open('ripped.json','w'))
