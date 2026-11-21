from scenario import *
import route_conn as RC
PLANE={'GND','VCC3V3'}
BIG={'GND','VCC3V3','VCC1V0','VCC1V8','VU'}   # local rip only
def touches_pad(p,o,kind):
    if kind=='t':
        if o['layer'] not in (p['layers'] or STACK): return False
        return RC.pad_seg(p,(o['x1'],o['y1'],o['x2'],o['y2']))<=o['w']/2+1e-4
    if not set(o['span'])&set(p['layers'] or STACK): return False
    return RC.pad_point(p,o['x'],o['y'])<=o['size']/2+1e-4
def bfs_local(M,net,oldpad):
    """copper of net reachable from oldpad, stopping at vias (ripped) and at other pads (kept)"""
    T=[i for i,t in enumerate(M['tracks']) if t['net']==net]; V=[i for i,v in enumerate(M['vias']) if v['net']==net]
    P=[p for p in M['pads'] if p['net']==net and p is not oldpad]
    rt,rv=set(),set(); front=[]
    for i in T:
        if touches_pad(oldpad,M['tracks'][i],'t'): rt.add(i); front.append(i)
    for i in V:
        if touches_pad(oldpad,M['vias'][i],'v'): rv.add(i)
    while front:
        i=front.pop(); a=M['tracks'][i]
        if any(touches_pad(p,a,'t') for p in P if abs(p['x']-a['x1'])<3 or abs(p['x']-a['x2'])<3): continue  # reached another pad: stop past it
        for j in T:
            if j in rt: continue
            b=M['tracks'][j]
            if b['layer']==a['layer'] and RC.seg_seg((a['x1'],a['y1'],a['x2'],a['y2']),(b['x1'],b['y1'],b['x2'],b['y2']))<=(a['w']+b['w'])/2+1e-4:
                rt.add(j); front.append(j)
        for j in V:
            if j in rv: continue
            v=M['vias'][j]
            if a['layer'] in v['span'] and RC.seg_dist(a['x1'],a['y1'],a['x2'],a['y2'],v['x'],v['y'])<=(a['w']+v['size'])/2+1e-4: rv.add(j)
    return rt,rv
def build_ripped(M,moved_refs,new_pads,old_pads):
    """M: scenario model (pads already moved, base copper). old_pads: the moved pads at their OLD positions."""
    rt,rv=set(),set(); why=collections.defaultdict(set)
    # (a) own nets of the moved parts
    for p in old_pads:
        n=p['net']
        if not n: continue
        if n in BIG:
            a,b=bfs_local(M,n,p); rt|=a; rv|=b
            if a or b: why[n].add('attached to moved %s.%s'%(p['ref'],p['pad']))
        else:
            rt|={i for i,t in enumerate(M['tracks']) if t['net']==n}; rv|={i for i,v in enumerate(M['vias']) if v['net']==n}
            why[n].add('net of moved %s'%p['ref'])
    # (b) other-net copper in the way of the new pads (and same-net copper of a plane net is fine)
    for k,ref,pad,net,lay,d,o in copper_conflicts(M,new_pads,0.10):
        if k=='track': rt.add(M['tracks'].index(o))
        else: rv.add(M['vias'].index(o))
        why[net].add('blocks new %s.%s'%(ref,pad))
    Mr=dict(M); Mr['tracks']=[t for i,t in enumerate(M['tracks']) if i not in rt]; Mr['vias']=[v for i,v in enumerate(M['vias']) if i not in rv]
    ripped_t=[M['tracks'][i] for i in rt]; ripped_v=[M['vias'][i] for i in rv]
    # (c) prune dead copper (islands with no pad and no plane) left behind
    isl=RC.islands(Mr)
    keep_t=set(); keep_v=set()
    for net,gs in isl.items():
        for g in gs: keep_t|=set(g['tracks']); keep_v|=set(g['vias'])
    dead_t=[t for i,t in enumerate(Mr['tracks']) if i not in keep_t]; dead_v=[v for i,v in enumerate(Mr['vias']) if i not in keep_v]
    Mr['tracks']=[t for i,t in enumerate(Mr['tracks']) if i in keep_t]; Mr['vias']=[v for i,v in enumerate(Mr['vias']) if i in keep_v]
    return Mr,ripped_t+dead_t,ripped_v+dead_v,why
