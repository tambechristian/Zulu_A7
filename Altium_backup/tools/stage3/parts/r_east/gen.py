import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
# -*- coding: utf-8 -*-
"""Stage 3, REGION "east" (x 52-69.85, y 0-25.4; 20 mA max): the 1206 caps C97/C98/C145/C146 (Top), the
south-east pull-ups R20/R23/R1 and JP4-3, the north-east pull-ups R2/R6/R7/R94/R99/R91/R92/R93/R90,
R4-8 (Top) and the Pmod power pins J1-6/J1-12.

    python gen.py            writes plan.json next to this file, prints the tight segments
    python gen.py --all      prints every segment

Built on the judge's hybrid trunk (s3_trunk/plan.json md5 a8bb54e8...): the u1field column is 0.70 mm on
x 52.60 (edges 52.25-52.95) with nodes (52.6, 14.45), (52.6, 11.05) and its free end (52.6, 7.65).
The first segment starts at the tap (53.2, 22.5) Top (the free end of the trunk's 1.495 mm Top run at
y 22.5).  Four vias, no inner-layer copper, every run placed where the board is already dead for GND
stitching:
  A (58.45, 22.55)  on the Top trunk itself; its Bottom side feeds every north-east 0201 pull-up and J1;
                    its Top side feeds R4-8 along y 21.6 (leaves the via row y 22-23.1 east of x 58.9)
  B (58.00, 5.50)   at the east end of the south Bottom bus (the bus lies under the C140-C142 pads' dead
                    zone); its Top side feeds C145-1 from the east, the only open side of that pad
  D (57.675, 15.749) in the 0.65 mm gap between C98-2 and the R4 array, fed on Bottom from the y 17.55
                    row bus; its Top side is the 1.1 mm into C98-1, then C98-1 -> C97-1 on the pad row
  C (51.95, 12.45)  level with C146-1's centre, 0.125 west of the pad's edge and 0.352 from the GND via
                    (51.9, 13.15): C143-2 (GND, y <= 11.5) and C146-1 (y >= 11.8) are 0.30 apart, so the
                    old corner site (52.0, 11.65) had 0.117 to both; this one keeps every gap >= 0.12.
                    Fed on Bottom from the column node (52.6, 11.05); its Top side runs straight east
                    into the pad centre.  The via centre is 0.05 mm west of the box edge x 52.0 (the
                    land of the old site was 0.175 outside it).
"""
import io, json, os, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3')
from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
OUT = os.path.join(HERE, 'plan.json')
V = 'VCC3V3'
T, B = 'Top', 'Bottom'


def pad(ref, num):
    """exact centre of a pad from the board file (route_emit anchors track ends on pad centres)"""
    for key in ('top_pads', 'bottom_pads', 'th_pads'):
        for p in INP0[key]:
            if p['ref'] == ref and str(p['pad']) == str(num):
                return (p['x'], p['y'])
    raise KeyError((ref, num))


def run(layer, pts, wish, tag, clr=0.12):
    P.run(V, layer, pts, wish, tag, clr, 0.09)


def via(x, y):
    P.via(V, x, y)


# ------------------------------------------------------------------------------------------------
# 1. TOP TRUNK east from the tap under X2's north pins (0.5 wide, 20 mA: 0.57 to the X2 pads instead of
#    the trunk's 0.12) to via A; R4-8 is fed from via A along y 21.6, just above R4-9, so the via row
#    y 22.0-23.1 east of x 58.9 stays open for GND stitching.
# ------------------------------------------------------------------------------------------------
TAP = (53.2, 22.5)
VA = (58.45, 22.55)
# MERGE 2026-09-21: 0.3, not 0.5 (20 mA: 0.17 mV over 5.25 mm); the whole-board merge broke the 75 % / 65 % stitching
# floors, and this run's 0.5 killed the y 23.0 row of sites north of C99-2 / C104-2.
run(T, [TAP, VA], 0.3, 'Top trunk east of the tap to via A (0.3: keeps the y 23.0-23.2 via sites north of C99-2 and C104-2 open)')
via(*VA)
R4_8 = pad('R4', '8')
run(T, [VA, (58.85, 21.6), (R4_8[0], 21.6), R4_8], 0.4, 'via A along y 21.6 into R4-8')

# ------------------------------------------------------------------------------------------------
# 2. NORTH-EAST pull-ups on Bottom from via A.  Every pin 2 (VCC3V3) is the east pad of its 0201, so
#    the row joins run one row-gap above each row and drop into the pads.
# ------------------------------------------------------------------------------------------------
R7, R6, R2 = pad('R7', '2'), pad('R6', '2'), pad('R2', '2')
run(B, [VA, R7], 0.3, 'via A -> R7-2')
BUS_N = 22.75
run(B, [VA, (R6[0], BUS_N), (R2[0], BUS_N)], 0.5, 'bus y 22.75 under X2-2/X2-3 to R6/R2')
run(B, [(R6[0], BUS_N), R6], 0.3, 'drop into R6-2')
run(B, [(R2[0], BUS_N), R2], 0.3, 'drop into R2-2')

R94, R99, R91, R92, R93, R90 = [pad(r, '2') for r in ('R94', 'R99', 'R91', 'R92', 'R93', 'R90')]
N1 = (R94[0], 20.45)                       # node above R94-2 (between the R94/R99 row and JP3-1)
N2 = (R99[0], 20.45)
run(B, [VA, (59.35, 21.55), N1], 0.4, 'via A -> node above R94-2')
run(B, [N1, N2], 0.5, 'bus y 20.45 over R99-1 to x 61.4')
run(B, [N2, R99], 0.3, 'drop into R99-2')
ROW = 17.55                                # row bus 0.24 above the y 17.01 pin-1 pads
run(B, [N1, R94, (R94[0], ROW), R91], 0.3, 'R94-2, on down x 59.35 to the row bus and R91-2')
run(B, [(R94[0], ROW), (R99[0], ROW), R92], 0.3, 'row bus east, drop into R92-2')
run(B, [(R99[0], ROW), (R93[0], ROW), R93], 0.3, 'row bus east, drop into R93-2')
run(B, [R93, (63.75, 16.7), (63.75, 14.47), R90], 0.3, 'R93-2 down to R90-2, offset east to keep the x 63.0-63.3 via column')
J6, J12 = pad('J1', '6'), pad('J1', '12')
run(B, [(R93[0], ROW), J6], 0.6, 'row bus end -> J1-6')
run(B, [J6, J12], 0.8, 'J1-6 -> J1-12')
# via D for C98/C97: the row bus west end drops into the C98-2 / R4 gap
VD = (57.675, pad('C98', '1')[1])
run(B, [(R94[0], ROW), (VD[0], ROW), VD], 0.3, 'row bus west to via D')
via(*VD)

# ------------------------------------------------------------------------------------------------
# 3. SOUTH-EAST from the column's free end (52.6, 7.65): a Bottom bus at y 5.5 between the VCC1V0 via
#    (53.6, 4.8) and the C1xx GND pads, drops into R20-2 / R23-1, down the west side of R1 to R1-4 /
#    R1-3, then along y 2.5 between X2-21 and JP4-1/JP4-2 to JP4-3.
# ------------------------------------------------------------------------------------------------
COL_END = (52.6, 7.65)
BUS_S = 5.5
R20, R23, R1_4, R1_3, JP4 = pad('R20', '2'), pad('R23', '1'), pad('R1', '4'), pad('R1', '3'), pad('JP4', '3')
VB = (58.0, BUS_S)
run(B, [COL_END, (52.6, BUS_S)], 0.8, 'column end down to the south bus')
run(B, [(52.6, BUS_S), (R20[0], BUS_S), (R23[0], BUS_S), (56.9, BUS_S), VB], 0.6, 'south bus y 5.5 to via B')
run(B, [(R20[0], BUS_S), R20], 0.3, 'drop into R20-2')
run(B, [(R23[0], BUS_S), R23], 0.3, 'drop into R23-1')
run(B, [(56.9, BUS_S), (56.9, R1_4[1]), R1_4, R1_3], 0.3, 'west of R1 down to R1-4, R1-3')   # MERGE: 0.3 (was 0.45), stitching sites
# MERGE 2026-09-21: y 2.68 and 0.3 wide, not y 2.5 / 0.5: the run carries no DC (JP4-3 is a header pin) and at
# y 2.5 / 0.5 it was the single most expensive object of the stage for GND stitching (541 sites that nothing else
# killed, x 59-67 y 2.1-2.9); at y 2.68 its dead band lies inside the JP4-1/JP4-2 pads' own dead zone (y >= 2.695)
# except for 0.43 mm, and it keeps 0.13 to those pads.
run(B, [R1_3, (59.2, 2.68), (JP4[0], 2.68), JP4], 0.3, 'y 2.68 between X2-21 and JP4-1/2 to JP4-3')
via(*VB)

# ------------------------------------------------------------------------------------------------
# 4. TOP: C145-1 from via B up x 58.0 (east of C142-2, west of the VCC1V8 via 58.3,10.0) and west along
#    the pad row; C98-1 from via D through the 0.65 mm gap, then C98-1 -> C97-1 on the pad row.
# ------------------------------------------------------------------------------------------------
C145, C98, C97 = pad('C145', '1'), pad('C98', '1'), pad('C97', '1')
run(T, [VB, (VB[0], C145[1]), C145], 0.25, 'via B up x 58.0, west into C145-1')   # MERGE: 0.25 (was 0.4), stitching sites; C145 carries no DC
run(T, [VD, C98], 0.41, 'via D into C98-1')
run(T, [C98, C97], 1.0, 'C98-1 -> C97-1')

# ------------------------------------------------------------------------------------------------
# 5. C146-1 from the column node (52.6, 11.05): Bottom north-west to via C (51.95, 12.45), level with
#    the pad centre; Top straight east into the pad.
# ------------------------------------------------------------------------------------------------
C146 = pad('C146', '1')
VC = (51.95, C146[1])
run(B, [(52.6, 11.05), VC], 0.3, 'column node -> via C')   # MERGE: 0.3 (was 0.5), stitching sites in the U1 surround; C146 carries no DC
via(*VC)
run(T, [VC, C146], 0.3, 'via C east into C146-1')   # MERGE: 0.3 (was 0.5), stitching sites in the U1 surround

if __name__ == '__main__':
    P.dump(OUT)
    P.print_report(only_tight='--all' not in ARGS)
    print('%d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
