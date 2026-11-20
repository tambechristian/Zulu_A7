"""SOURCE 22ee1dc -> HEAD copper delta in route-model terms, attributed to the commit that last changed each object,
and matched against TARGET (base_cur) the way emit_copper matches removals. Writes delta.json."""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F403

TOL = 0.002


def feature(commit, kd, o):
    x, y = centre(kd, o)
    if commit == '06d9f27':
        return 'dq_series_r'
    if commit == '04819de':
        return 'vip_r108_04819de'
    if commit == '3b1817d':
        return 'hq_s2b_msop'
    if commit == '3e4ee8c':
        if x < 20:
            return 'body_r34'
        if x > 55 and y < 6:
            return 'body_r1'
        if kd == 'T' and o['layer'] == 'Bottom Layer' and 22.15 <= y <= 22.45 and abs(o['x1'] - o['x2']) < 1e-3:
            return 'body_c_row'
        if o['net'] == 'USB5V0':
            return 'antenna_usb5v0'
        return 'body_u4'
    if commit == '427960e':
        return 'u4_via'
    return 'unattributed'


def tmatch(t, r):
    if t['net'] != r['net'] or t['layer'] != r['layer'] or abs(t['w'] - r['w']) >= TOL:
        return False
    a = abs(t['x1'] - r['x1']) < TOL and abs(t['y1'] - r['y1']) < TOL and abs(t['x2'] - r['x2']) < TOL and abs(t['y2'] - r['y2']) < TOL
    b = abs(t['x1'] - r['x2']) < TOL and abs(t['y1'] - r['y2']) < TOL and abs(t['x2'] - r['x1']) < TOL and abs(t['y2'] - r['y1']) < TOL
    return a or b


def vmatch(v, r):
    return v['net'] == r['net'] and abs(v['hole'] - r['hole']) < TOL and abs(v['x'] - r['x']) < TOL and \
        abs(v['y'] - r['y']) < TOL and span(v)[0] == span(r)[0] and span(v)[-1] == span(r)[-1]


def main():
    M = {c: load('src_' + c) for c in CHAIN}
    T = load('tgt_33023787')
    rem, add = mdiff(objs(M[CHAIN[0]]), objs(M[CHAIN[-1]]))
    keys = {k for _, k, _ in rem + add}
    cnt = {k: [0] * len(CHAIN) for k in keys}
    for i, c in enumerate(CHAIN):
        for _, k, _ in objs(M[c]):
            if k in cnt:
                cnt[k][i] += 1

    def last(k, up):
        c, out = cnt[k], None
        for i in range(1, len(c)):
            if (c[i] > c[i - 1]) if up else (c[i] < c[i - 1]):
                out = CHAIN[i]
        return out
    # TARGET index for emit-style matching
    grid = defaultdict(list)
    for kd, k, o in objs(T):
        x, y = centre(kd, o)
        grid[(int(x), int(y))].append((kd, o))

    def tgt_hits(kd, o):
        x, y = centre(kd, o)
        out = []
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for kd2, q in grid.get((int(x) + i, int(y) + j), ()):
                    if kd2 == kd and (tmatch(q, o) if kd == 'T' else vmatch(q, o)):
                        out.append(q)
        return out
    R, A = [], []
    for kd, k, o in rem:
        c = last(k, False)
        hits = tgt_hits(kd, o)
        R.append({'kind': kd, 'commit': c, 'feature': feature(c, kd, o), 'obj': o, 'desc': desc(kd, o),
                  'target_hits': len(hits), 'target_obj': hits[0] if hits else None})
    for kd, k, o in add:
        c = last(k, True)
        hits = tgt_hits(kd, o)
        A.append({'kind': kd, 'commit': c, 'feature': feature(c, kd, o), 'obj': o, 'desc': desc(kd, o),
                  'target_hits': len(hits)})
    dump({'removed': R, 'added': A}, 'delta.json')
    print('removed', len(R), Counter((r['commit'], r['kind']) for r in R))
    print('added', len(A), Counter((r['commit'], r['kind']) for r in A))
    print('removals by target hits', Counter((r['feature'], r['target_hits']) for r in R))
    print('adds already on target', Counter((r['feature'], r['target_hits']) for r in A if r['target_hits']))


if __name__ == '__main__':
    main()
