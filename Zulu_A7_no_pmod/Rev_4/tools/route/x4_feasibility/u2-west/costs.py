import refine, geo, json
MOVED={'U2','BTN','LD0','LD1','LD2','LD3','LD4','C155','C158','C159','X4'}
OWN=set(p['net'] for p in geo.M0['pads'] if p['ref'] in MOVED and p['net'])-{'GND','VCC3V3'}
res=[]
for r in json.load(open('refine_30.48.json')):
    c=refine.cost(r[0],r[1])
    rv=[n for n in c['rip_vias'] if n not in OWN]; tr=[n for n in c['tracks_hit'] if n not in OWN]
    res.append((r[0],r[1],len(rv),len(tr),len(c['convert_vias']),r[5],sorted(rv),tr,sorted(c['convert_vias'])))
res.sort(key=lambda x:(x[2]*3+x[3],x[4],-x[5]))
for x in res[:8]: print(x)
json.dump(res,open('costs_30.48.json','w'))
