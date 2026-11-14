import search as S, sys
net='D13'; runL,segs,used=S.run_poly(net)
for p1,p2,rot in [((39.875,14.1),(39.875,13.5),270),((39.9,14.1),(39.9,13.5),270),((39.875,14.075),(39.875,13.475),270)]:
    for side in ('Bottom',):
        ok1,m1=S.site_eval(net,side,runL,*p1); ok2,m2=S.site_eval(net,side,runL,*p2)
        c=S.build_candidate(net,side,rot,p1,p2,segs,used,runL)
        print(p1,p2,ok1,ok2, None if c is None else (c['conn1'],c['conn2']))
        if c:
            wc,fw,news=S.candidate_exact(c,runL); print('  cand',wc,'fam',fw)
        print('  ',{k:v for k,v in m1.items() if v[0]<0.02},{k:v for k,v in m2.items() if v[0]<0.02})
