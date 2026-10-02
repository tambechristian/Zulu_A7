import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3'); from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])
# -----------------------------------------------------------------------------------------------------------
# northbank region, re-run 2026-09-21 against the judge's hybrid trunk (plan md5 a8bb54e8...).
# Tap = node (40.0,22.5) of the 1.495 Top trunk y 22.5 (edges 21.75-23.25); other trunk nodes in the box:
# (45.3,22.5), (49.9,22.5), (52.65,22.5), the Top corner (52.93,21.9), the via pair (52.93,19.45)/(52.93,19.0)
# and the u1field column head (52.60,17.5) (end of the trunk's 1.0 Bottom piece from the 19.0 via).
# Loads: Q1-1/Q1-4 (Top SMD, 10 mA), U4-8 (Top SMD, 25 mA); no DC through the caps.  route_inputs.json has
# Q1 and U4 as Top SMD parts (top_pads; only X2 is TH in this box), so Bottom under them is free copper.
# GND-stitch economics (q_cost.py, route_stitch's rules): via sites are already dead over the 0603 rows
# (y 20.34-23.17), under Q1's Top pads, over VCC1V0's Bottom y 19.8 track (y 19.44-20.17), beside U4's pin
# columns and in the lane y 16.8-17.44 south of the 0201 row (D14/D15 on L4).  The live reservoirs are U4's
# body on Bottom (y 18.27-19.44), the strip x 47.8-50.1 y 19.9-20.6 and the field south of C104-2/C105.
# Bottom cells (VCC1V0's 0.2 tracks x 43.56/44.3, y 19.8, x 47.4; VCC1V8's x 50.5 column + via (50.5,19.4)):
#   W: x < 43.5 -> C100-1, C106-1, C101-1, C120-1 (via V1 west of C100/C106; C101-1 along y 20.3 under Q1)
#   M: x 44.4-47.3, y 19.9-22.4, closed -> C102-1 (via V2 under the pad, Top-fed from node 45.3; V2 is also
#      the Top hub for the 0201 via V6)
#   E: C103-1 (via V5 under the pad, Top-fed from node 49.9); C116-1 by via V6 straight above it (Top-fed from
#      V2: the one unavoidable crossing of U4's reservoir) with the stub carried on into the dead lane y 17.1
#      and west to C117-1 (the D14 via 47.9,17.15 blocks that lane east of C116); C118-1 from the column head
#      (52.60,17.5) along the dead lane y 17.3 under U4-5 (0.175 above the D15 via land), no via, no crossing.
#   far east: C104-1/C99-1 straight up from the column via (52.93,19.45); C105-1 by via V3 in the dead 0.6 mm
#      gap between C105-1 and C105-2 (the only site there that is not in the live field south of the caps),
#      Top-fed from the trunk's corner node (52.93,21.9) along y 21.5 below the trunk band.
# -----------------------------------------------------------------------------------------------------------
N = 'VCC3V3'
TAP = (40.0, 22.5)
V1 = (39.4, 21.75)     # cell W: 0.225 west of the C106-1/C100-1 pad edges; Top side under the trunk (own copper)
V2 = (46.55, 20.25)    # cell M: 0.175 above VCC1V0's y 19.8 track, 0.175 below C102-1; Top side = U4 body
V3 = (56.7, 21.1)      # C105-1: in the 0.60 gap between C105-1 (x <= 56.399) and C105-2 (x >= 56.999), 0.125 each
V5 = (49.65, 20.3)     # C103-1: 0.125 below the pad; Top side U4 body (0.57 from U4-7)
V6 = (46.59, 19.4)     # C116-1: straight above the pad, 0.125 below VCC1V0's y 19.8 track; Top side U4 body
for v in (V1, V2, V3, V5, V6):
    P.via(N, *v)
# ---- Top ----------------------------------------------------------------------------------------------------
P.run(N, 'Top', [TAP, (40.45, 20.85)], wish=0.8, tag='T1 tap -> Q1-1')                      # first segment: at the tap
P.run(N, 'Top', [(40.45, 20.85), (42.15, 20.85)], wish=0.8, tag='T2 Q1-1 -> Q1-4')
P.run(N, 'Top', [TAP, V1], wish=0.6, tag='T3 tap -> V1')
P.run(N, 'Top', [(45.3, 22.5), V2], wish=0.5, tag='T4 node45.3 -> V2')
P.run(N, 'Top', [(49.9, 22.5), (51.15, 21.305)], wish=0.8, tag='T5 node49.9 -> U4-8')
P.run(N, 'Top', [(49.9, 22.5), V5], wish=0.3, tag='T6 node49.9 -> V5')
P.run(N, 'Top', [V2, V6], wish=0.2, tag='T7 V2 -> V6')   # MERGE 2026-09-21: 0.2 (was 0.3): U4's Bottom reservoir, stitching floor
P.run(N, 'Top', [(52.93, 21.9), (56.7, 21.5), V3], wish=0.4, tag='T9 corner52.93 -> V3')
# ---- Bottom cell W ------------------------------------------------------------------------------------------
P.run(N, 'Bottom', [V1, (40.35, 22.4)], wish=0.6, tag='B1 V1 -> C106-1')
P.run(N, 'Bottom', [V1, (40.35, 21.1)], wish=0.6, tag='B2 V1 -> C100-1')
P.run(N, 'Bottom', [(40.35, 21.1), (42.15, 17.85)], wish=0.2, tag='B3 C100-1 -> C120-1')   # MERGE 2026-09-21: 0.2 (was 0.3), stitching floor
P.run(N, 'Bottom', [(40.35, 21.1), (40.35, 20.3), (43.45, 20.3), (43.45, 21.1)], wish=0.3, tag='B4 C100-1 -> C101-1')
# ---- Bottom cell M ------------------------------------------------------------------------------------------
P.run(N, 'Bottom', [V2, (46.55, 21.1)], wish=0.4, tag='B5 V2 -> C102-1')
# ---- Bottom cell E: C103-1, and the 0201 row -----------------------------------------------------------------
P.run(N, 'Bottom', [V5, (49.65, 21.1)], wish=0.3, tag='B7 V5 -> C103-1')
P.run(N, 'Bottom', [V6, (46.59, 17.85)], wish=0.2, tag='B9 V6 -> C116-1')   # MERGE 2026-09-21: 0.2 (was 0.3): 73 exclusive sites in U4's reservoir
P.run(N, 'Bottom', [(46.59, 17.85), (46.59, 17.1)], wish=0.3, tag='B14 C116-1 -> lane')
P.run(N, 'Bottom', [(46.59, 17.1), (44.37, 17.1), (44.37, 17.85)], wish=0.3, tag='B10 lane -> C117-1')
# MERGE 2026-09-21: the lane sits at y 17.45 / 0.2 (was 17.3 / 0.3): the U1-surround floor (65 %) broke on the
# whole-board merge; at 17.3/0.3 the lane killed the y 16.9-17.0 rows x 48.8-50.1 by itself (49 sites) and
# overlapped the u1field tap piece (y 16.925-17.325, same net); at 17.45 it hugs the 0201 row's own dead zone
# (pads' bottom edge 17.70, 0.15 clear) and stays 0.025 clear of that piece.
P.run(N, 'Bottom', [(52.6, 17.5), (52.2, 17.45), (48.81, 17.45), (48.81, 17.85)], wish=0.2, tag='B8 colhead -> C118-1')
# ---- Bottom far east ----------------------------------------------------------------------------------------
P.run(N, 'Bottom', [(52.93, 19.45), (52.749, 21.1)], wish=1.0, tag='B11 via19.45 -> C104-1')
P.run(N, 'Bottom', [(52.749, 21.1), (52.749, 22.4)], wish=0.8, tag='B12 C104-1 -> C99-1')
P.run(N, 'Bottom', [V3, (55.849, 21.1)], wish=0.3, tag='B13 V3 -> C105-1')
OUT = PARTS + '/r_northbank/plan.json'
P.dump(OUT)
P.print_report()
print('vias', len(P.VIAS), 'tracks', len(P.TRACKS))
