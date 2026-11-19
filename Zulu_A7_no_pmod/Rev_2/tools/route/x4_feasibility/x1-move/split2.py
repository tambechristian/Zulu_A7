from rip import *
import pipeline
# contribution of the X1 relocation alone (X1 + displaced C142/C145/R1), U2/X4/C155 untouched
def contrib(refs, PL):
    M=copy.deepcopy(M0); D=copy.deepcopy(D0)
    if 'X1' in refs: x1_east(M,D,YC)
    if 'X4' in refs:
        s2b(M,D,CX)
    if 'U2' in refs: move(M,'U2',0,DY)
    for ref,(x,y,rot,side) in PL.items():
        if ref not in refs: continue
        if side=='BOTTOM':
            for c in D['comps']:
                if c['ref']==ref: c['layer']='BOTTOM'
            for p in M['pads']:
                if p['ref']==ref: p['layers']=['Bottom Layer']
        place(M,D,ref,x,y,rot)
    old=[p for p in M0['pads'] if p['ref'] in refs]
    new=[p for p in M['pads'] if p['ref'] in refs]
    Mr,rt,rv,why=build_ripped(M,refs,new,old)
    per=collections.defaultdict(float)
    for t in rt: per[t['net']]+=tlen(t)
    return sum(per.values()),len(rt),len(rv),dict(per)
PL={'C142':(46.25,12.5,0,'BOTTOM'),'C145':(59.75,8.0,90,'BOTTOM'),'R1':(57.0,3.5,90,'BOTTOM'),'C155':(25.9,20.6,180,'TOP')}
for name,refs in (('X1 relocation (X1,C142,C145,R1)',['X1','C142','C145','R1']),('U2 +2.6 + C155',['U2','C155']),('S2B replaces X4',['X4'])):
    L,nt,nv,per=contrib(refs,PL)
    print('%s: %.1f mm, %d tracks, %d vias; nets: %s'%(name,L,nt,nv,', '.join('%s %.1f'%kv for kv in sorted(per.items(),key=lambda kv:-kv[1]))))
