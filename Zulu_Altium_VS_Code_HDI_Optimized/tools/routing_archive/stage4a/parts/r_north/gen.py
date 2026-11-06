import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 4a was planned in a scratch tree)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4'); from lib import Plan, INP0
# -*- coding: utf-8 -*-
"""Stage 4a, region NORTH: ties for U2-51, X1-MP2, X1-MP3, X1-5, U3-28, U3-41, U3-46, U3-52, U3-54, U10-5, R86-1.
Numbers from tools/route_inputs.json (commit a7aa623) via survey.py / dump.py / viafit.py in this directory.
Six new vias; five pads reach existing GND copper (X1-MH1, X1-MH2, X1-MS1, X1-MS2) with no via."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
P = Plan()
G = 'GND'

# --- Top, around X1 and U2's north row -------------------------------------------------------------
# U2-51 (34.2251, 19.3001; 0.28 x 1.55): no via site within 1.7 mm (the 0.508 band between U2's pins and
# X1's pins takes no 0.35 land).  Hook to the TH pad X1-MH2 (35.5201, 21.2585): north out of the pin,
# east under X1-1 (34.12-34.52 x, 20.5835 up), then NE into MH2's 1.45 mm square.
P.run(G, 'Top', [(34.2251, 19.3001), (34.2251, 20.32)], wish=0.28, tag='U2-51 leg1', clr=0.12)
P.run(G, 'Top', [(34.2251, 20.32), (34.70, 20.32)], wish=0.25, tag='U2-51 leg2', clr=0.12)
P.run(G, 'Top', [(34.70, 20.32), (35.5201, 21.2585)], wish=0.28, tag='U2-51 leg3 -> X1-MH2', clr=0.12)
# X1-5 (31.7201, 21.2585; 0.40 x 1.35): 0.275 mm east of X1-MH1's square; straight west to MH1's centre
P.run(G, 'Top', [(31.7201, 21.2585), (30.5199, 21.2585)], wish=0.40, tag='X1-5 -> X1-MH1', clr=0.12)
# X1-MP2 / X1-MP3 (shell pads, 1.5 x 1.9 at y 23.9585): the only via cells near them sit in the USB pair's
# Top band north of X1's pins (y 21.93-23.01) or in the 0.55 mm slots between the MPs; instead run along
# y 23.9585 (dead space between the connector's pads) into MS1 / MS2, the shell's TH pins inside MP1 / MP4
P.run(G, 'Top', [(32.02, 23.9585), (29.5199, 23.9585)], wish=0.50, tag='X1-MP2 -> X1-MS1', clr=0.12)
P.run(G, 'Top', [(34.02, 23.9585), (36.5201, 23.9585)], wish=0.50, tag='X1-MP3 -> X1-MS2', clr=0.12)

# --- Bottom -----------------------------------------------------------------------------------------
# R86-1 (31.9, 21.4498; 0.7 x 0.9): 0.305 mm east of X1-MH1's square on Bottom; west to MH1's centre
P.run(G, 'Bottom', [(31.9, 21.4498), (30.5199, 21.2585)], wish=0.50, tag='R86-1 -> X1-MH1', clr=0.12)
# U10-5 (27.215, 22.505; 2.07 x 0.51): via straight below the pad centre, between pins 5 and 6 (0.175 / 0.235
# to them; nothing else within 1.2 mm) -- route_emit wants the pad end of a tie at the pad CENTRE
P.via(G, 27.215, 21.90)
P.run(G, 'Bottom', [(27.215, 22.505), (27.215, 21.90)], wish=0.40, tag='U10-5 -> via', clr=0.12)
# U3-28 (17.9499, 17.53): no site within 0.8 mm (VCC3V3 L4 spine x 16.75-18.25, FT-VPHY/VPLL inner slots,
# the A4 fan-out); site at (18.56, 16.18): 0.135 to the spine, 0.143 to A4's L4 track, c-c 0.507 to A4's via
P.via(G, 18.56, 16.18)
P.run(G, 'Bottom', [(17.9499, 17.53), (17.9499, 16.70)], wish=0.45, tag='U3-28 leg1', clr=0.12)
P.run(G, 'Bottom', [(17.9499, 16.70), (18.56, 16.18)], wish=0.40, tag='U3-28 leg2 -> via', clr=0.12)
# U3-41 (28.35, 17.53): pocket between the pad (0.095), the FT-VCORE Top riser at x 28.6 (0.135) and the
# UDQM L3 track (0.13, rule 0.10) -- every cell has one gap under 0.12; the own-pad one is the harmless one
P.via(G, 28.14, 16.66)
P.run(G, 'Bottom', [(28.35, 17.53), (28.14, 16.66)], wish=0.45, tag='U3-41 -> via', clr=0.12)
# U3-46 (32.35, 17.53): straight south, site 0.18 from the pad, 0.194 from D10's L3 track
P.via(G, 32.35, 16.575)
P.run(G, 'Bottom', [(32.35, 17.53), (32.35, 16.575)], wish=0.45, tag='U3-46 -> via', clr=0.12)
# U3-52 (37.1501, 17.53): boxed by R83-2 (north, y 18.6) and U3-53 (east); via NE at (37.775, 18.475):
# 0.170 to U3-53, 0.173 to R83-2, 0.200 to the L4 spine; a 0.2 mm leg passes R83-2's corner at 0.124
P.via(G, 37.775, 18.475)
P.run(G, 'Bottom', [(37.1501, 17.53), (37.1501, 18.26)], wish=0.30, tag='U3-52 leg1', clr=0.12)
P.run(G, 'Bottom', [(37.1501, 18.26), (37.775, 18.475)], wish=0.30, tag='U3-52 leg2 -> via', clr=0.12)
# U3-54 (38.75, 17.53): east is the VCC3V3 Top column x 39.3 and the L4 spine legs; via NW at (38.35, 18.40):
# 0.147 to U3-53 and U3-54, 0.160 to the spine leg; 0.58 c-c from U3-52's via
P.via(G, 38.35, 18.40)
P.run(G, 'Bottom', [(38.75, 17.53), (38.35, 18.40)], wish=0.30, tag='U3-54 -> via', clr=0.12)

P.print_report()
P.dump(os.path.join(HERE, 'plan.json'))
print('wrote plan.json: %d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
