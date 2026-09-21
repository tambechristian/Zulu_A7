import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 4a was planned in a scratch tree)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4'); from lib import Plan, INP0
# Stage 4a, region EAST: the 20 GND pads east of U1 (x 52.5-69.85).  GND only, additions only.
#   route_emit joins a new track end only at a via centre / TH pad centre / SMD pad CENTRE / existing track end,
#   so every tie starts at its pad's centre.
#   The 3x4 grid of 1206 caps (x 53.0/54.8/56.6, y 7.55/10.85/14.149/17.449) has 0.30 mm gaps: no via fits
#   inside it.  Its west edge (x 52.25) faces U1's east-escape strip: only the existing fan-out via (51.9,13.15)
#   is used there (the via (51.9,8.9) is reachable only through the JA1/JA2 escape pocket x 51.8-52.0,
#   y 7.85-8.45 -- a tie there forecloses U18/U19, tested 2026-09-21).  Row 1's east end is sealed by the Top
#   VCC3V3 track at x 58.0 (y 5.5-9.15), so row 1 chains west to a new via south-west of C140-2, in the slot
#   the Bottom VCC3V3 y 7.05 feed already denies to escape vias.  Rows 2-3 chain east to vias hugging the
#   grid at x 57.65; row 4 has open sites north of it.
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
G = 'GND'
P = Plan()
V = {}
def via(tag, x, y):
    V[tag] = (x, y); P.via(G, x, y)
def pad(name):
    r, n = name.split('-')
    p = next(p for k in ('top_pads', 'bottom_pads') for p in INP0[k] if p['ref'] == r and str(p['pad']) == n)
    return (p['x'], p['y'])
# --- new vias -----------------------------------------------------------------------------------------
via('r1w', 51.90, 6.40)     # row 1 (C140-2 chain)  SW of C140-2: 0.125 to the Bottom VCC3V3 x 52.6 run, 0.175 to C140-1
via('r2a', 57.65, 10.60)    # C145-2 (Top)          east of the grid, between Top VCC1V8 y 10.0 and L3 VCC1V0 y 11.65
via('r2b', 57.65, 11.05)    # C119-2 (Bottom 0201)  same slot, 0.45 north
via('r3a', 57.65, 14.149)   # C86-2 (Top)           east of the grid, straight east of the pad
via('r3b', 57.65, 14.60)    # C121-2 (Bottom 0201)  0.451 north of r3a, 0.378 under R4-16
via('r1e', 58.45, 7.65)     # C122-2 (Bottom 0201)  east of the Top VCC3V3 x=58.0 track (the only side open)
via('r4a', 53.85, 18.40)    # C93-2   north of row 4, 0.173 from the 1.5 mm VCC3V3 Top trunk cap at (52.93,19.0)
via('r4b', 54.80, 18.40)    # C97-2
via('r4c', 56.60, 18.40)    # C98-2
via('c104', 54.45, 20.30)   # C104-2 (Bottom)  south of the pad, the only free side
via('c105', 57.55, 20.30)   # C105-2 (Bottom)  south of the pad, 0.275 west of R4-10
via('c99', 55.45, 23.00)    # C99-2  (Bottom)  north-east of the pad, between the Top y 22.5 run and X2-3
via('r5', 60.10, 14.17)     # R5-1   (Bottom)  in the R33/R5 0201 row, between R33-2 and R5-1
via('r22', 54.30, 4.80)     # R22-1  (Bottom)  north of R22, 0.7 east of the VCC1V0 via (53.6,4.8), under the VU/VCC1V0 gap
# --- ties (each starts at the pad centre) --------------------------------------------------------------
def tie(name, layer, pts, wish, to=None):
    P.run(G, layer, [pad(name)] + pts, wish=wish, tag=name + '>' + (to or ''))
# row 1 (y 7.55): C142-2 > C141-2 > C140-2 > r1w (west round C140-1's NW corner)
tie('C140-2', 'Top', [(52.0, 7.2), V['r1w']], 0.5, 'r1w')
tie('C141-2', 'Top', [pad('C140-2')], 0.5, 'C140-2')
tie('C142-2', 'Top', [pad('C141-2')], 0.5, 'C141-2')
# row 2 (y 10.85): C143-2 > C144-2 > C145-2 > r2a
tie('C145-2', 'Top', [V['r2a']], 0.5, 'r2a')
tie('C144-2', 'Top', [pad('C145-2')], 0.5, 'C145-2')
tie('C143-2', 'Top', [pad('C144-2')], 0.5, 'C144-2')
# row 3 (y 14.149): C146-2 west to the existing fan-out via (51.9,13.15); C85-2 > C86-2 > r3a
tie('C146-2', 'Top', [(51.95, 13.45), (51.9, 13.15)], 0.5, 'via51.9,13.15')
tie('C86-2', 'Top', [V['r3a']], 0.5, 'r3a')
tie('C85-2', 'Top', [pad('C86-2')], 0.5, 'C86-2')
# row 4 (y 17.449): one via north of each pad
tie('C93-2', 'Top', [V['r4a']], 0.5, 'r4a')
tie('C97-2', 'Top', [V['r4b']], 0.5, 'r4b')
tie('C98-2', 'Top', [V['r4c']], 0.5, 'r4c')
# the three Bottom 0201s under the grid: east along their own row to the via (Bottom is open under the grid)
tie('C122-2', 'Bottom', [V['r1e']], 0.3, 'r1e')
tie('C119-2', 'Bottom', [V['r2b']], 0.3, 'r2b')
tie('C121-2', 'Bottom', [V['r3b']], 0.3, 'r3b')
# north cluster
tie('C104-2', 'Bottom', [V['c104']], 0.5, 'c104')
tie('C105-2', 'Bottom', [V['c105']], 0.5, 'c105')
tie('C99-2', 'Bottom', [V['c99']], 0.5, 'c99')
# resistors
tie('R5-1', 'Bottom', [V['r5']], 0.3, 'r5')
tie('R22-1', 'Bottom', [(53.55, 4.22), V['r22']], 0.3, 'r22')   # between the VCC1V0 via land and R22-2
# --- write and report ---------------------------------------------------------------------------------
P.dump(os.path.join(HERE, 'plan.json'))
P.print_report()
print('%d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
pads = [(p, 'Top') for p in INP0['top_pads']] + [(p, 'Bottom') for p in INP0['bottom_pads']]
def rect_d(x, y, p):
    return math.hypot(max(abs(x - p['x']) - p['sx'] / 2, 0.0), max(abs(y - p['y']) - p['sy'] / 2, 0.0))
for tag, (x, y) in V.items():
    d, who = min(((rect_d(x, y, p) - 0.175, '%s-%s %s' % (p['ref'], p['pad'], L)) for p, L in pads), key=lambda t: t[0])
    dv = min([math.hypot(x - v['x'], y - v['y']) for v in INP0['vias']] + [math.hypot(x - a, y - b) for t, (a, b) in V.items() if t != tag])
    print('via %-5s (%.3f,%.3f)  land-to-pad-edge %.3f (%s)  nearest via c-c %.3f' % (tag, x, y, d, who, dv))
