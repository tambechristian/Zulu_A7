# -*- coding: utf-8 -*-
"""U1 (CPG236) fan-out: the merged, judged plan.

    python tools/fanout_plan.py             reads tools/fanout_inputs.json,
                                            writes tools/fanout_plan.json,
                                            runs its own geometry check
    python tools/fanout_plan.py --selftest  also plants faults and shows the
                                            checker reports them

Everything geometric comes from fanout_inputs.json (ball and cell centres,
blocked cells, Bottom 0201 pads, neighbour copper extents).  Nothing is
derived from prose.  Rows count from the TOP of the board (row A = largest y);
columns count left to right.  Coordinates in mm on the board origin.

WHAT WAS MERGED (judge's decisions, each with its number)
  rings 2-5 and the core   the "moat" plan: 56 ring-2 balls for 48 ring-3
                           cells, 3 of them blocked (E16 L16 M16) and used as
                           Top pass-throughs to ring-4 (F15 K15 N15); GND
                           sharing in the NW (D4 D5 D6 E4) saves 4; 52 balls
                           for 48 channels -> 4 leave outward, one per side.
                           CHANGE vs moat: the east one is U17 (JA10, lane
                           y = 8.15, via 51.40,8.15) instead of T17, because
                           T19 (GND) needs the row-line via and only ONE track
                           passes between two outside vias 0.75 mm apart at
                           the same x.  T17 takes T16 straight.
  rings 0-1 power          the "power" plan: NW GND mesh with west row-line
                           vias, north-centre GND into C10, GNDADC mesh into
                           D11, B14 corridor thread into A11, east row-line
                           GND vias, the H18/P2/V18 GND necks and the V6/V9/
                           V11 VCC3V3 necks, C18 -> B19 diagonal (0.20 wide:
                           0.141 to B18/C19, so it is NOT a neck).
                           CHANGE vs power: outside vias are STAGGERED in the
                           outward direction (x = 40.4/40.9/41.4 west,
                           51.4/51.9 east, y = 6.25/6.9 south) so that no two
                           outside vias 0.75 mm apart share an x/y zone; the
                           lane ledger below proves every ring-0/1 signal
                           ball keeps an exit.  V18 necks SOUTH (W18|W19 gap,
                           via 50.65,6.35) instead of east: the east via at
                           (51.4,7.15) was 0.025 mm from C115 pad 2 and
                           killed W19's east exit.
  under-die caps           every Bottom 0201 pad under the die gets copper:
                           GND stubs F7 F11 F15 N6 K11 L14 (moat), VCC1V0
                           F10 K10 stubs plus a Bottom trunk K10 -> C89-1 ->
                           C90-1 / C91-1 at y = 11.45 and 11.05 (checked
                           0.10 to the L14 via), VCC1V8 G14 -> C95-1 (moat)
                           and a NEW VCC1V8 via at ring-4 E5 for C96-1, fed
                           from D8 on L3 via E8 (0.15 wide, 0.25 to the
                           D-row vias).  Ring-0/1 cap ties (C107-C115) are
                           left to routing: they cross the Bottom escape
                           corridors of the T/D-row vias.
  PlaneConnect             Direct for IsVia (priority above the Relief rule),
                           Relief kept for through-hole pads; see the plane
                           raster printed by this script.
"""
import copy
import io
import json
import math
import os
import sys
from collections import Counter, defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(HERE, 'fanout_inputs.json')
OUT = os.path.join(HERE, 'fanout_plan.json')

CLR = 0.09            # Clearance rule, all nets, all layers (SDRAM extras are L3/L4 only)
VIA_LAND = 0.35
VIA_R = VIA_LAND / 2
VIA_HOLE = 0.20
VIA_PITCH = 0.44      # land 0.35 + 0.09
HOLE_GAP = 0.20       # HoleToHoleClearance
W3 = 0.0762           # 3 mil
W15 = 0.15
W20 = 0.20
TRK_MAX = 0.5         # global Width rule maximum

inp = json.load(io.open(INPUTS, encoding='utf-8'))
G = inp['grid']
ROWS = G['rows']
COLX = {int(k): v for k, v in G['col_x'].items()}
ROWY = G['row_y']
LAND_R = G['land'] / 2.0
PITCH = G['pitch_x']
EXT = G['u1_extent']
BALLS = {b['name']: b for b in inp['balls']}
VACANT = {v['name']: v for v in inp['vacant']}
BLOCKED = {b['cell'] for b in inp['blocked']}
BPADS = list(inp['bottom_pads_under_u1'])
NETS = set(inp['nets'])
NEIGH = inp['neighbours']

# net classes, from tools/ZuluSetup.pas MakeNetClasses (Width_SDRAM binds the
# SDRAM classes to 3 mil pref / 0.15 max on Top; PWR_RAILS min 0.15 unless a
# higher-priority rule exists: VCC3V3 has its own rule with min 3 mil, VCC1V0
# its own with min 0.15)
SDRAM = set('A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 BS0 BS1 '
            'D0 D1 D2 D3 D4 D5 D6 D7 D8 D9 D10 D11 D12 D13 D14 D15 '
            'CAS# RAS# WE# CKE LDQM UDQM SDRAM-CS# SDRAM-CLK'.split())
PWR_RAILS = set('VCC1V0 VCC1V8 VCC3V3 VCCADC VU VBATT USB5V0 FT-VCORE FT-VPHY FT-VPLL'.split())


def min_width(net, layer):
    if net == 'VCC1V0':
        return 0.15                       # Width_PWR_VCC1V0: min 0.15 all layers (mid layers 0.50)
    if net == 'VCC3V3':
        return W3 if layer in ('Top',) else (1.05 if layer in ('L3-SIG', 'L4-SIG') else 0.20)
    if net in ('VU', 'USB5V0', 'VBATT'):
        return 0.20
    if net in PWR_RAILS:
        return 0.15                       # Width_PWR_RAILS
    return W3


def max_width(net, layer):
    if net in SDRAM:
        return 0.15                       # Width_SDRAM MAXLIMIT 5.9055 mil
    if net in ('VCC3V3', 'VCC1V0', 'VU', 'USB5V0', 'VBATT'):
        return 1.5
    if net in PWR_RAILS:
        return 1.0
    return TRK_MAX


def cell(name):
    r, c = name[0], int(name[1:])
    return COLX[c], ROWY[r]


def X(c):
    return COLX[c]


def Y(r):
    return ROWY[r]


def half(a, b):
    return (a + b) / 2.0


def net_of(ball):
    return BALLS[ball]['net']


XW1 = X(1) - PITCH          # 41.4 : outside column west, one pitch off col 1
XW2 = X(1) - 2 * PITCH      # 40.9
XW3 = X(1) - 3 * PITCH      # 40.4
XE1 = X(19) + PITCH         # 51.4
XE2 = X(19) + 2 * PITCH     # 51.9
YS1 = Y('W') - PITCH        # 6.9  : outside row south
YS2 = Y('W') - PITCH - 0.65  # 6.25 : second south row (zone-disjoint from 6.9)
Y_OUT_S = EXT['y0'] - CLR - VIA_R - 0.0025   # 7.02 : the moat's "just outside the land field"
Y_CORR = 16.78              # corridor via row: 16.5125 + 0.09 + 0.175 + 0.0025 (U4 copper at 17.215)

vias = []
tracks = []
acts = {}
notes = []


def via(net, pos, why):
    if isinstance(pos, str):
        x, y = cell(pos)
        c = pos
    else:
        x, y = pos
        c = None
    vias.append({'net': net, 'x': round(x, 4), 'y': round(y, 4), 'cell': c, 'why': why})


def trk(net, p1, p2, width, why, layer='Top'):
    x1, y1 = cell(p1) if isinstance(p1, str) else p1
    x2, y2 = cell(p2) if isinstance(p2, str) else p2
    tracks.append({'net': net, 'x1': round(x1, 4), 'y1': round(y1, 4), 'x2': round(x2, 4), 'y2': round(y2, 4),
                   'layer': layer, 'width': width, 'why': why})


def act(name, action, detail=''):
    acts[name] = (action, detail)


def is_diag(a, b):
    (ax, ay), (bx, by) = cell(a), cell(b)
    return abs(ax - bx) > 0.01 and abs(ay - by) > 0.01


def link(a, b, why, width=W20, diag_width=W15):
    """same-net ball-ball or ball-cell link; diagonals default to 0.15 (0.104 to a flanking via)."""
    net = net_of(a) if a in BALLS else net_of(b)
    w = diag_width if is_diag(a, b) else width
    trk(net, a, b, w, why)


def dogbone(ball, c, why, width=None, place_via=True):
    net = net_of(ball)
    if width is None:
        width = W20 if net in ('GND', 'GNDADC', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VCCADC') else W3
    link(ball, c, why, width=width, diag_width=min(width, W15))
    if place_via:
        via(net, c, why)


def chain(names, why, width=W20):
    for a, b in zip(names, names[1:]):
        assert net_of(a) == net_of(b), (a, b)
        link(a, b, why, width=width)


# ============================================================================
# 0. defaults for rings 0-1 and the no-net balls (signals: actions only)
for n, b in BALLS.items():
    if b['net'] is None:
        act(n, 'none', 'no-net ball')
    elif b['ring'] == 0:
        act(n, 'direct', 'signal, leaves outward on Top at its row/column line')
    elif b['ring'] == 1:
        act(n, 'gap', 'signal, 3 mil stub through a ring-0 gap (named by the ledger below)')

# ============================================================================
# 1. RING 2 NORTH (row C -> row D).  D16 belongs to D17, so C8..C16 shift one
#    cell west as diagonals and C17 leaves north.  NW GND sharing: D4 (C3 C4
#    D3), D5 (C5), D6 (C6 + C7 chained), E4 (E3 + F3 chained).
via('GND', 'D4', 'GND: C3 (diag), C4, D3 share it')
link('C3', 'D4', 'ring-2 corner GND diagonal into the shared D4 via')
link('C4', 'D4', 'GND straight dog-bone into D4')
link('D3', 'D4', 'GND straight dog-bone into D4')
dogbone('C5', 'D5', 'GND straight dog-bone')
dogbone('C6', 'D6', 'GND straight dog-bone; C7 chains into C6')
link('C7', 'C6', 'GND chain C7-C6 frees D7 for the row-C shift')
dogbone('E3', 'E4', 'GND straight dog-bone; F3 chains into E3')
link('F3', 'E3', 'GND chain F3-E3 frees F4 for the col-3 shift')
for b in ('C3', 'C4', 'D3', 'C5', 'C6', 'E3'):
    act(b, 'dogbone-in', 'shared NW GND via')
act('C7', 'chain', 'C7-C6 -> D6'); act('F3', 'chain', 'F3-E3 -> E4')
for ball, c in (('C8', 'D7'), ('C9', 'D8'), ('C10', 'D9'), ('C11', 'D10'), ('C12', 'D11'), ('C13', 'D12'),
                ('C14', 'D13'), ('C15', 'D14'), ('C16', 'D15')):
    dogbone(ball, c, 'row-C shift: diagonal one cell west because D16 belongs to D17')
    act(ball, 'dogbone-in', c + ' (diagonal)')
dogbone('D17', 'D16', 'D17 has only D16 (E16 is blocked by C95 pad 2)')
act('D17', 'dogbone-in', 'D16')
# C17 (JA4 -> R29 on Bottom, east): out north through B17|B18 and A17|A18 to a corridor via
xl = half(X(17), X(18))
cx, cy = cell('C17')
trk('JA4', (cx, cy), (xl, cy + (xl - cx)), W3, 'C17 out north: 45 deg to the col 17|18 lane')
trk('JA4', (xl, cy + (xl - cx)), (xl, Y_CORR), W3, 'C17 out north: 3 mil lane through B17|B18 and A17|A18')
via('JA4', (xl, Y_CORR), 'C17 JA4 via in the north corridor (U4 copper at 17.215: 0.26 clear); it splits the corridor')
act('C17', 'dogbone-out', 'north lane x=%.2f -> via (%.2f, %.2f)' % (xl, xl, Y_CORR))

# ============================================================================
# 2. RING 2 WEST (col 3 -> col 4).  T4 belongs to U4, so G3..T3 shift one cell
#    north as diagonals; U3 leaves west.
for ball, c in (('G3', 'F4'), ('H3', 'G4'), ('J3', 'H4'), ('K3', 'J4'), ('L3', 'K4'), ('M3', 'L4'),
                ('N3', 'M4'), ('P3', 'N4'), ('R3', 'P4'), ('T3', 'R4')):
    dogbone(ball, c, 'col-3 shift: diagonal one cell north because T4 belongs to U4')
    act(ball, 'dogbone-in', c + ' (diagonal)')
yl = half(Y('T'), Y('U'))
ux, uy = cell('U3')
trk('A10', (ux, uy), (ux - (yl - uy), yl), W3, 'U3 out west: 45 deg to the row T|U lane')
trk('A10', (ux - (yl - uy), yl), (XW1, yl), W3, 'U3 out west: 3 mil lane through T2|U2 and T1|U1')
via('A10', (XW1, yl), 'U3 A10 via one pitch west of col 1 (SDRAM on Bottom, west)')
act('U3', 'dogbone-out', 'west lane y=%.2f -> via (%.2f, %.2f)' % (yl, XW1, yl))

# ============================================================================
# 3. RING 2 SOUTH (row U -> row T).  U4..U15 straight, T17 -> T16 straight,
#    U16 leaves south, U17 leaves east (see the ledger for why not T17).
for c in range(4, 16):
    dogbone('U%d' % c, 'T%d' % c, 'straight dog-bone into ring 3')
    act('U%d' % c, 'dogbone-in', 'T%d' % c)
dogbone('T17', 'T16', 'straight dog-bone into ring 3 (T16 is the only SE cell; U16/U17 leave outward)')
act('T17', 'dogbone-in', 'T16')
xl = half(X(16), X(17))
ux, uy = cell('U16')
trk('CHAN17', (ux, uy), (xl, uy - (xl - ux)), W3, 'U16 out south: 45 deg to the col 16|17 lane')
trk('CHAN17', (xl, uy - (xl - ux)), (xl, Y_OUT_S), W3, 'U16 out south: 3 mil lane through V16|V17 and W16|W17')
via('CHAN17', (xl, Y_OUT_S), 'U16 CHAN17 via just south of the land field (X2 pad 27 is at the bottom edge)')
act('U16', 'dogbone-out', 'south lane x=%.2f -> via (%.2f, %.2f)' % (xl, xl, Y_OUT_S))
yl = half(Y('U'), Y('V'))
ux, uy = cell('U17')
trk('JA10', (ux, uy), (ux + (uy - yl), yl), W3, 'U17 out east: 45 deg to the row U|V lane')
trk('JA10', (ux + (uy - yl), yl), (XE1, yl), W3, 'U17 out east: 3 mil lane through U18|V18 and U19|V19')
via('JA10', (XE1, yl), 'U17 JA10 via one pitch east of col 19 (R33 on Bottom, east); T19 via is staggered to x=51.9')
act('U17', 'dogbone-out', 'east lane y=%.2f -> via (%.2f, %.2f)' % (yl, XE1, yl))

# ============================================================================
# 4. RING 2 EAST (col 17 -> col 16).  E16 L16 M16 blocked: pass-through to ring 4.
for ball, c in (('F17', 'F16'), ('G17', 'G16'), ('H17', 'H16'), ('J17', 'J16'), ('K17', 'K16'),
                ('N17', 'N16'), ('P17', 'P16'), ('R17', 'R16')):
    dogbone(ball, c, 'straight dog-bone into ring 3')
    act(ball, 'dogbone-in', c)
for ball, thru, c in (('E17', 'E16', 'F15'), ('L17', 'L16', 'K15'), ('M17', 'M16', 'N15')):
    net = net_of(ball)
    w = W20 if net in ('VCC3V3', 'GND') else W3
    trk(net, ball, thru, w, '2-pitch dog-bone: %s is blocked for a via, used as a Top pass-through' % thru)
    trk(net, thru, c, min(w, W15), '2-pitch dog-bone: diagonal on to the ring-4 via %s' % c)
    via(net, c, '2-pitch dog-bone for %s through blocked %s' % (ball, thru))
    act(ball, 'dogbone-in', '%s -> %s -> %s' % (ball, thru, c))

# ============================================================================
# 5. THE CORE: same-net chains at 0.20, ring-5 vias facing every edge ball,
#    centre vias K9 K10 K11, two GND stitches for the Bottom caps.
core_chains = [
    ('G7', 'G8'), ('G8', 'G9'), ('G7', 'H7'), ('G8', 'H8'), ('G9', 'H9'), ('H7', 'H8'), ('H8', 'H9'),
    ('H8', 'J8'), ('H9', 'J9'), ('J8', 'J9'), ('J8', 'K8'), ('K8', 'L8'), ('L8', 'L9'), ('L9', 'M9'), ('M9', 'N9'),
    ('G11', 'H11'), ('H11', 'J11'), ('H11', 'H12'), ('J11', 'J12'), ('H12', 'J12'), ('M13', 'N13'), ('N12', 'N13'),
    ('J7', 'K7'), ('K7', 'L7'), ('L7', 'M7'), ('M7', 'N7'), ('M7', 'M8'), ('N7', 'N8'), ('M8', 'N8'),
    ('G12', 'G13'), ('K12', 'K13'), ('L12', 'L13'), ('K12', 'L12'), ('K13', 'L13'), ('L12', 'M12'),
    ('G10', 'H10'), ('H10', 'J10'), ('L10', 'M10'), ('M10', 'N10'), ('M10', 'M11'), ('N10', 'N11'), ('M11', 'N11'),
    ('H13', 'J13'),
]
for a, b in core_chains:
    link(a, b, '%s core chain %s-%s' % (net_of(a), a, b))
core_vias = [
    ('G7', 'F7'), ('G8', 'F8'), ('G9', 'F9'), ('G10', 'F10'), ('G11', 'F11'), ('G12', 'F12'), ('G13', 'F13'),
    ('G7', 'F6'),
    ('G7', 'G6'), ('H7', 'H6'), ('J7', 'J6'), ('K7', 'K6'),
    ('N7', 'P7'), ('N8', 'P8'), ('N9', 'P9'), ('N10', 'P10'), ('N11', 'P11'), ('N12', 'P12'), ('N13', 'P13'),
    ('N7', 'P6'), ('N13', 'P14'),
    ('H13', 'H14'), ('J13', 'J14'), ('K13', 'K14'), ('N13', 'N14'),
    ('H13', 'G14'),
    ('J9', 'K9'), ('L9', 'K9'), ('J10', 'K10'), ('L10', 'K10'), ('J11', 'K11'), ('L11', 'K11'),
]
seen = set()
for ball, c in core_vias:
    link(ball, c, '%s ball %s to its via %s' % (net_of(ball), ball, c))
    if c not in seen:
        via(net_of(ball), c, '%s via for core ball %s' % (net_of(ball), ball))
        seen.add(c)
via('GND', 'N6', 'GND stitch for C90 pad 2 (Bottom); no ball on Top')
via('GND', 'L14', 'GND stitch for C91 pad 2 (Bottom); no ball on Top')
for n, b in BALLS.items():
    if b['ring'] >= 6 and b['net']:
        act(n, 'via-adjacent' if any(x == n for x, _ in core_vias) else 'chain',
            'core %s' % b['net'])

# ============================================================================
# 6. RINGS 0-1 POWER
# 6a. NW GND block: Top mesh at 0.20 + west row-line vias (rows A B C E F have
#     no signal neighbours, so 0.5-pitch outside vias cost no lane)
chain(['A1', 'B1', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7'], 'NW GND mesh')
for c in ('3', '4', '5', '6', '7'):
    chain(['A' + c, 'B' + c, 'C' + c], 'NW GND mesh column')
chain(['A3', 'A4', 'A5', 'A6', 'A7'], 'NW GND mesh row A')
chain(['B3', 'B4', 'B5', 'B6', 'B7'], 'NW GND mesh row B')
chain(['C3', 'D3', 'E3', 'F3'], 'NW GND mesh col 3')
chain(['E1', 'E2', 'E3'], 'NW GND mesh row E'); chain(['F1', 'F2', 'F3'], 'NW GND mesh row F')
chain(['E1', 'F1'], 'NW GND mesh col 1 (C1-E1 would cross the no-net D1 land)')
# G1 is NOT chained to F1: that link would sit in the F|G gap, which G2 (AIN15_N) needs
# (the west side has 13 gaps F|G..V|W for 11 col-2 signals + the P2 neck + the U3 lane,
# zero slack), and a G1 -> F2 diagonal would cross G2's own 45 deg stub at (42.15, 13.65).
# G1 gets a row-line via staggered to x = 40.9, so the F|G lane passes both vias.
for r, x in (('A', XW1), ('B', XW1), ('C', XW1), ('E', XW1), ('F', XW1), ('G', XW2)):
    via('GND', (x, Y(r)), '%s1 ring-0 GND: outside west, row line at x=%.2f' % (r, x))
    trk('GND', r + '1', (x, Y(r)), W20, '%s1 -> outside via' % r)
    act(r + '1', 'direct', '0.20 to the outside via (%.2f, %.2f)' % (x, Y(r)))
via('GND', (XW1, YS1), 'W1 corner GND via, SW')
trk('GND', 'W1', (XW1, YS1), W15, 'W1 -> SW corner via (45 deg, 0.141 to V1 at 0.15 wide)')
act('W1', 'direct', '0.15 diagonal to the corner via (%.2f, %.2f)' % (XW1, YS1))
for n in ('A3', 'A4', 'A5', 'A6', 'A7', 'B3', 'B4', 'B5', 'B6', 'B7', 'C2', 'E2', 'F2'):
    act(n, 'chain', 'NW GND mesh')
# 6b. north-centre GND: A9 B9 A11 B11 -> C10 -> D9
chain(['A9', 'B9'], 'north GND pair'); chain(['A11', 'B11'], 'north GND pair')
link('B9', 'C10', 'B9 -> C10 diagonal between B10 (no-net) and C9 (VCC1V8): 0.141 at 0.20', diag_width=W20)
link('B11', 'C10', 'B11 -> C10 diagonal between B10 (no-net) and C11: 0.141 at 0.20', diag_width=W20)
for n in ('A9', 'A11', 'B9', 'B11'):
    act(n, 'chain', 'north GND group -> C10 -> D9')
# 6c. B14 (GND, boxed): 3 mil thread through the A13|A14 gap, west along the
#     corridor floor (y = A + 0.25) over A13/A12, down into A11.
xg = half(X(13), X(14)); yc = Y('A') + 0.25
trk('GND', 'B14', (xg, Y('B') + 0.25), W3, 'B14 thread: 45 deg into the A13|A14 gap')
trk('GND', (xg, Y('B') + 0.25), (xg, yc), W3, 'B14 thread: north through the A13|A14 gap')
trk('GND', (xg, yc), (half(X(11), X(12)), yc), W3, 'B14 thread: west along the corridor floor over A13/A12 (0.0995)')
trk('GND', (half(X(11), X(12)), yc), 'A11', W3, 'B14 thread: 45 deg down into A11')
act('B14', 'gap', 'GND thread: A13|A14 gap -> corridor floor -> A11 (uses the corridor floor x 47.15..48.15)')
# 6d. GNDADC: 2x2 mesh + C12 -> D11 (separate net from GND, never touches it)
chain(['A12', 'B12', 'C12'], 'GNDADC mesh'); chain(['A13', 'B13'], 'GNDADC mesh')
chain(['A12', 'A13'], 'GNDADC mesh'); chain(['B12', 'B13'], 'GNDADC mesh')
for n in ('A12', 'A13', 'B12', 'B13'):
    act(n, 'chain', 'GNDADC mesh -> C12 -> D11')
# 6e. east GND: A19 C19 F19 L19 row-line at x=51.4, T19 staggered to
#     x=51.9 (the U17 lane via sits at 51.4,8.15, 0.75 below the T row)
# A19 stays on the row line: a corner via at (51.4,16.9) would box A18 in (U4 pad 5
# copper starts at x 50.4, y 17.215; the JA4 via is 0.25 west of A18), whereas with
# the row-line via A18 and B18 run east above A19 at y 16.65/16.82, bumping to
# 16.70/16.87 at x 51.4, then north between U4 pad 5 (x <= 51.905) and C93 (x >= 52.35).
for r, x in (('A', XE1), ('C', XE1), ('F', XE1), ('L', XE1), ('T', XE2)):
    via('GND', (x, Y(r)), '%s19 ring-0 GND: outside east, row line at x=%.2f' % (r, x))
    trk('GND', r + '19', (x, Y(r)), W20, '%s19 -> outside via' % r)
    act(r + '19', 'direct', '0.20 to the outside via (%.2f, %.2f)' % (x, Y(r)))
# H18 (GND, boxed): neck through the G|H gap (13.15) to (51.9, 13.15); G|H is
# the gap that leaves J|K..U|V for J18..U18 plus the U17 lane (16 gaps, 16 users)
yg = half(Y('G'), Y('H'))
trk('GND', 'H18', (half(X(18), X(19)), yg), W3, 'H18 neck: 45 deg to the G19|H19 gap')
trk('GND', (half(X(18), X(19)), yg), (XE2, yg), W3, 'H18 neck: through the gap to the via')
via('GND', (XE2, yg), 'H18 neck via, staggered to x=51.9 (F19 via at 51.4,13.9 is 0.75 away)')
act('H18', 'gap', 'GND neck through G|H (y=%.2f) -> via (%.2f, %.2f)' % (yg, XE2, yg))
# 6f. south GND: W12 column-line via staggered to y=6.25 (V11 via at 46.65,6.9
#     is 0.75 away); V18 necks south through W18|W19 to (50.65, 6.35)
via('GND', (X(12), YS2), 'W12 ring-0 GND: outside south, column line, second row y=6.25')
trk('GND', 'W12', (X(12), YS2), W20, 'W12 -> outside via')
act('W12', 'direct', '0.20 to the outside via (%.2f, %.2f)' % (X(12), YS2))
xg = half(X(18), X(19)); yv18 = YS1 - 0.55
trk('GND', 'V18', (xg, half(Y('V'), Y('W'))), W3, 'V18 neck: 45 deg to the W18|W19 gap')
trk('GND', (xg, half(Y('V'), Y('W'))), (xg, yv18), W3, 'V18 neck: south through the W18|W19 gap')
via('GND', (xg, yv18), 'V18 neck via, south (zone-disjoint from the CHAN17 via at 49.65,7.02)')
act('V18', 'gap', 'GND neck through W18|W19 (x=%.2f) -> via (%.2f, %.2f)' % (xg, xg, yv18))
# 6g. P2 (GND, boxed): neck through the N1|P1 gap to (40.9, 10.15)
yg = half(Y('N'), Y('P'))
trk('GND', 'P2', (half(X(1), X(2)), yg), W3, 'P2 neck: 45 deg to the N1|P1 gap')
trk('GND', (half(X(1), X(2)), yg), (XW2, yg), W3, 'P2 neck: through the gap to the via')
via('GND', (XW2, yg), 'P2 neck via at x=40.9 (K1 via 40.9,11.9 is 1.75 away; R1 via is at 40.4)')
act('P2', 'gap', 'GND neck through N|P (y=%.2f) -> via (%.2f, %.2f)' % (yg, XW2, yg))
# 6h. VCC3V3 ring 0/1: B19 east; C18 -> B19 diagonal at 0.20; K1 R1 V1 west
#     staggered; V6 V9 V11 3 mil necks through W gaps
via('VCC3V3', (XE1, Y('B')), 'B19 outside east, row line (+ C18)')
trk('VCC3V3', 'B19', (XE1, Y('B')), W20, 'B19 -> via')
trk('VCC3V3', 'C18', 'B19', W20, 'C18 -> B19 diagonal between B18 and C19 (0.141 at 0.20: not a neck)')
act('B19', 'direct', '0.20 to the outside via (%.2f, %.2f)' % (XE1, Y('B')))
act('C18', 'chain', '0.20 diagonal into B19 (boxed orthogonally, B19 is the same net diagonally)')
for r, x in (('K', XW2), ('R', XW3), ('V', XW2)):
    via('VCC3V3', (x, Y(r)), '%s1 outside west, row line at x=%.2f' % (r, x))
    trk('VCC3V3', r + '1', (x, Y(r)), W20, '%s1 -> via' % r)
    act(r + '1', 'direct', '0.20 to the outside via (%.2f, %.2f)' % (x, Y(r)))
for b, cl, cr, yv in (('V6', 5, 6, YS1), ('V9', 8, 9, YS1), ('V11', 10, 11, YS1)):
    xg = half(X(cl), X(cr)); yg = half(Y('V'), Y('W'))
    trk('VCC3V3', b, (xg, yg), W3, '%s neck: 45 deg to the W%d|W%d gap' % (b, cl, cr))
    trk('VCC3V3', (xg, yg), (xg, yv), W3, '%s neck: south through the gap to the via' % b)
    via('VCC3V3', (xg, yv), '%s neck via (half-column %.2f, y=%.2f)' % (b, xg, yv))
    act(b, 'gap', 'VCC3V3 3 mil neck through W%d|W%d (x=%.2f) -> via (%.2f, %.2f)' % (cl, cr, xg, xg, yv))

# ============================================================================
# 7. BOTTOM: cap stubs under the die, the VCC1V0 trunk, the E5 VCC1V8 via
pad = {(p['ref'], p['pad']): p for p in BPADS}


def pc(ref, n):
    p = pad[(ref, str(n))]
    return p['x'], p['y']


def bstub(net, start, pts, why, w=W15):
    prev = cell(start) if isinstance(start, str) else start
    for q in pts:
        trk(net, prev, q, w, why, layer='Bottom')
        prev = q


bstub('GND', 'F7', [pc('C96', 2)], 'Bottom: F7 GND up into C96 pad 2')
bstub('GND', 'F11', [pc('C92', 2)], 'Bottom: F11 GND to C92 pad 2')
bstub('GND', 'F15', [pc('C95', 2)], 'Bottom: F15 GND to C95 pad 2')
bstub('GND', 'N6', [(pc('C90', 2)[0], cell('N6')[1]), pc('C90', 2)], 'Bottom: N6 GND east then north into C90 pad 2')
bstub('GND', pc('C89', 2), [(cell('P12')[0], pc('C89', 2)[1] - (cell('P12')[0] - pc('C89', 2)[0])), cell('P12')],
      'Bottom: C89 pad 2 GND 45 deg then south along x 47.40 into P12 (a K11 stub would cut the VCC1V0 trunk off C91-1)')
bstub('GND', 'L14', [(pc('C91', 2)[0], cell('L14')[1]), pc('C91', 2)], 'Bottom: L14 GND east along y 11.40 then south into C91 pad 2')
bstub('VCC1V0', 'F10', [pc('C92', 1)], 'Bottom: F10 VCC1V0 to C92 pad 1')
bstub('VCC1V0', 'K10', [pc('C89', 1)], 'Bottom: K10 VCC1V0 to C89 pad 1')
# VCC1V0 trunk between the three under-die caps: C89-1 -> y 11.45 -> C90-1 (west) and -> C91-1 (east)
yt = 11.45
bstub('VCC1V0', pc('C89', 1), [(pc('C89', 1)[0], yt), (pc('C90', 1)[0], yt), pc('C90', 1)],
      'Bottom VCC1V0 trunk: C89-1 north to y 11.45, west over C90-2 (0.175), south into C90-1')
bstub('VCC1V0', pc('C89', 1), [(pc('C89', 1)[0], yt), (47.5, yt), (47.9, pc('C91', 1)[1]), pc('C91', 1)],
      'Bottom VCC1V0 trunk: C89-1 north to y 11.45, east over C89-2, 45 deg down, east along y 11.05 (0.10 to the L14 via) into C91-1')
bstub('VCC1V8', 'G14', [(cell('G14')[0], cell('F14')[1]), pc('C95', 1)], 'Bottom: G14 VCC1V8 north through empty F14 then into C95 pad 1')
via('VCC1V8', 'E5', 'VCC1V8 via for C96 pad 1 (0.145 from the pad); fed from D8 on L3')
bstub('VCC1V8', 'E5', [pc('C96', 1)], 'Bottom: E5 VCC1V8 to C96 pad 1')
trk('VCC1V8', 'D8', 'E8', W15, 'L3 feed for E5: D8 south to the empty E8 cell (0.25 to D7/D9)', layer='L3-SIG')
trk('VCC1V8', 'E8', 'E5', W15, 'L3 feed for E5: west along row E over the blocked E7/E6 (no vias there)', layer='L3-SIG')

# ============================================================================
# 8. LANE LEDGER: does every ring-0/1 signal ball keep an exit past the
#    outside vias?  Model: a track at slot s passing an outside via at v
#    (|s - v| = 0.25) bumps to |s - v| = 0.303 (0.175 + 0.09 + 0.038) within
#    0.171 (+0.053 jog) of the via's outward coordinate; the slot at 0.5 keeps
#    0.121.  Two vias on one side whose outward coordinates differ by < 0.45
#    share a zone, and the tracks between them must fit sum(w) + 0.09 (n-1)
#    <= d - 0.53.  Each ring-0 gap carries one track.
SIDES = {
    'W': dict(ring0=lambda n: BALLS[n]['col'] == 1, ring1=lambda n: BALLS[n]['col'] == 2,
              along=lambda x, y: y, outward=lambda x, y: -x, edge=EXT['x0'],
              slots=[(r, Y(r)) for r in ROWS], gaps=[('%s|%s' % (a, b), half(Y(a), Y(b))) for a, b in zip(ROWS, ROWS[1:])],
              ballgaps=lambda n: ['%s|%s' % (p, n[0]) for p in [ROWS[ROWS.index(n[0]) - 1]]] + ['%s|%s' % (n[0], q) for q in [ROWS[ROWS.index(n[0]) + 1]]]),
    'E': dict(ring0=lambda n: BALLS[n]['col'] == 19, ring1=lambda n: BALLS[n]['col'] == 18,
              along=lambda x, y: y, outward=lambda x, y: x, edge=EXT['x1'],
              slots=[(r, Y(r)) for r in ROWS], gaps=[('%s|%s' % (a, b), half(Y(a), Y(b))) for a, b in zip(ROWS, ROWS[1:])],
              ballgaps=lambda n: ['%s|%s' % (p, n[0]) for p in [ROWS[ROWS.index(n[0]) - 1]]] + ['%s|%s' % (n[0], q) for q in [ROWS[ROWS.index(n[0]) + 1]]]),
    'S': dict(ring0=lambda n: BALLS[n]['row'] == 'W', ring1=lambda n: BALLS[n]['row'] == 'V',
              along=lambda x, y: x, outward=lambda x, y: -y, edge=EXT['y0'],
              slots=[(str(c), X(c)) for c in range(1, 20)], gaps=[('%d|%d' % (c, c + 1), half(X(c), X(c + 1))) for c in range(1, 19)],
              ballgaps=lambda n: ['%d|%d' % (int(n[1:]) - 1, int(n[1:])), '%d|%d' % (int(n[1:]), int(n[1:]) + 1)]),
    'N': dict(ring0=lambda n: BALLS[n]['row'] == 'A', ring1=lambda n: BALLS[n]['row'] == 'B',
              along=lambda x, y: x, outward=lambda x, y: y, edge=EXT['y1'],
              slots=[(str(c), X(c)) for c in range(1, 20)], gaps=[('%d|%d' % (c, c + 1), half(X(c), X(c + 1))) for c in range(1, 19)],
              ballgaps=lambda n: ['%d|%d' % (int(n[1:]) - 1, int(n[1:])), '%d|%d' % (int(n[1:]), int(n[1:]) + 1)]),
}


def side_of_point(x, y):
    """which side of the land field a point outside it belongs to (None inside)."""
    if x < EXT['x0'] - 1e-6:
        return 'W'
    if x > EXT['x1'] + 1e-6:
        return 'E'
    if y < EXT['y0'] - 1e-6:
        return 'S'
    if y > EXT['y1'] + 1e-6:
        return 'N'
    return None


def ledger(vias, tracks, acts, quiet=False):
    """returns (assignment dict ball->'side gapname', problems list, report lines)."""
    problems = []
    report = []
    # 1. outside vias per side, and fixed tracks (lanes/exits already drawn) per side
    out_vias = defaultdict(list)
    for v in vias:
        s = side_of_point(v['x'], v['y'])
        if s:
            out_vias[s].append((SIDES[s]['along'](v['x'], v['y']), SIDES[s]['outward'](v['x'], v['y']), v))
    fixed = defaultdict(list)   # side -> list of (along, width, name, outward_reach)
    used_gaps = defaultdict(set)
    for t in tracks:
        if t['layer'] != 'Top':
            continue
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            s = side_of_point(x, y)
            if s:
                sd = SIDES[s]
                # the segment's along-coordinate where it crosses the field edge; only axis-parallel lanes matter
                a1, a2 = sd['along'](t['x1'], t['y1']), sd['along'](t['x2'], t['y2'])
                if abs(a1 - a2) < 1e-6:
                    reach = max(sd['outward'](t['x1'], t['y1']), sd['outward'](t['x2'], t['y2']))
                    fixed[s].append((a1, t['width'], t['net'], reach))
                    for gname, ga in sd['gaps']:
                        if abs(ga - a1) < 1e-3:
                            used_gaps[s].add(gname)
                break
    # 2. demands (a ball that already has a Top track on it is served: its stub is a fixed lane)
    kk = lambda x, y: (round(x, 3), round(y, 3))
    served = set()
    for t in tracks:
        if t['layer'] == 'Top':
            for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
                served.add(kk(x, y))
    demands = []    # (ball, [(side, gapname or slot)])
    for n, b in sorted(BALLS.items(), key=lambda kv: (kv[1]['row'], kv[1]['col'])):
        if not b['net'] or acts[n][0] not in ('direct', 'gap'):
            continue
        if b['net'] in ('GND', 'GNDADC', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VCCADC'):
            continue
        if b['ring'] == 1 and kk(b['x'], b['y']) in served:
            continue
        opts = []
        for s, sd in SIDES.items():
            if sd['ring0'](n):
                if s in ('W', 'E'):
                    opts.append((s, 'row ' + n[0]))
                else:
                    opts.append((s, 'col ' + n[1:]))
            elif sd['ring1'](n) and b['ring'] == 1:
                for g in sd['ballgaps'](n):
                    if g not in used_gaps[s]:
                        opts.append((s, g))
        if b['name'] == 'B18':
            opts.append(('E', 'A|B'))       # offered, but dead between the A19 (16.4) and B19 (15.9) vias: the search rejects it
        if not opts:
            problems.append('ledger: %s (%s) has no free exit option' % (n, b['net']))
        demands.append((n, opts))

    # 3. window feasibility for a full assignment on one side
    def side_ok(s, assign):
        sd = SIDES[s]
        trks = list(fixed[s])   # (along, width, net, reach)
        for n, (ss, g) in assign.items():
            if ss != s:
                continue
            if g.startswith('row ') or g.startswith('col '):
                a = dict(sd['slots'])[g.split()[1]]
            else:
                a = dict(sd['gaps'])[g]
            trks.append((a, W3, BALLS[n]['net'], 99.0))
        vs = sorted(out_vias[s])
        msgs = []
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                (a1, o1, v1), (a2, o2, v2) = vs[i], vs[j]
                if abs(o1 - o2) >= 0.45:
                    continue
                d = a2 - a1
                between = [(a, w, net) for a, w, net, reach in trks
                           if a1 + 1e-6 < a < a2 - 1e-6 and reach >= min(o1, o2) - 0.224 and net not in (v1['net'], v2['net'])]
                # count every track strictly between the two vias that reaches their zone (its own via's feed included: it is foreign to the other via)
                between = [(a, w, net) for a, w, net, reach in trks
                           if a1 + 1e-6 < a < a2 - 1e-6 and reach >= min(o1, o2) - 0.224]
                need = sum(w for _, w, _ in between) + CLR * max(0, len(between) - 1)
                have = d - 2 * (VIA_R + CLR)
                if between and need > have + 1e-9:
                    msgs.append('side %s: vias %s(%.2f) and %s(%.2f) share a zone (outward %.2f/%.2f); %d tracks need %.3f, window %.3f'
                                % (s, v1['net'], a1, v2['net'], a2, o1, o2, len(between), need, have))
        # each gap once (fixed lanes included)
        cnt = Counter(g for ss, g in assign.values() if ss == s)
        for g in used_gaps[s]:
            cnt[g] += 1
        for g, k in cnt.items():
            if k > 1:
                msgs.append('side %s: gap %s used %d times' % (s, g, k))
        # no two tracks on one slot coordinate
        coords = Counter(round(a, 3) for a, w, net, r in trks)
        for a, k in coords.items():
            if k > 1:
                msgs.append('side %s: %d tracks on the slot at %.3f' % (s, k, a))
        return msgs

    # 4. search.  Balls whose options lie on two sides (corners: W19, V2, B18)
    #    are enumerated outside; each side is then an independent exhaustive
    #    search over the ring-1 balls' two gaps with gap-uniqueness pruning.
    multi = [(n, opts) for n, opts in demands if len({s for s, _ in opts}) > 1]
    single = [(n, opts) for n, opts in demands if len({s for s, _ in opts}) <= 1]

    def solve_side(s, fixed_assign):
        balls_s = [(n, [o for o in opts if o[0] == s]) for n, opts in single if opts and opts[0][0] == s]
        assign = dict(fixed_assign)
        usedg = {o for o in assign.values()}
        best = {'a': None, 'msgs': None}

        def rec(k):
            if k == len(balls_s):
                msgs = side_ok(s, assign)
                if not msgs:
                    best['a'] = dict(assign)
                    return True
                if best['msgs'] is None:
                    best['msgs'] = msgs
                return False
            n, opts = balls_s[k]
            for o in opts:
                if o in usedg:
                    continue
                assign[n] = o; usedg.add(o)
                ok = rec(k + 1)
                usedg.discard(o); del assign[n]
                if ok:
                    return True
            return False
        rec(0)
        return best['a'], best['msgs']

    import itertools
    solution = None
    diag = []
    for combo in itertools.product(*[opts for _, opts in multi]):
        fixed_assign = {n: o for (n, _), o in zip(multi, combo)}
        if len(set(fixed_assign.values())) < len(fixed_assign):
            continue
        full = {}
        ok = True
        for s in SIDES:
            a, msgs = solve_side(s, {n: o for n, o in fixed_assign.items() if o[0] == s})
            if a is None:
                ok = False
                diag.append('side %s with %s: %s' % (s, fixed_assign, msgs))
                break
            full.update(a)
        if ok:
            solution = full
            break
    if solution is None:
        problems.append('ledger: NO feasible exit assignment for the ring-0/1 signal balls with these outside vias')
        for d_ in diag[:6]:
            problems.append('ledger: ' + str(d_)[:300])
        return {}, problems, report
    assign = solution
    for s in SIDES:
        sd = SIDES[s]
        vs = sorted(out_vias[s])
        report.append('side %s: outside vias %s' % (s, ', '.join('%s(%.2f @%.2f)' % (v['net'], a, o) for a, o, v in vs)))
        report.append('side %s: fixed lanes %s' % (s, ', '.join('%s@%.2f' % (net, a) for a, w, net, r in sorted(fixed[s]))))
        gs = sorted(((g, n) for n, (ss, g) in assign.items() if ss == s and not g.startswith(('row', 'col'))), key=lambda t: t[0])
        report.append('side %s: gaps -> %s' % (s, ', '.join('%s:%s' % (g, n) for g, n in gs)))
    return assign, problems, report


# ============================================================================
# 9. THE CHECKER (independent of the two source plans' code)
def seg_pt(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def seg_seg(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b

    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    o1 = orient(x1, y1, x2, y2, x3, y3); o2 = orient(x1, y1, x2, y2, x4, y4)
    o3 = orient(x3, y3, x4, y4, x1, y1); o4 = orient(x3, y3, x4, y4, x2, y2)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return 0.0
    return min(seg_pt(x3, y3, x4, y4, x1, y1), seg_pt(x3, y3, x4, y4, x2, y2),
               seg_pt(x1, y1, x2, y2, x3, y3), seg_pt(x1, y1, x2, y2, x4, y4))


def pt_box(px, py, cx, cy, sx, sy):
    return math.hypot(max(abs(px - cx) - sx / 2, 0.0), max(abs(py - cy) - sy / 2, 0.0))


def seg_box(seg, cx, cy, sx, sy):
    x1, y1, x2, y2 = seg
    hx, hy = sx / 2, sy / 2
    if (abs(x1 - cx) <= hx and abs(y1 - cy) <= hy) or (abs(x2 - cx) <= hx and abs(y2 - cy) <= hy):
        return 0.0
    cs = [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)]
    best = 1e9
    for i in range(4):
        ax, ay = cs[i]; bx, by = cs[(i + 1) % 4]
        best = min(best, seg_seg(seg, (ax, ay, bx, by)))
    return best


LATTICE = {}
for name in list(BALLS) + list(VACANT):
    x, y = cell(name)
    LATTICE[(round(x, 3), round(y, 3))] = name
CAP_REFS = {p['ref'] for p in BPADS}


def check(vias, tracks, acts):
    P = []
    W = []
    tight = []
    infield = lambda x, y: EXT['x0'] - 1e-6 <= x <= EXT['x1'] + 1e-6 and EXT['y0'] - 1e-6 <= y <= EXT['y1'] + 1e-6
    # --- vias
    for i, v in enumerate(vias):
        x, y = v['x'], v['y']
        if v['net'] not in NETS:
            P.append('via %d net %r unknown' % (i, v['net']))
        nm = LATTICE.get((round(x, 3), round(y, 3)))
        if infield(x, y):
            if nm is None:
                P.append('via %s at (%.4f,%.4f) is inside the land field but on no lattice cell (interstitial)' % (v['net'], x, y))
            elif nm in BALLS:
                P.append('via %s sits on ball %s' % (v['net'], nm))
            elif nm in BLOCKED:
                P.append('via %s in blocked cell %s' % (v['net'], nm))
            if v['cell'] != nm:
                P.append('via %s labelled %r but sits at %r' % (v['net'], v['cell'], nm))
        elif v['cell']:
            P.append('via %s labelled %r is outside the land field' % (v['net'], v['cell']))
        for bn, b in BALLS.items():
            g = math.hypot(x - b['x'], y - b['y']) - VIA_R - LAND_R
            if b['net'] != v['net'] or not b['net']:
                if g < CLR - 1e-9:
                    P.append('via %s (%.3f,%.3f) %.4f from land %s (%s)' % (v['net'], x, y, g, bn, b['net']))
                else:
                    tight.append((g, 'via %s (%.2f,%.2f) - land %s' % (v['net'], x, y, bn)))
        for p in BPADS:
            g = pt_box(x, y, p['x'], p['y'], p['sx'], p['sy']) - VIA_R
            if p['net'] != v['net']:
                if g < CLR - 1e-9:
                    P.append('via %s (%.3f,%.3f) %.4f from Bottom pad %s.%s (%s)' % (v['net'], x, y, g, p['ref'], p['pad'], p['net']))
                else:
                    tight.append((g, 'via %s (%.2f,%.2f) - Bottom pad %s.%s' % (v['net'], x, y, p['ref'], p['pad'])))
            else:
                gh = pt_box(x, y, p['x'], p['y'], p['sx'], p['sy']) - VIA_HOLE / 2
                if gh < 0:
                    P.append('via %s (%.3f,%.3f) hole in same-net pad %s.%s' % (v['net'], x, y, p['ref'], p['pad']))
                elif g < CLR:
                    W.append('via %s (%.3f,%.3f) land %.3f from same-net Bottom pad %s.%s (hole clear %.3f)' % (v['net'], x, y, g, p['ref'], p['pad'], gh))
        for ref, e in NEIGH.items():
            if ref in CAP_REFS or ref == 'X2':
                continue
            g = pt_box(x, y, (e['x0'] + e['x1']) / 2, (e['y0'] + e['y1']) / 2, e['x1'] - e['x0'], e['y1'] - e['y0']) - VIA_R
            if g < CLR - 1e-9:
                P.append('via %s (%.3f,%.3f) %.4f from neighbour %s copper extent' % (v['net'], x, y, g, ref))
        for j in range(i + 1, len(vias)):
            w = vias[j]
            dd = math.hypot(x - w['x'], y - w['y'])
            if dd < VIA_PITCH - 1e-9:
                P.append('vias %s (%.3f,%.3f) and %s (%.3f,%.3f) %.4f apart (< %.2f)' % (v['net'], x, y, w['net'], w['x'], w['y'], dd, VIA_PITCH))
            elif dd - VIA_HOLE < HOLE_GAP - 1e-9:
                P.append('holes %s and %s %.4f apart' % (v['net'], w['net'], dd - VIA_HOLE))
            else:
                tight.append((dd - VIA_PITCH, 'via-via %s(%.2f,%.2f) - %s(%.2f,%.2f) over 0.44' % (v['net'], x, y, w['net'], w['x'], w['y'])))
    cells = [v['cell'] for v in vias if v['cell']]
    for c, k in Counter(cells).items():
        if k > 1:
            P.append('cell %s carries %d vias' % (c, k))
    # --- tracks
    for i, t in enumerate(tracks):
        seg = (t['x1'], t['y1'], t['x2'], t['y2'])
        w = t['width']
        if t['net'] not in NETS:
            P.append('track %d net %r unknown' % (i, t['net']))
        if t['layer'] not in ('Top', 'L3-SIG', 'L4-SIG', 'Bottom'):
            P.append('track %d layer %r' % (i, t['layer']))
        if w < min_width(t['net'], t['layer']) - 1e-9:
            P.append('track %s on %s width %.4f under its minimum %.4f [%s]' % (t['net'], t['layer'], w, min_width(t['net'], t['layer']), t['why']))
        if w > max_width(t['net'], t['layer']) + 1e-9:
            P.append('track %s on %s width %.4f over its maximum %.4f [%s]' % (t['net'], t['layer'], w, max_width(t['net'], t['layer']), t['why']))
        if math.hypot(seg[2] - seg[0], seg[3] - seg[1]) < 1e-6:
            P.append('track %d has zero length [%s]' % (i, t['why']))
        if t['layer'] == 'Top':
            for bn, b in BALLS.items():
                if b['net'] == t['net'] and b['net']:
                    continue
                g = seg_pt(*seg, b['x'], b['y']) - LAND_R - w / 2
                if g < CLR - 1e-9:
                    P.append('track %s Top %.4f from land %s (%s) [%s]' % (t['net'], g, bn, b['net'], t['why']))
                else:
                    tight.append((g, 'track %s [%s] - land %s' % (t['net'], t['why'][:40], bn)))
            for ref, e in NEIGH.items():
                if e['layer'] != 'Top' or ref in CAP_REFS:
                    continue
                g = seg_box(seg, (e['x0'] + e['x1']) / 2, (e['y0'] + e['y1']) / 2, e['x1'] - e['x0'], e['y1'] - e['y0']) - w / 2
                if g < CLR - 1e-9:
                    P.append('track %s Top %.4f from neighbour %s [%s]' % (t['net'], g, ref, t['why']))
        if t['layer'] == 'Bottom':
            for p in BPADS:
                if p['net'] == t['net']:
                    continue
                g = seg_box(seg, p['x'], p['y'], p['sx'], p['sy']) - w / 2
                if g < CLR - 1e-9:
                    P.append('track %s Bottom %.4f from pad %s.%s (%s) [%s]' % (t['net'], g, p['ref'], p['pad'], p['net'], t['why']))
                else:
                    tight.append((g, 'track %s [%s] - Bottom pad %s.%s' % (t['net'], t['why'][:40], p['ref'], p['pad'])))
            for ref, e in NEIGH.items():
                if e['layer'] != 'Bottom' or ref in CAP_REFS:
                    continue
                g = seg_box(seg, (e['x0'] + e['x1']) / 2, (e['y0'] + e['y1']) / 2, e['x1'] - e['x0'], e['y1'] - e['y0']) - w / 2
                if g < CLR - 1e-9:
                    P.append('track %s Bottom %.4f from neighbour %s [%s]' % (t['net'], g, ref, t['why']))
        for v in vias:                       # through vias are on every layer
            if v['net'] == t['net']:
                continue
            g = seg_pt(*seg, v['x'], v['y']) - VIA_R - w / 2
            if g < CLR - 1e-9:
                P.append('track %s %s %.4f from via %s (%.3f,%.3f) [%s]' % (t['net'], t['layer'], g, v['net'], v['x'], v['y'], t['why']))
            else:
                tight.append((g, 'track %s [%s] - via %s (%.2f,%.2f)' % (t['net'], t['why'][:40], v['net'], v['x'], v['y'])))
        for j in range(i + 1, len(tracks)):
            u = tracks[j]
            if u['layer'] != t['layer'] or u['net'] == t['net']:
                continue
            g = seg_seg(seg, (u['x1'], u['y1'], u['x2'], u['y2'])) - w / 2 - u['width'] / 2
            if g < CLR - 1e-9:
                P.append('tracks %s [%s] and %s [%s] on %s %.4f apart' % (t['net'], t['why'][:30], u['net'], u['why'][:30], t['layer'], g))
            else:
                tight.append((g, 'track-track %s/%s on %s' % (t['net'], u['net'], t['layer'])))
    # --- endpoints and connectivity
    key = lambda x, y: (round(x, 3), round(y, 3))
    via_at = {key(v['x'], v['y']): v['net'] for v in vias}
    ball_at = {key(b['x'], b['y']): b['net'] for b in BALLS.values()}
    pad_at = {key(p['x'], p['y']): p['net'] for p in BPADS}
    adj = defaultdict(set)
    for t in tracks:
        a, b = (t['layer'], key(t['x1'], t['y1'])), (t['layer'], key(t['x2'], t['y2']))
        adj[a].add(b); adj[b].add(a)
    for k in via_at:
        for la in ('Top', 'L3-SIG', 'L4-SIG', 'Bottom'):
            for lb in ('Top', 'L3-SIG', 'L4-SIG', 'Bottom'):
                if la != lb:
                    adj[(la, k)].add((lb, k))
    for t in tracks:
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            k = key(x, y)
            ok = via_at.get(k) == t['net'] or (t['layer'] == 'Top' and ball_at.get(k) == t['net']) or \
                (t['layer'] == 'Bottom' and pad_at.get(k) == t['net'])
            if not ok:
                others = [n for n in adj[(t['layer'], k)] if n != (t['layer'], k)]
                ok = len(others) >= 2      # a bend joining two of the plan's own tracks
                if ok:
                    # all tracks meeting here must be the same net
                    nets_here = {u['net'] for u in tracks if u['layer'] == t['layer'] and
                                 (key(u['x1'], u['y1']) == k or key(u['x2'], u['y2']) == k)}
                    if len(nets_here) > 1:
                        P.append('tracks of nets %s meet at (%.3f,%.3f) on %s' % (sorted(nets_here), x, y, t['layer']))
            if not ok and t.get('free_end') and (x, y) == (t['x2'], t['y2']) and not infield(x, y):
                ok = True                  # a declared stub end outside the land field
            if not ok:
                P.append('track %s endpoint (%.3f,%.3f) on %s lands on nothing [%s]' % (t['net'], x, y, t['layer'], t['why']))
    # every via has a track on it (on some layer)
    for v in vias:
        k = key(v['x'], v['y'])
        if not any(key(t['x1'], t['y1']) == k or key(t['x2'], t['y2']) == k for t in tracks if t['net'] == v['net']):
            P.append('via %s (%.3f,%.3f) has no track on it' % (v['net'], v['x'], v['y']))
    # nets never mix through copper: BFS components
    comp_net = {}
    for start in list(adj):
        if start in comp_net:
            continue
        stack = [start]; comp = []
        comp_net[start] = None
        while stack:
            n = stack.pop(); comp.append(n)
            for m in adj[n]:
                if m not in comp_net:
                    comp_net[m] = None; stack.append(m)
        compset = set(comp)
        nets_in = set()
        for la, k in comp:
            if k in via_at:
                nets_in.add(via_at[k])
            if la == 'Top' and k in ball_at and ball_at[k]:
                nets_in.add(ball_at[k])
            if la == 'Bottom' and k in pad_at:
                nets_in.add(pad_at[k])
        for t in tracks:
            if (t['layer'], key(t['x1'], t['y1'])) in compset or (t['layer'], key(t['x2'], t['y2'])) in compset:
                nets_in.add(t['net'])
        if len(nets_in) > 1:
            P.append('copper component mixes nets %s' % sorted(nets_in))
    # every netted ball of ring >= 2, and every power ball of rings 0-1, reaches a same-net via
    POWER = {'GND', 'GNDADC', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VCCADC'}
    for bn, b in BALLS.items():
        if not b['net']:
            continue
        if b['ring'] >= 2 or b['net'] in POWER:
            start = ('Top', key(b['x'], b['y']))
            seen = {start}; dq = deque([start]); hit = False
            while dq and not hit:
                n = dq.popleft()
                if n[1] in via_at and via_at[n[1]] == b['net']:
                    hit = True
                for m in adj[n]:
                    if m not in seen:
                        seen.add(m); dq.append(m)
            if not hit:
                P.append('ball %s (%s, ring %d) reaches no same-net via through the plan copper' % (bn, b['net'], b['ring']))
        if b['ring'] == 2:
            if not any(v['net'] == b['net'] and math.hypot(v['x'] - b['x'], v['y'] - b['y']) < 1.6 for v in vias):
                P.append('ring-2 ball %s (%s) has no same-net via within 1.6 mm' % (bn, b['net']))
        if b['ring'] >= 6 or b['ring'] == 2:
            if not any(t['layer'] == 'Top' and t['net'] == b['net'] and
                       (key(t['x1'], t['y1']) == key(b['x'], b['y']) or key(t['x2'], t['y2']) == key(b['x'], b['y'])) for t in tracks):
                P.append('ball %s (%s) has no Top track on it' % (bn, b['net']))
    # actions cover every ball
    for bn in BALLS:
        if bn not in acts:
            P.append('ball %s has no action' % bn)
    tight.sort()
    return P, W, tight


# ============================================================================
# 10. plane copper in the moat band (rings 3-5) on a GND plane, relief vs direct
def plane_fraction(vias, relief, step=0.01):
    x0 = half(X(3), X(4)); x1 = half(X(16), X(17)); y0 = half(Y('U'), Y('T')); y1 = half(Y('C'), Y('D'))
    cx0 = half(X(6), X(7)); cx1 = half(X(13), X(14)); cy0 = half(Y('N'), Y('P')); cy1 = half(Y('F'), Y('G'))
    nx = int(round((x1 - x0) / step)); ny = int(round((y1 - y0) / step))
    grid = [[1] * nx for _ in range(ny)]
    band = 0
    for iy in range(ny):
        y = y0 + (iy + 0.5) * step
        for ix in range(nx):
            x = x0 + (ix + 0.5) * step
            if cx0 <= x <= cx1 and cy0 <= y <= cy1:
                grid[iy][ix] = -1
            else:
                band += 1
    for v in vias:
        vx, vy = v['x'], v['y']
        if v['net'] == 'GND':
            if not relief:
                rin, rout = 0.0, VIA_HOLE / 2
            else:
                rin, rout = VIA_HOLE / 2 + 0.508, VIA_HOLE / 2 + 0.508 + 0.25
        else:
            rin, rout = 0.0, VIA_HOLE / 2 + 0.25
        ixa = max(0, int((vx - rout - x0) / step) - 1); ixb = min(nx - 1, int((vx + rout - x0) / step) + 1)
        iya = max(0, int((vy - rout - y0) / step) - 1); iyb = min(ny - 1, int((vy + rout - y0) / step) + 1)
        for iy in range(iya, iyb + 1):
            y = y0 + (iy + 0.5) * step
            for ix in range(ixa, ixb + 1):
                x = x0 + (ix + 0.5) * step
                if grid[iy][ix] == -1:
                    continue
                r = math.hypot(x - vx, y - vy)
                if rin <= r <= rout:
                    if v['net'] == 'GND' and relief and (abs(x - vx) < 0.125 or abs(y - vy) < 0.125):
                        continue
                    grid[iy][ix] = 0
    copper = sum(1 for row in grid for c in row if c == 1)
    # connected copper crossing from the band's outer boundary to the core boundary
    seen = [[False] * nx for _ in range(ny)]
    dq = deque()
    for ix in range(nx):
        for iy in (0, ny - 1):
            if grid[iy][ix] == 1 and not seen[iy][ix]:
                seen[iy][ix] = True; dq.append((iy, ix))
    for iy in range(ny):
        for ix in (0, nx - 1):
            if grid[iy][ix] == 1 and not seen[iy][ix]:
                seen[iy][ix] = True; dq.append((iy, ix))
    touch = 0
    while dq:
        iy, ix = dq.popleft()
        for dy_, dx_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            jy, jx = iy + dy_, ix + dx_
            if 0 <= jy < ny and 0 <= jx < nx:
                if grid[jy][jx] == -1:
                    touch += 1
                elif grid[jy][jx] == 1 and not seen[jy][jx]:
                    seen[jy][jx] = True; dq.append((jy, jx))
    return copper / band, touch * step, band * step * step


# ============================================================================
STUB_OUT = 0.10       # a ring-1 stub ends this far outside the land-field box (before any via's bump region)


def place_ring1_stubs(tracks, acts, assign):
    """the fact sheet's 'gap' action: a 3 mil Top stub from the ring-1 ball, 45 deg to the
    interstitial, then straight through the named ring-0 gap to just outside the land field."""
    n_placed = 0
    for n, (s, g) in sorted(assign.items()):
        b = BALLS[n]
        if b['ring'] != 1 or g.startswith(('row ', 'col ')):
            continue
        sd = SIDES[s]
        ga = dict(sd['gaps'])[g]
        bx, by = b['x'], b['y']
        if s == 'W':
            mid, end = (bx - abs(ga - by), ga), (EXT['x0'] - STUB_OUT, ga)
        elif s == 'E':
            mid, end = (bx + abs(ga - by), ga), (EXT['x1'] + STUB_OUT, ga)
        elif s == 'S':
            mid, end = (ga, by - abs(ga - bx)), (ga, EXT['y0'] - STUB_OUT)
        else:
            mid, end = (ga, by + abs(ga - bx)), (ga, EXT['y1'] + STUB_OUT)
        why = '%s ring-1 stub: 45 deg to the interstitial, then through the %s gap (%s) to just outside the field' % (n, g, s)
        trk(b['net'], (bx, by), mid, W3, why)
        trk(b['net'], mid, end, W3, why)
        tracks[-1]['free_end'] = True      # the stub ends in free space outside the field; routing continues it
        acts[n] = ('gap', 'exit %s %s: 3 mil stub placed to (%.4f, %.4f); via left to routing' % (s, g, end[0], end[1]))
        n_placed += 1
    return n_placed


def build_and_check(vias, tracks, acts, quiet=False):
    assign, lp, lreport = ledger(vias, tracks, acts)
    for n, (s, g) in assign.items():
        a, d = acts[n]
        acts[n] = (a, 'exit %s %s' % (s, g))
    place_ring1_stubs(tracks, acts, assign)
    # the ledger must still be feasible with the stubs in as fixed lanes (idempotence)
    assign2, lp2, lreport2 = ledger(vias, tracks, acts)
    P, W, tight = check(vias, tracks, acts)
    return P + lp + lp2, W, tight, assign, lreport2


if __name__ == '__main__':
    problems, warns, tight, assign, lreport = build_and_check(vias, tracks, acts)
    fr_rel, cross_rel, band = plane_fraction(vias, True)
    fr_dir, cross_dir, _ = plane_fraction(vias, False)

    by_net = Counter(v['net'] for v in vias)
    n_gnd = by_net['GND']
    n_out = sum(1 for v in vias if v['cell'] is None)
    n_gnd_out = sum(1 for v in vias if v['cell'] is None and v['net'] == 'GND')
    notes += [
        'MERGE: rings 2-5 and the core follow the moat plan (all 56 ring-2 balls resolved: 48 ring-3 cells, 3 blocked ones as Top pass-throughs to F15/K15/N15, NW GND sharing at D4 D5 D6 E4, row-C and col-3 shifted one cell as diagonals, four outward escapes C17 north / U3 west / U16 south / U17 east). Rings 0-1 power follows the power plan with the outside vias staggered outward so no two on one side that are 0.75 mm apart share a zone.',
        'WHY U17 AND NOT T17 LEAVES EAST: T19 (GND) has no same-net neighbour and needs the row-line via. A row-line via and a half-row via 0.75 mm apart at the same x leave a window of 0.75 - 0.53 = 0.22 mm between their lands, which holds ONE 3 mil track, and the T|U lane plus the U19 exit are two. T17 -> T16 straight; U17 takes the U|V lane (8.15) to (51.40, 8.15) and T19 goes to (51.90, 8.90): 0.90 apart, zones disjoint (0.5 in x >= 0.45).',
        'OUTSIDE VIAS PLACED NOW (rule): only where the ball has no in-array option AND the via position is forced by the land field: ring-0/1 power balls with no same-net neighbour (A1 B1 C1 E1 F1 W1 W12 A19 C19 F19 L19 T19 GND; K1 R1 V1 B19 VCC3V3), the boxed ring-1 necks (H18 P2 V18 GND; V6 V9 V11 VCC3V3) and the four ring-2 outward escapes (their via must be within 1.6 mm of the ball for tools/fanout_emit.py). Every ring-0/1 SIGNAL via is left to routing: its position depends on the route direction, and the ledger shows each such ball keeps a free slot (ring-1 signals get their stub, ring-0 signals nothing).',
        'LANE LEDGER (proved by search in this script): each ring-0 gap carries one 3 mil track; a track 0.25 mm from an outside via bumps 0.053 mm away (0.175 + 0.09 + 0.038 = 0.303 centre distance) and the next slot at 0.5 keeps 0.121; between two outside vias whose outward coordinates differ by < 0.45 the tracks between them must fit sum(w) + 0.09 (n-1) <= d - 0.53 (0.75 apart: one 3 mil track of two slots; 1.0 apart: all three). The assignment found is written into each ball\'s detail and the ring-1 signal balls get their 3 mil stub PLACED (45 deg to the interstitial, through the named gap, ending 0.10 outside the land-field box, before any bump region); their vias are routing\'s. Staggers used: west K1 (40.9) R1 (40.4) V1 (40.9) P2 neck (40.9); east T19 (51.9) H18 neck (51.9); south W12 (y 6.25) V18 neck (y 6.35). The east side has one spare gap: A|B and B|C are dead between the 0.5-pitch A19/B19/C19 vias (B18 goes north, C18 goes diagonally into B19), leaving C|D..V|W (16) for D18..U18 (13 signals), the H18 neck (G|H) and the U17 lane (U|V); V|W is spare because V18 necks south.',
        'NORTH SIDE: U4 is a wide SOIC-8 whose pads sit at x 43.10..44.60 (pads 1-4) and 50.40..51.905 (pads 5-8) with the south copper edge at y 17.215; between x 44.6 and 50.4 only the body is above the corridor, so A14 A15 A16 A17 and the B15 B16 B17 gap lanes (48.65 49.15 49.65) run straight north under the body (CHAN2-5 end on X2 pads 5-8 at the top edge, x 41.9..49.5). The JA4 via at (50.15, 16.78) is forced (C17 has no other cell; its via must be within 1.6 mm) and is a full barrier at that x (16.78 + 0.303 + 0.038 = 17.12 > 17.215 - 0.09). A18 (x 50.4) runs into U4 pad 5 and must go EAST above A19 (y >= 16.641 for 0.09 to the A19 land), B18 through the A18|A19 gap likewise: two corridor tracks at 16.65 and 16.82, bumping to 16.70 and 16.87 past the A19 row-line via, then north between U4 pad 5 (x <= 51.905) and C93 (x >= 52.35): 0.445 mm, exactly two 3 mil tracks. This is why A19 keeps a row-line via and not a corner via. The B14 GND thread uses the corridor floor from x 48.15 to 47.15 only, where nothing else exits north.',
        'GND VIAS: %d (%d in rings 2-5/core incl. the N6/L14 stitches, %d outside for the rings 0-1 GND balls that have no same-net neighbour). GNDADC has its own via D11 and never touches GND. A 0.20/0.35 through via in the 1.65 mm laminate is ~1 nH / ~1.5 mohm; the count is set by isolated balls and by decoupling-loop length (every Bottom 0201 GND pad under the die has a GND via within 0.7 mm with a stub placed), not by current.' % (n_gnd, n_gnd - n_gnd_out, n_gnd_out),
        'PLANE RASTER (this script, 10 um, one GND plane, moat band rings 3-5 = %.1f mm2): copper left with the present Relief rule (1.716 mm OD voids on GND vias) %.1f %%, with Direct on vias %.1f %%; connected copper crossing into the core: relief %.2f mm, direct %.2f mm. RECOMMENDATION: add PlaneConnect_Vias (scope IsVia, Direct, priority above the Relief rule), keep Relief for through-hole pads (X2, X4). Tented, never-soldered vias have no thermal reason for reliefs. Secondary lever: PlaneClearance 0.25 -> 0.20 (JLC minimum) widens every ring-3 bridge from 0.30 to 0.40 mm.' % (band, fr_rel * 100, fr_dir * 100, cross_rel, cross_dir),
        'VCC3V3 NECKS: only V6 V9 V11 neck to 3 mil (through W5|W6, W8|W9, W10|W11 to vias at y 6.9). C18 is boxed orthogonally but B19 is VCC3V3 diagonally: a 0.20 diagonal clears B18 and C19 by 0.141, so it is not a neck. M17 -> M16 -> N15 runs 0.15 (0.104 to the N16 via). All other VCC3V3 copper is 0.20.',
        'DIAGONAL WIDTHS: a diagonal between two foreign balls clears them by 0.354 - 0.1125 - w/2: 0.141 at 0.20; a diagonal beside a foreign VIA clears 0.354 - 0.175 - w/2: 0.104 at 0.15, 0.079 at 0.20 (fails). Hence 0.15 for every power diagonal that flanks a via, 0.20 for the B9/B11 -> C10 and C18 -> B19 diagonals, 3 mil for signals.',
        'UNDER-DIE CAPS, all placed: GND C96-2 <- F7, C92-2 <- F11, C95-2 <- F15, C90-2 <- N6, C89-2 <- K11, C91-2 <- L14; VCC1V0 C92-1 <- F10, C89-1 <- K10, C90-1 and C91-1 by the Bottom trunk from C89-1 (y 11.45 over the pad tops, 0.175; y 11.05 past the L14 via at 0.10); VCC1V8 C95-1 <- G14 (via F14), C96-1 <- E5 (new ring-4 via, fed D8 -> E8 -> E5 on L3 at 0.15 with 0.25 to the D/F-row vias). Ring-0/1 caps C107-C115 are left to routing.',
        'LEFT TO ROUTING: every escape below the vias (L3/L4/Bottom): between adjacent ring-3 vias no lane passes on any layer, three 3 mil lanes pass between vias 1.0 mm apart, one between vias 0.75 mm apart; the rail feeds into the core (Width_PWR_VCC3V3 mid-layer min 1.05 and Width_PWR_VCC1V0 mid-layer min 0.50 cannot pass the wall, so VCC3V3/VCC1V0 come in on Bottom, min 0.20/0.15, or those minima are re-derived); the GNDADC trace from D11 to C123/C124/L6; all ring-0/1 signal exits and their vias (slots named in the balls list); the north corridor problem above; the outer cap ties.',
    ]
    plan = {'vias': vias, 'tracks': tracks,
            'balls': [{'name': n, 'net': BALLS[n]['net'], 'ring': BALLS[n]['ring'], 'action': acts[n][0], 'detail': acts[n][1]}
                      for n in sorted(BALLS, key=lambda n: (ROWS.index(n[0]), int(n[1:])))],
            'notes': notes,
            'counts': {'vias': len(vias), 'tracks': len(tracks), 'gnd_vias': n_gnd, 'vias_by_net': dict(sorted(by_net.items())),
                       'vias_outside': n_out, 'moat_cells_used': sum(1 for v in vias if v['cell'] and VACANT[v['cell']]['ring'] in (3, 4, 5)),
                       'ring3_cells_used': sum(1 for v in vias if v['cell'] and VACANT[v['cell']]['ring'] == 3),
                       'ring4_cells_used': sum(1 for v in vias if v['cell'] and VACANT[v['cell']]['ring'] == 4),
                       'ring5_cells_used': sum(1 for v in vias if v['cell'] and VACANT[v['cell']]['ring'] == 5),
                       'tracks_by_layer': dict(Counter(t['layer'] for t in tracks)),
                       'actions': dict(Counter(a for a, _ in acts.values()))},
            'check': {'problems': problems, 'warnings': warns, 'tightest': ['%.4f %s' % (g, s) for g, s in tight[:15]],
                      'tightest_by_kind': {k: '%.4f %s' % min((g, s) for g, s in tight if s.startswith(k))
                                           for k in ('via-via', 'via ', 'track ', 'track-track')},
                      'ledger': lreport,
                      'plane': {'band_mm2': round(band, 2), 'copper_relief': round(fr_rel, 4), 'copper_direct': round(fr_dir, 4),
                                'crossing_mm_relief': round(cross_rel, 2), 'crossing_mm_direct': round(cross_dir, 2)}}}
    json.dump(plan, io.open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote', os.path.normpath(OUT))
    print(json.dumps(plan['counts'], indent=1))
    for line in lreport:
        print(' ', line)
    print('plane band %.2f mm2: relief %.1f%% copper (%.2f mm crossing), direct %.1f%% (%.2f mm crossing)' % (
        band, fr_rel * 100, cross_rel, fr_dir * 100, cross_dir))
    print('PROBLEMS: %d' % len(problems))
    for p in problems:
        print('  !!', p)
    print('WARNINGS: %d' % len(warns))
    for w in warns:
        print('  --', w)
    print('TIGHTEST (mm above the rule):')
    for g, s in tight[:12]:
        print('   %.4f %s' % (g, s))

    if '--selftest' in sys.argv:
        print('--- selftest: planted faults must be reported ---')
        v2 = copy.deepcopy(vias); t2 = copy.deepcopy(tracks); a2 = dict(acts)
        v2.append({'net': 'D0', 'x': 44.65, 'y': 14.65, 'cell': None, 'why': 'interstitial'})
        v2.append({'net': 'D1', 'x': cell('E6')[0], 'y': cell('E6')[1], 'cell': 'E6', 'why': 'blocked cell'})
        v2.append({'net': 'D2', 'x': cell('R5')[0] + 0.2, 'y': cell('R5')[1], 'cell': None, 'why': 'interstitial + pitch'})
        v2.append({'net': 'D3', 'x': X(19) + PITCH, 'y': Y('T') - 0.25, 'cell': None, 'why': 'outside via 0.75 from the JA10 via, same zone'})
        t2.append({'net': 'D4', 'x1': cell('C8')[0], 'y1': cell('C8')[1], 'x2': cell('D7')[0], 'y2': cell('D7')[1], 'layer': 'Top', 'width': 0.2, 'why': 'fat diagonal on a foreign ball'})
        t2.append({'net': 'VCC1V0', 'x1': 43.0, 'y1': 9.0, 'x2': 43.0, 'y2': 9.3, 'layer': 'Top', 'width': W3, 'why': 'under the VCC1V0 minimum, dangling'})
        t2.append({'net': 'GND', 'x1': cell('C12')[0], 'y1': cell('C12')[1], 'x2': cell('C11')[0], 'y2': cell('C11')[1], 'layer': 'Top', 'width': 0.2, 'why': 'GND onto GNDADC ball'})
        t2.append({'net': 'GND', 'x1': 44.5, 'y1': 14.45, 'x2': 44.9, 'y2': 14.45, 'layer': 'Bottom', 'width': 0.15, 'why': 'over C96 pad 1 (VCC1V8)'})
        t2 = [t for t in t2 if not (t['net'] == 'A10' and t['layer'] == 'Top')]   # strip U3's escape
        pr, _, _, _, _ = build_and_check(v2, t2, a2)
        for p in pr:
            print('  caught:', p)
        print('selftest caught %d problems' % len(pr))
    sys.exit(1 if problems else 0)
