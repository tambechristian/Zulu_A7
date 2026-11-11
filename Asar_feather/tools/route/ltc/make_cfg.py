"""Writes the place_opt config for one board: python make_cfg.py <ripped model> <board: asar|fabb> <region x0 y0 x1 y1> <out>"""
import json, sys
M = json.load(open(sys.argv[1])); board = sys.argv[2]; region = [float(v) for v in sys.argv[3:7]]; out = sys.argv[7]
net = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
def pad(ref, n):
    c = [k[1] for k, v in net.items() if k[0] == ref and v == n]
    assert c, (ref, n)
    return '%s.%s' % (ref, c[0])
U = lambda n: [k[1] for k, v in net.items() if k[0] == 'U8' and v == n]
L = []
def link(w, a, b): L.append([w, a, b])
# switch nodes and power loops (weight 10)
for n, l in (('PWR_SW1', 'L3'), ('PWR_SW2', 'L2'), ('PWR_SWAB3', 'L1'), ('PWR_SWCD3', 'L1'), ('PWR_SW', 'L8')):
    link(10, 'U8.' + U(n)[0], pad(l, n))
link(10, 'U8.24', pad('L8', 'VU'))
for c, pin in (('C149', '5'), ('C160', '18'), ('C148', '11'), ('C147', '24')):
    link(10, 'U8.' + pin, pad(c, 'VU')); link(4, 'U8.29', pad(c, 'GND'))
link(10, 'U8.12', pad('C80', 'VCC3V3')); link(4, 'U8.29', pad('C80', 'GND'))
link(10, 'U8.25', pad('C150', 'USB5V0')); link(4, 'U8.29', pad('C150', 'GND'))
link(8, pad('L3', 'VCC1V0'), pad('C84', 'VCC1V0')); link(8, pad('L2', 'VCC1V8'), pad('C82', 'VCC1V8'))
link(5, 'U8.23', pad('C151', 'VBATT'))
# feedback / program (weight 4)
for n in ('PWR_FB1', 'PWR_FB2', 'PWR_FB3', 'PWR_VC3', 'PWR_CLPROG', 'PWR_PROG'):
    hub = 'U8.' + U(n)[0]
    for (r, p), v in net.items():
        if v == n and r != 'U8':
            link(4, hub, '%s.%s' % (r, p))
for n in ('PWR_FB3_FF', 'PWR_VC3_RC'):
    ps = ['%s.%s' % k for k, v in net.items() if v == n]
    link(3, ps[0], ps[1])
link(1, pad('R111', 'VCC1V0'), pad('L3', 'VCC1V0')); link(1, pad('C162', 'VCC1V0'), pad('L3', 'VCC1V0'))
link(1, pad('R113', 'VCC1V8'), pad('L2', 'VCC1V8')); link(1, pad('C163', 'VCC1V8'), pad('L2', 'VCC1V8'))
link(1, pad('R115', 'VCC3V3'), pad('C80', 'VCC3V3')); link(1, pad('R118', 'VCC3V3'), pad('C80', 'VCC3V3'))
link(2, pad('C78', 'VU'), pad('L8', 'VU')); link(1, pad('R108', 'VU'), pad('L8', 'VU'))
link(1, 'U8.15', pad('R107', 'PWR_PGOODALL'))
A = {}
P = {(p['ref'], p['pad']): (p['x'], p['y']) for p in M['pads']}
def anchor(name, ref, pd):
    A[name] = list(P[(ref, pd)])
anchor('USB', 'X1', '1') ; anchor('X4BAT', 'X4', '1'); anchor('X2BAT', 'X2', '17') if board == 'asar' else None
anchor('LD3A', 'LD3', 'A'); anchor('LD4A', 'LD4', 'A'); anchor('LD4K', 'LD4', 'K')
link(2, pad('C150', 'USB5V0'), '@USB'); link(2, pad('C151', 'VBATT'), '@X4BAT')
if board == 'asar':
    link(1, pad('C151', 'VBATT'), '@X2BAT'); anchor('EN', 'X2', '18'); link(1, 'U8.28', '@EN')
link(1, pad('R107', 'PWR_PGOODALL'), '@LD3A'); link(1, pad('R108', 'LD4_A'), '@LD4A'); link(1, 'U8.21', '@LD4K')
v10 = [k for k, v in net.items() if v == 'VCC1V0' and k[0] in ('C85', 'C86', 'C89') ]
v18 = [k for k, v in net.items() if v == 'VCC1V8' and k[0] in ('C93', 'C144', 'C95', 'C96')]
if v10: A['V10'] = list(P[v10[0]]); link(2, pad('L3', 'VCC1V0'), '@V10')
if v18: A['V18'] = list(P[v18[0]]); link(2, pad('L2', 'VCC1V8'), '@V18')
parts = ['U8', 'L1', 'L2', 'L3', 'L8', 'C78', 'C80', 'C82', 'C84', 'C147', 'C148', 'C149', 'C150', 'C151', 'C160', 'C161',
         'C162', 'C163', 'C164', 'C165', 'C166', 'R102', 'R103', 'R107', 'R108', 'R111', 'R112', 'R113', 'R114', 'R115',
         'R116', 'R117', 'R118']
json.dump({'region': region, 'side': 'B', 'parts': parts, 'anchors': A, 'links': L}, open(out, 'w'), indent=1)
print(len(L), 'links', A)
