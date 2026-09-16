# -*- coding: utf-8 -*-
"""Zulu A7 stage 1 -- the charger's eight nets: VU, USB5V0, VBATT and the five LED nets.

Writes tools/stage1_route.json.  Chosen by a judge from three strategies (south / north / wide), each
attacked by a power-EMI and a manufacturing reviewer; this is "south" with the repairs below.
Record: docs/stage1_feeds.md.  Additions only; no `remove` key, and no new track shares a net+layer+
endpoint pair with an existing one (so Remove<Block> can never catch committed copper).

WHAT CHANGED FROM s1_south, and why
-----------------------------------
FATAL (manufacturing review, reproduced by the judge with tools/route_width.py):
  FT-VCORE C139-2 -> U2-12 went 0.538 mm -> UNREACHABLE.  C139-2's only escape is the
  0.568 mm Bottom channel between the X2 south header (pads top out at 2.032) and the
  0603 cap row (bottom 2.600), and s1_south filled it with VBATT while VU's 1.50 mm Top
  trunk at y 2.916 made every via centre in it illegal.  The arithmetic is closed:
  0.09 + w_VBATT + 0.09 + 0.15 + 0.09 <= 0.568 needs w_VBATT <= 0.148, below VBATT's own
  0.20 mm Bottom minimum, so no width fixes it -- VBATT has to leave the channel.
  It cannot hop the window either: a 0.35 mm land in that channel blocks y 2.051..2.581
  on Top AND Bottom, i.e. the whole channel.

  The fix is a swap.  VU moves NORTH into the empty Top band (x 16..27 carries no Top
  copper at all up to the SDRAM escape via row at y 6.975) and VBATT takes VU's old place
  on Top just above the header.  The Bottom channel is then completely free -- better than
  the board this stage started from for FT-VCORE, FT-VPHY and the CHAN20..26 escapes --
  and VBATT reaches X4-1 from the south-west on Top with NO via inside the connector
  footprint.  Total vias are unchanged at 9.

  Why a swap and not a detour: VBATT ends INSIDE the X4 obstacle and VU has to get past it,
  so whichever of the two is north has to cross the other, and the only Top ways past X4
  are the two 1.1 mm slots between X4-1/X4-2 and the MP anchors.  With VU north the
  crossing disappears: VU dips under X4-MP1 (bottom 3.800) and climbs the x 29.8..30.9
  slot, VBATT passes below it at y 1.55 and walks straight into X4-1's pad.

SERIOUS (power/EMI review) -- every clearance complaint answered by narrowing, not re-routing:
  X4: the fly-over is 0.70 mm, not 0.86, so the gaps to X4-1 (the live cell terminal),
      X4-2 (GND), MP1 and MP2 are 0.200 mm instead of 0.120 mm.
  XADC: VU's east trunk is 1.20 (was 1.35) and its neck under the AIN16_N Top link is 0.60
      (was 0.75).  AIN16_N's layer-change via goes 0.120 -> 0.195 mm, AIN15_P's 0.150 ->
      0.225 mm, and X2-26..29 improve at the same time.
  VBUS near the SDRAM: the two Top runs past the D12/D13 escape vias are 0.45 and 0.50
      (were 0.62 and 0.66): D12 0.126 -> 0.210 mm, D13 0.135 -> 0.215 mm.
  X1: the approach lane moves to the centre of the 1.025 mm MH2/MP corridor (y 22.500) and
      the drop into X1-1 is 0.40 to match the pad: X1-MH2 0.141 -> 0.242, X1-2 0.225 -> 0.250.
  X2 header pins: VU no longer runs anywhere near X2-30..36 (it is 1.3 mm further north),
      and VBATT keeps 0.168 mm to every one of them instead of 0.1225.

SERIOUS (manufacturing) -- the rest:
  The NetLD4_A via leaves R108's body: (6.500,5.800) sat 0.125 mm from BOTH of R108's
      terminations with VU on the far one; it is now at (7.200,5.800), clear of R108 and
      R107, so it can be teardropped.
  The C150-2 copper sliver is gone: the USB5V0 corner moves 0.15 mm east.
  No plan via sits inside X4's or X1's footprint any more.

LAYOUT
------
  VU      one layer change (a via pair on the block's own 1.00 mm Bottom track at y 11.0),
          Top the rest of the way.  Down the empty column at x 12.155 between the LED
          columns (right edge 11.505) and the GND via at (12.980,8.600); east at y 4.9493,
          threading the 0.8515 mm window between the GND vias at (15.8165,4.3485) and
          (15.8165,5.5500) at 0.55 mm and running 1.50 mm either side; down to y 3.15 to
          pass under X4-MP1; up the x 30.35 slot at 0.70; over X4-1 and X4-2 in the band
          between X4 (top 5.800) and U2's bottom pad row (7.125); down the x 34.45 slot;
          then east at 1.20 under the SDRAM escapes, 0.60 under the AIN16_N Top link, and
          1.50 into X2-22.
  VBATT   a via pair in the X2-36/X2-35 pin gap, then Top at y 2.50-2.60 the whole way,
          0.168 mm clear of every header pin, under VU's descent, and into X4-1's pad.
  USB5V0  Bottom across U3's belly, a via pair in the one window clear of the SDRAM bus on
          L3/L4, Top out through U2's inside and into X1-1 from the EAST.  No VBUS copper
          enters the X1 -> U2 differential lane.
  LEDs    Top, five stacked columns in the channel between the X3 keep-out (right edge
          9.275) and X3's pads (left edge 13.275).
"""
import io, json, os

T, B = 'Top', 'Bottom'
LW = 0.10          # LED nets: twice the 0.0762 mm global minimum, well under the 0.50 maximum

VIAS = [
    # net, x, y
    ('VU', 12.0000, 11.0000), ('VU', 12.4400, 11.0000),          # on the block's own 1.00 mm track
    ('VBATT', 12.7000, 2.3000), ('VBATT', 12.7000, 1.8600),      # in the X2-36 / X2-35 pin gap
    ('USB5V0', 32.1000, 11.0000), ('USB5V0', 32.1000, 13.2000),  # the one window clear of the SDRAM bus
    ('NetLD4_A', 7.2000, 5.8000),
    ('NetLD3_A', 8.3000, 4.4000),
    ('LD5_K', 8.3000, 3.6000),
]

# (net, layer, [(x, y), ...], width or [widths])
RUNS = [
    # ---------------- VU : ONE layer change, then Top all the way east
    ('VU', B, [(11.4998, 10.0500), (12.0000, 11.0000), (12.4400, 11.0000)], [0.60, 0.60]),
    ('VU', T, [(12.0000, 11.0000), (12.1550, 11.0000)], 0.40),
    ('VU', T, [(12.1550, 11.0000), (12.4400, 11.0000)], 0.40),
    ('VU', T, [(12.1550, 11.0000), (12.1550, 5.6000)], 1.00),      # LED columns / GND via 12.980,8.600
    ('VU', T, [(12.1550, 5.6000), (13.2000, 4.9493)], 1.00),
    ('VU', T, [(13.2000, 4.9493), (14.9600, 4.9493)], 1.50),
    ('VU', T, [(14.9600, 4.9493), (15.2900, 4.9493)], 1.00),       # stepped taper: every step stands
    ('VU', T, [(15.2900, 4.9493), (15.5800, 4.9493)], 0.70),       # 0.12 mm off the GND vias at
    ('VU', T, [(15.5800, 4.9493), (16.0600, 4.9493)], 0.55),       # (15.8165,4.3485) and (15.8165,5.5500),
    ('VU', T, [(16.0600, 4.9493), (16.3500, 4.9493)], 0.70),       # so only 0.48 mm is at 0.55 instead
    ('VU', T, [(16.3500, 4.9493), (16.6900, 4.9493)], 1.00),       # of 2.03 mm -- 0.85 mohm
    ('VU', T, [(16.6900, 4.9493), (25.6000, 4.9493)], 1.50),       # the empty north Top band
    ('VU', T, [(25.6000, 4.9493), (27.3000, 4.1000)], 1.40),
    ('VU', T, [(27.3000, 4.1000), (27.6000, 3.3000)], 0.70),
    ('VU', T, [(27.6000, 3.3000), (30.3500, 3.3000)], 0.70),       # under X4-MP1 (bottom 3.800)
    ('VU', T, [(30.3500, 3.3000), (30.3500, 6.4000)], 0.70),       # up between X4-MP1 and X4-1
    ('VU', T, [(30.3500, 6.4000), (34.4500, 6.4000)], 0.70),       # X4 (5.800) / U2 bottom row (7.125)
    ('VU', T, [(34.4500, 6.4000), (34.4500, 3.3660)], 0.70),       # down between X4-2 and X4-MP2
    ('VU', T, [(34.4500, 3.3660), (34.9000, 2.8500)], 0.70),
    ('VU', T, [(34.9000, 2.8500), (42.2000, 2.8500)], 1.20),
    ('VU', T, [(42.2000, 2.8500), (42.7000, 2.5300)], 0.60),
    ('VU', T, [(42.7000, 2.5300), (46.9000, 2.5300)], 0.60),       # under the AIN16_N Top link
    ('VU', T, [(46.9000, 2.5300), (47.6000, 3.2000)], 0.60),   # 0.198 mm off TH X2-26 (CHAN16)
    ('VU', T, [(47.6000, 3.2000), (48.2000, 3.6000)], 1.20),
    ('VU', T, [(48.2000, 3.6000), (56.0000, 3.6000)], 1.50),
    ('VU', T, [(56.0000, 3.6000), (57.1500, 1.2700)], 1.50),       # X2-22 centre

    # ---------------- VBATT : out of the block, up in the X2-36/X2-35 gap, Top east into X4-1
    ('VBATT', B, [(11.5000, 3.3980), (12.0000, 2.4400), (12.7000, 2.3000)], [0.40, 0.40]),
    ('VBATT', B, [(12.7000, 2.3000), (12.7000, 1.8600)], 0.40),
    ('VBATT', T, [(12.7000, 2.3000), (12.7000, 1.8600)], 0.40),
    ('VBATT', T, [(12.7000, 2.3000), (13.3000, 2.5000)], 0.40),
    ('VBATT', T, [(13.3000, 2.5000), (15.1000, 2.5000)], 0.60),    # under the GND via at 14.6665,3.147
    ('VBATT', T, [(15.1000, 2.5000), (15.7000, 3.0000)], 0.60),
    ('VBATT', T, [(15.7000, 3.0000), (25.5000, 3.0000)], 0.80),    # 0.568 mm clear of every X2 pin,
                                                                   # and it leaves the Bottom channel
                                                                   # its own legal via slots
    ('VBATT', T, [(25.5000, 3.0000), (26.5000, 2.5000)], 0.60),
    ('VBATT', T, [(26.5000, 2.5000), (27.7000, 2.5000)], 0.60),
    ('VBATT', T, [(27.7000, 2.5000), (28.4500, 1.5500)], 0.60),    # east of X2-30, under VU's descent
    ('VBATT', T, [(28.4500, 1.5500), (30.9500, 1.5500)], 1.20),
    ('VBATT', T, [(30.9500, 1.5500), (31.4000, 3.0500)], 0.80),    # X4-1 centre

    # ---------------- USB5V0 : Bottom across U3's belly, Top out of U2's corner, X1-1 from the EAST
    ('USB5V0', B, [(14.0020, 7.0000), (14.7500, 7.8000)], 0.45),
    ('USB5V0', B, [(14.7500, 7.8000), (16.9000, 7.8000)], 0.45),
    ('USB5V0', B, [(16.9000, 7.8000), (18.8000, 9.2000)], 0.45),
    ('USB5V0', B, [(18.8000, 9.2000), (32.1000, 11.0000)], 1.00),  # U3's belly is 10 mm tall
    ('USB5V0', B, [(32.1000, 11.0000), (32.1000, 13.2000)], 0.70),
    ('USB5V0', T, [(32.1000, 11.0000), (32.1000, 13.2000)], 0.70),
    ('USB5V0', T, [(32.1000, 13.2000), (34.8000, 16.6500)], 0.45), # between the D12 and D13 vias
    ('USB5V0', T, [(34.8000, 16.6500), (35.9000, 18.0000)], 0.50),
    ('USB5V0', T, [(35.9000, 18.0000), (36.6800, 20.0000)], 0.45), # U2's north-east corner
    ('USB5V0', T, [(36.6800, 20.0000), (36.6800, 22.5000)], 0.45), # east of the X1-MH2 mount
    ('USB5V0', T, [(36.6800, 22.5000), (34.3200, 22.5000)], 0.55), # centre of the MH2 / MP corridor
    ('USB5V0', T, [(34.3200, 22.5000), (34.3200, 21.2590)], 0.40), # X1-1 centre, pad width

    # ---------------- NetLD3_K : via (9.100,6.100) -> LD3-K.  column 10.575, lane 19.40
    ('NetLD3_K', T, [(9.1000, 6.1000), (9.6000, 6.6000)], 0.15),
    ('NetLD3_K', T, [(9.6000, 6.6000), (9.9000, 7.0000)], LW),
    ('NetLD3_K', T, [(9.9000, 7.0000), (9.9000, 8.1000)], LW),
    ('NetLD3_K', T, [(9.9000, 8.1000), (10.5750, 8.1000)], LW),
    ('NetLD3_K', T, [(10.5750, 8.1000), (10.5750, 19.4000)], LW),
    ('NetLD3_K', T, [(10.5750, 19.4000), (24.8000, 19.4000)], LW), # above X3-G4
    ('NetLD3_K', T, [(24.8000, 19.4000), (24.8000, 16.1850)], LW), # LED column / U2 left column
    ('NetLD3_K', T, [(24.8000, 16.1850), (24.1500, 16.1850)], LW), # LD3-K centre

    # ---------------- NetLD4_K : via (10.250,7.350) -> LD4-K.  columns 10.795 / 11.420, lane 19.10
    ('NetLD4_K', T, [(10.2500, 7.3500), (10.7950, 7.7000)], LW),
    ('NetLD4_K', T, [(10.7950, 7.7000), (10.7950, 14.9000)], LW),
    ('NetLD4_K', T, [(10.7950, 14.9000), (11.4200, 15.1500)], LW), # round the GND via 11.050,15.541
    ('NetLD4_K', T, [(11.4200, 15.1500), (11.4200, 19.1000)], LW),
    ('NetLD4_K', T, [(11.4200, 19.1000), (24.1500, 19.1000)], LW),
    ('NetLD4_K', T, [(24.1500, 19.1000), (24.1500, 17.3850)], LW), # LD4-K centre

    # ---------------- NetLD4_A : R108-1 -> LD4-A.  via clear of R108's body; columns 11.015 / 11.700
    ('NetLD4_A', B, [(6.5000, 5.1500), (6.8000, 5.5000)], 0.20),
    ('NetLD4_A', B, [(6.8000, 5.5000), (7.2000, 5.8000)], 0.20),
    ('NetLD4_A', T, [(7.2000, 5.8000), (7.6000, 5.6000)], 0.15),
    ('NetLD4_A', T, [(7.6000, 5.6000), (11.0150, 5.6000)], LW),
    ('NetLD4_A', T, [(11.0150, 5.6000), (11.0150, 14.3000)], LW),
    ('NetLD4_A', T, [(11.0150, 14.3000), (11.7000, 14.5000)], LW),
    ('NetLD4_A', T, [(11.7000, 14.5000), (11.7000, 16.7000)], LW),
    ('NetLD4_A', T, [(11.7000, 16.7000), (15.6000, 16.7000)], LW), # X3-1 (16.025) / X3-G4 (17.375)
    ('NetLD4_A', T, [(15.6000, 16.7000), (15.6000, 17.3850)], LW),
    ('NetLD4_A', T, [(15.6000, 17.3850), (22.5500, 17.3850)], LW), # LD4-A centre

    # ---------------- NetLD3_A : R107-1 -> LD3-A.  column 11.235, lane 14.065
    ('NetLD3_A', B, [(7.8500, 5.1500), (8.3000, 4.4000)], 0.20),
    ('NetLD3_A', T, [(8.3000, 4.4000), (8.6000, 4.1500)], 0.15),
    ('NetLD3_A', T, [(8.6000, 4.1500), (11.2350, 4.1500)], LW),
    ('NetLD3_A', T, [(11.2350, 4.1500), (11.2350, 14.0650)], LW),
    ('NetLD3_A', T, [(11.2350, 14.0650), (15.3000, 14.0650)], 0.0762), # X3-3 (13.825) / X3-2 (14.225)
    ('NetLD3_A', T, [(15.3000, 14.0650), (15.3000, 15.8000)], LW),
    ('NetLD3_A', T, [(15.3000, 15.8000), (21.9000, 15.8000)], LW), # under the A-bus via row
    ('NetLD3_A', T, [(21.9000, 15.8000), (22.5500, 16.1850)], LW), # LD3-A centre

    # ---------------- LD5_K : R78-2 -> LD5-K.  column 11.455, lane 11.825
    ('LD5_K', B, [(7.5000, 3.9000), (8.3000, 3.6000)], 0.20),
    ('LD5_K', T, [(8.3000, 3.6000), (8.6000, 3.4250)], 0.15),
    ('LD5_K', T, [(8.6000, 3.4250), (11.4550, 3.4250)], 0.0762),   # between the GND vias at 8.920
    ('LD5_K', T, [(11.4550, 3.4250), (11.4550, 11.8250)], LW),
    ('LD5_K', T, [(11.4550, 11.8250), (21.8000, 11.8250)], LW),    # X3-5 (11.625) / X3-4 (12.025)
    ('LD5_K', T, [(21.8000, 11.8250), (22.3000, 11.9725)], 0.0762),
    ('LD5_K', T, [(22.3000, 11.9725), (23.3500, 11.9725)], 0.0762),# between LD0-2 and LD1-A
    ('LD5_K', T, [(23.3500, 11.9725), (23.3500, 14.9850)], LW),    # the LED anode/cathode gap
    ('LD5_K', T, [(23.3500, 14.9850), (24.1500, 14.9850)], LW),    # LD5-K centre
]

tracks, vias = [], []

for net, x, y in VIAS:
    vias.append(dict(net=net, x=round(x, 4), y=round(y, 4)))

for net, layer, pts, w in RUNS:
    ws = w if isinstance(w, (list, tuple)) else [w] * (len(pts) - 1)
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        tracks.append(dict(net=net, layer=layer, x1=round(x1, 4), y1=round(y1, 4),
                           x2=round(x2, 4), y2=round(y2, 4), width=round(ws[i], 4)))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stage1_route.json')
json.dump(dict(vias=vias, tracks=tracks), io.open(out, 'w', encoding='utf-8'), indent=1)
print('%d vias, %d tracks -> %s' % (len(vias), len(tracks), out))
