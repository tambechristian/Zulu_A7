import json,sys,math,collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0,T)
import route_conn as RC
SRC='C:/Users/tambe/AppData/Local/Temp/claude/604b57bd2ceda17d/52f614a9-b2f5-42ff-ae9c-6f659acff616/scratchpad/feas/u2-bottom/'
B=json.load(open(T+'/route/bodies/base.json')); M=json.load(open(SRC+'model_u2bot.json'))
ob=RC.open_count(RC.islands(B)); om=RC.open_count(RC.islands(M))
print('base open',sum(ob.values()),ob)
print('model open',sum(om.values()))
print(sorted(om.items(),key=lambda kv:-kv[1]))
def key(t): return (t['net'],t['layer'],round(t['x1'],4),round(t['y1'],4),round(t['x2'],4),round(t['y2'],4))
km=collections.Counter(key(t) for t in M['tracks'])
rip=collections.defaultdict(float); rv=collections.Counter(); rl=collections.defaultdict(lambda:collections.defaultdict(float))
for t in B['tracks']:
    k=key(t)
    if km[k]>0: km[k]-=1; continue
    L=math.hypot(t['x2']-t['x1'],t['y2']-t['y1']); rip[t['net']]+=L; rl[t['net']][t['layer']]+=L
vm=collections.Counter((v['net'],round(v['x'],4),round(v['y'],4),tuple(v['span'])) for v in M['vias'])
spans=collections.Counter()
for v in B['vias']:
    k=(v['net'],round(v['x'],4),round(v['y'],4),tuple(v['span']))
    if vm[k]>0: vm[k]-=1; continue
    rv[v['net']]+=1; spans[(v['span'][0],v['span'][-1])]+=1
print('ripped track %.1f mm, vias %d, nets %d'%(sum(rip.values()),sum(rv.values()),len(set(rip)|set(rv))))
print('via spans ripped',spans)
for n in sorted(set(rip)|set(rv),key=lambda n:-rip[n]): print('  %-16s %6.1f mm %3d vias %s'%(n,rip[n],rv[n],{k[:3]:round(v,1) for k,v in rl[n].items()}))
