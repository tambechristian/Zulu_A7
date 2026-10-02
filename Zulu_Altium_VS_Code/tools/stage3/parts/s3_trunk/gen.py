import os as _os; PARTS = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # the parts directory (stage 3 was planned in a scratch tree; every path below is relative to it)
# -*- coding: utf-8 -*-
"""Stage 3, TRUNK, the judge's choice: the INNER TRUNK (t_innertrunk) repaired.

    python gen.py            writes plan.json and taps.json next to this file, prints the tight segments
    python gen.py --all      prints every segment

What is kept from t_innertrunk/gen.py (2026-09-21): the source row (five vias at y 20.40 north of L1-2,
Bottom bar 0.60, L4 bar 1.50), the 1.50 mm L4 spine along the empty north band at y 19.6, the pull-up via
(16.5, 19.9), the 1.50 mm L4 vertical at x 17.5 to the sdled tap (17.5, 12.45) and on to the south tap
(16.5, 6.0), every tap a via pair joined by a 0.30 stub on the tap layer.

What is repaired (the reviewers' serious findings, in order):
  R1  second Bottom riser from C80-2's pad centre to the west source via (the ring's riser B): the 745 mA
      no longer passes one 0.935 riser and one barrel (PI M1/M7 of the inner trunk).
  R2  north end per the manufacturing reviewer's gen_var2 (S2): the spine stays at y 19.6 to x 39.0, the
      north via pair hangs at (39.00, 19.0)/(39.45, 19.0) from a 1.1 stub, so U3-52/54's GND tie sites
      come back and the 1.5 mm step over x 37.4-38.3 is gone.
  R3  NO L4 east of x 39.45 (S1 of both reviewers: the 1.10 mm L4 spine at y 18.0 took every via site
      north of U1, the ties of C116/C117/C118/C120-2, U4-4 and the D14 parallel run).  The 150 mA for
      northbank / u1field / east instead climb on Top from the north pair up the free lane x 37-39.8
      (USB5V0 ends at x 36.9, Q1 starts at 39.85) to a 1.5 mm Top trunk at y 22.5 under X2's north pins
      (the outer-only trunk's NE segment, x 38.4 -> 53.2; northbank tap node (40.0, 22.5), east tap =
      the free end (53.2, 22.5)), and the u1field is fed by the outer-only trunk's east column: Top
      x 52.93 down to a via pair (52.93, 19.45)/(52.93, 19.0) and a 1.30 mm Bottom column x 52.93 with
      nodes at the 0201 rows y 17.5 (tap) / 14.45 / 11.05 / 7.65.
  R4  a north-west entry for the u1field region that never touches the AIN bundle (PI serious finding):
      Top 0.6 from the north pair down the U2/U1 gap at x 39.3 to (39.3, 15.5), then to a via at
      (40.85, 15.60) -- corr.py's only legal site there (margin 0.146; the outer-only trunk's G via) --
      inside the u1field box, 1.2 mm north of the bundle's last via (40.6, 14.05); the region crosses
      the bundle's north end at y > 14.4 on Bottom, as VCC1V0 does at y 17.3.
  R5  taps.json: 'width' is the width of the track that ENDS at the tap on the stated layer (what the
      region can extend), 'arrive_layer'/'arrive_width' the trunk's arrival; every aux via/node inside
      the box is listed under 'aux'.
  R6  (judge, resumed 2026-09-21) the u1field Bottom column is 0.70 mm on x 52.60 instead of 1.30 on x 52.93:
      it no longer floods the 0201 pads C121-1/C119-1/C122-1 (x 53.10-53.40) while their GND pads sit on a
      thin tie (tombstoning asymmetry, outer-only mfg review); the region ends a 0.30 stub inside each pad.
      Cost <= 0.3 mV at a tapering <= 95 mA.
Fab notes (from the reviews): tent every trunk via; the pairs (16.50/16.95, 6.0) sit 0.127 from R104-1 and
0.126 from VU's Top track, (39.00, 19.0) 0.225 from R83-2, (52.93, 19.0) 0.151 from C93-2 -- no teardrop room
there; every other new gap is >= 0.12 except the last south L4 leg (0.116 to the GND via 15.816, 5.55) and
riser A (0.121 to C11-1), both wider than a via land so Altium adds no teardrop.
"""
import io, json, os, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage3')
from lib import Plan, INP0

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
def opt(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default
OUT = opt('--out', os.path.join(HERE, 'plan.json'))
P = Plan()
V = 'VCC3V3'
T, B, L4 = 'Top', 'Bottom', 'L4-SIG'


def run(layer, pts, wish=1.5, tag='', clr=0.12, floor=0.09):
    P.run(V, layer, pts, wish, tag, clr, floor)


def free():
    """the last segment's far end is a tap (nothing of the net there yet)"""
    P.TRACKS[-1]['free_end'] = True


def via(x, y):
    P.via(V, x, y)


# ------------------------------------------------------------------------------------------------
# 1. SOURCE.  C80-2 / L1-2 / U5-4 are one Bottom island.  Two Bottom risers (from L1-2's and C80-2's pad
#    centres) land on the east and west vias of a row of five (0.45 pitch, y 20.40) in the strip between
#    L1-2 (top edge 19.903) and the C13/C11 cap row (20.94).  A Bottom bar joins the five (west tap), an
#    L4 bar over them starts the trunk.
# ------------------------------------------------------------------------------------------------
SRC_Y = 20.40
SRC_X = [3.433, 3.883, 4.333, 4.783, 5.233]
for x in SRC_X:
    via(x, SRC_Y)
run(B, [(5.233, 18.7535), (5.233, SRC_Y)], 1.0, 'riser A: L1-2 centre -> east via')   # route_emit anchors ends on pad CENTRES
run(B, [(3.9065, 16.6518), (SRC_X[0], SRC_Y)], 1.0, 'riser B: C80-2 centre -> west via')
run(B, [(x, SRC_Y) for x in SRC_X], 0.6, 'Bottom bar over the via row')
run(L4, [(x, SRC_Y) for x in SRC_X], 1.5, 'L4 bar over the via row')

# ------------------------------------------------------------------------------------------------
# 2. SPINE on L4 along the north band, y 19.6 (0.183 from X1's mounting holes), nodes at every branch.
# ------------------------------------------------------------------------------------------------
NORTH = [(39.00, 19.0), (39.45, 19.0)]          # north tap (via pair east of U2, west of Q1-2)
SDL_PULL = (16.50, 19.90)                        # extra sdled entry for the Bottom pull-ups (not the tap)
SDL_TAP = (17.50, 12.45)                         # sdled tap, 2.5 mm east of X3-4
SDL_TAP2 = (17.95, 12.45)
SOUTH = (16.50, 6.00)                            # south tap, west of U3-27
SOUTH2 = (16.95, 6.00)
NW_VIA = (40.85, 15.60)                          # u1field north-west entry (corr.py's only legal site)

run(L4, [(5.233, SRC_Y), (6.033, 19.6), (16.5, 19.6), (17.5, 19.6), (39.0, 19.6)], 1.5, 'spine (740 -> 310 mA)')
run(L4, [(39.0, 19.6), NORTH[0]], 1.1, 'stub to the north via pair')
run(L4, [NORTH[0], NORTH[1]], 1.05, 'north second via')
for x, y in NORTH:
    via(x, y)
run(B, NORTH, 0.3, 'north via pair (Bottom)')      # the tap is a Bottom track END at (39.0, 19.0)

# sdled: a stub up to a via for the Bottom pull-ups (sites start at y 19.73 because of the LD3_K Top lane)
run(L4, [(16.5, 19.6), SDL_PULL], 1.05, 'stub to the pull-up via')
via(*SDL_PULL)

# ------------------------------------------------------------------------------------------------
# 3. VERTICAL run down the west side of U3 (L4 is empty there) to the sdled tap and on to the south band,
#    threading between the GND vias at (15.82, 5.55) and (17.10, 6.75).
# ------------------------------------------------------------------------------------------------
run(L4, [(17.5, 19.6), SDL_TAP], 1.5, 'vertical x 17.5 to the sdled tap')
via(*SDL_TAP)
run(L4, [SDL_TAP, SDL_TAP2], 1.05, 'sdled second via')
via(*SDL_TAP2)
run(T, [SDL_TAP, SDL_TAP2], 0.3, 'sdled via pair (Top)')     # the tap is a Top track END at (17.5, 12.45)
run(L4, [SDL_TAP, (17.5, 9.5), (15.9, 7.2), SOUTH], 1.5, 'down to the south tap')
via(*SOUTH)
via(*SOUTH2)
run(B, [SOUTH, SOUTH2], 0.3, 'south via pair (Bottom)')

# ------------------------------------------------------------------------------------------------
# 4. NORTH-EAST on Top (150 mA): riser from the north pair up the free lane to y 22.5, then the 1.5 mm
#    Top trunk under X2's north pins to x 53.2 (northbank tap node 40.0, u1field branch node 52.65,
#    east tap = the free end 53.2).
# ------------------------------------------------------------------------------------------------
NY = 22.50
RX = 38.40
run(T, [NORTH[0], (RX, 19.6), (RX, NY)], 1.05, 'NE Top riser x 38.4 (150 mA; 1.05 keeps ~130 north-band sites)')
run(T, [(RX, NY), (40.0, NY), (45.3, NY), (49.9, NY), (52.65, NY)], 1.5, 'NE Top trunk y 22.5')
run(T, [(52.65, NY), (53.2, NY)], 1.5, 'NE east tap stub')
free()

# ------------------------------------------------------------------------------------------------
# 5. U1FIELD east column: Top from the trunk node down x 52.93 to a via pair (19.45 / 19.0), then the
#    1.30 mm Bottom column x 52.93 between the via lands at x 51.9-51.95 and the 0201 GND pads at x 53.85,
#    with nodes at the 0201 rows (tap at y 17.5 = the box's north edge).
# ------------------------------------------------------------------------------------------------
CX = 52.93
UV = [(CX, 19.45), (CX, 19.00)]
CCX = 52.60          # R6: column centre 52.60, 0.70 wide (edges 52.25-52.95): 0.125 from the via lands at x 51.9-51.95,
                     # 0.15 WEST of C121-1/C119-1/C122-1 (x 53.10-53.40) instead of flooding them (0201 terminal balance)
run(T, [(52.65, NY), (CX, 21.9), UV[0], UV[1]], 1.5, 'U Top branch x 52.93')
for x, y in UV:
    via(x, y)
run(B, [UV[0], UV[1], (CCX, 17.50)], 1.0, 'U Bottom from the via pair to the column head')
run(B, [(CCX, 17.50), (CCX, 14.45), (CCX, 11.05), (CCX, 7.65)], 0.7, 'U Bottom column x 52.60 (nodes at the 0201 rows)')
free()

# ------------------------------------------------------------------------------------------------
# 6. U1FIELD north-west entry: Top from the north pair down the U2/U1 gap (Q1-2 starts at 39.85, the D15
#    via land ends at 38.53) to (39.3, 15.5), east to the via (40.85, 15.60).
# ------------------------------------------------------------------------------------------------
run(T, [NORTH[0], (39.3, 18.4), (39.3, 15.5)], 0.6, 'NW Top branch x 39.3')
run(T, [(39.3, 15.5), NW_VIA], 0.8, 'NW Top to the via')
via(*NW_VIA)

# ------------------------------------------------------------------------------------------------
# taps: one per region.  'width' = the width of the plan track that ENDS at (x, y) on the stated layer
# (what the region can extend there); 'arrive_layer'/'arrive_width' = how the trunk arrives.
# ------------------------------------------------------------------------------------------------
MA = dict(west=5, sdled=230, north=160, south=200, u1field=95, northbank=35, east=20)


def w_at(layer, x, y):
    ws = [t['width'] for t in P.TRACKS if t['layer'] == layer and
          ((abs(t['x1'] - x) < 1e-6 and abs(t['y1'] - y) < 1e-6) or (abs(t['x2'] - x) < 1e-6 and abs(t['y2'] - y) < 1e-6))]
    return max(ws) if ws else None


def arrive(x, y):
    for L in (L4, T, B):          # the trunk arrives on L4 where it has L4 copper; else Top, else Bottom
        w = w_at(L, x, y)
        if w is not None:
            return (L, w)


def tap(region, layer, x, y, note, aux=(), width=None):
    w = w_at(layer, x, y)
    assert w is not None, (region, layer, x, y)
    if width is not None:
        assert width in [t['width'] for t in P.TRACKS if t['layer'] == layer and
                         ((abs(t['x1'] - x) < 1e-6 and abs(t['y1'] - y) < 1e-6) or (abs(t['x2'] - x) < 1e-6 and abs(t['y2'] - y) < 1e-6))]
        w = width          # the width of the piece the region is expected to continue (the narrower one)
    aL, aw = arrive(x, y)
    return dict(region=region, layer=layer, x=x, y=y, width=w, mA_downstream=MA[region],
                arrive_layer=aL, arrive_width=aw, aux=list(aux), note=note)


TAPS = [
    tap('west', B, SRC_X[0], SRC_Y,
        'west end of the Bottom bar over the five source vias (via centre; riser B from C80-2 also ends here; '
        'Top free above it, L4 bar 1.5 below). C13-2 / C11-2 / C12-2 / R35-2 are on Bottom 1 mm north; R34 '
        '(y 18.39) east; X2-17 is a TH pad (any layer).',
        aux=[dict(kind='via', layer='Bottom', x=x, y=SRC_Y, note='source via') for x in SRC_X[1:]]),
    tap('sdled', T, SDL_TAP[0], SDL_TAP[1],
        'via at the end of the 1.5 mm L4 vertical, 2.5 mm east of X3-4; the 0.30 Top stub to the second via '
        '(17.95,12.45) ends here. Top west to X3-4 is 0.85-0.9 wide at y 11.9-12.9 (keep the track in that band: '
        'pads 3 and 5 keep their eastward lanes); the via land is 0.32 mm from U7\'s LX pad L3-1 on Bottom, so '
        'start on Top. Bottom is free at the via too. The pull-ups R19/R96/R97/R98 and U10-8: use the trunk via '
        '(16.5,19.9) (Bottom lane y 20.3-20.5 east at 0.75); the L4 spine at y 19.6 (edges 18.85-20.35) and the '
        'x 17.5 vertical (edges 16.75-18.25) are L4 walls inside this box.',
        aux=[dict(kind='via', layer='Top/Bottom', x=17.95, y=12.45, note='second sdled via, joined on Top by the 0.30 stub'),
             dict(kind='via', layer='Bottom', x=16.5, y=19.9, note='pull-up via on a 1.05 L4 stub from the spine')]),
    tap('north', B, NORTH[0][0], NORTH[0][1],
        'via pair (39.00 / 39.45, 19.0) east of U2, west of Q1-2 (Top, x >= 39.85), between U3-54 (y <= 18.13) and '
        'R85-2 (y >= 19.8); the 0.30 Bottom stub between the vias ends here. Bottom: west along y 18.22-18.51 '
        'under R80/R81/R82 to U3-43/U3-49 (0.29 strip; route_width reaches U3-49 at 0.495). Top: the trunk itself '
        'leaves (39.0,19.0) north (riser x 38.4, 1.5) and south (branch x 39.3, 0.6, to the u1field via 40.85,15.6): '
        'U2-42 (37.175,14.35) is 0.2-0.28 west of that branch at y 14.2-14.5 through the D10/D11/UDQM Top lane; '
        'U2-50/56 through U2\'s body on Top (no exposed pad) or from a region via at ~(35.7,19.9) with a 0.1 Top '
        'track along y 20.3 (route_width: U2-50 0.538). The y 20.1-20.5 slot north of U2\'s pins is the USB pair\'s '
        'lane (keep >= 0.45). Tie the tap to C100-1 (40.35,21.1) early: the only VCC3V3 capacitor within 5 mm.',
        aux=[dict(kind='via', layer='Top/Bottom', x=39.45, y=19.0, note='second north via'),
             dict(kind='node', layer='Top', x=38.4, y=19.6, note='riser node'),
             dict(kind='node', layer='Top', x=39.3, y=18.4, note='NW branch node')]),
    tap('south', B, SOUTH[0], SOUTH[1],
        'via at the end of the L4 run, west of U3-27, 0.3 mm north of VU (Top); the 0.30 Bottom stub to the second '
        'via (16.95,6.0) ends here. Bottom exit 0.45-0.49 at the via (R104-1 at 0.15, VU\'s Top edge 0.13), then the '
        'Bottom lane east at y ~5.1 (0.69 max past R18 at x 19.7-21.7) and the free band y 4.19-5.48 under U3\'s '
        'south pads from x 22 to 39; Top lane y 5.8-7.1 north of VU. The 0201 row y 3.95 and the FT channel '
        'y 2.03-2.6 are south of the beads. U2-20/31 remain reachable at 0.163 / 0.538 (board values).',
        aux=[dict(kind='via', layer='Top/Bottom', x=16.95, y=6.0, note='second south via')]),
    tap('u1field', B, CCX, 17.50,
        'head of the 0.70 mm Bottom column x 52.60 (edges 52.25-52.95: 0.125 east of the via lands at x 51.9-51.95, '
        '0.15 WEST of the 0201 pads C121-1/C119-1/C122-1 at x 53.10-53.40; their GND pads -2 at 53.85 keep the east side '
        'for their ties) on the box north edge; the 1.0 mm Bottom piece from the via pair (52.93,19.0) also ends here. '
        'More nodes at y 14.45, 11.05 and the free end 7.65 (the 0201 rows): from each node end a 0.30 stub INSIDE the pad '
        'at x 53.25 (0.15 gap). '
        'Enter the land field from the east below VCC1V0\'s flank (y < 10.25) or along the south strip y 6.2-7.1 '
        '(0.90) to the y 6.9 via row. SECOND ENTRY: the via (40.85,15.60) (Bottom free end, Top-fed) 1.2 mm north '
        'of the AIN bundle\'s last via: cross the bundle\'s north end on Bottom at y ~14.9 between the GND vias '
        '(41.4,14.4)/(41.4,15.4) (<= 0.47) to C112-1 (42.15,14.45) and H3\'s via (43.4,13.4), then the lattice '
        'interior at 0.21-0.47; do NOT run down x 42.15 beside the bundle (x 39.9-41.9, y 4.3-14.4).',
        aux=[dict(kind='via', layer='Top/Bottom', x=NW_VIA[0], y=NW_VIA[1], note='NW entry via (Bottom free); Top 0.8 track from (39.3,15.5)'),
             dict(kind='via', layer='Top/Bottom', x=CX, y=19.0, note='column via (northbank box)'),
             dict(kind='via', layer='Top/Bottom', x=CX, y=19.45, note='column via (northbank box)'),
             dict(kind='node', layer='Bottom', x=CCX, y=14.45, note='column node'),
             dict(kind='node', layer='Bottom', x=CCX, y=11.05, note='column node'),
             dict(kind='node', layer='Bottom', x=CCX, y=7.65, note='column free end')],
        width=0.7),
    tap('northbank', T, 40.0, NY,
        'node of the 1.5 mm Top trunk y 22.5 (edges 21.75-23.25; X2\'s north pins above 23.37, U4-1/U4-8 and Q1-1/Q1-4 '
        'below 21.59); more nodes at x 45.3, 49.9, 52.65 and the riser node (38.4,22.5). Bottom is open under the '
        'trunk: vias to the 0603 bank fit between X2\'s pins (e.g. x 40.64 or 43.2, y 23.1-23.5) and in the U4 body '
        'area; Q1-1/Q1-4 are TH (all layers) 0.2 mm below the trunk. The 0201 row y 17.85 (C120/C117/C116/C118-1) '
        'is cut into cells by VCC1V0\'s Bottom columns x 44.3 / 47.4: a via per cell (e.g. (45.5,18.2), (48.05,18.2)) '
        'fed on Top through U4\'s body from the trunk. L4 north of U1 is EMPTY (y 17.4-20.4): leave it and the via '
        'sites at y 17.4-18.8 to the GND ties of C116/C117/C118/C120-2 and U4-4.',
        aux=[dict(kind='node', layer='Top', x=45.3, y=NY), dict(kind='node', layer='Top', x=49.9, y=NY),
             dict(kind='node', layer='Top', x=52.65, y=NY, note='u1field branch node'),
             dict(kind='node', layer='Top', x=RX, y=NY, note='riser node')]),
    tap('east', T, 53.2, NY,
        'free end of the 1.5 mm Top trunk y 22.5; Top open east to x 58 at y 21.7-23.2, Bottom open below (C99/C104 '
        'own pads). The 1206s C97/C98/C145/C146 (Top, x 53-56.6) down the east side; the u1field column x 52.93 '
        '(Bottom, nodes y 17.5/14.45/11.05/7.65) is trunk copper in this box too and feeds R20/R23/R1 and JP4-3 '
        'from its free end (52.60,7.65) or from C122-1 (the column is 0.70 on x 52.60).',
        aux=[dict(kind='node', layer='Bottom', x=CCX, y=7.65, note='u1field column free end')]),
]

if __name__ == '__main__':
    P.dump(OUT)
    io.open(os.path.join(HERE, 'taps.json'), 'w', encoding='utf-8', newline='\n').write(json.dumps(TAPS, indent=1))
    P.print_report(only_tight='--all' not in ARGS)
    print('%d vias, %d tracks' % (len(P.VIAS), len(P.TRACKS)))
    for t in TAPS:
        print('tap %-9s %-6s (%.3f, %.3f) w %.3f (arrives %s %.3f) %d mA' % (
            t['region'], t['layer'], t['x'], t['y'], t['width'], t['arrive_layer'], t['arrive_width'], t['mA_downstream']))
