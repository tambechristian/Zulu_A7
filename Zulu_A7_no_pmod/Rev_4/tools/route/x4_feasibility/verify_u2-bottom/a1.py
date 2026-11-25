import json,sys,math,copy,collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0,T)
import body_check as bc
SRC='C:/Users/tambe/AppData/Local/Temp/claude/604b57bd2ceda17d/52f614a9-b2f5-42ff-ae9c-6f659acff616/scratchpad/feas/u2-bottom/'
B=json.load(open(T+'/route/bodies/base.json')); D=json.load(open(T+'/route/bodies/comps.json'))
M=json.load(open(SRC+'model_u2bot.json'))
C={c['ref']:c for c in D['comps']}
W,H=60.96,25.4
# 1. my own U2 transform: mirror x about pad-extent centre, then rotate +90 CCW, centre (54.025,12.275)
U=[p for p in B['pads'] if p['ref']=='U2']
e=bc.ext([(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2) for p in U])
ux,uy=(e[0]+e[2])/2,(e[1]+e[3])/2
print('U2 top pad ext',[round(v,3) for v in e],'centre',ux,uy, 'pad sizes',collections.Counter((p['w'],p['h']) for p in U))
mine={}
for p in U:
    x,y=-(p['x']-ux),p['y']-uy; w,h=p['w'],p['h']
    x,y,w,h=-y,x,h,w
    mine[p['pad']]=(54.025+x,12.275+y,w,h,p['net'])
theirs={p['pad']:(p['x'],p['y'],p['w'],p['h'],p['net']) for p in M['pads'] if p['ref']=='U2'}
dev=max(max(abs(mine[k][i]-theirs[k][i]) for i in range(4)) for k in mine)
print('max deviation my U2 pads vs theirs',dev, 'nets equal',all(mine[k][4]==theirs[k][4] for k in mine))
for k in ('1','2','3','6','7','8','17','24','38','43','49','64'): print(' pin',k,[round(v,3) for v in mine[k][:2]],mine[k][4])
e2=bc.ext([(x-w/2,y-h/2,x+w/2,y+h/2) for x,y,w,h,n in mine.values()]); print('U2 bottom pad ext',[round(v,3) for v in e2],'edge margins',round(e2[0],3),round(e2[1],3),round(W-e2[2],3),round(H-e2[3],3))
# 2. which refs moved / changed between base and model
bp=collections.defaultdict(list); mp=collections.defaultdict(list)
for p in B['pads']: bp[p['ref']].append(p)
for p in M['pads']: mp[p['ref']].append(p)
moved=[r for r in bp if r in mp and sorted((q['x'],q['y']) for q in bp[r])!=sorted((q['x'],q['y']) for q in mp[r])]
print('refs whose pads changed:',moved, 'missing:',[r for r in bp if r not in mp],'new:',[r for r in mp if r not in bp])
for r in moved:
    if r in('U2','X4'):continue
    b=bp[r];m=mp[r]
    print(' ',r,C[r]['layer'],C[r]['pattern'],[(q['pad'],q['net'],q['x'],q['y'],q['w'],q['h']) for q in m],'orient same',[(q['w'],q['h']) for q in b]==[(q['w'],q['h']) for q in m])
json.dump(mine,open('u2_mine.json','w'))
