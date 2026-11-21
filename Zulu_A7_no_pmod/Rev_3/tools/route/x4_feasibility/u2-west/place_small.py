import column2 as C, json, math
targets=[('LD0',30.4,10.6),('LD1',30.4,12.4),('LD2',30.4,14.0),('LD3',30.4,15.6),('LD4',30.4,17.45),
         ('BTN',35.0,11.5),('C155',29.2,19.8),('C158',17.8,8.1),('C159',23.9,6.6)]
eP,eB,eBt=[],[],[]; out={}
for r,tx,ty in targets:
    found=None
    for rr in range(0,80):
        rad=rr*0.05
        for a in ([0] if rr==0 else range(32)):
            x=round(tx+rad*math.cos(a*math.pi/16),3); y=round(ty+rad*math.sin(a*math.pi/16),3)
            if C.fits(r,x,y,eP,eB,eBt): found=(x,y); break
        if found: break
    print(r,(tx,ty),'->',found)
    if found:
        out[r]=found; P,B,Bt=C.boxes(r,*found); eP.append(P); eB.append(B); eBt.append(Bt)
json.dump(out,open('small_fast.json','w'))
