"""Clearance margin of every NEW plan object against other-net copper in the result (SDRAM-Dn patched rules).
judge.drc tolerates 1e-4 mm; Altium does not. Reports objects with margin < 0 (would fail Altium), < 0.0005 and < 0.002.
Also hole-to-hole (shared layer) margins of new vias.   python margins.py <key>..."""
import json
import math
import sys
from collections import defaultdict

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
SYNC = TOOLS + '/route/sync'
sys.path.insert(0, TOOLS)
sys.path.insert(0, TOOLS + '/route/rev2/judge')
import router as R  # noqa: E402
import judge as J  # noqa: E402

R.SDRAM |= {'SDRAM-D%d' % i for i in range(16)}
STACK = J.STACK


def layers(k, o):
    if k == 'p':
        return J.pad_layers(o)
    if k == 't':
        return [o['layer']]
    return o['span']


for key in sys.argv[1:]:
    P = json.load(open('%s/%s/plan_%s.json' % (SYNC, key, key)))
    Rz = json.load(open('%s/judge/%s/result.json' % (SYNC, key)))
    for v in Rz['vias']:
        v['span'] = J.span(v)
    tk = {(t['net'], t['layer'], round(t['w'], 4), round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4)) for t in P['tracks']}
    vk = {(v['net'], round(v['x'], 4), round(v['y'], 4), v['from'], v['to']) for v in P['vias']}
    new = [('t', t) for t in Rz['tracks'] if (t['net'], t['layer'], round(t['w'], 4), round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4)) in tk]
    new += [('v', v) for v in Rz['vias'] if (v['net'], round(v['x'], 4), round(v['y'], 4), v['span'][0], v['span'][-1]) in vk]
    grid = defaultdict(list)
    allo = [('p', p) for p in Rz['pads']] + [('t', t) for t in Rz['tracks']] + [('v', v) for v in Rz['vias']]
    for k, o in allo:
        x0, y0, x1, y1 = J.bbox(k, o)
        for l in layers(k, o):
            for gx in range(int(math.floor((x0 - 0.25) / 0.5)), int(math.floor((x1 + 0.25) / 0.5)) + 1):
                for gy in range(int(math.floor((y0 - 0.25) / 0.5)), int(math.floor((y1 + 0.25) / 0.5)) + 1):
                    grid[(l, gx, gy)].append((k, o))
    worst = []
    for k, o in new:
        x0, y0, x1, y1 = J.bbox(k, o)
        best = None
        seen = set()
        for l in layers(k, o):
            for gx in range(int(math.floor((x0 - 0.25) / 0.5)), int(math.floor((x1 + 0.25) / 0.5)) + 1):
                for gy in range(int(math.floor((y0 - 0.25) / 0.5)), int(math.floor((y1 + 0.25) / 0.5)) + 1):
                    for k2, q in grid.get((l, gx, gy), ()):
                        if q is o or id(q) in seen:
                            continue
                        n1, n2 = o.get('net') or '', q.get('net') or ''
                        if n1 and n1 == n2:
                            continue
                        seen.add(id(q))
                        clr = max(R.clearance(n1, l), R.clearance(n2, l))
                        m = J.gap(k, o, k2, q) - clr
                        if best is None or m < best[0]:
                            best = (m, l, J.desc(k, o), k2, J.desc(k2, q))
        if best:
            worst.append(best)
    # hole-hole margins of new vias (spans sharing a layer, not coincident)
    hh = []
    for k, o in new:
        if k != 'v':
            continue
        for q in Rz['vias']:
            if q is o or not (set(q['span']) & set(o['span'])):
                continue
            c = math.hypot(q['x'] - o['x'], q['y'] - o['y'])
            if c < 1e-6:
                continue
            hh.append((c - q['hole'] / 2 - o['hole'] / 2 - R.HOLE_HOLE, J.desc('v', o), J.desc('v', q)))
        for p in Rz['pads']:
            if p['drill'] > 0 and not (p['net'] and p['net'] == o['net']):
                hh.append((math.hypot(p['x'] - o['x'], p['y'] - o['y']) - p['drill'] / 2 - o['hole'] / 2 - R.HOLE_HOLE, J.desc('v', o), J.desc('p', p)))
    worst.sort(key=lambda w: w[0])
    hh.sort(key=lambda w: w[0])
    print('== %s: %d new objects; clearance margin <0: %d, <0.0005: %d, <0.002: %d, <0.005: %d; min %.5f' % (
        key, len(new), sum(1 for w in worst if w[0] < -1e-9), sum(1 for w in worst if w[0] < 0.0005), sum(1 for w in worst if w[0] < 0.002),
        sum(1 for w in worst if w[0] < 0.005), worst[0][0]))
    print("   negatives:", [("%.2e" % w[0], w[2], w[4]) for w in worst if w[0] < 0][:10])
    for w in worst[:8]:
        print('   %.5f %s | %s | %s %s' % w)
    print('   hole-hole margin <0: %d, <0.002: %d; min %.5f' % (sum(1 for h in hh if h[0] < -1e-9), sum(1 for h in hh if h[0] < 0.002), hh[0][0] if hh else 9))
    for h in hh[:3]:
        print('   %.5f %s | %s' % h)
