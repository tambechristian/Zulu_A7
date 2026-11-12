"""minrip.py <base_moved.json> <model_base.json> <out_rip.json> <out_model.json> [--rip-nets N1,N2]
Strategy F (2026-11-11): a MINIMAL rip for Rev 2. Instead of ripping every track of a moved pad's net inside a
window (rev2_prep rule 1), keep every existing track and via unless its copper actually breaks a rule against a
MOVED pad (new position), judged with route_check's exact geometry:
  track vs pad: gap >= clearance on every shared layer (pads of no net are obstacles for every net);
  via   vs pad: land gap >= clearance on every layer of its span, and hole-to-hole >= 0.24 to a drilled pad (any net).
A clashing TRACK is split: only the stretch closer than clearance + MARGIN to the pad is cut, the rest stays.
A clashing VIA goes with its whole column (same net, x, y). --rip-nets rips every track / via of those nets
(e.g. the USB pair that is hand-routed). Writes the rip as {remove, remove_vias, tracks} (tracks = kept pieces
of split tracks, they are re-added) and the ripped model (router input)."""
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK
MARGIN = 0.01


def pad_layers(p):
    return p['layers'] or (STACK if p['drill'] else [])


def clr(n1, n2, layer):
    return max(R.clearance(n1, layer), R.clearance(n2 or '', layer))


def track_gap(t, p):
    return C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2


def pt_gap(t, p, s):
    x, y = t['x1'] + (t['x2'] - t['x1']) * s, t['y1'] + (t['y2'] - t['y1']) * s
    return C.pad_point(p, x, y) - t['w'] / 2


def bad_interval(t, p, need):
    """[s_lo, s_hi] of the track parameter where the track copper is closer than `need` to pad p (None if never);
    the gap along a line to a convex pad is convex in s, so the bad set is one interval"""
    L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
    if track_gap(t, p) >= need:
        return None
    if L < 1e-9:
        return (0.0, 1.0)
    n = max(4, int(L / 0.002))
    ss = [k / n for k in range(n + 1)]
    g = [pt_gap(t, p, s) for s in ss]
    bad = [k for k in range(n + 1) if g[k] < need]
    if not bad:
        k = min(range(n + 1), key=lambda k: g[k])
        bad = [k]
    lo, hi = bad[0], bad[-1]

    def bis(a, b):                             # a good, b bad -> a boundary on the good side
        for _ in range(40):
            m = (a + b) / 2
            if pt_gap(t, p, m) < need:
                b = m
            else:
                a = m
        return a
    s_lo = 0.0 if lo == 0 else bis(ss[lo - 1], ss[lo])
    s_hi = 1.0 if hi == n else bis(ss[hi + 1], ss[hi])
    return (s_lo, s_hi)


def vrec(v):
    return {'net': v['net'], 'x': v['x'], 'y': v['y'], 'size': v['size'], 'hole': v['hole'],
            'from': v['span'][0], 'to': v['span'][-1]}


def main():
    args = sys.argv[1:]
    rip_nets = set()
    if '--rip-nets' in args:
        k = args.index('--rip-nets')
        rip_nets = set(args[k + 1].split(','))
        del args[k:k + 2]
    B = json.load(open(args[0]))
    O = json.load(open(args[1]))
    moved = [n for o, n in zip(O['pads'], B['pads']) if (o['x'], o['y']) != (n['x'], n['y'])]
    print('%d moved pads' % len(moved))
    rm_t, keep_pieces, rm_v = [], [], set()
    for i, t in enumerate(B['tracks']):
        if t['net'] in rip_nets:
            rm_t.append(i)
            continue
        cuts = []
        for p in moved:
            if t['layer'] not in pad_layers(p):
                continue
            if p['net'] and p['net'] == t['net']:
                continue
            need = clr(t['net'], p['net'], t['layer'])
            if track_gap(t, p) >= need + 1e-4:
                continue
            iv = bad_interval(t, p, need + MARGIN)
            if iv:
                cuts.append(iv)
        if not cuts:
            continue
        rm_t.append(i)
        cuts.sort()
        merged = []
        for a, b in cuts:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        free, s = [], 0.0
        for a, b in merged:
            if a > s:
                free.append((s, a))
            s = max(s, b)
        if s < 1.0:
            free.append((s, 1.0))
        L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
        for a, b in free:
            if (b - a) * L < 0.02:
                continue
            x1, y1 = t['x1'] + (t['x2'] - t['x1']) * a, t['y1'] + (t['y2'] - t['y1']) * a
            x2, y2 = t['x1'] + (t['x2'] - t['x1']) * b, t['y1'] + (t['y2'] - t['y1']) * b
            pc = dict(t, x1=round(x1, 4) if a > 0 else t['x1'], y1=round(y1, 4) if a > 0 else t['y1'],
                      x2=round(x2, 4) if b < 1 else t['x2'], y2=round(y2, 4) if b < 1 else t['y2'])
            ok = all(track_gap(pc, p) >= clr(t['net'], p['net'], t['layer']) + 1e-4 for p in moved
                     if t['layer'] in pad_layers(p) and not (p['net'] and p['net'] == t['net']))
            if ok:
                keep_pieces.append(pc)
            else:
                print('  piece dropped after rounding', t['net'], t['layer'], pc)
    for i, v in enumerate(B['vias']):
        if v['net'] in rip_nets:
            rm_v.add(i)
            continue
        for p in moved:
            pl = pad_layers(p)
            hit = False
            for l in v['span']:
                if l not in pl or (p['net'] and p['net'] == v['net']):
                    continue
                if C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < clr(v['net'], p['net'], l) + 1e-4:
                    hit = True
            if p['drill'] and set(v['span']) & set(pl):
                if math.hypot(v['x'] - p['x'], v['y'] - p['y']) - v['hole'] / 2 - p['drill'] / 2 < R.HOLE_HOLE + 1e-4:
                    hit = True
            if hit:
                rm_v.add(i)
                break
    cols = {(B['vias'][i]['net'], round(B['vias'][i]['x'], 4), round(B['vias'][i]['y'], 4)) for i in rm_v}
    for i, v in enumerate(B['vias']):
        if (v['net'], round(v['x'], 4), round(v['y'], 4)) in cols:
            rm_v.add(i)
    rip = {'remove': [B['tracks'][i] for i in rm_t], 'remove_vias': [vrec(B['vias'][i]) for i in sorted(rm_v)],
           'tracks': keep_pieces, 'vias': []}
    M = dict(B)
    rs = set(rm_t)
    M['tracks'] = [t for i, t in enumerate(B['tracks']) if i not in rs] + keep_pieces
    M['vias'] = [v for i, v in enumerate(B['vias']) if i not in rm_v]
    json.dump(rip, open(args[2], 'w'), indent=0)
    json.dump(M, open(args[3], 'w'))
    print('removed %d tracks (%d pieces kept), %d vias' % (len(rm_t), len(keep_pieces), len(rm_v)))
    print('tracks by net', dict(Counter(B['tracks'][i]['net'] for i in rm_t)))
    print('vias by net', dict(Counter(B['vias'][i]['net'] for i in rm_v)))
    oc = C.open_count(C.islands(M))
    print('open %d on %d nets: %s' % (sum(oc.values()), len(oc), oc))


if __name__ == '__main__':
    main()
