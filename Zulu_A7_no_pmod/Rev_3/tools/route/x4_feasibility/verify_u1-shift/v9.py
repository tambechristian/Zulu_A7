exec(open('v4.py').read().split("import collections\nprint")[0])
import copy
# 1) fix test: move R133, C116, C117, C118, C120 with U1 (+3.5) and rerun body+pad checks
M3 = copy.deepcopy(M2)
for p in M3['pads']:
    if p['ref'] in ('R133','C116','C117','C118','C120'): p['x'] += 3.5
def worst(res):
    w = {}
    for r in res:
        k = r[:4]
        if k not in w or r[5] < w[k][5]: w[k] = r
    return w
wb = worst(bc.check(bc.build(M2, D2), None, 0.1)); wc = worst(bc.check(bc.build(M3, D2), None, 0.1))
print('with forgotten parts moved: findings', len(wc), 'vs', len(wb)); [print(' NEW', wc[k]) for k in wc if k not in wb]
ps = [p for p in M3['pads'] if p['ref'] in ('R133','C116','C117','C118','C120')]
for p in ps:
    for q in M3['pads']:
        if q['ref'] == p['ref'] or not (lays(p)&lays(q)): continue
        d = g(p, q)
        if d < 0.2: print('  padpad', p['ref'], p['pad'], q['ref'], q['pad'], round(d,3))
# 2) U2 minimal dx scan independent
U2o = [p for p in M['pads'] if p['ref']=='U2']
X1 = [p for p in M['pads'] if p['ref']=='X1']
others = [p for p in M2['pads'] if p['ref'] not in ('U2','X4') and 'Top Layer' in lays(p)]
def s2b(cx, cy=4.9):
    return [dict(x=cx+1, y=cy+2.85, w=1.0, h=3.5, shape='rect'), dict(x=cx-1, y=cy+2.85, w=1.0, h=3.5, shape='rect'),
            dict(x=cx-3.35, y=cy-2.9, w=1.5, h=3.4, shape='rect'), dict(x=cx+3.35, y=cy-2.9, w=1.5, h=3.4, shape='rect')], ('r', cx-3.95, cy-4.4, cx+3.95, cy+3.2)
best = None
for cxi in range(0, 260, 2):
    cx = 29.2 + cxi/100
    sp, sb = s2b(cx)
    # S2B vs X2 pins
    if any(g(a, q) < 0.2 for a in sp for q in M['pads'] if q['ref']=='X2'): continue
    for dyi in range(0, 31, 5):
        dy = dyi/100
        for dxi in range(400, 800, 2):
            dx = dxi/100
            U = [dict(p, x=p['x']+dx, y=p['y']+dy) for p in U2o]
            ok = all(g(a, u) >= 0.2 for a in sp for u in U) and all(g_rr(sb, shp(u)) >= 0.1 for u in U)
            # U2 body vs s2b pads
            ub = ('r', 31.475+dx-5, 13.6+dy-5, 31.475+dx+5, 13.6+dy+5)
            ok = ok and all(g_rr(ub, shp(dict(a))) >= 0.1 for a in sp) and all(g(u, x) >= 0.2 for u in U for x in X1)
            if ok:
                if best is None or dx < best[0]: best = (dx, dy, cx)
                break
print('min U2 dx (dy 0..0.3), S2B cx 29.2..31.8:', best)
