"""analyze.py <base_moved.json> <composed_plan.json>
Counts, via-in-pad audit (through / microvia lands over SMD pads), USB pair lengths + coupling, added track length."""
import json
import math
import sys
from collections import Counter

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2]))


def tk(t):
    return (t['net'], t['layer'], frozenset({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}))


def vfrom(v):
    return v.get('from') or v['span'][0], v.get('to') or v['span'][-1]


def vk(v):
    f, t = vfrom(v)
    return (v['net'], round(v['x'], 3), round(v['y'], 3), f, t)


def kind(v):
    f, t = vfrom(v)
    if f == 'Top Layer' and t == 'Bottom Layer':
        return 'through'
    if {f, t} == {'L3-SIG', 'L4-SIG'}:
        return 'buried L3-L4'
    return 'laser %s-%s' % (f.split('-')[0].replace(' Layer', ''), t.split('-')[0].replace(' Layer', ''))


L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])  # noqa: E731
print('plan: add %d tracks, %d vias; remove %d tracks, %d vias' % (len(P['tracks']), len(P['vias']), len(P['remove']),
                                                                    len(P['remove_vias'])))
print('vias added by type', dict(Counter(kind(v) for v in P['vias'])))
print('vias removed by type', dict(Counter(kind(v) for v in P['remove_vias'])))
print('added track length %.2f mm, removed %.2f mm' % (sum(map(L, P['tracks'])), sum(map(L, P['remove']))))

rt = {tk(t) for t in P['remove']}
rv = {vk(v) for v in P['remove_vias']}
tracks = [t for t in B['tracks'] if tk(t) not in rt] + P['tracks']
vias = [v for v in B['vias'] if vk(v) not in rv] + P['vias']


def overlap(v, p):
    dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0)
    dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
    if p['shape'] == 'circle':
        return math.hypot(v['x'] - p['x'], v['y'] - p['y']) < v['size'] / 2 + p['w'] / 2
    return math.hypot(dx, dy) < v['size'] / 2


smd = [p for p in B['pads'] if not p['drill']]
for label, vs in (('ADDED', P['vias']), ('ALL (final board)', vias)):
    th, mv = [], []
    for v in vs:
        f, t = vfrom(v)
        span = STACK[STACK.index(f):STACK.index(t) + 1]
        for p in smd:
            if p['layers'][0] in span and overlap(v, p):
                (th if kind(v) == 'through' else mv).append('%s %s.%s(%s) @%.3f,%.3f %s' % (
                    kind(v), p['ref'], p['pad'], p['net'], v['x'], v['y'], 'same-net' if p['net'] == v['net'] else 'OTHER-NET'))
    print('%s: through-vias-in-SMD-pads %d %s' % (label, len(th), th))
    print('%s: microvias-in-SMD-pads %d' % (label, len(mv)))
    for m in sorted(set(mv)):
        print('   ', m)

usb = {n: [t for t in tracks if t['net'] == n] for n in ('USB_D_P', 'USB_D_N')}
for n, ts in usb.items():
    print('%s: %d tracks, length %.3f mm, layers %s, vias %d' % (n, len(ts), sum(map(L, ts)), sorted({t['layer'] for t in ts}),
                                                              sum(1 for v in vias if v['net'] == n)))
lp, ln = sum(map(L, usb['USB_D_P'])), sum(map(L, usb['USB_D_N']))
print('USB mismatch %.3f mm' % abs(lp - ln))


def coupled(a, b, pitch=0.30, tol=0.03):
    """length of a parallel to b at centre distance pitch +- tol (projection overlap)"""
    ax, ay = a['x2'] - a['x1'], a['y2'] - a['y1']
    la = math.hypot(ax, ay)
    bx, by = b['x2'] - b['x1'], b['y2'] - b['y1']
    lb = math.hypot(bx, by)
    if la < 1e-6 or lb < 1e-6 or abs(ax * by - ay * bx) / (la * lb) > 0.02:
        return 0
    ux, uy = ax / la, ay / la
    d = abs((b['x1'] - a['x1']) * uy - (b['y1'] - a['y1']) * ux)
    if abs(d - pitch) > tol:
        return 0
    s1 = (b['x1'] - a['x1']) * ux + (b['y1'] - a['y1']) * uy
    s2 = (b['x2'] - a['x1']) * ux + (b['y2'] - a['y1']) * uy
    lo, hi = max(0, min(s1, s2)), min(la, max(s1, s2))
    return max(0, hi - lo)


cp = sum(coupled(a, b) for a in usb['USB_D_P'] for b in usb['USB_D_N'] if a['layer'] == b['layer'])
print('USB coupled length (0.30 pitch, same layer) %.3f mm' % cp)
