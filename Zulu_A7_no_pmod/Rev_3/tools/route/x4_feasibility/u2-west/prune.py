"""Lower bound of the own-net rip: remove the moved pads, prune copper that becomes dangling."""
import geo, impact, json, math, collections
RC=geo.RC
pl=json.load(open('final_placement.json'))['placements']
moved=set(pl)|{'X4'}
P0,T,V=geo.M0['pads'],geo.M0['tracks'],geo.M0['vias']
own=sorted(set(p['net'] for p in P0 if p['ref'] in moved and p['net'])-impact.PLANES)
isl=None
tot_keep=tot_rip=0; rows=[]; RIPT=set(); RIPV=set()
for net in own:
    pads=[i for i,p in enumerate(P0) if p['net']==net]; tr=[i for i,t in enumerate(T) if t['net']==net]; vi=[j for j,v in enumerate(V) if v['net']==net]
    nodes=[('p',i) for i in pads]+[('t',i) for i in tr]+[('v',j) for j in vi]
    def lay(n):
        k,i=n
        return set(P0[i]['layers'] or geo.BC.STACK) if k=='p' else {T[i]['layer']} if k=='t' else set(V[i]['span'])
    def touch(a,b):
        if not lay(a)&lay(b): return False
        (ka,ia),(kb,ib)=sorted([a,b])
        if ka=='p' and kb=='p': return False
        if ka=='p' and kb=='t': t=T[ib]; return RC.pad_seg(P0[ia],(t['x1'],t['y1'],t['x2'],t['y2']))<=t['w']/2+1e-4
        if ka=='p' and kb=='v': return RC.pad_point(P0[ia],V[ib]['x'],V[ib]['y'])<=V[ib]['size']/2+1e-4
        if ka=='t' and kb=='t': a_,b_=T[ia],T[ib]; return RC.seg_seg((a_['x1'],a_['y1'],a_['x2'],a_['y2']),(b_['x1'],b_['y1'],b_['x2'],b_['y2']))<=(a_['w']+b_['w'])/2+1e-4
        if ka=='t' and kb=='v': t,v=T[ia],V[ib]; return RC.seg_dist(t['x1'],t['y1'],t['x2'],t['y2'],v['x'],v['y'])<=(t['w']+v['size'])/2+1e-4
        v1,v2=V[ia],V[ib]; return math.hypot(v1['x']-v2['x'],v1['y']-v2['y'])<=(v1['size']+v2['size'])/2+1e-4
    adj=collections.defaultdict(set)
    for a in range(len(nodes)):
        for b in range(a+1,len(nodes)):
            if touch(nodes[a],nodes[b]): adj[a].add(b); adj[b].add(a)
    alive=set(range(len(nodes)))
    movedp={a for a,n in enumerate(nodes) if n[0]=='p' and P0[n[1]]['ref'] in moved}
    alive-=movedp
    import heapq
    def w(a):
        k,i=nodes[a]
        return impact.tlen(T[i]) if k=='t' else 0.01
    rem=[a for a in alive if nodes[a][0]=='p']
    keepset=set()
    if len(rem)>=2:
        src=rem[0]; dist={src:0}; prev={}; pq=[(0,src)]
        while pq:
            d,u=heapq.heappop(pq)
            if d>dist.get(u,1e9): continue
            for x in adj[u]:
                if x not in alive: continue
                if nodes[x][0]=='p' and x not in rem: continue
                nd=d+w(x)
                if nd<dist.get(x,1e9): dist[x]=nd; prev[x]=u; heapq.heappush(pq,(nd,x))
        for r in rem[1:]:
            u=r
            while u in prev: keepset.add(u); u=prev[u]
            keepset.add(u)
    alive={a for a in alive if a in keepset or nodes[a][0]=='p'}
    RIPT.update(nodes[a][1] for a in range(len(nodes)) if nodes[a][0]=='t' and a not in alive); RIPV.update(nodes[a][1] for a in range(len(nodes)) if nodes[a][0]=='v' and a not in alive)
    rip=sum(impact.tlen(T[nodes[a][1]]) for a in range(len(nodes)) if nodes[a][0]=='t' and a not in alive)
    keep=sum(impact.tlen(T[nodes[a][1]]) for a in alive if nodes[a][0]=='t')
    rv=sum(1 for a in range(len(nodes)) if nodes[a][0]=='v' and a not in alive)
    tot_keep+=keep; tot_rip+=rip; rows.append((net,round(rip,1),round(keep,1),rv))
rows.sort(key=lambda r:-r[1])
for r in rows: print(r)
print('own nets: min rip %.1f mm, kept %.1f mm'%(tot_rip,tot_keep))

json.dump({'t':sorted(RIPT),'v':sorted(RIPV)},open('minrip_own.json','w'))
