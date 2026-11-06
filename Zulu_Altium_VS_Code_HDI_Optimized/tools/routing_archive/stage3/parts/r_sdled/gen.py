import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3'); from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])
# -*- coding: utf-8 -*-
"""Stage 3, REGION "sdled": X3-4 (200 mA), BTN-1/2, LD5-A, the pull-ups R19/R96/R97/R98 and U10-8.

    python gen.py            writes plan.json next to this file, prints every segment's report

Tap (taps.json): Top (17.5, 12.45) = the west via of the sdled pair; the trunk's 0.30 Top stub ends there.
Aux trunk copper in the box: the second via (17.95, 12.45) and the pull-up via (16.5, 19.9).

Pads and their layers (route_inputs.json, which beats the region note): X3-4 Top 1.75x0.70 at (14.15, 12.375);
BTN-1 (19.225, 10.845) and BTN-2 (19.225, 14.995) are TOP SMD pads 0.65x1.05 (not TH); LD5-A (22.55, 14.985)
Top 0.90x0.90; R97-2 (18.15, 19.35), R98-2 (19.35, 19.35), R19-2 (19.35, 18.75), R96-2 (20.55, 18.75) 0201
Bottom; U10-8 (27.215, 18.695) Bottom 2.07x0.51.

Geometry that decides the shape (objs.py / corr.py, all from the files):
  * LD5_K runs on Top at y 11.825 (0.10 wide) from x 11.455 to 21.8, then (22.3..23.35, 11.973) and up x 23.35 to
    LD5-K: it separates BTN-1 (pad y 10.32-11.37) from the tap row (y 12.45) on Top.  So BTN-1 is fed on
    BOTTOM from the second via (17.95, 12.45) to a new via at (18.5, 10.5) (corr.py margin >= 0.45 there; Bottom
    holds only USB5V0 0.66 mm away; L3's A3 track starts 2.3 mm east) and a 0.30 Top stub into the pad.
  * BTN-2 is on the tap's side of LD5_K: a direct Top diagonal from the second via (corr.py: 1.0 wide).
  * LD5-A is walled by LD2-A (y <= 14.235) south, BTN-4 (x 21.05-21.7, y 14.47-15.52) west, LD5_K's x 23.35
    vertical east and LD3-A / the NetLD3_A track (y 15.8) north: the only door is the 0.464 mm diagonal gap between
    BTN-4's corner (21.7, 14.47) and LD2-A's corner (22.1, 14.235), midpoint (21.9, 14.35): the branch runs east on
    Top at y 12.45 (between LD5_K and BTN-2's feed), turns NE at x 20.5 and threads that gap at 0.20 wide
    (clearance 0.12-0.13 each side, forced by the two pads).
  * VCC1V0's 1.50 mm Bottom track at y 14.465 (x 15.85-36.6) walls Bottom north of the tap: the pull-ups are fed
    from the trunk's pull-up via (16.5, 19.9) along a Bottom lane at y 20.1 (0.4 from the 0201 row's top edge, so
    a signal can still pass over R98-1), verticals into R97-2 and R98-2 -> R19-2, east to R96-2, then the
    U10-1/U10-2 gap (y 18.95-19.71) and U10's interior to U10-8 (which is reachable only from its west end:
    U10-7 sits above it, R80-1 0.21 mm east of it).
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
V = 'VCC3V3'
T, B = 'Top', 'Bottom'


def run(layer, pts, wish, tag, clr=0.12, floor=0.09):
    P.run(V, layer, pts, wish, tag, clr, floor)


TAP = (17.50, 12.45)          # Top track END of the trunk (the west sdled via)
TAP2 = (17.95, 12.45)         # the second sdled via (aux)
PULL = (16.50, 19.90)         # the pull-up via (aux)

# 1. X3-4 (200 mA): west on Top at y 12.45 between LD5_K (edge 11.875) and X3-3 (bottom 13.125), into the pad centre.
run(T, [TAP, (14.90, 12.45)], 0.85, 'X3-4 feed y 12.45')
run(T, [(14.90, 12.45), (14.15, 12.375)], 0.70, 'X3-4 into the pad centre')

# 2. BTN-2: Top diagonal from the second via.
run(T, [TAP2, (19.225, 14.995)], 0.40, 'BTN-2 Top diagonal')

# 3. LD5-A: Top east at y 12.45, then through the BTN-4 / LD2-A door at (21.9, 14.35).
run(T, [TAP2, (20.50, 12.45)], 0.40, 'LD5 branch y 12.45')
run(T, [(20.50, 12.45), (21.90, 14.35)], 0.20, 'LD5 branch NE to the door')
run(T, [(21.90, 14.35), (22.55, 14.985)], 0.20, 'LD5-A through the door')

# 4. BTN-1: Bottom from the second via to a via west of the pad, Top stub into the pad.
BV = (18.50, 10.50)
P.via(V, *BV)
run(B, [TAP2, BV], 0.40, 'BTN-1 Bottom feed')
run(T, [BV, (19.225, 10.845)], 0.30, 'BTN-1 Top stub')

# 5. Pull-ups and U10-8 on Bottom from the pull-up via.
run(B, [PULL, (18.15, 20.10)], 0.40, 'pull-up lane from the via')
run(B, [(18.15, 20.10), (18.15, 19.35)], 0.40, 'R97-2')
run(B, [(18.15, 20.10), (19.35, 20.10)], 0.40, 'pull-up lane y 20.1')
run(B, [(19.35, 20.10), (19.35, 19.35)], 0.40, 'R98-2')
run(B, [(19.35, 19.35), (19.35, 18.75)], 0.40, 'R19-2')
run(B, [(19.35, 19.35), (20.55, 19.33)], 0.40, 'east to the R96 column')
run(B, [(20.55, 19.33), (20.55, 18.75)], 0.40, 'R96-2')
run(B, [(20.55, 19.33), (23.60, 19.33)], 0.50, 'U10-1/U10-2 gap')
run(B, [(23.60, 19.33), (23.90, 18.695)], 0.50, 'down into U10 interior')
run(B, [(23.90, 18.695), (27.215, 18.695)], 0.50, 'U10-8')

P.dump(os.path.join(HERE, 'plan.json'))
P.print_report()
print('vias %d tracks %d' % (len(P.VIAS), len(P.TRACKS)))
