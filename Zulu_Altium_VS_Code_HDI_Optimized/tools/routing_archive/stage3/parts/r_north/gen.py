import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
# -*- coding: utf-8 -*-
"""Stage 3, REGION "north": R80-1 R81-1 R82-1 U3-43 U3-49 U2-56 U2-50 U2-42 from the trunk's north tap.

Re-run 2026-09-21 (after the usage-limit break) against the judge's repaired trunk s3_trunk/plan.json
(md5 a8bb54e84b8c195e7f559a8d85c9f8bc): the north tap (39.00,19.00) Bottom and everything inside the box
are unchanged, the report is identical to the one measured on the interrupted run's trunk; the only edit is
that the Bottom tie tap -> C100-1 is now the plan's FIRST track, so the plan starts on the tap's layer.

    python gen.py                  writes plan.json next to this file (only this region's copper), prints tight segments
    python gen.py --all            prints every segment
    python gen.py --bottom-strip   the alternative that stays on Bottom from the tap (see 1b); gated too, see the result

Tap: the north via pair; the tap point is (39.00, 19.00) = the west via (a Bottom track END of the trunk's 0.30 stub,
the END of the trunk's 1.1 mm L4 stub, and the via centre).  Every branch here starts at a track END, a via
centre or a pad centre (route_emit / islands join end to end only).

1a. FEED (default): the only Bottom lane west from the tap is the 0.47 mm band y 18.13-18.60 between U3's north pad
    row and the LED resistors R80..R83, and the trunk-only board keeps exactly three VSS tie sites in that band:
    U3-52 (36.75,18.33) (37.55,18.33), U3-54 (38.35,18.33) (route_stitch's rules, 0.05 grid, the trunk judge's
    R2 repair).  A Bottom strip from the tap takes all three.  So the strip is fed from its WEST end instead: L4
    from the tap via's centre back into the spine's own 1.5 mm footprint (1.05 wide at y 19.6 -> zero new L4 area
    for 9.5 mm), a 1.15 mm L4 stub up the empty channel x 28.3-29.8 between U10's pads and X1's mounting hole MH1
    (corr.py: legal via sites, margin 0.525), via V2 (29.10, 20.75), Bottom 0.5 down the channel into R80-1, and the
    0.23 mm strip east along y 18.365 (0.12 clearance to U3's pads and to the resistor pads) with a node at every
    own pad: R80-1, U3-43, R81-1, R82-1, U3-49.  V2's Top land (bottom 20.575) stays 0.09 clear of the USB pair's
    y 20.1-20.5 slot (the pair keeps 0.539 on both rows).  The tap itself is tied on Bottom, 1.0 wide, to C100-1
    (40.35,21.10) -- the only VCC3V3 capacitor within 5 mm, as taps.json asks (0.35 mm past the box edge; it is the
    northbank region's pad, a second tie there is harmless).
1b. --bottom-strip: Bottom from the tap down to the band (U3-54's top edge binds, 0.23) and west along y 18.365
    with the same nodes; no L4, no V2, no C100 tie.  Passes every gate; loses the three VSS sites; 15 north-band
    sites instead of ~90.
2.  U2-50 (VREGIN 70 mA) and U2-56: via V1 (30.30, 16.40) in U3's pocket band (corr.py: legal, margin 0.146 --
    between the D8/D9 fan-out vias, 0.435 above VCC1V0's 1.5 mm Bottom band), fed from U3-43's pad on Bottom;
    Top from V1 up between the D9 via and pin 58 into U2's body (no exposed pad) to a node under pin 56, a 0.25 run
    under pins 55..51 (NC x4, GND) to a node under pin 50, and 0.45 stubs UP into the pads.  Nothing of this region
    lies north of y 19.3 on Top: the USB pair's slot and the single via slot in the pocket north of pin 49
    (35.9, 19.85; corr.py margin 0.25) stay free -- FT-VCORE's pin 49 can take that slot to L3, and its inner end
    keeps the Top corridor down the west side of USB5V0's Top track to pin 37 and the SW/NW interior.
3.  U2-42 (VCCIO, ~5 mA, east side y 14.35): the pad is walled on Top by the SDRAM fan-out via column x 38.5
    (D11/D10/UDQM/D8/CKE at 0.45 pitch, lands 0.10 apart) and can only be entered through the 0.375 mm column
    between the pins' outer ends (x 37.95) and those lands (x 38.325) -- corr.py's only path.  Fed from the trunk's
    Top NW-branch node (39.3, 15.5) past the D11 via, down the column at x 38.14 (0.13-0.14 wide, 0.12 clear) and
    west into the pad.  U2-43 (UART_FT_DTR#) loses the column north of its pad but keeps its inner end -> U2's Top
    interior pocket -> the NE-corner passage (0.46 between pin 48's corner and USB5V0's track end) -> the lane
    x 36.9-37.9 north (route_reach and route_foreclosure agree, see the result).
"""
import io, json, os, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3')
from lib import Plan, INP0
TRUNK = PARTS + '/s3_trunk/plan.json'
P = Plan(base_plans=[json.load(open(p)) for p in [TRUNK]])

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
BOTTOM_STRIP = '--bottom-strip' in ARGS
OUT = os.path.join(HERE, 'plan_bottom_strip.json' if BOTTOM_STRIP else 'plan.json')
V = 'VCC3V3'
T, B, L4 = 'Top', 'Bottom', 'L4-SIG'


def run(layer, pts, wish=0.5, tag='', clr=0.12, floor=0.09):
    P.run(V, layer, pts, wish, tag, clr, floor)


def via(x, y):
    P.via(V, x, y)


# pads (centres, from stage3_facts.md)
U3_49 = (34.75, 17.53); U3_43 = (29.95, 17.53)
R82_1 = (33.50, 19.05); R81_1 = (31.20, 19.05); R80_1 = (28.90, 19.05)
U2_50 = (34.725, 19.30); U2_56 = (31.725, 19.30); U2_42 = (37.175, 14.35)
C100_1 = (40.35, 21.10)
TAP = (39.00, 19.00)                       # Bottom track END (trunk) + via centre + L4 track END
SPINE_Y = 19.60                            # the trunk's 1.5 mm L4 spine centreline (edges 18.85-20.35)
NWNODE = (39.30, 15.50)                    # trunk Top node: end of the NW branch x 39.3, start of the run to (40.85,15.6)
SY = 18.365                                # the Bottom strip: U3 pad tops 18.13 / resistor bottoms 18.60

# ------------------------------------------------------------------------------------------------
# 1. FEED
# ------------------------------------------------------------------------------------------------
if not BOTTOM_STRIP:
    V2 = (29.10, 20.75)
    # first segment: on the tap's layer (Bottom), starting exactly at the tap point
    # MERGE 2026-09-21: 0.5, not 1.0 (the tie carries the capacitor's AC current only; the northbank region ties
    # C100-1 to the trunk as well): the 1.0 band killed 15 stitching sites nothing else did, and the U1-surround
    # floor (65 %) broke on the whole-board merge.
    run(B, [TAP, C100_1], 0.5, 'tap -> C100-1 (Bottom tie of the only nearby capacitor)')
    run(L4, [TAP, (38.60, SPINE_Y)], 1.05, 'tap via -> spine line (inside the trunk stub/spine footprint)')
    run(L4, [(38.60, SPINE_Y), (29.10, SPINE_Y)], 1.05, 'L4 west inside the 1.5 spine, 140 mA')
    run(L4, [(29.10, SPINE_Y), V2], 1.05, 'L4 stub up the U10/MH1 channel to V2')
    via(*V2)
    run(B, [V2, (29.10, 19.60), R80_1], 0.5, 'V2 -> R80-1 (Bottom, channel)')
    run(B, [R80_1, (R80_1[0], SY)], 0.45, 'R80-1 pad -> strip node')
    run(B, [(R80_1[0], SY), (U3_43[0], SY)], 0.5, 'strip: R80-1 -> U3-43 node, 133 mA')
else:
    run(B, [TAP, (38.60, SY)], 0.5, 'tap -> strip (U3-54 binds)')
    run(B, [(38.60, SY), (U3_49[0], SY)], 0.5, 'strip, 140 mA: tap -> U3-49 node')
    run(B, [(U3_49[0], SY), (R82_1[0], SY)], 0.5, 'strip: U3-49 -> R82-1 node')
    run(B, [(R82_1[0], SY), (R81_1[0], SY)], 0.5, 'strip: R82-1 -> R81-1 node')
    run(B, [(R81_1[0], SY), (U3_43[0], SY)], 0.5, 'strip: R81-1 -> U3-43 node')
    run(B, [(U3_43[0], SY), (R80_1[0], SY)], 0.5, 'strip: U3-43 -> R80-1 node')
    run(B, [(R80_1[0], SY), R80_1], 0.45, 'stub up into R80-1')

# the strip's pads (nodes at the x of every own pad; stubs end at pad centres)
run(B, [(U3_43[0], SY), U3_43], 0.45, 'stub down into U3-43')
if not BOTTOM_STRIP:
    run(B, [(U3_43[0], SY), (R81_1[0], SY)], 0.5, 'strip: U3-43 -> R81-1 node')
run(B, [(R81_1[0], SY), R81_1], 0.45, 'stub up into R81-1')
if not BOTTOM_STRIP:
    run(B, [(R81_1[0], SY), (R82_1[0], SY)], 0.5, 'strip: R81-1 -> R82-1 node')
run(B, [(R82_1[0], SY), R82_1], 0.45, 'stub up into R82-1')
if not BOTTOM_STRIP:
    run(B, [(R82_1[0], SY), (U3_49[0], SY)], 0.5, 'strip: R82-1 -> U3-49 node')
run(B, [(U3_49[0], SY), U3_49], 0.45, 'stub down into U3-49')

# ------------------------------------------------------------------------------------------------
# 2. V1 in U3's pocket band, fed from U3-43's pad; Top up into U2's body to pins 56 and 50 (from below).
# ------------------------------------------------------------------------------------------------
V1 = (30.30, 16.40)
run(B, [U3_43, V1], 0.4, 'U3-43 pad -> V1 (Bottom, 75 mA)')
via(*V1)
RY = 18.28                                 # run under the north pads: bottoms at 18.525, 0.12 clear at 0.25 wide
run(T, [V1, (30.30, 17.35), (U2_56[0], RY)], 0.25, 'V1 -> node under pin 56 (Top)')
run(T, [(U2_56[0], RY), U2_56], 0.45, 'stub up into U2-56')
run(T, [(U2_56[0], RY), (U2_50[0], RY)], 0.25, 'run under pins 55..51 to the node under pin 50')
# MERGE 2026-09-21: 0.28 (the pad's own width), not 0.45: the 0.45 stub's round end reached 0.225 below the
# node and closed the only way into pin 49 (FT-VCORE, the ft region) between this run and USB5V0's Top
# diagonal; at 0.28 the end reaches 18.14 and the ft line at y 17.92 keeps 0.12.  70 mA over 1 mm of 0.28:
# 1.75 mOhm, 0.12 mV.
run(T, [(U2_50[0], RY), U2_50], 0.28, 'stub up into U2-50 (VREGIN)')

# ------------------------------------------------------------------------------------------------
# 3. U2-42 from the trunk's NW-branch node, through the column between the pin ends and the fan-out via lands.
# ------------------------------------------------------------------------------------------------
CX = 38.14
run(T, [NWNODE, (38.50, 15.55), (CX, 15.20)], 0.3, 'NW node -> column top (past the D11 via)')
run(T, [(CX, 15.20), (CX, U2_42[1])], 0.3, 'column x 38.14')
run(T, [(CX, U2_42[1]), U2_42], 0.3, 'west into U2-42')

if __name__ == '__main__':
    P.dump(OUT)
    P.print_report(only_tight='--all' not in ARGS)
    print('%d vias, %d tracks -> %s' % (len(P.VIAS), len(P.TRACKS), OUT))
