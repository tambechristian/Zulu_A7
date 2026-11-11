"""Simulated-annealing placement of the LTC3556 power block (2026-11-10).

    python place_opt.py <ripped model.json> <config.json> <out placement.json> [seed] [iterations]

config.json:
  region   [x0, y0, x1, y1]        where the movable parts may go (Bottom side)
  side     "B"
  fixed    {"REF": [side, x, y, rot]}   parts placed by hand (not moved)
  parts    ["REF", ...]           parts to place (footprints from place_check.PARTS)
  anchors  {"NAME": [x, y]}        external connection points (e.g. where VBATT copper ends)
  links    [[w, "REF.pad" or "@ANCHOR", "REF.pad" or "@ANCHOR"], ...]  weighted connections (distance cost)
  init     {"REF": [x, y, rot]}   optional start positions
Obstacles: every pad of a non-movable part on the side (and drilled pads), tracks and vias on the side, board edge.
Hard constraints (penalised): pad extents + GAP between parts, + CLR to obstacle copper, inside region, edge.
"""
import json
import math
import random
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else __file__.rsplit('/', 1)[0])
import place_check as PC  # noqa: E402

R = 0.05


def main():
    M = json.load(open(sys.argv[1]))
    C = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    rng = random.Random(int(sys.argv[4]) if len(sys.argv) > 4 else 1)
    iters = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
    side = C.get('side', 'B')
    L = 'Bottom Layer' if side == 'B' else 'Top Layer'
    movable = set(C['parts']) | set(C.get('fixed', {}))
    W, H = M['board']['w'], M['board']['h']
    nx, ny = int(W / R) + 1, int(H / R) + 1
    obs = np.zeros((ny, nx), bool)

    def paint_rect(x0, y0, x1, y1):
        a, b = max(0, int(y0 / R)), min(ny, int(math.ceil(y1 / R)) + 1)
        c, d = max(0, int(x0 / R)), min(nx, int(math.ceil(x1 / R)) + 1)
        obs[a:b, c:d] = True
    m = PC.CLR
    for p in M['pads']:
        if p['ref'] in movable:
            continue
        if L in p['layers'] or p.get('drill', 0) > 0:
            paint_rect(p['x'] - p['w'] / 2 - PC.GAP, p['y'] - p['h'] / 2 - PC.GAP, p['x'] + p['w'] / 2 + PC.GAP, p['y'] + p['h'] / 2 + PC.GAP)
    for t in M['tracks']:
        if t['layer'] != L:
            continue
        n = max(1, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.03))
        r = t['w'] / 2 + m
        for k in range(n + 1):
            x = t['x1'] + (t['x2'] - t['x1']) * k / n
            y = t['y1'] + (t['y2'] - t['y1']) * k / n
            paint_rect(x - r, y - r, x + r, y + r)
    for v in M['vias']:
        if L in v['span']:
            r = v['size'] / 2 + m
            paint_rect(v['x'] - r, v['y'] - r, v['x'] + r, v['y'] + r)
    cs = np.pad(np.cumsum(np.cumsum(obs.astype(np.int32), 0), 1), ((1, 0), (1, 0)))

    def blocked(x0, y0, x1, y1):
        a, b = max(0, int(y0 / R)), min(ny, int(math.ceil(y1 / R)))
        c, d = max(0, int(x0 / R)), min(nx, int(math.ceil(x1 / R)))
        if a >= b or c >= d:
            return 0
        return int(cs[b, d] - cs[a, d] - cs[b, c] + cs[a, c])
    nets = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
    # line of sight (config 'los_min_w'): links of at least this weight between two pads must have a clear straight
    # Bottom path LOS_R wide (no other-net pad, track or via); every blocked 0.1 mm costs LOS_W times the link weight more
    LOS_R = C.get('los_r', 0.25)
    LOS_W = C.get('los_w', 4.0)
    LOS = [l for l in C['links'] if C.get('los_min_w') and l[0] >= C['los_min_w'] and not l[1].startswith('@') and not l[2].startswith('@')]
    onet = np.full((ny, nx), '', dtype=object)
    for t in M['tracks']:
        if t['layer'] != L:
            continue
        n = max(1, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.03))
        r = t['w'] / 2 + LOS_R
        for k in range(n + 1):
            x = t['x1'] + (t['x2'] - t['x1']) * k / n
            y = t['y1'] + (t['y2'] - t['y1']) * k / n
            onet[max(0, int((y - r) / R)):int((y + r) / R) + 1, max(0, int((x - r) / R)):int((x + r) / R) + 1] = t['net'] or '?'
    for v in M['vias']:
        if L in v['span']:
            r = v['size'] / 2 + LOS_R
            onet[max(0, int((v['y'] - r) / R)):int((v['y'] + r) / R) + 1, max(0, int((v['x'] - r) / R)):int((v['x'] + r) / R) + 1] = v['net'] or '?'
    for p in M['pads']:
        if p['ref'] in movable:
            continue
        if L in p['layers'] or p.get('drill', 0) > 0:
            onet[max(0, int((p['y'] - p['h'] / 2 - LOS_R) / R)):int((p['y'] + p['h'] / 2 + LOS_R) / R) + 1,
                 max(0, int((p['x'] - p['w'] / 2 - LOS_R) / R)):int((p['x'] + p['w'] / 2 + LOS_R) / R) + 1] = p['net'] or '?'

    def blocked_net(x, y, net):
        i, j = int(y / R), int(x / R)
        if not (0 <= i < ny and 0 <= j < nx):
            return True
        o = onet[i, j]
        return o != '' and o != net
    region = C['region']
    state = {}
    for ref in C['parts']:
        if ref in C.get('init', {}):
            x, y, rot = C['init'][ref]
        else:
            x, y, rot = rng.uniform(region[0], region[2]), rng.uniform(region[1], region[3]), rng.choice([0, 90, 180, 270])
        state[ref] = [x, y, rot]
    fixed = {k: v for k, v in C.get('fixed', {}).items()}

    def pads(ref, s):
        if ref in fixed:
            sd, x, y, rot = fixed[ref]
            return PC.pads_of(ref, sd, x, y, rot, nets)
        x, y, rot = s
        return PC.pads_of(ref, side, x, y, rot, nets)

    def ext(ps, g=0.0):
        return (min(p['x'] - p['w'] / 2 for p in ps) - g, min(p['y'] - p['h'] / 2 for p in ps) - g,
                max(p['x'] + p['w'] / 2 for p in ps) + g, max(p['y'] + p['h'] / 2 for p in ps) + g)
    allrefs = list(C['parts']) + list(fixed)

    def cost(st):
        P = {r: pads(r, st.get(r)) for r in allrefs}
        pen = 0.0
        boxes = {}
        for r in C['parts']:
            ps = P[r]
            e = ext(ps)
            if e[0] < region[0] or e[1] < region[1] or e[2] > region[2] or e[3] > region[3]:
                pen += 50 + 20 * (max(0, region[0] - e[0]) + max(0, region[1] - e[1]) + max(0, e[2] - region[2]) + max(0, e[3] - region[3]))
            if e[0] < PC.EDGE or e[1] < PC.EDGE or e[2] > W - PC.EDGE or e[3] > H - PC.EDGE:
                pen += 100
            for p in ps:
                b = blocked(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
                if b:
                    pen += 20 + 0.05 * b
            boxes[r] = ext(ps, PC.GAP / 2)
        for r in fixed:
            boxes[r] = ext(P[r], PC.GAP / 2)
        rs = list(boxes)
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = boxes[rs[i]], boxes[rs[j]]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox > 0 and oy > 0:
                    pen += 60 + 40 * min(ox, oy)
        wl = 0.0
        pp = {(p['ref'], p['pad']): (p['x'], p['y']) for r in P for p in P[r]}
        if LOS:
            allp = [p for r in P for p in P[r]]
            rx = np.array([p['x'] for p in allp]); ry = np.array([p['y'] for p in allp])
            hw = np.array([p['w'] / 2 for p in allp]) + LOS_R; hh = np.array([p['h'] / 2 for p in allp]) + LOS_R
            pn = [p['net'] for p in allp]
            for w, a, b in LOS:
                ka, kb = tuple(a.split('.')), tuple(b.split('.'))
                (xa, ya), (xb, yb) = pp[ka], pp[kb]
                d = math.hypot(xb - xa, yb - ya)
                n = max(1, int(d / 0.1))
                t = np.linspace(0, 1, n + 1)
                sx = xa + (xb - xa) * t; sy = ya + (yb - ya) * t
                net = nets.get(ka, '')
                bad = np.array([pn[k] != net for k in range(len(allp))])
                inside = (np.abs(sx[:, None] - rx[None, :]) < hw[None, :]) & (np.abs(sy[:, None] - ry[None, :]) < hh[None, :])
                hit = (inside & bad[None, :]).any(1)
                for k in range(n + 1):
                    if not hit[k]:
                        x, y = sx[k], sy[k]
                        if blocked_net(x, y, net):
                            hit[k] = True
                wl += LOS_W * w * 0.1 * hit.sum()
        for w, a, b in C['links']:
            pa = tuple(C['anchors'][a[1:]]) if a.startswith('@') else pp[tuple(a.split('.'))]
            pb = tuple(C['anchors'][b[1:]]) if b.startswith('@') else pp[tuple(b.split('.'))]
            wl += w * math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        return pen * 10 + wl, pen
    cur, curpen = cost(state)
    best, bestst, bestpen = cur, json.loads(json.dumps(state)), curpen
    T0 = C.get('t0', 30.0)
    for it in range(iters):
        T = T0 * (1 - it / iters) + 0.05
        ref = rng.choice(C['parts'])
        old = list(state[ref])
        r = rng.random()
        if r < 0.15:
            state[ref][2] = rng.choice([0, 90, 180, 270])
        elif r < 0.25:
            other = rng.choice(C['parts'])
            if other != ref:
                state[ref][:2], state[other][:2] = list(state[other][:2]), list(state[ref][:2])
                new, pen = cost(state)
                if new < cur or rng.random() < math.exp((cur - new) / T):
                    cur, curpen = new, pen
                    if new < best:
                        best, bestst, bestpen = new, json.loads(json.dumps(state)), pen
                else:
                    state[ref][:2], state[other][:2] = list(state[other][:2]), list(state[ref][:2])
                continue
        else:
            s = 0.3 + 2.5 * (1 - it / iters)
            state[ref][0] = round((old[0] + rng.gauss(0, s)) / 0.025) * 0.025
            state[ref][1] = round((old[1] + rng.gauss(0, s)) / 0.025) * 0.025
        new, pen = cost(state)
        if new < cur or rng.random() < math.exp((cur - new) / T):
            cur, curpen = new, pen
            if new < best:
                best, bestst, bestpen = new, json.loads(json.dumps(state)), pen
        else:
            state[ref] = old
    res = {r: [side] + v for r, v in bestst.items()}
    res.update(fixed)
    json.dump(res, open(out, 'w'), indent=1)
    print('best cost %.2f penalty %.2f' % (best, bestpen))


if __name__ == '__main__':
    main()
