import column2 as C, numpy as np, json
# rotate LED templates by 90 deg (CCW): (dx,dy,w,h) -> (-dy,dx,h,w); body swap
for r in ['LD0','LD1','LD2','LD3','LD4']:
    pads,(L,W,Lt,Wt)=C.tmpl[r]
    C.tmpl[r]=([(-dy,dx,h,w,n) for dx,dy,w,h,n in pads],(W,L,Wt,Lt))
def greedy_x(order, ys, x0, xmax, pitch):
    best=None
    for y in ys:
        eP,eB,eBt=[],[],[]; pos={}; x=x0
        for r in order:
            while x<xmax and not C.fits(r,x,y,eP,eB,eBt): x=round(x+0.05,3)
            if x>=xmax: break
            pos[r]=(x,y); P,B,Bt=C.boxes(r,x,y); eP.append(P); eB.append(B); eBt.append(Bt); x=round(x+pitch,3)
        if len(pos)==len(order):
            span=pos[order[-1]][0]-pos[order[0]][0]
            if best is None or span<best[0]: best=(round(span,2),y,pos)
    return best
res=[]
for y in [round(17.0+0.05*i,2) for i in range(60)]:
    b=greedy_x(['LD0','LD1','LD2','LD3','LD4'],[y],28.6,38.2,1.6)
    if b: res.append(b)
res.sort(key=lambda b:(b[0],-b[1]))
for b in res[:6]: print(b)
json.dump(res[:6],open('led_rows.json','w'))
