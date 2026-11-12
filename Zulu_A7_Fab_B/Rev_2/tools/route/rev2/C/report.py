"""Strategy C report: counts, via kinds, vias in SMD pads, USB pair coupling. python report.py <base_moved> <plan>"""
import json, math, sys
SP = lambda v: v['span'] if 'span' in v else [v['from'], v['to']]
from collections import Counter
B = json.load(open(sys.argv[1])); P = json.load(open(sys.argv[2]))
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
def key(t): return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))
def vkey(v): return (v['net'], round(v['x'], 4), round(v['y'], 4), tuple(SP(v)))
def kind(v):
    s = tuple(SP(v)); s = (s[0], s[-1]) if len(s) > 2 else s; return {('Top Layer', 'Bottom Layer'): 'through', ('L3-SIG', 'L4-SIG'): 'buried'}.get(s, 'laser ' + '-'.join(x.split('-')[0].replace(' Layer', '') for x in s))
rem = set(key(t) for t in P.get('remove', [])); remv = set(vkey(v) for v in P.get('remove_vias', []))
tracks = [t for t in B['tracks'] if key(t) not in rem] + P.get('tracks', [])
vias = [v for v in B['vias'] if vkey(v) not in remv] + P.get('vias', [])
L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
print('tracks added', len(P.get('tracks', [])), 'removed', len(P.get('remove', [])), 'added length %.2f mm' % sum(map(L, P.get('tracks', []))), 'removed length %.2f' % sum(L(t) for t in B['tracks'] if key(t) in rem))
print('vias added', dict(Counter(kind(v) for v in P.get('vias', []))), 'removed', dict(Counter(kind(v) for v in B['vias'] if vkey(v) in remv)))
def span_layers(v):
    i, j = STACK.index(SP(v)[0]), STACK.index(SP(v)[-1]); return STACK[min(i, j):max(i, j) + 1]
def overlap(v, p):
    r = v['size'] / 2
    if p['shape'] in ('round', 'circle', 'ellipse') and abs(p['w'] - p['h']) < 1e-6:
        return math.hypot(v['x'] - p['x'], v['y'] - p['y']) < r + p['w'] / 2 - 1e-6
    dx = max(abs(v['x'] - p['x']) - p['w'] / 2, 0); dy = max(abs(v['y'] - p['y']) - p['h'] / 2, 0)
    return math.hypot(dx, dy) < r - 1e-6
smd = [p for p in B['pads'] if not p['drill']]
for label, vs in (('ALL board', vias), ('NEW', P.get('vias', []))):
    th = []; mic = []
    for v in vs:
        for p in smd:
            if set(p['layers']) & set(span_layers(v)) and overlap(v, p):
                (th if kind(v) == 'through' else mic).append('%s %s.%s(%s) at %.3f,%.3f' % (kind(v), p['ref'], p['pad'], p['net'], v['x'], v['y']))
    print(label, 'through-vias-in-SMD-pads', len(th), th[:20]); print(label, 'microvias-in-SMD-pads', len(mic), mic if label == 'NEW' else mic[:0])
U = {n: [t for t in tracks if t['net'] == n] for n in ('USB_D_P', 'USB_D_N')}
for n, ts in U.items():
    print(n, 'length %.3f' % sum(map(L, ts)), 'layers', dict(Counter(t['layer'] for t in ts)), 'widths', sorted(set(t['w'] for t in ts)), 'vias', sum(v['net'] == n for v in vias))
lp, ln = (sum(map(L, U[n])) for n in ('USB_D_P', 'USB_D_N')); print('USB mismatch %.3f' % abs(lp - ln))
cpl = 0
for a in U['USB_D_P']:
    la = L(a)
    if la < 1e-6: continue
    ux, uy = (a['x2'] - a['x1']) / la, (a['y2'] - a['y1']) / la
    best = 0
    for b in U['USB_D_N']:
        if b['layer'] != a['layer'] or L(b) < 1e-6: continue
        bx, by = (b['x2'] - b['x1']) / L(b), (b['y2'] - b['y1']) / L(b)
        if abs(ux * by - uy * bx) > 0.02: continue
        d = abs((b['x1'] - a['x1']) * uy - (b['y1'] - a['y1']) * ux)
        pitch = (a['w'] + b['w']) / 2 + 0.15
        if abs(d - pitch) > 0.02: continue
        s1 = (b['x1'] - a['x1']) * ux + (b['y1'] - a['y1']) * uy; s2 = (b['x2'] - a['x1']) * ux + (b['y2'] - a['y1']) * uy
        best += max(0, min(la, max(s1, s2)) - max(0, min(s1, s2)))
    cpl += min(best, la)
print('USB coupled length %.3f (P-side, pitch 0.30 +-0.02)' % cpl)
