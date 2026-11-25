"""Rev 2 placement search (2026-11-11): rank spots for parts displaced by X1's moved mounting holes.
Hard: >=0.20 mm pad-to-pad (other parts), >=0.30 mm pad-to-hole land, no other pad or hole inside the body envelope.
Soft (rip cost): other-net vias reaching the Bottom and Bottom tracks within 0.12 mm of the new lands."""
import json, math, collections, sys
M = json.load(open('prep/base_moved.json'))
refs = collections.defaultdict(list)
for p in M['pads']:
    refs[p['ref']].append(p)
W, H = M['board']['w'], M['board']['h']


def rgap(a, b):
    dx = max(abs(a['x'] - b['x']) - (a['w'] + b['w']) / 2, 0)
    dy = max(abs(a['y'] - b['y']) - (a['h'] + b['h']) / 2, 0)
    return math.hypot(dx, dy)


def hgap(a, h):
    dx = max(abs(a['x'] - h['x']) - a['w'] / 2, 0)
    dy = max(abs(a['y'] - h['y']) - a['h'] / 2, 0)
    return math.hypot(dx, dy) - max(h['w'], h['h']) / 2


def segpt(t, x, y):
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L = dx * dx + dy * dy
    k = 0 if L == 0 else max(0, min(1, ((x - t['x1']) * dx + (y - t['y1']) * dy) / L))
    return t['x1'] + k * dx, t['y1'] + k * dy


def search(group, R=6.0, step=0.05, target=None):
    own = {p['net'] for r in group for p in refs[r] if p['net']}
    gp = [p for r in group for p in refs[r]]
    cx = sum(p['x'] for p in gp) / len(gp); cy = sum(p['y'] for p in gp) / len(gp)
    others = [p for p in M['pads'] if p['ref'] not in group and (p['drill'] or 'Bottom Layer' in p['layers'])]
    holes = [p for p in others if p['drill']]
    smd = [p for p in others if not p['drill']]
    vias = [v for v in M['vias'] if 'Bottom Layer' in v['span'] and v['net'] not in own]
    trks = [t for t in M['tracks'] if t['layer'] == 'Bottom Layer' and t['net'] not in own]
    out = []
    n = int(R / step)
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            dx, dy = i * step, j * step
            P = [dict(p, x=p['x'] + dx, y=p['y'] + dy) for p in gp]
            if any(not (0.4 < p['x'] - p['w'] / 2 and p['x'] + p['w'] / 2 < W - 0.4 and 0.4 < p['y'] - p['h'] / 2 and p['y'] + p['h'] / 2 < H - 0.4) for p in P):
                continue
            if any(rgap(p, q) < 0.20 for p in P for q in smd if q['net'] != p['net'] or True):
                continue
            if any(hgap(p, h) < 0.30 for p in P for h in holes):
                continue
            # body envelope per part
            bad = False
            for r in group:
                Q = [p for p in P if p['ref'] == r]
                xs = [p['x'] for p in Q]; ys = [p['y'] for p in Q]
                body = dict(x=(min(xs) + max(xs)) / 2, y=(min(ys) + max(ys)) / 2, w=max(xs) - min(xs), h=max(ys) - min(ys) + Q[0]['h'])
                if any(rgap(body, q) == 0 for q in smd + holes):
                    bad = True; break
            if bad:
                continue
            rv = {k for k, v in enumerate(vias) for p in P if rgap(p, dict(x=v['x'], y=v['y'], w=v['size'], h=v['size'])) < 0.12}
            rt = set()
            for k, t in enumerate(trks):
                for p in P:
                    qx, qy = segpt(t, p['x'], p['y'])
                    if rgap(p, dict(x=qx, y=qy, w=t['w'], h=t['w'])) < 0.12:
                        rt.add(k); break
            dist = math.hypot(dx, dy)
            tgt = 0 if target is None else math.hypot(cx + dx - target[0], cy + dy - target[1])
            out.append((len(rv) * 3 + len(rt) + dist * 0.5 + tgt * 0.3, round(dx, 2), round(dy, 2), len(rv), len(rt),
                        sorted({vias[k]['net'] for k in rv}), sorted({trks[k]['net'] for k in rt})))
    out.sort()
    return out


if __name__ == '__main__':
    grp = sys.argv[1].split(',')
    tgt = tuple(map(float, sys.argv[2].split(','))) if len(sys.argv) > 2 else None
    res = search(grp, target=tgt)
    print(grp, len(res), 'legal offsets')
    for r in res[:12]:
        print('  cost %.1f dx %s dy %s  vias %d tracks %d  vianets %s tracknets %s' % r)
