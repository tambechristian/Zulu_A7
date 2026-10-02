# Stage 12: 136 of 140 -- DO-NOT-PLACE; the last four are sealed in U1's east field (2026-10-01)

**Nothing placed.** Workflow wf_d7b08600 (close, review, judge; 1.45M tokens, 12.6 h). Plan
`scratchpad/stage12/close/plan.json` md5 `594166d3921a5f29f045f2546f90855b`, `gen.py --check` byte-identical over
the whole chain from the 11b warm state; Pascal in 5 chunks <= 389 KB. Structured result: docs/stage12_close.json.

| stage | closed of 140 |
|---|---|
| stage 10 (square-pad gates) | 96 |
| stage 11b (round-pad gates) | 131 |
| **stage 12 (XADC L3->L4 lever, 7 bank-14 swaps, defects fixed, smoothed)** | **136** |

PASS: route_emit --require-complete clean; tie_check 129/129; gnd_check 206/206; plane_islands L2 216/216 + 135/135
and L5 133/133 + 86/86 (EXIT 0 -- the off-plane lasers are fixed); webs; USB pair coupled (15.22 mm coupled,
1.86 mm uncoupled, skew 0.0001); SDRAM via rule (+0.0022 mm); via land to outline 0.825 mm; 0 tracks < 0.02 mm
(2221 tracks, 3083 mm, was 7014 with 3418 staircase fragments). FAIL: signals_check and route_reach -- **LED0_R
(U1-P17), UART_FT_TXD (K17), CHAN9 (J17), CHAN6 (H17) are sealed in Top-only pockets inside U1's land field** by the
plan's own copper (0 of 4 routable even from the balls), and the plan removed their col-16 dogbones. 40+ repair
seeds, a 114-candidate swap screen (0 gave 3 open) and the judge's sealer survey put 4 as the floor of the
measured levers. Two of the seven swaps (LED0_R P19->P17, UART_FT_TXD K18->K17) are not earned -- they moved
those nets onto balls that are now sealed.

Two ways on, per the judge: **A** (a product decision for the user) defer UART flow control RTS#/DTR#/CTS#, LED0_R
and CHAN6 -- candidate `lev/F0/fc4_plan.json` closes 134 of the 136 still required, UART_FT_TXD included; **B** (taken
under the standing authorisation, stage 13) structural levers in U1's east field: east-field GND through vias with
only a Top fan-out become Top>L2 microvias, the XADC supplies routed around the field, LD0 relocated, the two
unearned swaps revisited, rows D-T x columns 14-19 re-negotiated.

---

# Stage 12 judge: 136 of 140 on HDI -- DO-NOT-PLACE (2026-10-01)

Directory `scratchpad/stage12/judge/` (S12 = `.../scratchpad/stage12`). Plan judged: `S12/close/plan.json`, md5
`594166d3921a5f29f045f2546f90855b` (`md5sum`; my copy `judge/plan.json` is identical). Gate inputs: `inputs_gate.json`
md5 `269c16709cdfa0ee144bde289e392df6`, `drc_gate.drc` md5 `859444b17b7ab5be892980eaebcd8659` (copies in `judge/`).
Board and sources, all by `md5sum`:
- PcbDoc `c927413f3422a37f230e78ac3de58942`
- `tools/route_inputs.json` `67f6464a93d48498da41268f0105e24b`
- `vivado/zulu_a7_pins.xdc` `2b81f24d36494236755c919bc63b9432`
- `docs/drc_hdi_rules_2026-09-29.drc` `6dfcfe48589a7c8d1879ec6162b57116`
- `zulu_a7_5.SchDoc` `05c093fdce41ff79ffaebcc8dda3c866`

`judge/tools` is `diff -rq`-identical to the repo's `tools/`, and `git status --short tools` is empty.

Boundaries kept:
- No Altium, no computer-use.
- No edit to tools/, the PrjPcb, the XDC or the schematic. The XDC and the SchDoc were only read, and their md5s are
  unchanged at the end.
- No git commit; `git status` is as at the session start.
- Never `--write`: route_emit was imported for `check()` and run with `--pas` into `judge/` only.
- No pictures.

Everything I wrote is in `judge/`, with one exception: route_reach's own board cache, which the tool writes to the
system temp directory. The lever probes ran copies of the plan's engine inside `judge/lev/`, and all of them were
stopped at 13:54. No file in `close/`, `review/`, `stage11*/` or `stage9/` is newer than my copy of the plan.

## 0. The verdict

**DO-NOT-PLACE.** These numbers force it:

| test | result | command (in `judge/`) |
|---|---|---|
| closed of 140 | **136**. Open: LED0_R LD0-4<->U1-P17, UART_FT_TXD U2-38<->U1-K17, CHAN9 X2-12<->U1-J17, CHAN6 X2-9<->U1-H17 | `python uf_judge.py inputs_gate.json docs/drc_hdi_rules_2026-09-29.drc plan.json` |
| signals_check (brief: every signal net one island) | 170 joined, 5 split (the 4 nets + VCC3V3's 86 bare-board islands), **EXIT 1** | `sh run_gates.sh plan.json g_plan` |
| route_reach (brief: nothing open) | board 4/4, **with the plan 0/4**, EXIT 1 | same |
| route_reach with the U1 **balls** as endpoints | board 4/4, **with the plan 0/4** | `python tools/route_reach.py --inputs inputs_gate.json --drc drc_balls.drc plan.json` |
| placed copper of the 4 open nets that the plan removes with no replacement | **4 through vias + 4 Top stubs** at x 49.4001 (y 9.8999 LED0_R, 11.8999 UART_FT_TXD, 12.4 CHAN9, 12.8999 CHAN6) | `plan.json` `remove`; `removals_listing.txt` |
| keep those 8 objects | route_emit **37 problems** | `carve.log` iteration 1 (reviewer: `keep_dogbones_emit.log`, the same 37) |
| the nearest legal partial that keeps them | **121 / 140**, 19 open; route_reach still **18/19** (CHAN10 walled off) | `python carve.py ...`, `uf_carve.log`, `reach_carve.log` |

The plan fails both placeable criteria:
- **Not PLACE.** Four connections are open, and two of the brief's ALL-must-pass gates fail: signals_check and
  route_reach.
- **Not PLACE-PARTIAL.** By 11b's standard, a partial must wall off nothing it leaves open and must remove no placed
  copper without replacement. This plan does both:
  - It walls off all four open connections. This is not an endpoint artefact: with the U1 balls themselves as
    endpoints, the result is still 0/4.
  - It repeats 11b's defect in a new place: the col-16 dogbones of the four open nets are removed and nothing
    replaces them.
- **Carving does not rescue it.** The cheapest carve that keeps those dogbones has to drop 12 more nets (121/140) and
  still walls off CHAN10.

Placing copper now would also freeze exactly the region (U1's east land field) where every remaining lever acts
(section 6).

The plan is very good otherwise:
- Every other gate passes.
- Every gate and census number the plan reports reproduces (section 2), and so does `gen.py --check`.
- Two search-history figures do not reproduce (section 4).

It is the right warm start for the next stage.

## 1. Closed = 136, established three ways

| count | source |
|---|---|
| **closed 136, open 4**, strict endpoint-only joins and also with T-joins, 0 islands holding pads of two nets; empty-plan baseline 0 / 140 | my own union-find, written from scratch (`uf_judge.py`): geometry-only joins, plane nodes for GND/VCC3V3 vias spanning L2/L5, original DRC (140 Un-Routed lines), final ball map from the 13 XDC edits. Logs `uf_plan_strict.log`, `uf_plan_tjoin.log`, `uf_empty.log` |
| 4 signal nets split (CHAN6, CHAN9, LED0_R, UART_FT_TXD) | `tools/stage6/signals_check.py` (`g_plan/signals_check.log`) |
| closed 136, open 4 (strict and T-join); empty plan 0 / 140 | reviewer's `review/uf_rev.py`: `review/uf_plan.log`, `uf_plan_strict.log`, `uf_baseline.log` |

I count no GND among the open. Without the plane nodes my count is 134: the two extra are the U2-5 and R15-1 GND
ties, which close through L2 (gnd_check 206/206).

## 2. Every gate, re-run by me

Command: `sh judge/run_gates.sh judge/plan.json judge/g_plan`, 2 min 20 s (`g_plan_run.log`). It uses the repo tools
copy plus the author's helper scripts, copied unchanged.
- Every log is identical line for line to the author's `close/gates_v11` once the directory paths are stripped (`diff`
  of each log).
- The five `.pas` files are byte-identical (`cmp`).

| gate (brief) | my result | reading |
|---|---|---|
| route_emit `--require-complete` | `824 vias, 2221 tracks / geometry and connectivity check: clean / removes 8 existing via(s) and 63 track(s)`, EXIT 0 | PASS |
| `--pas` in chunks | 5 chunks: 387888 / 388896 / 367823 / 384122 / 290515 bytes, each route_emit EXIT 0; 109 nets, no net in two chunks; chunk 01 carries the guard `Kill.Count <> 71` | PASS |
| signals_check | 170 joined, 5 split, EXIT 1 | **FAIL** (4 signal nets) |
| tie_check VCC3V3 | 129 / 129 tied, EXIT 0 | PASS |
| gnd_check | GND SMD pads 206, tied 206, EXIT 0 | PASS |
| plane_islands L2 | 216/216 GND pads, 135/135 GND vias on the main island, EXIT 0 | PASS (11b's 4 off-plane pads fixed) |
| plane_islands L5 | 133/133 pads, 86/86 vias, EXIT 0 | PASS |
| webs | `WEBS PASS: 0 plan-involved thin web(s)`, EXIT 0 | PASS |
| route_foreclosure | `pads foreclosed by the plan(s): none`; ball-slot section EXIT 1 | PASS on the brief's criterion (no pad foreclosed); its ball table is stale (section 4) |
| route_reach | board 4/4, plan 0/4, EXIT 1 | **FAIL** |
| route_stitch / capacity | EXIT 0 / EXIT 0 (U1 east cut x 52.9: 398 -> 212 lanes) | reports |
| USB pair | 17.0808 mm each, coupled 15.2245 at 0.300 pitch, uncoupled 1.8563 / 1.8562 (limit 3.0), skew 0.0001; route_width P 0.200, N 0.225, EXIT 0 | PASS |
| via land to outline | worst 0.8250 mm over 824 plan vias (rule >= 0.80) | PASS |
| short tracks | 2221 tracks, 3083.356 mm; 53 < 0.08 mm; **0 < 0.02 mm** | PASS |
| SDRAM 0.10 via rule (stage-local) | worst slack +0.0022 mm (N$LD0G (31.80,16.25) vs D10) | PASS |

Census (`extra.log`):
- 824 via records -> 1292 Altium via objects: 239 Top>L2>L3 lasers, 229 Bottom>L5>L4 lasers, 326 buried L3/L4,
  30 through.
- Widths: 0.0762 x 2181, 0.15 x 30, 0.16 x 2, 0.2 x 8.

## 3. The brief's defect list

| defect (11b judge) | status | measurement |
|---|---|---|
| 12 stub tracks of 6 open nets removed without replacement | **fixed for those 6** (CHAN2, FLASH-D03, UART_FT_RTS#, CHAN-CLK, CHAN27, CHAN18 all joined) -- **but recurs**: 4 through vias + 4 Top stubs of the 4 now-open nets are removed with no replacement | `uf_plan_strict.log`; `removals_listing.txt` |
| duplicate UART_FT_CTS# track | exact duplicates 0; **3 collinear same-net overlaps + 1 plan track lying over a placed track** remain | `overlaps.log` (section 4) |
| 4 lasers voiding a pad centre off-plane | fixed: L2 216/216, L5 133/133, EXIT 0 | `g_plan/plane_L2.log`, `plane_L5.log` |
| 2 lasers < 0.10 from SDRAM vias | fixed: worst slack +0.0022 mm | `g_plan/extra.log` check 4 |
| 3418 of 7014 tracks < 0.08 mm | fixed: 53 < 0.08, 0 < 0.02 | `g_plan/extra.log` check 2 |
| 3.8 MB Pascal | fixed: 5 chunks, largest 388,896 bytes | `g_plan/route_emit_pas.log` |

All removals check out (`removals_listing.txt`):
- 63 tracks + 8 vias in total:
  - 14 XADC L3 segments (authorised);
  - 5 corridor D (11b);
  - 36 ring-1 stubs (18 nets x 2);
  - 8 col-16 dogbone stubs + 8 through vias.
- No SDRAM or power copper is removed besides the authorised VCCADC/GNDADC move.
- The nearest removal is 7.864 mm from a C155-C159 pad.

## 4. The reviewer's refutations -- adopted, both re-measured; plus my own corrections

1. **Overlaps** (re-measured, `python overlaps.py inputs_gate.json plan.json`):
   - plan-plan, 3 pairs: SD-DAT3 Top 0.3251 mm, UART_FT_CTS# Top 0.1768 mm, FPGA-DONE Top 0.0719 mm;
   - plan-board, 1 pair: UART_FT_CTS# Top (49.1501,16.15)-(49.1501,16.6251) over the placed track
     (49.1501,16.15)-(49.1501,16.6125), 0.4625 mm.

   **Adopted.** None of these is a DRC violation, and the endpoint-only count is unaffected. They are cosmetic leftovers
   to be dropped by the successor's smoother.
2. **route_foreclosure's ball table is not swap-aware.** **Adopted.** My log still names the swapped balls by their
   old nets: W19 CHAN12, W18 CHAN13, R19 CHAN28, H19 CHAN7, E19 JA8, P19 LED0_R, N19 LED0_B, K18 UART_FT_TXD. Those
   names come from `tools/fanout_inputs.json` and `fanout_plan.json` (lines 56-57, 123-124).
   - The 4 open balls (col 17, ring 2) are not in its escape table at all, because their escapes were placed dogbones.
   - So this gate cannot see the open four; route_reach does.
3. **Swap-screen tally** (mine, `cat close/scr/*/result.txt`): 114 candidates gave **64 at 4 open, 50 at 5, 0 at 3**.
   The plan's "53 / 36" matches the 89 result files that existed by 09:42:41 (file times), so it was an interim
   count. The "none gave 3" conclusion stands.
4. **v16b is an empty directory.** The "v16a/b/c (4)" evidence is v16a and v16c only. v15 (CHAN6/CHAN9 dogbones kept)
   starts at 5 open and makes no move in 2-3 attempts per seed.
5. **route_reach's 0/4 is not an endpoint artefact.** The DRC endpoints of the 4 are the removed dogbone vias. With
   the U1 balls as endpoints (`drc_balls.drc`), it is still 0/4 with the plan and 4/4 on the board.
6. Confirmed read-only, which the reviewer had left open:
   - **All 13 schematic label claims match** (`python sch_check.py zulu_a7_5.SchDoc`): every U1 pin has the claimed
     label at the claimed coordinates, 30 units from the pin. The next-nearest label is a neighbour's at 31.6, so the
     wire, not proximity, must be what compare_netlists proves in Phase II.
   - **All 13 XDC lines** read as the plan lists them (`sed -n`).
   - The 13 from-balls and to-balls are the same set (a permutation).
   - All 13 are bank 14 IO.
   - **Every VCCO on U1 is VCC3V3** (B19/C14/C18/G13 = VCCO_16, F17/K12/K13/L12/L13/M12/M17/R17/U13 = VCCO_14), and
     **all 101 XDC ports are LVCMOS33**.

## 5. Why not PLACE-PARTIAL: the carve, measured

`python carve.py inputs_gate.json plan.json carve_plan.json LED0_R UART_FT_TXD CHAN9 CHAN6` (`carve.log`). The method:
- Keep every placed object of the four open nets.
- Then, repeatedly, drop whole every plan net named by `route_emit.check`, keeping its placed copper as well, until the
  check is clean.

| iteration | nets kept placed / dropped | problems | newly named |
|---|---|---|---|
| 1 | 4 | 37 | CHAN7 CLK-12M-FPGA LED0_B LED2 SD-CMD UART_FT_DTR# UART_FT_RTS# |
| 2 | 11 | 5 | CHAN11 FPGA-DONE SD-DAT0 |
| 3 | 14 | 5 | CHAN8 |
| 4 | 15 | 4 | CHAN10 |
| 5 | 16 | **0** | -- |

Result:
- **121 closed, 19 open** (`uf_carve.log`).
- route_reach **18 / 19** routable; CHAN10 X2-13<->U1-J19 is walled off (`reach_carve.log`).

So no clean partial exists near this plan. The nearest one gives back 15 closures and still walls off a connection.
A placed partial could also never make the last ones easier: the copper it fixes is a subset of a solution that could
not close them while everything was still free.

## 6. Where the four are stuck, and what that means for the levers

**A wall inside U1's land field, not a band outside it.** I ran single-net reachability in route_reach's own model
(`python reach_diag.py inputs_gate.json drc_balls.drc plan.json`, `reach_diag_plan.log`):
- Each far end (LD0-4, U2-38, X2-12, X2-9) reaches **4.92-4.93 M** free cells over the whole board on all four layers.
- The U1 ends are sealed in pockets:

| ball | open net | free cells reachable with the plan |
|---|---|---|
| K17 | UART_FT_TXD | **170**, Top only, nothing outside U1's land field |
| J17 | CHAN9 | **225**, Top only, nothing outside the field |
| H17 | CHAN6 | **241**, Top only, nothing outside the field |
| P17 | LED0_R | **77,251**, on Top/L3/L4 inside the field; only 149 L3 cells lie outside it |

- On the bare board (dogbones in place) each U1 end reaches about **6.87 M** cells (`reach_diag_board.log`).
- The east cut itself still has room: `capacity.py` gives 212 of 398 lanes free at x 52.9 with the plan.

So the binding resource is **in-field escape for the ring-2 (column 17) east balls**. That refines the plan's "NE funnel
/ SW band" reading, which describes where the soft paths collide once a ball is out.

**The sealers are few and local** (`python sealers.py inputs_gate.json drc_balls.drc plan.json`, 74 candidate nets;
`--sets` for named groups, `lifts.log`). Lifting one plan net's copper opens an open net, one net at a time:

| open net | single lifts that open it |
|---|---|
| CHAN6 | CHAN11, CHAN7, CLK-12M-FPGA, UART_FT_RTS# |
| CHAN9 | CHAN11, CLK-12M-FPGA, LED2 |
| UART_FT_TXD | CHAN11, LED2, UART_FT_RTS# |
| LED0_R | 16 nets, including GNDADC (the new L4 XADC run) |

| lifted set | open nets that become routable |
|---|---|
| CHAN11 | CHAN6, CHAN9, UART_FT_TXD |
| LED2 + CHAN11 | all four |
| UART_FT_RTS# + UART_FT_DTR# (with or without CTS#) | CHAN6, LED0_R, UART_FT_TXD |
| GNDADC | LED0_R |
| VCCADC | none |

This is necessary, not sufficient, because each open net is tested alone. The contention is the rows G-M of the east
columns: K18 CHAN11, M19 LED2, L18 RTS#, M18 DTR#, L17 CLK-12M-FPGA and G17 CHAN7.

**What that says about the levers:**
- **Another ball swap, in bank 14 or bank 16, cannot add an in-field site.** It only changes which net sits in a sealed
  pocket.
  - Bank 16 is electrically legal (all VCCO 3.3 V, all LVCMOS33, section 4), but its balls are the NE-corner rows
    A-C, which have their own north escapes.
  - The 114-candidate bank-14 screen found 0 improvements, which is consistent with this.
  - I do not recommend more swap screening.
- **Re-pathing the XADC supplies onto one other layer is not available** (`python xadc_bottom.py inputs_gate.json
  <plan> <layer> <width>`). VCCADC and GNDADC do not connect between their existing through vias on Bottom, at 0.15 or
  0.20, with the plan or even on the bare board. On L3 with the plan they do not connect either. A different XADC path
  would be a re-negotiation item, not a swap of layers.
- **Real routing probes with the plan's own engine.** I copied `close/gen_out/F_led1_stub` unchanged to
  `judge/lev/F0`.
  - The start state is the plan's final committed state:
    `python fixopen.py st03_repair3/committed_state.json st_open.json`, which gives routes 128, open 4.
  - Each lever is applied to that state, then run with
    `PYTHONHASHSEED=0 python -u pf/repair3.py --state=<lever state> --out=<run> --fixed_extra=hand_D.json,xadc_l4.json
    --seed=N --iters=24 --budget=1e9 --anneal=0.15 --via_edge=0.80 --depth=2 --improve=0 (0.3 for FC seeds 4-6) --top=15
    --gain=1.0`.
  - A "deferred" net (`lev/defer.py`) has its routes dropped, and its connections are never required.
  - All runs were stopped at 13:54. The table below is `lev/probe_summary.txt`; rejected-insertion costs come from the
    `undo` lines of the run logs.

| lever | its cost | runs | best open per run |
|---|---|---|---|
| **UART flow control deferred** (RTS#, DTR#, CTS#: 4 connections) | product scope, stage 9's open question 1 | 12 seeds, 6-12 attempts each | **2** in 11 of 12 (one at 3). The remaining pair varies: {LED0_R, CHAN6} in 5 seeds, {LED0_R, UART_FT_TXD} in 3, {UART_FT_TXD, CHAN9} in 3. Rejected insertions still cost at least 2 others (LED0_R 22 tries, UART_FT_TXD 17, CHAN6 18). |
| CHAN11 + LED2 deferred (2 connections) | product scope | 4 seeds, 6-8 attempts, stopped 13:36 | 2 (one seed), 3 (three seeds). **No net gain**: 2 deferred + 2 open. |
| Bottom-reaching lasers allowed in U1's field (`land_field_ban` false on L4/L5/Bottom; `lev/F1`) | the user's land-field constraint (HDI spec item 7) | 4 seeds, 3-4 attempts | **4: no gain.** Single net (`reach_diag_bottomok.log`), it grows only P17's pocket (77,251 -> 97,370 cells) and cannot touch the three Top-only pockets. |

  **The flow-control state is a real plan.** I turned seed 4's best state (`lev/F0/fc4_best_state.json`, md5
  `09c0abbf...`) into a plan exactly as gen.py does (final.py, smooth.py, assemble.py): `lev/F0/fc4_plan.json`, md5
  `364f980eea5514ef82bab16adb46296d`. It has 2194 tracks and 806 via records, and its final.py exact check gave 126
  committed, 0 refused.

  | check (`lev/g_fc4/`, `lev/uf_fc4.log`) | result |
  |---|---|
  | route_emit `--require-complete` | clean |
  | `uf_judge.py` on the original DRC minus the 4 flow-control lines (`lev/drc_orig_noFC.drc`) | **134 of 136**: only LED0_R and CHAN6 open, both DEFER class; 0 shorts; **every other connection of stage 9's MUST set is closed**, including UART_FT_TXD (the 4 flow-control connections are the ones deferred) |
  | gnd_check / plane L2 / plane L5 / webs / extra gates | 206/206, EXIT 0, EXIT 0, PASS, PASS |
  | route_reach | 0/2 for the two open (walled off) |

  So deferring flow control buys UART_FT_TXD (MUST) and CHAN9, but not completion. That is not a PLACE either.

## 7. Phase II change list

**NOW: nothing.** No XDC or schematic edit, no ECO, no re-net, no removal, no placement, no part move.

**CARRY-FORWARD**, in apply order. It is the exact list this plan implies; apply it only with a successor plan that
closes 140 and passes every gate, and re-derive every line from that plan.
1. **XDC** `../vivado/zulu_a7_pins.xdc` (md5 `2b81f24d...`): 13 `PACKAGE_PIN` edits, IOSTANDARD unchanged; update
   each trailing comment to the new pin name.
   - line 80 JA3 G17 -> **W18** (IO_L16P_T2_CSI_B_14)
   - line 49 CHAN7 H19 -> **G17** (IO_L5N_T0_D07_14)
   - line 28 CHAN13 W18 -> **H19** (IO_L4P_T0_D04_14)
   - line 82 JA7 T17 -> **R19** (IO_L10N_T1_D15_14)
   - line 44 CHAN28 R19 -> **T17** (IO_L17P_T2_A14_D30_14)
   - line 83 JA8 E19 -> **W19** (IO_L16N_T2_A15_D31_14)
   - line 27 CHAN12 W19 -> **E19** (IO_L3N_T0_DQS_EMCCLK_14)
   - line 104 UART_FT_TXD K18 -> **K17** (IO_L12N_T1_MRCC_14)
   - line 26 CHAN11 K17 -> **K18** (IO_L8N_T1_D12_14)
   - line 86 LED0_B N19 -> **N17** (IO_L13P_T2_MRCC_14)
   - line 21 BTN N17 -> **N19** (IO_L9N_T1_DQS_D13_14)
   - line 76 FT_PWREN_N P17 -> **P19** (IO_L10P_T1_D14_14)
   - line 88 LED0_R P19 -> **P17** (IO_L13N_T2_MRCC_14)

   *Verify:* the 13 balls are a permutation (each appears once as from and once as to); Vivado I/O-planner DRC is
   clean.
2. **Schematic** `zulu_a7_5.SchDoc`: rename the RECORD=25 net label at each U1 pin end. All 13 were checked read-only
   by `sch_check.py`.
   - (255,952) H19 CHAN7->CHAN13
   - (255,912) K17 CHAN11->UART_FT_TXD
   - (255,892) W19 CHAN12->JA8
   - (255,882) W18 CHAN13->JA3
   - (935,802) K18 UART_FT_TXD->CHAN11
   - (235,1132) P17 FT-PWREN#->LED0_R
   - (935,357) E19 JA8->CHAN12
   - (935,367) T17 JA7->CHAN28
   - (935,387) G17 JA3->CHAN7
   - (740,262) N19 LED0_B->BTN
   - (740,252) P19 LED0_R->FT-PWREN#
   - (740,212) N17 BTN->LED0_B
   - (740,202) R19 CHAN28->JA7

   *Verify:* export the Protel netlist; `python tools/compare_netlists.py` must show exactly these 13 U1 pin-net
   changes and nothing else.
3. **ECO** (Design > Update PCB Document): exactly 13 pad-net changes, U1:
   - E19 JA8->CHAN12, G17 JA3->CHAN7, H19 CHAN7->CHAN13, K17 CHAN11->UART_FT_TXD, K18 UART_FT_TXD->CHAN11;
   - N17 BTN->LED0_B, N19 LED0_B->BTN, P17 FT-PWREN#->LED0_R, P19 LED0_R->FT-PWREN#;
   - R19 CHAN28->JA7, T17 JA7->CHAN28, W18 CHAN13->JA3, W19 CHAN12->JA8.

   **Untick the removal of the 10 PCB-only net classes and of the USB differential pair.**

   *Verify:* the ECO lists 13 changes and no others.
4. **Re-net by script** the 12 placed objects (old net -> new net; per object `Obj.Net := N; N.AddPCBObject(Obj)`).
   This list is phase2_list section 2, confirmed against the inputs:
   - G17 Top (49.4001,13.4)-(49.9,13.4) and via (49.4001,13.4): JA3->CHAN7
   - K17 Top (49.4001,11.8999)-(49.9,11.8999) and via (49.4001,11.8999): CHAN11->UART_FT_TXD
   - K18 Top (50.4001,11.8999)-(50.6502,12.15) and (50.6502,12.15)-(51.1125,12.15): UART_FT_TXD->CHAN11
   - N17 Top (49.4001,10.345)-(49.9,10.4) and via (49.4001,10.345): BTN->LED0_B
   - P17 Top (49.4001,9.8999)-(49.9,9.8999) and via (49.4001,9.8999): FT-PWREN#->LED0_R
   - T17 Top (49.4001,8.8999)-(49.9,8.8999) and via (49.4001,8.8999): JA7->CHAN28

   *Verify:* read every object back (ZuluProbe-style); DRC Short-Circuit 0.
5. **Removals** are executed by `PlaceStage12_01` itself, first and guarded by `Kill.Count <> 71`. That is 63 tracks
   + 8 vias, every one listed in `removals_listing.txt`:
   - 14 VCCADC/GNDADC L3-SIG segments: x 50.33 / 50.68 verticals, y 15.45 / 15.8 / 8.05 / 7.7 runs, x 47.8 / 48.1 /
     48.35 tails;
   - corridor D: NODE_P1 Bottom (43.17,2.42)-(43.17,3.65), (42.5498,3.65)-(43.17,3.65), (43.17,2.42)-(43.4,1.89), and
     AIN16_N Bottom (42.65,3.05)-(42.98,2.90), (42.98,1.45)-(42.98,2.90);
   - 36 ring-1 Top stubs of 18 nets;
   - the 8 col-16 dogbones at x 49.4001 (stub + through via): y 8.8999 CHAN28, 9.8999 LED0_R, 10.345 LED0_B,
     11.8999 UART_FT_TXD, 12.4 CHAN9, 12.8999 CHAN6, 13.4 CHAN7, 14.8999 CHAN5.

   **The 4 dogbones of LED0_R / UART_FT_TXD / CHAN9 / CHAN6 may only go if the successor routes those nets.**
6. **Place** `PlaceStage12_01` .. `_05` in order, from `judge/g_plan/pas/`, which is byte-identical to
   `close/gates_v11/pas/`:
   - 01: 23 nets, 473 tracks, 233 via objects, plus the removals;
   - 02: 22 nets, 467 tracks, 294 via objects;
   - 03: 24 nets, 442 tracks, 274 via objects;
   - 04: 26 nets, 462 tracks, 291 via objects;
   - 05: 14 nets, 377 tracks, 200 via objects.

   *Verify after each chunk:* DRC Clearance / Short-Circuit / Width 0 new, and the chunk's object counts read back.
7. **DRC** with the HDI rules: Un-Routed must be **0**. Then the USB DiffPairsRouting report: 0.150/0.150, uncoupled
   <= 3.0 mm.

## 8. Risks carried forward

These apply to whatever is eventually placed:
- **Corridor D slack** is +0.0012 to +0.0014 mm (fixed_D/hand_D, byte-identical to 11b), at Altium's rounding edge.
- **SDRAM via slack** is +0.0022 mm (N$LD0G (31.80,16.25) vs D10). The 0.10 via rule lives only in the router copy and
  `extra_gates.py`; tools/ does not enforce it.
- **XADC on L4** now references L5 (VCC3V3), not L2 (GND). That is a noise question for the user.
- **Stage-12 rules are not in tools/:**
  - router copy `exact.py` / `pf.py` / `router.py`;
  - stage-local `extra_gates.py` and `webs_gate.py`.

  A successor that gates with tools/ alone would not catch a regression in them.
- **route_foreclosure is weak here.** Its ball table is stale for the 13 swapped balls, and it cannot see ring-2
  dogbone escapes. route_reach is the gate that sees the open four.
- **Two of the seven swaps are not earned yet.** LED0_R (P19->P17) and UART_FT_TXD (K18->K17) were moved onto the two
  balls that are now sealed. Re-examine them with whatever lever comes next.
- **The schematic labels are only 1.6 units apart.** Each label is 30 units from its pin; the neighbour's is 31.6.
  Phase II must prove the renames with the netlist compare, not by label proximity.
- **Topology freedom** (conn_override_flash.json): FLASH-D02/D03 join at alternative points. Altium's Un-Routed check
  is net-based, so this is fine, but DRC endpoints will differ from the report's.
- **Collinear overlaps** (4, section 4) are cosmetic.

## 9. What next

1. **Do not place.** Keep this plan as the warm start. I re-ran `gen.py --check` in a copy (`judge/genrep`): recorded
   state `snap/v6_s6_att7.json` md5 `01f5d754...`, then `repair done: 6 attempts, 4 moves, open 4` (527 s), then
   `gen_out/plan.json` md5 `594166d3921a5f29f045f2546f90855b`, **IDENTICAL byte for byte**, EXIT 0
   (`gen_check_judge.log`).
2. **No measured lever reaches 140.**
   - Within the brief's levers the 4 are a floor: the author's 40+ seeds and the 0/114 swap screen.
   - My carve shows no clean partial exists (section 5).
   - My sealer survey and probes locate the wall: the in-field escape of the column-17 east balls (section 6).

   Measured here:

   | lever | result |
   |---|---|
   | flow-control deferral | 4 -> 2, best `fc4_plan.json` = 134/136 with LED0_R and CHAN6 open and walled off |
   | CHAN11 + LED2 deferral | no net gain |
   | Bottom-reaching lasers in the field | no gain |
   | XADC single-layer re-path | not available |
   | ball swaps | add no in-field capacity |
3. **A decision for the main session. It is product scope, not routing, so it is the user's call.** Stage 9's question
   1 (flow control) is still open. The two ways forward:
   - **Option A: the fastest placeable board.**
     - What it gives up: rev A ships without UART flow control (RTS#/DTR#/CTS#), without LED0's red channel (LED0_R)
       and without X2 CHAN6. LED0_R and CHAN6 are DEFER class in stage 9's split.
     - What it builds on: `lev/F0/fc4_plan.json` already closes everything else (134/136, route_emit clean, planes,
       GND and webs pass).
     - Stage 13 would then:
       - remove the 5 nets from the U1 side in the schematic and XDC, so Altium's Un-Routed can reach 0;
       - delete their now-orphan dogbones and stubs, which is legitimate only because those nets would no longer
         exist at U1;
       - re-gate with route_reach trivially clean;
       - run the review and the judge, then Phase II.
   - **Option B: the full 140.** This needs a structural lever in U1's east field. None is measured to succeed. The
     candidates, all needing authorisation or a product/mechanical decision:
     - LD0 relocated. LED0_B and LED0_G are among LED0_R's sealers, and the LED0 runs are about 27 mm.
     - The XADC supplies re-routed around the field.
     - The east-field GND through vias with Top-only fan-out converted to Top>L2 microvias: (47.9,9.8999),
       (48.4001,10.4) and (48.4001,9.8999). Their L3/L4 land would be freed.
     - A fresh negotiation of rows D-T x cols 14-19 with these combined, plus flow-control deferral if the user allows
       it.

   Not recommended:
   - more bank-14 or bank-16 swap screening;
   - lifting the Bottom field ban on its own;
   - any partial placement now.
4. **Stage 13, whichever option.**
   - Warm-start from this plan (gen.py chain) or from `fc4_best_state.json` (option A).
   - Make no removal without replacement unless the net is deferred.
   - Drop the 4 collinear overlaps.
   - Run the full gate set plus `--require-complete`, then the reviewer and the judge.
   - Then one Phase II from section 7, re-derived.

## 10. Evidence index (all in `judge/`)

- `run_gates.sh`, `g_plan/*.log`, `g_plan/pas/*`, `g_plan_run.log`: my gate re-run (2 min 20 s).
- `uf_judge.py` + `uf_plan_strict.log`, `uf_plan_tjoin.log`, `uf_empty.log`, `uf_carve.log`: the independent count.
- `overlaps.py` + `overlaps.log`: the collinear overlaps.
- `drc_balls.drc`, `reach_balls_plan.log`: route_reach with the balls as endpoints.
- `reach_diag.py` + `reach_diag_plan.log`, `reach_diag_board.log`, `reach_diag_bottomok.log`
  (`inputs_gate_bottomok.json`): pocket sizes.
- `sealers.py` + `sealers.log`, `lifts.log`: the sealer survey.
- `carve.py` + `carve.log`, `carve_plan.json`, `reach_carve.log`: the partial carve.
- `xadc_bottom.py`: the XADC single-layer probe.
- `sch_check.py` + `sch_check.log`: the read-only schematic check.
- `removals_listing.txt`: the 63 + 8 removals.
- Lever probes, all stopped at 13:54:
  - `lev/defer.py`;
  - `lev/F0/` (copy of `close/gen_out/F_led1_stub`): `st_open.json`, `st_fc.json`, `st_cl.json`, `fc_s1..12.log`,
    `cl_s1..4.log`, `cl_final_status.txt`;
  - `lev/F1/` (Bottom-ban variant): `bt_s1..4.log`;
  - `lev/probe_summary.txt`.
- Flow-control candidate: `lev/F0/fc4_best_state.json`, `fc4_body/`, `fc4_smooth.json`, `fc4_plan.json`,
  `fc4_assemble.log`, `lev/g_fc4/*.log`, `lev/uf_fc4.log`, `lev/drc_orig_noFC.drc`, `lev/drc_gate_noFC.drc`.
- `genrep/`, `gen_check_judge.log`: my `gen.py --check` re-run.
