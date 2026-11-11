"""Compare the saved board (tools/board_dump.json, re-dumped after placement) with tools/placement.json and run
the pad-clearance check on the AS-PLACED pads (absolute positions from the board, not the plan).
    python tools/verify_placement.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PL = json.load(open(os.path.join(HERE, 'placement.json')))['placed']
D = json.load(open(os.path.join(HERE, 'board_dump.json')))
B = D.pop('_board')            # KiCad imports with an offset origin: shift so the board edge starts at 0, 0
W, H = 50.8, 22.86
_ox, _oy = (B['x0'] + B['x1']) / 2 - W / 2, (B['y0'] + B['y1']) / 2 - H / 2   # edge-line width cancels out
for _c in D.values():
    _c['x'] -= _ox
    _c['y'] -= _oy


def abs_pads(ref):
    c = D[ref]
    import math
    a = math.radians(c['rot'])
    out = []
    for p in c['pads']:
        # KiCad's FP-relative position of a flipped footprint is already in the flipped frame: no mirror here
        x, y = p['x'], p['y']
        X = c['x'] + x * math.cos(a) - y * math.sin(a)
        Y = c['y'] + x * math.sin(a) + y * math.cos(a)
        rot = round((c['rot'] + p['rot']) % 180)
        w, h = (p['dy'], p['dx']) if rot == 90 else (p['dx'], p['dy'])
        out.append((ref, p['name'], p['net'], X - w / 2, Y - h / 2, X + w / 2, Y + h / 2,
                    {'top', 'bottom'} if p['tht'] else {'bottom' if c['bottom'] else 'top'}))
    return out


def main():
    bad = 0
    for ref, v in PL.items():
        c = D[ref]
        ps = abs_pads(ref)
        side = 'bottom' if c['bottom'] else 'top'
        if side != v['side']:
            print('SIDE', ref, side, v['side']); bad += 1
        if ps:
            cx = (min(q[3] for q in ps) + max(q[5] for q in ps)) / 2
            cy = (min(q[4] for q in ps) + max(q[6] for q in ps)) / 2
            # plan stores pad-centre-box centres; compare those
            ccx = (min((q[3] + q[5]) / 2 for q in ps) + max((q[3] + q[5]) / 2 for q in ps)) / 2
            ccy = (min((q[4] + q[6]) / 2 for q in ps) + max((q[4] + q[6]) / 2 for q in ps)) / 2
            if abs(ccx - v['x']) > 0.01 or abs(ccy - v['y']) > 0.01:
                print('POS %s board %.3f,%.3f plan %.3f,%.3f' % (ref, ccx, ccy, v['x'], v['y'])); bad += 1
    allp = [q for r in PL if PL[r]['x'] < 55 for q in abs_pads(r)]
    clash = 0
    for i, a in enumerate(allp):
        for b in allp[i + 1:]:
            if a[0] == b[0] or not (a[7] & b[7]) or (a[2] and a[2] == b[2]):
                continue
            if max(b[3] - a[5], a[3] - b[5], b[4] - a[6], a[4] - b[6]) < 0.15:
                clash += 1
                if clash < 10:
                    print('CLASH', a[:2], b[:2])
    edge = [(q[0], q[1]) for q in allp if q[0] != 'X1' and (q[3] < 0.25 or q[4] < 0.25 or q[5] > W - 0.25 or q[6] > H - 0.25)]
    print('%d parts checked: %d side/position mismatches, %d pad clashes, %d pads near the edge %s' % (
        len(PL), bad, clash, len(edge), edge[:6]))
    ok = bad == 0 and clash == 0 and not edge
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
