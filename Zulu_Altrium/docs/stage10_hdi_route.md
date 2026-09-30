# Stage 10: one global HDI route -- 96 of 140, DO-NOT-PLACE (2026-09-30)

**Nothing placed.** The user's instruction: "focus only on the $309 HDI order routing" -- one global route, no knot
decomposition, no placement changes. Workflow wf_fe8a5285 (instrument hardening + verifier, one global router,
reviewer, judge; 0.98M tokens, 6.5 h). Plan kept at `scratchpad/stage10/global/plan.json` (md5
`a1ed28d5db5a2af10e9c6cb978979007`, 429 via objects / 1198 tracks / 1641.6 mm, `gen.py --check` byte-identical).
Structured result: docs/stage10_hdi_route.json.

| | closed of 140 |
|---|---|
| through-only global routes (stages 4b / Situs / 6) | 92 / 90 / 86, none placed |
| **HDI, one global route, scope=all, hardened instrument** | **96** (95 signal + the U2-5 GND tie) |

**Verdict DO-NOT-PLACE**: 44 open in four local corridors; signals_check and gnd_check fail; the USB pair is
routed as two single-ended 0.0762 mm tracks (coupled length 0, skew 1.95 mm) -- the router has no differential
mode; three laser-laser plane voids in adjacent sites leave 0.020-0.030 mm webs; a partial placement would
freeze the very commit order that keeps the 44 open.

**What HDI did buy, placed-quality:** the U2-5 GND tie -- a GND Top>L2 laser stack at (26.8,15.15) where no
through via fit within 1.5 mm. The emitter now writes a merged laser stack as two Altium vias (uVia 1:2 + 2:3),
proven on a synthetic plan; the router now enforces same-path via pitch.

**The 44 open are corridor-limited, not via-limited:** A. U1's NE/east edge column x 50.9-52.0 (22: CHAN0-11,
SD-DAT0/3, FLASH-CS#/D01/D03, JA8, UART_FT_TXD/RTS#/DTR#/RXD, LED2) -- the A16/A17/A18 stubs share ONE Top lane
down x 50.9; the K19/J19/H19 lane carries one track; the D19/F18/E19 column holds one lane / one laser site.
B. South band under the W row (14: CHAN13-26, FPGA-TMS, RST#, LED0_R/G/B) -- one lane per stub column; the 0.4 mm
pocket south of W9/W10 must hold TDI+TMS+RST# at 0.175 pitch with 0.009 mm margins. C. U1 east edge y 8.5-8.7
(5: JA1, JA2, CHAN27, CHAN-CLK, CHAN28) -- one lane. D. NODE_P0 x2 and the R15-1 GND tie -- the R15-1 exit
channel is 0.136 mm wide (one track) and is ANALOG-IO1's only exit too: **R15-1 OR ANALOG-IO1 on this placement,
or a two-removal edit of stage-8 NODE_P1/AIN16_N copper (6.7 um conflict).**

---

# Stage 10 judge: the whole-board HDI plan -- DO-NOT-PLACE (2026-09-30)

Directory: `scratchpad/stage10/judge/` (this file, `webs.py` + `webs.log`, `u2_5_r15.py` + `u2_5_r15.log`).
Plan judged: `scratchpad/stage10/global/plan.json`, md5 `a1ed28d5db5a2af10e9c6cb978979007` (`md5sum`, identical for
`global/plan.json`, `global/check/plan.json` and the reviewer's `review/check/plan.json`). Inputs / model in force:
`global/inputs_hdi.json` md5 `730bac7e9fefa522ec62b38e133a1fd6` = `instrument/inputs_hdi.json` = the brief's
`hdi_gain/repro/inputs_hdi_B_field_merged.json` (all three md5sums equal). Board: `Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc`
md5 `c927413f3422a37f230e78ac3de58942` = the brief's; `tools/route_inputs.json` md5 `70f2061c95c4ae81133580e60e010539`
= the brief's. Boundaries: `git status --porcelain` shows nothing modified under `tools/`, `docs/` or the PrjPcb (only
the pre-existing `Claude_Fable/*` edits, `Altium_backup/`, `VS_Code/` and the 09:00 `Zulu_Altrium/plan.json`, all from
before this stage); nothing was placed, no `--write`, no Altium, no git commit, no pictures, my own scripts live only here.

## 0. The verdict in one paragraph

**DO-NOT-PLACE.** The plan closes **96 of 140** (95 signal connections + the U2-5 GND tie) and leaves **44 open**;
it is reproduced byte for byte by two independent 10-chunk re-runs (the agent's `global/check`, the reviewer's
`review/check`), and every gate log reproduces. But the deliverable the user asked for is *all 140, every gate
passing*, and the plan is not that: `signals_check` 43 nets split, `gnd_check` 205/206 (R15-1), the USB pair routed
single-ended at 0.0762 mm with zero coupled length (the 0.150/0.150 DiffPairsRouting requirement is simply not met),
and a stated hard boundary broken that no gate measures -- foreign-net laser voids in adjacent 0.5 mm sites leaving
0.020-0.030 mm plane webs at three laser-laser sites (my `webs.py`), plus 8 thin laser-through webs and 57 merged
void pairs. A **PLACE-PARTIAL** of the 96 is also refused (section 6): it would freeze 95 routes whose commit order is
exactly what keeps the 44 open (UART_FT_RXD, FLASH-D01/D03/JA8 close under other orders), it carries the web
violations and the uncoupled USB pair onto the board, and one of the connections it would leave open
(UART_FT_RXD U2-39<->U1-G19) holds only a raster-legal witness that is exactly illegal by -0.0203 mm -- so "nothing
walled off" is true of `route_reach` (37/37) but not proven for that one. The 44 open connections are not a router
accident: they sit in four local corridors (22 on U1's NE/east edge column, 14 in the south band under the W row,
5 on U1's east edge at y 8.5-8.7, 3 on the R10/R11 lane and the R14/R15 channel), each one "routable alone" but
each one cutting a neighbour's last corridor (`global/diag/state_open.log`, reproduced identically by the reviewer).

## 1. Closed of 140 = 96, established three ways

| count | source | command |
|---|---|---|
| 95 signal closed, 43 open | the router, `global/run2/gen.log`: `CLOSED 95 of 138 signal connections in all`, `still OPEN: 43`; `global_result.json` closed_names 95 / open_names 43 | `cd global; python gen.py --out=run2 --state=run2/state.json --deadline=500 [--resume] --passes=AB` (10 chunks, end times sum 5026 s) |
| +1 = U2-5 tie | `global/gates/gnd_check.log`: `GND SMD pads 206, tied 205, untied 1 ... UNTIED R15-1 Bottom (43.750, 3.950)`; bare board (`review/gates_bare/gnd_check.log`) `tied 204, untied 2 (U2-5, R15-1)` | `python tools/stage6/gnd_check.py --inputs INP PL` |
| 96 closed / 44 open | reviewer's own union-find over the DRC's 140 lines, `review/audit.log`: `CLOSED by board+plan: 96 of 140 OPEN: 44 endpoints not found: 0`; its 44 = the agent's 43 + `GND track<->R15-1` exactly | `python review/audit.py` |
| 132 joined / 43 split | `global/gates/signals_check.log`: `175 nets checked ... 132 joined, 43 split` (bare board `66 joined, 109 split`); the 43 SPLIT nets are one per open signal connection | `python tools/stage6/signals_check.py --inputs INP PL` |

Reproduction: `global/check/chunk10.log` and `review/check/chunk10.log` both end `--check .../global/plan.json:
IDENTICAL byte for byte`; `review/lines.py` 131 names, 131 identical decision histories. Reviewer's correction accepted:
`diff global/check/lines.txt global/check/run2_lines.txt` is NOT empty (13 pass-B lines reordered by chunk
boundaries); it is empty after sorting -- the substantive claim holds, the wording did not.

The 96 placed connections (should anyone later want them by name): the 95 `closed_names` of
`global/global_result.json` (N$BTN x3, PMOD-1/2/3/4/7/8/9/10, TCK x3, TMS x3, TDI x3, TDO x3, N$LD0B, N$LD0R, N$LD0G,
N$LD1A, N$LD2A, CLK-12M-SHARED x2, CLK-12M-FT, CLK-12M-FPGA, EE-DATA-DO x2, EE-DATA x2, EE-CLK x2, EE-CS x2, ANALOG-IO0,
ANALOG-IO1, FPGA-INIT#, RST# R4-16<->R1-2 and X2-23<->R1-2, FT-REF, FT-RESETN, CFG-M0, CFG-M1, CFG-M2, FLASH-D02 x2,
FLASH-D00, FLASH-D03 U4-7<->R6-1, FLASH-CS# U4-1<->R7-1, PUDC_B, JA3, JA4, JA7, JA9, JA10, SD-DAT0 R34-1<->X3-7,
SD-DAT1 x2, SD-DAT2 x2, SD-DAT3 R34-4<->X3-2, SD-CMD x2, SD-CLK, PROG# x2, DONE, DONE-PU, FPGA-TCK x2, FPGA-TDO,
FPGA-TDI, FPGA-DONE x2, LED1, BTN, UART_FT_CTS# x2, UART_FT_RXD U1-G19<->R94-1, FT-PWREN#, USB_D_N, USB_D_P,
FPGA-CCLK, CHAN5, CHAN12, CHAN14, CHAN17, CHAN21, CHAN22, CHAN24) + `GND U2-5<->track`.

## 2. Every gate, with what it actually says

All run from `instrument/` with `INP=global/inputs_hdi.json`, `PL=global/plan.json`, commands in `global/run_gates.sh`,
logs `global/gates/*.log`; the reviewer re-ran every one into `review/gates/` and they are byte-identical apart from
path/time header lines.

| gate | result | reading |
|---|---|---|
| `route_emit.py PL Stage10 --inputs INP --require-complete` | `plan: 429 vias, 1198 tracks / geometry and connectivity check: clean / nets joined end to end: 66/67`, EXIT 0 | **PASS**. Every track 0.0762 mm (1198), every via one of the four model spans, 0 pitch violations, 0 field-banned spans in the land field (`review/audit.log`). |
| `--pas` | `429 plan via(s) -> 640 Altium via object(s), 1198 track(s)`; 99+99 laser Top/L2 + L2/L3, 112+112 Bottom, 187 buried 0.27/0.15, 31 through; md5 `b2f5c1119b4b29842542816290a65660` (agent = reviewer) | **PASS** (instrument gap 1 closed; read only, never run). |
| `signals_check.py` | `132 joined, 43 split`, EXIT 1 | **FAIL** -- the 43 split nets are the 43 open signal connections (list in `global/gates/signals_check.log`). `VCC3V3 86 islands` is the bare board's own state (plane polygon, not a track): identical in `review/gates_bare/signals_check.log`. |
| `tie_check.py --net VCC3V3` | worst tie U2-56 2.999 mm, EXIT 0 | **PASS**. |
| `gnd_check.py` | `tied 205, untied 1: R15-1 Bottom (43.750,3.950)`, EXIT 1 | **FAIL** -- U2-5 newly tied by the plan (Top track (25.775,15.3501)-(26.8,15.15) + GND Top/L2/L3 stack at (26.8,15.15); my `u2_5_r15.py`: worst exact slack to foreign Top copper +0.0569 mm (U2-6 FT-REF pad), worst via-pitch slack +0.035 mm (FT-REF buried via at (26.8,14.7)) -- legal). R15-1 cannot be tied on this placement without a user decision (section 4 D). |
| `plane_islands.py --net GND --plane L2 --uvia-clearance 0.165` | `island 1 1470.692 mm2 (100.0 %)`, `215 of 216 GND pads`, `OFF-PLANE C115-2 (51.630,7.650)`, 3 strays 0.0156 mm2, EXIT 1 | **One island: the brief's criterion is met.** EXIT 1 comes from the reportable heuristic: C115-2 is a *Bottom* 0.3x0.3 GND pad (inputs `bottom_pads`) whose centre projects into the L2 antipad of the plan's JA9 Top/L2/L3 stack at (51.7,7.7), 0.086 mm away -- no copper conflict on any layer (route_emit clean), the pad's own tie via lands on the main island (135/135). The 0.0156 mm2 of slivers are plan-caused (bare board: none, `review/gates_bare/plane_L2.log` EXIT 0). |
| `plane_islands.py --net VCC3V3 --plane L5 --uvia-clearance 0.165` | `island 1 1442.695 mm2 (100.0 %)`, `132 of 133`, `OFF-PLANE U1-K1 (41.900,11.900)`, 8 strays 0.5084 mm2, EXIT 1 | **One island: met.** U1-K1 is a *Top* 0.225 ball whose centre projects into the L5 antipad of the plan's SD-CLK L4/L5/Bottom stack at (41.75,11.75), 0.212 mm away (0.0375 mm outside the land-field box, model-legal); no copper conflict; 86/86 VCC3V3 vias land on the main island. **Reviewer's correction adopted:** the 0.4800 mm2 island at x 48.648-49.148 y 12.208-13.588 is on the BARE board (`review/gates_bare/plane_L5.log`, 5 strays 0.5024 mm2, EXIT 0; walled by the board's own VCC1V8/JA3/CHAN9/CHAN6/GND/VCC3V3 through vias, no plan via in the box). The plan adds 0.006 mm2. |
| `route_foreclosure.py` | `foreclosed by the plan(s): FLASH-D02 D10 D15`, pads foreclosed none, EXIT 1 | **Formal FAIL, no open connection foreclosed -- my correction to the record (section 5).** |
| `route_reach.py --inputs INP --drc docs/drc_hdi_rules_2026-09-29.drc PL` | `37 un-routed connections of nets the plan(s) do not touch ... routable on the board: 37 / 37, routable with the plan(s): 37 / 37, connections walled off by the plan(s): none`, EXIT 0; bare board `138 / 138` | **PASS** as defined. Note its scope: 37 = the 44 open minus the 6 whose nets the plan touches (RST#, FLASH-D03, FLASH-CS#, SD-DAT0, SD-DAT3, UART_FT_RXD) minus GND. For those 6 the only "not walled off" evidence is the router's own witness (`diag/state_open.log`: all 43 `routable alone`), and for UART_FT_RXD that witness is raster-legal only (section 4 A). |
| `route_stitch.py` | whole board 30750 -> 21481 sites 69.9 %; U1 surround 15.4 %, south band x 31-58 11.3 %, north band 55.0 % | **PASS** (a report, no threshold). |
| `route_width.py --net USB_D_P/--net USB_D_N` | `max width 0.325 mm` / `0.363 mm`, EXIT 0 | The tool passes, **the requirement does not**: the pair is single-ended, every USB track 0.0762 mm (P 14 tracks 16.02 mm, N 16 tracks 14.07 mm), coupled length 0, min same-layer centre distance 0.204 mm, skew 1.95 mm (`review/audit.log`); the inputs carry no USB width rule at all (`rules` keys: Width_SDRAM, Width_PWR_*, Width 3 mil), so the board's DiffPairsRouting 0.150/0.150 would flag the pair the moment it is placed. |
| `capacity.py` | TOTAL -553.3 mm2 (4191.2 -> 3637.9); north band lanes 669 -> 499, U1 east 382 -> 287, south band 699 -> 608 | **PASS** (a report). |
| **void alternation (brief, no gate)** | my `webs.py` (laser antipad 0.48, through 0.53 = 0.20 + 2 x 0.165, plan+board vias): L2 thin webs 0 < w <= 0.03 mm: 3 plan-involved -- **TMS/CHAN24 laser-laser (36.5,7.8)/(37.0,7.85) d 0.5025 web 0.0225**, FPGA-TCK laser/TMS through (59.3,18.4)/(59.4,17.9) web 0.0049, TDO laser/VCC3V3 board through (59.4,17.1)/(59.34,16.58) web 0.0185; L5: 8 plan-involved -- **N$LD0R/N$LD1A laser-laser (29.7,13.4)/(29.2,13.4) d 0.500 web 0.020**, **FPGA-TDO/CHAN22 laser-laser (45.7,5.8)/(45.2,5.9) web 0.0299**, FT-RESETN/A5 0.0049, FPGA-TCK/TMS 0.0049, FLASH-D02/GND 0.017, CLK-12M-SHARED/GND 0.0223, N$LD0G/GND 0.0224, FLASH-D03/GND 0.029; merged pairs (web <= 0) plan-involved 32 on L2, 25 on L5 | **FAIL against the brief's boundary** ("alternate sites"). Both reviewer cases confirmed exactly; one more laser-laser case found. The planes stay one island, so the consequence is manufacturing (a 5-30 um copper web etches away and the two voids merge), not connectivity -- but the boundary is the user's and it is broken at 3 laser-laser sites and 8 laser-through sites. The bare board already carries webs of this class between its own through vias (BS0/A0 0.0223, UDQM/SDRAM-CLK 0.0251 on both planes; VCC1V0/GND 0.0151 on L5), which the boundary did not address. |

Via census (reproduced by the reviewer exactly): 325 sites, 429 objects; buried L3-L4 102 (17 inside U1's field),
Bottom stack 54 (0), Top stack 53 (2), chains 39 + 27 + 19 (0), through 31 (0); track length 1641.6 mm; tracks by
layer L4 342, Top 293, Bottom 292, L3 271.

## 3. Reviewer's findings -- adopted, with one addition

1. 96 of 140 confirmed by an independent count -- adopted.
2. The 0.48 mm2 L5 island pre-exists on the bare board -- adopted (I read both bare and plan logs; the reviewer is right).
3. "diff empty" was true only after sorting -- adopted; the reproduction itself stands (two independent byte-identical re-runs).
4. The void-alternation boundary is broken and unmeasured -- adopted and re-measured (`judge/webs.py`); my numbers agree
   with the reviewer's two exact cases and add FPGA-TDO/CHAN22 (0.0299) and the eight laser-through thin webs.
5. Not reproduced by the reviewer and taken as the router's word: "U2-5 has 0 THRU-legal cells within 1.5 mm" (moot --
   the tie is closed with a laser stack, which I checked exactly), the route_reach own-copper raster gap (I accept the
   agent's measurement; it is visible in the failure string `no route on the lattice (after 1 exact retries)` and the
   fix is in `router_fine.diff inset_own_cells`), and the 0.136 mm channel -- **which I re-measured** (section 4 D).

## 4. The 44 open connections, by corridor, each with its measured reason and what was tried

Sources: `global/diag/state_open.log` (`python global/diag_state.py global/run2/state.json`, 95 routed / 43 witnesses,
every one `routable alone`; the reviewer's `review/state_open.log` OPEN and walls-off lines are identical -- my
`diff`), the per-connection decision lines in `global/run2/gen.log`, the knot/order tests `global/knots/*/log` and
`global/orders/*/route.log`, `global/tie_r15.log` (+ the reviewer's `review/tie_r15.log`). "Walls off X at (p)" means:
the connection's own route now cuts X's last witness at those cells and no witness for X can be re-found; committing it
would wall X off, so the engine refused it. Ladder tried on every one: via-slot denial ("left it its via slot and took
another"), the 0.05 and 0.025 mm lattices, detours 6/12/24 cells, arbitration (lay the blocker first), pass A at
(90,36) with the knots at (400,120), pass B at (400,120) -- `pass B: closed 0 of 43`.

**A. U1's NE / east edge column, x 50.9-52.0, y 11.4-15.3 -- 22 connections.** One lane and one laser site per stub
column; the A16/A17/A18 stubs share one Top lane down x 50.9; the K19/J19/H19 stubs one lane at x 51.0-51.9 y 11.4-12.4;
D19/F18/E19 one lane at x 51.1-51.9 y 14.2-15.3; and once the edge is full the north band over U1 at (47.6,17.95) is
CHAN10's only corridor.

| connection | walls off / reason | tried beyond the ladder |
|---|---|---|
| CHAN0 track<->X2-3 (wit 18.95 mm) | CHAN3 X2-6<->U1-A17 at (50.900,13.35-13.475) | via-slot denial then no route on any lattice |
| CHAN3 X2-6<->U1-A17 (22.39) | CHAN0 at (50.900,13.25-13.375), 256 cells | -- |
| CHAN1 U1-A18<->X2-4 (18.70) | CHAN0 at (50.75-50.875,16.65), 251 cells | -- |
| CHAN2 X2-5<->track (20.45) | CHAN0 at (50.900,13.25..), 329 cells | -- |
| CHAN4 X2-7<->via (20.93) | CHAN0 at (51.000,13.15)-(51.125,13.025) | -- |
| CHAN6 X2-9<->via (22.63) | CHAN0, same cells | -- |
| CHAN9 X2-12<->via (41.01) | CHAN0, same cells | pass A also hit `work budget spent (110 searches)` |
| CHAN11 X2-14<->via (46.30) | CHAN0, same cells | budget spent (108) in pass A, no route in B |
| SD-DAT0 X3-7<->via (54.84) | CHAN0, same cells | -- |
| SD-DAT3 X3-2<->U1-A16 (56.79) | CHAN0 at (50.900,13.25-13.375), 329 cells | -- |
| CHAN7 X2-10<->U1-H19 (36.49) | CHAN10 X2-13<->U1-J19 at (51.15-51.275,12.2-12.35) | -- |
| CHAN8 X2-11<->track (39.02) | CHAN10 at (51.0-51.125,12.375-12.4) | -- |
| CHAN10 X2-13<->U1-J19 (43.61) | UART_FT_TXD U2-38<->track at (51.125-51.25,12.0-12.125) | -- |
| FLASH-CS# U4-1<->U1-K19 (17.12) | CHAN10 at (51.300,11.925-12.05) | detour 6 cells, no route |
| LED2 R84-1<->U1-M19 (29.26) | CHAN10 at (51.825-51.95,11.45-11.475) | -- |
| UART_FT_DTR# U2-43<->track (29.12) | CHAN10 at (51.8-51.925,11.45-11.5) | -- |
| UART_FT_RTS# U2-40<->track (33.16) | CHAN10 at (47.575-47.7,17.95) -- the north band over U1 | -- |
| UART_FT_TXD U2-38<->track (31.73) | CHAN10 at (47.575-47.7,17.95) | -- |
| FLASH-D01 U4-2<->U1-D19 (13.17) | FLASH-D03 track<->U4-7 at (51.825-51.925,14.425-14.525), 162 cells | knots/ne_d closed 6 of 11, ne_s2 4 of 11: D01 closes only when D03 or JA8 opens instead |
| FLASH-D03 track<->U4-7 (8.38) | FLASH-D01 at (51.725-51.85,14.6) | closed in ne_d / test3_ne when D01 lost |
| JA8 U1-E19<->R31-2 (12.00) | FLASH-D03 at (51.25-51.375,14.175-14.225); its route damages 28 witnesses | orders ne_s2 / ne_d |
| UART_FT_RXD U2-39<->U1-G19 (29.04) | `no route on the lattice (after 1 exact retries)`: the last corridor into G19 rides own UART_FT_RXD copper 0.02 mm too close to the GND via (51.4,13.9), exact slack -0.0203 -- raster-legal, exactly illegal | closed in test2_ne / test3_ne / run1 under a different commit order -- **order-dependent, and the one connection whose "not walled off" is not proven** |

**B. The south band under the W row, x 46.8-50.3, y 2.3-7.2 -- 14 connections.** One lane per stub column and every
X2-to-W-row connection needs one; the 0.4 mm pocket south of balls W9/W10 (x 45.95-46.35, y 6.6-7.05, only 0.3 mm at
y 6.9) must hold FPGA-TDI (placed by the plan), FPGA-TMS and RST# -- three 0.0762 tracks at exact lanes
45.975/46.15/46.325 (0.175 pitch, 0.009 mm margins), never achieved on the 0.1, 0.05 or 0.025 mm lattice.

| connection | walls off / reason | tried beyond the ladder |
|---|---|---|
| CHAN16 X2-26<->U1-W16 (7.23) | CHAN18 X2-28<->track at (46.85-46.975,2.55-2.6), 262 cells | bare-board knot test knots/chan: 2 of 6 |
| CHAN18 X2-28<->track (12.70) | CHAN16 at (47.000,2.325-2.45), 324 cells | -- |
| CHAN19 X2-29<->U1-W15 (88.95) | CHAN16 at (49.225-49.325,6.125-6.75) | knots/chan |
| CHAN20 X2-30<->track (82.79) | CHAN16, same cells | -- |
| CHAN23 X2-33<->track (75.24) | CHAN16 at (49.000,5.5-5.775) | -- |
| CHAN25 X2-35<->U1-W13 (76.44) | CHAN16 at (49.000,5.5-5.775) | knots/chan; budget spent (114) in one chunk |
| CHAN26 X2-36<->track (77.39) | CHAN16 at (49.000,5.5-5.675) | knots/chan |
| CHAN13 X2-16<->U1-W18 (53.94) | CHAN15 X2-25<->track at (50.15-50.2,6.75-7.15) -- the W18/W19 stub lanes | -- |
| CHAN15 X2-25<->track (9.45) | CHAN13 at (50.15-50.3,6.75-6.9) | -- |
| FPGA-TMS U1-W9<->R4-12 (24.51) | CHAN16 at (48.500,4.375-4.5) | first in orders sw_2 / sw_s1: then FPGA-TDI is arbitrated first and TMS still finds no lane; sw_1/sw_2 closed 1 of 6, sw_3 2 of 6, sw_d1/d2 3 of 6, sw_s1/s1b 1 of 6 |
| RST# track<->X2-23 (14.81) | FPGA-TMS at (46.000-46.05,6.5-6.65) -- the W9/W10 pocket | 0.025 mm runs sw_s1/sw_s1b, default-lattice sw_d1/sw_d2: TMS and RST# never both |
| LED0_B LD0-2<->U1-N19 (57.09) | CHAN16 at (48.500,4.35-4.475); its 62.7 mm / 24-via route damages 19 witnesses | -- |
| LED0_R LD0-4<->U1-P19 (56.09) | CHAN16, same cells; 61.8 mm, 19 witnesses | -- |
| LED0_G LD0-6<->track (56.77) | CHAN16, same cells; 61.2 mm, 19 witnesses | -- |

**C. U1's east edge at y 8.5-8.7, x 51.5-52.2 -- 5 connections.** One lane for JA1 / JA2 / CHAN27 / CHAN-CLK / CHAN28.

| connection | walls off / reason | tried |
|---|---|---|
| JA1 track<->R26-1 (13.56) | CHAN27 X2-37<->track at (51.75-51.875,8.5) | 0.05/0.025 rungs, detour 6 |
| JA2 U1-U19<->R27-1 (7.98) | CHAN27, same cells | detour 6 |
| CHAN27 X2-37<->track (70.78) | JA1 at (51.525-51.65,8.55-8.65) | -- |
| CHAN-CLK track<->X2-2 (24.61) | CHAN27 at (52.1-52.225,9.95) | detour 6, no route |
| CHAN28 X2-38<->U1-R19 (72.97) | CHAN27 at (28.325..,7.75), 952 cells -- its 73 mm witness circles the board | closed on the bare board in knots/chan |

**D. The R10/R11 lane at y 2.3-2.45 and the R14/R15 channel -- 3 connections (2 signal + the R15-1 tie).**

| connection | walls off / reason | tried |
|---|---|---|
| NODE_P0 R10-1<->R11-2 (3.19) | NODE_P0 R12-2<->R10-1 at (45.000,2.300): the two NODE_P0 links and ANALOG-IO0/IO1 share the one lane under R10/R11 (ANALOG-IO0/IO1 were arbitrated first, 44 and 47 mm) | pass A/B |
| NODE_P0 R12-2<->R10-1 (95.24) | NODE_P0 R10-1<->R11-2 at (45.0,2.3) (47.0,2.6); its own route is 95-110 mm around the board | pass A/B |
| GND R15-1 tie, Bottom (43.75,3.95) | **my re-measure (`u2_5_r15.py`, inputs only):** NODE_P1's stage-8 Bottom track (43.17,2.42)-(43.17,3.65) w 0.0762 and the AIN16_P pad C37-2 0.7x0.9 at (43.95,3.05) (x 43.600-44.300, y 2.600-3.500) leave a free centre-line band of **x 43.3362..43.4719 = 0.1357 mm** for a 0.0762 track at 0.09 clearance -- one track, not two (two need 0.1662). North of the R14/R15 pads (top edge y 4.0999) the D6/D5/D3/D1/D2/D0 through-via row at y 4.4 (lands to y 4.225) leaves 0.125 mm, less than one track needs; west is NODE_P1's own copper (R14-1 pad, the (42.55-43.17, 3.65) track). So that channel is R14-2's only exit (ANALOG-IO1 X2-40<->R14-2, closed by the plan) and R15-1's only exit too. Widening it to two tracks needs NODE_P1's run at x <= 43.1395 while the AIN16_N stub end (42.98,2.90) needs it at x >= 43.1462: a 6.7 um conflict, i.e. two placed-copper removals, more than the one the addendum allows. `tie_r15.log` (agent) and `review/tie_r15.log` (reviewer, own copy): 33 GND joins on Bottom within 6 mm, nearest first (R12-? tracks 1.64 mm, R11-1 pad 2.51 mm, the via (46.575,3.225) 2.92 mm, ...), every route `commit False walls off ANALOG-IO1 X2-40<->R14-2`; `AssertionError: no R15-1 tie commits under full witness protection`. The U2S agent's tie (`ties_u2s.json`, through the channel at x 43.45 and along y 2.45) walls off NODE_P0 x2, ANALOG-IO0 and ANALOG-IO1 -- refused by `gen.py`'s `lay_base`. | **User decision on this placement: the R15-1 tie OR ANALOG-IO1 X2-40<->R14-2, not both** -- or the two-removal edit of NODE_P1 + the AIN16_N stub with replacement copper. |

22 + 14 + 5 + 3 = 44.

## 5. My corrections to the record

1. **`route_foreclosure` FAIL names no open connection.** FLASH-D02 is JOINED by the plan (both DRC links closed:
   Top tracks (50.15,13.05)-(50.4001,13.4) off the ball and (50.6501,13.65)-(50.65,13.575) off the stub corner,
   `signals_check` lists no FLASH-D02 split). The tool enumerates escapes from `fanout_plan.json` actions, not from the
   routed state, and counts EVERY via against a slot (`slot_mask`: `for v in vias`, no own-net exclusion), so the G18
   stub-end (51.1125,13.65) reads 0 slots because of the plan's PUDC_B buried via at (51.35,13.175) 0.531 mm away and
   PUDC_B's L4 tracks 0.2 mm away -- the net no longer needs that slot; what remains is a 0.46 mm dangling Top stub
   (51.1125,13.65)-(50.65,13.65), electrically harmless. D10 (ball K2) and D15 (ball A15) are routed SDRAM nets, absent
   from the DRC's 140: K2's stub continues on Top to (41.2,12.14), A15 goes to its own through via at (48.9,16.8); their
   slot loss (the plan's SD-CLK Bottom stack at 0.405 mm, CHAN5 Bottom stack at 0.57 mm) matters only if the placed
   SDRAM bus were ever ripped up. Formal FAIL; substantively no foreclosure. (Tool improvement for a later stage: skip
   escapes of joined nets and exclude the escape net's own vias from the slot count.)
2. **`plane_islands` EXIT 1 is the reportable heuristic, not an island failure**: both planes are one island (100 %),
   which is the brief's pass criterion; the two OFF-PLANE pads are a Bottom pad (C115-2) and a Top ball (U1-K1) whose
   centres project into the L2 / L5 antipad of a laser stack that never touches their own layer.
3. **`route_width` EXIT 0 is not a pair-rule pass** (section 2): the USB pair fails the brief's coupled 0.150/0.150
   requirement outright, and the report's own "usb_pair" paragraph says so -- the VERDICT line listing route_width
   among the passes should not be read as the pair being acceptable.
4. `pass A: closed 4 of 138` in `run2/gen.log` is the last chunk's count only; pass A closed 95 in all (the chunked
   log prints the per-chunk `res`). The pass-B line `closed 0 of 43` is the whole pass.
5. The reviewer's three corrections stand (section 3).

## 6. Why not PLACE-PARTIAL (the 96)

1. **It freezes the order that keeps the 44 open.** UART_FT_RXD U2-39<->U1-G19 closed in test2_ne/test3_ne/run1;
   FLASH-D01 closed in 3 of 5 NE runs (losing D03 or JA8 instead); CHAN28 closed on the bare board; the SW pocket
   closes TMS or RST# but never both. Each of those needs a different commit order over routes the partial placement
   would make immovable. A later "route the remaining 44" would start from a strictly worse position than this run did.
2. **It places a stated hard-boundary violation** (3 laser-laser thin webs, 8 laser-through, 57 merged pairs) that no
   gate would catch on the board either.
3. **It places the USB pair single-ended at 0.0762 mm** -- an Altium DRC violation on the board's DiffPairsRouting
   0.150/0.150 rule the moment it lands, and a re-route of the pair later would have to rip plan copper.
4. **"Nothing walled off" is not proven for the six open connections of nets the plan touches**; for UART_FT_RXD the
   surviving witness is exactly illegal by -0.0203 mm (the agent's own measurement), so placing may leave U2-39<->G19
   with no exactly-legal corridor at all.
5. `route_emit --require-complete` is clean and every added object is legal, so the copper itself is placeable -- the
   reason not to is what it forecloses, not what it is.
6. The user asked for the complete board. 96 of 140 on HDI, against 92 of 140 through-only at stage 4b and the stage-9
   through plan (86 of 140, not placed), is progress of +4..+10 connections for a $309 order (+66 % over the $186
   standard board, `docs/hdi_gain.md`), and the survivors are the same local knots docs/hdi_gain.md named before this
   stage started. That is information the user should have before any copper moves.

## 7. What next (in order, all measurable, none placed)

1. **Decide R15-1**: tie it (and leave ANALOG-IO1 X2-40<->R14-2 open on this placement), or keep ANALOG-IO1 (and leave
   R15-1 untied), or authorise the two-removal edit: NODE_P1's Bottom run (43.17, 2.42-3.65) moved to x <= 43.1395 and
   the AIN16_N stub (42.65,3.05)-(42.98,2.90) re-drawn so its end sits at x <= 42.973, both with replacement copper in
   the same plan. Only then can a plan reach 140.
2. **Give the router a differential mode** (or hand-plan the USB pair at 0.150/0.150 with 0.150 gap, then protect it
   as a base plan) before anything is placed; today the pair's only "pass" is a width tool that measures each track alone.
3. **Add a web gate** (`judge/webs.py` is a starting point: laser antipad 0.48, through 0.53, report every foreign-net
   pair with 0 < web <= 0.03 mm) to the gate set, and re-site the three laser-laser offenders (TMS (36.5,7.8) or CHAN24
   (37.0,7.85); N$LD0R (29.7,13.4) or N$LD1A (29.2,13.4); FPGA-TDO (45.7,5.8) or CHAN22 (45.2,5.9)) -- each is a
   0.1-0.2 mm move of one via site, then `gen.py --check` no longer applies and every gate must be re-run.
4. **Close the raster-vs-exact gap in the instrument**: `route_reach.py` and the stage-9 witness cache still free every
   cell under own copper; port `inset_own_cells` there so a witness is exactly legal, then re-warm the cache (the
   `%TEMP%/route_reach_board_565af2dd...json` key changes with the raster rule).
5. **Then one more global run** with a commit-order search restricted to the four corridors of section 4 (22 + 14 + 5
   + 2 connections) on top of the rest of this plan held as base -- the only order-dependent connections are in A and
   B, and a full 138-permutation search is 84 min per sample. Where a corridor holds one lane for N stubs (the A16-A18
   Top lane, the W-row pocket, the JA1/JA2/CHAN27 edge), no order closes all N: report those as the placement-limited
   set with the smallest move that opens a second lane (the stage-10 brief's phase-2 measurement, which the addendum
   deferred, is still the honest answer for the W9/W10 pocket and the NE column -- see `docs/hdi_gain.md` for U4 / R20 /
   R21 / R23).
6. Only after 1-5 does a PLACE or PLACE-PARTIAL become a question; if the user wants copper on the board sooner, the
   safest partial is the plan minus the USB pair and minus the three re-sited via stacks, re-gated -- not this file.

## 8. Evidence index

- Plan and run: `global/plan.json` (md5 a1ed28d5...), `global/global_result.json`, `global/run2/gen.log`,
  `global/check/chunk*.log` (agent's --check), `review/check/chunk*.log` + `loop.log` (reviewer's --check),
  `global/gen.py`, `global/router_fine.diff` (322 lines), `global/engine_fine.diff` (69 lines), `global/ties.json`.
- Gates: `global/run_gates.sh`, `global/gates/*.log`, `global/gates/tails.txt`, `global/gates/PlaceStage10.pas` (read
  only), `review/gates/*.log`, `review/gates_bare/*.log` (bare board), `review/audit.py` + `audit.log`.
- Diagnosis: `global/diag/state_open.log`, `review/state_open.log`, `global/knots/*/log`, `global/orders/*/route.log`,
  `global/tie_r15.log`, `review/tie_r15.log`, `global/ties_u2s.json`.
- Instrument: `instrument/commands.sh`, `instrument/logs/synth_route_emit*.log`, `pitch_proof_old/new.log`;
  `diff -rq instrument/tools tools/`: only hdi.py, route_emit.py, stage6/plane_islands.py differ.
- Judge: `judge/webs.py` + `webs.log` (void webs), `judge/u2_5_r15.py` + `u2_5_r15.log` (U2-5 tie clearances, the
  R14/R15 channel), this file.
