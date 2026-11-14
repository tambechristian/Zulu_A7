import search as S, collections
net='D14'; runL,segs,used=S.run_poly(net)
import json
pf=json.load(open('prefilter_D14.json'))
sites={(round(x,4),round(y,4)) for sd,x,y in pf['legal_sites'] if sd=='Bottom'}
cnt=collections.Counter(); ex=[]
for (x,y) in sites:
    for rot,(dx,dy) in S.ROT.items():
        p2=(round(x+dx,4),round(y+dy,4))
        if p2 not in sites: continue
        c=S.build_candidate(net,'Bottom',rot,(x,y),p2,segs,used,runL)
        if c is None: cnt['order']+=1; continue
        if c['conn1']>S.BAND or c['conn2']>S.BAND: cnt['band']+=1; continue
        wc,fw,news=S.candidate_exact(c,runL)
        if wc[0]<0: cnt['cl:'+wc[1].split(' vs ')[1][:40]]+=1
        if fw[0]<0: cnt['fam:'+fw[1][:60]]+=1
print(cnt.most_common(30))
xs=sorted(sites); print(xs[:5], xs[-5:])
import collections
print(collections.Counter((round(x),round(y,1)) for x,y in sites).most_common(40))
