"""Scan every edge position/side for a JST S2B-PH-SM4-TB (side entry) on the Zulu A7 no-PMOD Rev_2 board."""
import json, math, sys, collections
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools'
sys.path.insert(0, T)
import body_check as bc
M = json.load(open(T + '/route/bodies/base.json'))
D = json.load(open(T + '/route/bodies/comps.json'))
W, H = M['board']['w'], M['board']['h']
P = bc.build(M, D)
C = {c['ref']: c for c in D['comps']}
D0 = 0.30          # MP pad front edge from the board edge
PADGAP, BODYGAP = 0.20, 0.10
CU = 0.09          # copper clearance for tracks/vias vs the new pads

def fp(d0=D0):
    """footprint in (t, d): t along the edge, d depth inward. returns pads [(name,t0,t1,d0,d1)], body (t0,t1,d0,d1)"""
    pads = [('MP1', -4.10, -2.60, d0, d0 + 3.4), ('MP2', 2.60, 4.10, d0, d0 + 3.4),
            ('1', -1.5, -0.5, d0 + 5.7, d0 + 9.2), ('2', 0.5, 1.5, d0 + 5.7, d0 + 9.2)]
    body = (-3.95, 3.95, d0 + 0.2, d0 + 7.8)
    return pads, body

def tobox(edge, c, r):
    t0, t1, d0, d1 = r
    if edge == 'S': return (c + t0, d0, c + t1, d1)
    if edge == 'N': return (c - t1, H - d1, c - t0, H - d0)
    if edge == 'W': return (d0, c - t1, d1, c - t0)
    if edge == 'E': return (W - d1, c + t0, W - d0, c + t1)

LAYER = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}

def seg_box_gap(t, b):
    # gap between a track (capsule) and box: sample
    x1, y1, x2, y2, w = t['x1'], t['y1'], t['x2'], t['y2'], t['w']
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.05) + 1)
    g = 1e9
    for i in range(n):
        u = i / (n - 1)
        x, y = x1 + u * (x2 - x1), y1 + u * (y2 - y1)
        dx = max(b[0] - x, 0, x - b[2]); dy = max(b[1] - y, 0, y - b[3])
        g = min(g, math.hypot(dx, dy) - w / 2)
    return g

def seglen_in(t, b):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    L = math.hypot(x2 - x1, y2 - y1); n = max(2, int(L / 0.05) + 1); k = 0
    for i in range(n):
        u = i / (n - 1); x, y = x1 + u * (x2 - x1), y1 + u * (y2 - y1)
        if b[0] <= x <= b[2] and b[1] <= y <= b[3]: k += 1
    return L * k / n

def evaluate(edge, side, c, d0=D0, copper=True):
    pads, body = fp(d0)
    pb = [(n, tobox(edge, c, r)) for n, *r in [(p[0], *p[1:]) for p in pads]]
    bb = tobox(edge, c, body)
    out = collections.defaultdict(list)
    # board outline for every pad
    for n, b in pb:
        if b[0] < 0.3 - 1e-6 or b[1] < 0.3 - 1e-6 or b[2] > W - 0.3 + 1e-6 or b[3] > H - 0.3 + 1e-6:
            out['_EDGE'].append(n)
    if bb[0] < -1e-6 or bb[1] < -1e-6 or bb[2] > W + 1e-6 or bb[3] > H + 1e-6:
        out['_EDGE'].append('body')
    for ref, v in P[side].items():
        base = ref.split('[')[0]
        if base in ('X4',): continue
        for pbx, p in v['pads']:
            for n, b in pb:
                g = bc.gap(b, pbx)
                if g < PADGAP: out[base].append('pad%s-%s %.2f' % (p['pad'], n, g))
            g = bc.gap(bb, pbx)
            if g < BODYGAP: out[base].append('pad%s-body %.2f' % (p['pad'], g))
        for ob in v['body']:
            g = bc.gap(bb, ob)
            if g < BODYGAP: out[base].append('body-body %.2f' % g)
            for n, b in pb:
                g = bc.gap(b, ob)
                if g < BODYGAP: out[base].append('body-pad%s %.2f' % (n, g))
    cu = collections.defaultdict(lambda: [0, 0.0, 0])  # net: [ntracks, length under pads(+clear), nvias]
    if copper:
        L = LAYER[side]
        for t in M['tracks']:
            if t['layer'] != L: continue
            for n, b in pb:
                g = seg_box_gap(t, b)
                if g < CU:
                    e = cu[t['net']]; e[0] += 1; e[1] += math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
                    break
        for v in M['vias']:
            if L not in v['span']: continue
            for n, b in pb:
                dx = max(b[0] - v['x'], 0, v['x'] - b[2]); dy = max(b[1] - v['y'], 0, v['y'] - b[3])
                if math.hypot(dx, dy) - v['size'] / 2 < CU:
                    cu[v['net']][2] += 1; break
    return dict(out), dict(cu), pb, bb

if __name__ == '__main__':
    res = []
    for edge in 'SNWE':
        span = W if edge in 'SN' else H
        for side in ('Top', 'Bottom'):
            c = 4.4
            while c <= span - 4.4 + 1e-9:
                o, cu, _, _ = evaluate(edge, side, round(c, 2), copper=False)
                res.append((edge, side, round(c, 2), o))
                c += 0.1
    json.dump([(e, s, c, {k: v for k, v in o.items()}) for e, s, c, o in res], open(sys.argv[1], 'w'))
    for edge in 'SNWE':
        for side in ('Top', 'Bottom'):
            R = [r for r in res if r[0] == edge and r[1] == side]
            best = sorted(R, key=lambda r: (len(r[3]), r[2]))[:1]
            nb = min(len(r[3]) for r in R)
            print(edge, side, 'min blockers', nb)
            # distinct blocker sets with min count+1
            seen = {}
            for r in R:
                k = tuple(sorted(r[3]))
                if len(k) <= nb + 2:
                    seen.setdefault(k, []).append(r[2])
            for k, cs in sorted(seen.items(), key=lambda kv: len(kv[0]))[:8]:
                print('   c %.1f..%.1f' % (min(cs), max(cs)), k)
