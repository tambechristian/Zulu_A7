import geo, impact, json, collections
pl={k:tuple(v) for k,v in json.load(open('placement.json')).items()}
M,D=geo.build(pl,s2b=(30.48,4.9))
moved=set(pl)|{'X4'}
U=[p for p in M['pads'] if p['ref']=='U2']; e=geo.ext(U)
zones=[(e[0]-0.5,e[1]-0.5,e[2]+0.5,e[3]+0.5,'U2 fan-out ring')]
per,why,rt,rv=impact.impact(M,moved,zones)
tot,rows=impact.report(per,why)
print('ripped tracks %d, length %.1f mm, vias %d, nets %d'%(len(rt),tot,len(rv),len(rows)))
for r in rows: print(r)
# split: own-net vs foreign
own=set(p['net'] for p in geo.M0['pads'] if p['ref'] in moved and p['net'])
fl=sum(v[1] for n,v in per.items() if n not in own); fn=[n for n in per if n not in own]
print('own nets (signal, whole-net rip):',sorted(own-impact.PLANES))
print('foreign nets hit: %d, length %.1f mm:'%(len(fn),fl),sorted(fn))
print('SDRAM foreign:',sorted(n for n in fn if n in geo.SDRAM))
# what layers do ripped foreign tracks occupy
c=collections.Counter(geo.M0['tracks'][i]['layer'] for i in rt if geo.M0['tracks'][i]['net'] not in own)
print('foreign ripped by layer',c)
json.dump({'rip_tracks':sorted(rt),'rip_vias':sorted(rv)},open('rip.json','w'))
