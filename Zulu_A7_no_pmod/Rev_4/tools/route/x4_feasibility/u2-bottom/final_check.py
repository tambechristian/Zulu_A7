import json,sys,copy
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0,T)
import body_check as bc
M=json.load(open('model_u2bot.json')); D=copy.deepcopy(json.load(open(T+'/route/bodies/comps.json')))
for c in D['comps']:
    if c['ref']=='U2': c['layer']='BOTTOM'
D['mech'].pop('X4')
P=bc.build(M,D)
# add S2B body on Top
P['Top']['X4']['body']=[(26.53,0.5,34.43,8.1)]; P['Top']['X4']['bodyt']=[(26.43,0.4,34.53,8.2)]
refs={'U2','X4','C110','C111','C114','C115','C119','C121','C122','C123','C91','C95','R25','R90','R91'}
r=bc.check(P,refs,0.10)
print('body_check on moved parts (gap 0.10):',r if r else 'CLEAN')
print('baseline full-board findings now:',len(bc.check(P,None,0.10)))
# pad-pad min gaps for moved parts on their side
import itertools
def padgap(ref):
    s='Bottom' if ref!='X4' else 'Top'
    mn=(9,None)
    for o,v in P[s].items():
        if o.split('[')[0]==ref: continue
        for a,_ in P[s][ref]['pads']:
            for b,p in v['pads']:
                g=bc.gap(a,b)
                if g<mn[0]: mn=(round(g,3),o+'-'+p['pad'])
    return mn
for ref in sorted(refs): print(ref,'min pad-pad gap',padgap(ref))
