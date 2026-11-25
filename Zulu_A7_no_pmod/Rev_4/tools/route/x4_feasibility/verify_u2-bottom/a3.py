import json,sys,math,collections
T='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
SRC='C:/Users/tambe/AppData/Local/Temp/claude/604b57bd2ceda17d/52f614a9-b2f5-42ff-ae9c-6f659acff616/scratchpad/feas/u2-bottom/'
STACK=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
def segpt(x,y,t):
    ax,ay,bx,by=t['x1'],t['y1'],t['x2'],t['y2']; dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
    u=0 if L==0 else max(0,min(1,((x-ax)*dx+(y-ay)*dy)/L)); return math.hypot(ax+u*dx-x,ay+u*dy-y)
def seg_rect(t,r):
    # exact: min over segment of distance to rect = min( corners->segment, segment endpoints->rect, intersection)
    ds=[segpt(cx,cy,t) for cx in (r[0],r[2]) for cy in (r[1],r[3])]
    for x,y in ((t['x1'],t['y1']),(t['x2'],t['y2'])):
        dx=max(r[0]-x,0,x-r[2]); dy=max(r[1]-y,0,y-r[3]); ds.append(math.hypot(dx,dy))
    # segment crossing the rect: sample check
    n=20
    for i in range(n+1):
        x=t['x1']+(t['x2']-t['x1'])*i/n; y=t['y1']+(t['y2']-t['y1'])*i/n
        if r[0]<=x<=r[2] and r[1]<=y<=r[3]: ds.append(0)
    return min(ds)-t['w']/2
def audit(M,refs,label):
    bad=collections.defaultdict(list)
    for p in M['pads']:
        if p['ref'] not in refs: continue
        L=p['layers'] or STACK
        r=(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2)
        for t in M['tracks']:
            if t['layer'] not in L or t['net']==p['net'] : continue
            if max(t['x1'],t['x2'])<r[0]-1 or min(t['x1'],t['x2'])>r[2]+1 or max(t['y1'],t['y2'])<r[1]-1 or min(t['y1'],t['y2'])>r[3]+1: continue
            g=seg_rect(t,r)
            if g<0.09: bad[(p['ref'],p['pad'],p['net'])].append(('trk',t['net'],t['layer'],round(g,3)))
        for v in M['vias']:
            if v['net']==p['net'] or not set(v['span'])&set(L): continue
            dx=max(r[0]-v['x'],0,v['x']-r[2]); dy=max(r[1]-v['y'],0,v['y']-r[3]); g=math.hypot(dx,dy)-v['size']/2
            if g<0.09: bad[(p['ref'],p['pad'],p['net'])].append(('via',v['net'],v['span'][0],v['span'][-1],round(g,3)))
    print(label,'pads with other-net copper < 0.09:',len(bad))
    for k,v in list(bad.items())[:30]: print('  ',k,v[:4])
B=json.load(open(T+'/route/bodies/base.json')); M=json.load(open(SRC+'model_u2bot.json'))
MOV=['U2','R91','R90','R25','C123','C122','C121','C119','C115','C114','C111','C110','C95','C91','X4']
audit(B,MOV,'BASE (sanity, released board)')
audit(M,MOV,'U2-bottom model')
# S2B mounting pads net '' : copper of ANY net under them
