"""U10 short-move search: U10 shifts (no rotation); small 2-pad Bottom parts in the way may be displaced
(each then needs its own spot). Hard: holes, multi-pad parts (pads + envelope), board edge, power copper."""
import math, collections
from place_search import M, refs, rgap, hgap, segpt, W, H
POWER = {'GND', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'USB5V0', 'VU', 'VBATT'}
gp = refs['U10']; own = {p['net'] for p in gp if p['net']}
bot = {r: ps for r, ps in refs.items() if r != 'U10' and ps and not ps[0]['drill'] and ps[0]['layers'] == ['Bottom Layer']}
small = {r for r, ps in bot.items() if len(ps) == 2 and max(p['w'] for p in ps) <= 0.95}
holes = [p for p in M['pads'] if p['drill']]
def env(ps, m=0):
    x0 = min(p['x'] - p['w'] / 2 for p in ps); x1 = max(p['x'] + p['w'] / 2 for p in ps)
    y0 = min(p['y'] - p['h'] / 2 for p in ps); y1 = max(p['y'] + p['h'] / 2 for p in ps)
    return dict(x=(x0 + x1) / 2, y=(y0 + y1) / 2, w=x1 - x0 + 2 * m, h=y1 - y0 + 2 * m)
vias = [v for v in M['vias'] if 'Bottom Layer' in v['span'] and v['net'] not in own]
trks = [t for t in M['tracks'] if t['layer'] == 'Bottom Layer' and t['net'] not in own]
res = []
for i in range(-80, 21):
    for j in range(-40, 41):
        dx, dy = i * 0.05, j * 0.05
        P = [dict(p, x=p['x'] + dx, y=p['y'] + dy) for p in gp]
        if any(not (0.4 < p['x'] - p['w'] / 2 and p['x'] + p['w'] / 2 < W - 0.4 and 0.4 < p['y'] - p['h'] / 2 and p['y'] + p['h'] / 2 < H - 0.4) for p in P): continue
        if any(hgap(p, h) < 0.30 for p in P for h in holes): continue
        E = env(P)
        bad = False; disp = set()
        for r, ps in bot.items():
            if r in small:
                if any(rgap(p, q) < 0.20 for p in P for q in ps) or rgap(E, env(ps)) == 0: disp.add(r)
            else:
                if any(rgap(p, q) < 0.20 for p in P for q in ps) or rgap(E, env(ps)) < 0.15: bad = True; break
        if bad: continue
        rv = [v for v in vias if any(rgap(p, dict(x=v['x'], y=v['y'], w=v['size'], h=v['size'])) < 0.12 for p in P)]
        rt = []
        for t in trks:
            for p in P:
                qx, qy = segpt(t, p['x'], p['y'])
                if rgap(p, dict(x=qx, y=qy, w=t['w'], h=t['w'])) < 0.12: rt.append(t); break
        if any(t['net'] in POWER or t['w'] >= 0.25 for t in rt) or any(v['net'] in POWER for v in rv): continue
        res.append((len(disp) * 4 + len(rv) * 3 + len(rt) + math.hypot(dx, dy), round(dx, 2), round(dy, 2), sorted(disp), len(rv), len(rt), sorted({v['net'] for v in rv}), sorted({t['net'] for t in rt})))
res.sort()
print(len(res), 'legal short moves')
for r in res[:10]: print('  cost %.1f dx %s dy %s displace %s  vias %d tracks %d  %s %s' % r)
