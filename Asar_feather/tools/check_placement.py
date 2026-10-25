"""Pad-level clearance check of tools/placement.json (before it goes to Altium): every pair of copper pads
on a shared side (through-hole pads count on both) from different parts and different nets must be at least
0.15 mm apart, and no pad may come within 0.25 mm of the board edge (the USB-C mouth is exempt).
    python tools/check_placement.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PL = json.load(open(os.path.join(HERE, 'placement.json')))['placed']
D = json.load(open(os.path.join(HERE, 'board_dump.json')))
W, H = 50.8, 22.86


def pads_abs(ref):
    v = PL[ref]
    ps = D[ref]['pads']
    if not ps:
        return []
    cx = (min(p['x'] for p in ps) + max(p['x'] for p in ps)) / 2
    cy = (min(p['y'] for p in ps) + max(p['y'] for p in ps)) / 2
    c, s = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}[v['rot']]
    out = []
    for p in ps:
        x, y = p['x'] - cx, p['y'] - cy
        if v['side'] == 'bottom':
            x = -x
        X, Y = v['x'] + x * c - y * s, v['y'] + x * s + y * c
        w, h = (p['dy'], p['dx']) if v['rot'] in (90, 270) else (p['dx'], p['dy'])
        out.append((ref, p['name'], p['net'], X - w / 2, Y - h / 2, X + w / 2, Y + h / 2,
                    {'top', 'bottom'} if p['tht'] else {v['side']}))
    return out


def main():
    allp = [q for r in PL if PL[r]['x'] < 55 for q in pads_abs(r)]
    bad = 0
    for i, a in enumerate(allp):
        for b in allp[i + 1:]:
            if a[0] == b[0] or not (a[7] & b[7]) or (a[2] and a[2] == b[2]):
                continue
            gap = max(b[3] - a[5], a[3] - b[5], b[4] - a[6], a[4] - b[6])
            if gap < 0.15:
                bad += 1
                print('pad clash %s-%s / %s-%s gap %.3f' % (a[0], a[1], b[0], b[1], gap))
    edge = [(q[0], q[1]) for q in allp if q[0] != 'X1' and (q[3] < 0.25 or q[4] < 0.25 or q[5] > W - 0.25 or q[6] > H - 0.25)]
    print('%d parts, %d pads: %d clashes, %d pads near the edge %s' % (
        len({q[0] for q in allp}), len(allp), bad, len(edge), edge[:8]))
    print('PASS' if bad == 0 and not edge else 'FAIL')
    return 0 if bad == 0 and not edge else 1


if __name__ == '__main__':
    sys.exit(main())
