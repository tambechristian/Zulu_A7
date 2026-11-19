"""Foreign copper hit by the new Top pads, and rip of own nets (independent)."""
import json, math, sys, collections
from v1 import build, MOVES, M0, ext, BC, RC
M, D = build()
moved = set(MOVES) | {'X4'}
PL = {'GND', 'VCC3V3'}
newp = [p for p in M['pads'] if p['ref'] in moved]
own = set(p['net'] for p in M0['pads'] if p['ref'] in moved and p['net']) - PL
own |= set(p['net'] for p in newp if p['net']) - PL
print('own nets (%d):' % len(own), sorted(own))
SDR = set(['A%d' % i for i in range(13)] + ['BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CLK',
           'SDRAM-CS#'] + ['D%d' % i for i in range(16)] + ['SDRAM-D%d' % i for i in range(16)])
def clr(n): return 0.10 if n in SDR else 0.09
T, V = M0['tracks'], M0['vias']
hits = collections.defaultdict(list)
for p in newp:
    for i, t in enumerate(T):
        if t['layer'] != 'Top Layer' or t['net'] == p['net'] and p['net']: continue
        if t['net'] in own: continue
        d = RC.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2
        if d < clr(t['net']) - 1e-6:
            hits[('T', i)].append((p['ref'] + '.' + p['pad'], p['net'], round(d, 3)))
    for j, v in enumerate(V):
        if v['net'] in own or (v['net'] == p['net'] and p['net']): continue
        if 'Top Layer' not in v['span']: continue
        d = RC.pad_point(p, v['x'], v['y']) - v['size'] / 2
        if d < clr(v['net']) - 1e-6:
            hits[('V', j)].append((p['ref'] + '.' + p['pad'], p['net'], round(d, 3)))
L = lambda t: math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
bynet = collections.defaultdict(lambda: [0, 0.0, 0])
for (k, i), h in hits.items():
    o = T[i] if k == 'T' else V[i]
    if k == 'T': bynet[o['net']][0] += 1; bynet[o['net']][1] += L(o)
    else: bynet[o['net']][2] += 1
print('foreign copper conflicting with new Top pads (net: tracks, mm, vias):')
for n, v in sorted(bynet.items()): print('  %-14s %d %.2f %d' % (n, v[0], v[1], v[2]))
for (k, i), h in sorted(hits.items()):
    o = T[i] if k == 'T' else V[i]
    if k == 'V': print('  via', o['net'], o['x'], o['y'], o['span'][0], o['span'][-1], 'hole', o['hole'], h[:2])
# own-net copper totals
ot = [t for t in T if t['net'] in own]; ov = [v for v in V if v['net'] in own]
print('own nets whole: %.1f mm tracks, %d vias' % (sum(map(L, ot)), len(ov)))
for n in sorted(own, key=lambda n: -sum(L(t) for t in T if t['net'] == n)):
    print('   %-14s %.1f mm %d vias' % (n, sum(L(t) for t in T if t['net'] == n), sum(1 for v in V if v['net'] == n)))
