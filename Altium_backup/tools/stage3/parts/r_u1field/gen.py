import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
# -*- coding: utf-8 -*-
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3'); from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])
"""u1field region of stage 3 (re-run 2026-09-21 against the judged trunk, plan md5 a8bb54e8...): the 16 VCCO islands
of U1 and the twelve 0201s on the y 7.65 / 11.05 / 14.45 rows, from the trunk's tap (52.60,17.5) on Bottom (head of
the 0.70 mm column x 52.60, nodes y 14.45 / 11.05 / free end 7.65) and its NW via (40.85,15.6).

Topology (all Bottom unless said; every branch starts at a track end, a via or a pad):
  EAST   tap -> B19/C18 via (51.4,15.9) at 0.35 round the north end of the x 51.4 via wall (the via is boxed N and S
         by GND vias at 0.5 pitch and E by the VCC1V8 via 51.95,15.75; U1-A19/C19 already carry Top GND tracks to
         the wall's vias, so their via sites are not needed); column nodes -> C121-1 / C114-1, C119-1 / C111-1, C122-1
  SOUTH  column end (52.6,7.65) -> C115-1 (in SERIES with the field) and a parallel 0.6 entry beside it -> (50.6,8.2) ->
         the y 8.2 lane (between the 0201 GND pads and the row-8.9 vias, inside the land field so it costs no via
         sites) west to C113-1; C110-1 / C109-1 are stubs off the lane, C107-1 is in SERIES between the lane and V11;
         V9 and V6 hang on V11 at 0.35 so the 3-mil GND corridor y 7.165-7.41 under C113-2/C109-2 stays open (their
         only way out on the board is each other) and C107-2 keeps its way to the GND via (47.4,6.25)
  POCKET (50.6,8.2) -> (50.3,9.4) -> R17 -> the y 9.4 lane west to J7 (44.9,9.9); M17 and U13 off it
  WEST   the lane on to a vertical at x 43.9 (between the x 43.4 via wall and the J7 vias) -> J7's (44.4,11.9) and
         (44.4,12.4) vias and H3 (43.4,13.4) -> south of the AIN15_P wall -> K1 (40.9,11.9); C108-1 off that path
  CELL   J7 (44.4,12.4) -> the empty cell x 44.9-47.9, y 12.9 -> G12 (47.9,13.9) -> C14; -> K12 (48.4,11.9)
  TOP    K12 via -> the depopulated column x 48.9 -> F17 via (49.4,13.9)  (F17 is sealed on Bottom by the GND via
         48.9,13.9, JA3 49.4,13.4, C95's ties and VCC1V0's flank)
  NW     the trunk via (40.85,15.6) -> between the GND vias (41.4,14.4)/(41.4,15.4) -> C112-1 at 0.25 (a LEAF: the
         AIN15_P Bottom track y 13.7-13.9 from x 40.43 to the via 43.4,13.9 walls the C112 pocket from H3 on Bottom,
         and corr.py finds NO Top path from the NW via to K1's via (the GND ties of B1..G1 and the D/AIN fan-outs))
  SW     V1 and R1 are sealed inside the box on all four layers (AIN bundle on Bottom, the A0..A11 Top escapes,
         A1/A12 on L3, A4/A6/A8/A10 on L4): V1 leaves its via SW between BS0's via and AIN15_N to a new via
         (39.75,6.45), R1 leaves on Top west along y 9.42 (between A2 and A5) and down x 38.0-38.5 (west of A2's via)
         to the same via; the via ties to U3-1 (the south region's pad, 0.25 mm outside the box) on Bottom -- the
         connection Altium's own list pairs with V1's via.  With the trunk alone V1/R1 are therefore two islands of
         their own; they join the source through the south region's U3-1 feed (proved with r_south/plan.json).
"""
import math

inp = INP0
VIAS = [(v['x'], v['y']) for v in inp['vias'] if v['net'] == 'VCC3V3']
PADS = {}
for k in ('top_pads', 'bottom_pads', 'th_pads'):
    for p in inp[k]:
        PADS[p['ref'] + '-' + p['pad']] = (p['x'], p['y'])


def V(x, y):
    """exact centre of the existing VCC3V3 via nearest (x, y)"""
    d, b = min((math.hypot(vx - x, vy - y), (vx, vy)) for vx, vy in VIAS)
    assert d < 0.02, (x, y, b)
    return b


def PAD(name):
    return PADS[name]


N = 'VCC3V3'
B, T = 'Bottom', 'Top'

# trunk nodes (from s3_trunk/plan.json: the 0.70 column on x 52.60 and its nodes; the NW via)
TAP = (52.6, 17.5)
COL_1445, COL_1105, COL_765 = (52.6, 14.45), (52.6, 11.05), (52.6, 7.65)
NWVIA = (40.85, 15.6)

# ---------------- EAST: the tap and the column ----------------
# the first segment begins exactly at the tap; the east links stay narrow (every 0.1 mm of width here is ~10 GND via sites)
P.run(N, B, [TAP, (52.3, 17.15), (51.25, 17.1), (50.7, 16.4), (51.05, 15.9), V(51.4, 15.9)], 0.35, 'tap -> B19/C18 via')
P.run(N, B, [COL_1445, PAD('C121-1')], 0.3, 'column -> C121-1')
P.run(N, B, [COL_1445, (52.1, 14.91), (51.3, 14.91), PAD('C114-1')], 0.3, 'column -> C114-1')
P.run(N, B, [COL_1105, PAD('C119-1')], 0.3, 'column -> C119-1')
P.run(N, B, [COL_1105, (52.1, 10.55), (51.3, 10.55), PAD('C111-1')], 0.3, 'column -> C111-1')
P.run(N, B, [COL_765, PAD('C122-1')], 0.3, 'column end -> C122-1')

# ---------------- SOUTH: C115 in series, the parallel entry, the y 8.2 lane ----------------
P.run(N, B, [COL_765, (52.2, 7.05), (51.4, 7.05), PAD('C115-1')], 0.5, 'column end -> C115-1')
P.run(N, B, [PAD('C115-1'), (50.6, 8.2)], 0.5, 'C115-1 -> lane east end')
# a parallel entry beside C115 (the C115-1 approach necks to ~0.365 at C115-2's corner)
P.run(N, B, [(51.4, 7.05), (50.6, 7.55), (50.6, 8.2)], 0.6, 'parallel entry beside C115')
# V11 -> V9 -> V6 at <= 0.35 so the top edge stays at the via lands' 7.075: the 3-mil GND corridor y 7.165-7.41 under
# C113-2 / C109-2 stays open (their only way out on the board is each other); nothing of ours between C107-2 and the GND
# via (47.4,6.25) (its way out); V11 is fed through C107-1 only
P.run(N, B, [V(46.65, 6.9), V(45.65, 6.9), V(44.15, 6.9)], 0.35, 'V11 -> V9 -> V6 vias')
# the y 8.2 lane
P.run(N, B, [(50.6, 8.2), (48.81, 8.2), (47.9, 8.2), (46.59, 8.2), (44.37, 8.2), (43.2, 8.2)], 0.7, 'y 8.2 lane')
P.run(N, B, [(48.81, 8.2), PAD('C110-1')], 0.6, 'lane -> C110-1')
P.run(N, B, [(47.9, 8.2), V(47.9, 8.9)], 0.47, 'lane -> U13 via')
P.run(N, B, [(46.59, 8.2), PAD('C107-1'), V(46.65, 6.9)], 0.5, 'lane -> C107-1 -> V11 via')
P.run(N, B, [(44.37, 8.2), PAD('C109-1')], 0.3, 'lane -> C109-1 (leaf: a stub on to V6 would cut C113-2 from C109-2)')
P.run(N, B, [(43.2, 8.2), (42.4, 8.4), PAD('C113-1')], 0.5, 'lane -> C113-1')

# ---------------- POCKET and the y 9.4 lane ----------------
P.run(N, B, [(50.6, 8.2), (50.3, 9.4), V(49.4, 9.4)], 0.6, 'pocket -> R17 via')
P.run(N, B, [V(49.4, 9.4), (48.9, 9.4), (47.9, 9.4), (44.9, 9.4)], 0.47, 'y 9.4 lane')
P.run(N, B, [(48.9, 9.4), (48.9, 9.9), V(48.9, 10.4)], 0.47, 'lane -> M17 via')
P.run(N, B, [(47.9, 9.4), V(47.9, 8.9)], 0.47, 'lane -> U13 via (2)')
P.run(N, B, [(44.9, 9.4), V(44.9, 9.9)], 0.47, 'lane -> J7 group')

# ---------------- CELL ----------------
P.run(N, B, [V(44.4, 12.4), (44.9, 12.4), (44.9, 12.9), (47.9, 12.9), V(47.9, 13.9)], 0.47, 'cell bus J7 -> G12')
P.run(N, B, [(47.9, 12.9), (47.9, 11.9), V(48.4, 11.9)], 0.47, 'cell -> K12 via')
P.run(N, B, [V(47.9, 13.9), V(47.9, 14.9)], 0.42, 'G12 -> C14 via')
# F17 on Top through the depopulated column x 48.9 (sealed on Bottom: GND 48.9,13.9 / JA3 49.4,13.4 / C95 ties / VCC1V0 flank)
P.run(N, T, [V(48.4, 11.9), (48.9, 12.4), (48.9, 12.9), (48.9, 13.4), V(49.4, 13.9)], 0.47, 'Top: K12 via -> F17 via')

# ---------------- WEST ----------------
# a Bottom vertical at x 43.9 (between the x 43.4 via wall and the J7 vias) carries the cell/west current from the y 9.4
# lane to (44.4,11.9)/(44.4,12.4) and H3 directly, instead of through the J7 island's 0.2 mm Top fan-out tracks
P.run(N, B, [(44.9, 9.4), (43.9, 9.4), (43.9, 11.9), (43.9, 12.4), (43.9, 13.4), V(43.4, 13.4)], 0.47, 'x 43.9 vertical -> H3 via')
P.run(N, B, [(43.9, 11.9), V(44.4, 11.9)], 0.47, '-> J7 via (44.4,11.9)')
P.run(N, B, [(43.9, 12.4), V(44.4, 12.4)], 0.47, '-> J7 via (44.4,12.4)')
P.run(N, B, [V(43.4, 13.4), (43.0, 13.3), (41.9, 12.2), (41.6, 11.9), V(40.9, 11.9)], 0.47, 'H3 -> K1 via')
P.run(N, B, [(41.6, 11.9), PAD('C108-1')], 0.4, '-> C108-1')
# NW entry via -> C112-1 (leaf pocket, see the docstring)
P.run(N, B, [NWVIA, (40.85, 14.9), (41.4, 14.9), (41.9, 14.7), PAD('C112-1')], 0.25, 'NW via -> C112-1')

# ---------------- SW: V1 and R1 through a new via to U3-1 ----------------
SWV = (39.75, 6.45)   # corr.py via-site margin 0.125 here (D4 on L4 at y 6.9 is the binding object: 0.2125 to its edge)
P.via(N, *SWV)
P.run(N, B, [V(40.9, 7.9), (40.55, 7.15), (40.3, 6.9), SWV], 0.5, 'V1 via -> SW via')
P.run(N, B, [SWV, PAD('U3-1')], 0.6, 'SW via -> U3-1 pad centre')   # route_emit joins pads at their centre only
P.run(N, T, [V(40.4, 9.4), (39.8, 9.45), (38.3, 9.42), (37.95, 8.7), (38.5, 8.1), (38.5, 6.7), SWV], 0.4, 'Top: R1 via -> SW via')

if __name__ == '__main__':
    P.print_report()
    tight = [r for r in P.REPORT if r['clr'] < 0.12 - 1e-6 or r['short']]
    print('%d tracks, %d vias; %d segment(s) under 0.12 clearance or below the rule minimum' % (len(P.TRACKS), len(P.VIAS), len(tight)))
    for r in tight:
        print('   TIGHT', r['tag'], r['seg'], 'w', r['w'], 'clr', r['clr'], r['who'])
    import os
    HERE = os.path.dirname(os.path.abspath(__file__))
    P.dump(os.path.join(HERE, 'plan.json'))
    L = {}
    for t in P.TRACKS:
        L[t['layer']] = L.get(t['layer'], 0) + math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
    print('copper by layer (mm):', {k: round(v, 2) for k, v in L.items()})
