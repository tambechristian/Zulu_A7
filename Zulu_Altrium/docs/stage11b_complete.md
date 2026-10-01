# Stage 11b: 131 of 140 on HDI with round pads -- DO-NOT-PLACE, one lever from completion (2026-10-01)

**Nothing placed.** Workflow wf_ca1173b1 (USB pair, complete, review, judge; 1.69M tokens, 9.3 h). Plan:
`scratchpad/stage11b/complete/plan.json` md5 `ea0657de0f2bff7e4fd04533fe09a492`; structured result
docs/stage11b_complete.json.

| stage | closed of 140 |
|---|---|
| through-only global routes (4b / Situs / 6) | 92 / 90 / 86 |
| stage 10, HDI, square-pad gates | 96 |
| **stage 11b, HDI, round-pad gates, coupled USB, corridor D edit, 2 ball swaps** | **131** |

What is now done in the plan: **the USB pair coupled** (0.150/0.150, 17.0808 mm each, uncoupled 1.86 mm vs 3.0
limit, skew 0.0001 mm, all on Top over L2, no vias); **both GND ties** (U2-5 by a GND Top>L2 laser stack, R15-1 by
corridor D's hand copper with the authorised two-removal edit of stage-8 NODE_P1/AIN16_N, worst slack +0.0013 mm);
**webs PASS** (stage 10's thin plane webs gone; the router now refuses new ones); two bank-14 ball swaps
(JA3 G17<->H19 CHAN7, JA7 T17<->R19 CHAN28).

**Why not placeable:** the 9 open (FLASH-D02, FLASH-D03, CHAN2, CHAN10, CHAN13, CHAN18, CHAN27, CHAN-CLK,
UART_FT_RTS#) are walled off by the plan's own copper (route_reach 0 of 7 with the plan, 7 of 7 bare;
route_foreclosure takes their balls from 25+ slots to 0). Every forced closure in 52 repair logs cost >= 2 others.

**The lever the judge found:** the placed VCCADC/GNDADC L3-SIG runs inside U1's land field block the interstitial
sites. Moving those 14 segments to L4-SIG on the same path, between the existing through vias, with no new via, is
route_emit-clean and takes legal interstitial sites 37 -> 79 of 324 (the two east columns 1 -> 31) and gives 7 of
the 9 open balls their own inward microvia site (1 of 9 today). **Taken under the user's standing authorisation
(2026-10-01)** -- see stage 12.

---

# Stage 11b judge: the HDI round-pad plan -- DO-NOT-PLACE (2026-10-01)

Directory: `scratchpad/stage11b/judge/` (S = `.../scratchpad/stage11b`). Plan judged: `S/complete/plan.json`,
md5 `ea0657de0f2bff7e4fd04533fe09a492` (`md5sum`; identical to the reviewer's `review/plan_under_review.json` and to my
copy `judge/plan.json`). Gate inputs: `complete/inputs_gate.json` md5 `c0fd0f7e05c4bb66170221ac6dce10e6` (=
`review/inputs_swap.json`, the reviewer's independent rebuild) and `complete/drc_gate.drc` md5 `6883e769...`. Board:
`Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc` md5 `c927413f3422a37f230e78ac3de58942` and `tools/route_inputs.json` md5
`67f6464a...`, both as the brief states. My tools copy `judge/tools` is `diff -rq`-identical to the repo's `tools/`.
Boundaries kept: no Altium, no computer-use, no edit to tools/, the PrjPcb, the XDC or the schematic (both only read),
no git commit, no `--write`, no pictures; everything I wrote is in `judge/`.

## 0. The verdict

**DO-NOT-PLACE.** The plan closes **131 of 140** and leaves **9 open**. It is a large step from stage 10's 96, and its
copper is clean (`route_emit` clean, webs PASS, USB pair coupled, GND 206/206). But it is neither placeable criterion:

- **Not PLACE:** 9 connections open (signals_check: 9 signal nets split), so the brief's goal (all 140, every gate
  passing) is not met.
- **Not PLACE-PARTIAL:** a partial must wall off nothing it leaves open, and this plan walls off all of them:
  - `route_reach`: **7 of 7** evaluated open connections are routable on the bare board and **0 of 7** with the plan.
  - `route_foreclosure`: **every one of the 9 open balls** goes from `25+` escape slots on the board to `0` with the plan.
  - The 2 open connections route_reach cannot evaluate (FLASH-D02, FLASH-D03, nets the plan touches) are among those
    foreclosed balls (G18, F18).
- **Unauthorised removal (reviewer's refutation, adopted):** the plan removes **12 placed fan-out stub tracks of 6
  still-open nets** with no replacement. They are load-bearing: keeping them gives `route_emit` **43 PROBLEM(S)**. That
  is placed signal copper removed without replacement, outside the brief's "removals-with-replacement".

The 9 are a measured floor on this geometry, not a router accident. In all 52 repair logs every forced closure
displaced **at least 2** closed connections (section 1).

I measured one lever that targets them directly. Moving the placed **VCCADC/GNDADC L3 runs** inside U1's field to L4 on
the same path (14 segments, no new via) is `route_emit`-clean on the bare board. It gives own-net inward microvia sites
to **7 of the 9 open balls** (1 of 9 today). It touches placed XADC/power copper, so it needs the main session's
decision under the user's standing authorisation (section 7).

## 1. Closed of 140 = 131, established three ways

| count | source | command |
|---|---|---|
| closed 131, open 9 | reviewer's independent union-find, no tools import (`review/uf_plan.log`, identical with `--strict`) | `python review/uf.py inputs_swap.json drc_swap.drc plan_under_review.json` |
| 165 joined / 10 split = the 9 open signal nets + VCC3V3's 86 bare-board plane islands | my re-run, `judge/g_plan/signals_check.log` | `python tools/stage6/signals_check.py --inputs inputs_gate.json plan.json` |
| repair end state `open 9` | the plan's own engine, `complete/rep7_s64.log` last line `repair done: 29 attempts, 3 moves, open 9: ...` | `python -u pf/repair.py ...` (gen.py step 4) |

The 9 open, with their U1 ball (`review/uf_plan.log`):

| connection | ball | why open (the plan's text, corrected where the reviewer re-counted) |
|---|---|---|
| FLASH-D02 track<->R2-1 | G18 side | NE via band. Closing it cuts JA3 + FLASH-CS# in **42 of 56** attempts (reviewer re-count; "every path" overstated) |
| CHAN10 X2-13<->U1-J19 | J19 | east via band. Costs JA3 + FLASH-CS# (+LED2) |
| CHAN13 X2-16<->U1-W18 | W18 | SE corner. Costs CHAN15 + LED0_G; it alternates with CHAN15 |
| UART_FT_RTS# U2-40<->U1-L18 | L18 | costs 2 to 8 closed connections (8 in 41 of 95 attempts) |
| FLASH-D03 U1-F18<->U4-7 | F18 | fixed-function ball. Costs JA3 + FLASH-CS# |
| CHAN-CLK U1-P18<->X2-2 | P18 | costs LED0_R + LED0_G |
| CHAN27 X2-37<->U1-T18 | T18 | costs LED0_G, LED1, CHAN19. The CHAN27:JA10 swap was net zero (10 open) |
| CHAN2 X2-5<->U1-B17 | B17 | costs FLASH-D02 U4-3 + UART_FT_RXD U2-39 |
| CHAN18 X2-28<->U1-V16 | V16 | opened by the 0.80 mm via-edge rule. Costs CHAN22 + CHAN19 |

**Floor evidence:** I tallied every `undo ... would lose N` line in all 52 `complete/rep*_s*.log` files, across all
board variants, with an inline Python counter. The minimum N is **2 for every open connection**, and also for every
other connection ever forced. Per open connection:

| connection | attempts | min lost | spread |
|---|---|---|---|
| CHAN-CLK | 66 | 2 | all 2 |
| CHAN10 | 100 | 2 | 66 lost 2 |
| CHAN13 | 60 | 2 | 54 lost 2 |
| CHAN18 | 27 | 2 | 25 lost 2 |
| CHAN2 | 46 | 2 | 44 lost 2 |
| CHAN27 | 40 | 2 | mostly 3-4 |
| FLASH-D02 track<->R2-1 | 81 | 2 | — |
| FLASH-D03 | 75 | 2 | — |
| UART_FT_RTS# | 95 | 2 | 41 of 95 lost 8 |

## 2. Every gate, re-run by me

Command: `sh judge/run_gates.sh judge/plan.json judge/g_plan`. It uses the repo tools copy, `inputs_gate.json` and
`drc_gate.drc`, and took 2 min 17 s. route_stitch, capacity, route_width and the USB coupling were not re-run by me:
the reviewer's `review/gates/` and the plan's `gates_final/` agree on them, and none of them decides the verdict.

| gate | result (my log) | reading |
|---|---|---|
| route_emit `--require-complete` | `plan: 741 vias, 7014 tracks / geometry and connectivity check: clean / removes 0 existing via(s) and 39 track(s)`, EXIT 0 | PASS. One track is a reversed duplicate (section 3.4). |
| route_emit `--pas` | reviewer + plan: `741 plan via(s) -> 1153 Altium via object(s), 7014 track(s)`, EXIT 0 | emits. |
| signals_check | `165 joined, 10 split`, EXIT 1 | **FAIL**: the 9 open nets. |
| tie_check VCC3V3 | farthest U3-9 4.613 mm, EXIT 0 | PASS. |
| gnd_check | `GND SMD pads 206, tied 206, untied 0`, EXIT 0 | PASS: U2-5 and R15-1 are tied. |
| plane_islands L2 GND | main island 100.0 %, **213 of 216** pads; OFF-PLANE R17-2, C94-2, C115-2; EXIT 1 | **formal FAIL, plan-caused** (section 3.2). |
| plane_islands L5 VCC3V3 | main island 100.0 %, **132 of 133**; OFF-PLANE U1-K1; EXIT 1 | **formal FAIL, plan-caused** (section 3.2). |
| webs (`complete/work/webs_gate.py`) | `WEBS PASS: 0 plan-involved thin web(s)`, EXIT 0 | PASS. Stage 10's 3 laser-laser webs are gone. |
| route_foreclosure | `foreclosed by the plan(s): ...` lists all 9 open nets (plus routed nets: the stub-end heuristic); `pads foreclosed: none`; EXIT 1 | **FAIL for the 9 open balls** (25+ -> 0 slots each). |
| route_reach | `routable on the board: 7 / 7`, `routable with the plan(s): 0 / 7`, `connections walled off by the plan(s): 7`, EXIT 1 | **FAIL**. |
| route_stitch / capacity / route_width / USB | reviewer: 59.1 % / TOTAL -913.9 mm2 / P 0.300 N 0.263 / coupled 15.22 mm, uncoupled 1.86 mm (dp_proj), skew 0.0001 | reports; USB meets 0.150/0.150 and uncoupled <= 3.0. |

## 3. The reviewer's refutations: all adopted, two re-measured by me

1. **The 12 stub removals cannot be dropped** (`review/keepstubs_route_emit.log`: `43 PROBLEM(S)`, for example
   `via 63 (FLASH-D02) -0.1880 from existing Top track (CHAN2)`). By my count (`judge/plan.json` `remove`): 39 tracks
   are removed. They are:
   - corridor D: NODE_P1 x3 and AIN16_N x2;
   - 34 ring-1 Top stubs of 17 nets, of which 12 belong to the 6 still-open nets CHAN2, FLASH-D03, UART_FT_RTS#,
     CHAN-CLK, CHAN27 and CHAN18.
   **Adopted.** Those 12 are placed signal copper removed with no replacement.
2. **plane_islands fails because of the plan**, not because of strays. The reviewer's empty-plan runs give L2
   216/216 and L5 133/133, EXIT 0 (`review/plane_L2_empty.log`, `plane_L5_empty.log`). My re-run shows the same four
   OFF-PLANE pads. **Adopted.**
   - My reading, as at stage 10: the brief's "one island each" is met (100.0 %), and the four pads are tied by their own
     vias (gnd 206/206, tie 129/129), so this is electrically benign.
   - It is still a formal gate failure that a successor should remove by re-siting four lasers: CHAN23 (46.8,4.15),
     TCK (51.45,22.35), JA9 (51.6,7.75) and SD-CLK (41.75,11.75).
3. **FLASH-D02 "every path"**: 42 of 56 attempts, not all. **Adopted.** The floor conclusion is unchanged.
4. **Duplicate track** (re-measured): `judge/plan.json` has 7014 tracks and 7013 unique. The duplicate is UART_FT_CTS#
   Top (49.025,17.1)-(49.225,16.925), appearing twice. **Adopted.**
5. **SDRAM 0.10 vs vias on L3/L4** (reviewer's open risk): two plan lasers sit 0.0911 and 0.0993 mm, land to land,
   from SDRAM through vias (CHAN28 (43.1,4.05)/D5, SD-CLK (38.2,12.25)/A9).
   - The rule scope is `(InNetClass(SDRAM_*)) And (OnLayer('L3-SIG') Or OnLayer('L4-SIG'))`, from inputs `rules`.
   - The placed board cannot settle whether Altium's `OnLayer` matches a via: **0** SDRAM/non-SDRAM via pairs under
     0.10 exist (my check), and the 2026-09-29 DRC shows 0 violations for that rule.
   - Kept as a risk. The cheap cure is to apply 0.10 to via lands near SDRAM vias in the successor (2 vias move).

## 4. Why not PLACE-PARTIAL of a carved subset

I did not carve one, for three reasons.

1. **The plan as delivered walls off everything it leaves open** (section 0). Any partial would have to drop every
   competitor of the 9: per the repair logs, at least JA3, FLASH-CS#, LED2, CHAN15, LED0_G/R/B, CHAN0/4/5/7,
   UART_FT_RXD, PUDC_B, JA8, LED1, CHAN19, CHAN22, CHAN16 and JA1. It would also have to keep the 12 stubs, which means
   dropping FLASH-D02, JA1, LED0_B, LED0_G, JA8 and more (route_emit's 43 problems). That leaves roughly 30 open, all
   in U1's east half.
2. **The fix for those 9 rebuilds exactly that region.**
   - The XADC lever (section 6) collides with 20 of this plan's nets: `route_emit.check` gives **327 problems** with the
     runs on L4, in CHAN4/5/6/7/9/11, FPGA-TDI/TMS/TCK/DONE/INIT#, SD-DAT0, BTN, UART_FT_TXD, LED0_R/G/B, CLK-12M-FPGA,
     FT-PWREN# and CHAN22.
   - The cap-block lever lands on 17 plan vias.
   - Copper placed there now would be ripped in Altium next stage. That is stage 10's "freezes the order" argument,
     made concrete.
3. **One Phase II is cheaper than two.** This plan stays the warm start in the model, where any of its copper can still
   move for free.

## 5. What the plan does well (carried forward)

These parts are worth keeping in the successor:
- 131/140, with byte-identical regeneration from the recorded negotiated state (reviewer, `review/regen`).
- Corridor D closed: R15-1 tied and ANALOG-IO1 routed. Worst slack is +0.0012 to +0.0014 mm (`review/clr.log`).
- U2-5 tied, so GND is 206/206.
- USB pair at 0.150/0.150: 17.0808 mm each, skew 0.0001, uncoupled 1.86 mm. The stage-10 router lacked this.
- Via land to outline is at least 0.815 mm, and there are 0 plan-involved thin webs.
- Two bank-legal swaps. JA3 G17 <-> CHAN7 H19 is IO_L5N_T0_D07_14 <-> IO_L4P_T0_D04_14. JA7 T17 <-> CHAN28 R19 is
  IO_L17P_T2_A14_D30_14 <-> IO_L10N_T1_D15_14. All four are bank 14, LVCMOS33, not dedicated or fixedfn (reviewer,
  from `Datasheet/xc7a35tcpg236pkg_pinout.txt` and `stage9/repin/freeset.json`).

## 6. Levers for the 9, measured here

**A. The XADC supply runs (recommended first).**

*What the copper is.* The placed VCCADC (0.2 mm, class PWR_RAILS) and GNDADC (0.2 mm) L3-SIG runs run inside U1's land
field. VCCADC runs from via (47.4001,14.8999) east along y 15.45, south down **x 50.33** to y 8.05, west to x 47.8 and
down to via (47.8,5.25). GNDADC runs from via (46.9,14.8999) along y 15.8, down **x 50.68**, and out to via (48.35,5.0).
The two verticals sit on U1's two east interstitial columns (x 50.15 / 50.65). Six of the 9 open balls are in column 18,
beside x 50.65 (`judge/interstitial_sites*.py` locate it).

*Measured with `tools/route_emit.check`, one Top>L2>L3 0.30 laser per site* (`python judge/interstitial_sites2.py`,
`judge/open_ball_sites.py`; logs alongside):

| | bare board | XADC L3 runs removed |
|---|---|---|
| legal interstitials (net of an adjacent signal ball) | 37 of 324 | 79 of 324 |
| in the two east columns | 1 | 31 |
| **open balls with an own-net inward site** | **1 of 9** (B17) | **7 of 9** (B17, F18, G18, L18, P18, T18, V16) |
| blocker balls with an own-net inward site | 1 of 21 | 11 of 21 (R18, N18, M18, K18, J18, E18, D18, U18, V17, G17, B18) |

With a dummy net (no own-stub exemption) the count is 21 -> 43 of 324 (`interstitial_sites.log`). The brief's "50" used
another counting rule; I report only what my commands produce. J19 (CHAN10) and W18 (CHAN13) gain no own site. They
would gain only through the band capacity their neighbours free.

*The replacement is trivial.* Moving those 14 segments to **L4-SIG on the same path**, between the same through vias
with no new via, gives **0 route_emit problems on the bare board** (`python judge/xadc_l4_probe.py`; plan fragment
`judge/xadc_l4_probe_plan.json`, inputs `judge/inputs_lever_gate.json` via `lever_inputs.py`). VCCADC and GNDADC stay
parallel (0.35 mm apart).

*The costs.*
- The runs would reference L5 (VCC3V3) instead of L2 (GND). That is an XADC noise question for the user.
- They collide with 20 of this plan's nets (327 problems), so U1's east half must be re-negotiated, not repaired.

**B. The plan author's cap-block shift (second).**
- The C140..C98 3x4 bulk-cap block (x 52.25-57.35) carries 77 plan vias and 509 inner/Bottom segments underneath it.
- Its west-column tie vias are part of the band itself: C143-1 (51.9,9.445), C146-1 (51.95,12.45), C93-1 (51.95,15.75).
  The band widens only if those vias move with the caps.
- A 0.5 mm east shift lands on 17 plan vias and 92 segments (FPGA-TDI/TDO/TMS/TCK, JA7-JA10, PROG#, DONE), and narrows
  the cap-to-R4 corridor from 0.65 to 0.15 mm (R4 west pads start at x 58.0).
- Measured with `judge/` inline scripts; numbers above.

**C. More bank-14 swaps (third).** CHAN27:JA10 was measured net zero (10 open, `complete/fp6c`, `rep5_s*`). Swaps help
J19/W18 at most.

## 7. Phase II change list

**NOW: nothing.** Phase II applies nothing from this plan: no part move, no XDC or schematic edit, no ECO, no copper
removal, no placement.

**CARRY-FORWARD.** The exact list this plan's content implies. Apply it only together with a successor plan that closes
140 and passes every gate; re-derive it from that plan.
1. Part moves: none.
2. XDC `vivado/zulu_a7_pins.xdc` (md5 `2b81f24d36494236755c919bc63b9432`):
   - line 80: JA3 `PACKAGE_PIN G17` -> `H19` (comment IO_L4P_T0_D04_14);
   - line 49: CHAN7 `H19` -> `G17` (IO_L5N_T0_D07_14);
   - line 82: JA7 `T17` -> `R19` (IO_L10N_T1_D15_14);
   - line 44: CHAN28 `R19` -> `T17` (IO_L17P_T2_A14_D30_14).
   IOSTANDARD stays LVCMOS33. Re-run Vivado's I/O-planner DRC; this file is its validated baseline (commit 3314cd2).
3. Schematic `zulu_a7_5.SchDoc`, where U1 is drawn as single-pin parts. Rename the net label (RECORD=25) at each pin end:
   - (255,952) CHAN7 -> JA3, on U1-H19 (part 58);
   - (935,387) JA3 -> CHAN7, on U1-G17 (part 133);
   - (935,367) JA7 -> CHAN28, on U1-T17 (part 132);
   - (740,202) CHAN28 -> JA7, on U1-R19 (part 120).
   Then prove with `compare_netlists.py` that exactly those 4 pin-net changes occurred.
4. ECO (Design > Update PCB Document): exactly 4 pad-net changes (U1-G17 JA3->CHAN7, H19 CHAN7->JA3, T17 JA7->CHAN28,
   R19 CHAN28->JA7). **Untick the ECO's removal of the 10 PCB-only net classes and the USB differential pair.**
5. Re-net the swapped balls' dogbones by script, with Net.AddPCBObject per object:
   - Top track (49.4001,13.4)-(49.9,13.4) and through via (49.4001,13.4): JA3 -> CHAN7;
   - Top track (49.4001,8.8999)-(49.9,8.8999) and through via (49.4001,8.8999): JA7 -> CHAN28.
6. Remove 39 placed tracks (0 vias), exactly `complete/removals.json`:
   - corridor D NODE_P1 Bottom (43.17,2.42)-(43.17,3.65), (42.5498,3.65)-(43.17,3.65), (43.17,2.42)-(43.4,1.89);
   - AIN16_N Bottom (42.65,3.05)-(42.98,2.90), (42.98,1.45)-(42.98,2.90);
   - 34 ring-1 Top stubs (2 per net) of CHAN0, CHAN2, CHAN8, CHAN15, CHAN18, CHAN20, CHAN23, CHAN26, CHAN27, CHAN-CLK,
     FLASH-D03, JA1, LED0_G, RST#, UART_FT_DTR#, UART_FT_RTS# and UART_FT_TXD.
   None of these may be dropped while the plan's copper sits on their sites.
7. Place the plan: `route_emit --pas`, giving 741 plan vias -> 1153 Altium via objects and 7013 tracks once the
   duplicate is dropped. Split the 3.8 MB script into chunks. Run DRC with Un-Routed expected 0, and read the USB
   DiffPairsRouting report.

## 8. Risks (for whatever is eventually placed)

- **Corridor D slack** is +0.0012 to +0.0014 mm, at Altium's DRC rounding edge.
- **SDRAM 0.10 rule scope vs two laser vias** (section 3.5).
- **3418 of 7014 tracks are shorter than 0.08 mm**: unsmoothed 0.05 mm staircases (my count). Smooth them in the model
  and re-gate before placing; do not do it in Altium. PlaceStage11.pas is 3.8 MB.
- **Merged plane voids** (web <= 0): 77 on L2 and 61 on L5 involve plan vias (32/25 at stage 10). They are not gated.
  The planes stay one island, but the merged voids lie under L3 signals.
- **The negotiation step is not reproducible**: prun2 used a non-deterministic parallel update. Only the chain after
  negotiated_state.json regenerates byte for byte.
- **XADC lever**: VCCADC/GNDADC would move from a GND-referenced layer (L3) to a VCC3V3-referenced one (L4).

## 9. What next (in order)

1. **Main session decision** under the user's standing authorisation: allow the XADC supply runs to be removed and
   replaced in U1's field.
   - The change: the 14 VCCADC/GNDADC L3-SIG segments move to L4-SIG on the same path, between the same through vias.
     That is `route_emit`-clean on the bare board.
   - What it buys: own-net inward sites for 7 of 9 open balls and 11 of 21 blockers.
   - It is placed XADC/PWR_RAILS copper, outside stage 11b's boundary. The judge measures; the main session decides.
2. **Stage 12 (model only)**, starting from this plan as the warm start:
   - put the lever in the inputs;
   - re-negotiate U1's east half, freeing the 20 colliding nets plus the 9 open and their competitors;
   - keep fixed the USB pair, corridor D, the U2-5 tie and the two swaps;
   - target 140, with fixes for this plan's defects: replace or keep every stub, dedupe tracks, re-site the four
     off-plane lasers, apply 0.10 to vias near SDRAM vias on L3/L4, smooth the staircases;
   - run the full gate set plus `--require-complete`, then review and judge.
3. If the lever is refused or falls short, measure lever B (the cap-block shift, with its west tie vias) and then
   lever C (swaps) the same way.
4. Then one Phase II, using section 7's list re-derived from the 140 plan.

## 10. Evidence index (all in `judge/` unless noted)

- `run_gates.sh`, `g_plan/*.log`: my gate re-run.
- `interstitial_sites.py` + `.log`, `interstitial_sites2.py` + `.log`, `open_ball_sites.py` + `.log`: the XADC lever
  site counts.
- `xadc_l4_probe.py` + `.log` + `xadc_l4_probe_plan.json`, `lever_inputs.py` -> `inputs_lever_gate.json`: L4
  replacement is clean; 327 collisions with this plan.
- `sch_find.py`, `sch_u1.py`: read-only schematic location of the swap labels.
- Reviewer: `S/review/uf_plan.log`, `keepstubs_route_emit.log`, `plane_L*_empty.log`, `clr.log`, `gates/`.
- Plan: `S/complete/plan.json`, `gen.py`, `gen_check3.log`, `rep*_s*.log`, `gates_final/`, `removals.json`,
  `swaps.json`.
- USB: `S/usb/usb_plan.json`, `S/usb/gates_final/`.
