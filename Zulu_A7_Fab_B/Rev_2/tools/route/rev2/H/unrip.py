"""unrip.py <model.json> <rip.json> <out_seed.json> [nets|ALL] [--margin M] [--trim T] [--skip NET,NET] [--extra plan.json]
The rip copper that still fits: every ripped track / via (rip.json) of the chosen nets is checked EXACTLY against the
ripped model (other nets' copper, clearance as router.clearance, via hole-hole 0.24 incl. drilled pads, board edge).
A via column (same net, x, y) is kept only if every part fits. A track that clashes is split: the parts of its
centreline farther than clearance + MARGIN from the clashing copper survive, cut back a further TRIM where they
border a clash (room for the router's joint), >= 0.15 mm long, each re-checked. --extra adds a plan's copper (router
copper already held, e.g. a checkpoint) to the model as obstacles. v2 defaults: margin 0, trim 0.1 (v1: margin 0.05,
trim 0, which cut needless gaps next to legal neighbours).
The result is a router plan {tracks, vias} meant as --seed (rippable router copper), so the router re-uses the old
route where it still fits and only builds the connector from the moved land to it."""
import json
import math
import os
import sys

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def main():
    args = [a for a in sys.argv[1:]]
    margin, trim = 0.0, 0.1
    skip = {'CHAN10'}
    if '--trim' in args:
        i = args.index('--trim')
        trim = float(args[i + 1])
        del args[i:i + 2]
    extra = None
    if '--extra' in args:
        i = args.index('--extra')
        extra = json.load(open(args[i + 1]))
        del args[i:i + 2]
    if '--margin' in args:
        i = args.index('--margin')
        margin = float(args[i + 1])
        del args[i:i + 2]
    if '--skip' in args:
        i = args.index('--skip')
        skip |= set(args[i + 1].split(','))
        del args[i:i + 2]
    M = json.load(open(args[0]))
    if extra:
        M['tracks'] = M['tracks'] + extra['tracks']
        M['vias'] = M['vias'] + [dict(v, span=span(v)) for v in extra['vias']]
    rip = json.load(open(args[1]))
    out = args[2]
    want = None if len(args) < 4 or args[3] == 'ALL' else set(args[3].split(','))
    W, H = M['board']['w'], M['board']['h']
    ok_net = lambda n: n not in skip and (want is None or n in want)  # noqa: E731

    def items_on(layer):
        for p in M['pads']:
            ls = p['layers'] or (STACK if p['drill'] > 0 else [])
            if layer in ls:
                yield 'p', p
        for t in M['tracks']:
            if t['layer'] == layer:
                yield 't', t
        for v in M['vias']:
            if layer in v['span']:
                yield 'v', v
    cache = {l: list(items_on(l)) for l in STACK}

    def clr(n1, n2, layer):
        return max(R.clearance(n1, layer), R.clearance(n2, layer))

    def gap_pt(k, o, x, y, r):
        if k == 'p':
            return C.pad_point(o, x, y) - r
        if k == 't':
            return C.seg_dist(o['x1'], o['y1'], o['x2'], o['y2'], x, y) - r - o['w'] / 2
        return math.hypot(o['x'] - x, o['y'] - y) - r - o['size'] / 2

    def gap_seg(k, o, s, r):
        if k == 'p':
            return C.pad_seg(o, s) - r
        if k == 't':
            return C.seg_seg(s, (o['x1'], o['y1'], o['x2'], o['y2'])) - r - o['w'] / 2
        return C.seg_dist(s[0], s[1], s[2], s[3], o['x'], o['y']) - r - o['size'] / 2

    def edge_ok(x, y, r):
        if x - r < R.EDGE or y - r < R.EDGE or x + r > W - R.EDGE or y + r > H - R.EDGE:
            return False
        for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
            if abs(x - cx) < 1.2 + r and abs(y - cy) < 1.2 + r:
                return False
        return True

    def seg_ok(t, s):
        for k, o in cache[t['layer']]:
            if o['net'] and o['net'] == t['net']:
                continue
            if gap_seg(k, o, s, t['w'] / 2) < clr(t['net'], o['net'] or '', t['layer']) - 1e-4:
                return False
        return edge_ok(s[0], s[1], t['w'] / 2) and edge_ok(s[2], s[3], t['w'] / 2)

    def pt_ok(t, x, y, extra):
        for k, o in cache[t['layer']]:
            if o['net'] and o['net'] == t['net']:
                continue
            if gap_pt(k, o, x, y, t['w'] / 2) < clr(t['net'], o['net'] or '', t['layer']) + extra - 1e-4:
                return False
        return edge_ok(x, y, t['w'] / 2)

    def via_ok(v):
        sp = span(v)
        for l in sp:
            for k, o in cache[l]:
                if o['net'] and o['net'] == v['net']:
                    continue
                if gap_pt(k, o, v['x'], v['y'], v['size'] / 2) < clr(v['net'], o['net'] or '', l) - 1e-4:
                    return False
        for o in M['vias']:
            if not (set(o['span']) & set(sp)) or math.hypot(o['x'] - v['x'], o['y'] - v['y']) < 1e-6:
                continue
            if math.hypot(o['x'] - v['x'], o['y'] - v['y']) - o['hole'] / 2 - v['hole'] / 2 < R.HOLE_HOLE - 1e-4:
                return False
        for p in M['pads']:
            if p['drill'] > 0 and p['net'] != v['net']:
                if math.hypot(p['x'] - v['x'], p['y'] - v['y']) - p['drill'] / 2 - v['hole'] / 2 < R.HOLE_HOLE - 1e-4:
                    return False
        return edge_ok(v['x'], v['y'], v['size'] / 2)

    cols = {}
    for v in rip['remove_vias']:
        if ok_net(v['net']):
            cols.setdefault((v['net'], round(v['x'], 4), round(v['y'], 4)), []).append(v)
    keep_v, drop_cols = [], []
    for k, vs in cols.items():
        if all(via_ok(v) for v in vs):
            keep_v += [{kk: vv for kk, vv in v.items() if kk != 'span'} | {'from': span(v)[0], 'to': span(v)[-1]} for v in vs]
        else:
            drop_cols.append(k)
    keep_t, split, dropped = [], [], []
    for t in rip['remove']:
        if not ok_net(t['net']):
            continue
        s = (t['x1'], t['y1'], t['x2'], t['y2'])
        if seg_ok(t, s):
            keep_t.append(dict(t))
            continue
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        n = max(1, int(L / 0.025))
        good = [pt_ok(t, t['x1'] + (t['x2'] - t['x1']) * i / n, t['y1'] + (t['y2'] - t['y1']) * i / n, margin)
                for i in range(n + 1)]
        runs, i = [], 0
        while i <= n:
            if good[i]:
                j = i
                while j + 1 <= n and good[j + 1]:
                    j += 1
                runs.append((i, j))
                i = j + 1
            else:
                i += 1
        pieces = []
        k = int(round(trim / (L / n)))
        runs = [(i + (k if i > 0 else 0), j - (k if j < n else 0)) for i, j in runs]
        for i, j in runs:
            if (j - i) * L / n < 0.15:
                continue
            a = (round(t['x1'] + (t['x2'] - t['x1']) * i / n, 4), round(t['y1'] + (t['y2'] - t['y1']) * i / n, 4))
            b = (round(t['x1'] + (t['x2'] - t['x1']) * j / n, 4), round(t['y1'] + (t['y2'] - t['y1']) * j / n, 4))
            if i == 0:
                a = (t['x1'], t['y1'])
            if j == n:
                b = (t['x2'], t['y2'])
            nt = dict(t, x1=a[0], y1=a[1], x2=b[0], y2=b[1])
            if seg_ok(nt, (a[0], a[1], b[0], b[1])):
                pieces.append(nt)
        if pieces:
            split.append((t, pieces))
            keep_t += pieces
        else:
            dropped.append(t)
    print('vias kept %d (%d columns dropped), tracks kept whole %d, split %d, dropped %d' % (
        len(keep_v), len(drop_cols), len(keep_t) - sum(len(p) for _, p in split), len(split), len(dropped)))
    for k in drop_cols:
        print('  drop via column %s %.3f,%.3f' % k)
    for t, ps in split:
        print('  split %s %s (%.3f,%.3f)-(%.3f,%.3f) -> %s' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'],
              ' '.join('(%.3f,%.3f)-(%.3f,%.3f)' % (p['x1'], p['y1'], p['x2'], p['y2']) for p in ps)))
    for t in dropped:
        print('  drop %s %s (%.3f,%.3f)-(%.3f,%.3f)' % (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2']))
    # only copper that joins an island with a pad (or the net's pour) is worth seeding: floating pieces are obstacles
    nt0, nv0 = len(M['tracks']), len(M['vias'])
    Mx = dict(M, tracks=M['tracks'] + keep_t, vias=M['vias'] + [dict(v, span=span(v)) for v in keep_v])
    live_t, live_v = set(), set()
    for gs in C.islands(Mx).values():
        for g in gs:
            live_t |= {i - nt0 for i in g['tracks'] if i >= nt0}
            live_v |= {i - nv0 for i in g['vias'] if i >= nv0}
    print('connected to a pad / pour: %d of %d tracks, %d of %d vias' % (len(live_t), len(keep_t), len(live_v), len(keep_v)))
    keep_t = [t for i, t in enumerate(keep_t) if i in live_t]
    keep_v = [v for i, v in enumerate(keep_v) if i in live_v]
    json.dump({'tracks': keep_t, 'vias': keep_v, 'remove': [], 'remove_vias': []}, open(out, 'w'), indent=0)


if __name__ == '__main__':
    main()
