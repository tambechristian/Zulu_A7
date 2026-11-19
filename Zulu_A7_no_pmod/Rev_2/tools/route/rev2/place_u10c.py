"""U10 spot search, binned: hard = pads/holes/body as before + no power track (w >= 0.25 mm or power net) within
0.12 mm of a new land; cost = 3 x vias + tracks ripped + 0.3 x distance to U2's EE pins + 0.15 x distance to the
EEPROM pull-ups (R96-R101)."""
import math, collections
from place_search import M, refs, rgap, hgap, segpt, W, H
POWER = {'GND', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'USB5V0', 'VU', 'VBATT'}
gp = refs['U10']; cx = sum(p['x'] for p in gp) / 8; cy = sum(p['y'] for p in gp) / 8
own = {p['net'] for p in gp if p['net']}
B = 1.0
def bins(items, ext):
    g = collections.defaultdict(list)
    for it in items:
        x0, y0, x1, y1 = ext(it)
        for i in range(int(x0 // B), int(x1 // B) + 1):
            for j in range(int(y0 // B), int(y1 // B) + 1):
                g[(i, j)].append(it)
    return g
others = [p for p in M['pads'] if p['ref'] != 'U10' and (p['drill'] or 'Bottom Layer' in p['layers'])]
for k, p in enumerate(others): p['_k'] = k
pe = lambda p: (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
GP = bins(others, pe)
vias = [dict(x=v['x'], y=v['y'], w=v['size'], h=v['size'], net=v['net'], _k=k) for k, v in enumerate(M['vias']) if 'Bottom Layer' in v['span'] and v['net'] not in own]
GV = bins(vias, pe)
trks = [dict(t, _k=k) for k, t in enumerate(M['tracks']) if t['layer'] == 'Bottom Layer' and t['net'] not in own]
GT = bins(trks, lambda t: (min(t['x1'], t['x2']) - t['w'], min(t['y1'], t['y2']) - t['w'], max(t['x1'], t['x2']) + t['w'], max(t['y1'], t['y2']) + t['w']))
def near(g, x0, y0, x1, y1):
    seen = {}
    for i in range(int(x0 // B) - 1, int(x1 // B) + 2):
        for j in range(int(y0 // B) - 1, int(y1 // B) + 2):
            for it in g.get((i, j), ()):
                seen[it['_k']] = it
    return seen.values()
ENV = []
for r, ps in refs.items():
    if r == 'U10' or not ps or ps[0]['drill'] or ps[0]['layers'] != ['Bottom Layer']: continue
    x0 = min(p['x'] - p['w'] / 2 for p in ps); x1 = max(p['x'] + p['w'] / 2 for p in ps)
    y0 = min(p['y'] - p['h'] / 2 for p in ps); y1 = max(p['y'] + p['h'] / 2 for p in ps)
    ENV.append(dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, w=x1 - x0, h=y1 - y0, ref=r))
U2EE = (28.72, 19.3); PULL = (18.6, 19.0)
out = []
for rot in (0, 90, 180, 270):
    c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    base = []
    for p in gp:
        ox, oy = p['x'] - cx, p['y'] - cy
        w, h = (p['w'], p['h']) if rot in (0, 180) else (p['h'], p['w'])
        base.append(dict(p, ox=c * ox - s * oy, oy=s * ox + c * oy, w=w, h=h))
    for i in range(int(W / 0.1) + 1):
        for j in range(int(H / 0.1) + 1):
            x, y = i * 0.1, j * 0.1
            P = [dict(b, x=x + b['ox'], y=y + b['oy']) for b in base]
            xs = [p['x'] for p in P]; ys = [p['y'] for p in P]
            X0, Y0, X1, Y1 = min(xs) - 1.5, min(ys) - 1.5, max(xs) + 1.5, max(ys) + 1.5
            if X0 + 1.5 - 1.04 < 0.4 or Y0 + 1.5 - 1.04 < 0.4 or X1 - 1.5 + 1.04 > W - 0.4 or Y1 - 1.5 + 1.04 > H - 0.4:
                continue
            obs = list(near(GP, X0, Y0, X1, Y1))
            ok = True
            for p in P:
                for q in obs:
                    if (hgap(p, q) < 0.30) if q['drill'] else (rgap(p, q) < 0.20):
                        ok = False; break
                if not ok: break
            if not ok: continue
            body = dict(x=x, y=y, w=max(xs) - min(xs), h=max(ys) - min(ys))
            if any(rgap(body, q) == 0 for q in obs): continue
            env = dict(x=x, y=y, w=max(xs) - min(xs) + 2.07, h=max(ys) - min(ys) + 0.51) if rot in (0, 180) else dict(x=x, y=y, w=max(xs) - min(xs) + 0.51, h=max(ys) - min(ys) + 2.07)
            if any(rgap(env, e) < 0.15 for e in ENV): continue
            rv = {v['_k'] for v in near(GV, X0, Y0, X1, Y1) for p in P if rgap(p, v) < 0.12}
            rt = set(); bad = False
            for t in near(GT, X0, Y0, X1, Y1):
                for p in P:
                    qx, qy = segpt(t, p['x'], p['y'])
                    if rgap(p, dict(x=qx, y=qy, w=t['w'], h=t['w'])) < 0.12:
                        if t['net'] in POWER or t['w'] >= 0.25: bad = True
                        rt.add(t['_k']); break
                if bad: break
            if bad: continue
            if any(v['net'] in POWER for v in vias if v['_k'] in rv): continue
            d1 = math.hypot(x - U2EE[0], y - U2EE[1]); d2 = math.hypot(x - PULL[0], y - PULL[1])
            vn = sorted({v['net'] for v in vias if v['_k'] in rv}); tn = sorted({M['tracks'][k]['net'] for k in rt})
            out.append((len(rv) * 3 + len(rt) + 0.3 * d1 + 0.15 * d2, round(x, 2), round(y, 2), rot, len(rv), len(rt), round(d1, 1), round(d2, 1), vn, tn))
out.sort()
print(len(out), 'legal U10 placements (no power copper ripped)')
seen = []
for r in out:
    if any(abs(r[1] - q[1]) < 1.5 and abs(r[2] - q[2]) < 1.5 for q in seen): continue
    seen.append(r)
    print('  cost %.1f at (%s, %s) rot %d  rip vias %d tracks %d  to-U2 %s to-pullups %s  vianets %s tracknets %s' % r)
    if len(seen) >= 12: break
