import json,sys,math,copy,collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0,T)
import body_check as bc
SRC='C:/Users/tambe/AppData/Local/Temp/claude/604b57bd2ceda17d/52f614a9-b2f5-42ff-ae9c-6f659acff616/scratchpad/feas/u2-bottom/'
B=json.load(open(T+'/route/bodies/base.json')); D=json.load(open(T+'/route/bodies/comps.json'))
M=json.load(open(SRC+'model_u2bot.json'))
D2=copy.deepcopy(D)
for c in D2['comps']:
    if c['ref']=='U2': c['layer']='BOTTOM'
D2['mech'].pop('X4')
MOV=['U2','R91','R90','R25','C123','C122','C121','C119','C115','C114','C111','C110','C95','C91']
P0=bc.build(B,D); P1=bc.build(M,D2)
P1['Top']['X4']['body']=[(26.53,0.5,34.43,8.1)]; P1['Top']['X4']['bodyt']=[(26.43,0.4,34.53,8.2)]
f0=bc.check(P0,None,0.10); f1=bc.check(P1,None,0.10)
key=lambda f:(f[0],f[1],f[2],f[3],f[4])
s0=set(map(key,f0)); s1=set(map(key,f1))
print('findings base',len(f0),'model',len(f1))
print('NEW findings:',[f for f in f1 if key(f) not in s0])
print('findings removed:',sorted(set(s0)-set(s1)))
# also body_check with the standard 0.10 for moved refs only:
print('moved refs check:',bc.check(P1,set(MOV+['X4']),0.10))
# pad-pad gaps all pairs on each side involving moved parts
def pr(p): return (p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2)
def onside(p,s):
    L=p['layers'] or bc.STACK
    return ('Top Layer' if s=='Top' else 'Bottom Layer') in L
for s in ('Top','Bottom'):
    pads=[p for p in M['pads'] if onside(p,s)]
    for r in MOV+['X4']:
        mine=[p for p in pads if p['ref']==r]
        if not mine: continue
        best=(9,None)
        for a in mine:
            for b in pads:
                if b['ref']==r: continue
                g=bc.gap(pr(a),pr(b))
                if g<best[0]: best=(round(g,3),(a['pad'],a['net'],b['ref'],b['pad'],b['net']))
        if best[0]<0.3: print(s,r,'min pad gap',best)
# X2 housings vs moved parts
for k,v in P1['Bottom'].items():
    if k.startswith('X2['):
        for r in MOV:
            if r in P1['Bottom']:
                for pb,p in P1['Bottom'][r]['pads']:
                    g=bc.gap(v['body'][0],pb)
                    if g<0.4: print('X2 housing',k,'vs',r,p['pad'],round(g,3))
# edge
for p in M['pads']:
    b=pr(p); m=min(b[0],b[1],60.96-b[2],25.4-b[3])
    if p['ref'] in MOV+['X4'] and m<0.5: print('edge margin',p['ref'],p['pad'],round(m,3))
