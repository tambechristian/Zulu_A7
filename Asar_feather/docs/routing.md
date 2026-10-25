# Asar A7 Feather -- routing log

Stack: the production 6-layer HDI stack, unchanged: Top / L2-GND (pour) / L3-SIG / L4-SIG / L5-VCC3V3 (pour) / Bottom,
through 0.20/0.35, laser 0.15/0.30 (Top-L2, L2-L3, L4-L5, L5-Bottom), buried L3-L4 0.15/0.27.

## Stage 1 -- U1 fan-out transplanted from production (2026-10-23)

U1 (XC7A35T, CPG236) is at rot 0 on both boards, and the Feather's 24 under-U1 decaps sit at the production
offsets. So production's DRC-clean escape copper inside U1's footprint is valid Feather geometry: shift it by
the U1-centre offset and re-net it ball by ball.

| Step | Tool | Result |
|---|---|---|
| Production copper | `tools/transplant_u1.py --dump` (KiCad python) -> `tools/route/prod_u1_copper.json` | 4,203 tracks, 1,790 vias, 238 U1 balls |
| Ball map | same | 193 balls keep their net, 18 swapped header balls take the new CHAN net, 19 now unconnected, 8 unconnected on both boards. Every production net maps to one Feather net. |
| Plan | `tools/transplant_u1.py --r 5.5` -> `tools/route/stage1_u1.json` | Window: +-5.5 mm around U1's centre (24.40, 11.43), all layers. Tracks crossing its edge are clipped there, and their outer ends become stage-2 starting points. Every piece is checked against every Feather pad of another net at 0.09 mm, with BGA lands modelled as circles. Copper not connected back to a pad of its own net is pruned. **201 vias + 771 tracks on 103 of U1's 104 nets.** CHAN1 has none: its production copper left the window. |
| Placement for it | `plan_placement.py`, `FeatherPlace6/7.pas` | Bulk parts are banned from the window on the bottom (new zones `B_u1n`/`B_u1s`). Ten 0805 bulk caps had been packed under U1, on production's through-via sites; they moved to the north and south bands, the column east of the window, and C94 by the buck cells. C92 and C123 now use production's rot 180; at rot 0 their pad nets swapped sides. The buck output caps are at x 16.705/18.455 (0.1 mm mask webs to the inductors). |
| Place | `tools/emit_copper.py` -> `FeatherCopper_Stage1U1.pas` (PlaceStage1U1) | 201 vias, 771 tracks, every net found |
| Microvias | `Zulu_Altium_VS_Code/tools/stage13_mark_microvias.py <pcbdoc> --expect 87` (board closed) | Scripted laser vias save as regular blind vias. 87 were marked (Vias6 byte 312) and verified. |
| Verify | `tools/verify_copper.py tools/route/stage1_u1.json` | **PASS**: 201/201 vias, 771/771 tracks, nothing missing or extra |
| DRC | `docs/drc_stage1_u1.drc` (after Repour All) | **580 = 465 un-routed + 115 net antennae**, nothing else. Un-routed went from 595 to 465. The antennae are the clipped stubs at the window edge, where stage 2 continues. 0 clearance, short, width, hole, mask or silk violations. |

Dropped at the window edge for Feather pad conflicts: one Top-L2 microvia (UART_FT_RTS#, on R16), two west
through vias (AIN16_N, GND, on C86/C144), and stubs into the strap row, RESET and the buck caps. These nets
are routed onward in stage 2.

X3's designator has no clean spot after C146 moved, so it is now hidden too (11 hidden designators).

## Remaining

465 connections: SDRAM U1 -> U3 (east), FT2232HQ U2 <-> U1 (JTAG, UART, FIFO), flash U4, header pins, USB pair
X1 -> U2, microSD X3, LEDs, buck feeds and plane ties, U8 charger, the XADC dividers.

RESET sits 0.85 mm south of U1's south ball row, in the path of the south-row escapes. That is where the SE
header balls (W13-W19, V19, U19) and several SDRAM balls exit.

## Stage 2 -- Freerouting through KiCad (2026-10-23/24)

Tools, installed without admin rights:
- Freerouting 2.5.0 jar in `%LOCALAPPDATA%\Programs\freerouting`.
- Temurin 25 JRE zip in `%LOCALAPPDATA%\Programs\temurin25`, checksum-verified against Adoptium's published value.
- Freerouting's native `freerouting-cli.exe` crashes 12 s in (a ComponentOutline serialization error) and then hangs, so it is not used.
- Always pass `--usage_and_diagnostic_data.disable_analytics=true`; otherwise it tries to send usage data to its servers.

| Step | Tool | Notes |
|---|---|---|
| Board -> DSN | `tools/fr_prepare.py <wd>`, then the same with `--export` | Every existing track and via is locked and exports as `(type fix)`. L2/L5 become power layers. Per-layer width classes come from the board's Width rules: sdram, v33, u8, v10, sw, rails, usb, default 0.0762. Clearance 0.09. The six board via types. 0.3 mm keepout band inside the board edge. KiCad's python exits 127 right after SaveBoard; the file is complete. |
| Route | `java -jar freerouting-2.5.0.jar --gui.enabled=false --usage_and_diagnostic_data.disable_analytics=true --router.automatic_neckdown=false -de feather.dsn -do run.ses --router.autorouter.max_passes=100 -mt 22` | About 70 min. Pass 1 is always the best; later passes score worse and it stops early. Fan-out escapes only 47-49 % of SMD pins. It uses through vias, and microvias essentially never. |
| SES -> plan | `tools/fr_import.py <wd> run.ses tools/route/stage2_fr.json` | The new copper is everything not locked |
| Place | `emit_copper.py` -> `FeatherCopper_Stage2FR5.pas`; `FeatherWidthFix.pas` (WidenPowerTracks) | 126 vias, 1,496 tracks. 46 neck-downs of 0.057 mm were widened to 0.0762 in the plan, and 21 power tracks to their per-layer minimum on the board. |
| Verify | `verify_copper.py stage1_u1.json stage2_fr.json` | **PASS** 327/327 vias, 2,267/2,267 tracks; 87 microvias still marked |

| Run | Rules | Unrouted after (KiCad, planes refilled) | Placed? |
|---|---|---|---|
| 3 | single power class, no edge keepout | 179 | no (copper on the board edge) |
| 4 | + edge keepout | 180 | placed, then rolled back (334 width violations) |
| 5 | + per-layer width classes, neck-down off | 190 | **on the board** |

Altium DRC with run 5 on the board (`docs/drc_stage2_fr.drc`): **340 = 190 un-routed + 144 net antennae +
6 clearance**. The 6 clearance violations are VCC3V3 fan-out stubs on Bottom: by L4-1 (14.0, 4.2) and at
(20.2, 17.0)-(20.8, 15.5). Freerouting narrowed them to fit, and they collide once widened to the 0.2 mm
Bottom minimum. No width, short, hole or mask violations.

The 190 open connections are spread over about 120 nets: GND 22 and VCC3V3 19 (plane ties), most of the SDRAM
bus with one connection each, JTAG, flash, microSD, FT2232 control, clocks, header CHAN nets, USB pair, LEDs, XADC.

## Stage 3 -- targeted HDI router (2026-10-24)

Freerouting stopped at 190 open connections and used no microvias, so stage 3 is a router of our own.

| Tool | What it does |
|---|---|
| `tools/route_model.py` (KiCad python) | The saved board as the router sees it, written to `tools/route/model.json`: pads (true extents, BGA lands round), tracks, vias with spans, planes |
| `tools/route_conn.py` | Connectivity the way Altium judges it: copper overlap on a shared layer, a via joins its span, the L2/L5 pours join GND/VCC3V3 vias. **Reproduces Altium's 190 exactly.** |
| `tools/router.py` | A* on a 0.025 mm grid over Top/L3/L4/Bottom. Clearance comes from distance transforms with a 1.5 mm halo; every shape is painted 0.7 cell fatter, plus a 0.02 mm allowance. Uses the board's per-layer width table and its via types: Top-L3 and Bottom-L4 microvia stacks, buried L3-L4, through. Plane ties are microvias Top-L2 (GND) and L5-Bottom (VCC3V3), or through vias. String-pulling straightens paths. Hole-to-hole 0.24 mm applies within a net too (Altium only exempts a stack at exactly one point). Optional rip-up and reroute (`--rip`; it gained 3 connections in 3 hours, so stage 3 used `--rip 0`). |
| `tools/route_check.py` | Independent exact check of a plan against all copper: clearance per net/layer, widths, edge 0.3 mm, hole-to-hole, then a connectivity recount |
| `tools/emit_copper.py` | Now also deletes a plan's `remove` tracks first (all of them or nothing) |

Bugs found on the way, each caught by `route_check.py` or Altium before placement stuck:
- The distance field ignored copper outside the search window.
- Raster edges under-drew copper by up to one cell.
- The path trace put each via on the node before the layer change, so tracks landed on the wrong layer.
- Two vias of one net were placed within hole spacing.
- The same via was committed twice where two routes met (3 duplicates removed with `FeatherDedupeVias.pas`).

Result on the board (`tools/route/stage3b.json`, `FeatherCopper_Stage3b.pas`):
- The 6 failing VCC3V3 stubs were removed (`tools/route/remove_stage3.json`).
- 398 vias and 1,464 tracks added; 280 microvias marked, 365 in all.
- `verify_copper.py` stages 1+2+3: **PASS**, 725/725 vias, 3,725/3,725 tracks.
- Altium DRC (`docs/drc_stage3.drc`): **169 = 64 un-routed + 105 net antennae**, nothing else.
- All 43 plane ties closed but one (VCC3V3 at 18.12, 8.15).

**Open: 64 connections.** Most are the SDRAM bus between U1 and U3 (the A, D and control nets). The rest are
JTAG/config (FPGA-T*, CFG-M*, CCLK, INIT#, DONE), microSD, FT2232 UART/power-enable, XADC (AIN15/16, ANALOG-IO*),
a few header CHAN nets, RST#, VBATT and VCC1V0. The SDRAM bus needs a planned lane assignment on L3/L4, as
production did (`sdram_route_plan.py`), not more search. The 105 antennae are dead-end stubs from stages 1-2;
the ones still unused at the end get trimmed.

## Why the SDRAM bus does not close (2026-10-24, after stage 3)

29 of the 64 open connections are SDRAM nets. On the Feather, 33 of U1's 39 SDRAM balls face WEST, toward U2.
That is where production put U3, but the Feather's U3 is EAST of U1. The transplanted escapes end on Top at U1's
west window edge (x 18.95), in pockets with no via room: the L3/L4 copper under U1, the buck caps below, and
U2's east pins 0.7 mm away. A0's escape, for example, reaches only a 288-cell pocket. A* with a 6-million-step
budget (9 min) still fails.

Straight-line ball-to-destination totals for U1's signal nets, by U1 rotation:

| U1 rot | total | SDRAM | header CHAN | FPGA cfg | flash | microSD |
|---|---|---|---|---|---|---|
| 0 (now) | 1193 mm | 552 | 187 | 95 | 52 | 71 |
| 90 | 1142 | 354 | 296 | 113 | 66 | 52 |
| 180 | 1197 | 333 | 380* | 106 | 82 | 39 |
| 270 | 1303 | 538 | 302 | 79 | 72 | 66 |

\* before re-running the header ball swap (`plan_pin_swap.py`) for the new orientation.

## Re-start with U1 turned 180 degrees (2026-10-24, user's choice)

- All routing copper cleared (`FeatherClearCopper.pas`: 725 vias, 3,725 tracks).
- U1 at rot 180. The 16 production decaps inside U1's +-5.5 mm window turned with it: point-mirrored about
  (24.40, 11.43), rot +180.
- C111/C114/C115, whose mirrored spots land on the buck output caps, plus C116-C122 and C124, which sit outside
  the window, are packed by the planner. 61 parts moved in all (`FeatherPlace8.pas`). `check_placement`/`verify_placement` PASS.
- Header ball swap redone from the original schematic (SchDocs 5/6 restored from d678306, then
  `plan_pin_swap.py` + `apply_pin_swap.py`): 250.9 -> 243.7 mm. XDC regenerated. Import Changes (36 pin moves,
  removals unticked). `check_feather_schematic` PASS, `sch_vs_board` MATCH.
- Stage 1 again: `transplant_u1.py` now turns production copper with U1's rotation and uses rotated ball
  positions. 211 vias, 815 tracks, 88 microvias marked; `verify_copper` PASS.

## SDRAM bus: U3 turned 90 degrees (2026-10-25)

With U1 at rot 180, the bus is almost a reversed permutation: data first at U1 and last at U3, in y. 346 net
pairs cross, which is not layer-separable. Turning U3 instead:

| U3 rot | crossing pairs | straight length |
|---|---|---|
| 0 | 346 | 298 mm |
| 90 | **77** | 268 mm |
| 180 | 312 | 265 mm |
| 270 | 538 | 296 mm |

At rot 90 a 3-layer colouring has no same-layer crossing: L3 18, L4 16, Top 5 nets
(`tools/route/sdram_layers.json` holds the rot-0 end points; recompute after the turn).

Placement plan: U3 rot 90; C3-C8 turned with it into the now-horizontal centre channel and shifted west to
clear X3 (x 31.20-36.95, y 11.43). C9 and C11 are packed by the planner; 19 parts move, all east of x 30.6, so the
stage-1 copper is untouched. `check_placement` PASS. **Not yet on the board:** Altium fell into Viewer mode
(license) before the placement could be saved.

Earlier trials, on the rot-0 U3: sequential shortest-first closes 31/39 SDRAM nets, rip-up 29, and the
negotiated-congestion mode (`tools/negotiate.py`, `router.py --negotiate`) 11.

## SDRAM bus placed (2026-10-25)

- U3 rot 90 is on the board (`FeatherPlace9.pas`). The checks pass.
- Layer plan: `tools/sdram_layers.py`. The router takes it with `--layers` (per-net layer cost multipliers:
  own layer 1, Top 4, other inner layer 8, Bottom 12).
- Trials, each for 39 SDRAM nets:
  - stage 1 at 5.5 mm + layers: 24 (short-first order), 27 (name or y order)
  - negotiated mode + layers: stalled
  - stage 1 at **7 mm** + layers, y order: **32**, 0 violations
  - the last 7 with no layer plan on top of those 32: 0 (walled in)
- On the board:
  - the 5.5 mm stage 1 cleared (`FeatherClearCopper2.pas`)
  - stage 1 at 7 mm placed (`FeatherCopper_Stage1U1R7.pas`: 271 vias, 989 tracks)
  - the SDRAM bus placed (`tools/route/stage3_sdram.json`, `FeatherCopper_Stage3Sdram.pas`: 162 vias, 801 tracks)
  - 247 microvias marked
  - `verify_copper` PASS 433/1790
- 430 connections open. SDRAM still open: A5, A7, D1, D2, D3, LDQM, SDRAM-CS#.

## Stage 4 -- the rest (2026-10-25)

- `tools/router.py` over every open connection, on top of stage 1 + the SDRAM bus: `tools/route/stage4.json`,
  route_check PASS (0 violations). 373 connections routed, 57 open on 45 nets.
- On the board (`FeatherCopper_Stage4.pas`): 681 vias, 1993 tracks; microvias marked (733 in all).
- DRC (`docs/drc_stage4.drc`) found 6 problems that route_check does not model; `FeatherFixStage4.pas` and
  `FeatherFixC3Mask.pas` cleared them:
  - Hole To Hole (2): the router put a VCC3V3 through via and a VCC3V3 L4>L5>Bottom microvia stack at the same
    point (34.95, 12.425). route_check exempts exact coincident stacks. The through via joins every layer, so the
    two microvias were removed, from the board and from stage4.json (679 vias).
  - Mask Sliver (4): C3, moved with U3's rotation, is 0.185 mm from X3's pads. Rule SolderMaskExpansion_C3 at
    0.02 mm leaves 0.115 mm (0.035 mm left exactly 0.100 mm, which still fails).
- After the fixes: verify_copper PASS (1112 vias, 3783 tracks), 731 microvias, DRC 124 = **57 Un-Routed + 67 Net
  Antennae** (the stubs of the open nets), nothing else. Board md5 f30d1167.
- Still open (57 connections): SDRAM A5, A7, D1, D2, D3, LDQM, SDRAM-CS#; the XADC nets; CFG-M0/M1; the FLASH
  nets; the FPGA JTAG nets; RST#; header CHAN nets; SD nets; LEDs; VCC1V0 x3, VCC3V3 x4, GND x2, USB5V0,
  FT-VPLL, PUDC_B, BTN; 6 plane ties.

## Renamed Zulu -> Asar (2026-10-25, user request)

`tools/rename_asar.py` rewrote the contents (every replacement keeps its length, so the Altium binaries were
edited stream by stream): Zulu_feather -> Asar_feather, zulu_feather -> asar_feather, zulu_a7_N -> asar_a7_N
(sheets, sheet component classes, SOURCEHIERARCHICALPATH), DRAWING_NAME zulu_a7 -> asar_a7, the silkscreen
'ZULU A7' -> 'ASAR A7'. Then git mv: the seven sheets, the project, board and library, the XDC and the folders.
References to the production board (Zulu_Altium_VS_Code, Zulu_kicad, vivado/zulu_a7_pins.xdc) and the part names
ZULU-CONN / ZULU-DIP37 are unchanged. Checks after: check_feather_schematic PASS, verify_copper PASS, the board
opens in Altium with ASAR A7 on the silkscreen. Earlier `docs/drc_*.drc` keep the old paths (they record past runs).
