import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 4a was planned in a scratch tree)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4'); from lib import Plan, INP0
# Stage 4a, region u1: GND ties for the 29 pads of regions.json["u1"].  GND only, additions only.
import os, io
HERE = os.path.dirname(os.path.abspath(__file__))
P = Plan()
B, T = 'Bottom', 'Top'

def V(x, y):
    P.via('GND', x, y); return (x, y)

def tie(layer, pts, wish, tag, clr=0.12):
    P.run('GND', layer, pts, wish=wish, tag=tag, clr=clr)

# ---- existing GND vias (fan-out / stitching) as tie targets
v_51_114 = (51.4, 11.4); v_51_139 = (51.4, 13.8999); v_434_144 = (43.4001, 14.4)

# ---- 0201 caps under / beside U1 (Bottom, 0.30 pads)
tie(B, [(51.6299, 11.05), v_51_114], 0.3, 'C111-2 -> via 51.4,11.4')
tie(B, [(51.6299, 14.45), v_51_139], 0.3, 'C114-2 -> via 51.4,13.9')
tie(B, [(42.7499, 14.45), v_434_144], 0.3, 'C112-2 -> via 43.4,14.4')
# (judge) the new via at (47.4,7.0) sat 0.137 from the CFG-M0 / CHAN26 escape stub ends and 0.099 from CFG-M0 on Top, in the
# CHAN14..28 L3/L4 exit column; the tie now continues 0.75 mm to the board's GND via (47.4001,6.25) (0.30 wide, 0.35 clear).
tie(B, [(47.1899, 7.65), (47.4, 7.0), (47.4001, 6.25)], 0.3, 'C107-2 -> existing via 47.4,6.25')
tie(B, [(51.6299, 7.65), V(51.9, 8.1)], 0.3, 'C115-2 -> new via')
tie(B, [(49.4099, 7.65), (49.4099, 7.45), (49.25, 7.3), (49.25, 6.8), V(49.05, 6.6)], 0.3, 'C110-2 -> new via')
# C109-2 and C113-2 sit in the pocket between the VCC3V3 wall (y 8.2) and the AIN16 diagonals; the only exit
# is west of the VCC3V3 via 44.15,6.9 then east under the y 6.9 rail to the triangle east of the D0 stub
# chain via 45.75,6.45 (foreclosure-clean, reach 140/140; 45.5,6.45 seals FPGA-TDO W8); --chaina keeps the
# earlier 46.35,6.44 site (also fully gated, 0.6 mm longer) and writes plan_a.json
CHAINC = '--chaina' not in sys.argv
vC109 = V(45.75, 6.45) if CHAINC else V(46.35, 6.44)
tie(B, [(44.9699, 7.65), (44.9699, 7.3), (43.8, 7.3), (43.8, 6.55), (45.65, 6.55) if CHAINC else (46.25, 6.55), vC109], 0.3, 'C109-2 -> new via (pocket exit)')
tie(B, [(42.7499, 7.65), (42.7499, 7.3), (43.8, 7.3)], 0.3, 'C113-2 -> C109-2 tie (same row)')
# C108-2: walled east by the x 43.4 via column and north by the VCC3V3 diagonal; west to the GND via 40.9,10.15
# (judge) the diagonal into the via ran 0.120 from AIN16_N's x 40.597 vertical at 0.29 wide; the last 0.32 mm is a 0.13 neck (0.200 clear).
tie(B, [(42.7499, 11.05), (42.45, 10.75), (42.275, 10.675), (41.425, 10.675), (41.125, 10.375)], 0.3, 'C108-2 -> via 40.9,10.15')
tie(B, [(41.125, 10.375), (40.9, 10.15)], 0.13, 'C108-2 neck into the via')
# north row y 17.85
vI = V(43.175, 18.125)
tie(B, [(42.7499, 17.85), vI], 0.3, 'C120-2 -> new via (shared U4-4)')
tie(T, [(43.85, 17.495), vI], 0.3, 'U4-4 -> new via (shared C120-2)')
tie(B, [(44.9699, 17.85), V(44.975, 18.3)], 0.3, 'C117-2 -> new via')
tie(B, [(47.1899, 17.85), V(47.2, 18.3)], 0.3, 'C116-2 -> new via')
tie(B, [(49.4099, 17.85), V(49.85, 17.85)], 0.3, 'C118-2 -> new via')

# ---- south of U1 (Bottom)
tie(B, [(50.25, 4.2499), V(50.25, 4.975)], 0.45, 'R21-1 -> new via')
vS = V(46.575, 3.225)
tie(B, [(46.7495, 3.9499), vS], 0.3, 'R17-2 -> new via (shared R11-1)')
# (judge) R11-1 was 0.085 at 0.12 clearance; 0.10 clearance gives 0.105 (max 0.1255, R11-2's corner).
tie(B, [(45.9499, 2.75), vS], 0.3, 'R11-1 -> new via (shared R17-2)', clr=0.10)
# (judge) L6-1's own via at (48.05,2.325) cut the CHAN14..28 L3/L4 exit column (x 47.85: 9 -> 7 lanes); a 1.5 mm Bottom tie
# west to vS (0.45 / 0.295 wide, 0.12 to the AIN16_N via) costs nothing on the inner layers.
tie(B, [(48.05, 3.05), (47.3, 3.05), vS], 0.45, 'L6-1 -> via vS (shared R11-1/R17-2)')
# R13-2 / R15-1: NOT TIED.  R13-2's only exit is the 0.30 slot between C36-2 and C37-1 (x 42.0-42.3), which is
# also the only exit of ANALOG-IO1 (R14-2 -> X2-40); R15-1's only exit is the 0.30 channel y 3.5-3.8 under the
# R13..R16 row, which is the only path of the NODE_P1 hop (R14-1 -> R15-2).  With either tie placed route_reach
# drops to 137/140 and route_foreclosure seals R14-1/R14-2/R15-2 (run of 2026-09-21).  Needs copper moved
# (the AIN16_N via 43.3,3.2 or C36/C37) before they can be tied.  Set TIE_R13_R15 = True to emit those ties.
TIE_R13_R15 = False
if TIE_R13_R15:
    vR = V(43.18, 1.6)
    tie(B, [(41.9498, 3.9499), (42.15, 3.65), (42.15, 2.3), (43.18, 2.3), vR], 0.3, 'R13-2 -> new via (X2-27/28 gap)')
    tie(B, [(43.7498, 3.9499), (43.7498, 3.65), (42.15, 3.65)], 0.3, 'R15-1 -> R13-2 tie (same row)')

# ---- Q1 (Top)
tie(T, [(40.45, 18.65), V(41.5, 19.85)], 0.4, 'Q1-2 -> new via')

# ---- bulk caps north of U1 (Bottom, 1.1 x 1.0 pads)
tie(B, [(45.1497, 21.1), V(45.15, 20.25)], 0.45, 'C101-2 -> new via')
tie(B, [(48.2495, 21.1), V(48.25, 20.3)], 0.45, 'C102-2 -> new via')
tie(B, [(51.3494, 21.1), V(51.35, 19.475)], 0.45, 'C103-2 -> new via (U4-6/7 gap)')
tie(B, [(42.0498, 22.4), (42.55, 22.85), (43.0, 23.35), V(43.18, 23.6)], 0.3, 'C106-2 -> new via (X2-7/8 gap)')
tie(B, [(42.0498, 21.1), (42.0498, 22.4)], 0.5, 'C100-2 -> C106-2 (boxed by VCC3V3 y 20.3)')
tie(B, [(45.1497, 22.4), (45.45, 22.75), (45.72, 23.3), V(45.72, 23.6)], 0.4, 'C87-2 -> new via (X2-6/7 gap)')
tie(B, [(48.2495, 22.4), V(48.26, 23.6)], 0.45, 'C88-2 -> new via (X2-5/6 gap)')
tie(B, [(51.3494, 22.4), (51.05, 22.75), (50.8, 23.3), V(50.8, 23.6)], 0.4, 'C94-2 -> new via (X2-4/5 gap)')

P.dump(os.path.join(HERE, 'plan.json' if CHAINC else 'plan_a.json'))
io.open(os.path.join(HERE, 'report.json' if CHAINC else 'report_a.json'), 'w', encoding='utf-8').write(json.dumps(P.REPORT, indent=0))
if '--quiet' not in sys.argv:
    P.print_report(only_tight='--tight' in sys.argv)
    print('%d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
