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
