"""Compare an Altium Protel-format netlist (.NET) with eagle_netlist.json.
Nets are compared by their pad sets, so auto-named nets still match; the
names are reported separately."""
import sys, json, re
from collections import defaultdict
net_path,eagle_path=sys.argv[1],sys.argv[2]
txt=open(net_path,encoding='utf-8',errors='replace').read()
alt={}
for block in re.findall(r'^\($(.*?)^\)$',txt,re.S|re.M):
    lines=[l.strip() for l in block.strip().splitlines() if l.strip()]
    name,pads=lines[0],lines[1:]
    # the importer joins EAGLE pins that own several pads into one pin 'A,B'
    exp=set()
    for pd in pads:
        part,_,des=pd.partition('-')
        ds=des.split(',')
        import re as _re
        pre=_re.match(r'[A-Za-z]+',ds[0])
        for d in ds:
            # 'G1,3' means pads G1 and G3: the importer drops the repeated prefix
            if pre and not _re.match(r'[A-Za-z]',d): d=pre.group(0)+d
            exp.add(f'{part}-{d}')
    alt[name]=exp
comps=re.findall(r'^\[\s*\n(\S+)',txt,re.M)
eag={n:set(v) for n,v in json.load(open(eagle_path)).items()}
print(f'Altium: {len(comps)} components, {len(alt)} nets, {sum(len(v) for v in alt.values())} pads')
print(f'EAGLE : {len(eag)} nets, {sum(len(v) for v in eag.values())} pads')
# pad -> net maps
def padmap(d):
    m={}
    for n,ps in d.items():
        for p in ps: m[p]=n
    return m
am,em=padmap(alt),padmap(eag)
only_a=sorted(set(am)-set(em)); only_e=sorted(set(em)-set(am))
print('pads only in Altium:',len(only_a),only_a[:15])
print('pads only in EAGLE :',len(only_e),only_e[:15])
# connectivity: for each EAGLE net, the Altium net(s) its pads land in
split=[]; merged=defaultdict(set); renamed=[]
for n,ps in eag.items():
    targets=defaultdict(set)
    for p in ps:
        if p in am: targets[am[p]].add(p)
    if len(targets)>1: split.append((n,{t:sorted(v) for t,v in targets.items()}))
    for t in targets: merged[t].add(n)
    if len(targets)==1:
        t=next(iter(targets))
        if t!=n: renamed.append((n,t))
        extra=alt[t]-ps
        if extra: print(f'  Altium net {t} has extra pads vs EAGLE {n}: {sorted(extra)[:10]}')
print('EAGLE nets split across several Altium nets:',len(split))
for s in split[:20]: print('   ',s)
mg={t:sorted(v) for t,v in merged.items() if len(v)>1}
print('Altium nets that merge several EAGLE nets:',len(mg))
for t,v in list(mg.items())[:20]: print('   ',t,v)
print('nets identical in connectivity but renamed:',len(renamed))
for r in renamed[:40]: print('   ',r)
ok = not split and not mg and not only_a and not only_e
print('CONNECTIVITY MATCH' if ok else 'CONNECTIVITY DIFFERS')
