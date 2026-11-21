"""gaps.py <model.json> [NETS] -- for each open net, the closest pair of points between its islands (any layer):
a quick measure of how long the missing connector is. Plane nets: islands without the pour are listed alone."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import route_conn as C  # noqa: E402


def pts(M, g):
    out = []
    for i in g['pads']:
        p = M['pads'][i]
        out.append((p['x'], p['y'], '%s.%s' % (p['ref'], p['pad']), ','.join(l[:2] for l in p['layers'])))
    for i in g['tracks']:
        t = M['tracks'][i]
        n = max(1, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.1))
        for k in range(n + 1):
            out.append((t['x1'] + (t['x2'] - t['x1']) * k / n, t['y1'] + (t['y2'] - t['y1']) * k / n, 'T', t['layer'][:2]))
    for i in g['vias']:
        v = M['vias'][i]
        out.append((v['x'], v['y'], 'V', v['span'][0][:2] + '>' + v['span'][-1][:2]))
    return out


def main():
    M = json.load(open(sys.argv[1]))
    want = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
    isl = C.islands(M)
    for net, gs in sorted(isl.items()):
        if len(gs) < 2 or (want and net not in want):
            continue
        if net in ('GND', 'VCC3V3'):
            for g in gs:
                if not g['plane']:
                    P = pts(M, g)
                    print('%-12s unplaned island at %s' % (net, ' '.join('%s(%.2f,%.2f)' % (a[2], a[0], a[1]) for a in P if a[2] != 'T')[:200]))
            continue
        P = [pts(M, g) for g in gs]
        for a in range(len(gs)):
            for b in range(a + 1, len(gs)):
                best = min(((math.hypot(p[0] - q[0], p[1] - q[1]), p, q) for p in P[a] for q in P[b]), key=lambda r: r[0])
                d, p, q = best
                print('%-12s isl%d-isl%d %.2f mm  (%.2f,%.2f %s %s) -> (%.2f,%.2f %s %s)' % (net, a, b, d, p[0], p[1], p[2], p[3],
                                                                                    q[0], q[1], q[2], q[3]))


if __name__ == '__main__':
    main()
