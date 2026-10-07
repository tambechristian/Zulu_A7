import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 4a was planned in a scratch tree)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4'); from lib import Plan, INP0
# Stage 4a, region "south" (x 16-40, y 0-7.5): 24 GND pads, all on Bottom except X4-2 (Top).
# Geometry (route_inputs.json, a7aa623): the 0805 row at y 3.05 (pads y 2.60-3.50) and the 0201 row at
# y 3.95 (pads y 3.80-4.10) leave a 0.30 mm gap; the VCC3V3 trunk (y 4.85, 1.2 wide -> y 4.25-5.45) seals
# the 0201 row from the north; the Top VBATT/X4 copper and the X2 header pads decide where a via can go.
# Every tie ends inside a pad, on a via centre or on another tie's end (end-to-end joins only).
import os
HERE = os.path.dirname(os.path.abspath(__file__))
P = Plan()
B, T = 'Bottom', 'Top'
G = 'GND'

def via(x, y):
    P.via(G, x, y); return (x, y)

def run(layer, pts, w, tag, exact=None, clr=0.12):
    P.run(G, layer, pts, wish=w, tag=tag, exact=exact, clr=clr)

# --- west end.  R18-1 has exactly one exit, the R18-1/R18-2 slot (21 legal via cells at (20.7, 3.77-3.93)):
#     north the VCC3V3 trunk at 0.12, west the VCC3V3 diagonal C9-2 -> L4-2 crosses the row gap, south the
#     L4-2/L5-1 gap narrows to 0.248 under the FT-VPLL track.  The slot was also FT-REF's (R18-2) only via
#     slot; FT-REF keeps a way out instead: R18-2's bottom edge -> the row gap (x 21.0-21.55 left free) ->
#     the L5-1/L5-2 gap (0.425 strip west of C133-1's drop) -> the y 2.03-2.60 channel, where it has via
#     slots at ~(20.75-21.2, 2.3) and (22.05-22.3, 2.3) -- route_foreclosure checks it.
#     C133-1 (boxed by R18-2, C133-2, L5-2, the VCC3V3 diagonal; no via site north) runs west along the
#     0.30 row gap and drops down the L5 gap at x 21.6 to a via above X2-32.
vR18 = via(20.70, 3.85)
run(B, [(20.05, 4.2499), vR18], 0.4, 'R18-1 -> via (slot)')
v133 = via(21.60, 2.316)
run(B, [(22.15, 3.9499), (22.15, 3.65), (21.60, 3.65)], 0.1, 'C133-1 row-gap bus W', exact=0.1)
run(B, [(21.60, 3.65), (21.60, 3.45)], 0.1, 'C133-1 drop under R18-2', exact=0.1)
run(B, [(21.60, 3.45), v133], 0.15, 'C133-1 drop L5 gap -> via', exact=0.15)
# C9-1: the pocket west of the pad (VU Top track above 4.2, L4-1 below 3.5); the existing GND via at
#     (15.8165, 4.3485) is 1.58 mm away, so a new one 0.36 mm from the pad edge.
vC9 = via(17.10, 3.90)
run(B, [(17.75, 4.2499), vC9], 0.4, 'C9-1 -> via')

# --- C139 group: via between X2-32 and X2-31 (rect clearance kept), C134-1 chains down into C139-1.
v139 = via(23.10, 2.25)
run(B, [(23.3503, 3.05), v139], 0.4, 'C139-1 -> via')
run(B, [(23.3499, 3.9499), (23.3503, 3.05)], 0.3, 'C134-1 -> C139-1')

# --- C3 group: no legal via in the pocket right under C3-1 (X2-30 rect, the FT-VCORE via + L4 track at
#     x 25.2, the VBATT Top track); the nearest is (25.6, 1.8).  C136-1 drops straight into C3-1;
#     C135-1 and C137-1 are boxed by VCC3V3/FT-VCORE pads and reach C136-1's stub through the row gap.
v3 = via(25.60, 1.80)
run(B, [(25.6503, 3.05), v3], 0.3, 'C3-1 -> via')
#     (judge) v3 serves four pads: a second via 0.63 mm SW (corr.py margin 0.25 cells; land 1.025 inside the edge) in parallel.
v3b = via(25.40, 1.20)
run(B, [v3, v3b], 0.3, 'v3 -> v3b (second via)')
run(B, [(25.7497, 3.9499), (25.75, 3.65)], 0.3, 'C136-1 stub (upper)')
run(B, [(25.75, 3.65), (25.6503, 3.05)], 0.3, 'C136-1 stub (lower) -> C3-1 centre')
run(B, [(24.5498, 3.9499), (24.55, 3.65), (25.75, 3.65)], 0.1, 'C135-1 row-gap bus -> C136-1 stub', exact=0.1)
run(B, [(26.9497, 3.9499), (26.95, 3.65), (25.75, 3.65)], 0.1, 'C137-1 row-gap bus -> C136-1 stub', exact=0.1)

# --- C4 group: the single legal site SE of C4-1 (VBATT Top tracks below, C4-1/C4-2 above).
v4 = via(28.52, 2.43)
run(B, [(27.9502, 3.05), v4], 0.4, 'C4-1 -> via')
run(B, [(28.1496, 3.9499), (27.9502, 3.05)], 0.3, 'C138-1 -> C4-1 centre')

# --- C6 group: via under C6-1 (also X4-2's via, on Top).  C5-1 / C152-1 / C153-1 have no via site
#     reachable on Bottom within 2.6 mm (VCC3V3 walls at x 29.25 and 31.55 down to y 0.78, the Top
#     VBATT/X4-1 copper over the pocket, FT-VCORE north): they chain east along the row gap to C154-1,
#     which reaches C6-1.  C38-1 drops straight into C6-1.
v6 = via(32.55, 2.25)
run(B, [(32.5502, 3.05), v6], 0.5, 'C6-1 -> via')
#     (judge) v6 is the only plane entry of eight pads: a second via 0.69 mm SW (corr.py best cell, margin 0.25) in parallel.
v6b = via(32.40, 1.575)
run(B, [v6, v6b], 0.3, 'v6 -> v6b (second via)')
run(T, [(33.40, 3.0501), v6], 0.5, 'X4-2 (Top) -> via')
run(B, [(32.9493, 3.9499), (32.5502, 3.05)], 0.3, 'C38-1 -> C6-1 centre')
run(B, [(31.7494, 3.9499), (32.5502, 3.05)], 0.3, 'C154-1 -> C6-1 centre')
run(B, [(30.2502, 3.05), (30.50, 3.65)], 0.3, 'C5-1 centre -> stub up (lower)')
run(B, [(30.50, 3.65), (30.5494, 3.9499)], 0.3, 'C5-1 stub up (upper) -> C153-1')
run(B, [(29.3495, 3.9499), (29.35, 3.65), (30.50, 3.65)], 0.1, 'C152-1 row-gap bus -> C5-1 stub', exact=0.1)
run(B, [(30.50, 3.65), (31.75, 3.65), (31.7494, 3.9499)], 0.1, 'C5-1 stub -> row-gap bus -> C154-1', exact=0.1)

# --- C7 group: via SW of C7-1 in the pocket between the VCC3V3 diagonal and FT-VPLL.
v7 = via(34.30, 2.00)
run(B, [(34.8502, 3.05), v7], 0.4, 'C7-1 -> via')
run(B, [(34.1492, 3.9499), (34.8502, 3.05)], 0.3, 'C40-1 -> C7-1 centre')
run(B, [(35.3491, 3.9499), (34.8502, 3.05)], 0.3, 'C41-1 -> C7-1 centre')

# --- C8-1: the dead pocket north of the pad between the two VCC3V3 verticals (36.36 / 38.0).
v8 = via(37.15, 4.00)
run(B, [(37.1502, 3.05), v8], 0.5, 'C8-1 -> via')

# --- U3-6 / U3-12 (SDRAM GND pins): south is sealed by X4's mounting pads + the VU Top tracks, the
#     Top U2 pin row (y 7.125-8.675) forbids a via beside the pins; the first legal site is north of it,
#     between the routed D3 / FT-VPHY (U3-6) and D7 / FT-VCORE (U3-12) escapes.
vU36 = via(34.475, 9.00)
run(B, [(34.75, 6.1701), (34.475, 7.00), vU36], 0.45, 'U3-6 -> via N')
# U3-12: a via in its Bottom channel north (x 29.5-30.2, y 6.86-9.14) is the ONLY Top escape corridor of
#     U2-21 (PROG#) and U2-22 (DONE) -- 0.52 wide, a 0.35 land + 2 x 0.09 needs 0.53 -- so route_foreclosure
#     seals them for any via there.  The pin's one other exit is the 3 mil passage south-west (between U3-13,
#     the VCC3V3 trunk's end cap and the FT-VCORE cap) into C152-1's island, which reaches V6.
#     (judge) the exit was 0.085/0.090 at 0.12 clearance; 0.10 clearance gives 0.115/0.13 (max 0.138/0.152, U3-13 / FT-VCORE cap).
run(B, [(29.9499, 6.1701), (29.54, 5.55), (29.54, 4.30), (29.3495, 3.9499)], 0.3, 'U3-12 -> C152-1 chain', clr=0.10)
P.dump(os.path.join(HERE, 'plan.json'))
P.print_report()
print('vias %d tracks %d' % (len(P.VIAS), len(P.TRACKS)))
