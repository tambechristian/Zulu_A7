# -*- coding: utf-8 -*-
"""Stage 2 FINAL (judge): VCC1V0, VCC1V8, VCCADC, GNDADC -- writes tools/stage2_route.json.
Record: docs/stage2_rails.md.  Needs lib.py and segw.py beside it.

Base: s2_bottomdirect (VCC1V0 on Bottom, no inner copper, no layer change between L3-2 and U1),
rebuilt segment by segment with every width measured (lib.Plan.run: route_emit's own distance code,
clearance target 0.12 mm, relaxed only where the geometry forces it and reported).

REMEDY (b), no rule change: the BTN fan-out via (49.4001,10.400) moves 0.055 mm south to
(49.4001,10.345) with its 3 mil Top dogbone.  That opens the one Bottom gate into U1's VCC1V0 island
(C91-2's GND pad vs the BTN via) from 0.140 mm to 0.195 mm, so the whole feed is inside
Width_PWR_VCC1V0 (Bottom min 0.15).  The via keeps 0.445 mm to FT-PWREN# (49.4001,9.9) -- the 0.44 pitch.
"""
import io, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import Plan, INP0


def pad(ref, name, key=None):
    for k in (key,) if key else ('top_pads', 'bottom_pads', 'th_pads'):
        for p in INP0[k]:
            if p['ref'] == ref and str(p['pad']) == str(name):
                return (p['x'], p['y'])
    raise KeyError((ref, name))


REMOVE = {'vias': [dict(net='BTN', x=49.4001, y=10.4)],
          'tracks': [dict(net='BTN', layer='Top', x1=49.4001, y1=10.4, x2=49.9, y2=10.4)]}
P = Plan(REMOVE, replace_vias=[dict(net='BTN', x=49.4001, y=10.345)],
         replace_tracks=[dict(net='BTN', layer='Top', x1=49.4001, y1=10.345, x2=49.9, y2=10.4, width=0.0762)])
run, via = P.run, P.via

L3_2 = pad('L3', 2)
C91_1 = pad('C91', 1)
# ============================================================== VCC1V0 (367 mA)
V0 = 'VCC1V0'
# A. trunk, all Bottom: L3-2 -> U3's belly -> over the SDRAM via column -> over the x 41.4 GND via
#    column -> U1's north strip (inside the land field) -> east flank -> the BTN gate -> C91-1
run(V0, 'Bottom', [L3_2, (36.60, 14.49)], 1.50, 'trunk belly')
run(V0, 'Bottom', [(36.60, 14.49), (37.85, 15.85)], 1.50, 'trunk up to the SDRAM gap')
run(V0, 'Bottom', [(37.85, 15.85), (39.60, 15.85)], 1.50, 'trunk SDRAM gap')
run(V0, 'Bottom', [(39.60, 15.85), (40.90, 17.30)], 1.50, 'trunk up over GND column')
run(V0, 'Bottom', [(40.90, 17.30), (41.50, 17.30)], 1.50, 'trunk over (41.4,16.4)')
run(V0, 'Bottom', [(41.50, 17.30), (42.00, 17.00)], 1.50, 'trunk down past C120')
run(V0, 'Bottom', [(42.00, 17.00), (42.80, 16.00)], 1.50, 'trunk into the strip')
run(V0, 'Bottom', [(42.80, 16.00), (43.60, 15.935)], 1.50, 'trunk strip W')
run(V0, 'Bottom', [(43.60, 15.935), (48.30, 15.935)], 1.20, 'trunk north lane')
run(V0, 'Bottom', [(48.30, 15.935), (49.60, 15.935)], 1.20, 'trunk north lane E (D15)')
run(V0, 'Bottom', [(49.60, 15.935), (50.23, 15.30)], 1.20, 'trunk descent')
run(V0, 'Bottom', [(50.23, 15.30), (50.23, 10.85)], 1.20, 'trunk east flank')
run(V0, 'Bottom', [(50.23, 10.85), (49.70, 10.7075)], 1.50, 'neck approach', clr=0.12, floor=0.10)
run(V0, 'Bottom', [(49.70, 10.7075), (49.18, 10.7075)], 1.50, 'NECK C91-2 pad / BTN via', clr=0.10, floor=0.10)
run(V0, 'Bottom', [(49.18, 10.7075), (48.95, 10.84)], 1.50, 'neck exit', clr=0.10, floor=0.10)
run(V0, 'Bottom', [(48.95, 10.84), C91_1], 0.30, 'into C91-1 (0201: <= 0.30)', clr=0.10, floor=0.10)
# B. inside the cage (Bottom), paralleling the existing 0.15 chain and the Top ball chain.  Only the
#    south of U1's inner via square is used: a copper route through its north half (tried) walls VCC3V3
#    out of its own fan-out vias (48.4,11.9) and (47.4/47.9,13.9) -- U1-K12/K13/L12/L13/M12/G12/G13 fell
#    from 0.525 to 0.175 mm in route_width; with this route they keep 0.463 (VCC1V0 +0.56 mV).
run(V0, 'Bottom', [C91_1, (48.40, 10.93)], 0.30, 'cage: out of C91-1 (<= 0.30)', floor=0.09)
run(V0, 'Bottom', [(48.40, 10.93), (47.95, 10.95)], 0.47, 'cage: through the x 48.4 gate', floor=0.09)
run(V0, 'Bottom', [(47.95, 10.95), (47.60, 11.50), (46.75, 11.50), (46.4001, 11.8999)], 0.47, 'cage: past C89-2 onto via 46.4,11.9', floor=0.09)
run(V0, 'Bottom', [(46.4001, 9.8999), (46.25, 10.30), (46.25, 11.30), (46.59, 11.45)], 0.30, 'cage: S bar via 46.4,9.9 -> chain node (46.59,11.45)', floor=0.09)
run(V0, 'Bottom', [(46.4001, 9.8999), (46.90, 9.8999)], 0.35, 'cage: feed via 46.9,9.9', floor=0.09)
# C. the north bulk caps C87/C88 (boxed in the second cap row): one column up the 0201 gap and under
#    U4-4..U4-1 (dead stitching zone), then C101's own 0.60 pad gap; a branch east at y 19.80 (0.70 below
#    cap row 1, so C102-1 keeps a VCC3V3 via site) to C102's gap.  0.20 mm, 0.20 from the pads each side.
C87_1 = pad('C87', 1)
C88_1 = pad('C88', 1)
run(V0, 'Bottom', [(43.60, 15.935), (43.56, 18.60), (44.30, 19.30), (44.30, 19.80)], 0.20, 'C87/C88 column under U4-1..4', clr=0.15)
run(V0, 'Bottom', [(44.30, 19.80), (44.30, 22.40), C87_1], 0.20, 'C87 up C101 gap', clr=0.15)
run(V0, 'Bottom', [(44.30, 19.80), (47.40, 19.80)], 0.20, 'C88 branch under U4 (0.70 below row 1: C102-1 keeps a via site)', clr=0.15)
run(V0, 'Bottom', [(47.40, 19.80), (47.40, 22.40), C88_1], 0.20, 'C88 up C102 gap', clr=0.15)
# D. the east 22 uF bank.  C143-1 is boxed on Top except to the west, row 1 (C140-C142) except to the
#    south, row 3 (C85/C86) except to the east.  One via each: VB143 west of C143 (fed on Bottom from the
#    flank), VR1 under row 1 (in the 0.85 mm Top band above VU), VR3 east of row 3; joined on L3 (0.50,
#    the inner minimum) under the array's x 53.0 column (x 53.6) and its row gap y 11.65, where no
#    stitching or escape via site exists.
via(V0, 51.90, 9.445)   # 0.545 from the GND via (51.9,8.9): its kill circle mostly overlaps that via's own
run(V0, 'Bottom', [(50.23, 10.85), (50.60, 10.20), (51.00, 9.45), (51.90, 9.445)], 0.25, 'bank link from the flank (AC only)')
run(V0, 'Top', [(51.90, 9.445), pad('C143', 1)], 0.30, 'C143-1 stub')
via(V0, 53.60, 4.80)   # under C140-1: leaves R22-2 (CFG-M2) its via site north of the resistor
via(V0, 57.80, 12.45)
run(V0, 'L3-SIG', [(51.90, 9.445), (53.60, 9.445)], 0.50, 'bank L3 VB143 east')
run(V0, 'L3-SIG', [(53.60, 4.80), (53.60, 9.445)], 0.50, 'bank L3 under the x 53.0 column S')
run(V0, 'L3-SIG', [(53.60, 9.445), (53.60, 11.65)], 0.50, 'bank L3 under the x 53.0 column N')
run(V0, 'L3-SIG', [(53.60, 11.65), (57.80, 11.65), (57.80, 12.45)], 0.50, 'bank L3 row gap to VR3')
run(V0, 'Top', [(53.60, 4.80), pad('C140', 1)], 0.40, 'row 1 stub')
run(V0, 'Top', [pad('C142', 1), pad('C141', 1), pad('C140', 1)], 0.50, 'row 1 C142 C141 C140')
run(V0, 'Top', [(57.80, 12.45), pad('C86', 1), pad('C85', 1)], 0.50, 'row 3 C86 C85')
# E. X2-19 monitor pin (no current): Bottom up the free x 15.3 channel and along the X2 pin row, on the
#    same centreline as VCC1V8's L3 lane so the two share one stitching shadow
run(V0, 'Bottom', [L3_2, (15.30, 15.60), (15.30, 23.05), (3.81, 23.05), pad('X2', 19)], 0.20, 'X2-19 tap (under the VCC1V8 L3 lane)')

# ============================================================== VCCADC / GNDADC
VA, GA = 'VCCADC', 'GNDADC'
L7_2 = pad('L7', 2)
C123_1 = pad('C123', 1)
C123_2 = pad('C123', 2)
C124_1 = pad('C124', 1)
C124_2 = pad('C124', 2)
L6_2 = pad('L6', 2)
run(VA, 'Bottom', [L7_2, C123_1], 0.60, 'L7-2 to C123-1')
run(GA, 'Bottom', [L6_2, C124_2], 0.40, 'L6-2 to C124-2')
via(VA, 53.34, 2.30)
via(GA, 56.20, 4.80)
via(VA, 47.80, 5.25)
via(GA, 48.35, 5.00)
run(VA, 'Bottom', [C123_1, (53.34, 2.30)], 0.30, 'C123-1 to its via')
run(GA, 'Bottom', [C123_2, (55.75, 3.05), (56.20, 3.50), (56.20, 4.80)], 0.30, 'C123-2 to its via')
run(VA, 'Bottom', [C124_1, (47.80, 5.25)], 0.30, 'C124-1 to its via')
run(GA, 'Bottom', [C124_2, (48.35, 5.00)], 0.30, 'C124-2 to its via')
# C123 -> C124 on L3 under VU's Top trunk (no stitching or escape sites there), 0.40 apart
run(VA, 'L3-SIG', [(53.34, 2.30), (53.34, 3.90), (47.80, 3.90), (47.80, 5.25)], 0.20, 'VCCADC L3 C123 -> C124 (under VU)')
run(GA, 'L3-SIG', [(56.20, 4.80), (55.70, 4.30), (48.85, 4.30), (48.35, 5.00)], 0.20, 'GNDADC L3 C123 -> C124 (under VU)')
# C124 -> U1: the only crossing of U1's south escape ring, 0.15 mm tracks 0.30 apart, hugging the dead
# circle of the GND via (47.4,6.25); then inside the land field (no stitching or escape-slot cost):
# the field's south strip, the east flank, the north strip, onto the fan-out vias (47.4,14.9)/(46.9,14.9)
run(VA, 'L3-SIG', [(47.80, 5.25), (47.80, 7.35)], 0.15, 'VCCADC L3 south-ring crossing')
run(GA, 'L3-SIG', [(48.35, 5.00), (48.35, 5.40), (48.10, 5.75), (48.10, 7.35)], 0.15, 'GNDADC L3 south-ring crossing')
run(VA, 'L3-SIG', [(47.80, 7.35), (47.80, 8.05), (50.33, 8.05), (50.33, 15.45), (47.40, 15.45), (47.4001, 14.8999)], 0.20, 'VCCADC L3 to U1-C13 (in the field)')
run(GA, 'L3-SIG', [(48.10, 7.35), (48.10, 7.70), (50.68, 7.70), (50.68, 15.80), (46.90, 15.80), (46.9, 14.8999)], 0.20, 'GNDADC L3 to U1-C12 (in the field)')

# ============================================================== VCC1V8 (77 mA max)
V8 = 'VCC1V8'
via(V8, 1.10, 9.30)
run(V8, 'Bottom', [pad('L2', 2), (1.10, 9.30)], 0.40, 'V8 block to via')
run(V8, 'L3-SIG', [(1.10, 9.30), (0.50, 9.90), (0.50, 23.05), (6.35, 23.05)], 0.30, 'V8 west edge (inside the 0.8 mm plane pullback)')
run(V8, 'L3-SIG', [(6.35, 23.05), pad('X2', 18)], 0.30, 'V8 X2-18')
run(V8, 'L3-SIG', [(6.35, 23.05), (15.30, 23.05), (15.30, 17.50)], 0.30, 'V8 over the X2-19 tap, along the X2 pin row')
run(V8, 'L3-SIG', [(15.30, 17.50), (39.30, 17.50)], 0.80, 'V8 under U3 north pads')
run(V8, 'L3-SIG', [(39.30, 17.50), (40.50, 18.40), (40.50, 21.75), (44.00, 21.75)], 0.60, 'V8 through Q1 / cap rows')
run(V8, 'L3-SIG', [(44.00, 21.75), (49.95, 21.75)], 0.60, 'V8 between the cap rows')
run(V8, 'L3-SIG', [(44.00, 21.75), (44.00, 16.20), (45.40, 15.50), (45.4001, 14.8999)], 0.40, 'V8 drop to C9 group')
run(V8, 'L3-SIG', [(45.4001, 14.4000), (48.40, 14.40), (48.4001, 13.4000)], 0.20, 'V8 join C9 and H13 groups')
via(V8, 50.50, 19.40)   # between U4-6 and U4-7, so C103-1 keeps its south side
run(V8, 'L3-SIG', [(49.95, 21.75), (50.50, 21.20), (50.50, 19.40)], 0.40, 'V8 to C94 via')
run(V8, 'Bottom', [(50.50, 19.40), (50.50, 22.40), pad('C94', 1)], 0.20, 'V8 C94 up C103 gap', clr=0.15)
via(V8, 51.95, 15.75)
run(V8, 'L3-SIG', [(50.50, 19.40), (51.30, 18.60), (51.95, 17.00), (51.95, 15.75)], 0.20, 'V8 to C93 via (25 mA)')
run(V8, 'Top', [(51.95, 15.75), pad('C93', 1)], 0.30, 'V8 C93-1 stub')
via(V8, 58.30, 10.00)
via(V8, 50.80, 2.30)
run(V8, 'L4-SIG', [(51.95, 15.75), (55.70, 15.75), (55.70, 10.00)], 0.40, 'V8 L4 under the array (col gap x 55.7)')
run(V8, 'L4-SIG', [(55.70, 10.00), (58.30, 10.00)], 0.40, 'V8 L4 to C144 via')
run(V8, 'Top', [(58.30, 10.00), (54.8002, 10.00), pad('C144', 1)], 0.15, 'V8 C144-1 through C145 gap', clr=0.12)
run(V8, 'L4-SIG', [(55.70, 10.00), (55.70, 2.90), (50.80, 2.90), (50.80, 2.30)], 0.40, 'V8 L4 to L7 via (under VU)')
run(V8, 'Bottom', [(50.80, 2.30), pad('L7', 1)], 0.30, 'V8 L7-1 stub')

if __name__ == '__main__':
    P.dump(os.path.join(os.path.dirname(HERE), 'stage2_route.json'))
    print('%d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
    P.print_report(only_tight='--all' not in sys.argv)
    print('segments below their rule minimum: %d' % sum(1 for r in P.REPORT if r['short']))
