import json, geo
exec(open('final.py').read().split("done={'U2'")[0])  # defs: try_place, foreign_hits, PENDING, OWN
done={'U2':(UX,UY,UROT)}
offs={'LD0':0.0,'LD1':2.09,'LD2':3.69,'LD3':5.29,'LD4':6.89}   # LD0 tall, then 1.6 pitch
sols=[]
for x in [round(32.0+0.05*i,2) for i in range(110)]:
  for y0 in [round(9.9+0.05*j,2) for j in range(60)]:
    pl=dict(done); pl.update({r:(x,y0+o,0) for r,o in offs.items()})
    if y0+6.89+0.45>20.3: continue
    M,D=geo.build(pl,s2b=(CX,CY))
    M['pads']=[p for p in M['pads'] if p['ref'] not in {'BTN','C155','C158','C159'}]
    refs=set(offs)
    if geo.body_findings(M,D,refs) or geo.pad_checks(M,refs) or any(foreign_hits(M,r) for r in refs): continue
    sols.append((x,y0)); break
print(len(sols), sols[:40])
json.dump(sols,open('led_columns.json','w'))
