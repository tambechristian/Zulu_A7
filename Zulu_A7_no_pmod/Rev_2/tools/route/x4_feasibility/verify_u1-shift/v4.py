exec(open('v1.py').read().split("def key")[0])
W, H = 60.96, 25.4
STACK = bc.STACK
def lays(p): return set(p['layers'] or STACK)
def shp(p):
    if p.get('shape') == 'circle' or (p.get('shape') in ('round','oval') and abs(p['w']-p['h'])<1e-6): return ('c', p['x'], p['y'], p['w']/2)
    return ('r', p['x']-p['w']/2, p['y']-p['h']/2, p['x']+p['w']/2, p['y']+p['h']/2)
def g_rr(a, b):
    dx = max(a[1]-b[3], b[1]-a[3]); dy = max(a[2]-b[4], b[2]-a[4])
    if dx < 0 and dy < 0: return max(dx, dy)
    return math.hypot(max(dx,0), max(dy,0))
def g_cr(c, r):
    dx = max(r[1]-c[1], 0, c[1]-r[3]); dy = max(r[2]-c[2], 0, c[2]-r[4]); return math.hypot(dx, dy) - c[3]
def g(a, b):
    A, B = shp(a), shp(b)
    if A[0]=='c' and B[0]=='c': return math.hypot(A[1]-B[1], A[2]-B[2]) - A[3] - B[3]
    if A[0]=='c': return g_cr(A, B)
    if B[0]=='c': return g_cr(B, A)
    return g_rr(A, B)
import collections
print(collections.Counter(p.get('shape') for p in M['pads']))
def padpad(MM, thr=0.2):
    out = {}
    ps = [p for p in MM['pads'] if p.get('ref')]
    for i, p in enumerate(ps):
        for q in ps[i+1:]:
            if p['ref'] == q['ref'] or not (lays(p) & lays(q)): continue
            if abs(p['x']-q['x']) > 8 or abs(p['y']-q['y']) > 8: continue
            d = g(p, q)
            if d < thr: out[(p['ref'],p['pad'],q['ref'],q['pad'])] = round(d,3)
    return out
def norm(d): return {tuple(sorted([(k[0],k[1]),(k[2],k[3])])): v for k, v in d.items()}
A = norm(padpad(M)); B = norm(padpad(M2))
print('padpad<0.2 base', len(A), 'cand', len(B))
for k in sorted(B):
    if k not in A or B[k] < A[k]-1e-6: print('  NEW/WORSE', k, A.get(k), B[k])
# edge for all pads in candidate
for p in M2['pads']:
    s = shp(p)
    e = min(s[1]-s[3], s[2]-s[3], W-s[1]-s[3], H-s[2]-s[3]) if s[0]=='c' else min(s[1], s[2], W-s[3], H-s[4])
    if e < 0.3-1e-9:
        p0 = [q for q in M['pads'] if q['ref']==p['ref'] and q['pad']==p['pad']][0]
        s0 = shp(p0); e0 = min(s0[1]-s0[3], s0[2]-s0[3], W-s0[1]-s0[3], H-s0[2]-s0[3]) if s0[0]=='c' else min(s0[1], s0[2], W-s0[3], H-s0[4])
        if abs(e-e0) > 1e-6: print('  EDGE NEW', p['ref'], p['pad'], round(e,3), 'was', round(e0,3))
# body outline vs board
P2 = bc.build(M2, D2)
for s, PP in P2.items():
    for r, v in PP.items():
        for b in v['body']:
            if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H:
                print('  body outside board', s, r, [round(x,2) for x in b])
