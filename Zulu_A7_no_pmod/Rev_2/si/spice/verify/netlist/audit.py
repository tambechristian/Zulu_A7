"""Audit bus_sim.net_elements against an independent copper-connectivity rebuild for every SDRAM net."""
import sys, json, math, collections, re
sys.path.insert(0, '../..')
import bus_sim as B

M = json.load(open(B.MODEL))

def segdist(ax, ay, bx, by, cx, cy, dx, dy):
    # min distance between segments AB and CD
    def pd(px, py, x1, y1, x2, y2):
        return B._seg_dist(px, py, x1, y1, x2, y2)[0]
    # intersection test
    def ccw(A, Bp, C):
        return (C[1]-A[1])*(Bp[0]-A[0]) - (Bp[1]-A[1])*(C[0]-A[0])
    A, Bq, C, D = (ax, ay), (bx, by), (cx, cy), (dx, dy)
    d1, d2, d3, d4 = ccw(C, D, A), ccw(C, D, Bq), ccw(A, Bq, C), ccw(A, Bq, D)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(pd(ax, ay, cx, cy, dx, dy), pd(bx, by, cx, cy, dx, dy), pd(cx, cy, ax, ay, bx, by), pd(dx, dy, ax, ay, bx, by))

def copper_graph(net):
    """objects: tracks, vias (one object per via, all its layers), pads; edge when copper overlaps on a shared layer."""
    T = [t for t in M['tracks'] if t['net'] == net]
    V = [v for v in M['vias'] if v['net'] == net]
    P = [p for p in M['pads'] if p['net'] == net]
    objs = [('t', i) for i in range(len(T))] + [('v', j) for j in range(len(V))] + [('p', k) for k in range(len(P))]
    E = []
    def layers(o):
        return {T[o[1]]['layer']} if o[0] == 't' else set(V[o[1]]['span']) if o[0] == 'v' else set(P[o[1]]['layers'])
    def touch(a, b):
        if not (layers(a) & layers(b)):
            return False
        if a[0] == 'p' and b[0] == 'p':
            return False
        if a[0] == 't' and b[0] == 't':
            s, u = T[a[1]], T[b[1]]
            return segdist(s['x1'], s['y1'], s['x2'], s['y2'], u['x1'], u['y1'], u['x2'], u['y2']) <= (s['w'] + u['w']) / 2 - 1e-4
        if a[0] == 'v' and b[0] == 'v':
            v, w = V[a[1]], V[b[1]]
            return math.hypot(v['x'] - w['x'], v['y'] - w['y']) <= (v['size'] + w['size']) / 2 - 1e-4
        if b[0] == 't':
            a, b = b, a
        if a[0] == 't':
            s = T[a[1]]
            if b[0] == 'v':
                v = V[b[1]]
                return B._seg_dist(v['x'], v['y'], s['x1'], s['y1'], s['x2'], s['y2'])[0] <= (v['size'] + s['w']) / 2 - 1e-4
            p = P[b[1]]
            # sample along the track centreline; overlap with pad (rect) expanded by w/2
            for k in range(101):
                x = s['x1'] + (s['x2'] - s['x1']) * k / 100; y = s['y1'] + (s['y2'] - s['y1']) * k / 100
                if abs(x - p['x']) <= p['w'] / 2 + s['w'] / 2 and abs(y - p['y']) <= p['h'] / 2 + s['w'] / 2:
                    return True
            return False
        if a[0] == 'p':
            a, b = b, a
        v, p = V[a[1]], P[b[1]]
        return abs(v['x'] - p['x']) <= p['w'] / 2 + v['size'] / 2 and abs(v['y'] - p['y']) <= p['h'] / 2 + v['size'] / 2
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            if touch(objs[i], objs[j]):
                E.append((objs[i], objs[j]))
    return T, V, P, objs, E

def components(nodes, edges):
    uf = B.UF()
    for n in nodes: uf.find(n)
    for a, b in edges: uf.union(a, b)
    c = collections.defaultdict(list)
    for n in nodes: c[uf.find(n)].append(n)
    return list(c.values())

def audit(net, verbose=False):
    T, V, P, objs, E = copper_graph(net)
    comp = components(objs, E)
    el, n1, n3, rep = B.net_elements(M, net)
    # bus_sim element graph
    nodes, edges = set(), []
    tl_len_by_layer = collections.defaultdict(float)
    for e in el:
        tok = e.split()
        if tok[0][0] == 'T':
            a, b = tok[1], tok[3]
        elif tok[0][0] in 'RL':
            a, b = tok[1], tok[2]
        elif tok[0][0] == 'C':
            nodes.add(tok[1]); continue
        nodes |= {a, b}; edges.append((a, b))
    nodes |= {n1, n3}
    bcomp = components(sorted(nodes), edges)
    # T-line delay sum check vs total track length
    tot_len = sum(math.hypot(t['x2']-t['x1'], t['y2']-t['y1']) for t in T)
    tl = [e for e in el if e.startswith('T')]
    tdsum = sum(float(re.search(r'TD=(\S+)', e).group(1)) for e in tl)
    lumpC = sum(float(e.split()[3]) for e in el if e.startswith('Cl_'))
    out = {'net': net, 'tracks': len(T), 'vias': len(V), 'pads': [(p['ref'], p['pad']) for p in P],
           'copper_components': len(comp), 'spice_components': len(bcomp), 'u1_u3_same': rep['connected'],
           'track_len_mm': round(tot_len, 3), 'rep_len_mm': round(rep['len_mm'], 3), 'tlines': len(tl), 'lumped': rep['lumped'],
           'td_ps': round(tdsum * 1e12, 2), 'lumpC_pF': round(lumpC * 1e12, 4)}
    # copper edges the endpoint-merger may miss: track-track touch not at endpoints; track crossing via/pad mid-segment
    return out, comp, bcomp

if __name__ == '__main__':
    nets = sys.argv[1:] or B.NETS
    for n in nets:
        o, comp, bcomp = audit(n)
        flag = '' if o['copper_components'] == 1 and o['spice_components'] == 1 else '  <-- CHECK'
        print(json.dumps(o) + flag)
