from spots import *
M,D=base_scenario()
for r in ('C142','C145','C155','R1'): move(M,r,200,200)
# whole Top
for ref in ('C142',):
    o=fast_spots(M,D,ref,(1,1,60,24.5,56.6,6.7),step=0.25)
    print('TOP',ref,'zero:',sum(1 for z in o if z[0]==0)); [print('  ',x) for x in o[:10]]
# Bottom: flip to bottom side
for c in D['comps']:
    if c['ref'] in ('C142','C145'): c['layer']='BOTTOM'
for p in M['pads']:
    if p['ref'] in ('C142','C145'): p['layers']=['Bottom Layer']
o=fast_spots(M,D,'C142',(40,2,60,24,56.6,6.7),step=0.25)
print('BOTTOM zero:',sum(1 for z in o if z[0]==0)); [print('  ',x) for x in o[:12]]
json.dump(o[:60],open('spots_bot.json','w'))
