"""Routing impact of a placement: which copper must be ripped."""
import geo, math, collections, json, sys
RC=geo.RC
PLANES={'GND','VCC3V3'}
def tlen(t): return math.hypot(t['x2']-t['x1'],t['y2']-t['y1'])
def on_top_v(v): return 'Top Layer' in v['span']
def on_top_p(p): return p['layers'] is None or 'Top Layer' in p['layers']
def impact(M, moved_refs, extra_zones=()):
    """M: placed model (pads moved). moved_refs: refs whose pads moved/replaced. extra_zones: [(x0,y0,x1,y1,label)] Top keepouts."""
    old={(p['ref'],p['pad']):p for p in geo.M0['pads'] if p['ref'] in moved_refs}
    new=[p for p in M['pads'] if p['ref'] in moved_refs]
    T,V=geo.M0['tracks'],geo.M0['vias']
    rip_t=set(); rip_v=set(); why=collections.defaultdict(set)
    # 1. nets of moved pads (old and new pins)
    nets=set(p['net'] for p in old.values() if p['net'])|set(p['net'] for p in new if p['net'])
    sig=nets-PLANES
    for i,t in enumerate(T):
        if t['net'] in sig: rip_t.add(i); why[t['net']].add('own net')
    for i,v in enumerate(V):
        if v['net'] in sig: rip_v.add(i)
    # plane nets: BFS over Top copper of the same net from each moved pad; stop at vias (ripped) and at other parts' pads
    stay=[p for p in geo.M0['pads'] if p['ref'] not in moved_refs and on_top_p(p)]
    for (r,pn),p in old.items():
        if p['net'] not in PLANES or not on_top_p(p): continue
        net=p['net']
        cand=[i for i,t in enumerate(T) if t['net']==net and t['layer']=='Top Layer']
        frontier=[('p',p)]; seen=set()
        while frontier:
            k,o=frontier.pop()
            for i in cand:
                if i in seen: continue
                t=T[i]; seg=(t['x1'],t['y1'],t['x2'],t['y2'])
                if k=='p': hit=RC.pad_seg(o,seg)<=t['w']/2+1e-4
                else: hit=RC.seg_seg(seg,(o['x1'],o['y1'],o['x2'],o['y2']))<=(t['w']+o['w'])/2+1e-4
                if not hit: continue
                if any(RC.pad_seg(q,seg)<=t['w']/2+1e-4 for q in stay if q['net']==net and abs(q['x']-t['x1'])<3 and abs(q['y']-t['y1'])<3): continue
                seen.add(i); rip_t.add(i); why[net].add('stub at %s.%s'%(r,pn))
                atvia=[j for j,v in enumerate(V) if v['net']==net and on_top_v(v) and RC.seg_dist(*seg,v['x'],v['y'])<=v['size']/2+1e-4]
                for j in atvia: rip_v.add(j)
                if not atvia: frontier.append(('t',t))
            for j,v in enumerate(V):
                if k=='p' and v['net']==net and on_top_v(v) and RC.pad_point(o,v['x'],v['y'])<=v['size']/2: rip_v.add(j); why[net].add('via-in-pad %s.%s'%(r,pn))
    # 2. foreign copper vs new pads (Top), clearance 0.09
    foreign=collections.defaultdict(lambda:[0,0.0,0])
    for p in new:
        for i,t in enumerate(T):
            if t['layer']!='Top Layer' or i in rip_t or t['net']==p['net'] and p['net']: continue
            if abs((t['x1']+t['x2'])/2-p['x'])>8 or abs((t['y1']+t['y2'])/2-p['y'])>8: continue
            if RC.pad_seg(p,(t['x1'],t['y1'],t['x2'],t['y2']))<t['w']/2+geo.CLEAR:
                rip_t.add(i); why[t['net']].add('hits new pad %s.%s'%(p['ref'],p['pad']))
        for j,v in enumerate(V):
            if not on_top_v(v) or j in rip_v or (v['net']==p['net'] and p['net']): continue
            if RC.pad_point(p,v['x'],v['y'])<v['size']/2+geo.CLEAR:
                rip_v.add(j); why[v['net']].add('via hits new pad %s.%s'%(p['ref'],p['pad']))
    # 3. extra Top keepout zones (fan-out ring of the moved QFP etc)
    for x0,y0,x1,y1,lab in extra_zones:
        for i,t in enumerate(T):
            if t['layer']!='Top Layer' or i in rip_t: continue
            if max(t['x1'],t['x2'])+t['w']/2>x0 and min(t['x1'],t['x2'])-t['w']/2<x1 and max(t['y1'],t['y2'])+t['w']/2>y0 and min(t['y1'],t['y2'])-t['w']/2<y1:
                rip_t.add(i); why[t['net']].add('in zone '+lab)
        for j,v in enumerate(V):
            if not on_top_v(v) or j in rip_v: continue
            if x0<v['x']<x1 and y0<v['y']<y1: rip_v.add(j); why[v['net']].add('via in zone '+lab)
    per=collections.defaultdict(lambda:[0,0.0,0])
    for i in rip_t: per[T[i]['net']][0]+=1; per[T[i]['net']][1]+=tlen(T[i])
    for j in rip_v: per[V[j]['net']][2]+=1
    return per, why, rip_t, rip_v
def report(per, why):
    tot=sum(v[1] for v in per.values())
    rows=[]
    for n,(nt,L,nv) in sorted(per.items(),key=lambda kv:-kv[1][1]):
        tag=('SDRAM' if n in geo.SDRAM else 'USB-diff' if n.startswith('USB_D') else 'clock' if 'CLK' in n or n=='TCK' else 'plane' if n in PLANES else '')
        rows.append((n,nt,round(L,2),nv,tag,sorted(why[n])[:3]))
    return tot,rows
