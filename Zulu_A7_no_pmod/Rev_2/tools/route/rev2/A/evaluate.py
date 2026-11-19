"""evaluate.py <base_moved.json> <composed_plan.json>
Applies the plan to base, reports: via counts by type (added/removed), track counts, added track length,
through vias whose land overlaps any SMD pad, microvias whose land overlaps an SMD pad, USB pair lengths/coupling."""
import json
import math
import sys

B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2]))


def span(v):
    return tuple(v['span']) if 'span' in v else (v['from'], v['to'])


def kind(v):
    s = span(v)
    if s == ('Top Layer', 'Bottom Layer') or s == ('Bottom Layer', 'Top Layer'):
        return 'through %.2f/%.2f' % (v['size'], v['hole'])
    return '%s>%s %.2f/%.2f' % (s[0], s[1], v['size'], v['hole'])


def tkey(t):
    return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))


rem = {tkey(t) for t in P.get('remove', [])}
remv = {(v['net'], round(v['x'], 4), round(v['y'], 4)) for v in P.get('remove_vias', [])}
tracks = [t for t in B['tracks'] if tkey(t) not in rem] + P.get('tracks', [])
L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])  # noqa: E731
print('tracks added', len(P.get('tracks', [])), 'removed', len(P.get('remove', [])),
      'added length %.2f mm, removed length %.2f mm' % (sum(map(L, P.get('tracks', []))), sum(map(L, P.get('remove', [])))))
from collections import Counter
print('vias added', dict(Counter(kind(v) for v in P.get('vias', []))))
print('vias removed', dict(Counter(kind(v) for v in P.get('remove_vias', []))))

smd = [p for p in B['pads'] if not p['drill']]


def overlap(p, v):
    r = v['size'] / 2
    if p['shape'] in ('round', 'circle', 'ellipse') and abs(p['w'] - p['h']) < 1e-6:
        return math.hypot(v['x'] - p['x'], v['y'] - p['y']) < r + p['w'] / 2 - 1e-6
    dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0)
    dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
    return math.hypot(dx, dy) < r - 1e-6


thr, mic = [], []
for v in P.get('vias', []):
    s = span(v)
    for p in smd:
        if p['layers'][0] not in s and not (s[0] == 'Top Layer' and s[1] == 'Bottom Layer' or s[1] == 'Top Layer'):
            pass
        if not overlap(p, v):
            continue
        if 'through' in kind(v):
            thr.append((v['net'], v['x'], v['y'], p['ref'], p['pad']))
        elif p['layers'][0] in s:
            mic.append((v['net'], v['x'], v['y'], kind(v), p['ref'], p['pad']))
print('through vias in SMD pads', len(thr), thr)
print('microvias in SMD pads', len(mic), mic)

for n in ('USB_D_P', 'USB_D_N'):
    ts = [t for t in tracks if t['net'] == n]
    print(n, 'length %.3f' % sum(map(L, ts)), 'layers', set(t['layer'] for t in ts), 'widths', set(t['w'] for t in ts),
          'vias', sum(1 for v in P.get('vias', []) if v['net'] == n))
# coupled length: sample P, count samples within gap 0.15+-0.02 (centre 0.30) of an N track
tp = [t for t in tracks if t['net'] == 'USB_D_P']
tn = [t for t in tracks if t['net'] == 'USB_D_N']


def dseg(x, y, t):
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    l2 = dx * dx + dy * dy
    k = 0 if l2 == 0 else max(0, min(1, ((x - t['x1']) * dx + (y - t['y1']) * dy) / l2))
    return math.hypot(x - t['x1'] - k * dx, y - t['y1'] - k * dy)


cp = 0
for t in tp:
    n = max(1, int(L(t) / 0.01))
    for k in range(n):
        x = t['x1'] + (t['x2'] - t['x1']) * (k + .5) / n
        y = t['y1'] + (t['y2'] - t['y1']) * (k + .5) / n
        if tn and abs(min(dseg(x, y, u) for u in tn) - 0.30) <= 0.02:
            cp += L(t) / n
print('USB coupled length (P side, centre 0.30+-0.02) %.3f' % cp)
