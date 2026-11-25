"""merge_gnd.py IN OUT -- collapse the router's two-offset GND plane-tie via stacks into one co-located stack.

A: Top-L2/L2-L3 at (25.375,21.525) move to (25.375,21.5); the L3 jog between them is deleted.
B: the L3-L4 via at (51.4,11.4) moves to (51.375,11.425), the L4 track end follows it; the L3 jog is deleted."""
import json
import sys

plan = json.load(open(sys.argv[1]))
T, V = plan['tracks'], plan['vias']


def near(a, b, tol=1e-6):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def drop_track(layer, p, q):
    global T
    n = len(T)
    T = [t for t in T if not (t['net'] == 'GND' and t['layer'] == layer and
                              ((near((t['x1'], t['y1']), p) and near((t['x2'], t['y2']), q)) or
                               (near((t['x1'], t['y1']), q) and near((t['x2'], t['y2']), p))))]
    assert n - len(T) == 1, ('track', layer, p, q)


def move_vias(src, dst, spans=None):
    k = 0
    for v in V:
        if v['net'] == 'GND' and near((v['x'], v['y']), src) and (spans is None or (v['from'], v['to']) in spans):
            v['x'], v['y'] = dst
            k += 1
    return k


# A
drop_track('L3-SIG', (25.375, 21.5), (25.375, 21.525))
assert move_vias((25.375, 21.525), (25.375, 21.5)) == 2
# B
drop_track('L3-SIG', (51.4, 11.4), (51.375, 11.425))
assert move_vias((51.4, 11.4), (51.375, 11.425), {('L3-SIG', 'L4-SIG')}) == 1
k = 0
for t in T:
    if t['net'] == 'GND' and t['layer'] == 'L4-SIG':
        for a, b in (('x1', 'y1'), ('x2', 'y2')):
            if near((t[a], t[b]), (51.4, 11.4)):
                t[a], t[b] = 51.375, 11.425
                k += 1
assert k == 1, k
plan['tracks'] = T
json.dump(plan, open(sys.argv[2], 'w'))
print('merged')
