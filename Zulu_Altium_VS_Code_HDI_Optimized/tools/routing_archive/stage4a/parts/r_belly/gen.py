import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 4a was planned in a scratch tree)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4'); from lib import Plan, INP0
# Stage 4a, region "belly": GND ties for U2's west/south/east GND pins and LD1-K/LD2-K.  GND only, Top only.
# Result: 10 of 11 tied; U2-5 cannot be tied without foreclosing U2-2 or cutting the USB pair's corridor (see below).
# Every tie starts at its pad centre (route_emit anchors ends at pad centres) and ends on a new via centre or
# on another tie's end.  Positions are legal via cells from corr.py (0.025 raster) on the board of a7aa623.
import os, io
HERE = os.path.dirname(os.path.abspath(__file__))
G, T = 'GND', 'Top'
pads = {p['ref'] + '-' + str(p['pad']): p for p in INP0['top_pads']}
def C(n):
    p = pads[n]; return (p['x'], p['y'])
# Merge (2026-09-21): U2-47's own via at (38.175,18.475) sat 0.190 / 0.400 mm from the north region's U3-54 /
# U3-52 vias (route_emit on the merged plan); the tie now ends on north's U3-54 via (38.35,18.40) instead, so the
# north plan is loaded as base copper for the clearance checks (it is never dumped from here).
north = json.load(io.open(os.path.join(HERE, '..', 'r_north', 'plan.json'), encoding='utf-8'))
P = Plan(base_plans=[north])

# U2-47 (east row, top): north up the lane between U2-48's east end (37.95) and VCC3V3's x 39.0 vertical to a
# via in the pocket at y 18.4-18.5 (the only cells within reach; D15's via at (38.35,16.725) blocks a straight exit).
# (merge) no own via: up the lane to y 18.2, then NE onto the north region's U3-54 via at (38.35, 18.40);
# every segment keeps >= 0.12 (0.120 to U2-48, 0.219 to VCC3V3's (38.4,19.6)-(39.0,19.0) Top track).
P.run(G, T, [C('U2-47'), (37.85, 16.85), (38.175, 17.125), (38.175, 18.2), (38.35, 18.40)], wish=0.28, tag='U2-47 -> north U3-54 via')

# U2-25 (south row): north between the SDRAM vias D5 (31.55,8.95) and D4 (33.325,8.95); D5's land sits on the
# pad's centreline so the tie leaves the pad's east half.  VU's 0.7 trunk at y 6.4 leaves no site south.
P.via(G, 32.475, 9.025)
P.run(G, T, [C('U2-25'), (31.80, 8.60), (32.00, 8.85), (32.475, 9.025)], wish=0.28, tag='U2-25')

# U2-11 and U2-10 (west row): one via in the 33-cell pocket under U2's body between FT-VCORE's ring and
# FT-VPLL's via (the only cells within 1.5 mm of either pin); both hooks end on the via centre.
P.via(G, 27.025, 12.125)
P.run(G, T, [C('U2-11'), (26.50, 12.3501), (27.025, 12.125)], wish=0.28, tag='U2-11')
P.run(G, T, [C('U2-10'), (26.50, 12.85), (27.025, 12.125)], wish=0.28, tag='U2-10')

# U2-15 (west row): east from the pin's inner end, then south to the SW pocket under U2-16/17.  The tie keeps
# x >= 26.84 so U2-14's (FT-RESETN) and U2-16's (TCK) only escape lane along the pin ends (x ~26.68) stays open.
P.via(G, 26.975, 9.0)
P.run(G, T, [C('U2-15'), (26.50, 10.3501), (26.975, 10.15), (26.975, 9.0)], wish=0.28, tag='U2-15')

# U2-13 (west row): a 3 mil jog past U2-14's inner end (FT-VCORE's ring cap at (27.0,11.2) caps the east side,
# 0.121 max), east above U2-14's escape, then a 0.28 vertical at x 27.6 -- 0.165 clear of U2-15's tie so U2-14
# keeps a lane between the two ties -- to a via in the (28.2-28.9, 9.0) pocket north of U2-18.  A tie down the
# pin-end lane (x 26.7) seals U2-14 (route_foreclosure: U2-14 foreclosed); this one forecloses nothing.
P.via(G, 28.4, 9.05)
P.run(G, T, [C('U2-13'), (26.50, 11.3501)], wish=0.28, tag='U2-13 in pad')
# (judge) the jog was 0.0762 at 0.112 clearance; a 4 mil track at 0.100 clearance is the standard fab feature (max 0.1207).
P.run(G, T, [(26.50, 11.3501), (26.70, 11.15), (26.70, 11.0), (27.6, 10.55)], wish=0.30, clr=0.10, tag='U2-13 jog')
P.run(G, T, [(27.6, 10.55), (27.6, 9.3), (28.4, 9.05)], wish=0.28, tag='U2-13 to via')

# U2-35 (east row): the inner end faces FT-VCORE's x 36.15 vertical (0.12 gap) and the east end faces the
# x 38.5 SDRAM via column (0.45 pitch: no via slot in the lane).  Down the 0.375 lane, through the one 3 mil
# pinch between U2-33's SE corner and VCC3V3's (38.3,9.42) cap, west under U2-33 to the open SE pocket.
P.via(G, 36.1, 8.7)
P.run(G, T, [C('U2-35'), (37.85, 10.85), (38.14, 10.6), (38.14, 9.95), (38.18, 9.78)], wish=0.28, tag='U2-35 lane')
P.run(G, T, [(38.18, 9.78), (38.056, 9.622), (37.93, 9.47)], wish=0.0762, tag='U2-35 pinch')
P.run(G, T, [(37.93, 9.47), (36.65, 9.47), (36.1, 8.7)], wish=0.28, tag='U2-35 to via')

# U2-1 (west row, top): north along NetLD3_K's x 24.8 wall to the first via row north of the L3/L4 bus
# (no cell at y 17.6-20.6).  The only pocket under the body, (28.0,16.65), is the USB pair's Top corridor.
P.via(G, 25.1, 20.8)
P.run(G, T, [C('U2-1'), (25.1, 17.3501), (25.1, 20.8)], wish=0.28, tag='U2-1')

# LD1-K / LD2-K: boxed by LD5_K's L-shaped track (x 23.35 / y 11.973), FT-VPHY (x 24.8) and LD5-K.  The one
# exit is the 0.35 gap between LD5_K's corner cap and LD1-K's SW corner; from there the tie hugs LD0's west
# column so LD0-1's (N$LD0B) westward exit stays open, to the 2-cell site south of LD0.  LD2-K bridges to LD1-K.
P.via(G, 23.25, 10.575)
P.run(G, T, [C('LD1-K'), (23.76, 12.20)], wish=0.28, tag='LD1-K in pad')
# (judge) was 0.0762 throughout with 0.16-0.22 legal: now up to 0.15 at >= 0.10 clearance (LD0-1's exit keeps >= 0.125).
P.run(G, T, [(23.76, 12.20), (23.57, 11.95), (23.57, 11.75), (23.15, 11.60), (23.15, 10.90), (23.25, 10.575)], wish=0.15, clr=0.10, tag='LD1-K')
P.run(G, T, [C('LD2-K'), C('LD1-K')], wish=0.5, tag='LD2-K bridge')

# U2-5: NOT tied.  West: FT-VPHY (0.125); east: CKE's via land (0.125); south: the USB pair's approach to
# U2-7/8's inner ends; the only via pocket under the body, (28.0,16.65), is the USB corridor itself; the chain
# to U2-1 over UDQM's via takes U2-2's (CLK-12M-FT) only exit lane (route_foreclosure: U2-2 foreclosed).

P.dump(os.path.join(HERE, 'plan.json'))
P.print_report()
