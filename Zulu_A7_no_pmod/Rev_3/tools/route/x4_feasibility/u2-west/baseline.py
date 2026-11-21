import geo, time
M,D=geo.build({},s2b=None)
t=time.time()
f=geo.body_findings(M,D,None)
print('baseline body findings (whole board):',len(f), time.time()-t)
for r in sorted(set(f)): print(r)
# S2B alone at its slot, with U2 still in place
for cx in (29.28,30.48,31.68):
    M,D=geo.build({},s2b=(cx,4.9))
    print(cx,'S2B pads:',geo.pad_checks(M,{'X4'}))
    fb=geo.body_findings(M,D,{'X4'})
    print(cx,'S2B body:',sorted(set(fb))[:12])
