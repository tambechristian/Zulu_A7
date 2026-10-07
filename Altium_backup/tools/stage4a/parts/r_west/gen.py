import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 4a was planned in a scratch tree)
import sys, json; sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4'); from lib import Plan, INP0
# Stage 4a, region "west": the eight open GND pads west of x 17 (X3's four shield tabs and its GND pin 6 on
# Top, C11-1 / C12-1 / C13-1 on Bottom).  No existing GND via or GND track end lies within 1.0 mm of any of
# them (nearest: C82-1's fan-out via 1.22 mm from X3-G2, the R103/C150 fan-out vias 1.95 mm from X3-6), so
# every pad gets one NEW 0.20/0.35 via and one straight tie from the pad CENTRE (route_emit joins a track to
# an SMD pad only at its centre) to the via centre, 0.50 wide (the global Width max; every pad is >= 0.7 wide).
# Sites chosen with corr.via_sites (r_west/sites.py): the nearest legal cell that stays >= 0.125 mm from every
# pad and >= 0.125 mm from foreign copper on every layer, off the SD escape rows (X3-5/7/8 stay clear).
import os
HERE = os.path.dirname(os.path.abspath(__file__))
G = 'GND'
P = Plan()

TIES = [
    # pad      layer     pad centre           via site           why this site
    ('X3-G4', 'Top',    (14.025, 18.125),   (14.025, 17.060)),  # south: north blocked by LD3/LD4_K Top rows (y 19.1/19.4), east by the x 15.3 VCC1V0/VCC1V8 columns
    ('X3-G3', 'Top',    (5.7751, 18.475),   (6.150, 17.750)),   # south-east: L1-2 (Bottom, x <= 5.758) forbids a via straight south; 0.217 from L1-2, 0.275 from U5-4/5
    ('X3-G2', 'Top',    (6.4251, 6.5251),   (6.4251, 7.225)),   # straight south, 0.25 from R108-2 (Bottom); the C82-1 via (5.454, 5.7785) would be a 1.23 mm tie past X3-B's corner
    ('X3-G1', 'Top',    (14.025, 6.775),    (12.975, 7.100)),   # west, under the socket body: east is R104/R105 (Bottom) and the L4 VCC3V3 leg, south-east only between R105's pads
    ('X3-6',  'Top',    (14.150, 10.175),   (15.325, 10.175)),  # east on the pin's own row, between the SD-DAT0 (y 9.075) and SD-CLK (y 11.275) escape rows, 0.575 from each
    ('C13-1', 'Bottom', (1.750, 21.440),    (1.750, 22.250)),   # north: 0.135 from the pad, 0.475 from the L3 VCC1V8 run at y 23.05
    ('C11-1', 'Bottom', (4.6499, 21.390),   (4.6499, 22.150)),  # north: 0.135 from the pad; east/west are C11-2 / C13-2 (VCC3V3) at 0.6 mm
    ('C12-1', 'Bottom', (6.9498, 21.390),   (6.9498, 22.140)),  # north: 0.125 from the pad, 0.135 from the Bottom VCC3V3 run at y 22.6; south would sit 0.125 from the L4 trunk
]

for pad, layer, (px, py), (vx, vy) in TIES:
    P.via(G, vx, vy)
    P.run(G, layer, [(px, py), (vx, vy)], wish=0.5, tag=pad)

P.dump(os.path.join(HERE, 'plan.json'))
P.print_report()
print('vias %d, tracks %d' % (len(P.VIAS), len(P.TRACKS)))
