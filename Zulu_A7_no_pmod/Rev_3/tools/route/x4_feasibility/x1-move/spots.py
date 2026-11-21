from scenario import *
import numpy as np, time
def fast_spots(M,D,ref,reg,rots=(0,90),step=0.25,clr=0.10):
    parts=BC.build(M,D)
    c=[c for c in D['comps'] if c['ref']==ref][0]
    side='Top' if c['layer']=='TOP' else 'Bottom'
    others={k:v for k,v in parts[side].items() if k.split('[')[0]!=ref}
    opads=[p for p in M['pads'] if p['ref']!=ref and (('Top Layer' if side=='Top' else 'Bottom Layer') in (p['layers'] or STACK))]
    lay='Top Layer' if side=='Top' else 'Bottom Layer'
    trk=[t for t in M['tracks'] if t['layer']==lay]
    vias=[v for v in M['vias'] if lay in v['span']]
    out=[]
    base=pads_of(M,ref)
    for rot in rots:
        for x in np.arange(reg[0],reg[2]+1e-9,step):
            for y in np.arange(reg[1],reg[3]+1e-9,step):
                ps=[dict(p) for p in base]; Dt={'comps':[dict(c)],'mech':{}}
                Mt={'pads':ps}
                place(Mt,Dt,ref,x,y,rot)
                bx=[pad_box(p) for p in ps]
                if any(min(b[0],b[1],W-b[2],H-b[3])<0.3 for b in bx): continue
                L,Wd,_,_=BC.BODY[c['pattern']]
                if round(Dt['comps'][0]['rot'])%180==90: L,Wd=Wd,L
                body=(x-L/2,y-Wd/2,x+L/2,y+Wd/2)
                bad=False
                for k,P in others.items():
                    for b2 in P['body']:
                        if BC.gap(body,b2)<0.10: bad=True;break
                    if bad: break
                    for pb,_ in P['pads']:
                        if BC.gap(body,pb)<0.10: bad=True;break
                    if bad: break
                if bad: continue
                for q in opads:
                    if abs(q['x']-x)>4 or abs(q['y']-y)>4: continue
                    qb=pad_box(q)
                    if any(BC.gap(b,qb)<0.15 for b in bx) or BC.gap(body,qb)<0.10: bad=True;break
                if bad: continue
                nets=set(); n=0
                for p,b in zip(ps,bx):
                    for t in trk:
                        if max(t['x1'],t['x2'])<b[0]-1 or min(t['x1'],t['x2'])>b[2]+1 or max(t['y1'],t['y2'])<b[1]-1 or min(t['y1'],t['y2'])>b[3]+1: continue
                        if t['net']==p['net'] and p['net']: continue
                        if seg_box_dist(t['x1'],t['y1'],t['x2'],t['y2'],b)-t['w']/2<clr: n+=1; nets.add(t['net'])
                    for v in vias:
                        if v['net']==p['net'] and p['net']: continue
                        dx=max(b[0]-v['x'],0,v['x']-b[2]); dy=max(b[1]-v['y'],0,v['y']-b[3])
                        if math.hypot(dx,dy)-v['size']/2<clr: n+=1; nets.add(v['net'])
                out.append((n,round(math.hypot(x-reg[4],y-reg[5]),2),round(x,3),round(y,3),rot,sorted(nets)))
    out.sort(key=lambda t:(t[0],t[1])); return out
if __name__=='__main__':
    M,D=base_scenario()
    # take displaced parts out of the way first (far away), so they don't block each other
    for r in ('C142','C145','C155','R1'):
        move(M,r,200,200)
    jobs={'C142':(44,2,58,13,56.6,6.7),'C145':(44,2,58,14,56.6,10.0),'C155':(23.5,19.5,28,23.2,26.0,20.25),'R1':(44,2,58.5,14,58.2,3.7)}
    res={}
    for ref,reg in jobs.items():
        t=time.time()
        o=fast_spots(M,D,ref,reg,step=0.25 if ref!='C155' else 0.1)
        print(ref,'%.0fs'%(time.time()-t),len(o),'zero-conflict:',sum(1 for z in o if z[0]==0)); [print('  ',x) for x in o[:8]]
        res[ref]=o[:40]
    json.dump(res,open('spots.json','w'))
