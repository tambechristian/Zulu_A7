from rip import *
from spots import fast_spots
import sys
MOVED=['X1','X4','U2','C155','C142','C145','R1']
def run(place_map, out='model_ripped.json', search=False):
    M,D=base_scenario()
    old={p['ref']+'.'+p['pad']:p for p in M0['pads'] if p['ref'] in MOVED}
    for ref,(x,y,rot,side) in place_map.items():
        if side=='BOTTOM':
            for c in D['comps']:
                if c['ref']==ref: c['layer']='BOTTOM'
            for p in M['pads']:
                if p['ref']==ref: p['layers']=['Bottom Layer']
        place(M,D,ref,x,y,rot)
    new=[p for p in M['pads'] if p['ref'] in MOVED]
    oldp=[old[k] for k in old]
    # X4 old pads (B2B) are replaced: rip their copper as attached
    Mr,rt,rv,why=build_ripped(M,MOVED,new,oldp)
    return M,D,Mr,rt,rv,why
if __name__=='__main__':
    park={'C142':(250,250,90,'TOP'),'C145':(250,240,90,'TOP'),'R1':(250,230,0,'BOTTOM'),'C155':(26.0,20.6,180,'TOP')}
    M,D,Mr,rt,rv,why=run(park)
    for r in ('C142','C145','R1'): pass
    # search spots on the ripped model
    for ref,reg,side in (('C142',(44,2,60,24,56.6,6.7),'TOP'),('C145',(44,2,60,24,56.6,10.0),'TOP'),('R1',(44,2,60,24,58.2,3.7),'BOTTOM')):
        o=fast_spots(Mr,D,ref,reg,step=0.25)
        print(ref,side,'zero-conflict',sum(1 for z in o if z[0]==0)); [print('  ',z) for z in o[:6]]
    # also bottom for the caps
    D2=copy.deepcopy(D); M2=copy.deepcopy(Mr)
    for c in D2['comps']:
        if c['ref'] in ('C142','C145'): c['layer']='BOTTOM'
    for p in M2['pads']:
        if p['ref'] in ('C142','C145'): p['layers']=['Bottom Layer']
    o=fast_spots(M2,D2,'C142',(44,2,60,24,56.6,6.7),step=0.25)
    print('caps on BOTTOM zero-conflict',sum(1 for z in o if z[0]==0)); [print('  ',z) for z in o[:10]]
