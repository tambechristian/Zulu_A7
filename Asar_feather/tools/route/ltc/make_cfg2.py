"""place_opt config for the LTC3556 + U7 SC189A block (2026-11-10, VCC1V0 back on U7):
    python make_cfg2.py <ripped model> <asar|fabb> x0 y0 x1 y1 <out> [los_min_w]

Weights: switch nodes and input/output loops 30 (line-of-sight checked with los_min_w), the U7 loop (VIN cap, LX ->
L3, L3 -> C84) 30, Buck1 slot (SW1 -> L9 -> C168) 10, feedback/program parts 4, rails to their consumers 1-2.
"""
import json
import sys

M = json.load(open(sys.argv[1]))
board = sys.argv[2]
region = [float(v) for v in sys.argv[3:7]]
out = sys.argv[7]
los = float(sys.argv[8]) if len(sys.argv) > 8 else 24
net = {(p['ref'], p['pad']): p['net'] for p in M['pads']}


def pad(ref, n):
    c = [k[1] for k, v in net.items() if k[0] == ref and v == n]
    assert c, (ref, n)
    return '%s.%s' % (ref, c[0])


U = lambda n: [k[1] for k, v in net.items() if k[0] == 'U8' and v == n]   # noqa: E731
L = []


def link(w, a, b):
    L.append([w, a, b])


# LTC3556 switch nodes (U8.4 SW1 is now the unloaded Buck1 slot through L9)
for n, ind, w in (('PWR_SW2', 'L2', 30), ('PWR_SWAB3', 'L1', 30), ('PWR_SWCD3', 'L1', 30), ('PWR_SW', 'L8', 30),
                  ('PWR_SW1', 'L9', 10)):
    link(w, 'U8.' + U(n)[0], pad(ind, n))
link(30, 'U8.24', pad('L8', 'VU'))
link(10, pad('L9', 'PWR_FB1'), pad('C168', 'PWR_FB1'))
link(4, 'U8.6', pad('C168', 'PWR_FB1'))
# LTC3556 input caps (VIN1 C167, VIN2 C160, VIN3 C148, VOUT C147) and their GND to the exposed pad
for c, pin in (('C167', '5'), ('C160', '18'), ('C148', '11'), ('C147', '24')):
    link(30, 'U8.' + pin, pad(c, 'VU'))
    link(4, 'U8.29', pad(c, 'GND'))
link(30, 'U8.12', pad('C80', 'VCC3V3'))
link(4, 'U8.29', pad('C80', 'GND'))
link(30, 'U8.25', pad('C150', 'USB5V0'))
link(4, 'U8.29', pad('C150', 'GND'))
link(24, pad('L2', 'VCC1V8'), pad('C82', 'VCC1V8'))
link(5, 'U8.23', pad('C151', 'VBATT'))
# U7 SC189A: VIN cap, LX -> L3, L3 -> C84, VOUT sense, GND
link(30, 'U7.1', pad('C149', 'VU'))
link(10, 'U7.2', pad('C149', 'GND'))
link(30, 'U7.5', pad('L3', 'NetL3_1'))
link(24, pad('L3', 'VCC1V0'), pad('C84', 'VCC1V0'))
link(4, 'U7.4', pad('C84', 'VCC1V0'))
link(10, 'U7.2', pad('C84', 'GND'))
link(2, pad('C149', 'VU'), 'U8.24')                     # U7 takes VU from the LTC3556 VOUT
link(2, 'U7.3', 'U8.28')                                 # EN with ENALL
# feedback / program
for n in ('PWR_FB2', 'PWR_FB3', 'PWR_VC3', 'PWR_CLPROG', 'PWR_PROG'):
    hub = 'U8.' + U(n)[0]
    for (r, p), v in net.items():
        if v == n and r != 'U8':
            link(4, hub, '%s.%s' % (r, p))
for n in ('PWR_FB3_FF', 'PWR_VC3_RC'):
    ps = ['%s.%s' % k for k, v in net.items() if v == n]
    link(3, ps[0], ps[1])
link(1, pad('R113', 'VCC1V8'), pad('L2', 'VCC1V8'))
link(1, pad('C163', 'VCC1V8'), pad('L2', 'VCC1V8'))
link(1, pad('R115', 'VCC3V3'), pad('C80', 'VCC3V3'))
link(1, pad('R118', 'VCC3V3'), pad('C80', 'VCC3V3'))
link(2, pad('C78', 'VU'), pad('L8', 'VU'))
link(1, pad('R108', 'VU'), pad('L8', 'VU'))
link(1, 'U8.15', pad('R107', 'PWR_PGOODALL'))
A = {}
P = {(p['ref'], p['pad']): (p['x'], p['y']) for p in M['pads']}


def anchor(name, ref, pd):
    A[name] = list(P[(ref, pd)])


anchor('USB', 'X1', '1')
anchor('X4BAT', 'X4', '1')
if board == 'asar':
    anchor('X2BAT', 'X2', '17')
    anchor('EN', 'X2', '18')
    link(1, 'U8.28', '@EN')
anchor('LD3A', 'LD3', 'A')
anchor('LD4A', 'LD4', 'A')
anchor('LD4K', 'LD4', 'K')
link(2, pad('C150', 'USB5V0'), '@USB')
link(2, pad('C151', 'VBATT'), '@X4BAT')
if board == 'asar':
    link(1, pad('C151', 'VBATT'), '@X2BAT')
link(1, pad('R107', 'PWR_PGOODALL'), '@LD3A')
link(1, pad('R108', 'LD4_A'), '@LD4A')
link(1, 'U8.21', '@LD4K')
v10 = [k for k, v in net.items() if v == 'VCC1V0' and k[0] in ('C85', 'C86', 'C89')]
v18 = [k for k, v in net.items() if v == 'VCC1V8' and k[0] in ('C93', 'C144', 'C95', 'C96')]
if v10:
    A['V10'] = list(P[v10[0]])
    link(2, pad('C84', 'VCC1V0'), '@V10')
if v18:
    A['V18'] = list(P[v18[0]])
    link(2, pad('L2', 'VCC1V8'), '@V18')
parts = ['U8', 'U7', 'L1', 'L2', 'L3', 'L8', 'L9', 'C78', 'C80', 'C82', 'C84', 'C147', 'C148', 'C149', 'C150', 'C151',
         'C160', 'C161', 'C163', 'C164', 'C165', 'C166', 'C167', 'C168', 'R102', 'R103', 'R107', 'R108', 'R113',
         'R114', 'R115', 'R116', 'R117', 'R118']
json.dump({'region': region, 'side': 'B', 'parts': parts, 'anchors': A, 'links': L, 'los_min_w': los}, open(out, 'w'),
          indent=1)
print(len(L), 'links', sorted(A))
