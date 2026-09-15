# U1 fan-out — XC7A35T CPG236, placed 2026-09-15

**Status: PLACED, DRC-CLEAN ON EVERY GEOMETRIC RULE, SAVED.** 107 vias and 318 tracks, generated
from `tools/fanout_plan.json` by `tools/fanout_emit.py` into `PlaceFanout` (`tools/ZuluSetup.pas`)
and placed by script. `RemoveFanout` takes it all out again while the fan-out is the only routed
copper on the board.

## How it was designed

Inputs from the files only: `tools/fanout_inputs.py` reads the PcbDoc and writes
`tools/fanout_inputs.json` — the 238 lands with nets, the 123 vacant lattice cells (15 blocked for
a 0.35 mm via by the Bottom-side 0201s under the die), every U1 net's destinations, the rules as
saved, the neighbours. Three planners (moat / exits / power) wrote solvers against it; one died on
output length; a geometric refuter checked each surviving plan with its own code; a judge merged
them into `tools/fanout_plan.py` (re-runnable, with a `--selftest` that plants nine fault kinds)
and iterated to zero findings. Four independent checkers agree on the merged plan to 0.1 µm:
the judge's, both refuters', and the repo's own gate `tools/fanout_emit.py`.

Tightest real margins: via to foreign land **0.1673 mm**, via to a foreign Bottom 0201 pad
0.1223 (L19 via vs C111-1), via-via 0.4999 (adjacent cells), Top track to foreign land **0.0993**
(the 3 mil gap passages, 57 of them), track to a foreign via 0.1000, track-track 0.1118.

## What was placed

| part of the array | balls | what happens |
|---|---|---|
| ring 0 | 72 (68 netted) | `direct` — nothing placed; they leave on Top at their row/column line |
| ring 1 | 64 | 47 signal balls get a 3 mil Top stub through a named ring-0 gap, ending 0.10 mm outside the land field (`gap`); power/GND balls chain or take an outside via |
| ring 2 | 56 | `dogbone-in` to a moat via — 48 ring-3 cells, three blocked ring-3 cells (E16 L16 M16) used as Top pass-throughs to ring-4, four outward escapes (C17 N, U3 W, U16 S, U17 E) |
| moat rings 3–5 | 120 cells | 77 used: ring-2 vias, core-edge vias in ring 5, GND stitches N6/L14 for the under-die caps |
| core 7×7 | 46 (all GND/power) | 20 chained ball-to-ball at 0.20, 26 via-adjacent; K9 GND, K10 VCC1V0, K11 GND at the centre |

Vias by net: GND 40, VCC3V3 21, VCC1V8 5, VCC1V0 4, GNDADC 1 (D11, an island — never joined to
GND), VCCADC 1, FPGA-TCK 1, FPGA-CCLK 1. Tracks: 295 Top, 21 Bottom (0201 pad stubs and the VCC1V0
trunk under the die), 2 on L3-SIG (the E5 VCC1V8 feed). Widths: 136 × 0.0762, 37 × 0.15, 145 × 0.20.

**VCC3V3 necks to 3 mil in exactly three places** — V6, V9, V11 through the W5|W6, W8|W9, W10|W11
gaps to vias at y 6.90; C18 turned out not to need one (B19 is VCC3V3 on the diagonal and a 0.20
diagonal clears B18/C19 by 0.141). Every under-die 0201 (C89–C92, C95, C96) has its GND and rail
pad served by a via within 0.7 mm.

## Decisions, each with its number

- MOAT ASSIGNMENT = the moat plan: 56 ring-2 balls over 48 ring-3 cells, E16/L16/M16 (blocked) used as Top pass-throughs to ring-4 F15/K15/N15, NW GND sharing D4 (C3 C4 D3), D5 (C5), D6 (C6+C7), E4 (E3+F3) saves 4 cells, row C shifted one cell west and col 3 one cell north as diagonals (0.15 wide next to a foreign via: 0.354-0.175-0.075 = 0.104), four outward escapes C17 north (via 50.15,16.78), U3 west (41.40,8.65), U16 south (49.65,7.02), U17 east (51.40,8.15). CHANGE vs moat: U17 leaves east, not T17, because T19 (GND, no same-net neighbour) needs the row-line via and between two outside vias 0.75 mm apart at the same x the window is 0.75-0.53 = 0.22 mm = one 3 mil track, while the T|U lane plus the U19 exit are two; T17 -> T16 straight, T19's via staggered to (51.90, 8.90), 0.90 from the JA10 via.
- CORE CHAINS = the moat plan: 46 core balls, 20 chained ball-to-ball at 0.20 and 26 via-adjacent; ring-5 vias facing every edge ball (F6 F7 F8 F9 F10 F11 F12 F13, G6 H6 J6 K6, P6 P7 P8 P9 P10 P11 P12 P13 P14, G14 H14 J14 K14 N14), centre K9 (GND) K10 (VCC1V0) K11 (GND), plus GND stitches N6 and L14 for C90-2/C91-2. Adjacent-cell via pairs are 0.4999 apart (>= 0.44).
- GND VIA COUNT 40 + 1 GNDADC (D11, an isolated island for A12 A13 B12 B13 C12): 24 in rings 2-5/core (moat), 16 outside for rings-0/1 GND balls with no same-net neighbour or path (A1 B1 C1 E1 F1 G1 W1 W12 A19 C19 F19 L19 T19, H18/P2/V18 necks). Count is set by isolated balls and decoupling loops (every under-die 0201 GND pad has a GND via within 0.7 mm with its stub placed), not by current (~1 nH / ~1.5 mohm per via).
- PLANECONNECT: Direct for vias (new rule scope IsVia, style Direct, priority above the existing Relief rule; keep Relief for through-hole pads). Numbers: moat-band copper 24.8% (relief) vs 42.8% (direct); copper crossing into the core 1.05 mm vs 7.50 mm per plane. Secondary lever: PlaneClearance 0.25 -> 0.20 widens each ring-3 bridge from 0.30 to 0.40 mm.
- VCC3V3 NECKS: only three 3 mil necks, V6 (W5|W6, via 44.15,6.90), V9 (W8|W9, 45.65,6.90), V11 (W10|W11, 46.65,6.90). C18 is not a neck: B19 is VCC3V3 on the diagonal and a 0.20 diagonal clears B18/C19 by 0.354-0.1125-0.10 = 0.141. M17 -> M16 -> N15 runs 0.15 (0.104 to the N16 via). Ring 0: K1 (40.90,11.90), R1 (40.40,9.40), V1 (40.90,7.90), B19 (51.40,15.90), all 0.20.
- RING-1 GAP ASSIGNMENT (solved by the ledger, stubs PLACED for the 47 ring-1 signal balls: 3 mil, 45 deg to the interstitial, through the named gap, ending 0.10 outside the land-field box): east D18 C|D, E18 D|E, F18 E|F, G18 F|G, H18 G|H (GND neck to 51.90,13.15), J18 H|J, K18 J|K, L18 K|L, M18 L|M, N18 M|N, P18 N|P, R18 P|R, T18 R|T, U18 T|U, U17 U|V (lane), V|W spare, B18 north through A18|A19; west G2 F|G, H2 G|H, J2 H|J, K2 J|K, L2 K|L, M2 L|M, N2 M|N, P2 N|P (GND neck to 40.90,10.15), R2 P|R, T2 R|T, U3 T|U (lane), U2 U|V, V2 V|W; south V3 2|3, V4 3|4, V5 4|5, V6 5|6, V7 6|7, V8 7|8, V9 8|9, V10 9|10, V11 10|11, V12 11|12, V13 12|13, V14 13|14, V15 14|15, V16 15|16, U16 16|17 (lane), V17 17|18, V18 18|19 (GND neck to 50.65,6.35); north B14 A13|A14 (GND thread along the corridor floor into A11), B15 14|15, B16 15|16, B17 16|17, C17 17|18 (lane), B18 18|19. W19 exits east at its row line.
- OUTSIDE-ARRAY VIAS: placed now ONLY where the ball has no in-array option and the land field fixes the position: rings-0/1 power balls without a same-net neighbour, the six boxed ring-1 necks, and the four ring-2 escapes (a ring-2 via must lie within 1.6 mm for tools/fanout_emit.py). All ring-0/1 SIGNAL vias are left to routing (their position depends on the route direction); the ledger proves each keeps a slot. 27 outside vias, staggered so no two 0.75 mm apart share an outward zone: west x = 41.4 (GND A B C E F, A10 lane, W1 corner) / 40.9 (G1, K1, V1, P2 neck) / 40.4 (R1); east x = 51.4 (A19 C19 F19 L19, B19, JA10) / 51.9 (T19, H18 neck); south y = 6.9 (V6 V9 V11) / 6.25 (W12) / 6.35 (V18) / 7.02 (CHAN17).
- A19 keeps a ROW-LINE via (51.40,16.40), not a corner via: U4 is a wide SOIC-8 with pad copper only at x 43.10..44.60 and 50.40..51.905 (south edge 17.215), so A18 (x 50.4) runs into U4 pad 5 and must go east above A19 at y >= 16.641; a corner via at (51.4,16.9) would box it. A18 and B18 use two corridor tracks (16.65 / 16.82, bumping to 16.70 / 16.87 past the A19 via) and then the 0.445 mm channel between U4 pad 5 and C93, which holds exactly two 3 mil tracks. A14..A17 and the B15..B17 lanes run straight north under U4's body.
- G1 (GND) gets its own via at (40.90,13.40): a G1-F1 chain would sit in the F|G gap that G2 (AIN15_N) needs (the west side has 13 gaps F|G..V|W for 11 col-2 signals + the P2 neck + the U3 lane: zero slack) and a G1 -> F2 diagonal would cross G2's stub at the (42.15,13.65) interstitial.
- V18 necks SOUTH (W18|W19 gap, via 50.65,6.35, zone-disjoint from the CHAN17 via at y 7.02) instead of east: the power plan's east via at (51.4,7.15) was 0.025 mm from C115 pad 2 and killed W19's east exit.
- UNDER-DIE CAPS all served: GND C96-2<-F7, C92-2<-F11, C95-2<-F15, C90-2<-N6, C91-2<-L14, C89-2<-P12 (a K11 stub would cut the VCC1V0 trunk off C91-1); VCC1V0 C92-1<-F10, C89-1<-K10, and a Bottom trunk from C89-1 at y 11.45 (0.175 over the pad tops, 0.20 to the K-row via lands) to C90-1 and via a 45 deg drop to y 11.05 past the L14 via at 0.10 into C91-1; VCC1V8 C95-1<-G14 (through empty F14), C96-1 <- NEW via at ring-4 E5 (0.145 from the pad) fed D8 -> E8 -> E5 on L3 at 0.15 (0.25 to the D-row and F-row vias). Ring-0/1 caps C107-C115 left to routing (their ties cross the T/D-row Bottom escape corridors).
- Diagonal widths by number: between two foreign balls 0.354-0.1125-w/2 -> 0.141 at 0.20 (B9/B11 -> C10, C18 -> B19); beside a foreign via 0.354-0.175-w/2 -> 0.104 at 0.15, 0.079 at 0.20 (fails), so every power diagonal that flanks a via is 0.15; signals 3 mil.

## Plane connection

`PlaneConnect_Vias` — scope `IsVia`, **Direct** — was added at plane-connect priority 1 above the
global Relief rule before the first DRC (set in the Rules dialog: the connect-style property has
no proven script name). The judge's 10 µm raster of one GND plane over the moat band (rings 3–5,
30.0 mm², 40 GND vias, 67 non-GND 0.70 mm anti-pads): copper left **24.8 % with Relief vs 42.8 %
with Direct**; connected copper crossing into the core 1.05 mm vs 7.50 mm per plane. Both
refuters' rasters bracket it (25/48 and 23/43). Tented, never-soldered vias have no thermal
reason for reliefs. `tools/ZuluRules.pas` `ApplyPlaneConnect` is guarded to the global rule.

## DRC after placement — `docs/drc_fanout_2026-09-15.drc`

603 violations, Warnings 0: **Un-Routed 499** (down from 603 — the chains and dog-bones completed
104 connections), the 2 waived X2-20 starved thermals, and **102 Net Antennae** — all of them the
work in progress by construction: 40 are the ring-1 stubs' free ends (every one 0.10 mm outside
the land field, on Top), 62 are vias that so far carry copper on Top only (51 in the land field,
11 outside). **Clearance (all three rules), Short-Circuit, every Width rule, Routing Via Style,
Hole-to-Hole: 0.** Saved file: `Vias6` 107, `Tracks6` 948 = 630 + 318 (Top 295, L3 2, Bottom 21),
pads 829 unchanged, `verify_widths.py` and `verify_stack.py` PASS.

## Handed to routing

- Every escape below the vias on L3/L4/Bottom (107 vias). Between adjacent ring-3 vias no lane passes on any layer; three 3 mil lanes pass between vias 1.0 mm apart, one between vias 0.75 mm apart, two between vias 1.0 mm apart only if one is 0.20 wide.
- Rail feeds into the core: Width_PWR_VCC3V3 mid-layer min 1.05 mm and Width_PWR_VCC1V0 mid-layer min 0.50 mm cannot pass the 0.5 mm-pitch wall, so VCC3V3 (min 0.20) and VCC1V0 (min 0.15) come in on Bottom, or those inner-layer minima are re-derived first (already an open item). VCC1V8 into D8/E5/G14/H14/J14 from C93/C144 (east, Top). The VCC1V0 trunk placed under the die (K10 -> C89-1 -> C90-1 / C91-1) still needs its feed from C140-C143.
- The GNDADC trace from the D11 via to C123/C124/L6 on Bottom, kept off the GND planes (separate net).
- All ring-0/1 signal vias and routes: the ring-1 stubs end 0.10 mm outside the land field with their gap fixed; ring-0 signals leave at their row/column line. Bumps: a track 0.25 mm from an outside via moves 0.053 mm away within +-0.171 mm of the via's outward coordinate. The east side has one spare gap (V|W), the west side none, the south side one (1|2).
- North side: A14 A15 A16 A17 and the B15 B16 B17 stubs go north under U4's body (no copper between x 44.6 and 50.4); D14/D15 need vias there, SD-DAT1/SD-DAT3 go west to X3, CHAN2/CHAN3 to X2 pads 5/6 at the top edge. A18 and B18 must turn east above A19 (two corridor tracks) and then north through the 0.445 mm channel between U4 pad 5 and C93 (exactly two 3 mil tracks). The B14 thread occupies the corridor floor from x 48.15 to 47.15.
- Outer-band cap ties: C107-1 C108-1 C109-1 C110-1 C111-1 C112-1 C113-1 C114-1 C115-1 (VCC3V3) and C107-2 ... C115-2 (GND) are not drawn; the nearest same-net vias are the south/west/east outside vias (0.4-1.5 mm) but the straight ties cross the Bottom escape corridors of the T-row and D-row vias.
- Ring 4 keeps 24 free cells (E8 E9 E13, F5 G5 H5 J5 K5 L5 M5 N5 P5, R5..R15 except none used, G15 H15 J15 P15) for stagger or stitch vias; each non-GND via there costs another 0.385 mm2 of plane.
- The 3-mil-in-BGA-fanout question sent to JLC applies to the 0.0993 mm gap passages (47 ring-1 stubs, the six necks, the four escape lanes) and to the 0.104 mm diagonal-beside-via cases.
- Placement questions surfaced, not fan-out: C90/C91 (VCC1V0 0201s) sit under VCC3V3 balls, 2 mm from any VCC1V0 ball; C115 pad 2 is 0.025 mm from the natural V18 east via position.

Also surfaced, not fan-out: C90/C91 (VCC1V0 0201s) sit under VCC3V3 balls 2 mm from any VCC1V0
ball; C115 pad 2 is 0.025 mm from the natural V18 east via position. The 3-mil-in-fan-out
allowance JLC confirmed on 2026-09-14 is what the 57 gap passages and the 0.104 mm
diagonal-beside-via cases rely on.
