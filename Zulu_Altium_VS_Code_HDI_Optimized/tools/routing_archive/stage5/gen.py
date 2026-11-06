# -*- coding: utf-8 -*-
"""Stage 5, THE FINAL PLAN (judge): L5 becomes the VCC3V3 plane.

    python tools/stage5/gen.py            writes tools/stage5_route.json
    python tools/stage5/gen.py --check    rebuilds it and compares byte for byte
    python tools/stage5/gen.py --out F    writes somewhere else

BASE: planner "balanced" (p_bal/gen.py, plan.json md5 1b1be752e103c382c6033ac21deb68dd), rebuilt here
so there is one authoritative file.  p_bal was chosen because it is the only one of the three plans
that passes `tools/route_emit.py` with ZERO problems against the rules as they stand today -- it needs
no Width_PWR_VCC3V3 relaxation -- while reaching 669 of the 671 achievable north-band lanes (the same
as the maximal plan) and 382 of 391 on the U1-east cut.

FOUR CHANGES from p_bal, each answering a reviewer finding I re-measured and confirmed:

  J1  KEEP board tracks 93 and 96.  p_bal removed the two Top segments that enter U2-31's and U2-20's
      pads and kept 94/97, which stop 0.075 mm inside the pad rectangle.  That is a pad OVERLAP, not
      an end-to-end join, and brief.md says "Copper joins end to end only".  Measured cost: 2 x 0.70 mm
      of 0.28 mm Top copper between two QFN pin rows.

  J2  KEEP the in-field via (44.4001, 9.8999).  brief.md: "the 14 VCC3V3 vias already there stay".
      p_bal removed one of them, p_max five.  Restored; see decisions.md, item 2.

  J3  REGULATOR: the second plane entry comes off C80-2, not off U5-4.  p_bal's entry B at
      (6.0250, 16.7500) is fed from U5-4 -- the SC189's VOUT/feedback pad -- through kept track 1106,
      so 253.5 mA of the 745 mA rail crossed the sense pad (measured with rev_p_bal_elec/fullir.py).
      Entry B is deleted and TWO new entries are placed beside the output capacitor at (2.6250,16.1250)
      and (2.6250,17.1500), fed from C80-2's own pad.  U5-4 stays tied through kept track 1106 and now
      carries only its own sense current.  Three barrels, all at the capacitor, none on the sense pin.

  J4  C111-1 gets its own barrel at (51.8500, 11.8500) instead of sharing (51.9500, 12.4495) with
      C119-1, C121-1 and C146-1.  Four 100 nF parts behind one 0.20 mm hole multiply their plane-side
      ESL by four.  The new stub is also 0.70 mm SHORTER than the one it replaces.
      The other heavily shared barrel, (27.9300, 4.8500) with nine pads, could NOT be split:
      `corr.via_sites` returns ZERO legal via cells within 2.2 mm of it.  Reported, not fixed.

WHAT THE PLAN DOES (unchanged from p_bal in kind)
  * removes the VCC3V3 trunk and the seven regional feeds stage 3 laid (tools/stage3/parts/s3_trunk,
    r_west, r_sdled, r_north, r_south, r_u1field, r_northbank, r_east) -- and NOTHING of any other net;
  * keeps only copper that pays for itself in four-layer free routing area (a via costs
    4 * pi * (0.175 + 0.09 + 0.0381)^2 = 1.1545 mm2; a track of length L and width w costs about
    L * (w + 0.2562) plus its end caps), plus the SC189 output loop, which is a circuit requirement;
  * narrows thirteen kept runs that were sized for trunk current and now carry one pad's tie current;
  * gives every orphaned pad a via to the L5 plane, sharing a via wherever two pads can reach one.

Built on tools/stage5/lib.py (Plan.run measures every width with route_emit's own distance code
against the board AS THIS PLAN LEAVES IT -- the plan's removals are applied first).
"""

import hashlib
import io
import json
import math
import os
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage5')
from lib import Plan, INP0                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NET = 'VCC3V3'
TOL = 0.0015

# ----------------------------------------------------------------------------------------------
# 1.  the existing VCC3V3 tracks this plan KEEPS, by index in tools/route_inputs.json
# ----------------------------------------------------------------------------------------------
# U1's 28 VCCO dog-bones: the 32 Top tracks that keep every ball on a via (route_emit's
# "power ball U1-xx no longer reaches a VCC3V3 via" test fails on all 28 without them).
KEEP_U1 = [369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 382, 383, 384, 385, 386,
           387, 388, 389, 391, 392, 394, 397, 399, 401, 402, 403, 404, 405, 406, 407]
# copper inside U1's land field, where no new via may be placed: C107-1, C109-1, C112-1, C113-1
KEEP_FIELD = [821, 822, 823, 824, 853, 855]
# U2's QFN rows and the south capacitor row: pads with no legal via site at all
# J1: 93 and 96 restored -- they are the segments that reach U2-31's and U2-20's pad centres.
KEEP_U2_SOUTH = [93, 94, 95, 96, 97, 98, 99, 100, 916]
KEEP_U2_NORTH = [105, 106, 108, 109, 939, 940, 941, 943, 944, 945]
# short local ties that are cheaper than the via they would otherwise need
KEEP_LOCAL = [65, 110, 798, 799, 808, 809]
# the SC189 output loop: block_place.loop_joins() requires L1-2, C80-2 and U5-4 on ONE island
# made by DIRECT copper.  1107 is the 1.0 mm inductor-to-cap run, 1106 the 0.4 mm run to U5-4.
KEEP_LOOP = [1106, 1107]
KEEP = sorted(KEEP_U1 + KEEP_FIELD + KEEP_U2_SOUTH + KEEP_U2_NORTH + KEEP_LOCAL + KEEP_LOOP)

# J2: existing VCC3V3 vias that stay whatever the kept copper does.  brief.md's land-field rule
# says the 14 vias already inside x 41.7875-51.0125, y 7.2875-16.5125 stay; p_bal dropped this one
# because no kept track still lands on it.  A VCC3V3 via on a VCC3V3 plane is a stitch, not an
# antenna, so keeping it is free of any DRC consequence.
PROTECT_VIAS = [(44.4001, 9.8999)]

# ----------------------------------------------------------------------------------------------
# 2.  kept runs that are REDRAWN thinner: stage 3 sized them for trunk current, they now carry one
#     tie's current (21 mA at a U3 pad, 3.4 mA at a U1 VCCO ball).  Removed and re-laid on the same
#     centreline at 0.20 mm, the Width_PWR_VCC3V3 Bottom minimum.
# ----------------------------------------------------------------------------------------------
REDRAW = [                                     # (index(es) in route_inputs.json, layer, polyline)
    ((107,), 'Top', [(31.7250, 18.2800), (31.7250, 19.3000)]),       # U2-56 stub, was 0.450
    ((854,), 'Bottom', [(42.4000, 8.4000), (43.2000, 8.2000)]),      # C113-1 run, was 0.500
    ((856,), 'Bottom', [(46.5900, 7.6500), (46.6501, 6.9000)]),      # C107-1 tie, was 0.500
    ((857,), 'Bottom', [(46.5900, 7.6500), (46.5900, 8.2000)]),      # was 0.500
    ((860,), 'Bottom', [(43.2000, 8.2000), (44.3700, 8.2000)]),      # was 0.700
    ((861,), 'Bottom', [(44.3700, 8.2000), (46.5900, 8.2000)]),      # was 0.560
    ((896,), 'Bottom', [(32.3500, 6.1701), (32.5000, 5.1000)]),      # U3-9 tie, was 0.450
    ((897,), 'Bottom', [(32.5000, 5.1000), (33.5492, 5.1000)]),      # was 0.600
    ((898,), 'Bottom', [(33.5492, 3.9499), (33.5492, 5.1000)]),      # C38-2 tie, was 0.600
    ((912,), 'Bottom', [(28.7495, 3.9499), (29.2502, 3.0500)]),      # C4-2 tie, was 0.400
    ((922, 923), 'Bottom', [(27.9300, 4.8500), (28.7495, 4.8500)]),  # south row spine, was 1.200
    ((938,), 'Bottom', [(29.9500, 17.5300), (30.3000, 16.4000)]),    # U3-43 tie, was 0.400
    ((974,), 'Bottom', [(5.2330, 20.4000), (5.9499, 21.3900)]),      # C11-2 tie, was 0.500
]

# ----------------------------------------------------------------------------------------------
# 3.  new vias.  0.20 hole / 0.35 land, through-hole.  Every one is a legal site on route_width's
#     own raster (tools/stage5/corr.via_sites), >= 1.00 mm from every U1 escape, outside U1's land
#     field, >= 0.44 mm from every other via.
# ----------------------------------------------------------------------------------------------
VIAS = [
    ((2.8750, 16.6500), 'C80-2 / SC189 output island, plane entry A'),
    ((2.6250, 16.1250), 'C80-2 / SC189 output island, plane entry B (J3)'),
    ((2.6250, 17.1500), 'C80-2 / SC189 output island, plane entry C (J3)'),
    ((7.6200, 21.3800), 'C12-2'),
    ((9.9200, 21.3800), 'R35-2'),
    ((10.1000, 18.3800), 'R34-8'),
    ((12.2200, 17.6600), 'R34-5 + R34-6 + R34-7'),
    ((12.3000, 12.2750), 'X3-4 second barrel (200 mA, hot-plugged SD socket)'),
    ((13.0000, 12.3750), 'X3-4 first barrel'),
    ((18.9250, 20.1000), 'R19-2 + R97-2 + R98-2'),
    ((19.2200, 13.4400), 'BTN-2'),
    ((19.3400, 2.3200), 'L4-2'),
    ((20.9800, 18.7400), 'R96-2'),
    ((22.6400, 2.1200), 'C133-2 + L5-2'),
    ((23.2600, 15.5000), 'LD5-A'),
    ((23.9400, 2.3200), 'C134-2'),
    ((27.2200, 19.2200), 'U10-8 + R80-1'),
    ((32.1750, 1.0250), 'C5-2'),
    ((32.6250, 1.0000), 'C38-2 + U3-9'),
    ((34.1800, 1.5400), 'C6-2'),
    ((35.2600, 16.3800), 'R82-1 + U3-49'),
    ((36.1200, 13.3000), 'U2-42'),
    ((36.1400, 1.9800), 'C7-2'),
    ((37.2000, 7.0400), 'U3-3'),
    ((38.4400, 3.7800), 'C8-2'),
    ((39.5200, 20.8400), 'Q1-1'),
    ((42.1400, 19.8800), 'Q1-4 + C101-1 + C120-1'),
    ((44.8750, 19.0500), 'C117-1'),
    ((48.3800, 17.8400), 'C118-1'),
    ((51.4200, 6.5400), 'C115-1 + C122-1'),
    ((51.8500, 11.8500), 'C111-1 own barrel (J4)'),
    ((52.1800, 20.3200), 'U4-8'),
    ((52.5750, 4.6250), 'R20-2 (0.325 mm clear of the x = 52.9 cut-line)'),
    ((53.5400, 21.7400), 'C104-1 + C99-1'),
    ((54.7400, 4.6200), 'R23-1'),
    ((57.2400, 22.4800), 'R6-2'),
    ((57.6200, 9.1400), 'C145-1'),
    ((58.2000, 3.5000), 'R1-3 + R1-4'),
    ((59.3400, 16.5800), 'R91-2'),
    ((59.4200, 20.3400), 'R4-8 + R94-2'),
    ((61.8200, 17.0000), 'R92-2'),
    ((61.8200, 19.8400), 'R99-2'),
    ((63.4400, 13.7400), 'R90-2'),
    ((63.4400, 16.5800), 'R93-2'),
]

# ----------------------------------------------------------------------------------------------
# 4.  new copper.  Every polyline starts at a pad CENTRE and ends on a via centre, another pad
#     centre or the end of a kept track (route_emit.py:310-317 accepts nothing else).
#     wish = the width asked for; Plan.run gives min(wish, rule max, widest that keeps 0.09).
# ----------------------------------------------------------------------------------------------
STUBS = [
    # ---- the regulator block: the whole 745 mA rail enters the plane here, so ask for width ----
    ('C80-2', 'Bottom', [(3.9065, 16.6518), (2.8750, 16.6500)], 1.00),
    ('C80-2 b', 'Bottom', [(3.9065, 16.6518), (2.6250, 16.1250)], 1.00),
    ('C80-2 c', 'Bottom', [(3.9065, 16.6518), (2.6250, 17.1500)], 1.00),
    # ---- X3-4, the heaviest single load on the rail (200 mA), two barrels ----
    ('X3-4', 'Top', [(14.1500, 12.3749), (13.0000, 12.3750), (12.3000, 12.2750)], 0.50),
    # ---- west ----
    ('C13-2', 'Bottom', [(3.4498, 21.4400), (3.4330, 20.4000)], 0.20),
    ('C12-2', 'Bottom', [(8.2498, 21.3900), (7.6200, 21.3800)], 0.20),
    ('R35-2', 'Bottom', [(10.5498, 21.3900), (9.9200, 21.3800)], 0.20),
    ('R34-8', 'Bottom', [(10.6200, 18.3901), (10.1000, 18.3800)], 0.20),
    ('R34-7', 'Bottom', [(11.4201, 18.3901), (12.2200, 17.6600)], 0.20),
    ('R34-6', 'Bottom', [(12.2199, 18.3901), (12.2200, 17.6600)], 0.20),
    ('R34-5', 'Bottom', [(13.0200, 18.3901), (12.2200, 17.6600)], 0.20),
    ('BTN-2', 'Top', [(19.2251, 14.9950), (19.2200, 13.4400)], 0.20),
    ('LD5-A', 'Top', [(22.5499, 14.9850), (23.2600, 15.5000)], 0.20),
    # ---- the north band: the shared via sits north of y = 19.6 by more than its 0.3031 halo ----
    ('R97-2', 'Bottom', [(18.1499, 19.3500), (18.9250, 20.1000)], 0.20),
    ('R98-2', 'Bottom', [(19.3498, 19.3500), (18.9250, 20.1000)], 0.20),
    ('R19-2', 'Bottom', [(19.3498, 18.7500), (18.9250, 20.1000)], 0.20),
    ('R96-2', 'Bottom', [(20.5497, 18.7500), (20.9800, 18.7400)], 0.20),
    ('U10-8', 'Bottom', [(27.2150, 18.6950), (27.2200, 19.2200)], 0.20),
    ('R80-1', 'Bottom', [(28.9000, 19.0500), (27.2200, 19.2200)], 0.20),
    ('U3-49', 'Bottom', [(34.7500, 17.5300), (35.2600, 16.3800)], 0.20),
    ('U2-42', 'Top', [(37.1750, 14.3501), (36.1200, 14.3501), (36.1200, 13.3000)], 0.20),
    # ---- the south capacitor row ----
    ('L4-2', 'Bottom', [(19.4502, 3.0500), (19.3400, 2.3200)], 0.20),
    ('L5-2', 'Bottom', [(22.2503, 3.0500), (22.6400, 2.1200)], 0.20),
    ('C133-2', 'Bottom', [(22.7499, 3.9499), (22.6400, 2.1200)], 0.20),
    ('C134-2', 'Bottom', [(23.9498, 3.9499), (23.9400, 2.3200)], 0.20),
    ('C135-2', 'Bottom', [(25.1497, 3.9499), (25.1497, 4.8500), (26.3496, 4.8500)], 0.20),
    ('C136-2', 'Bottom', [(26.3496, 3.9499), (26.3496, 4.8500), (27.9300, 4.8500)], 0.20),
    ('C137-2', 'Bottom', [(27.5496, 3.9499), (27.9300, 4.8500)], 0.20),
    ('C3-2', 'Bottom', [(26.9503, 3.0500), (27.9300, 4.8500)], 0.20),
    ('U3-14', 'Bottom', [(28.3500, 6.1701), (27.9300, 4.8500)], 0.20),
    ('C9-2', 'Bottom', [(19.0500, 4.2499), (16.9500, 6.0000)], 0.20),
    ('U3-27', 'Bottom', [(17.9499, 6.1701), (16.9500, 6.0000)], 0.20),
    ('C5-2', 'Bottom', [(31.5502, 3.0500), (32.1750, 1.0250)], 0.20),
    ('C38-2', 'Bottom', [(33.5492, 3.9499), (32.6250, 1.0000)], 0.20),
    ('C6-2', 'Bottom', [(33.8502, 3.0500), (33.8502, 1.5400), (34.1800, 1.5400)], 0.20),
    ('C7-2', 'Bottom', [(36.1502, 3.0500), (36.1400, 1.9800)], 0.20),
    ('C8-2', 'Bottom', [(38.4502, 3.0500), (38.4400, 3.7800)], 0.20),
    ('U3-3', 'Bottom', [(37.1501, 6.1701), (37.2000, 7.0400)], 0.20),
    ('U3-1', 'Bottom', [(38.7500, 6.1701), (39.7500, 6.4500)], 0.20),
    # ---- U1's surround ----
    ('C108-1', 'Bottom', [(42.1500, 11.0500), (40.9000, 11.8999)], 0.20),
    ('C110-1', 'Bottom', [(48.8100, 7.6500), (47.9000, 8.8999)], 0.20),
    ('C102-1', 'Bottom', [(46.5497, 21.1000), (46.5500, 20.2500)], 0.20),
    ('C117-1', 'Bottom', [(44.3700, 17.8500), (44.8750, 19.0500)], 0.20),
    ('C118-1', 'Bottom', [(48.8100, 17.8500), (48.3800, 17.8400)], 0.20),
    ('C120-1', 'Bottom', [(42.1500, 17.8500), (42.1400, 19.8800)], 0.20),
    ('C101-1', 'Bottom', [(43.4499, 21.1000), (42.1400, 19.8800)], 0.20),
    ('C100-1', 'Bottom', [(40.3500, 21.1000), (39.4000, 21.7500)], 0.20),
    ('C106-1', 'Bottom', [(40.3500, 22.4000), (39.4000, 21.7500)], 0.20),
    ('Q1-1', 'Top', [(40.4500, 20.8499), (39.5200, 20.8400)], 0.20),
    ('Q1-4', 'Top', [(42.1500, 20.8499), (42.1400, 19.8800)], 0.20),
    # ---- the U1 east corridor: every crossing of x = 52.9 is as near perpendicular as the
    #      GND vias at (51.900,13.150) and (51.900,6.400) allow ----
    ('C111-1', 'Bottom', [(51.0300, 11.0500), (51.0300, 11.8500), (51.8500, 11.8500)], 0.20),
    ('C114-1', 'Bottom', [(51.0300, 14.4500), (51.0300, 15.8999), (51.4000, 15.8999)], 0.20),
    ('C115-1', 'Bottom', [(51.0300, 7.6500), (51.4200, 6.5400)], 0.20),
    ('C119-1', 'Bottom', [(53.2501, 11.0500), (52.6000, 11.0500), (51.9500, 12.4495)], 0.20),
    ('C121-1', 'Bottom', [(53.2501, 14.4500), (53.2501, 13.2000), (51.9500, 12.4495)], 0.20),
    ('C122-1', 'Bottom', [(53.2501, 7.6500), (52.3000, 7.6500), (51.4200, 6.5400)], 0.20),
    ('R20-2', 'Bottom', [(52.9499, 3.9499), (52.5750, 4.6250)], 0.20),
    ('U4-8', 'Top', [(51.1500, 21.3050), (52.1800, 20.3200)], 0.20),
    ('C104-1', 'Bottom', [(52.7494, 21.1000), (53.5400, 21.7400)], 0.20),
    ('C99-1', 'Bottom', [(52.7494, 22.4000), (53.5400, 21.7400)], 0.20),
    # ---- east ----
    ('R23-1', 'Bottom', [(54.7498, 3.9499), (54.7400, 4.6200)], 0.20),
    ('R1-4', 'Bottom', [(57.8000, 2.8501), (58.2000, 3.5000)], 0.20),
    ('R1-3', 'Bottom', [(58.6001, 2.8501), (58.2000, 3.5000)], 0.20),
    ('C145-1', 'Top', [(56.6003, 9.1497), (57.6200, 9.1400)], 0.20),
    ('C97-1', 'Top', [(54.8002, 15.7492), (56.6003, 15.7492)], 0.20),
    ('C98-1', 'Top', [(56.6003, 15.7492), (57.6750, 15.7492)], 0.20),
    ('R2-2', 'Bottom', [(56.0491, 22.0500), (56.7000, 21.1000)], 0.20),
    ('R6-2', 'Bottom', [(57.2490, 22.0500), (57.2400, 22.4800)], 0.20),
    ('R4-8', 'Top', [(60.1499, 20.9781), (59.4200, 20.3400)], 0.20),
    ('R94-2', 'Bottom', [(59.3499, 19.8500), (59.4200, 20.3400)], 0.20),
    ('R91-2', 'Bottom', [(59.3499, 17.0100), (59.3400, 16.5800)], 0.20),
    ('R92-2', 'Bottom', [(61.3999, 17.0100), (61.8200, 17.0000)], 0.20),
    ('R99-2', 'Bottom', [(61.3999, 19.8500), (61.8200, 19.8400)], 0.20),
    ('R90-2', 'Bottom', [(63.4500, 14.1700), (63.4400, 13.7400)], 0.20),
    ('R93-2', 'Bottom', [(63.4500, 17.0100), (63.4400, 16.5800)], 0.20),
]


def build():
    tracks = INP0['tracks']
    vias = INP0['vias']
    keep = set(KEEP)
    redraw = set(i for idxs, _, _ in REDRAW for i in idxs)
    assert not (keep & redraw), 'a track cannot be both kept and redrawn'
    for i in keep | redraw:
        assert tracks[i]['net'] == NET, 'index %d is not %s' % (i, NET)
    # every VCC3V3 track that is neither kept nor redrawn comes out; so does every redrawn one
    rem_tracks = [dict(t) for i, t in enumerate(tracks)
                  if t['net'] == NET and i not in keep and i not in redraw]
    rem_tracks += [dict(tracks[i]) for i in sorted(redraw)]
    # provisional: no via removals yet -- the via keep-set falls out of the finished copper
    P = Plan(remove=dict(vias=[], tracks=rem_tracks))
    for (x, y), tag in VIAS:
        P.via(NET, x, y)
    for idxs, layer, pts in REDRAW:
        P.run(NET, layer, pts, wish=0.20, tag='redraw ' + ','.join(str(i) for i in idxs))
    for tag, layer, pts, wish in STUBS:
        P.run(NET, layer, pts, wish=wish, tag=tag)
    # ---- which existing vias still carry something?  every other one comes out ----
    kept_tracks = [tracks[i] for i in sorted(keep)]
    live = set()
    for v in vias:
        if v['net'] != NET:
            continue
        for t in kept_tracks + P.TRACKS:
            for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
                if abs(x - v['x']) <= TOL and abs(y - v['y']) <= TOL:
                    live.add((round(v['x'], 4), round(v['y'], 4)))
    live |= {(round(x, 4), round(y, 4)) for x, y in PROTECT_VIAS}
    rem_vias = [dict(net=v['net'], x=v['x'], y=v['y'])
                for v in vias if v['net'] == NET and (round(v['x'], 4), round(v['y'], 4)) not in live]
    P.remove['vias'] = rem_vias
    return P, rem_vias, rem_tracks


def main():
    P, rv, rt = build()
    out = dict(vias=P.VIAS, tracks=P.TRACKS, remove=dict(vias=rv, tracks=rt))
    txt = json.dumps(out, indent=1)
    path = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else         os.path.join(os.path.dirname(HERE), 'stage5_route.json')
    if '--check' in sys.argv:
        old = io.open(path, encoding='utf-8').read()
        same = old == txt
        print('gen.py --check: %s' % ('IDENTICAL' if same else 'DIFFERENT'))
        if not same:
            sys.exit(1)
    else:
        io.open(path, 'w', encoding='utf-8', newline='\n').write(txt)
        print('wrote %s' % path)
    L = lambda ts: sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts)
    print('  new vias   %d' % len(P.VIAS))
    print('  new tracks %d  (%.3f mm)' % (len(P.TRACKS), L(P.TRACKS)))
    print('  removes    %d via(s), %d track(s) (%.3f mm); nets touched: %s'
          % (len(rv), len(rt), L(rt), ','.join(sorted({t['net'] for t in rt} | {v['net'] for v in rv}))))
    print('  md5 %s' % hashlib.md5(txt.encode('utf-8')).hexdigest())
    if '--report' in sys.argv:
        P.print_report()


if __name__ == '__main__':
    main()
