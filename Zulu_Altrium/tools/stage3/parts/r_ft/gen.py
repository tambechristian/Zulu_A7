import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3'); from lib import Plan, INP0
S3 = PARTS
TRUNK = S3 + '/s3_trunk/plan.json'
# MERGE 2026-09-21: the bases are every part that precedes "ft" in the final order (trunk, west, sdled, north,
# south), so this region measures against the sdled via (18.5,10.5) and the north region's Top run under U2's
# north pins -- the two seams route_emit found on the first whole-board merge (see the notes at the segments).
BASES = [S3 + '/r_west/plan.json', S3 + '/r_sdled/plan.json', S3 + '/r_north/plan.json', S3 + '/r_south/plan.json']
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK, *BASES]])
# Region "ft": FT-VCORE, FT-VPHY, FT-VPLL.  Top under U2's body (LQFP, no e-pad) carries the VCORE
# ring; the cap row is reached through the Bottom channel vias south of the 0603 row (x 17.57 /
# 20.12 / 25.2 / 35.2, y 1.6-2.1; each at the west edge of its X2 gap so a GND via site stays beside it) and two 0.15 mm Bottom squeezes through U3's 0.35 mm pad gaps
# (x 30.35 between U3-12 GND / U3-11, x 35.15 between U3-6 GND / U3-5).  Inner copper: FT-VCORE on
# L4 (cap row, y 3.7), FT-VPLL on L3 (cap row y 3.35 and the x 17.9 slot up to U2), FT-VPHY on L4
# (the x 17.9 slot up to U2).  No L3/L4 copper east of x 34.6 or north of y 12.
OUT = PARTS + '/r_ft/plan.json'
VC, VPHY, VPLL = 'FT-VCORE', 'FT-VPHY', 'FT-VPLL'

# ---------------- FT-VCORE: Top ring pin 12 -> 37 / 49 / 64 ----------------
P.run(VC, 'Top', [(25.775, 11.85), (26.65, 11.85), (27.0, 11.2), (28.6, 11.2)], 0.3, 'pin12 exit')
P.run(VC, 'Top', [(28.6, 11.2), (28.6, 18.2)], 0.3, 'spine x28.6')
P.run(VC, 'Top', [(28.6, 18.2), (27.725, 18.2), (27.725, 19.3)], 0.3, 'strip -> pin64')
# MERGE 2026-09-21: the old strip (28.6,18.2)->(35.225,18.2) lay on the north region's VCC3V3 run under
# pins 55..51 (y 18.28) and its V1 riser / pin-56 stub.  Pin 49's pocket is closed by that run (west), by
# USB5V0's Top diagonal (32.1,13.2)->(34.8,16.65)->(35.9,18.0)->(36.68,20.0) (south and east) and by the
# pins; the only way in is from BELOW, between USB5V0's diagonal and the north run's south edge (18.155):
# a 0.20 riser from the ring's y 10.0 lane up the 0.475 mm gap between the D9 (30.825) and D10 (31.65)
# fan-out via lands at x 31.2375, a NE piece under the north region's V1->pin-56 diagonal, and the y 17.92
# line east to pin 49 (0.12 to the round end of the north run / pin-50 stub at (34.725,18.28), which the
# north region narrowed to 0.28 for this; 0.124 to USB5V0 at the corner), then up into the pad.
P.run(VC, 'Top', [(28.6, 11.2), (28.6, 10.0), (30.375, 10.0)], 0.4, 'lane west')
P.run(VC, 'Top', [(30.375, 10.0), (31.2375, 10.0), (36.15, 10.0), (36.15, 11.85)], 0.4, 'lane east')
P.run(VC, 'Top', [(31.2375, 10.0), (31.2375, 17.4), (32.4, 17.92), (35.225, 17.92), (35.225, 19.3)], 0.2, 'riser D9/D10 -> pin49')
P.run(VC, 'Top', [(36.15, 11.85), (37.175, 11.85)], 0.28, 'pin37')
P.run(VC, 'Top', [(30.375, 10.0), (30.375, 9.05)], 0.3, 'V1 stub')
P.via(VC, 30.375, 9.05)                                   # V1: Top ring <-> Bottom column
P.run(VC, 'Bottom', [(30.375, 9.05), (30.35, 7.05)], 0.3, 'column')
P.run(VC, 'Bottom', [(30.35, 7.05), (30.35, 5.3)], 0.15, 'SQUEEZE U3-12/11', clr=0.10, floor=0.09)
P.run(VC, 'Bottom', [(30.35, 5.3), (30.35, 4.55)], 0.3, 'column')
P.run(VC, 'Bottom', [(29.949, 4.55), (30.35, 4.55), (31.149, 4.55), (32.349, 4.55), (32.55, 4.45)], 0.5, '100nF bus')
for x in (29.949, 31.149, 32.349):
    P.run(VC, 'Bottom', [(x, 4.55), (x, 3.95)], 0.3, 'C15x-2 stub')
P.via(VC, 32.55, 4.45)                                    # V2: bus <-> L4 cap-row run
P.run(VC, 'L4-SIG', [(32.55, 4.45), (32.55, 3.7), (25.45, 3.7), (25.2, 3.45), (25.2, 2.1)], 0.4, 'L4 cap row')
P.via(VC, 25.2, 2.1)                                      # V3: channel via for C139
P.run(VC, 'Bottom', [(25.2, 2.1), (24.75, 2.55), (24.65, 3.05)], 0.3, 'C139-2')

# ---------------- FT-VPHY: L4-1 -> VA -> L4 slot -> VB -> Top -> pin 4; VB -> VC -> Bottom -> C40 ----
P.run(VPHY, 'Bottom', [(17.85, 3.05), (17.57, 2.1)], 0.4, 'L4-1 -> VA')
P.via(VPHY, 17.57, 2.1)                                  # VA
# MERGE 2026-09-21: the slot's y 9.5-11.7 leg moved 0.10-0.15 east (18.9/19.0 -> 19.05/19.1) to keep 0.12 from the
# sdled region's BTN-1 via (18.5,10.5), whose land ends at x 18.675; the trunk's L4 vertical (edge 18.25) is the
# same net and the leg's east side had >= 0.5 mm of room (its max width was 1.12, bound by the trunk on the west).
P.run(VPHY, 'L4-SIG', [(17.57, 2.1), (17.9, 3.4), (17.9, 6.8), (18.3, 8.0), (19.05, 9.5), (19.1, 11.7), (24.65, 11.7)], 0.5, 'L4 slot')
P.via(VPHY, 24.65, 11.7)                                  # VB: west of pin 12
P.run(VPHY, 'Top', [(24.65, 11.7), (24.8, 12.1), (24.8, 15.85), (25.775, 15.85)], 0.15, 'x24.8 -> pin4')
P.run(VPHY, 'Top', [(24.65, 11.7), (24.8, 11.3), (24.8, 9.45)], 0.15, 'x24.8 south')
P.run(VPHY, 'Top', [(24.8, 9.45), (26.4, 8.1)], 0.3, '-> VC')
P.via(VPHY, 26.4, 8.1)                                    # VC: U2's SW corner
P.run(VPHY, 'Bottom', [(26.4, 8.1), (27.2, 8.6), (28.2, 9.55), (35.15, 9.55), (35.15, 7.05)], 0.3, 'pocket lane')
P.run(VPHY, 'Bottom', [(35.15, 7.05), (35.15, 5.3)], 0.15, 'SQUEEZE U3-6/5', clr=0.10, floor=0.09)
P.run(VPHY, 'Bottom', [(35.15, 5.3), (35.15, 4.55), (34.749, 4.25), (34.749, 3.95)], 0.3, 'C40-2')

# ---------------- FT-VPLL: L5-1 -> VD -> L3 slot -> VE -> Top -> pin 9; VD -> L3 east -> VF -> C41 ----
P.run(VPLL, 'Bottom', [(20.65, 3.05), (20.12, 2.1)], 0.4, 'L5-1 -> VD')
P.via(VPLL, 20.12, 2.1)                                  # VD
# MERGE 2026-09-21: the slot stays at x 17.9 up to y 11.1 (it used to drift east to 18.1/18.3, through the
# sdled region's BTN-1 via (18.5,10.5)); the L3 there is open (that leg's max width was 2.26).
# JUDGE 2026-09-21: VE and its Top vertical moved 0.10 east (x 27.35 -> 27.45).  The GND-stage slot for U2-10/11
# (the only via site those two GND pins keep, boxed by U2-11's pad end x 26.55, pin 12's exit, A5's L3 track and
# this vertical) had 0.025 mm of margin; the vertical's edge is now at 27.35.  The via keeps 0.100 to the FT-VCORE
# ring (a y gap, unchanged) and the USB pair's in-body corridor (x 27.0-27.75) is only used at y >= 13.6.
XE = 27.45
P.run(VPLL, 'L3-SIG', [(20.12, 2.1), (19.0, 3.3), (17.9, 4.4), (17.9, 7.4), (17.9, 11.1), (XE, 11.1), (XE, 11.625)], 0.5, 'L3 slot')
P.via(VPLL, XE, 11.625)                                   # VE: under U2, east of pin 12
P.run(VPLL, 'Top', [(XE, 11.625), (XE, 12.9), (26.9, 13.35), (25.775, 13.35)], 0.2, 'pin9')
P.run(VPLL, 'L3-SIG', [(20.12, 2.1), (21.0, 3.35), (34.6, 3.35), (35.2, 1.575)], 0.4, 'L3 cap row')
P.via(VPLL, 35.2, 1.575)                                  # VF: channel via for C41
P.run(VPLL, 'Bottom', [(35.2, 1.575), (35.5, 2.2), (35.5, 3.5)], 0.2, 'C41 approach')
P.run(VPLL, 'Bottom', [(35.5, 3.5), (35.949, 3.95)], 0.15, 'C41 corner')

P.dump(OUT)
if '--report' in sys.argv:
    P.print_report()
else:
    P.print_report(only_tight=True)
print('vias %d tracks %d' % (len(P.VIAS), len(P.TRACKS)))
