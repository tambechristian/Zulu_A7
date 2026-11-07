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

## Stage 5 -- finishing passes and ball swaps (2026-10-26 .. 28)

Working base: `model_53` = stage 1 (7 mm) + the SDRAM bus + a stage-4 re-run (`short_r3_p400000`, rip 3, short-first
order: 53 open, 4 better than the plan on the board). The board itself still holds `stage4.json` (57 open), so the
copper of stages 1/3/4 is cleared (`FeatherClearCopper3.pas`, which insists on the board's 1112 vias / 3783 tracks)
and everything re-placed when the next plan goes on.

- Finishing passes on top of model_53 (`router.py --seed`, the seeds rippable): name order at 6M pops **45 open on
  36 nets, 0 violations** (`fin_name_6000000`); short order 45, y order 46. Seeded rip-up passes that also let the
  SDRAM bus move (model = stage 1 only, bus + stage 4 + plan as seeds): rip 3 at 1.5M pops 50 and 56 (short / y
  order), rip 6 at 800k 51. Rip-up makes it worse: the victims re-route and fail.
- `tools/diagnose_open.py` on the 45: no placement walls; 19 blocked by fixed copper, 16 by congestion, 18 by
  budget/order.
- **Probes (2026-10-28, `router.py` now records `Rt.pops`): every failing search ends by exhausting its pocket, never
  its budget** -- LED1 at N18 after 5,238 pops, LED0_R moved to the spare ball U19 after 20,433, CHAN18 at W13 has 60
  free cells and no via site, the large ones (SD-CMD, A5, CLK-12M-FPGA) after 130k-600k with 3M allowed. The open
  islands sit in pockets sealed by other nets' copper: on U1's west face FLASH-CS#, FPGA-DONE, FPGA-TMS, FT-PWREN#,
  UART_FT_DTR#, FLASH-D02, CHAN22 on L3/L4, GND, VCC1V8, VCC1V0, BTN on Bottom, RST#, CHAN-CLK on Top (U2 sits 1.8
  mm west of U1; the flash is east beyond X3, the LEDs and SD socket east too, so the west-face nets have to get
  round or through U1). `tools/pocket_walls.py <model> <plan> <stage1> <ball>` lists a pocket's walls per layer
  with their owning plan.
- **`tools/swap_reach.py`**: for every swappable or spare U1 ball, an exact flood of the router's free cells from
  the ball's stub (or bare pad), crossing layers wherever the router's own via test passes, the ball's net stripped
  to its stub and everything else fixed; says which single-ball nets' far-end pads the pocket touches. 99 balls in
  4 minutes on 16 cores (`reach.json`). Findings on model_53 + fin_name:
  - 34 balls are sealed outright, among them the open nets' own balls for A5 A7 AIN16_P/N CHAN18 CLK-12M-FPGA D1 D2
    D3 LDQM LED1 SD-CLK SDRAM-CS# SD-DAT3 and 16 of the 19 spare (NC) balls (all bank 14, west face).
  - the north-face header balls CHAN15/16/17/19/20/21/22 (W14-W16, V13-V15, U14, U15) sit in pockets of 0.9M
    cells that reach 42-46 far ends, including the open SDRAM lines' U3 pads and the LEDs.
  - a pair swap needs both pockets: X's target must reach X's far end and X's old ball must reach the displaced
    net's far end; a sealed ball fails the second test, so those nets only move by a **rotation** through a spare
    ball (X takes a header ball, the header net takes a spare ball whose pocket reaches its header pin, the
    sealed ball is vacated). Spare balls with a pocket: E19 (reaches CHAN0/14/15, SD-DAT0/1), H19, J19.
  - own-ball re-route possible (strip the partial copper, route from the stub): AIN15_N, AIN15_P, SD-DAT0, SD-DAT1.
- Swap rules (`tools/swap_rules.py`, from the CPG236 pinout): all used banks are 3.3 V, so an I/O net may take any
  HR ball of banks 14/16/34/35 except the configuration balls the board uses (D00-D03, FCS_B, PUDC_B) and bank 0;
  XADC inputs move as P/N pairs onto ADnP/ADnN; CLK-12M-FPGA stays on an MRCC ball; header nets avoid RDWR_B and
  EMCCLK; SDRAM nets stay in banks 34/35/16. 131 of U1's balls are fixed, 19 spare, 86 movable.
- `tools/swap_eval.py --reach reach.json`: only the 199 swaps the floods allow (4 own-ball re-routes, 80 pairs, 115
  rotations) are routed for real, one whole-board window at 1.2M pops, the swapped balls' islands stripped to the
  stubs (`swapped(..., side=True)`), gain = connections closed minus connections opened. `swap_apply.py` turns the
  chosen set into the swapped model + seed for the finishing pass, `perm.json` for `apply_pin_swap.py` (the
  symbol-pin renames follow the pin positions, so rotations work) and the re-netted stage-1 plan for the board.
- `router.py --soft 0.5`: rip-up now looks for the path crossing the least rippable copper (a cost per cell of it)
  and rips only what that path's own clearance overlaps, instead of the straight base-only path and every net near
  it. Running on model_53 + fin_name as `soft_r3`.
- **Swap evaluation result (2026-10-28, `swap_reach.log`)**: 47 of the 199 jobs close a connection (gain +1 each; every
  base job, every pair without a header or SD-DAT2 ball, and every rotation that hands a ball to A5/A7/AIN16 is 0
  or negative), and every gain is bounded by the receiving pocket: L3 (SD-DAT2) and W15 (CHAN15) each take one of
  CHAN18 / LED0_R / LED1 / LED2 / SD-CLK / SD-CMD, W16 (CHAN14) takes SD-DAT3, the spares E19/H19/J19 take the
  displaced header net or SD-DAT3 straight, and SD-DAT0 / SD-DAT1 swap with CHAN4 (C17), CHAN17 (V15), CHAN21
  (U15) or CHAN16 (W14). Five disjoint swaps is the most the floods allow at once; the greedy set (the cheapest
  copper per gain) is applied as `swapA`:

  | swap | nets | expected |
  |---|---|---|
  | P17 <-> L3 | LED0_R -> L3, SD-DAT2 -> P17 | +1 |
  | W16 -> J19, A16 -> W16 | SD-DAT3 -> W16, CHAN14 -> J19, A16 vacated | +1 |
  | C15 <-> C17 | SD-DAT0 -> C17, CHAN4 -> C15 | +1 |
  | W15 -> H19, W13 -> W15 | CHAN18 -> W15, CHAN15 -> H19, W13 vacated | +1 |
  | B15 <-> V15 | SD-DAT1 -> V15, CHAN17 -> B15 | +1 |

  Ten nets move; `swap_apply.py` dropped their copper from the seeds (2768 tracks / 776 vias left) and re-netted
  16 stage-1 via stubs. Finishing passes on the swapped model: `swapA/plain` (rip 3, 1.5M pops) and `swapA/soft`
  (rip 3, soft 0.5). The nine nets no swap reaches (A5, A7, AIN16, CLK-12M-FPGA, D1-D3, LDQM, SDRAM-CS#, ...) still
  need the walls moved, which is what the soft pass is for.
- **Review of the swap toolchain (2026-10-28, 49 agents, before anything touched the project)**: the ten moves are
  legal (every destination an HR ball of a 3.3 V bank, none a configuration ball the board uses, CHAN4 keeps a
  SRCC ball, no clock or XADC net moved, H19/J19 really unconnected), the symbol-pin rename moves every net label
  to the intended ball on both sheets that hold U1 (1668 + 36 pin records) and the routing inputs match their
  sources object for object. Three defects, all fixed:
  - `swap_apply.py` re-netted none of the 71 stub **tracks** (only the 16 vias): its track key depended on the end
    order and the board export stores every stage-1 stub end-reversed. The board chain would have put old-net
    tracks under new-net vias at every swapped ball. Keys are end-order-free now; the script also refuses when
    the re-netted count differs from the touched balls' stub count, de-duplicates the seed (short_r3 holds 12
    tracks twice) and refuses an XADC input whose mate ends on another ADn pair. `tools/swap_check.py` proves an
    output folder: pads, stubs, `stage1.json + stage3_sdram == model.json`, seed clean -- PASS on swapA.
  - `apply_pin_swap.py`'s run-twice guard could not fire (a pool closed under its permutation looks the same after
    any number of runs) and its default argument re-applied the pre-routing swap. It now needs the path and
    refuses unless every net of the plan's `swap` table still sits on its old ball in the schematic netlist
    (tested on copies: first run applies, second refused, `pin_swap.json` refused).
  - `check_feather_schematic.py` knew only `pin_swap.json`; `--perm <file>` composes later permutations in
    order (PASS on the swapped copies with swapA's perm.json, FAIL without it).
  Noted, not fixed: `tools/route/model.json`, `board_dump.json` and the committed stage-1 artefacts carry the
  pre-swap pad nets until the ECO and a re-dump; README's pin table is stale since the first swap; EXTERNAL_AVOID
  does not list DOUT_CSO_B/CSI_B (unused in SPI x4, harmless on a header). `tools/plan_dedupe.py` strips the
  duplicate tracks from a finished plan before it is emitted.
- **swapA finishing passes, first results (2026-10-29)**: name order **49 open on 35 nets** (`swapA/plain`, 0
  violations, 20 h), y order 50 on 35 (`swapA/y`); the pre-swap best stays 45 on 36. Every moved net routed except
  SD-DAT0, SD-DAT1 (plain) and LED0_R (y), and the passes closed nine nets the seed had open (AIN15_N CHAN18
  CLK-12M-SHARED FLASH-D00 LED2 SD-CLK SD-CMD SD-DAT3 TMS in plain) -- but rip-up lost eight seed nets that never
  re-routed (CFG-M2 CHAN2 CHAN22 FLASH-CS# FLASH-D02 GNDADC UART_FT_CTS# VCC1V8), so the count did not move. The
  two passes lost different nets (y: BTN CHAN16 CHAN17 CHAN20 FPGA-TMS VCCADC ...), so the loss is the rip-up
  heuristic, not a wall. Round 2 started on `plain.dedup.json` (`plan_dedupe.py`: 3005 -> 2988 tracks): a second
  flood + reach-filtered evaluation (`swapA/reach2.json`, `swapA/swap_eval2.json`, W13/A16 now spare) and two
  passes seeded from plain (`r2soft` soft 0.5 name order, `r2short` short order). `swapA/soft`, `swapA/short` and
  the no-swap control `soft_r3` are still running (checkpoints 68 / 69 / 75 open at 16 h).
- **Round 2 (2026-10-29, `swapA/reach2.json`, `swapA/swap_eval2.json`, 163 jobs)**: on the 49-open plan only four
  nets have a swap at all -- SD-DAT0 (C17) routes from its own ball and every rotation through C17 gains, CHAN22 and
  LED1 can take H19/C17, UART_FT_CTS# L18; the rest (A5 A7 AIN15/16 CLK-12M-FPGA D1-D3 LDQM SDRAM-CS# LED0_R SD-DAT1)
  have no candidate. Greedy disjoint set +4, of which the AIN16 rotation (`H2>L3 J2>M3`) was dropped: it buys LED0_R
  by leaving A12, a routed SDRAM address line, open. Applied as `swapB` (`swap_apply.py --stage1-src swapA/stage1.json`,
  `swap_check.py` PASS; `perm.json` composes after swapA's):

  | swap | nets | expected |
  |---|---|---|
  | C17 -> W18, A17 -> C17 | CHAN2 -> C17, SD-DAT0 -> W18, A17 vacated | +2 |
  | H19 -> R19, V15 -> H19 | SD-DAT1 -> H19, CHAN15 -> R19, V15 vacated | +1 |

  Finishing passes `swapB/plain`, `swapB/soft`, `swapB/short` seeded from `swapA/plain.dedup.json` minus the four nets.
- **Pocket walls of the sixteen sealed balls (`swapA/walls2.log`)**: A5 (R2), A7 (P1), D1 (V7), D3 (W6), LDQM (W4) and
  SD-DAT1 (V15) reach a few hundred Top cells, no inner layer and no via site -- their walls are the *model's* own
  stage-1 stubs (A7 and A5 wall each other, D0/D2 wall D1, WE#/D6 wall LDQM, CHAN19/AIN15_N wall V15). The
  transplanted fan-out gave these balls Top-only stubs (W4 none) because on the Zulu board they ran on Top straight
  into the SDRAM; here U3's west edge sits 0.7 mm east of P1. No swap or finishing pass can open them: the fix is
  at the fan-out. The other sealed balls (AIN15_P, AIN16_P/N, LED0_R, CLK-12M-FPGA, CHAN2, D2) have pockets of
  thousands of cells walled by routed plans, which the soft passes may move.
- **Corner experiment (`corner/`, `tools/corner_seed.py`)**: the stage-1 stubs of the 34 balls at x >= 25.6,
  y >= 12.6 (26 with stubs, 112 tracks + 11 vias of 26 nets: A0-A11, BS0/1, D1-D7, RAS#, WE#, SD-CMD, SDRAM-CS#,
  VCC3V3) moved from the model into a rippable seed (`corner/stubs.json`, dropped list in `corner/dropped.json`),
  so the router may rip a neighbour's stub to escape a sealed ball; `corner/soft` (soft 0.5, name order) and
  `corner/short` on swapB's model + seed. If a plan from here is chosen, the board chain must drop the dropped
  stubs from stage1.json before placing.
- **Six of the open power connections are U3's own balls** (GND E3, B7; VCC3V3 C7, A7, A9 and one more site): the
  router's plane-tie search fails under the SDRAM (`FAIL plane tie` lines in every log since fin_name). A
  via-in-pad or a hand-placed via each, not a routing problem.
- Memory: every router / evaluation worker commits ~2 GB; 50 python processes at once hit the Windows commit limit
  (`tools/procs.ps1` lists and kills by command line; `swap_eval.py --procs 6` while routers run).
- **swapA/short finished (2026-10-29 07:30): 48 open on 34 nets**, the best on the swapped model, with yet another
  open set (it closes AIN15_P AIN16_P/N CHAN2 CHAN22 LED0_R SD-DAT0 UART_FT_CTS# CFG-M2 FPGA-TCK that plain leaves
  open, and loses CHAN14 CHAN18 CHAN3 FLASH-D00 FPGA-TMS LED0_B LED2 NODE_P1 SD-DAT3). So CHAN2 and SD-DAT0, moved in
  swapB, are routable where they were -- the sealed pockets of the big balls are plan-dependent; only the
  fan-out-sealed five and the fixed configuration/JTAG/power connections are open in every pass. Merging the passes
  does not work: every donor route collides with base copper (`scratchpad/merge/merge.py` kept nothing; the
  merge-then-repair variant `merge2.py` had to rip 19 base nets for 4 donor routes, 70 open). Iteration pass
  `swapA/r3soft` seeded from short.
- **The U3 plane ties, diagnosed (2026-10-29):** the two GND balls (E3, B7) tie once the router may place a single
  Top>L2 microvia (`uvia_top`; `uvia_bot` L5>Bottom for VCC3V3 on the Bottom side) -- `planetest` closed both. The
  three VCC3V3 balls A7, A9, C7 and U1's own VCC3V3 ball R1 cannot be tied on any plan: VCC3V3 may only run on Top and
  Bottom, its plane is L5, and the fixed SDRAM bus runs on L3/L4 directly under the pad centres (D4 0.055 mm from A7's
  centre, A4 0.015 mm from C7's, RAS# and its L4>L5>Bottom stack 0.07 mm from A9's; A1/A4/A6 under R1), while every
  interstitial around them holds a bus via and its dogbone -- `scratchpad/tie_probe.py` found no site for a through
  via (0.35 land) nor for a stacked column Top>L2>L3>L4>L5 (0.30/0.27 lands) within 1.7 mm, and a Top-only join to
  the tied island exhausts 1.3 M cells (the Top is sealed by the bus dogbones). So the ties need bus copper moved:
  `router.py` gained the `stack_tie` column type (via-in-pad allowed, Bottom untouched) and a rip-up step in the
  plane-tie branch (base-board search, blockers, rip, retry; victims re-queued), and `tools/bus_seed.py` moves the
  bus (`stage3_sdram.json`, 801 tracks / 162 vias) out of a model into a rippable seed. Test: `$D/tie/` = swapA model
  minus the bus + seed (short.dedup + bus, route_check 48 open / 0 violations), `--nets GND,VCC3V3 --rip 2 --soft
  0.5`. If a plan from here is chosen, the board chain must drop `tie/dropped.json` from the stage-3 emission.
- **No-swap control `soft_r3` finished (13:21): 50 open on 36 nets** (route_check PASS), worse than the 45 of
  `fin_name` it was seeded from: the soft rip-up iteration on the unswapped model lost BTN CFG-M2 CHAN14 CHAN4
  FLASH-CS# FLASH-D02 GNDADC VCCADC for FPGA-TCK LED0_R LED1 LED2 SD-CMD SD-DAT0 SD-DAT1 TMS. Another plan-dependent
  open set; the control line stays at 45.
- **swapA/soft finished (13:26): 48 open on 38 nets** (route_check PASS, `soft.dedup.json`), level with short's 48
  but on a different set again (closes CHAN14 CHAN18 CHAN3 CLK-12M-FPGA FLASH-CS# FLASH-D00 FLASH-D03 FPGA-TMS LED0_B
  NODE_P1 SD-DAT3 VCC1V8; loses AIN15_P AIN16_N/P ANALOG-IO1 BTN CHAN19 CHAN20 FPGA-CCLK FPGA-TCK LED0_G SD-CLK
  SD-CMD SD-DAT0 SD-DAT2 UART_FT_CTS# VCCADC). The swapped model's three passes sit at 48-50; the swapped nets
  themselves are closed, the loss is rip-up collateral that differs per pass.
- **Tie pass `tie/ties` finished (15:03): 47 open on 37 nets** (route_check PASS, 0 violations). Both GND balls tied
  with a Top>L2 microvia (E3 at 34.95,9.80; B7 at 32.65,12.90). Three of the four VCC3V3 islands tied with an in-pad
  `stack_tie` column (C7 at 33.375,12.875 after ripping A4 A6 D0 D4; A9 at 31.775,14.475 after A1 A2 A3 RAS#; A7 at
  31.775,12.875 after A11 A8 A9); the torn bus nets cascaded (D0's re-route ripped nine more, A2's five) and A3 D0 D6
  RAS# ran out of rip budget and stayed open -- the pass's own summary hid them because the OPEN report under
  `--nets` only listed the wanted nets (router.py now reports every net the pass touched). U1's own VCC3V3 ball R1
  has no router site: its 1.5 mm Top stub ends in the channel between the A5 and A2 fan-out stubs, 0.554 mm edge to
  edge, where a 0.30 land needs 0.48 by the rule but 0.56 with the router's raster margin counted twice; a hand
  column at the stub's end (30.400,13.935, `tie/ties_r1.json`) passes route_check with 0 violations: **46 open on 36
  nets, VCC3V3 and GND fully tied**. Pass 2 (`tie/ties2`, `--nets A3,D0,D6,RAS# --rip 2 --soft 0.5`, seeded from
  ties_r1) re-routes the four bus nets.
- **`tie/ties2` (bus re-route after the ties) finished worse: 50 open on 40 nets.** None of A3 D0 D6 RAS# found a
  path once fully ripped, and their rip-ups cascaded through 20 more nets (A2 BS1 CAS# D5 lost). A bus net torn out
  of the packed corner cannot be re-fitted by a from-scratch A* with rip-up. Local repair instead
  (`tools/tie_cut.py`): the column sites inside each pad that collide with the least seed copper
  (`scratchpad/tie_sites.py`: A7 31.725,12.880 hits only D4's L4 track; C7 33.400,12.830 hits A4 L4 and A6 L3; A9
  cannot avoid RAS#'s L4>L5>Bottom stack 0.07 mm from its centre, 31.725,14.455 adds only A2's Top track), the
  copper of those nets within 0.6 / 1.2 mm of the site cut out, and a `--rip 0 --margin 1.0` pass re-joining the
  five nets (`tie/rep0.6`, `tie/rep1.2`).
- **Local tie repair, rounds 1-4 (`tie/rep_*`)**: cutting whole segments let A4/A6/D4 re-join in some variants (45
  open, PASS) but never A1 or RAS#; clipping the tracks at the cut circle (`tie_cut.py` now keeps the parts outside)
  made every net fail, and the free-cell maps (`scratchpad/pocket_map.py`) show why: D4's only way around the A7
  column is the gap to the dangling end of A8's fixed L4 stub at (31.400,13.367), 0.352 mm free for a 0.30 need --
  legal, but not with the router's 0.02 mm raster allowance on each side. `router.py --slack` sets that allowance;
  at 0 the pass re-joined A1 A6 D4 (44 open) but D4 landed 0.095 from the column on L4 (rule 0.10, raster error), at
  0.01 D4 failed again. So the stub's tail is trimmed instead (plan `remove` of the stub + a seed track to its via at
  30.875,13.425; the tail was dead copper). A4 at the C7 column is sealed between D4's L4 diagonal (0.104 free) and
  D0's L4 via (0.161 free): D4 is cut there too so A4 can take its lane and D4 shifts south-west. RAS# at A9: the L4
  pocket next to the column is 0.25 mm wide, no stack_bot fits, and the Bottom is free only in the 0.25 mm cap-pad
  channel at y 14.63-14.88 -- its whole Bottom jog (both stacks) is freed in variant k.
- **Local tie repair reached 43 open on 33 nets (`tie/rep_n_s0.005`, route_check PASS, 0 violations)**: all six ties
  in, A1 A4 A6 D0 D4 RAS# re-joined. What it took: A8's dead stub tail trimmed (plan `remove`); the A9 column on the
  grid at (31.700,14.500) with A2's Top run nudged 0.01 mm south so A1 clears the column at exactly the 0.10 rule;
  D0 clipped 0.6 mm at C7 so A4 and D4 each get a lane; RAS# freed 2.5 mm -- its new L4>L5>Bottom stack sits at
  (32.075,14.700), 0.3 mm east of the old one, in the space of A3's stack and L4 diagonal, which were clipped 0.8 mm
  and did not re-join (A3 is the one net still open). A 0.005 mm raster allowance (`--slack`) is the sweet spot: 0
  leaves 0.095 mm near-misses the exact checker rejects, 0.01 and the default 0.02 seal the lanes. Next: keep A3's
  stack, clip only the first 0.45 mm of its diagonal at RAS#'s new site, and route RAS# before A3 in two passes.
- **TIE REPAIR COMPLETE: 42 open on 32 nets (`tie/rep_s2_0.005.json`, deduped `tie/final.dedup.json`; route_check
  PASS, 0 violations; open set = the short seed's 48 minus GND 2 and VCC3V3 4, nothing lost).** The chain, every stage
  `--rip 0 --margin 1.0 --pops 1500000` on `tie/model.json` with `--remove tie/remove_a8.json`:
  1. `tie_cut.py` with `tie/sites_p.json` on the seed (short.dedup + bus): the six ties (A7 column 31.725,12.905;
     C7 33.400,12.830; A9 31.700,14.500; R1 30.400,13.935; GND uvias 34.95,9.80 / 32.65,12.90), clips D4 0.4 at A7;
     A4 A6 0.4, D4 0.5, D0 0.6 at C7; A1 0.4, RAS# 2.5 at A9; A3 0.45 around 32.075,14.700 (kind-less cut site);
     then A8's stub tail trimmed and A2's Top run nudged to y 14.215 (`cut_p.json`).
  2. `--nets RAS# --slack 0.005` (its stack lands at 32.075,14.700, the pocket's only via site; routed first or A1
     takes it with a needless Bottom stack).
  3. `--nets A1 --slack 0.0` (its L3 lane past the A9 column is exactly at the 0.10 rule; any allowance seals it).
  4. `--nets A4,A6,D0,D4 --slack 0.005`.
  5. `tie_cut.py` with `tie/sites_s.json` (A0 clipped 0.6 around 32.2,15.2 -- its L4 staircase pinched A3's gap to
     0.325 mm; BS0 at y 15.625 leaves it 0.2 mm to move north), then `--nets A3 --slack 0.005`, then `--nets A0
     --slack 0.005`.
  Board chain for this plan: stage1 copper minus nothing new, stage3_sdram NOT emitted (the bus is inside the plan,
  `tie/dropped.json` lists it), the plan's `remove` (A8's L4 stub 29.800,13.530-31.400,13.367) deleted from the
  board, then the plan. The repair is seed-specific: a better signal plan needs the chain re-run on it.
- Housekeeping 19:30: `swapA/model.json` had been overwritten at 13:30 with the soft pass's deduped plan (a wrong
  output path); moved back to `swapA/soft.dedup.json` and the model rebuilt as `tie/model.json` + `tie/dropped.json`
  (1788 tracks / 433 vias / 821 pads) -- short.dedup and soft.dedup re-check at 48/34 and 48/38 as recorded. The
  passes running since before 13:30 loaded the model at launch and are unaffected. `tools/tie_repair.py` runs the
  whole tie recipe as one command (`<model with bus> <signal plan> <outdir>`).
- **swapB/short finished (2026-10-30 21:34): 42 open on 34 nets** (route_check PASS, 0 violations; rip 3, short
  order, seeded from `swapA/plain.dedup.json` minus the four swapped nets = 52 open). Against that seed it closes
  AIN15_P AIN16_N AIN16_P CFG-M2 CHAN15 CHAN2 CLK-12M-FPGA FLASH-D02 GND LED1 PUDC_B SD-DAT0 VCC1V8 (and one each of
  FLASH-CS#, SD-DAT1, VCC1V0) and loses BTN CHAN16 CHAN18 CHAN20 CLK-12M-SHARED FLASH-D00 LED0_G SD-CLK SD-CMD
  SD-DAT3 UART_FT_CTS# UART_FT_DTR#. The pass closed both GND ties itself; the four VCC3V3 ties still `FAIL plane tie`.
- **NEW BEST: tie repair on swapB/short = 38 open on 33 nets** (`swapB/tie_short/final.json`, md5 3de9caa7,
  route_check PASS, 0 violations, 4364 tracks / 1032 vias / 1 remove; repo copy `tools/route/stage5/tie38_swapB.json`).
  `python tools/tie_repair.py swapB/model.json swapB/short.json swapB/tie_short` ran unchanged in 12 min (the bus
  copper is identical in swapB's model: 801 tracks, 75 vias), stages 44 / 43 / 39 / 39 / 38, no bus net lost; its two
  GND sites duplicate vias the pass had already placed (deduped away). Open set: the fan-out-sealed five (A5 A7 D1
  D3 LDQM), D2, SDRAM-CS#, the configuration/JTAG group (CFG-M0 CFG-M1 FPGA-TCK x2 FPGA-TDI FPGA-TDO RST#), flash
  (FLASH-CS# FLASH-D00 FLASH-D01 FLASH-D03 x2), SD (SD-CLK SD-CMD SD-DAT1 SD-DAT3), CHAN16 CHAN18 CHAN20 CHAN22,
  CLK-12M-SHARED x2, BTN, LED0_G LED0_R, UART_FT_CTS# x2 UART_FT_DTR#, GNDADC x2, VCC1V0. Board chain for this
  plan: apply_pin_swap swapA then swapB (`swapB/perm.json` composes both), check_feather_schematic --perm, make_xdc,
  ECO (untick the 10 net classes + USB pair), FeatherClearCopper3, re-dump the model, emit swapB's stage1.json, NOT
  stage3_sdram.json (the bus is inside the plan; `bus_dropped.json` lists what must not be emitted), the plan with its
  `remove` (A8 stub), mark microvias, repour, DRC, verify_copper. Still running at 21:50: swapA r2soft / r2short /
  r3soft, swapB plain / soft, corner soft / short (queues 2-36 nets); any that beats 42 gets the same tie repair.
- **swapB/plain finished (2026-10-30 22:46): 47 open on 32 nets** (route_check PASS, 0 violations; rip 3, name
  order, same 52-open seed). Worse than swapB/short's 42, so no tie repair; it closes AIN15_P AIN16_N AIN16_P
  CFG-M2 CHAN15 CHAN2 CHAN22 CLK-12M-FPGA FLASH-D02 FLASH-D03 GND GNDADC LED0_R SD-DAT0 SD-DAT1 of the seed and loses
  AIN15_N CHAN-CLK CHAN18 CLK-12M-SHARED FLASH-D00 LED0_B NODE_P0 NODE_P1 RST# SD-CLK SD-CMD VCC1V8. Same four
  VCC3V3 `FAIL plane tie` sites. Four swap passes left: swapA r2soft / r2short / r3soft, swapB soft.
- **corner/short finished (2026-10-31 01:25): 54 open on 39 nets, route_check FAIL** (one hole-hole: two VCCADC vias
  0.225 apart at 21.600,18.075; rip 3, short order, seed = swapB seed + the 26 corner stubs, 52 open). Far worse
  than swapB/short's 42, so not a candidate -- but it answers the corner question: with the stubs rippable, **A7 and
  LDQM close** (two of the five fan-out-sealed balls) and one more VCC3V3 tie lands, while the pass tears the bus
  apart and cannot re-fit it (A0 A2 A3 BS0 BS1 D6 D7 WE# SD-CMD lost, plus CHAN16 CHAN20 CHAN6 NODE_P0 RST# SD-CLK
  UART_FT_RTS#). So the sealed balls are stub-walled as the pocket-wall analysis said, and the fix has to be a
  targeted stub move for A5/A7/D1/D3/LDQM with the bus held fixed, not a rippable corner. corner/soft still running.
- **swapA/r2short finished (2026-10-31 02:47): 49 open on 38 nets** (route_check PASS, 0 violations; rip 3, short
  order, seeded from `swapA/plain.dedup.json`, 49 open). No gain at all: it closes 16 nets of the seed (AIN15_P
  AIN16_N AIN16_P CFG-M2 CHAN2 CHAN22 CLK-12M-FPGA FLASH-CS# FLASH-D02 FLASH-D03 FPGA-TCK GND GNDADC LED0_R LED1
  VCC1V8) and loses 20 (AIN15_N BTN CHAN-CLK CHAN17 CHAN18 CHAN20 CHAN3 CHAN6 FLASH-D00 FPGA-TMS LED0_B NODE_P0
  NODE_P1 RST# SD-CLK SD-DAT3 UART_FT_CTS# UART_FT_RTS# VCC1V0 VCCADC). Same four VCC3V3 tie failures. Left:
  swapA r2soft / r3soft, swapB soft, corner soft.
- **swapB/soft finished (2026-10-31 04:40): 47 open on 36 nets** (route_check PASS, 0 violations; rip 3, soft 0.5,
  name order, 52-open swapB seed). Same count as swapB/plain, worse than swapB/short's 42, no tie repair. Closes
  AIN15_P AIN16_N AIN16_P CFG-M2 CHAN15 CHAN2 CHAN22 CLK-12M-FPGA FLASH-CS# FLASH-D02 FPGA-TCK GND SD-DAT0 VCC1V8,
  loses CHAN17 CHAN18 CHAN3 CLK-12M-SHARED FLASH-D00 FPGA-TMS LED2 NODE_P1 PROG# SD-CMD SD-DAT3. Same four VCC3V3 tie
  failures. All three swapB passes are in: short 42 / plain 47 / soft 47; short order wins on both swap models.
  Left: swapA r2soft / r3soft, corner soft.
- **swapA/r3soft finished (2026-10-31 05:35): 44 open on 34 nets** (route_check PASS, 0 violations; rip 3, soft 0.5,
  name order, seeded from `swapA/short.dedup.json`, 48 open). Closes CHAN14 CHAN3 CLK-12M-FPGA FLASH-CS# FLASH-D00
  FPGA-TMS GND GNDADC SD-DAT1 SD-DAT3 VCC1V8, loses AIN15_P AIN16_P CHAN-CLK CHAN16 CHAN19 CHAN20 CLK-12M-SHARED
  LED0_R RST# UART_FT_DTR# VCC1V0 VCCADC; GND ties closed by the pass, the four VCC3V3 ties not.
- **swapA/r2soft finished (2026-10-31 05:40): 44 open on 33 nets** (route_check PASS, 0 violations; rip 3, soft 0.5,
  name order, seeded from `swapA/plain.dedup.json`, 49 open). Closes AIN15_P AIN16_N CFG-M2 CHAN2 CLK-12M-FPGA
  FLASH-CS# FPGA-TCK GND GNDADC LED0_R LED1 SD-DAT0 SD-DAT1 UART_FT_CTS# VCC1V8, loses AIN15_N ANALOG-IO0 ANALOG-IO1
  BTN CHAN18 CHAN3 FLASH-D00 LED2 SD-CMD SD-DAT2 SD-DAT3 UART_FT_TXD VCC1V0; same tie picture. Both beat swapA's 48,
  so both get the tie repair (`swapA/tie_r3soft`, `swapA/tie_r2soft`; expected 40 each, since only the four VCC3V3
  ties are left to add). All six swap passes are in: swapA short 48 / r2short 49 / r2soft 44 / r3soft 44, swapB
  short 42 / plain 47 / soft 47. Only corner/soft still runs.
- **corner/soft finished (2026-10-31 05:42): 55 open on 41 nets** (route_check PASS, 0 violations; rip 3, soft 0.5,
  name order, same 52-open corner seed). Same story as corner/short: A7 closes once the neighbouring stubs are
  rippable (plus AIN15_P CFG-M2 CHAN15 CHAN2 CHAN22 FLASH-CS# FLASH-D02 FLASH-D03 GND LED0_R UART_FT_CTS# VCC1V0
  VCC3V3), but the bus is torn and not re-fitted (A2 A8 BS0 D6 WE# lost, plus ANALOG-IO0 CHAN-CLK CHAN16 CHAN21
  CHAN3 CLK-12M-SHARED FPGA-TMS LED2 NODE_P1 SD-CMD VCC1V8 VCCADC). The corner experiment is closed: not a
  candidate, but the stub-wall diagnosis for A7 (and LDQM in corner/short) is confirmed. **All eight stage-5 passes
  are finished**; results: swapA short 48 / r2short 49 / r2soft 44 / r3soft 44, swapB short 42 / plain 47 / soft 47,
  corner short 54 (FAIL) / soft 55. Pending: the tie repairs of swapA r3soft and r2soft.
- **Tie repair on swapA/r3soft: 40 open on 33 nets** (`swapA/tie_r3soft/final.json`, route_check PASS, stages
  46 / 45 / 41 / 41 / 40, 12 min, no bus net lost) -- the expected -4, two behind the swapB result (38).
- **Tie repair on swapA/r2soft: 40 open on 32 nets** (`swapA/tie_r2soft/final.json`, route_check PASS, stages
  46 / 45 / 41 / 41 / 40). **Stage 5 is complete (2026-10-31 05:45)**; after the tie repair the candidates are
  swapB/short 38 (best, `tools/route/stage5/tie38_swapB.json`), swapA r2soft 40, swapA r3soft 40, swapA short 42.
  Six finishing passes on two swap models span 42-49 before ties, each trading one open set for another, so the
  finishing passes have plateaued. What the 38 still holds: the five fan-out-sealed balls (A5 A7 D1 D3 LDQM; the
  corner passes show A7 and LDQM open as soon as the walling stubs move, so a *local* stub cut-and-reroute in the
  tie_repair style with the bus held fixed is the next lever), D2, SDRAM-CS#, the configuration/JTAG group, flash,
  SD, four CHANs, CLK-12M-SHARED, BTN, LED0_G/R, the UART pair, GNDADC, VCC1V0.
- **Walls of the five sealed balls on the 38 plan** (`pocket_walls.py` on `swapB/tie_short`, `scratchpad/walls38_*.log`,
  2026-10-31): every one is a Top-only pocket with no via site, walled by *model* copper, i.e. stage-1 stubs --
  A5 (R2, 475 cells): VCC3V3 107, A7 82, GND 21, A4 20, A2 18; A7 (P1, 195): A5 134, GND 122; D1 (V7, 628): D2 100,
  AIN16_P 53, VCC3V3 45, D3 25, SD-CMD 21, D0 19; D3 (W6, 292): VCC3V3 93, D1 66, D2 57, AIN16_P 53; LDQM (W4, 58):
  WE# 43, D6 41 (D6 partly plan copper). The stub repair therefore means moving the A5/A7 pair's own stubs (they wall
  each other), one of D0/D2 for D1, D2 for D3, and WE# or D6 for LDQM, with each displaced net re-routed locally
  (tie_repair style, --rip 0, bus held fixed).

## Stage 5 placed: the 38-open plan is on the board (2026-10-31, user's call "Place 38 now")

- **Schematic**: `apply_pin_swap.py` with `tools/route/stage5/swapA_perm.json` (1668 + 36 U1 pin records over 12 balls)
  then `swapB_perm.json` (834 + 18 over 6 balls), Altium closed; `check_feather_schematic.py --perm swapA_perm.json
  --perm swapB_perm.json` PASS (136 named nets, 0 mismatches). `make_xdc.py` regenerated `vivado/asar_feather_pins.xdc`
  (82 pins checked; it takes each ball from the schematic netlist, so the swaps carry through: CHAN2 C17, CHAN15 R19,
  CHAN18 W15, CHAN14 J19, CHAN17 B15, CHAN4 C15).
- **ECO** (Design > Import Changes): 11 pin removals + 11 additions on U1 (SD-DAT3 A16>W16, CHAN2 A17>C17, SD-DAT1
  B15>H19, SD-DAT0 C15>W18, CHAN4 C17>C15, SD-DAT2 L3>P17, LED0_R P17>L3, CHAN17 V15>B15, CHAN18 W13>W15, CHAN15 W15>R19,
  CHAN14 W16>J19), the 10 net-class removals and the USB differential pair unticked. All green.
- **Copper**: `FeatherClearCopper3.pas` removed 1112 vias / 3783 tracks (stages 1/3/4); `emit_copper.py` scripts
  `FeatherCopper_Stage1SwapB` (swapB's stage1: 271 vias, 975 tracks), `FeatherCopper_Tie38A` (562 / 2395, removes the
  A8 L4 stub) and `FeatherCopper_Tie38B` (470 / 1969) -- the plan was split into two chunks (`tie38_swapB_a/b.json`)
  to stay near stage 4's script size; no missing nets. stage3_sdram.json NOT emitted (the bus is inside the plan).
- **Microvias**: `stage13_mark_microvias.py --expect 875` marked 875 of 875 (Top>L2 255, L2>L3 245, L4>L5 192,
  L5>Bottom 183).
- **DRC** (`docs/drc_stage5.drc`, after Repour All): first run 109 = 38 Un-Routed + 69 Net Antennae + 2 Hole To Hole
  (the stage-4 artefact again: VCC3V3 through via + L4>L5>Bottom microvia stack at 34.95,12.425). `FeatherFixStage5.pas`
  removed the two microvias and `tools/route/stage5/fix_stage5.py` trimmed them from the plan files (1030 vias). Second
  run: **107 = 38 Un-Routed + 69 Net Antennae, nothing else**. The 38 are exactly the plan's open set (A5 A7 BTN CFG-M0
  CFG-M1 CHAN16 CHAN18 CHAN20 CHAN22 CLK-12M-SHARED x2 D1 D2 D3 FLASH-CS# FLASH-D00 FLASH-D01 FLASH-D03 x2 FPGA-TCK x2
  FPGA-TDI FPGA-TDO GNDADC x2 LDQM LED0_G LED0_R RST# SD-CLK SD-CMD SD-DAT1 SD-DAT3 SDRAM-CS# UART_FT_CTS# x2
  UART_FT_DTR# VCC1V0); the antennae are the open nets' stubs.
- **Verify**: `verify_copper.py swapB_stage1.json tie38_swapB.json` PASS: 1301/1301 vias, 5338/5338 tracks, nothing
  missing or extra. Model re-dumped (`board_dump.py`, `route_model.py`): 821 pads, 5338 tracks, 1301 vias, the swapped
  balls carry their new nets, open 38 on 33 nets. Board md5 d0bdb7d0 (saved after the DRC; copper identical to the
  verified a6aa6192 save). Board went 57 -> 38 open. Not committed.

## Stage 6 -- the five stub-walled balls (2026-10-31, user: "Start the five-ball stub repair")

Base: the ed2677b board model (`tools/route/model.json`, 38 open). Work dir `%LOCALAPPDATA%/Temp/routing/s6`.
- **Dead stubs**: the six sealed balls' Top-only stage-1 stubs (A5 5 tracks, A7 4, D1 2, D2 1, D3 1, SDRAM-CS# 1; LDQM
  has none) are dead copper that walls the neighbours. `tools/route/stage6/dead_stubs.json` lists them (a router
  `--remove` file, carried into every plan's `remove`); `model_nostub.json` is the model without them.
- **Pockets without the stubs** (`scratchpad/walls6_*.log`): A7, D2, D3, SDRAM-CS# open into thousands of cells with
  via sites; A5 opens only at slack 0 (its lane sits exactly at the rule); D1 (V7) stays a 432-cell Top pocket with
  no via site; LDQM (W4) 58 cells walled by WE# 43 / D6 41. The U3 ends: J2 (A5) and H2 (A7) wide open; B9 (D1) a
  685-cell Top pocket walled by the bus (A1 93, D2 60, A2 32, D4 29); E8 (LDQM) open.
- **Seven corner nets on the stub-free model, every order, 1.5M-3M pops, slack 0.005 and 0: 0 of 7 routed** (v_name,
  v_short, v_y, v_short3M, v_short_sd, v_short_s0, each route_check PASS at 38). Open pockets at both ends do not
  connect: the corridor between U1's east edge and U3's north-west corner is full of bus copper.
- **Why U1's field has no via sites**: the interstitial centres (x.15/x.65, y.18/y.68) give exactly 0.0915 mm to
  the four 0.225 lands (rule 0.09) and are off the 0.025 grid in y, so a Top>L2 microvia never fits; the stage-1
  dogbones use buried L3>L4 vias (no Top land) at y.13/y.83 instead. Via-in-pad stacks (kind stack_top at the ball
  centre) collide on L3 with the copper already under the balls: V7 (CHAN20 track, -0.088), B9 (D5 via/track), R2
  (A1 track, -0.070) -- and did not route anyway.
- **tools/knot.py** (generic tie_repair: `net_seed.py` moves the cut nets' copper into a rippable seed, `tie_cut.py`
  cuts around the sites, ordered `--rip 0` passes, route_check each stage) and **tools/net_seed.py** are new.
  `diagnose_open.py --nets` filters the diagnosis.
- **LDQM**: cuts of WE#/D6 at 0.5/0.7/0.9/2.0 mm free W4 completely yet LDQM fails; diagnosis = congestion (it routes
  when WE# and D6 are absent). Removing both entirely: LDQM closes, WE# re-routes, **D6 does not** (both orders end at
  38 with D6 swapped for LDQM). Removing only D6: LDQM closes (`ldqm_d6`); D6's re-route and two wide-window
  (margin 8, 3M pops) D6 retries are running.
- **D1**: diagnosis = fixed copper. Cuts of D0, SD-CMD, the U6 GND strap, the CHAN22 via, LED0_G's via and the bus
  around B9 (A1/A2/D4/D0 at 0.5-0.7 mm) in every combination leave D1 open while the cut nets re-join cleanly
  (d1_a..h all end at 38). The C109 decap (VCC3V3/GND 0201 between rows V and W at x 25.83/26.43) sits on V7's two
  northern via sites; moving it is the remaining local lever, not tried.
- **Negotiated corner re-route** (`router.py --negotiate 40`, tools/negotiate.py) launched on two groups with their
  copper removed from the model: G1 = the 7 + A1 A2 A4 A6 A8 A10 A11 A12 D0 D4 D5 D6 D7 WE# RAS# CAS# BS0 BS1 (25
  nets, 707 tracks / 116 vias out), G2 = the 7 + A1 A2 A4 A6 D0 D4 D6 WE# (15 nets); `negG1/short`, `negG1/name`,
  `negG2/short`. The board chain for any plan from here must delete `negG*/dropped.json` (the group's stage-1 stubs
  included) before placing.
- **Diagnosis of the six** (`diagnose_open.py --nets`, 3M pops, board-wide windows, stub-free model): A5 A7 D2 D3 LDQM
  SDRAM-CS# are all "fixed copper" -- routable with the pads alone, walled by the model's copper. Only the
  negotiated group re-route (which takes that copper out) can move them; LDQM-only knots are a swap with D6.
- **Single nets on the bus-free model** (`negG1/one_*.json`, the 18 corner bus nets removed = 56 open): A5 (slack 0),
  A7, SDRAM-CS#, LDQM, D3, D2 each route alone; D1 never does (B9/V7 stays sealed by non-bus copper).
- **Sequential knots** (`knot.py`, `sites_all99.json` = the 18 bus nets cut entirely, `--rip 0` stages, margin 4,
  1.5M pops): seqA/seqB (A5:0 > A7 > CS# > LDQM > D3 > D2 > D1) close six of the seven, 56 -> 50; seqD (D1 first)
  closes the other five (D1 fails first, 56 -> 51). **seqA's bus stage** (all 18 bus nets back, --rip 0)
  re-routes 11 and loses BS1 D0 D4 D6 D7 RAS# WE#: **39 on 34 nets, route_check PASS** -- one worse than the board.
  `negG2/short` (15 nets negotiated) also ends at 39. The corner's capacity, not the order, is the wall so far.
- **Retries running** (`retry/`, 3M pops, margin 8): the 7 lost nets on seqA's bus stage (orders name/short/y and a
  `--rip 3` pass), the 18 bus nets on seqA's st7 in the other orders and with `--rip 2`, and two bus-first knots
  (seqE name / seqF short: bus first, then the sealed six). `router.py` now logs `FAIL net (budget|nopath)`;
  `knot.py --reuse <dir>` re-runs other stage orders on an existing cut; `tools/plan_open.py` lists a plan's open
  nets. A computer restart killed seqB/seqD's bus stage and the negG1 runs (not relaunched: negG2 covers them).
- **Board chain for a knot result**: `tools/knot_full.py <knot dir> <plan> <out>` rewrites a knot plan for the full
  model (the moved copper of `dropped.json` goes into `remove` / `remove_vias`); `route_check.py`, `plan_open.py` and
  `emit_copper.py` now honour `remove_vias` (net, x, y, hole; a board via is deleted once even when a stacked column
  shares the point). Proven on seqA: `seqA/final_full.json` against `tools/route/model.json` = 39, PASS.
- **Corridor lanes are not the wall** (`tools/corridor.py`, cut lines with every copper + clearance): on the seqA plan
  the escape edges of U1 (x 29.25 east, y 16.25 south, the corner band) still hold 3-14 free lanes per layer and the
  mid-corridor (x 30.3) 8-10 per layer, yet seven bus nets fail. The binding resource is inside U1's field (via
  sites and ball escapes), as on Zulu A7.

## Stage 7 -- via-in-pad laser microvias on U1 (2026-10-31, user: "go ahead with the via-in-pad laser microvias on U1")

Why: forty-odd stage-5/6 runs plateau at 38-39 open; `corridor.py` shows free lanes everywhere outside U1; every
open net is a U1 net; the field's escape capacity (interstitial via sites + Top necks) is the wall. A laser via in
every netted ball removes it: the ball leaves on L3 at its own position, rings 3-5 (vacant) take the buried
L3>L4 vias to leave the field on L4.
- **Fab assumption** (PCBWay's published floor, docs/pcbway_vip_enquiry.md is the draft to send): laser 0.10 mm
  hole / 0.25 mm land (0.075 ring), filled and capped; the U1 lands must grow 0.225 -> 0.25 on the board (no Top
  neck between netted balls afterwards; none is needed). Laser-to-plane clearance 0.15 keeps an L2 web.
- **`tools/vip_fanout.py`** -> `tools/route/stage7/`: `model_bare.json` (the board with every track and via removed),
  `vip.json` (410 via objects on 211 balls: 68 GND Top>L2, 28 VCC3V3 Top..L5 columns, 115 signal Top>L2>L3
  stacks), `model_vip.json` (bare + columns). route_check on the bare board: **0 violations, PASS**; the columns
  close the 96 U1 plane ties (595 -> 499 open on 153 nets).
- **Global routes from the columns** (`%LOCALAPPDATA%/Temp/routing/s7`, 1.5M pops, `--rip 2`): `g_name`, `g_short`,
  `g_y` (all nets), and `s_sdram` (39 SDRAM nets with `route/sdram_layers.json`, y order, margin 7) followed by
  `s_rest` seeded on it. Running.
- Still to do when a plan wins: U1 lands 0.25 on the board (footprint + placed pads), a 0.10/0.25 laser via type
  and rules (Routing Via Style, Hole Size + Annular Ring `IsMicroVia`, Hole-to-Hole with stacked allowed, plane
  clearance for laser holes), `stage13_mark_microvias.py` extended to 0.25/0.10 (it matches 0.30/0.15 only), then
  the chain: clear all routing copper -> place vip.json + the plan -> mark microvias -> DRC -> verify_copper.
- Stage 6 side result: seqE/seqF (bus first, then the sealed six) are worse at their first stage (41 / 45 open) and
  seqE died on an A5 slack-0 lane 0.0981 from A1 (route_check FAIL). The seven lost-bus-net retries are still
  running; any result below 38 is a bonus, not the path to zero.
- **Plane web under the rings (design consequence, not modelled)**: a 0.25 land on L2 at 0.5 mm pitch with the
  0.09 polygon clearance leaves a 0.07 mm GND web between netted balls, below 3 mil -- the L2 pour under rings 0-2
  becomes a mesh with slivers or, with neck removal, a perforated band 1.5 mm wide. L5 is untouched except under the
  28 VCC3V3 columns. Standard via-in-pad compromise on a 6-layer 0.5 mm BGA; PCBWay's minimum plane web is asked
  in the enquiry. `vip_fanout.py --land 0.25` writes the models with the enlarged U1 lands for the final check
  (`s7/land25/`); the running routes use 0.225 pads with 0.25 via lands (0.0125 mm optimistic next to the 27
  no-net balls only).

### Stage 7 result (2026-11-01): the all-to-L3 columns are a trap; layer-per-ring columns replace them

- The three global routes finished after 18 h: g_name **36** open / g_short **34** / g_y **44** (route_check PASS each;
  the board is 38). Not a win. The staged SDRAM-first run was stopped (same flawed model). Stage 6's last retries
  finished at 38-43 -- that lever is closed for good.
- **Why so little** (`s7/diag`): AIN16_N and LED1 fail *alone on the bare via-in-pad board* ("nopath"), and the
  SDRAM "budget" failures are the same thing with a bigger pocket. A laser stack at every signal ball puts a
  0.25 mm land on L3 at every ball of rings 0-2, so a ring-1/2 ball is fenced on L3 exactly as on Top: the gap
  between adjacent lands is 0.25 mm and a 0.0762 track needs 0.256 with 0.09 clearance. The only L3 exits are
  chains of GND / no-net sites (GND stacks stop at L2). Geometry, not congestion.
- Dead ends checked before the fix: (a) 0.225/0.075 lasers (lands unchanged): the Top necks between 0.225 lands
  exist exactly (0.019 mm slack) but the 0.025 mm raster cannot represent them (INFL 0.018 + 0.09 leaves the
  midpoint cell 0.030 < 0.043 needed) -- the production necks were placed exactly by hand, never by this router;
  (b) interstitial laser + buried L3>L4 column: the buried 0.15 hole is 0.2411 from the ball lasers' 0.075 holes
  exactly (rule 0.24) and 0.2375 once snapped to the grid (U1 sits 0.005 mm off the y grid) -- not usable.
- **The right via-in-pad**: `vip_fanout.py --scheme rings` -- ring 0 (36 signal balls) keeps a bare pad and leaves on
  Top; ring 1 (35) gets Top>L2>L3 and leaves on L3 where ring 0 has no land; ring 2 (34) and the 10 core power
  balls get Top>L2>L3 + buried L3>L4 and leave on L4 where rings 0-1 have nothing; GND 68 Top>L2, VCC3V3 28 full
  columns as before. 382 via objects, route_check PASS on the bare board, 499 open from scratch (same as before).
  Alone on it: AIN16_N routes, A8 (ring 2) routes, LED1 needs more than 400k pops (3M retry running) -- the pocket
  is gone.
- Two models, both running two global routes (short/name orders, 1.5M pops, rip 2, slack 0.005):
  `s7/v3a` = laser 0.25/0.10 with U1 lands grown to 0.25 (PCBWay's published floor; router `--laser-small 0.25/0.10`);
  `s7/v3b` = laser 0.225/0.075, lands unchanged (0.075 drill is "on evaluation"; `--laser-small 0.225/0.075`).
- Tool changes: `router.py --laser S/H` (replace the standard 0.30/0.15 laser), `--laser-small S/H` (adds a second
  laser family `*_s`, +0.3 via cost, also in the plane tie lists), hole-to-hole raster safety 0.005 -> 0.001;
  `vip_fanout.py --laser S/H --scheme rings`. Board to-do for v3a adds the 0.25 lands; for v3b only the rules change
  (HoleSize/RoutingVias IsMicroVia 0.075..0.15, land 0.225..0.30). FeatherVip.pas still encodes the old 0.25 plan.

**Paused 2026-11-01 16:46 for a reboot.** LED1 routes alone with 3M pops (2 vias, 15 tracks): the sealed-net
proof is complete on the ring scheme. The four global runs were stopped cleanly at their per-net checkpoints
(v3a short 51 nets queued / name 59; v3b short 83 / name 65, of 154) and resume with
`bash "$LOCALAPPDATA/Temp/routing/s7/resume.sh"` (each run seeds from its checkpoint copy, appends to its log).

**Stage 7 ring-scheme results (2026-11-02 07:20, resumed after the reboot, route_check arbiter):**
v3a (0.25/0.10, U1 lands 0.25) short **25** on 24 nets, name 27; v3b (0.225/0.075, lands 0.225) short 26, name 27.
Board 38, old all-to-L3 model 34. Survivors common to every run: SDRAM data (D0/D3/D5/D6/D10), SDRAM-CS#/CLK,
CHAN-CLK, flash CS#/D00/D02/D03, JTAG TDI/TDO/TMS, LED2, UART_FT_CTS#, PUDC_B, CFG-M0; mostly `budget`, a few
`nopath` (PUDC_B, JTAG, LED1/LED2, BTN, D15 in v3b short). Nothing placed. Next: diagnose_open on both short plans,
seeded finishing passes (rip 3, 3M pops), corridor analysis.

- **Diagnosis of v3a short's 25** (`diagnose_open.py --laser-small 0.25/0.10`, 1.5M pops): **23 congestion, 2
  routable (budget)**, none placement- or fixed-copper-sealed -- every survivor routes alone on the pads and on the
  via-in-pad model; only the other nets' copper blocks it. Corridors are open (cut x=30.3: 34/25/12/17 free lanes
  Top/L3/L4/Bottom; cut y=16.4: 22/29/18/38). Running: seeded finishing passes (`fin_short`, rip 3, 3M pops, both
  variants) and keystone-first chains (`keystone.sh`: the union of all four runs' survivors -- 40 nets on v3a, 44 on
  v3b -- routed first on the bare model with rip 2 / 3M pops, then the rest seeded; k1_*/k2_* in v3a and v3b).
  `diagnose_open.py` gained `--laser-small`.

- **Keystone-first chains (2026-11-03 04:26)**: k2 = 27 (v3a short), **23** (v3a name), 26 (v3b short). Stage 1 alone
  -- the 40/44 hard nets on the otherwise EMPTY board, rip 2, 3M pops -- already fails 6 / 5 / 11 of them (v3a short:
  LDQM D3 CAS# SDRAM-CS# CHAN20 CFG-M0; name: CAS# D0 D2 D6 FPGA-TDI), so the hard set conflicts with itself.
  Geometry (`s7/u1_balls.json`): 13 SDRAM nets sit on U1's y=15.93 row, east half (W2-W7, V3-V8, U4, U5: D0-D7,
  LDQM, CAS#, RAS#, WE#, CS#) and must turn U1's NE corner (x 28.9, y 15.93) to reach U3's top rows (y 13-14.6);
  the east column already carries 26 SDRAM + 4 XADC + LED0_R; no spare I/O ball exists (80 permutable, 18 fixed).
  Running (`iso.sh`, v3a, rip 2, 3M pops): the 24 corner SDRAM nets alone, all 39 SDRAM alone, SDRAM + 18 fixed.

**Isolation runs (2026-11-03 06:11-06:53, v3a, rip 2, 3M pops, short):** the 24 corner nets ALONE on the empty
model fail 4 (`iso_corner`: D3 W6, D4 U5, SDRAM-CS# W2, D6 V5 -- nopath/nopath/budget/nopath); all 39 SDRAM alone
fail 3 (D4, SDRAM-CS#, D6); SDRAM + the 18 fixed nets fail 7 (D3 D5 SDRAM-CS# LDQM CFG-M0 D7 RAS#). **U1's NE corner
is over capacity by itself** -- the conflict is not with the fixed config/JTAG nets. The v3b finishing pass (rip 3,
3M) ends at 24 open (from 26); v3a's is still running. In `iso_corner.json` the router itself lays laser stacks at
ring-0 balls (CAS# at 27.98,15.9) and THROUGH vias in the Top band north of row W (D2 25.88,16.1; D1 27.4,16.32),
each one sealing every layer around it; lanes across the gap are plentiful (cut x=29.3: 17/20/26/27 free), so the wall
is the simultaneous escape from rows U-W x columns 1-8. Geometry: the Top band between row W's lands and the pull-up
pads R20/R6/R7 (y 16.72) is 0.6 mm = 3 outer lanes for six Top-only SDRAM balls W2-W7 (+ CFG-M1, SD-DAT0/3 going
east); the Bottom of the U1-U3 gap is blocked for y 12.95-16.55 by C141/C143 (VCC1V0 0603s at x 30.9/32.6).

Experiments launched 06:55 (`s7/exp/iso_exp.sh`, 8 router processes, same 24-net corner protocol):
order sensitivity on v3a (`o_name`, `o_y`, `o_neg` = --negotiate 30, `o_key` = the four failures first, then the
rest seeded) and four model variants built by `s7/exp/build_variants.py`, each proven with route_check (vip.json on
model_bare.json PASS): `v1_pullups` (R6 R7 R20 R23 R21 +1.5 mm north: Top band 0.6 -> 2.1 mm), `v2_northvip`
(row W Top>L2>L3, row V + buried = L4, row U full column to Bottom; rings elsewhere; 448 vias), `v3_both`,
`v4_nocaps` (C141 C143 C7 C8 removed: upper bound of the Bottom-gap lever). A proposal workflow (three lenses:
placement / via scheme / pin permutation, each adversarially refuted on legality and mechanism) runs alongside;
facts brief in `s7/exp/FACTS.md`. Nothing on the board.

**Order sensitivity (2026-11-03, first results):** the same 24 corner nets on the same v3a model: `--order short`
4 fail, `--order name` 3 (CAS# budget, D3 nopath, SDRAM-CS# budget), **`--order y` 1 (RAS#, budget)**; the four
failures routed first (`o_key1`) go 4/4. So the corner is simultaneity- and order-limited, not hard-capacity-
limited; a RAS# retry seeded from `o_y.json` with 8M pops (`o_y_fin`) and a global `--order y` run (`g_y`, 1.5M
pops) are running. The v3a rip-3 finishing pass lost ground (28 open). Workflow proposals, all route_check PASS,
now routing in `s7/exp/` (short and y orders): `p_band_clear` (R20 R6 R7 R23 R21 moved to a row at y 19.7 north
of U3, x 30.5-36.9, leaving 4.6 mm of empty Top above row W; sub-variant `plus_caps` also moves C141/C143 under
U1's VCC1V0 core at y 10.6), `p_w_holes` (17 extra via objects: Top>L2>L3 at W3/W15/W16/W18, Top>L2>L3+L3>L4 at
W5/W6/W7, nothing else), `p_perm_a` (30-ball re-pin: W6/W7/U3 vacated, SD-CMD/SD-CLK/LED0_R to bank-14 balls,
SDRAM data in planar order; perm.json + xdc_edits.txt in its folder; legality still to be refuted).

**Corner levers measured (2026-11-03 10:40):** every corner isolation (24 nets, rip 2, 3M pops) is in except the
proposal runs. Unchanged v3a: short 20/24, name 21, y 23 (RAS# budget); `o_key` stage 2 (the four seeded, then the
rest) 16/20 (CAS# nopath, RAS# WE# D5 budget); `o_neg` (--negotiate 30) stalled at 4217 shared cells after 18
iterations. Variants: `v1_pullups` 20 (the SAME four, rip log byte-identical to `iso_corner`), `v2_northvip` 22
(BS0 budget, D5 nopath), `v3_both` 22 (md5-identical plan to v2 -- the pull-up move changes nothing once row W is
on L3), `v4_nocaps` 20. **`p_perm_a` (U1-side re-pin) 24/24 in short order, 30 vias, 766 tracks, route_check PASS,
0 violations** -- the only lever measured above the unchanged board. Workflow verdicts (journal of
wf_ddf16187-102): p_band_clear and p_w_holes pass legality but their MECHANISM is refuted -- the Top band is not the
binding resource (o_y put more copper in the band than iso_corner and still routed the four; v1_pullups with 22-25
free band lanes repeats the four); the four die inside U1's land field, boxed by the router's own L4>L5>Bottom
stacks / buried vias / ball-edge lasers between rows T and W, and each layer group's lane order is reversed relative
to U3's pad order by the control nets fixed at W2/W3/W4 and V2/V3/V4 -- which only a U1-side move can change.
p_perm_a's legality refuter: not refuted (pure permutation, all moves swap_rules.legal, non-U1 pads identical --
re-verified here for p_perm_a, x_perm_b and x_perm_min). Synthesis: the single lever expected to win is
`exp/x_perm_b` = p_perm_a minus the A5<->A9 (R2/N2) swap (24 XDC lines, 28 balls re-netted, vip 387 vias PASS);
`exp/x_perm_min` = the 19-line minimum that keeps the planar order (W2 D3, W3 D5, W4 CAS#, W5 SDRAM-CS#, W6 A10,
W7 empty; V2 D0, V3 D6, V4 RAS#, V5 WE#, V7 BS0, V8 BS1; U1 D1, U3 empty, U4 D2, U7 D7, U8 LDQM; U2 A2, T2 A0;
V16 SD-CMD, V17 SD-CLK; 383 vias PASS); `exp/x_nobot` = unchanged pinout + a netless Bottom keepout over U1's NE
field (x 25.1-29.2, y 13.7-16.6; the zero-ECO control of the "router-made knot" hypothesis). Launched 10:40
(`exp/x_corner.sh`, `exp/x_global.sh`): x_perm_b tier 2 (39 SDRAM, v3a 36/39) and tier 3 (SDRAM + 18 fixed, v3a
50/57), x_perm_min short + y, x_nobot short + y, and the GLOBAL short-order route on x_perm_b (1.5M pops, the long
pole). Correction: `g_y` (global y order on v3a) is NOT finished -- 21 of 154 nets routed at 10:35; the synthesis
agent's "44 failed" was wrong. 18 router processes alive. Nothing on the board, enquiry unsent, nothing committed.
`o_y_fin` (RAS# retry seeded from o_y, 8M pops, 11:0x): ripped 9 nets and ended at 22/24 (D5 and RAS# nopath) --
the unchanged pinout tops out at o_y's 23/24; more budget does not close the corner.
`o_neg` (--negotiate 30) finished at 22/24 (LDQM, WE# budget; 73 vias, 1469 tracks). First-batch summary on the
unchanged pinout, all orders and strategies: 20 / 21 / 22 / 23 of 24, never 24.

**Proposal isolations finished (2026-11-03 ~11:30, 24 corner nets, short / y order):** `p_band_clear` 20 / 23 (the
baseline's own numbers: D3 D4 SDRAM-CS# D6 / RAS#), `plus_caps` 20 / 21, `p_w_holes` 22 / 21, `alt_l3` 18,
**`p_perm_a` 24 / 21 (y order fails D2 nopath, D3 nopath, SDRAM-CS# budget)**. So the re-pin's 24/24 is a
single-order result, not a robust closure: every model is order-sensitive, and the re-pin raises the best-of-orders
from 23 to 24 while its worst order (21) is no better than the baseline's. What decides is a complete GLOBAL plan,
and any order that yields one is acceptable, so the corner plan that closed (`p_perm_a/iso.json`, 30 vias, 766
tracks, route_check PASS on the x_perm_b model too) is now used as a keystone seed for a global route on x_perm_b
(`g_seed`: --seed iso.json, short order, 1.5M pops) alongside the unseeded g_short / g_y; `iso_name` (third order)
also launched. The Bottom-keepout control (`x_nobot`) and the 19-line `x_perm_min` are still routing.

**Re-pin tiers (2026-11-03 ~12:00):** on `x_perm_b` the 24 corner nets close in NAME order too (24/24, 36 vias,
613 tracks) -- so short 24 / name 24 / y 21 -- and **tier 2, all 39 SDRAM nets alone, closes 39/39** (63 vias, 1059
tracks; the unchanged pinout gave 36/39). The 19-line `x_perm_min` closes the corner 24/24 in short order (30 vias,
779 tracks). The Bottom-keepout control `x_nobot` in y order repeats the baseline's 23/24 (RAS#), so forbidding the
router's Bottom drops under U1's NE field is not the lever. Still running: x_perm_b tier 3 (57), g_short, g_y,
g_seed; x_perm_min y; x_nobot short; v3a g_y.
Tier 3 on x_perm_b (SDRAM + 18 fixed nets, short, 16:3x): 58 of 66 connections, 8 FAIL (FLASH-D02, A5, CKE,
SDRAM-CLK, CFG-M1 nopath, D3, D5, SDRAM-CS#) -- the fixed config/flash nets re-enter the conflict once the corner
is re-pinned (A10's Top lane between R6 and R21/R23 walls R6-1/R7-1 off, as the synthesis warned). `x_perm_min` y
order 19/24 (worse than its short 24), `x_nobot` short 19/24. Globals at 16:37: x_perm_b g_short 151 net lines /
8 rips, g_y 143 / 15, g_seed 118 / 10; v3a g_y 161 / 17.

**First global on the re-pin (2026-11-04 01:25):** `x_perm_b/g_seed` (seeded with the 24/24 corner plan, short,
1.5M pops) = **25 open on 23 nets** -- the same plateau as the unchanged pinout's best (v3a short 25). The seed
itself was ripped (D6 nopath, SDRAM-CS#, BS0, BS1 budget) and the non-corner knot is the rest: AIN16_N/P nopath x2
each, FPGA-TDI/TDO/TMS nopath, CFG-M1 nopath, LED0_R nopath, plus budget failures on D8 A2 A5 UDQM SDRAM-CLK
CHAN18-21 CHAN-CLK UART_FT_CTS# SD-CLK. The corner lever does not move the global number. g_short / g_y on x_perm_b
and v3a g_y are in their rip phase.

## 3 mil clearance -- the lanes between U1's lands (2026-11-04)

Reading the raster code while the re-pin globals ran: a lane cell is free when the distance to the nearest painted
foreign pixel is >= width/2 + clearance + slack. U1's 0.25 lands at 0.5 pitch paint out to 0.125 from their centres
on the 0.025 grid, so the midline between two lands has 0.125 free: 0.0381 + 0.09 + 0.005 = 0.133 > 0.125 blocks it
(the "U1 is a wall" of every stage since 7), while **0.0381 + 0.0762 + 0.005 = 0.119 <= 0.125 opens it** -- a
3 mil Clearance rule (exact geometry: 0.0869 between a 3 mil track and the land edge) turns the whole 236-ball field
into a sieve on Top. Probe (`Router.dist` on v3a, CHAN0 and D3): with clearance 0.09 the Top lanes between columns /
rows are 55-91 % free (broken by the lands); with 0.0762 they are **100 % free on all 18 columns and rows**, for
SDRAM nets too (their 0.10 clearance is inner-only). On L3/L4 the ring-1 laser lands (0.25) open the same way for
non-SDRAM nets (81-100 %); the buried 0.27 lands of ring >= 2 do not (exact margin 0.0007 mm) and SDRAM's inner
0.1/0.10 rules keep L3/L4 closed for the bus. Fab: 3/3 mil is on PCBWay's order form (docs/x1_slot_fix.md) and
already in the enquiry draft; it is a user/fab decision, so this is MEASURED, not applied.
Tooling (uncommitted): `router.py --clear X` and `--sdram-plain` (SDRAM nets at the default width/clearance),
`route_check.py --clear X / --sdram-plain` (judges the plan by the rules it was routed with; without the flag a
3 mil plan FAILs, as it should), `corridor.py clear=X sdram=plain`, `diagnose_open.py --clear/--sdram-plain`.
Smoke: D3 (W6, Top-only) alone at 3 mil routes on Top with 0 vias / 6 tracks, PASS at 0.0762, 11 violations at 0.09.
Launched (`s7/c3/`, v3a model, unchanged pinout): corner 24 in short / y / name, corner short with --sdram-plain,
tier 3 (57) short; globals g_short and g_y (1.5M pops). The x_perm_b g_short / g_y and v3a g_y continue.
`v3a/g_y` (global, y order, unchanged pinout, 0.09 rules) finished 01:45: **29 open on 27 nets** -- worse than
g_short's 25; the y order that helped the corner in isolation does not help globally (corner nets RAS# SDRAM-CS#
D0 D1 D4 D7 D8 A2 A3 A10 BS1 WE# SDRAM-CLK open, plus AIN15_N/AIN16_N x2, LED0_R, FPGA-INIT#, FLASH-CS#/D00, CFG-M0,
CHAN-CLK/3/19, GNDADC, SD-DAT0/2, UART_FT_RTS#). 0.09-rule series on the ring scheme: 25 / 27 / 29 / 36 (short,
name, y, fin). Only the 3 mil runs (`c3/`) and the x_perm_b g_short / g_y remain.
`x_perm_b/g_short` (global, short, re-pin, 0.09 rules) finished 02:37: **26 open on 23 nets** (corner nets WE# A8
A10 D5 D7 RAS# BS1 D4 D6 LDQM SDRAM-CS# all budget; FPGA-TDI/TDO nopath; LED1/LED2/D15/CFG-M0 nopath; VCC1V8 x4,
VCC1V0, CHAN16, UART_FT_DTR#/RTS#, FLASH-D03 budget). Re-pin globals so far: 25 (seeded) / 26 (short); the
re-pin is confirmed NOT to move the global plateau at the 0.09 rules. The 3 mil runs are the open question.
`x_perm_b/g_y` (global, y order, re-pin, 0.09 rules) finished 03:1x: **33 open** (466 routed) -- the worst re-pin
global. Re-pin series: 25 (seeded) / 26 (short) / 33 (y) against the unchanged pinout's 25 / 27 / 29 / 36. Closed:
the U1 re-pin is not a lever for the whole board and no ECO is justified by it.

**3 mil corner isolations (c3, unchanged pinout, 24 nets, rip 2, 3M pops, --clear 0.0762), finished ~03:10:**
short 21/24 (RAS# SDRAM-CS# WE# budget), y 19/24 (D3 D5 SDRAM-CS# budget, D0 LDQM nopath), name 21/24 (BS1
SDRAM-CS# budget, D4 nopath), short with --sdram-plain 20/24 (LDQM budget, CAS# D0 D4 nopath) -- against the 0.09
rules' 20 / 23 / 21. The 3 mil Top sieve does NOT close the corner: the corner knot is an inner-layer problem (the
four die between the router's own buried/laser stacks under rows T-W, where the 0.27 buried lands never open at any
clearance and the SDRAM inner rules keep L3/L4 at 0.1/0.10), and the plain-SDRAM variant that lifts those rules is
no better. The y order that was the baseline's best (23) is the 3 mil worst (19): the opened Top field widens the
search and the same 3M budget runs out sooner (every failure above but five is "budget"). Still running: iso_fixed
(57), g_short, g_y at 3 mil -- the global number is what matters for the non-SDRAM nets that CAN use the Top lanes.
`diagnose_open` on the 3 mil corner plans (c3/iso, iso_y, iso_name; --clear 0.0762, 1.5M pops): every corner
failure is **congestion** -- each open net routes on the bare pads and on the model's fixed copper, and fails only
with the plan's own 20-21 corner nets present (short: RAS# SDRAM-CS# WE#; y: D0 D3 D5 LDQM SDRAM-CS#; name: A2 BS1
D4 SDRAM-CS#). No placement or fixed-copper wall; the 24 nets do not fit the region simultaneously at any clearance.
Side finding: 3-4 VCC3V3 plane ties at U3's supply pads (x 31.8-35.0, y 13.0-14.6) are also "congestion" on every
corner plan -- the corner routes take the lanes those ties need, which a global route has to pay for too.
Launched 03:5x (`c3/more.sh`): corner y / short at 8M pops (the 3 mil failures are budget), and two more 3 mil
globals -- `g_plain` (short, --sdram-plain: SDRAM at 0.0762/0.0762 on the inner layers, a signal-integrity rule
change to decide only if it wins) and `g_name`. Seven router processes alive.
`c3/iso_fixed` (tier 3, SDRAM + 18 fixed nets, short, 3M pops, 3 mil) finished 07:2x: **57 of 66, 9 FAIL** (D5 BS0
CAS# LDQM BS1 SDRAM-CS# WE# budget, D0 D4 nopath -- all corner nets) against 59/66 at 0.09 and 58/66 on the re-pin.
Third tier in a row where 3 mil is no better than 0.09 for the SDRAM corner. At 07:31: g_short 133 nets / 6 rips,
g_y 141 / 8, g_plain 55 / 2, g_name 57 / 3, iso_y8 37 / 5, iso_s8 14 / 1.

**3 mil globals finished 15:2x (c3, unchanged pinout, ring scheme, 1.5M pops): `g_short` = 12 open on 11 nets**
(487 routed, 1044 vias, 4229 tracks; all 12 budget: WE# BS1 D2 D3 D5 D6 CAS#, AIN16_P, VCC1V0, FPGA-TCK, SD-DAT1 x2,
UART_FT_DTR#) -- **the first lever that moves the global number: 25 -> 12**. `g_y` = 24 (vs 29 at 0.09; many
nopath: AIN15_P/AIN16_P x2, FPGA-TDI/TDO/TMS, D0 D2 D8 D9 BS0, CLK-12M-FPGA). route_check at 0.0762 on g_short: 7
violations, all raster rounding at the limit (VU tracks on Bottom 0.0759 from GND pads, 0.0759 from EE-CS, a GND via
0.0756 from AIN16_P) -- so the ROUTING clearance has to carry a hair of margin: route at 0.077, judge at 0.0762
(0.0381 + 0.077 + 0.005 = 0.1201 still opens U1's lanes). The 8M-pop corner runs (`iso_y8` 19, `iso_s8` 21) produced
plans byte-equal in size to the 3M ones with the failures now "nopath": the corner in isolation is a real 24-net
congestion knot, not budget -- yet the global in short order routes 17 of the 24 corner nets, so isolation is the
wrong frame for it. Launched 15:3x (`c3/fin.sh`): `g_short_fin` (seeded with g_short, 8M pops, short, --clear
0.077), `g_s77` (fresh global, short, 0.077, the clean candidate), `diag_g_short` (12 open at 4M pops). g_plain
(218 net lines / 13 rips) and g_name (235 / 20) continue. DECISION FOR THE USER: 3/3 mil is a PCBWay order-form tier
and an Altium Clearance-rule change (0.0762 board-wide or a U1-region rule); nothing applied.
17:19: `g_plain` (3 mil, short, SDRAM inner rules lifted) = **13 open on 12 nets** (A2 A3 BS1 D3 D5 WE# CHAN19
FLASH-D02 budget; FPGA-DONE x2, FPGA-INIT#, FPGA-TDI/TDO nopath) -- no better than g_short's 12, so the SDRAM
inner rules stay (no signal-integrity change to decide). `g_name` = 21 on 18 nets. 3 mil series: **short 12 / plain
13 / name 21 / y 24** (0.09: 25 / 27 / 29). `diag_g_short` (4M pops): **11 of the 12 are congestion** with the
plan's own copper (the seven corner nets, AIN16_P, SD-DAT1 x2, UART_FT_DTR#), only FPGA-TCK is budget -- so the
seeded 8M finish can close them only through rip-up, not budget. The residue is 7/12 the SDRAM corner, which only
the U1 re-pin has ever closed (24/24, 39/39) while 3 mil is what moved everything else: launched 17:2x
(`exp/x_perm_b/c3.sh`) the combination -- `x_perm_b/g_s77` (re-pin, fresh, short, 0.077) and `x_perm_b/g_seed77`
(re-pin seeded with the 24/24 corner plan, 0.077) -- plus `c3/g_s77_3m` (unchanged pinout, 0.077, 3M pops). Still
running: `c3/g_short_fin` (11 nets / 3 rips), `c3/g_s77` (108 / 3). Five router processes.

**DECIDED by the user 2026-11-04 (evening): 3/3 mil.** The Feather is ordered at PCBWay's 3/3 mil tier and the
Altium Clearance rule goes to 0.0762 mm; routing runs at --clear 0.077 and plans are judged at 0.0762.
**3 mil APPLIED TO THE BOARD 2026-11-04 17:44** (`tools/FeatherRules3.pas` SetClearance3mil, run from its own
`FeatherRules3.PrjScr` via File > Run Script > Browse > From file): the rule named `Clearance` (All/All) went
0.0900 -> 0.0762 mm; Clearance_SDRAM_INNER 0.10, Clearance_SDRAM_CLK 0.20 and Clearance_Plane_ThruVia 0.175 untouched
(the script lists all four before and after). Then Tools > Polygon Pours > Repour All, DRC, File > Save. Verified
from the saved file (Rules6): `Clearance GAP=3mil GENERICCLEARANCE=3mil`, the other three unchanged. DRC
(`docs/drc_3mil.drc`, 17:43): **107 = 38 Un-Routed + 69 Net Antennae, 0 clearance** -- identical to stage 5's
107, as it must be (the board's copper was routed at 0.09). PcbDoc md5 391629d2 (was d0bdb7d0). The enquiry draft
got a question 7 on 3/3 mil against BGA / microvia lands and the 0.098 mm L2 webs (still NOT sent). Not committed.
Altium leg notes: the retry of open_application started a SECOND X2 instance (killed, PID by start time); Edge in
front blocks clicks -- `altium_drive.ps1 Activate` brings Altium forward; the on-screen-keyboard strip sat over the
DRC dialog's Run button, Alt+R pressed it; File menu: Up x11 = Run Script, Down x6 = Save; Tools: Down x6, Right,
Down x4 = Repour All; the window jumped to the built-in display when the DRC report opened (frame 1389x868).
18:0x: the user restarts the laptop. The five 3 mil routers were stopped by Stop-Process; their checkpoints are
valid JSON and `s7/c3/resume.sh` relaunches each as `<tag>_r` seeded from `<tag>.ckpt.json` (a seeded continuation,
not the identical run). Board saved (md5 391629d2), Altium open with nothing dirty, nothing committed.
18:12 after the restart: checkpoints, models and the board (md5 391629d2) intact; `c3/resume.sh` relaunched the
five runs as g_short_fin_r, g_s77_r, g_s77_3m_r, x_perm_b/g_seed77_r (seeded from their checkpoints) and
x_perm_b/g_s77 (fresh, its checkpoint was truncated).
21:00: the machine rebooted a second time at 20:11 (EventLog 6005 with no clean-shutdown 6006 before it), killing
the five resumed runs at 20:04-20:08 with none finished. All five checkpoints valid; `c3/resume2.sh` relaunched them
as g_short_fin_r2, g_s77_r2, g_s77_3m_r2, x_perm_b/g_s77_r2, x_perm_b/g_seed77_r2.

### 2026-11-05 07:15 -- first two 3 mil results in (both re-pin, both incomplete)

- `exp/x_perm_b/g_s77_r2` (re-pin, fresh, short, 0.077): **10 open on 10 nets** -- SD-DAT3, BS1, CHAN19,
  WE#, AIN16_N, PUDC_B, FPGA-TCK (budget); CFG-M0, FPGA-TDO, RAS# (nopath). 1064 vias, 4005 tracks.
- `exp/x_perm_b/g_seed77_r2` (re-pin, corner-seeded): 13 open on 12 nets. Seeding the corner is worse again.
- route_check at 0.0762: one violation in both, the routed GND through via at 26.900,18.000, 0.0756 from
  pad AIN16_P. Same via is in c3/g_short.json, so routing at 0.077 does not remove every raster case;
  it needs a nudge in post before any placement.
- Still running (no reboot since 20:11): c3/g_short_fin_r2, c3/g_s77_r2, c3/g_s77_3m_r2.
- Best so far: re-pin 10 open; unchanged pinout 12 open (g_short). No complete plan.

### 2026-11-05 07:55 -- diagnosis of the re-pin 10-open plan, three seeded finishes started

- `diagnose_open` on `exp/x_perm_b/g_s77_r2`: 9 congestion (AIN16_N, BS1, CFG-M0, CHAN19, FPGA-TDO, PUDC_B, RAS#,
  SD-DAT3, WE#), 1 routable on budget/order (FPGA-TCK).
- Started `exp/x_perm_b/fin2.sh`: seeded finishes of that plan -- fin_short (rip 2, 8M, short), fin_y3 (rip 3, 4M, y),
  fin_name (rip 2, 4M, name), all at 0.077.
- c3/g_short_fin_r2, c3/g_s77_r2, c3/g_s77_3m_r2 still running.

### 2026-11-05 10:00-11:00 -- all five overnight 3 mil globals in; `tools/finish.py` (partial rip-up) starts closing the residue

- Overnight globals at 0.077 (resume2): `x_perm_b/g_s77_r2` **10**, `x_perm_b/g_seed77_r2` 13, `c3/g_short_fin_r2` 15
  (the seeded 8M "finish" of the 12-open plan made it WORSE), `c3/g_s77_3m_r2` 21, `c3/g_s77_r2` 28. The whole-net
  rip-up router scatters between 10 and 28 on the same board and never converges; more runs of it are pointless.
- Why: `router.py` rips WHOLE nets (every track and via of each victim, multi-pin power nets included) and
  re-routes them from scratch, so each rip cascades. Its base=True probe is also slow: `via_ok` walks every via in
  Python (~0.3 ms per candidate), a few hundred expansions per second on a probe.
- **`tools/finish.py`** (new): local finisher on an almost complete plan. For an open connection it probes the
  cheapest path through rippable copper (plane-tie copper included, locked nets painted hard), cuts each victim only
  within `--rc` of the cells where the path conflicts with it, routes the net through the freed corridor, then
  re-joins each victim the same way one level down (depth-limited, backtracking; a victim that cannot be re-joined
  becomes immovable for the next probe). GND / VCC3V3 ties are re-tied with a plane via. It monkey-patches
  `Router.via_ok` with a numpy version (same test) and adds `Router.hw` (heuristic weight, default 1.0 = unchanged)
  to `router.py`. `--kick NET@x,y,r` cuts and re-joins copper at a point with a wider raster allowance first.
- First results on `x_perm_b/g_s77_r2` (10 open): single-net runs closed **9 of the 10 nets individually** in
  2-17 min each (AIN16_N, BS1, CFG-M0, FPGA-TCK, FPGA-TDO, PUDC_B, RAS#, SD-DAT3, WE#); CHAN19 needs the exact
  probe with cheap crossings (`--hw 1.0 --soft 0.05`: path in 84 s; `--hw 1.5 --soft 0.2` blows 1.6M pops).
  Chains (all ten in sequence, `s7/fin/run1.sh`, `run2.sh`) are at 6-7 open and still running.
- **Raster misses**: the base plan has 7 objects 0.0756-0.0759 from a pad (six VU tracks on Bottom, the GND via at
  26.9,18.0) -- routing at 0.077 with slack 0.005 does not cover every raster case. `tools/fix_clear.py` (new) loops
  route_check -> `finish.py --kick` (re-join with allowance 0.02 first) until PASS: 7 -> 0 on the base plan in one
  round. New finisher copper is routed at 0.078.
- Post-processing (new): `tools/plan_prune.py` (stub tails, dead vias; island count per net as the guard) and
  `tools/plan_final.py` (fan-out + plan as one set on the bare model: dedupe, drop stacks on a same-net through
  via, prune -- which removes the unused fan-out column ends -- then split into vip.final / plan.final /
  model.final and print NV / NT / NE). On a 9-open test plan: fan-out 387 -> 308 vias.
- Board scripts written for the placement (not run): `tools/FeatherVip2.pas` (VipPrepare2, U1 pads through the
  group iterator) and `tools/FeatherClearCopper4.pas` (guard 1301 vias / 5338 tracks).
- A read-only workflow produced the placement runbook (`%TEMP%/routing/s7/runbook.md`, 22 steps, both variants,
  cross-checked against the files): re-pin = apply_pin_swap + make_xdc + ECO BEFORE any placement.

### 2026-11-05 11:00-12:10 -- stage 7: COMPLETE PLAN (0 open), gates pass; not on the board yet

- User decisions this morning: the U1 re-pin (schematic + XDC + ECO per `x_perm_b/perm.json`) is AUTHORIZED; the
  PCBWay via-in-pad enquiry was rewritten for the ring scheme, checked by three readers and handed to the user to send
  (`docs/pcbway_vip_enquiry.md`, 10 questions).
- Finisher relays on `x_perm_b/g_s77_r2` (10 open): chain D (`--hw 1.0 --soft 0.1`) reached 4, relay `rD2` from its
  6-open snapshot reached **1 open (BS1)** and stuck there: every cheap BS1 path (U1 V8, L3-only column -> U3 G8) cuts
  9-15 routed nets, and seven more runs (crossing limit 6-10, soft 0.05-6.0, rc 0.4-0.6) all failed it.
- What closed it: the finisher only re-joins a victim LOCALLY, it never sends a slow net the long way round. With the
  slow nets that wall BS1 in removed WHOLE from the seed (`seedJ2` = rD2's plan minus LED0_R and CFG-M0), BS1 first,
  then CFG-M0 and LED0_R routed anywhere: `rJ2` -> **`finish: open 0 on 0 nets`** in 482 s (1197 vias, 4816 tracks).
  Lever to remember: whole-rip the static / slow nets around a walled-in fast net.
- `fix_clear.py` on it: 11 violations (6 VU raster misses, the GND via at 26.9,18.0, two GND hole-to-hole pairs) ->
  it looped on the two hole-to-hole pairs: its kick re-joins a GND tie with a laser stack 0.16 mm beside the buried
  via it serves, which is itself a hole-to-hole violation. Fixed by hand: each laser stack replaced by one L2>L3
  0.25/0.10 ON the buried via (26.700,13.350 and 27.025,17.450), the L3 link track dropped. BUG TO FIX in
  finish.py's tie placement: no hole-to-hole test against same-net vias.
- `plan_final.py`: dedupe 4819 -> 4818 tracks, 15 vias dropped on three same-net through vias (TMS 10.125,4.5; GND
  32.0,10.475; GND 29.15,17.75; GND 35.6,15.175), 52 nets pruned, fan-out 387 -> 312 vias.
  **NV 1482, NT 4773, NE 1093.**
- Gates: `route_check plan.final.json model.final.json --clear 0.0762` -> violations 0, open 0, PASS; the same at
  0.0763; `plan_open` 0 on 0 nets.
- Frozen in `tools/route/stage7/final/`: plan.final.json (md5 8a94694f), vip.final.json (c387cb26),
  model.final.json (8fe8e24c), x_perm_b_perm.json (2a453dbc), x_perm_b_model_bare.json, x_perm_b_vip.json,
  x_perm_b_xdc_edits.txt, plan.raw_rJ2.json (the finisher's output, 154a77e5), plan_final.log. The older
  `tools/route/stage7/{vip,model_vip,model_bare}.json` are the all-to-L3 scheme -- never place them.
- Board backup before the re-pin: `%TEMP%/routing/s7/backup_pre_stage7/` (PcbDoc 391629d2, seven SchDocs, XDC).
- Known quality items of the plan (from the enquiry check on partial plans; being re-measured on the final one):
  ~115 through vias and ~240 lasers in or on SMD pads, 1-2 through vias on U1 lands, the USB pair not coupled
  (N on Top, P on L3, ~4 mm each).

### 2026-11-05 12:10-13:20 -- stage 7 PLACED: 140/140 ROUTED ON THE BOARD, DRC 0

**Board md5 1162f2f9: DRC 0 violations on every rule (`docs/drc_stage7.drc`), Un-Routed 0, Net Antennae 0, Hole To Hole
0, Hole Size 0.** verify_copper: vias 1487/1487, tracks 4724/4724, missing 0, extra 0, PASS. mark_microvias --verify
after the final save: 1095. route_conn 0 open. sch_vs_board MATCH. check_feather_schematic (3 perms) PASS.

- Order done: re-pin first (apply_pin_swap: 3892 + 84 U1 pin records over 28 balls; two-perm control FAILs with 24, a
  second apply REFUSED; make_xdc: exactly the 24 expected rows), ECO 24 + 24 pins with the 10 net-class removals and the
  USB pair unticked (md5 4383b19d), VipPrepare2 (238 lands 0.25, both rules read back, 36987548), ClearRoutingCopper4
  (1301 / 5338 removed, 9048e895; re-dump equals x_perm_b_model_bare on 821 pads, 0 tracks, 0 vias), four-chunk
  placement (S7Vip 312/0, S7A 259/1710, S7B 423/1612, S7C 493/1402, Missing nets empty on all), mark (--expect 1095),
  Repour All, DRC, save. Stage copies: `%TEMP%/routing/s7/stages/` (1_eco .. 6_routed_drc0); pre-stage-7 board and
  schematics in `%TEMP%/routing/s7/backup_pre_stage7/`.
- The two untested Altium behaviours passed on the real board: Hole To Hole on a 0.10 laser coincident with a 0.15 buried
  via, and IsMicroVia beating IsBuriedVia on marked L2>L3 / L4>L5 0.10 vias. The canary was skipped on purpose: the
  whole chain is restorable from 3_cleared and a rule question would not have needed a re-place.
- A read-only four-lens audit (own exact geometry code, pour raster, DFM/electrical, placement chain) said "place" with
  no blockers but found what route_check cannot see. Fixed in `tools/route/stage7/final/plan.patched.json` (md5 ea2e0144;
  `patch_audit.py`, `dead_copper.json`): 49 dead tracks + 5 dead vias, including a 4-track floating GND island that
  route_conn.py:164 drops silently; three overhangs; C113-2's only link was a 12.8 um corner graze (track now ends at the
  pad centre); GNDADC through via off ball A13; 10 power vias (VCC3V3 entered L5 through one laser at L1-2, U5-4 and
  C80-2; U8's exposed pad had one via). The audit's code, re-run on the result: 0 shorts, 0 under 0.0762, smallest
  0.076345, 0 dangling ends, 0 floating islands, every joint overlaps >= 0.0375 mm.
- **Open quality items, none of them DRC errors:**
  - Plane necks under 3 mil stay in the pour (18 on L2, 29 on L5; REMOVENECKS=FALSE). Measured on the saved polygons: the
    orthogonal U1 webs on L2 are 0.085-0.09 mm (65 of them), not 0.098.
  - Pours sit 0.0762 mm from the six NPTH holes (no rule pulls them back); tracks down to 0.086 mm from them.
  - Power trunks at rule minimum: VCC1V0 0.15 (0.6 A by IPC-2221 10 C), VU / VBATT 0.2 at 94 % of capacity at the 0.7 A
    budget. Widening needs no re-route (VCC1V0 could reach 0.5 on 28 of 47 mm).
  - 113 through vias in or on SMD pads, including BGA lands U1-W8, U3-G9, U3-H2: the build depends on resin plug + plate
    over (enquiry item D, question 8), otherwise the HIGH / MEDIUM wicking pads need dogbones.
  - Decoupling: C109-2, C107-2, C113-2 reach GND through 2.6-3.8 mm of 3 mil track.
  - USB pair not coupled (N on Top 4.4 mm, P on L3 3.7 mm; ~20 ps, low risk). XADC inputs not routed as pairs. SDRAM
    spread 3.8-25.7 mm. R25 is far from the 12 MHz oscillator.
  - Bugs: finish.py's plane tie has no hole-to-hole test against same-net vias; route_check.py:128 tests plan vias only,
    so fan-out vias are never checked against pads; route_conn.py:164 hides pad-less islands.
  - Not done: the PcbLib keeps U1 at 0.225 (never update U1 from the library); README pin table is stale; no Vivado place
    / report_drc on the re-pinned XDC; no SI simulation.

### 2026-11-05 13:20-14:00 -- stage 7 clean-up: necks, NPTH pullback, trunks, U1 library footprint

**Board md5 3c46c977: DRC 0 on every rule (`docs/drc_stage7_clean.drc`), 1487 vias, 4827 tracks, verify_copper PASS against
`tools/route/stage7/final/plan.clean.json` (md5 c2c38921), 1095 microvias still marked, route_conn 0 open, sch_vs_board
MATCH.** The routed board before this is commit 1f55305.

- **Plane necks:** Remove Necks at 3 mil on both pours (`FeatherPourClean.pas`). Measured on the saved polygons: webs
  under 0.0762 mm 18 -> 0 on L2 and 29 -> 0 on L5 (min 0.0764 and 0.0807). The orthogonal U1 webs stay 0.085-0.09 mm.
- **NPTH pullback:** new rule Clearance_Plane_NPTH, 0.25 mm, priority 1. Measured: 0.250 mm from all six holes on both
  planes (was 0.076). Pour copper lost: about 8 mm2 per plane (L2 944.1 -> 936.3, L5 922.3 -> 914.5 mm2).
  - TRAP, cost one round: the first scope `IsPad And InNet('No Net')` matches NOTHING, so the rule did nothing and the DRC
    passed vacuously. A clearance rule passing proves nothing; only measuring the saved pour caught it. `R.Scope2Includes(P)`
    counts what a scope matches (`FeatherProbeNpth.pas`): `Net = 'No Net'` 68 pads, `Name = 'X2-'` 4 and `Name = 'X1-'` 2.
    Final scope `IsPad And ((Name = 'X2-') Or (Name = 'X1-'))` (`FeatherNpthScope.pas`). FeatherPourClean.pas still shows the
    wrong scope in its source; it was loaded, so it stays as it ran.
- **Trunks:** `tools/widen.py` keeps every centreline and only changes width, in pieces of at most 0.4 mm so a pinch narrows
  only its own piece, capped at the short side of a same-net SMD pad. 96 tracks became 199 (`FeatherCopper_S7W`). Length at
  the old minimum width: VCC1V0 Top/Bottom 32.6 -> 10.7 mm of 0.15; VU 35.5 -> 18.0, VBATT 23.9 -> 8.5, USB5V0 35.1 -> 8.5
  mm of 0.2; each SW node 2.7 -> 1.2-1.9 mm of 0.2. Everything else on these nets is 0.25-0.5. The sum of length / width
  falls 26-39 % on VCC1V0 (Top/Bottom), VU, VBATT and USB5V0.
  - NOT gained: the narrowest section in series is unchanged (0.15 on VCC1V0, 0.2 on the others), so the worst-case
    current figure at the pinches stands. No legal site within 3 mm for a second VCC1V0 L4>L5 + L5>Bottom stack, so the two
    single stacks remain.
  - The audit's own geometry code on plan.clean: 0 shorts, 0 under 0.0762, 0 dangling, 0 floating.
- **U1 library footprint:** XC7A35T-CPG236 in asar_feather.PcbLib now has 0.25 mm lands (`FeatherLibU1.pas`, guarded on 238
  pads at 0.225). Saving made Altium re-serialise a few other footprints (1X03-NOSILK primitive order, small changes in
  CC_* and TDFN-8); the board does not read them unless updated from the library.
- Enquiry updated: pour to non-plated hole 0.25 mm, no strip under 0.0762 mm.
- Still open: 113 through vias in pads (PCBWay's answer), tracks 0.086-0.095 mm from the X1 non-plated holes, long 3 mil GND
  ties at C109 / C107 / C113, README pin table, no Vivado run on the re-pinned XDC, no SI simulation.

### 2026-11-06 -- STEMMA QT connector X5 added: DRC 0

**Board md5 243ef145: Altium DRC 0 on every rule (`docs/drc_stemma_qt.drc`), 1512 vias, 4861 tracks, verify_copper PASS against
`tools/route/stage7/final/plan.stemma.json`, 1113 microvias marked, route_conn 0 open, sch_vs_board MATCH (174 parts),
check_feather_schematic PASS, verify_footprints PASS.** Pads on the board equal `model.stemma.json`, 827 of 827.

- Part: JST SM04B-SRSS-TB, side entry, X5 (J1 is on the Feather's removed list). Top side, right end, rotation 90, pad 1 at
  45.725, 8.2, mouth towards x = 50.8; housing front 0.5 mm inside the edge, tabs 0.30 mm from it, the plug ends about 1.5 mm
  past the edge (JST's 6.25 mm mated depth). Pins 1 GND, 2 VCC3V3, 3 SDA (CHAN22), 4 SCL (CHAN21), MP1 and MP2 GND. Schematic on
  asar_a7_2.SchDoc by `tools/add_stemma_qt.py`, footprint by `tools/footprints.py`.
- Why side entry: top entry (BM04B) needs no part moved at 36.3, 4.3, but stands 6.3 mm mated plus the cable bend under a stacked
  Wing, and its trial disturbed 198 tracks including SDRAM nets; this one 76 added, 42 removed.
- Parts moved to make room: R80, R81 and R82 right of BTN, R84 left of BTN, LD0 0.90 mm west. BTN's designator gave way to a free
  'BTN' text, 0.6 mm high, between X2's pads and BTN; X5's designator is hidden.
- Routing: `tools/finish.py` on scratch copies. SDA and SCL both run on L3, about 11 mm each, from X2-28 and X2-27. The first SCL
  route ran on Top under U4; a temporary obstacle over U4's body in the routing model moved it to L3.
- An independent review before placement confirmed orientation and pin order four ways, including Adafruit's own SHT40 design
  file, which has the same pads at the same rotation on a +x edge. It found what route_check cannot see, all fixed before
  placing: R82 0.05 mm from X5-MP1 (`tools/pad_gate.py` is the new gate for moved pads), two mask slivers at BTN, X5's silk
  into BTN's mask and U4's silk, BTN's designator landing on R80 and R81, and no mask dam between LD0-3 and X5-2. DRC then
  caught one more: R84 0.202 mm from the 'ASAR A7' silk, moved 0.06 mm north.
- Traps: `RemovePCBObject` on a library footprint did not survive the save, even with that footprint current (the track count
  in the script dropped, the file kept them); selecting and deleting in the editor did. Library silk coordinates carry an
  offset in a script. finish.py leaves GND and VCC3V3 out of its top-level net list by design: tie new plane pads with a copy
  that drops that filter (`n not in PLANES`).
- Not done: no XDC change was needed, and no PULLUP was added on F_SCL / F_SDA (the devices carry pull-ups, FPGA internal ones
  are optional). No ESD part on SDA / SCL. Vivado not run. Gerbers not generated. README pin table corrected from the XDC.

### 2026-11-07 -- LED row and pin labels: DRC 0

**Board md5 7789390c: Altium DRC 0 on every rule, silk rules included (`docs/drc_led_row.drc`), 1521 vias, 4718 tracks,
verify_copper PASS against `tools/route/stage7/final/plan.led.json`, 1123 microvias marked, route_conn 0 open, sch_vs_board MATCH
(174 parts), check_feather_schematic PASS.** Pads on the board equal `model.led.json`, 827 of 827, worst 0.0002 mm. All 25 text
anchors in the saved file equal `labels.led.json`.

- LEDs: LD5, LD1, LD2, LD0 in one row 3.2 mm apart, x centres 28.8, 32.0, 35.2, 38.4 at y 4.675. R78, R83, R84 sit north of the row at
  y 6.3, also 3.2 mm apart. LD1, LD2 and the three resistors turned 180 degrees, so every resistor faces its LED's east pad. R80 to R82
  stay. The first trial had the resistors south of the row at y 3.1, which routed but sat exactly where 5 pin labels go.
- Labels: 22 of 28 header pins, Feather names at PCBWay's minimum, 0.8 mm high, 0.15 mm stroke. South: RS, A1, A4, A5, SCK, MO, MI, RX, TX,
  D4. North: BAT, EN, USB, D13, D12, D11, D10, D9, D6, D5, SCL, SDA. 3V3, AREF, GND, A0, A2 and A3 have no spot on either side: U2 and the
  reset switch on Top, capacitors and inductors on Bottom. Names match the XDC's `F_<name>` ports.
- Other silk: BTN up to 0.8 mm above its switch; title on two lines, ASAR and A7, at 1.2 mm beside X5; RESET's designator off. The reset
  switch has no label: its only spot went to A1, and RST there read as the name of pin 6 or 7. RS is pin 1, because RST would sit 0.08 mm
  from the edge. A4 is upright, 0.68 mm east of its pin. 9 Top vias lie under label strokes (tented, rule scope IsPad). The earlier 0.6 mm
  BTN and the 0.6 mm RST I proposed were below PCBWay's minimum, which their capabilities page calls too small to recognise.
- Font, measured from `zulu_a7.GTO` by the independent review: grid unit height / 6, most glyphs 4 wide with advance 6, I and 1 are 2 wide
  with advance 5, ink starts at the anchor, rot 90 ink runs west of the anchor. M, O and E have no Gerber sample: `LittFont.Fnt` gives 4 wide,
  advance 6. Altium's `BoundingRectangle` is one half stroke wider than the ink on each side (`docs/labels.log`); DRC passed anyway.
- Copper: `tools/finish.py` on scratch copies, first run moved D14, FPGA-CCLK and six more bystanders. A scratch copy with a list of nets its
  probe may not cut gave 17 changed nets: the LED nets, BTN, N$BTN, FLASH-D00 (+3.7 mm, now the longest flash net), SD-DAT0, the GND ties of
  the moved parts and of C9, C12 and X3-G1, and LD5-A's VCC3V3 column. No SDRAM, clock or other power-rail copper moved. Delta -496 +353 tracks,
  -64 +73 vias.
- Reviews: three independent checks of the trial, two more of the final files. They found what the gates cannot see: five GND vias stacked
  inside the through via at 30.3, 8.175 (now `tools/hole_gate.py`, controls 0 pairs on the committed plan, 5 on the trial), M narrower than
  assumed, and the misreadable RST. finish.py left 54 orphan FLASH-D00 tracks that plan_prune does not remove (route_check passes them): the
  audit's floating-island line is the gate.
- Scripts: `tools/emit_led_row.py` writes `FeatherLedParts.pas` and `FeatherPinLabels.pas`; `route/stage7/final/led_delta.py` writes the delta
  behind `FeatherCopper_S7L.pas`. Order: LedParts, PinLabels, PlaceS7L, save, close, mark_microvias, reopen, Repour All, DRC, save.
- Not done: Vivado not run, Gerbers not generated, no polarity mark on LED0603 (LD1 and LD2 now face the other way from LD5, only pad names and
  the placement file carry it). The enquiry text still quotes the 243ef145 counts, with the new totals noted at its top. The wrong XADC channel
  numbers in the docs (A0 is AD4, A1 is AD12) are being corrected in a separate session.
- Designators, same day (board md5 786c6120, Altium DRC 0 in `docs/drc_designators.drc`): the user moved U1's designator by hand to
  (19.292, 5.700), which DRC flagged at 0.235 mm from the mask of balls A18 and A19 (Silk To Solder Mask 0.254). U1's designator went
  0.05 mm south to y 5.650, and X1's went from 1.0 to 0.8 mm high (stroke 0.15) with its centre kept, anchor (3.664, 17.118). U1 and U2
  were already at PCBWay's 0.8 mm minimum and stay there. Against the user's save only these two texts changed. verify_copper PASS,
  1123 microvias, route_conn 0 open, sch_vs_board MATCH, check_feather_schematic PASS, all 25 label anchors as planned.
  Scripts: `FeatherSilkDesig.pas` (X1; its direct `YLocation` write on U1 did not hold) and `FeatherSilkU1.pas` (U1: autoposition
  manual, then `MoveByXY` between robot modify messages). `Near` is a reserved word in DelphiScript ("Program name expected").
- Stale ratsnest, same day (board md5 edc539d8, Altium DRC 0 in `docs/drc_connections.drc`): Altium drew about 280 thin connection lines
  although its DRC found Un-Routed 0 and route_conn 0 open. They were not open nets. The PcbDoc saves its ratsnest (`Connections6`,
  47 bytes a line): 368 lines at stage 5, 271 at stage 7, 278 at 786c6120. Altium loads them as saved, and copper placed by script never
  made it recompute them, so they still pointed at old pad positions and at the parking grid east of the board (x 53-57 mm).
  `tools/FeatherRebuildConn.pas` (every net `ConnectivelyInValidate`, then `Board.ConnectivelyValidateNets`) cleared all but GND's 124;
  `tools/FeatherRebuildGnd.pas` removed those (display objects only) and re-validated: Altium re-created none, so `Connections6` is now
  empty. Against 786c6120 no track, arc, fill, text, region, pad or via changed (one net record gained a cached routed length);
  verify_copper PASS, 1123 microvias, route_conn 0 open, sch_vs_board MATCH. `tools/FeatherRatsnest.pas` lists the connection objects
  Altium holds. Gate from now on: a fully routed save must have an empty `Connections6`.
