import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3'); from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])
# -*- coding: utf-8 -*-
"""Stage 3, REGION "south" (box x 16-40, y 0-9, 200 mA max): VCC3V3 from the trunk's south tap (16.5, 6.0)
Bottom to the 23 pads C9-2, L4-2, L5-2, C133..C138-2, C3..C8-2, C38-2, U3-27/14/9/3/1 and U2-20/31.

    python gen.py            writes plan.json next to this file and prints every segment's report

Topology (all Bottom unless said; every track end is a pad CENTRE, a via or a shared track end):
  A  tap exit: (16.5,6.0) and the trunk's second via (16.95,6.0) both run to the node (17.3,5.13).
  B  narrow band bus y 5.13 under U3's south pads, x 17.3 -> 22.0 (the 0.69 slot between C9/R18 and U3's
     pad row): stubs up into U3-27 and down into C9-2; C9-2 -> L4-2 diagonally.
  C  wide band bus y 4.835 (1.2 mm) x 22.75 -> 28.75 between the 0201 row (top 4.10) and U3's pads (5.57):
     nodes at every 0201 VCC3V3 pad (stub down into the pad centre) and at x 28.35 (stub up into U3-14).
     L5-2 hangs on C133-2, C3-2 on C137-2, C4-2 on C138-2 (the 0603s are boxed by the 0201 row's 0.3 gaps).
  D  channel bus y 0.78 (0.6 mm, 0.48 to the outline) x 29.25 -> 37.9 along the board edge in the wide part of
     the Bottom channel (no X2 pins between x 27.43 and 38.61): 0.5 stubs up into C4-2, C5-2, C7-2, a diagonal
     from x 33.3 into C6-2 (leaves the (34.2,2.25) GND sites of C7-1/X4-2) and a diagonal into C8-2.  Fed twice:
     C138-2 -> C4-2 and C3-2 -> (26.95,2.315) -> (27.9,2.315) -> (29.25,0.78).  It hugs the edge so the GND
     stitching reservoir under VU's Top track (x 34.3-38.4, y 1.2-2.0) and the pad-adjacent sites (y 2.25-2.65) survive.
  E  C6-2 -> C38-2 diagonal, C38-2 -> y 5.1 bar hugging U3-8 -> U3-9; C7-2 -> x 36.36 (east of C41-2) -> a y 5.05 bar
     x 36.36-38.75 with stubs into U3-3 and U3-1; C8-2 -> x 38.0 (west of the SDRAM-CS# via 38.5,4.4) -> the
     same bar.  The band east of x 29.4 carries NO east-west VCC3V3: FT-VCORE's 100 nF (C152-154-2, x 29.95-32.35)
     and C40-2/C41-2 stay reachable from U3's pad gaps at 29.55/30.35/31.15/31.95/34.35/35.95.
  F  U2-20 and U2-31 (Top): via A ON the wide bus at (27.93,4.85), Top north at x 27.93 and east through the
     0.145 mm slot between X4-MP1 / VU (tops 6.80 / 6.75) and U2's pin bottoms (7.125) under pins 17-31, up into
     both pads from the south.  U2-20 cannot be entered from the north (D7's fan-out via land is 0.10 above the
     pad) and a pocket via north of the pin row cannot stay inside the box (centre y >= 8.94).
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
V, B, T = 'VCC3V3', 'Bottom', 'Top'


def pad(ref, num):
    for k in ('bottom_pads', 'top_pads', 'th_pads'):
        for p in INP0[k]:
            if p['ref'] == ref and p['pad'] == num:
                return (p['x'], p['y'])
    raise KeyError(ref + '-' + num)


def run(layer, pts, wish, tag, clr=0.12):
    P.run(V, layer, pts, wish, tag, clr, 0.09)


def via(x, y):
    P.via(V, x, y)


TAP, TAP2 = (16.5, 6.0), (16.95, 6.0)
N0 = (17.3, 5.13)
YB, YW, YC = 5.13, 4.85, 0.78           # narrow band bus, wide band bus, channel bus (0.48 to the outline)
# JUDGE 2026-09-21: YC was 0.6, i.e. the bus's south edge exactly 0.30 from the routed outline (the 0.25 rule
# passes, but JLC's routed-edge minimum is 0.3 with a +-0.2 outline tolerance, and this was the only copper on the
# whole board within 0.35 of the edge).  0.78 keeps 0.48; the five risers follow; a GND via still fits between the
# bus (top edge 1.08) and the 0603 row (centre y >= 1.345, plane pull-back 0.80).
VA = (27.93, YW)                         # via A on the wide bus: feeds U2-20 and U2-31 on Top through the slot

U3_27, U3_14, U3_9, U3_3, U3_1 = pad('U3', '27'), pad('U3', '14'), pad('U3', '9'), pad('U3', '3'), pad('U3', '1')
C9, L4, L5 = pad('C9', '2'), pad('L4', '2'), pad('L5', '2')
C133, C134, C135, C136, C137, C138, C38 = [pad(c, '2') for c in ('C133', 'C134', 'C135', 'C136', 'C137', 'C138', 'C38')]
C3, C4, C5, C6, C7, C8 = [pad(c, '2') for c in ('C3', 'C4', 'C5', 'C6', 'C7', 'C8')]
U2_20, U2_31 = pad('U2', '20'), pad('U2', '31')

# A. tap exit (the first segment starts exactly at the tap)
run(B, [TAP, N0], 0.62, 'A tap exit from the tap via')
run(B, [TAP2, N0], 0.45, 'A tap exit from the 2nd via')

# B. narrow band bus y 5.13 (C9-1 top 4.70 / U3 pads 5.57)
run(B, [N0, (U3_27[0], YB), (C9[0], YB), (22.0, YB)], 0.62, 'B band bus y5.13')
run(B, [(U3_27[0], YB), U3_27], 0.45, 'B stub up into U3-27')
run(B, [(C9[0], YB), C9], 0.6, 'B stub down into C9-2')
run(B, [C9, L4], 0.6, 'B C9-2 -> L4-2')

# C. wide band bus y 4.835 (0201 row top 4.10 / U3 pads 5.57)
run(B, [(22.0, YB), (C133[0], YW)], 0.62, 'C taper into the wide bus')
run(B, [(C133[0], YW), (C134[0], YW), (C135[0], YW), (C136[0], YW), (C137[0], YW), VA, (U3_14[0], YW), (C138[0], YW)], 1.2, 'C wide band bus y4.85')
for c in (C133, C134, C135, C136, C137, C138):
    run(B, [(c[0], YW), c], 0.3, 'C stub into 0201 x%.2f' % c[0])
run(B, [(U3_14[0], YW), U3_14], 0.45, 'C stub up into U3-14')
run(B, [C133, L5], 0.4, 'C C133-2 -> L5-2')
run(B, [C137, C3], 0.34, 'C C137-2 -> C3-2')
run(B, [C138, C4], 0.4, 'C C138-2 -> C4-2 (feed 1 of the channel bus)')

# D. channel bus y 0.78 along the edge, x 29.25 -> 37.9
run(B, [C3, (C3[0], 2.315)], 0.33, 'D C3-2 down to the channel')
run(B, [(C3[0], 2.315), (27.9, 2.315)], 0.33, 'D under X2-30 corner')
run(B, [(27.9, 2.315), (C4[0], YC)], 0.55, 'D into the channel bus (feed 2)')
run(B, [(C4[0], YC), (C5[0], YC), (33.3, YC), (C7[0], YC), (37.9, YC)], 0.6, 'D channel bus y0.78')
for c in (C4, C5, C7):
    run(B, [(c[0], YC), c], 0.5, 'D stub up into 0603 x%.2f' % c[0])
run(B, [(33.3, YC), C6], 0.45, 'D diagonal up into C6-2 (keeps the 34.2,2.25 GND sites)')
run(B, [(37.9, YC), C8], 0.5, 'D diagonal up into C8-2')

# E. east loads from the channel bus
run(B, [C6, C38], 0.5, 'E C6-2 -> C38-2')
run(B, [C38, (C38[0], 5.1)], 0.6, 'E C38-2 up into the band')
run(B, [(C38[0], 5.1), (32.5, 5.1)], 0.6, 'E y5.1 bar hugging U3-8 (FT-VCORE lane y 4.2-4.7 stays open)')
run(B, [(32.5, 5.1), U3_9], 0.45, 'E into U3-9')
run(B, [C7, (36.36, 3.55)], 0.45, 'E C7-2 -> x36.36')
run(B, [(36.36, 3.55), (36.36, 5.05)], 0.28, 'E x36.36 up past C41-2')
run(B, [(36.36, 5.05), (U3_3[0], 5.05), (38.0, 5.05), (U3_1[0], 5.05)], 0.7, 'E y5.05 bar under U3-3/U3-1')
run(B, [(U3_3[0], 5.05), U3_3], 0.45, 'E stub up into U3-3')
run(B, [(U3_1[0], 5.05), U3_1], 0.45, 'E stub up into U3-1')
run(B, [C8, (38.0, 3.9)], 0.6, 'E C8-2 -> x38.0')
run(B, [(38.0, 3.9), (38.0, 5.05)], 0.4, 'E x38.0 up past the CS# via')

# F. U2-20 (Top, above X4-MP1): via A on the wide bus at (27.93, 4.85) -- the only legal site between VU's Top
#    end cap (27.3,4.1) r 0.7, X4-MP1's west edge 28.2 and the SDRAM-CS# L4 track (y 5.23 there) -- then Top north
#    at x 27.93 and east through the 0.145 mm slot between X4-MP1 (top 6.80) and U2's pin bottoms (7.125).
#    U2-20 cannot be entered from the north: D7's fan-out via (29.325,8.95) has a Top land 0.10 mm above the pad.
via(*VA)
run(T, [VA, (VA[0], 6.5)], 0.3, 'F Top via A north at x27.93')
run(T, [(VA[0], 6.5), (VA[0], 6.9625)], 0.145, 'F Top up to the slot', clr=0.09)          # forced: U2-17 corner
run(T, [(VA[0], 6.9625), (U2_20[0], 6.9625)], 0.145, 'F Top slot X4-MP1 / U2 pins', clr=0.09)  # forced: 0.325 slot
run(T, [(U2_20[0], 6.9625), (U2_20[0], 7.2)], 0.145, 'F Top into U2-20 (slot part)', clr=0.09)
run(T, [(U2_20[0], 7.2), U2_20], 0.28, 'F Top up into U2-20')
# U2-31 (Top): the same slot continues east under pins 21-31 (X4-MP1, VU's y 6.4 Top run and its corner cap all
#    stay >= 0.09 below it) to x 34.725, then up into the pad.  A via north of U2's pins cannot stay inside the box
#    (its land must clear the pin tops at 8.675 -> centre y >= 8.94), so no pocket via is used.
run(T, [(U2_20[0], 6.9625), (U2_31[0], 6.9625)], 0.145, 'F Top slot on east to U2-31', clr=0.09)   # forced: 0.325 slot
run(T, [(U2_31[0], 6.9625), (U2_31[0], 7.2)], 0.145, 'F Top into U2-31 (slot part)', clr=0.09)
run(T, [(U2_31[0], 7.2), U2_31], 0.28, 'F Top up into U2-31')

P.dump(os.path.join(HERE, 'plan.json'))
P.print_report()
print('%d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
