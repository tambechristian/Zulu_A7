import json,sys,math,collections
sys.path.insert(0,'.')
from copper import *
cx,cy,rot=54.025,12.275,0
rs,body,_=u2geom(cx,cy,rot)
print('U2 bottom pad extent',[round(v,3) for v in bc.ext([r for r,_,_ in rs])],'body',body)
# vias under pads: classify by whether the via has bottom-layer copper or bottom pad attached
def touches_bottom(v):
    for t in BT:
        if t['net']!=v['net']: continue
        for x,y in ((t['x1'],t['y1']),(t['x2'],t['y2'])):
            if abs(x-v['x'])<0.01 and abs(y-v['y'])<0.01: return 'trk'
    for p in M['pads']:
        if p['net']==v['net'] and (p['layers'] is None or 'Bottom Layer' in p['layers']) and abs(p['x']-v['x'])<p['w']/2+0.05 and abs(p['y']-v['y'])<p['h']/2+0.05: return 'pad:'+p['ref']
    return ''
c=collections.Counter()
for v in BV:
    if any(pt_rect(v['x'],v['y'],r)-v['size']/2<0.09 for r,_,_ in rs):
        k=('through' if len(v['span'])==6 else 'L5-Bot', touches_bottom(v) or 'no-bottom-copper')
        c[(k[0],k[1].split(':')[0])]+=1
        print('via',v['net'],v['x'],v['y'],v['span'][0],'->',v['span'][-1],k[1])
print(c)
# small parts displaced: nets
for r in ['C110','C111','C114','C115','C119','C121','C122','C123','C91','C95','R25','R90','R91']:
    print(r,C[r]['pattern'],[(p['pad'],p['net']) for p in M['pads'] if p['ref']==r])
# U2 net copper
U2N={p['net'] for p in M['pads'] if p['ref']=='U2' and p['net'] and p['net'] not in('GND','VCC3V3')}
L=collections.defaultdict(float); NV=collections.Counter()
for t in M['tracks']:
    if t['net'] in U2N: L[t['net']]+=math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
for v in M['vias']:
    if v['net'] in U2N: NV[v['net']]+=1
print('U2 signal/rail nets copper:')
for n in sorted(L): print(' %-14s %6.1f mm %d vias'%(n,L[n],NV[n]))
print('total %.1f mm, %d vias'%(sum(L.values()),sum(NV.values())))
