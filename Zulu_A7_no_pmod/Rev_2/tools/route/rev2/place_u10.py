import math, sys
from place_search import M, refs, rgap, hgap, segpt, W, H
gp = refs['U10']
cx = sum(p['x'] for p in gp) / 8; cy = sum(p['y'] for p in gp) / 8
own = {p['net'] for p in gp if p['net']}
others = [p for p in M['pads'] if p['ref'] != 'U10' and (p['drill'] or 'Bottom Layer' in p['layers'])]
holes = [p for p in others if p['drill']]; smd = [p for p in others if not p['drill']]
vias = [v for v in M['vias'] if 'Bottom Layer' in v['span'] and v['net'] not in own]
trks = [t for t in M['tracks'] if t['layer'] == 'Bottom Layer' and t['net'] not in own]
U2EE = (28.72, 19.3)
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
            if any(not (0.4 < p['x'] - p['w'] / 2 and p['x'] + p['w'] / 2 < W - 0.4 and 0.4 < p['y'] - p['h'] / 2 and p['y'] + p['h'] / 2 < H - 0.4) for p in P):
                continue
            if any(rgap(p, q) < 0.20 for p in P for q in smd):
                continue
            if any(hgap(p, hh) < 0.30 for p in P for hh in holes):
                continue
            xs = [p['x'] for p in P]; ys = [p['y'] for p in P]
            body = dict(x=x, y=y, w=max(xs) - min(xs), h=max(ys) - min(ys))
            if any(rgap(body, q) == 0 for q in smd + holes):
                continue
            rv = {k for k, v in enumerate(vias) for p in P if rgap(p, dict(x=v['x'], y=v['y'], w=v['size'], h=v['size'])) < 0.12}
            rt = set()
            for k, t in enumerate(trks):
                for p in P:
                    qx, qy = segpt(t, p['x'], p['y'])
                    if rgap(p, dict(x=qx, y=qy, w=t['w'], h=t['w'])) < 0.12:
                        rt.add(k); break
            d = math.hypot(x - U2EE[0], y - U2EE[1])
            out.append((len(rv) * 3 + len(rt) + d * 0.5, round(x, 2), round(y, 2), rot, len(rv), len(rt), round(d, 1),
                        sorted({vias[k]['net'] for k in rv}), sorted({trks[k]['net'] for k in rt})))
out.sort()
print(len(out), 'legal U10 placements')
seen = []
for r in out:
    if any(abs(r[1] - q[1]) < 1.5 and abs(r[2] - q[2]) < 1.5 for q in seen):
        continue
    seen.append(r)
    print('  cost %.1f at (%s, %s) rot %d  rip vias %d tracks %d  dist-to-U2 %s  vianets %s tracknets %s' % r)
    if len(seen) >= 10:
        break
