import geo, impact, json, sys, itertools, math
UX,UY,UROT=21.75,15.75,270.0
CX,CY=30.48,4.9
# relocated parts: ref -> (preferred x, y, drot)
SMALL0=json.loads(open('small_targets.json').read())
def try_place(base, ref, tx, ty, r, done):
    best=None
    for rr in range(0,60):
        rad=rr*0.05
        cands=[(tx,ty)] if rr==0 else [(tx+rad*math.cos(a*math.pi/16),ty+rad*math.sin(a*math.pi/16)) for a in range(32)]
        for x,y in cands:
            pl=dict(done); pl[ref]=(x,y,r)
            M,D=geo.build(pl,s2b=(CX,CY))
            M['pads']=[p for p in M['pads'] if p['ref'] not in PENDING-set(pl)]
            f=geo.body_findings(M,D,{ref})
            pc=geo.pad_checks(M,{ref})
            if not f and not pc and not foreign_hits(M,ref): return (round(x,3),round(y,3),r)
    return None
PENDING=set(SMALL0)
MOVED={'U2','X4'}|set(SMALL0)
OWN=set(p['net'] for p in geo.M0['pads'] if p['ref'] in MOVED and p['net'])-{'GND','VCC3V3'}
TT=[t for t in geo.M0['tracks'] if t['layer']=='Top Layer' and t['net'] not in OWN]
TV=[v for v in geo.M0['vias'] if 'Top Layer' in v['span'] and v['net'] not in OWN]
def foreign_hits(M,ref):
    for p in M['pads']:
        if p['ref']!=ref: continue
        for v in TV:
            if v['net']!=p['net'] and abs(v['x']-p['x'])<2 and abs(v['y']-p['y'])<2 and geo.RC.pad_point(p,v['x'],v['y'])<v['size']/2+geo.CLEAR: return True
        for t in TT:
            if t['net']!=p['net'] and min(abs(t['x1']-p['x']),abs(t['x2']-p['x']))<4 and min(abs(t['y1']-p['y']),abs(t['y2']-p['y']))<4 and geo.RC.pad_seg(p,(t['x1'],t['y1'],t['x2'],t['y2']))<t['w']/2+geo.CLEAR: return True
    return False
done={'U2':(UX,UY,UROT)}
for ref,(tx,ty,r) in SMALL0.items():
    res=try_place(None,ref,tx,ty,r,done)
    print(ref,'target',(tx,ty,r),'->',res); sys.stdout.flush()
    if res: done[ref]=res
json.dump(done,open('placement.json','w'),indent=1)
M,D=geo.build(done,s2b=(CX,CY))
moved=set(done)|{'X4'}
f=geo.body_findings(M,D,moved); pc=geo.pad_checks(M,moved)
print('FINAL body findings involving moved parts:',sorted(set(f)))
print('FINAL pad findings:',pc)
allf=geo.body_findings(M,D,None)
base=geo.body_findings(*geo.build({},s2b=None),None)
key=lambda r:(r[0],r[1],r[2],r[3])
print('whole-board body findings: base %d -> new %d'%(len(set(map(key,base))),len(set(map(key,allf)))))
print('new-only:',sorted(set(map(key,allf))-set(map(key,base))))
print('gone:',sorted(set(map(key,base))-set(map(key,allf))))
json.dump({'pads':[p for p in M['pads'] if p['ref'] in moved]},open('moved_pads.json','w'),indent=0)
