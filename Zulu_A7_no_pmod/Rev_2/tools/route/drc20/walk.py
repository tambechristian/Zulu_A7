"""Walk a dead branch back from an Altium Net Antenna to its first real junction (2026-11-19). READ-ONLY.

    python tools/route/drc20/walk.py

Joins (TOL 0.02 mm): a track end on a pad/via copper of a shared layer, on another track's end or body on its layer;
vias of one net at the same place stack. From the antenna object, step to the single other neighbour; stop at the
first object with two or more onward neighbours (a junction) or at a pad. Prints every step.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(os.path.dirname(HERE), 'illustration', 'base.json')))
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
TOL = 0.02


def segd(px, py, t):
    x1, y1, x2, y2 = t['x1'], t['y1'], t['x2'], t['y2']
    dx, dy = x2 - x1, y2 - y1
    L = dx * dx + dy * dy
    k = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - k * dx, py - y1 - k * dy)


def touches(a, b):
    ka, A = a
    kb, B = b
    if ka == 'p' and kb == 'p':
        return False
    if ka != 't' and kb == 't':
        return touches(b, a)
    if ka == 'p' and kb == 'v':
        return touches(b, a)
    if ka == 't':
        ends = ((A['x1'], A['y1']), (A['x2'], A['y2']))
        if kb == 't':
            if A['layer'] != B['layer']:
                return False
            return any(segd(x, y, B) <= TOL for x, y in ends) or \
                any(segd(x, y, A) <= TOL for x, y in ((B['x1'], B['y1']), (B['x2'], B['y2'])))
        if kb == 'v':
            return A['layer'] in B['span'] and any(math.hypot(x - B['x'], y - B['y']) <= B['size'] / 2 for x, y in ends)
        L = B['layers'] or STACK
        return A['layer'] in L and any(abs(x - B['x']) <= B['w'] / 2 + TOL and abs(y - B['y']) <= B['h'] / 2 + TOL for x, y in ends)
    if ka == 'v' and kb == 'v':
        return bool(set(A['span']) & set(B['span'])) and math.hypot(A['x'] - B['x'], A['y'] - B['y']) <= TOL
    L = B['layers'] or STACK
    return any(l in L for l in A['span']) and abs(A['x'] - B['x']) <= B['w'] / 2 and abs(A['y'] - B['y']) <= B['h'] / 2


def name(o):
    k, A = o
    if k == 't':
        return 'track %-12s (%.4f,%.4f)-(%.4f,%.4f) w%.4f' % (A['layer'], A['x1'], A['y1'], A['x2'], A['y2'], A['w'])
    if k == 'v':
        return 'via   %s..%s (%.4f,%.4f) %.2f' % (A['span'][0], A['span'][-1], A['x'], A['y'], A['size'])
    return 'pad   %s-%s' % (A['ref'], A['pad'])


def walk(net, start):
    objs = [('t', t) for t in M['tracks'] if t['net'] == net] + [('v', v) for v in M['vias'] if v['net'] == net] + \
           [('p', p) for p in M['pads'] if p['net'] == net]
    nb = {i: [j for j in range(len(objs)) if j != i and touches(objs[i], objs[j])] for i in range(len(objs))}
    cur = [i for i, o in enumerate(objs) if start(o)]
    assert len(cur) == 1, [name(objs[i]) for i in cur]
    cur, seen, path = cur[0], set(), []
    while True:
        seen.add(cur)
        path.append(cur)
        rest = [j for j in nb[cur] if j not in seen]
        print('   %-60s neighbours %d, onward %d' % (name(objs[cur]), len(nb[cur]), len(rest)))
        if objs[cur][0] == 'p' or len(rest) != 1:
            break
        nxt = rest[0]
        if len([j for j in nb[nxt] if j not in seen]) >= 2 or objs[nxt][0] == 'p':
            print('   stop before %s (junction, %d onward)' % (name(objs[nxt]), len([j for j in nb[nxt] if j not in seen])))
            break
        cur = nxt
    return [objs[i] for i in path]


out = {}
print('USB5V0 from the Top stub at 34.325')
out['USB5V0'] = walk('USB5V0', lambda o: o[0] == 't' and abs(o[1]['x1'] - 32.9) < 1e-3 and abs(o[1]['x2'] - 34.325) < 1e-3)
print('PROG# from the L3-L4 via at (50.05, 13.75)')
out['PROG#'] = walk('PROG#', lambda o: o[0] == 't' and o[1]['layer'] == 'L3-SIG' and abs(o[1]['y1'] - 13.625) < 1e-3 and abs(o[1]['x1'] - 50.05) < 1e-3)
print('FLASH-D02 from the L5-Bottom via at (51.05, 13.55)')
out['FLASH-D02a'] = walk('FLASH-D02', lambda o: o[0] == 't' and o[1]['layer'] == 'Bottom Layer' and abs(o[1]['x1'] - 50.95) < 1e-3 and abs(o[1]['y1'] - 13.45) < 1e-3)
print('CLK-12M-FPGA from the L4-L5 via at (53.2, 12.7)')
out['CLK'] = walk('CLK-12M-FPGA', lambda o: o[0] == 't' and o[1]['layer'] == 'L4-SIG' and abs(o[1]['x1'] - 53.1) < 1e-3 and abs(o[1]['y1'] - 12.8) < 1e-3)
print('FLASH-D02 from the L2-L3 via at (55.7, 13.3)')
out['FLASH-D02b'] = walk('FLASH-D02', lambda o: o[0] == 't' and o[1]['layer'] == 'L3-SIG' and abs(o[1]['x1'] - 55.6) < 1e-3 and abs(o[1]['y1'] - 13.3) < 1e-3)
json.dump({k: [dict(kind=a, **b) for a, b in v] for k, v in out.items()}, open(os.path.join(HERE, 'walk.json'), 'w'), indent=1)
