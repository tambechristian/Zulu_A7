# Stage 13 routing closeout: fully routed and DRC clean (2026-10-02)

## Final implementation closeout

Stage 13 has been applied to the live board and is complete. The historical judge record below explains the selected
route and the original placement procedure; its `b59c...` plan hash and 4,199-track / 1,794-via target describe the
pre-placement candidate, not the final cleaned board.

### Final saved-board result

- Physical stack: Top -> L2-GND -> L3-SIG -> L4-SIG -> L5-VCC3V3 -> Bottom.
- L2 and L5 were converted from negative internal planes to positive signal layers. Full-board
  `L2_GND_PLANE` and `L5_VCC3V3_PLANE` polygons provide the power planes and preserve the intended direct via
  connections.
- Final copper census: **4,196 tracks and 1,787 Altium via objects**.
- Final via breakdown:
  - through Top-Bottom: 380;
  - Top-L2 microvias: 296;
  - L2-L3 microvias: 282;
  - L3-L4 buried vias: 369;
  - L4-L5 microvias: 230;
  - L5-Bottom microvias: 230.
- Total records marked `IsMicroVia`: **1,038**.
- Final route model: 2,746 tracks and 925 plan-via records; it removes 68 original tracks and 27 original vias.
- Final `tools/stage13/plan.json` MD5: `0466e74f4ed722c5670143cdec15b354`.
- Final live-board MD5: `5256fc1a9a46708596f24de1696617b8`.
- Matching FPGA files:
  - `zulu_a7_5.SchDoc`: `91307767c393e03d90318e7548801aab`;
  - `vivado/zulu_a7_pins.xdc`: `4310ec58cd324dceb194796b041f51b8`.

The final file-level checks pass:

- `verify_placed.py`: 4,196 / 4,196 tracks, 1,787 / 1,787 vias, no missing or extra geometry, and no pad-net
  differences.
- `verify_stack.py`: stack matches JLC06161H-3313E.
- `verify_widths.py`: every effective Width, Clearance, and solder-mask rule matches the target.
- Polygon connectivity:
  - L2: 216/216 GND pads and 135/135 GND vias are on the main island;
  - L5: 133/133 VCC3V3 pads and 85/85 VCC3V3 vias are on the main island.

### Post-placement corrections

- The CHAN8 diagonal from (36.65,25.05) to (38.75,22.95) crossed X1-MP4. It was replaced by a clearance-safe
  dogleg through (37.45,25.05).
- Four dangling pre-existing tracks and four unused through vias were removed.
- The unused CHAN6 stack at (49.4,12.92) was removed from the plan and live board.
- These edits reduced the initially placed 4,199-track / 1,794-via board to the final 4,196 / 1,787 census without
  opening any connection.

### Final Altium DRC

The saved report `Design Rule Check - zulu_a7.html`, generated 2026-10-02 12:44:33, shows:

- **Warnings: 0**
- **Rule violations: 0**
- Clearance, Short-Circuit, Un-Routed, Net Antennae, Width, routing topology, hole size, hole clearance, solder mask,
  polygon, and power-plane connection categories: all 0.

### Fabrication-output verification

Conventional Gerbers were regenerated in `Imported zulu_a7.PrjPcb` at 0.0001 mm resolution. The output includes all
six copper layers, both overlays, solder masks, paste masks, and the board profile.

- `zulu_a7.G1` (L2) and `zulu_a7.G4` (L5) both declare positive file polarity.
- Both power-layer Gerbers define a 0.3000 mm circular aperture for microvia lands.
  - L2 contains 578 such flashes: 296 Top-L2 plus 282 L2-L3.
  - L5 contains 460: 230 L4-L5 plus 230 L5-Bottom.
- Isolated Gerber clearance regions measure 0.4894 mm and 0.7138 mm across their circumscribed polygon vertices.
  Correcting the 32-segment circle approximation gives nominal **0.4800 mm microvia voids** and **0.7001 mm
  through-via voids**.
- No via-sized clearance region is centered on any of the 135 same-net GND via positions on L2 or the 85 same-net
  VCC3V3 via positions on L5; these vias connect directly to their planes.

The NC drill set is also in `Imported zulu_a7.PrjPcb`. `zulu_a7.LDP` maps all six drill pairs, and
`zulu_a7.DRR` records these counts:

| file | drill pair | tool | holes |
|---|---|---:|---:|
| `zulu_a7.TXT` | Top-Bottom | 0.20 mm | 380 routed through vias |
| `zulu_a7.TX3` | L3-L4 | 0.15 mm | 369 buried vias |
| `zulu_a7.TX6` | Top-L2 | 0.15 mm | 296 microvias |
| `zulu_a7.TX7` | L2-L3 | 0.15 mm | 282 microvias |
| `zulu_a7.TX9` | L4-L5 | 0.15 mm | 230 microvias |
| `zulu_a7.TX10` | L5-Bottom | 0.15 mm | 230 microvias |

`zulu_a7.TXT` also contains the 62 larger plated component holes. The drill report totals the four laser pairs at
1,038 microvias.

Directory `scratchpad/stage13/judge/` (J below; S13 = `scratchpad/stage13`, S12 = `scratchpad/stage12`). Every number
below comes from a command run in J, named next to it; the logs are in J.

Original plan judged: `S13/arm_copper/plan.json`, md5 `b59c168ae3dc1b602a155d26fd0f349a` (`md5sum`; my copy `J/plan.json` is
identical). Gate inputs `inputs_gate.json` md5 `cf43b174921e2e8c56399dcb50998747`, `drc_gate.drc` md5
`859444b17b7ab5be892980eaebcd8659` (= stage 12's). Project files by `md5sum`, unchanged since stage 12 and still
unchanged at the end of this judgement:
- PcbDoc `c927413f3422a37f230e78ac3de58942`
- `zulu_a7_5.SchDoc` `05c093fdce41ff79ffaebcc8dda3c866`
- `vivado/zulu_a7_pins.xdc` `2b81f24d36494236755c919bc63b9432`
- `tools/route_inputs.json` `67f6464a93d48498da41268f0105e24b`
- `docs/drc_hdi_rules_2026-09-29.drc` `6dfcfe48589a7c8d1879ec6162b57116`

`J/tools` is `diff -rq`-identical to the repo's `tools/` (pycache excluded). `git status --short tools` is empty and
`git status` is as it was at the session start.

Boundaries kept:
- No Altium, no computer-use.
- No edit to tools/, the PrjPcb, the XDC or the schematic. They were only read, and their md5s are as above.
- No commit. Never `--write`: route_emit ran only with `--pas`, into J.
- No pictures.
- Everything I wrote is in J. route_reach's board cache was redirected into `J/tmp` (TMPDIR/TEMP/TMP).

## 0. The verdict

**PLACE, arm copper.** These numbers force it:

| test | result | command (in J) |
|---|---|---|
| closed of 140 | **140, open 0**; islands holding pads of 2+ nets: 0; DRC nets split: 0 | `python uf_judge.py inputs_gate.json docs/drc_hdi_rules_2026-09-29.drc plan.json` (`uf_plan_strict.log`) |
| same, with T-joins allowed / with planes off / with the empty plan | 140 / **138** / 0. The two missing without planes are the R15-1 and U2-5 GND ties, which close through L2 only. | `--tjoin`, `--noplanes`, `empty_plan.json` (`uf_plan_tjoin.log`, `uf_plan_noplanes.log`, `uf_empty.log`) |
| every brief gate | all pass; every log line-identical to the arm's `gates_final/` | `sh run_gates.sh plan.json g_plan` (2 min 43 s, `g_plan_run.log`) |
| Pascal | 6 chunks, byte-identical to the arm's (md5s in section 7) | same run, `g_plan/pas/` (`cmp`) |
| reproducibility | `gen13.py --check`: recorded state E4nA_fin `88938337...`; `repair done: 6 attempts, 6 moves, open 0` (300 s); final state `d161ddeb...`; `gen_out/plan.json md5 b59c168a...`; **IDENTICAL byte for byte**; EXIT 0 (5 min 33 s) | `cd genrep && python gen13.py --out=gen_check_judge --check` (`gen_check_judge.log`) |

Copper is the only arm at 140, so the tie-break (copper over swaps over part moves) is not needed. It also moves no part.
The ld0 arm is DO-NOT-PLACE on its own numbers (section 1).

Nothing I found blocks placement. Three findings change what Phase II must check and what goes to JLC (sections 4.2-4.4):
1. **Plane webs.** The webs gate sizes through-via plane voids at 0.53 mm; the board's own PlaneClearance rule gives
   0.70 mm. "webs PASS" therefore holds only in the gate's model. Under the board's rule the plan adds 12 thin plane webs,
   on top of the 18 the placed board already has. No web carries plane connectivity.
2. **Hole-to-hole.** How Altium treats stacked and disjoint-span vias is unproven. I counted the classes it might flag;
   the class that would be a real defect is 0.
3. **Stacked-via test.** This was still open when the candidate was judged. During Phase II it triggered the documented
   fallback: L2/L5 were converted to signal layers with full-board polygons, then verified in Gerber and DRC.

## 1. The arms

| arm | closed (my `uf_judge.py`) | gates | part moves | verdict |
|---|---|---|---|---|
| **copper** | **140 / 140** (`uf_plan_strict.log`) | all pass | none | **PLACE** |
| ld0 | 136 / 140 with its own inputs `arm_ld0/inputs_gate_final.json` (`uf_ld0.log`). Open: CHAN7 X2-10<->U1-G17, UART_FT_TXD U2-38<->U1-K17, CHAN9 X2-12<->U1-J17, CHAN6 X2-9<->U1-H17 | signals_check and route_reach FAIL (its verifier reproduced both) | LD0 to (58.8,12.5) rot 90 | DO-NOT-PLACE |
| capacity (separate workflow wf_e40d749b; not in this judge's slate, listed only for the main session's cross-arm view) | 135 / 140 with its own inputs (`uf_capacity.log`). Open: LED0_R, UART_FT_TXD, UART_FT_RTS#, CHAN6, SD-CMD | -- | -- | not judged here; below copper |

Control: the stage-12 plan on these inputs gives 136, with exactly LED0_R, UART_FT_TXD, CHAN9 and CHAN6 open
(`uf_s12_control.log`).

## 2. Every gate, re-run by me

`J/run_gates.sh` runs the gate list of the arm's `run_gates13.sh` from J, using:
- J's copy of tools;
- the stage-local scripts copied from the arm, md5-checked (`webs_gate.py` and `dp_proj.py` equal stage 12's);
- the fixed parts in `J/F`: the STAGE 12 originals `usb_plan.json` (b480fb37), `fixed_D.json` (7cede1df), `hand_D.json`
  (b6270d8f) and `tie.json` (0254682b), plus the arm's `lever13.json` (4e88f52f) and `esc13.json` (06310ea1).

Every log equals the arm's once paths are stripped (`diff`), and the .pas files are byte-identical (`cmp`).

| gate (brief) | my result | reading |
|---|---|---|
| route_emit `--require-complete` | `plan: 927 vias, 2745 tracks / geometry and connectivity check: clean / nets joined end to end: 66/67 (touched by the plan: 3, of them joined: 3) / removes 23 existing via(s) and 64 track(s); every U1 power/GND ball still reaches its via`, EXIT 0 | PASS |
| `--pas` chunks <= 400 KB | 6 chunks: 373491 / 387845 / 367780 / 384186 / 355359 / 277730 bytes, each route_emit EXIT 0, `PAS CHUNKS PASS` | PASS |
| signals_check | `175 nets checked ...: 174 joined, 1 split`. The split is VCC3V3's 86 bare-board islands, which join through L5 (tie_check 129/129, plane_L5 133/133 + 86/86). EXIT 1 by construction. | PASS on the brief's criterion (every signal net one island) |
| tie_check VCC3V3 | 129 SMD pads, tied 129, EXIT 0 | PASS |
| gnd_check | 206 / 206 tied (R15-1 0.40 mm, end 0.599 from a via), EXIT 0 | PASS |
| plane_islands L2 / L5 | L2: 216/216 GND pads + 135/135 GND vias on the main island. L5: 133/133 + 86/86. EXIT 0 / 0 | PASS |
| webs | `WEBS PASS: 0 plan-involved thin web(s)`, EXIT 0 | PASS as defined (but see 4.3) |
| route_reach | `0 un-routed connections of nets the plan(s) do not touch ... walled off by the plan(s): none`, EXIT 0 | PASS |
| route_foreclosure | `211 audited / pads foreclosed by the plan(s): none`; EXIT 1 from the stale, swap-unaware ball-slot table (stage 12 judge, section 4.2) | not a brief gate; nothing foreclosed |
| route_stitch / capacity | EXIT 0 / EXIT 0 (south band 699 -> 554 lanes, U1 east 398 -> 187) | reports |
| USB pair | 17.0808 mm each; coupled at 0.300 pitch (0.150/0.150) for 15.2245 mm; uncoupled 1.8563 / 1.8562 (limit 3.0); skew 0.0001; route_width P 0.200 / N 0.225, EXIT 0 | PASS |
| SDRAM 0.10 rule | extra gate 4 (via-to-via) +0.0022 mm; **all copper +0.0010188 mm** (LED0_B via (31.8,6.95) vs a D5 track on L4; `slack_s13.log`) | PASS |
| via land to outline | worst 0.8150 mm over 927 plan vias | PASS |
| short / duplicate / overlapping tracks | 2745 tracks, 3319.792 mm; 145 < 0.08 mm, 0 < 0.02 mm; 0 duplicates, 0 zero-length; collinear same-net overlaps plan-plan 0 / plan-board 0 (extra gate 8 and `overlaps.py`). Stage 12's 4 are gone. | PASS |
| widths | {0.0762: 2696, 0.15: 35, 0.2: 14}; per-net rules 0 violations (route_emit) | PASS |
| fixed parts | usb_plan, fixed_D, hand_D, tie (stage-12 originals), lever13, esc13: 0 missing or altered; XADC L3 segments in the remove list 14; lever-1 conversions 14 / 14 | PASS |

Census (extra gate 7):
- 927 via records become **1440 Altium via objects**:
  - Top/L2-GND 297 (283 stack tops + 14 lever-1 GND microvias);
  - L2-GND/L3-SIG 283;
  - L3-SIG/L4-SIG 370;
  - L4-SIG/L5-VCC3V3 230;
  - L5-VCC3V3/Bottom 230;
  - through 30.
- Removals: 64 tracks + 23 vias.

## 3. The plan's levers, checked from the files

- **Inputs** (`cmp_inputs.log`). `inputs_gate.json` equals stage 12's `inputs_gate.json` (269c1670) in every key. The
  only differences are one added HDI span `Top,L2-GND` and its comment. The span is a laser, 0.15/0.30, pitch 0.39,
  antipad 0.48, land_field_ban false.
  The 13 swap re-nets are stage 12's: against `tools/route_inputs.json`, the gate inputs differ in exactly 13 U1 pad
  nets, 7 tracks and 5 vias (`verify_placed_selftest.log`, first run).
- **Lever 1** (`lever1_check.log`).
  - Each of the 14 removed GND through vias carried only Top GND track ends (1 or 2). Each is replaced at the same XY by
    a Top>L2-GND microvia.
  - 13 of the 14 freed sites now carry plan copper on L3/L4/Bottom. K9 (45.9,11.8999) carries none. That is harmless:
    the tie is the same, with one laser in place of one through via.
  - The PcbDoc already defines this via type: Board6 has `VIATYPE1LOW = TOP, VIATYPE1HIGH = PLANE1, DRILLPAIRTYPE = 1`
    (read-only olefile read). It is the same Top-L2 laser layer that every stack top uses, so Altium needs no new setup.
- **Lever 2**. VCCADC 12.69 mm and GNDADC 10.62 mm run on L4 through U1's core (stage 12: 16.21 / 18.14), with 0 vias and
  the same end vias. VCCADC at 0.20 mm meets the PWR_RAILS 0.15 minimum. The pair still references L5 (VCC3V3), which is
  stage 12's open noise question.
- **Removals** (my census). 64 tracks + 23 vias in all:
  - SDRAM objects removed: 0. USB objects removed: 0.
  - Power/GND-class removals are only the 14 GND vias (lever 1), 6 VCCADC + 8 GNDADC L3 segments (lever 2) and 3 NODE_P1
    Bottom tracks (corridor D, stage 11b).
  - The nearest removal to a C155-C159 pad is 7.864 mm.
  - All 12 placed objects of the swapped balls (phase2 section 2) are in the removal list.
- **Land-field ban**. Plan vias inside U1's land field: 48 L3/L4 buried, 8 Top/L2, 26 Top/L2/L3. Banned spans inside: 0.
- **Lengths** (my census against stage 12).
  - The four that were open: LED0_R 87.31 mm / 29 via records, UART_FT_TXD 27.33 / 10, CHAN9 40.49 / 9, CHAN6 20.61 / 8.
  - UART_FT_DTR# grows from 24.2 to 75.3 mm.
  - Clock nets are unchanged (FPGA-TCK 94.7, CLK-12M-FT 51.9, SD-CLK 36.2 mm).
  - Every net that changed is low-speed, so there is no SI concern.

## 4. My own measurements beyond the gates

### 4.1 Clearance margin, down to Altium's integer unit

Census: `python slack_census.py inputs_gate.json plan.json` (`slack_s13.log`). It uses route_emit's geometry and both
nets' clearances, with my own pairing over every plan-involved different-net pair on a shared layer.
- **0 pairs below 0.** 1 below 0.000026 mm, 10 below 0.0005, 70 below 0.001, 200 below 0.002.
- The worst is **+0.0000212 mm**: the plan's UART_FT_DTR# laser at (31.625,13.55) against the placed USB5V0 Top track
  (32.1,11.0)-(32.1,13.2), width 0.70.
- Stage 12's worst was +0.0000917 (`slack_s12.log`).

The same pair at Altium's own precision (`python altium_precision.py <PcbDoc>`, `altium_precision.log`):
- 1 unit = 2.54e-6 mm.
- The track's raw Tracks6 integers, read from the PcbDoc, are 12637795 / 4330709 / 12637795 / 5196850, width 275591.
- The via is placed at MMsToCoord, with either rounding or truncation.
- The gap is 35441.24-35441.84 units. The Clearance rule is stored as 3.5433 mil = 35433 units.
- **Slack: +8.24 to +8.84 units (+21 to +22 nm).** It does not flip.

The worst SDRAM-rule pair is +0.0010188 mm.

### 4.2 Hole-to-hole: the classes Altium may flag

`python holes_expected.py inputs_gate.json plan.json holes_expected.txt` (`holes_expected.log`) takes every Altium via
object after placement: board 354 + plan 1440 = 1794. It classifies every pair whose hole edges are closer than the
board's HoleToHoleClearance of 0.24 mm (ALLOWSTACKEDMICROVIAS TRUE):

| class | stage 13 | stage 12 |
|---|---|---|
| A: same XY, same net, stacked microvias (exempt by the checkbox) | 513 | 468 |
| B: same XY, same net, a microvia on a buried via (Altium behaviour unproven; JLC question 1) | 195 | 182 |
| C: same XY, same net, disjoint spans of one full stack | 303 | 294 |
| D: different nets, disjoint spans (tools/hdi.json `disjoint_span_pitch` 0.0; JLC question 11) | 122 | 88 |
| **E: anything else (a real hole-to-hole defect)** | **0** | 0 |

The verifier's "2 new same-XY different-net disjoint stacks" are real but **not new in kind**:
- They are (29.0,11.85), N$LD0B over CHAN23, and (38.3,24.4), LED0_R over FPGA-TCK.
- Together they are 8 of class D's 122 object pairs.
- Stage 12 already had class-D pairs whose holes overlap in plan view by 0.10 mm (`disjoint_vias.log`).

The class is legal in the adopted HDI model and still open with JLC. It sets a rule for reading the Phase II DRC and is a
question for JLC; it is not a plan defect.

### 4.3 Plane webs: the gate's through-via void is too small (gate-calibration finding)

`webs_gate.py` (the stage-10 judge's webs.py) voids a through via at 0.20 + 2 x 0.165 = 0.53 mm. The board's
PlaneClearance for anything that is not a microvia is the All-scoped 9.8425 mil = 0.25 mm (inputs `rules`, hdi_spec
section 7), which gives 0.70 mm. That is also what `tools/stage6/plane_islands.py` uses ("a 0.20 mm via hole punches
0.70 mm").

I re-measured with 0.70 (`python webs_thru.py inputs_gate.json plan.json 0.25`, `webs_thru_025.log`; `webs_thru.py` is
webs_gate.py with the through clearance as an argument). Result: **12 plan-involved thin webs (0 < web <= 0.03 mm)**.

| layer | pair (web in mm) |
|---|---|
| L2 | UART_FT_DTR# / USB5V0 at (31.625,13.55) (about 0) |
| L2 | PROG# / USB5V0 (0.0121) |
| L2 | LED0_G / VCC3V3 (0.0183) |
| L2 | CHAN-CLK / VCC3V3 (0.0183) |
| L2 | LED0_G / BS0 (0.0203) |
| L2 | FLASH-CS# / VCC3V3 (0.0285) |
| L2 | FLASH-D02 / CHAN2 (0.0285) |
| L5 | FLASH-D02 / GND at (57.65,15.3) (about 0) |
| L5 | CLK-12M-FPGA / VCC1V0 (0.0121) |
| L5 | PROG# / GND (0.0121) |
| L5 | LED1 / GND (0.0121) |
| L5 | CLK-12M-SHARED / CHAN2 (0.0285) |

For comparison:
- the placed board alone already has 18 such webs (6 on L2, 12 on L5);
- stage 12's plan had 9 (`webs_thru_025_s12.log`).

**No web is load-bearing.** I enlarged every void by 0.03 mm (through clearance 0.265, microvia 0.18), which closes
every web of 0.03 mm or less. All 216 GND pads and 135 GND vias stay on L2's main island, and all 133 VCC3V3 pads and 86
vias stay on L5's (`python plane_robust.py 0.265 ... --uvia-clearance 0.18`, `plane_robust.log`).

So these are plane slivers for JLC's CAM (question 7), not a connectivity problem. I do not block on them. The gate must
still be corrected before later work relies on it.

### 4.4 The plane-clearance reading (hole edge vs pad edge)

The plane gates assume Altium measures PlaneClearance from the hole edge, which is unproven (hdi_spec section 7). I
stress-tested the pad-edge reading:
- **Pad-edge reading** (through-via voids 0.85 mm, microvia voids 0.63 mm): every via still lands on its plane's main
  island. But R17-2 and C88-2 (GND) and U1-K1 (VCC3V3) would sit over a void (`plane_robust.log`).
- **Pad-edge reading with PlaneClearance_uVia set to 0.09** (the spec's prescribed value under that reading; through-via
  voids stay at 0.85): everything passes again, 216/216 + 135/135 on L2 and 133/133 + 86/86 on L5
  (`plane_padedge_fixed.log`).

Phase II step 0 settles which reading Altium uses. If it is the pad edge, the remedy is a rule value, not copper.

### 4.5 DRC categories the brief does not gate (expectations for Phase II)

- **Net Antennae** (`python antennae.py inputs_gate.json plan.json`, `antennae.log`). Calibration: on the placed board my
  model gives 24 dangling ends + 27 one-sided vias; Altium reports 50. After the plan:
  - **1 dangling track end:** the FLASH-D02 Top stub (50.6501,13.65)-(51.1125,13.65). The net joins at (50.65,13.65), per
    conn_override_flash.json.
  - **5 one-sided vias:** VCC1V8 (48.4001,12.4) and (48.4001,12.8999), SD-DAT2 (43.4001,11.8999), CHAN17
    (49.6501,7.02), all four already on today's report; and CHAN6's new buried via (49.4,12.92) under its microvia
    dogbone, whose L4 land carries nothing.
  - Expect about 6 (down from 50).
- **Power Plane Connect (relief).** Today 1 (X2-20, at the board corner). `thermals.py` (an approximate spoke model)
  finds that the plan blocks at most one more entry, on one GND TH pad (X1-MS1 with 45-degree spokes), and never all
  four.
- **Isolated plane copper** (reported under Un-Routed). Today 3: GND on L2 x1, VCC3V3 on L5 x2, each "0.125 sq. mm".
  plane_islands predicts 1 stray > 0.0005 mm2 on L2 and 6 on L5 after the plan; none holds a pad or a via. Record
  Altium's count.

### 4.6 Altium mechanics the plan depends on

- **Helpers.** Each chunk calls `BoardOrNil`, `FanNet` (-> `NetByName`), `FanTrk`, `FanVia` and the global `Brd`. All of
  them are defined in `tools/ZuluSetup.pas` (md5 `869dc1b266d9574447c548bcfc7cd6c1`, lines 85-97, 712 and 1132-1165);
  no chunk defines them. Altium script projects share globals across units, so each chunk runs from its own fresh
  `.PrjScr` that holds ZuluSetup.pas (unchanged) plus that chunk. ZuluSetup.pas has no PlaceStage12/13 procedure, so no
  name collides.
- **Kill-list order.** Chunk 01's kill list finds its 87 objects by POST-swap net name and geometry (`If Kill.Count <> 87
  ... Nothing changed`). The XDC, schematic, ECO and re-net steps must therefore come first, as at stage 12.
- **Reading a placed board back.** After placement the board stores each laser stack as two via objects.
  tools/block_place.islands joins a via only on the signal layers of its span, so the gates read every stacked net as
  split (on a simulated placed board: 100 split nets). `merge_stacks.py` merges the stacks back. On the simulated placed
  board (gate board minus removals plus plan objects, passed through Altium's integer unit) the gates then give:
  - signals_check 174 joined / 1 split (VCC3V3);
  - gnd_check 206/206; tie_check 129/129;
  - planes 216/216 + 135/135 on L2 and 133/133 + 86/86 on L5;
  - `verify_placed.py` PASS (`verify_placed_selftest.log`).

## 5. The verifiers' claims

**Copper verifier: all three corrections adopted.**
1. The SDRAM margin over all copper is +0.0010 mm, not +0.0022 (which is via-to-via only). Re-measured: **+0.0010188**
   (4.1).
2. "GNDADC west of VCCADC everywhere at 0.28 mm" holds only on the main core run; at the south end VCCADC wraps the
   GNDADC via. Adopted as stated; it affects the description only.
3. Two same-XY different-net disjoint laser stacks: adopted as fact and re-framed (4.2). They are class D, 122 pairs in
   all; stage 12 had 88.

Where it mattered, I re-measured their confirmed claims:
- 140 closed / 0 open / 0 shorts (my uf_judge);
- every gate tail;
- the Pascal md5s;
- the removals;
- the swaps (xdc_check.py: the 13 balls are a permutation, all bank 14, no create_clock port moved, 101 PACKAGE_PINs
  unique after the edits);
- gen13 --check.

**ld0 verifier.** Its three corrections concern the arm's supporting prose: the mixed models in the site choice, the
TXD:CLK-12M-FPGA proxy result, and an unrecorded FORBID rectangle. I adopted them without re-measuring, because none of
them can change the 136.

## 6. Risks carried forward

1. **Stacked signal vias on the former negative planes: resolved.**
   - The negative-plane representation did not provide a reliable fabrication path for all required stacked-microvia
     lands, so the prescribed fallback was applied before placement.
   - L2-GND and L5-VCC3V3 are now positive signal layers with full-board net polygons.
   - Final Gerbers contain every 0.300 mm land, nominal 0.480 mm foreign-microvia voids, nominal 0.700 mm
     foreign-through-via voids, and direct same-net plane connections.
2. **Plane webs.** 12 plan-involved thin webs under the board's real through-via void (4.3), plus 18 already on the
   board. JLC question 7. None is load-bearing.
3. **Hole-to-hole.** Altium may flag class B (195), C (303) and D (122) pairs (4.2); class E is 0. JLC questions 1 and 11.
4. **Plane-clearance reading** (4.4). If Altium measures from the pad edge, set PlaneClearance_uVia to 0.09.
5. **Thin margins at the rule edge.** Clearance +21 nm (checked at integer precision), SDRAM +0.0010 mm, corridor D
   +0.0013 (stage 11b).
6. **XADC on L4** references the L5 VCC3V3 plane (stage 12's open question for the user).
7. **Buried vias.** The plan needs 370 buried L3-L4 vias (stage 12: 326). JLC's buried-via and lamination fees are still
   "manual quote" (hdi_spec sections 2-3).
8. **Provenance.** `gen13.py --check` replays phase F only. `--full` (D1, E2, and E4 with its 6-worker PathFinder
   negotiation) was not re-run by the arm, the verifier or me. The plan file is what gets placed, and it is gated
   directly.
9. **Stage-local rules outside tools/** (SDRAM 0.10 via rule, webs, overlaps, chunking): unchanged from stage 12.
10. **Cosmetic.** FLASH-D02's 0.46 mm stub antenna; CHAN6's buried via dead-ends on L4; K9's conversion is unused; LED0_R
    takes 87 mm and 29 via records (it carries DC).

## 7. Phase II change list (historical execution record; completed)

Files to use (copy them into the repo record before starting):
- `J/plan.json` (b59c168a...);
- `J/inputs_gate.json` (cf43b174...);
- `J/g_plan/pas/PlaceStage13_0k.pas` (= the arm's `gates_final/pas`):

  | chunk | md5 | bytes |
  |---|---|---|
  | 01 | edbfbe37 | 373491 |
  | 02 | 2dd60971 | 387845 |
  | 03 | 4ee593cc | 367780 |
  | 04 | fad037e3 | 384186 |
  | 05 | 1a739542 | 355359 |
  | 06 | 7beed814 | 277730 |
- `J/g_plan/pas/chunk_0k.json`: 01 4d1b20a6, 02 18d866fb, 03 1c41a8f7, 04 370ecfe7, 05 92df6ae5, 06 6dd7bcd2.

### Step 0: preconditions (no edit to the live board)

**Completed result:** the negative-plane test triggered the signal-polygon fallback described in the closeout. The
converted stack and polygons passed connectivity, saved-file, Gerber, and final DRC checks.

(a) The md5s of the PcbDoc, zulu_a7_5.SchDoc, the XDC and tools/route_inputs.json equal the ones in the header. Only one
X2.EXE is running.

(b) The HDI stacked-via test, on a COPY of the PcbDoc:
- Place one foreign-net Top-L2 + L2-L3 microvia pair at one free XY, with Top and L3 track ends, and one GND Top-L2
  microvia. Run DRC and export an L2/L5 Gerber.
- Pass means all four hold:
  - Altium shows the Top-L3 connection as made (no Un-Routed line for it);
  - the L2 Gerber has a 0.30 landing pad inside the void;
  - the foreign void is 0.48 mm (and through-via voids are 0.70);
  - the GND microvia connects Direct.
- If the voids are 0.63 / 0.85 (the pad-edge reading): set PlaneClearance_uVia to 0.09 (4.4).
- If there is no landing pad or no connection: first convert L2/L5 to signal layers with full polygons (spec user
  decision 8), re-run the plane gates, then continue.
- Delete the copy.

### Step 1: XDC

`vivado/zulu_a7_pins.xdc`: 13 PACKAGE_PIN edits. IOSTANDARD stays unchanged; update each trailing comment to the new
ball's function.

| line | port | from | to | new ball's function |
|---|---|---|---|---|
| 80 | JA3 | G17 | W18 | IO_L16P_T2_CSI_B_14 |
| 49 | CHAN7 | H19 | G17 | IO_L5N_T0_D07_14 |
| 28 | CHAN13 | W18 | H19 | IO_L4P_T0_D04_14 |
| 82 | JA7 | T17 | R19 | IO_L10N_T1_D15_14 |
| 44 | CHAN28 | R19 | T17 | IO_L17P_T2_A14_D30_14 |
| 83 | JA8 | E19 | W19 | IO_L16N_T2_A15_D31_14 |
| 27 | CHAN12 | W19 | E19 | IO_L3N_T0_DQS_EMCCLK_14 |
| 104 | UART_FT_TXD | K18 | K17 | IO_L12N_T1_MRCC_14 |
| 26 | CHAN11 | K17 | K18 | IO_L8N_T1_D12_14 |
| 86 | LED0_B | N19 | N17 | IO_L13P_T2_MRCC_14 |
| 21 | BTN | N17 | N19 | IO_L9N_T1_DQS_D13_14 |
| 76 | FT_PWREN_N | P17 | P19 | IO_L10P_T1_D14_14 |
| 88 | LED0_R | P19 | P17 | IO_L13N_T2_MRCC_14 |

*Verify:* `python J/xdc_check.py <xdc> Datasheet/xc7a35tcpg236pkg_pinout.txt <edited xdc>` must print XDC_CHECK PASS:
- each line names its port on its new ball;
- the 101 PACKAGE_PINs are unique;
- the 13 balls are a permutation;
- all are bank 14, LVCMOS33;
- no create_clock port moved.

CONFIG_MODE is SPIx4 and there is no PERSIST, so CSI_B, D04-D15 and EMCCLK are user I/O after configuration.

### Step 2: schematic

`zulu_a7_5.SchDoc`:
1. Before editing, export the Protel netlist (Design > Netlist For Project > Protel) and keep it as before.NET. Run
   `python J/netlist_expect.py before.NET <prefix>`.
2. Rename the 13 RECORD=25 net labels by coordinate. Each label is 30 units from its U1 pin and the neighbour's label is
   31.6 away, so go by the coordinate, not by proximity. All 13 matched in a read-only check (`sch_check.log`: ALL 13
   CLAIMS MATCH).

   | label at | ball | from | to |
   |---|---|---|---|
   | (255,952) | H19 | CHAN7 | CHAN13 |
   | (255,912) | K17 | CHAN11 | UART_FT_TXD |
   | (255,892) | W19 | CHAN12 | JA8 |
   | (255,882) | W18 | CHAN13 | JA3 |
   | (935,802) | K18 | UART_FT_TXD | CHAN11 |
   | (235,1132) | P17 | FT-PWREN# | LED0_R |
   | (935,357) | E19 | JA8 | CHAN12 |
   | (935,367) | T17 | JA7 | CHAN28 |
   | (935,387) | G17 | JA3 | CHAN7 |
   | (740,262) | N19 | LED0_B | BTN |
   | (740,252) | P19 | LED0_R | FT-PWREN# |
   | (740,212) | N17 | BTN | LED0_B |
   | (740,202) | R19 | CHAN28 | JA7 |
3. Save and export after.NET.

*Verify:*
- `python tools/compare_netlists.py after.NET <prefix>_expected.json` must print CONNECTIVITY MATCH.
- `python tools/compare_netlists.py after.NET <prefix>_before.json` must show differences on exactly these 13 U1 pads.

### Step 3: ECO

Design > Update PCB Document must list exactly 13 pad-net changes on U1:

| pad | from | to |
|---|---|---|
| E19 | JA8 | CHAN12 |
| G17 | JA3 | CHAN7 |
| H19 | CHAN7 | CHAN13 |
| K17 | CHAN11 | UART_FT_TXD |
| K18 | UART_FT_TXD | CHAN11 |
| N17 | BTN | LED0_B |
| N19 | LED0_B | BTN |
| P17 | FT-PWREN# | LED0_R |
| P19 | LED0_R | FT-PWREN# |
| R19 | CHAN28 | JA7 |
| T17 | JA7 | CHAN28 |
| W18 | CHAN13 | JA3 |
| W19 | CHAN12 | JA8 |

**Untick Remove Net Classes (10) and Remove Differential Pair USB.** If the ECO lists anything else, stop. Then
Validate, Execute, Ctrl+S.

*Verify from the file:* run `python tools/route_inputs.py`, then `python J/verify_placed.py tools/route_inputs.json
J/inputs_gate.json`. The 13 pad nets must now match; only the 7 tracks + 5 vias of step 4 may still differ. A pad whose
net did not persist (the R78-1 trap) is re-netted in step 4 with `N.AddPCBObject(P)`.

### Step 4: re-net the swapped balls' placed copper by script

Use a fresh .PrjScr with ZuluSetup.pas. For each object: `O.BeginModify; O.Net := N; N.AddPCBObject(O); O.EndModify`.
Guard: find exactly these 12 objects by old net + geometry within 0.001 mm, or change nothing.

| ball | objects | from | to |
|---|---|---|---|
| G17 | Top track (49.4001,13.4)-(49.9,13.4) + through via (49.4001,13.4) | JA3 | CHAN7 |
| K17 | Top track (49.4001,11.8999)-(49.9,11.8999) + via (49.4001,11.8999) | CHAN11 | UART_FT_TXD |
| K18 | Top tracks (50.4001,11.8999)-(50.6502,12.15) and (50.6502,12.15)-(51.1125,12.15) | UART_FT_TXD | CHAN11 |
| N17 | Top track (49.4001,10.345)-(49.9,10.4) + via (49.4001,10.345) | BTN | LED0_B |
| P17 | Top track (49.4001,9.8999)-(49.9,9.8999) + via (49.4001,9.8999) | FT-PWREN# | LED0_R |
| T17 | Top track (49.4001,8.8999)-(49.9,8.8999) + via (49.4001,8.8999) | JA7 | CHAN28 |

Chunk 01 deletes all 12 one step later. The re-net exists only so its kill guard finds them. Ctrl+S.

*Verify:*
- `python tools/route_inputs.py`, then `python J/verify_placed.py tools/route_inputs.json J/inputs_gate.json` must print
  VERIFY_PLACED PASS (tracks 1518, vias 377, 0 missing / 0 extra, pad nets 0 differ).
- DRC: Short-Circuit 0, Clearance 0, and Un-Routed 140 connections on 109 nets plus the 3 isolated-copper items.
  `python J/drc_compare.py <report.drc> J/drc_gate.drc` must print DRC_COMPARE MATCH.

### Step 5: removals and chunk 01

Make a fresh `Stage13_01.PrjScr` = tools/ZuluSetup.pas + PlaceStage13_01.pas, then Run Script > Browse >
PlaceStage13_01.

The script first collects the 87 objects (64 tracks + 23 vias):
- 14 XADC L3 segments;
- 5 corridor-D tracks;
- 36 ring-1 stubs of 18 nets;
- 9 dogbones: CHAN28, LED0_R, LED0_B, UART_FT_TXD, CHAN9, CHAN6, CHAN7 and CHAN5 at x 49.4001, and CHAN24 at
  (48.4001,8.8999);
- 14 GND through vias.

It aborts with "found N of the 87 ... Nothing changed" unless all of them exist. Otherwise it removes them and adds GND,
VCCADC and GNDADC first, so no U1 power ball is left without its via between chunks.

Final regenerated message: "removed 95, added 219 via objects (146 plan vias) and 450 tracks". If a "nets were NOT found" message
appears, do not save: run RemoveStage13_01 or close without saving.

*Verify:*
- DRC: Clearance / Short-Circuit / Width 0; HoleToHole only in classes A-D of `J/holes_expected.txt`.
- Ctrl+S, then `python tools/route_inputs.py`.
- `python J/verify_placed.py tools/route_inputs.json J/inputs_gate.json J/plan.json J/g_plan/pas/chunk_01.json` must
  print PASS (tracks 1900, vias 569).

### Step 6: chunks 02 to 06

Run each from its own fresh .PrjScr (ZuluSetup.pas + the chunk), in this order. The order is fixed, because each chunk's
route_emit proof is against the board after the earlier chunks. The undo for chunk k is RemoveStage13_0k, applied in
reverse order.

| chunk | nets | tracks | via objects | tracks after | vias after |
|---|---|---|---|---|---|
| 02 | 16 | 544 | 238 | 2444 | 807 |
| 03 | 21 | 488 | 242 | 2932 | 1049 |
| 04 | 20 | 463 | 289 | 3395 | 1338 |
| 05 | 24 | 458 | 250 | 3853 | 1588 |
| 06 | 9 | 343 | 199 | 4196 | 1787 |

*Verify after each:* as in step 5, listing chunk_01 .. chunk_0k on the verify_placed line; the expected totals are the
last two columns.

### Step 7: final DRC and file-level gates

DRC with the HDI rules, read with `python J/drc_compare.py <report.drc>`:

| rule | expected |
|---|---|
| Un-Routed | **0 "Net ... Between" connection lines** (record isolated plane copper items separately; today 3) |
| Clearance (0.09, SDRAM 0.10, SDRAM-CLK 0.20) | 0 |
| Short-Circuit | 0 |
| every Width rule | 0 |
| DiffPairsRouting | **0 violations: the USB pair at 0.150 / 0.150 with uncoupled length <= 3.0 mm** (gates: 15.2245 mm coupled, 1.8563 uncoupled) |
| HoleToHole | only classes A-D; any class-E pair is a defect: stop |
| Net Antennae | about 6 (4.5) |
| Power Plane Connect | at most 2 |

Then, from the saved file:
1. `python tools/route_inputs.py`.
2. `python J/verify_placed.py tools/route_inputs.json J/inputs_gate.json J/plan.json` prints PASS: 4196 tracks and
   1787 vias (through 380, Top-L2 296, L2-L3 282, L3-L4 369, L4-L5 230, L5-Bottom 230).
3. `python J/merge_stacks.py tools/route_inputs.json J/inputs_gate.json placed.json`, then run on `placed.json` with
   `J/empty_plan.json`:
   - signals_check: 174 joined / 1 split (VCC3V3 only);
   - gnd_check: 206/206;
   - tie_check: 129/129;
   - plane connectivity: L2 216/216 + 135/135 and L5 133/133 + 85/85 with the final signal polygons.
4. Save, commit, record.

## 8. Remaining manufacturing handoff

Routing, DRC, Gerbers, and NC drills are complete. Before ordering, package the generated fabrication files and provide
the fabricator with the six-layer sequential-lamination drill-pair map from `zulu_a7.LDP`. The XADC supply pair remains
on L4 over the L5 VCC3V3 plane, as carried from stage 12. Teardrops and IBIS work remain optional engineering follow-up;
they are not routing-completion blockers.

## 9. Evidence index (all in J)

- **The gate re-run:** `run_gates.sh`, `g_plan/*.log`, `g_plan/pas/*` (6 .pas + chunk/inputs json), `g_plan_run.log`.
- **The closure counts:** `uf_judge.py` (the stage-12 judge's, md5 bf59607a) with `uf_plan_strict.log`,
  `uf_plan_tjoin.log`, `uf_plan_noplanes.log`, `uf_empty.log`, `uf_s12_control.log`, `uf_ld0.log`, `uf_capacity.log`.
- **My measurements:**
  - `cmp_inputs.py` + `cmp_inputs.log`;
  - `lever1_check.py` + `.log`;
  - `slack_census.py` + `slack_s13.log`, `slack_s12.log`;
  - `altium_precision.py` + `.log`;
  - `holes_expected.py` + `.log` + `holes_expected.txt`;
  - `disjoint_vias.py` + `.log`;
  - `webs_thru.py` + `webs_thru_025.log`, `webs_thru_0165.log`, `webs_thru_025_s12.log`;
  - `plane_robust.py` + `plane_robust.log`, `plane_padedge_fixed.log`, `plane_L2_empty.log`, `plane_L5_empty.log`;
  - `antennae.py` + `.log`;
  - `thermals.py` + `.log`.
- **Phase II tools:**
  - `xdc_check.py` + `xdc_check.log`;
  - `phase2.py` + `phase2_list.txt`;
  - `sch_check.py` + `sch_check.log`;
  - `netlist_expect.py`;
  - `verify_placed.py` + `verify_placed_selftest.log`;
  - `merge_stacks.py`;
  - `drc_compare.py`;
  - `selftest/` (the simulated placed board and the netlist round-trip).
- **The gen13 --check replay:** `genrep/` + `gen_check_judge.log`.
