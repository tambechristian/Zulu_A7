import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3'); from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])
# -*- coding: utf-8 -*-
"""Stage 3, REGION "west" (the header corner): VCC3V3 from the trunk's west tap to
C13-2, C11-2, C12-2, R35-2, X2-17 (TH), R34-5/6/7/8.  5 mA.  Box x 0-14.5, y 15-25.4.

    python gen.py                     writes plan.json next to this file, prints every segment
    python gen.py --tight             prints only the segments under 0.12 mm clearance or below the rule minimum
    python gen.py --lane Y --lanew W  experiment: the lane's y and width (defaults 22.60 / 0.30, see below)
    python gen.py --out PATH          write the plan somewhere else (the q/ sweep uses it)

Topology (one chain, one new via, Bottom except the 1.5 mm Top hop to the header pin):
  tap (3.433,20.40) Bottom  -> C13-2 (the 1.1 x 1.0 bulk cap, 1.0 mm wide, 1.04 mm)
  source via (5.233,20.40)  -> C11-2 on a diagonal past C11-1's SE corner (the trunk's east source via, a via
                               centre, so a legal branch point; it keeps C11-1's tie sites north of the cap row)
  C11-2 -> north through its own pad to the lane y 22.60 between the cap row (pad tops 21.84) and VCC1V0's
           0.20 Bottom track (y 22.95..23.15, X2-19 -> east): nodes at x 8.2498 (stub down to C12-2), 8.89 (via,
           Top hop up to X2-17 at 8.89,24.13) and 10.5498 (stub down to R35-2).  The lane is 0.30 (the rule's
           preferred width; 5 mA) at y 22.60 rather than 0.50 at y 22.40 so that C11-1 / C12-1 / R35-1 keep a
           row of GND via sites directly north of their pads (route_stitch: 0.35 land + 0.09 on both sides needs
           a 0.53 mm band; pad top 21.84 to the lane's south edge 22.45 = 0.61); clearance to VCC1V0 0.20.
  R35-2 -> R34-8 round the WEST of R34-1 (SD-DAT0, 10.37-10.87 x 19.74-20.64 sits exactly between them):
           down x 9.95 to the R34 VCC3V3 row y 18.3901, then east through R34-8 -> R34-7 -> R34-6 -> R34-5;
           0.30 on the detour (clearances 0.232 R34-1 / 0.248 R35-1), 0.40 along the row.
Every track end is a pad centre (INP0 coordinates), a via centre or another segment's end (joins are end
to end).  Capacitors: C13 on the tap itself, C11 and C12 between the source and the header pin X2-17.
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]


def arg(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default


V = 'VCC3V3'
T, B = 'Top', 'Bottom'


# pad centres straight from the board file (route_emit anchors a track end on the exact centre)
def pad(ref, num):
    for k in ('bottom_pads', 'top_pads', 'th_pads'):
        for p in INP0[k]:
            if p['ref'] == ref and p['pad'] == num and p['net'] == V:
                return (p['x'], p['y'])
    raise SystemExit('pad %s-%s not found on %s' % (ref, num, V))


C13 = pad('C13', '2'); C11 = pad('C11', '2'); C12 = pad('C12', '2'); R35 = pad('R35', '2'); X217 = pad('X2', '17')
R34 = {n: pad('R34', n) for n in ('5', '6', '7', '8')}

TAP = (3.433, 20.40)          # taps.json "west": Bottom, w 1.0, via centre (riser B and the Bottom bar end here)
SRC_E = (5.233, 20.40)        # the trunk's east source via (aux of the west tap): riser A ends here
LANE_Y = arg('--lane', 22.60) # the free Bottom lane north of the cap row, south of VCC1V0's y 23.05 track
LANE_W = arg('--lanew', 0.30)
VIA_X = X217[0]               # 8.89: via straight under the header pin
DET_X = 9.95                  # the detour west of R34-1 (west edge 10.37) and R35-1 (east edge 9.60)
DET_W = 0.30
ROW_Y = R34['8'][1]           # 18.3901


def run(layer, pts, wish, tag, clr=0.12):
    P.run(V, layer, pts, wish, tag, clr, 0.09)


# 1. the tap -> C13-2 (bulk cap on the source bar; the first segment starts exactly at the tap)
run(B, [TAP, C13], 1.0, 'tap -> C13-2')

# 2. east source via -> C11-2 (diagonal, past C11-1's south-east corner)
run(B, [SRC_E, C11], 0.5, 'source via (5.233,20.4) -> C11-2')

# 3. C11-2 north to the lane, east along it with a node at every stub and at the via
run(B, [C11, (C11[0], LANE_Y)], LANE_W, 'C11-2 north to the lane')
run(B, [(C11[0], LANE_Y), (C12[0], LANE_Y)], LANE_W, 'lane C11 -> C12 node')
run(B, [(C12[0], LANE_Y), C12], LANE_W, 'stub down to C12-2')
run(B, [(C12[0], LANE_Y), (VIA_X, LANE_Y)], LANE_W, 'lane C12 node -> via')
P.via(V, VIA_X, LANE_Y)
run(B, [(VIA_X, LANE_Y), (R35[0], LANE_Y)], LANE_W, 'lane via -> R35 node')
run(B, [(R35[0], LANE_Y), R35], LANE_W, 'stub down to R35-2')

# 4. the header pin: Top from the via straight up into X2-17 (TH, all layers)
run(T, [(VIA_X, LANE_Y), X217], 0.8, 'Top hop via -> X2-17')

# 5. R35-2 -> the R34 array round the west of R34-1, then along the VCC3V3 row
run(B, [R35, (DET_X, 20.75), (DET_X, ROW_Y), R34['8']], DET_W, 'R35-2 -> R34-8 (west of R34-1)')
run(B, [R34['8'], R34['7'], R34['6'], R34['5']], 0.4, 'R34 row 8 -> 7 -> 6 -> 5')

P.dump(arg('--out', os.path.join(HERE, 'plan.json')))
P.print_report(only_tight='--tight' in ARGS)
import math
L = {}
for t in P.TRACKS:
    L[t['layer']] = L.get(t['layer'], 0) + math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
print('copper by layer (mm):', {k: round(v, 2) for k, v in L.items()}, '| vias:', len(P.VIAS), '| tracks:', len(P.TRACKS))
