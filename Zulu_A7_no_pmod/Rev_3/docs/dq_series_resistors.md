# SDRAM DQ series resistors: implementation plan (Zulu_a7_no_pmod Rev 2)

Status: **16 resistors (R119-R134, one on every data bit D0-D15). SCHEMATIC APPLIED 2026-11-13** (sheet 3, by
`tools/dq_series_r_sch.py`; backup `backups/zulu_a7_3.SchDoc.pre-series-r`; Altium compile 0 errors, Protel netlist:
16 bits split exactly as planned, every other pad on its PcbDoc net). **PCB UPDATED AND LAYOUT APPLIED 2026-11-13** (PcbDoc 2a616c1c -> c88d7ac6; backups in `backups/`:
`.pre-series-r-eco`, `.series-r-placed`, `.series-r-pre-microvia`).
- ECO with only the resistor changes enabled: 16 parts, 16 SDRAM-Dn nets, U3's 16 DQ pads re-netted, SDRAM_DATA = 32
  nets. Pre-existing schematic/PCB drift that the ECO also offered (U2 FT2232HL->HQ design item, R113-R118 and
  C78/C80/C160-C167 design items, JP3/JP4 NOTE, U7 class, 4 supply-net rule edits, net-class/diff-pair deletions) was
  left unapplied.
- Placement: `tools/SeriesRPlace2.pas` (pad-anchored; all 32 pads within 0.05 um of the plan, every part at its planned
  rotation, designators hidden); U1's designator moved to (39.70, 16.55) by `tools/SeriesRDesig.pas`.
- Copper: `tools/FabBCopper_SeriesR.pas` from `tools/emit_copper.py` (which now also accepts the plan's short 'Top' /
  'Bottom' via-span names): "removed 69 tracks and 14 vias, placed 32 vias and 107 tracks, Missing nets: (none)".
  `tools/mark_microvias.py --laser 0.30/0.15 --expect 1202` marked exactly the 19 new laser vias.
- Re-poured both planes (`NoPmod_Repour`), rebuilt the ratsnest (`RebuildConnR2`: 0 connections remain).
- **Batch DRC: 0 violations, 0 warnings** (`docs/drc_series_r.drc`).
- Re-extracted board vs (old board + plan): 5707 tracks and 1946 vias, 0 missing, 0 extra. The copper on the board is
  therefore exactly the copper the section-7 simulation and the checkers were run on.
**FAB AND ASSEMBLY RELEASES BUILT 2026-11-13 (steps 9-10)** after five pre-existing through vias were moved out of
SMD pads (PcbDoc c88d7ac6 -> 00989c86, DRC 0/0): see `docs/fab_release.md`. Not done yet: stale copies (step 11). The library has not changed. Every measurement here comes from the PcbDoc on disk, md5
`2a616c1c74f8788a4a1c837c7d76c3b0`, saved 2026-11-12 18:13. Altium had the file open when it was read, so edits that
were not saved yet are not included. Supporting work is in `si/series_r/`. The plan in machine form is
`si/series_r/dq_series_r_plan.json` (md5 `7c2b8ae6`). **User decision 2026-11-13: R132 is accepted with its
spacing (decisions 14 and 15), so D13 keeps its resistor.** History:
- 2026-11-13, D10 pass (`si/series_r/d10/`): R129 on D10, R130 re-sited 0.20 mm east. That 13-resistor plan is kept
  as `si/series_r/dq_series_r_plan_13.json` (md5 `f2949630`).
- 2026-11-13, D13-D15 pass (`si/series_r/d13/`): R132 on D13 (Top), R133 on D14 and R134 on D15 (Bottom, at the U1
  end), plus the DFM fix that moves U1's visible designator. No item of the 13-resistor plan changes.
- 2026-11-13, fallback study (`si/series_r/d13/fallback15/`): a 15-resistor variant without R132 (D13 left without a
  resistor) was built and fully proven (0 hard DFM findings), briefly adopted, then withdrawn by the user the same day
  in favour of this plan. It is kept as `si/series_r/dq_series_r_plan_15.json` (md5 `187b8703`) and is the reserve if
  PCBWay rejects the R131-R132 spacing. On that variant D13 passes on the fab stack at only 93.8 % of the budget
  (21 mV / 0.052 ns margin) and fails on the PcbDoc stack at 507.5 %, which is why R132 was preferred.
- The 12-resistor plan written by `si/series_r/plan_export.py` is kept as `si/series_r/dq_series_r_plan_12.json`
  (md5 `21972745`).

## 1. Why

The independent ngspice + IBIS run (`docs/si_analysis.md`, `si/spice/`) checked SDRAM reads: U3, an AS4C32M16SB-7TCN
on the Bottom side, drives U1, an XC7A35T-2CPG236I with LVCMOS33 inputs in an HR bank. At U1's BGA ball the reads
undershoot to -0.85 to -1.05 V for about 1.2 ns. At R=0 and the max corner, 12 of the 16 data nets fail DS181
Table 4: D0 and D2-D12 (source: `si/series_r/r0_pernet.json`). At the die they pass, using up to 69 % of the
budget. The part has no drive-strength setting.

A 22 ohm series resistor fixes this. This plan places 16 of them, one on every data net D0-D15. Thirteen sit at
the SDRAM end; R133 and R134 (D14, D15) sit at the U1 end, which works as well at these edge rates. Placed where this
plan puts them, the worst ball reading is -0.272 V, which uses 1.2 % of the Table 4 budget on the fab stack (D10,
max corner), and 1.35 % (D8) on the PcbDoc stack. The die uses 0 % everywhere. Writes still pass, and the reads
arrive 0.03-0.10 ns later. Without R132-R134, D13, D14 and D15 failed at the ball on the PcbDoc stack (D14 31239 %
at the max corner); with them they read 0 % on both stacks (decision 4).

## 2. Decisions needed from you

| # | Question | Recommended answer | Basis |
|---|---|---|---|
| 1 | Value: 15, 22 or 33 ohm? | **22 ohm.** | It is the only value tested that is clean on every criterion: worst ball 0.85 % on the 12-resistor run and 1.2 % with R129 added (`d10/sim/sim_final.md`), die 0 %, and no ringback into 0.8-2.0 V. 15 ohm leaves less margin (6.6 % on the fab stack, 8.8 % on the PcbDoc stack). 33 ohm reuses the existing RC0201FR-0733RL line, but it brings back ringback at the U1 ball on D5-D8 (up to 0.169 V on D7) and stretches read edges to 1.35 ns. Source: `si/series_r/sim_placed.md` §1. The 16-resistor sweep on the PcbDoc stack (worst nets D8, D10, D0, D3 plus D13, D14) agrees: 15 ohm 8.68 % ball / 3.19 % die, 22 ohm 1.35 % / 0 %, 33 ohm 0 % / 0 % but 0.025 V ringback at the D8 ball and slower edges (`d13/sim/sim_final.md` §4). |
| 2 | ~~D10 has no resistor in the 12-resistor plan. How should D10 be handled?~~ **ANSWERED 2026-11-13: R129 is in the plan.** | Done: the targeted D10 pass ran (`si/series_r/d10/`). Three designs were built; the judge chose "relocate". | R129 goes on D10's own Top run at (39.21, 14.36), and R130 moves 0.20 mm east and 0.02 mm north to make room. No new vias, no via-in-pad, no pour change, no other net touched. D10 at the ball: 3059 % -> 1.2 % (max) and 2609 % -> 0.6 % (typ); die 68.7 % -> 0 %. Proven by two checkers on the folded plan (0 violations, 0 shorts, 0 opens, pours one island each) and an independent adversarial DFM review (PASS). Fallback: `d10/stagger/plan.json` (decision 12). Source: `d10/judge/`, `d10/verify/adversary_final.log`, `d10/sim/sim_final.md`, `d10/fold/`. |
| 3 | ~~Add the optional R134 on D15?~~ **SUPERSEDED 2026-11-13 by decision 4.** | R134 is in the plan, but not at the judge's optional site: it sits on the Bottom at the U1 end, (46.80, 16.80). | The D13-D15 pass searched every proven site; the U1-end Bottom site needs only 2 new vias and is compatible with R132 and R133. U1's designator still has to move, now because of R132 (decision 13). |
| 4 | ~~D13, D14 and D15 have no resistor. On the PcbDoc stack they fail at the U1 ball (max corner D14 31239 %, D13 508 %, D15 368 %). Accept them?~~ **ANSWERED 2026-11-13: no; R132-R134 are in the plan.** | Done: the D13-D15 pass ran (`si/series_r/d13/`). R132 (D13) on the Top at (38.75, 16.3035), R133 (D14) on the Bottom at (45.60, 17.15), R134 (D15) on the Bottom at (46.80, 16.80). Confirming the stack in the EQ is still useful, but it no longer decides anything. | All three read 0 % at the ball and the die on both stacks and both corners. PcbDoc max corner: D14 31239 % -> 0 %, D13 507.5 % -> 0 %, D15 368 % -> 0 %. R132 is the only D13 site found (u1_end and inner_run found none). Proven by two checkers on the folded plan (0 violations, 0 shorts, 0 opens, pours one island each) and an adversarial DFM review (PASS WITH FIXES; fix F1 is folded in). Fallback without R132: `d13/u1_end/plan.json` (D14 + D15 only, D13 uncovered). Source: `d13/combine/`, `d13/verify/`, `d13/fold/`, `d13/sim/sim_final.md`. |
| 5 | Part: RC0201FR-0722RL on the existing R0201 footprint? | **Yes.** | Adds one BOM line. PCBWay already assembles 86 0201s on this design family. The MPN is built from Yageo's naming pattern; stock and lifecycle at PCBWay were not checked, so check them when the quote is made. |
| 6 | Designators? | **Number by bit: R119 + n.** That gives R119-R134. | R119-R134 are free in both the SchDocs and the PcbDoc. Source: `schematic_plan.md` §3.1. |
| 7 | Net names on the resistor's U3 side? | **SDRAM-D0 ... SDRAM-D15.** | This follows the existing SDRAM-CLK / SDRAM-CS# style, and it is the only style `tools/bom_audit.py` `sdram_ok()` accepts without a code change. None of the names is in use today. For R133 and R134 the SDRAM-Dn side is the long one (U3 pin to the R at the U1 end). |
| 8 | Commit the uncommitted Altium signal-integrity model edits in sheets 3-5 (saved 2026-11-12 18:21-18:23) first, or fold them into this change? | **Commit them first, as a separate commit.** | That keeps the resistor diff limited to the resistor change. |
| 9 | Accept the south resistors at 0.195-0.25 mm from U3's toes? That is below the 0.254 mm ComponentClearance, and they overlap U3's IPC-7351B nominal courtyard by about 0.19 mm. | **Yes, and ask PCBWay to confirm it in the EQ.** | The batch DRC does not process ComponentClearance (`docs/drc_jtag_column.drc`), and the board already has 60 part pairs closer than 0.254 mm. After fix F2 the copper-to-copper gap to the other-net toes is 0.25 mm, with a 0.15 mm mask web. |
| 10 | U3-12 (VSSQ) ground path gets longer: 7.40 -> 7.81 mm to the nearest L2 via, 2.39 -> 2.81 mm to C152-1. Add a GND drop? | **Accept it.** | That ground was already the weakest on the row. A new drop would need its own site search, which has not been done. U3-9 VDDQ improves from 6.37 mm to 0.83 mm. |
| 11 | Open an AMD support case asking whether DS181 Table 4 applies at the die or at the ball? | **Yes, in parallel.** | If the answer is "die", the board passes today and the resistors are optional. No AMD document says which. |
| 12 | Accept R129 and R130 (both Top, D10 and D11) at 0.26 mm pad to pad? Their bodies are about 0.23 mm apart at the 0.33 mm maximum body width, their IPC-7351B nominal courtyards overlap by 0.04-0.07 mm, and the mask web between them is 0.16 mm. | **Yes, and add the pair to the PCBWay EQ next to decision 9.** If PCBWay objects, switch to `d10/stagger/plan.json`. | Every enforced rule passes: mask web >= 0.10, and ComponentClearance 0.26 against 0.254 on Altium's pad-box measure (the R0201 footprint has no body or outline). ComponentClearance is not in the batch DRC. The stagger plan is fully proven too (0 violations, D10 1.1 % max): 0.35 mm body gap and 0.28 mm mask web, but it also moves R127, re-routes UDQM and creates about 10 new +0.0003 mm copper pairs. Do not nudge R130 north to gain spacing: its +0.035 mm to the UART_FT_CTS# microvia is the next limit. |
| 13 | U1's visible designator "U1" at (39.2168, 16.6251) is 0.045 mm from R132-1's mask opening. Silk To Solder Mask (0.254 mm, IsPad) is in the batch DRC, so this fails DRC. Move it or hide it? | **Move it to (39.70, 16.55), rot 0** (folded into the plan as `designator_moves`). Hiding it is the alternative. | The new position is at least 0.374 mm from every Top mask opening and at least 3.7 mm from other silk, using a conservative glyph width (`d13/verify/u1_silk.py`). It is the most robust legal anchor within 2.5 mm; the nearest legal one is (39.60, 16.60) at 0.275 mm. `d13/fold/check.py` section 9 gives 0.452 mm to R132-1 and 0.55 mm to R131-2. |
| 14 | Accept R132 at 0.2035 mm pad box to R131 (ComponentClearance 0.254)? Their IPC-7351B nominal courtyards overlap by 0.127 mm, and the mask web between them is 0.1035 mm against the 0.10 sliver rule. R132's courtyard also overlaps U2's by about 0.05 mm (pad gap 0.35 mm). **ANSWERED 2026-11-13 by the user: yes, accept it.** The impedance sweep (§7) confirms it: without R132, D13 fails at the max corner anywhere outside about 42.6-45.3 ohm, which a +-10 % tolerance does not hold. Add both pairs to the PCBWay EQ next to decisions 9 and 12. If PCBWay objects, fall back to `dq_series_r_plan_15.json` (the proven 15-resistor variant, `d13/fallback15/`), which drops R132 (D13 then passes on the fab stack only, at 93.8 %). | Same class as decisions 9 and 12: ComponentClearance is not in the batch DRC. R132 was nudged 0.0035 mm north to lift the mask web from exactly 0.100 to 0.1035; the unnudged pose `d13/combine/plan_alt0.json` also passes. R132 is the only D13 site found. |
| 15 | Accept the new SDRAM-D13 Top track (0.0762 mm) that runs about 1 mm under U2's body corner, between USB5V0 and U2-48? Its mask cover to U2-48's opening is 0.025 mm on the released GTS (corrected 2026-11-13; the plan's estimate said 0.044), and its copper margin to U2-48 is +0.0044 mm. | **ANSWERED 2026-11-13: accepted with R132** (the track is part of the only D13 site). Ask PCBWay about mask registration in the EQ. | U2-48 has no net, so a solder bridge would only hang an unused FT2232 IO on SDRAM-D13. Coupling to USB5V0 and the U2 leads was not simulated. |

## 3. Premise check: what does not fix it

Source: `si/series_r/premise_check.md`, with text extracts in `si/series_r/txt/`.

| Option without a board change | Result | Source |
|---|---|---|
| IN_TERM on U1 | Not available for LVCMOS33/LVTTL; only HSTL/SSTL support it. | UG471 v1.10 Table 1-7, p.33 |
| PULLUP / PULLDOWN / KEEPER | 68-330 uA (about 10-50 kohm), far too weak against a 1 ns event carrying tens of mA. | DS181 v1.27.1 Table 3 |
| U1 input clamp | Not configurable. It is what holds the die at -0.50 V: 6.5 mA typ and 11.3 mA max-corner at -0.5 V. The ball still reaches -0.98 V because the 4.6-6.4 nH package rings in front of the clamp. | U1 IBIS, LVCMOS33_S_8_HR |
| SDRAM drive strength | Not available. There is only the MRS: A7/A8 are vendor test bits and there is no extended mode register. The IBIS DQ_72/39/11 % models cannot be selected on the part. | AS4C32M16SB datasheet Rev 1.2, Table 5, p.14 |
| Slower clock | Does not help. At R=0 the ball peak lies beyond the last row of Table 4, so it fails at any UI. | DS181 Table 4 |
| Accept as is | The die passes at up to 69 %. Whether Table 4 applies at the die or at the ball is unknown (decision 11). | — |

Flag: at R=0 and the max corner, U1's peak die clamp current is 11.7 mA. DS181 Table 2 gives IIN as 10 mA. The pulse
lasts about 1 ns, so this is a flag, not a proven violation. With R >= 15 ohm the clamp current is zero.

**Read timing.** 22 ohm moves the 1.65 V crossing at U1's die by +0.04 to +0.05 ns and narrows the data window by at
most 0.006 ns (`timing.py`). The 16-resistor run gives +0.032 to +0.097 ns at the 1.4 V crossing for reads and
+0.091 to +0.183 ns at U3 for writes (both stacks, `d13/sim/sim_final.md`). D13 is the slowest, because its route
grows by about 6.6 mm: read +0.083 to +0.097 ns, write +0.146 to +0.183 ns. (The 13-resistor run gave +0.032 to
+0.088 and +0.097 to +0.177 ns.) At 133 MHz CL3 the window is 4.6 ns. Taking out 0.255 ns of
bit spread and 0.30 ns of FF setup+hold leaves 4.05 ns for the FPGA's own variation. **Direct next-edge capture fails
with or without the resistor**: data arrives at 9.88 ns against a 7.5 ns tCK. Any controller therefore needs a
phase-shifted MMCM capture clock or IDELAY. No SDRAM controller exists in the repo yet, so Vivado must confirm the
margin once one is written. The resistor costs less than 0.1 ns of it.

**What else needs no resistor.** SDRAM-CLK, address and control. Writes at R=0 and the max corner peak at the SDRAM pin
at +0.22 V of overshoot (address) and -0.59 V of undershoot (SDRAM-CLK). That is inside the part's -1.0/4.6 V limit,
and there is no ringback (`premise_check.md` §4). A resistor on SDRAM-CLK could push its
0.63-0.92 ns edge past 1 ns, where the datasheet adds a tAC/tOH penalty.

## 4. Part

| Item | Value |
|---|---|
| MPN | Yageo **RC0201FR-0722RL**: 22 ohm, +-1 %, 1/20 W, +-200 ppm/C, 0201 |
| Footprint | **R0201** from `zulu_a7.PcbLib`, unchanged: two 0.30 x 0.30 mm pads at 0.60 mm centres. Pad 1 is at local x = -0.30. |
| Symbol | Cloned from R24 (sheet 4): R-US_SMALLR0201 from rcl.IntLib |
| BOM | **+1 line**, quantity 16 (R119-R134). The family already has 14 RC0201FR lines. |
| Dissipation | At most about 10 mW per part (11.5 pF x 3.465 V^2 / 2 per edge at 143 MHz), 20 % of the rating |
| Fallback | RC0201FR-0733RL (33 ohm), already the R24/R25 line. Same geometry. Not recommended (decision 1). |

Arrays were rejected. U3's DQ pins are interleaved with VDDQ/VSSQ at uneven 0.8/1.6 mm spacing. The 0.8 mm-pitch CTS
742C parts need 3.0-3.1 mm of depth, but only 1.47 mm (south) and 0.47 mm (north) is available. The 0.4/0.5 mm-pitch
0201 arrays leave 0.20-0.25 mm between elements, under the 0.28 mm a return track needs. Source: `parts.md`,
`design_arrays.json` arrays_eval.

## 5. Schematic change

Sheet `zulu_a7_3.SchDoc` (U3). The full recipe is in `si/series_r/schematic_plan.md`. This plan uses that recipe at
its full size: **16 resistors**.

- **Nets.** Today each Dn is one net, joined by global labels on sheet 3 (at U3) and sheet 5 (at U1). For all 16
  nets D0-D15:
  - change the U3-side label text on sheet 3 from `Dn` to `SDRAM-Dn` (U3 pins 2, 4, 5, 7, 8, 10, 11, 13, 42, 44, 45,
    47, 48, 50, 51 and 53);
  - leave sheet 5, the XDC, the HDL and the IBIS names unchanged on `Dn`.
  The schematic does not show where the part sits on the board, so R133 and R134 (at the U1 end on the PCB) are drawn
  the same way as the others.
- **Parts.** R119-R134 go in the empty window x 45..540, y 340..698 on sheet 3, using the two-column layout from
  schematic_plan.md §4. Each row is: label SDRAM-Dn — pin 1, R, pin 2 — label Dn (pin 1 is the template R24's
  left pin). Pin 1 must be SDRAM-Dn to match pad 1 in §6.1. (Corrected 2026-11-13: the old row text and
  `schematic_plan.md` both put Dn on pin 1, which would have made the ECO net every R's pads opposite to the copper.)
- **Part parameters.** Comment=22, MANF=Yageo, MANF#=RC0201FR-0722RL, SPEC "thick film +-1%, 1/20W, 0201", footprint
  R0201, and a hidden NOTE: "series R on the SDRAM data net; position is SI-critical, see docs/dq_series_resistors.md".
- **Method.** An append-only Python script modelled on `Zulu_Altrium/tools/stitch_caps.py`, which added C155-C159
  to this sheet. It writes new records, changes only 16 label texts, and updates the header Weight.

Traps (all from schematic_plan.md §6 and project memory):

1. Every record must end in NUL.
2. The header `Weight` must equal the record count, or appended records vanish silently.
3. Append only, never insert, because OwnerIndex is positional.
4. Give each clone fresh UniqueIDs, and make each pin's PinUniqueId equal that pin's UniqueID.
5. Drop the EAGLE-import HiddenNetName pin parameters from clones.
6. Do not touch any of U3's own records.
7. Close the sheet in Altium before writing, and back it up to `Rev_2/backups/` first: a malformed SchDoc makes
   Altium hang.
8. Altium re-keys parameter IDs and renumbers fonts on save, so verify by connectivity and text, not by bytes.
9. Re-run the label-name collision check right before applying, because labels are global.

## 6. Layout change

![Free area around U3 (phase-1 extract)](../si/series_r/region_map.png)

![Implementation plan: 16 R, the 13-R plan plus R132-R134, the gnd47 unlock and the U1 designator move](../si/series_r/dq_series_r_plan.png)

The plan is a hybrid of several designs, combined by judges and then hardened by adversarial DFM reviews.
- South row: the "arrays" plan's discrete solution (`../si/series_r/design_arrays.png`).
- D8, D11 and D12: the Top plan (`../si/series_r/design_top.png`).
- D9: added by the judge.
- The DFM fixes F1 and F2 of the 12-resistor review are folded in below.
- D10: the "relocate" design from the D10 pass (`../si/series_r/d10/relocate/`). It adds R129 and moves R130 (not
  yet on the board) 0.20 mm east and 0.02 mm north. Chosen over "stagger" and "d10_elsewhere" by the D10 judge.
- D13-D15: the D13-D15 pass (`../si/series_r/d13/`) searched three families: the U3 end (`u3_end/`), the inner run
  (`inner_run/`) and the U1 end (`u1_end/`). `combine/rank.py` chose exhaustively among all proven sites (D13 2,
  D14 939, D15 1083), ranked by coverage, then new vias, then copper changes, then margins. D13 fits in one place
  only: R132 on the Top, next to R131, which needs the "gnd47" unlock (U2-47 GND re-tied by its own microvia). R133
  and R134 are U1-end Bottom sites with 2 new vias each, the minimum of any family.
- The D13-D15 adversarial review's fix F1 (U1 designator moved, decision 13) is folded in.

The 12-resistor FIXED variant was proven with `dfm_check.py --variant FIXED`. The 13-resistor plan was re-proven with
`si/series_r/d10/fold/check.py` (a copy of dfm_check.py that reads the plan JSON literally, plus an Altium-style
ComponentClearance section) and with the unchanged `judge_check.py` (`d10/fold/judge_fold.py`). The 16-resistor plan
was proven the same way, with a byte copy of that checker (`d13/fold/check.py`, md5 `b2520429`, run through
`d13/fold/run_check.py`, which only applies the plan's designator move to the extract's texts first) and with the
unchanged `judge_check.py` (`d13/fold/judge_fixed.py`):
- 0 apply errors; 0 clearance, hole, width and mask violations; 0 acid traps;
- 16/16 bits split cleanly into SDRAM-Dn and Dn, 2 islands each, no bypass;
- 0 new shorts, and no net among all 181 gains an island; 0 dangling ends;
- both pours stay one live island each, with 0 objects off the main island and 0 necks;
- silk: U1's moved designator is 0.452 mm from R132-1's opening (rule 0.254);
- the log is line-for-line identical to `d13/combine/check_final.log` except section 9 (silk), which now passes;
- the judge's result is identical to `d13/combine/judge_final.json`: 0 errors, 0 violations, 37 nets with good
  connectivity.
Independent adversarial reviews share no code with those checkers: `d10/verify/dfm_adversary.py` (13-resistor plan,
0 hard violations) and `d13/verify/adv13.py` (16-resistor plan: 1 hard finding, the U1 designator, now fixed; the
13-resistor plan re-run gives 0 hard findings, and every 13-resistor advisory is unchanged).

### 6.1 Placement (all 22 ohm R0201; pad 1 = SDRAM-Dn = U3 side, pad 2 = Dn = U1 side; no existing part moves; designators hidden)

| Ref | Net | Side | Centre x, y (mm) | Rot | Pad 1 (SDRAM-Dn) | Pad 2 (Dn) | Copper U3 pin -> R | Ball at 22 ohm, max |
|---|---|---|---|---|---|---|---|---|
| R119 | D0 | Bottom | 38.2499, 5.17015 | 0 | 37.9499, 5.17015 | 38.5499, 5.17015 | 1.00 mm, 0 vias | -0.206 V, 0.5 % |
| R120 | D1 | Bottom | 36.6500, 5.17015 | 0 | 36.3500, 5.17015 | 36.9500, 5.17015 | 1.00 mm, 0 vias | -0.091 V, 0 % |
| R121 | D2 | Bottom | 35.5501, 4.91015 | 270 | 35.5501, 5.21015 | 35.5501, 4.61015 | 0.96 mm, 0 vias | -0.140 V, 0 % |
| R122 | D3 | Bottom | 34.2499, 5.17015 | 0 | 33.9499, 5.17015 | 34.5499, 5.17015 | 1.00 mm, 0 vias | -0.200 V, 0 % |
| R123 | D4 | Bottom | 32.8501, 5.17015 | 180 | 33.1501, 5.17015 | 32.5501, 5.17015 | 1.00 mm, 0 vias | -0.137 V, 0 % |
| R124 | D5 | Bottom | 31.5501, 4.91015 | 270 | 31.5501, 5.21015 | 31.5501, 4.61015 | 0.96 mm, 0 vias | -0.218 V, 0.8 % |
| R125 | D6 | Bottom | 30.7500, 4.91015 | 270 | 30.7500, 5.21015 | 30.7500, 4.61015 | 0.96 mm, 0 vias | -0.186 V, 0 % |
| R126 | D7 | Bottom | 29.4501, 5.21015 | 0 | 29.1501, 5.21015 | 29.7501, 5.21015 | 0.96 mm, 0 vias | -0.181 V, 0 % |
| R127 | D8 | Top | 39.2000, 13.6000 | 0 | 38.9000, 13.6000 | 39.5000, 13.6000 | 11.13 mm, 2 vias | -0.185 V, 0 % |
| R128 | D9 | Bottom | 42.0500, 12.9500 | 0 | 41.7500, 12.9500 | 42.3500, 12.9500 | 13.87 mm, 3 vias | -0.160 V, 0 % |
| **R129** | **D10** | Top | **39.2100, 14.3600** | 0 | **38.9100, 14.3600** | **39.5100, 14.3600** | 8.65 mm, 2 vias | -0.272 V, 1.2 % |
| R130 | D11 | Top | **39.4000, 14.9200** | 0 | **39.1000, 14.9200** | **39.7000, 14.9200** | 7.15 mm, 2 vias | -0.120 V, 0 % |
| R131 | D12 | Top | 39.2000, 15.8000 | 0 | 38.9000, 15.8000 | 39.5000, 15.8000 | 6.21 mm, 4 vias | -0.157 V, 0 % |
| *R132* | *D13* | Top | *38.7500, 16.3035* | 180 | *39.0500, 16.3035* | *38.4500, 16.3035* | 5.53 mm, 1 via | -0.166 V, 0 % |
| *R133* | *D14* | Bottom | *45.6000, 17.1500* | 0 | *45.3000, 17.1500* | *45.9000, 17.1500* | 10.33 mm, 3 vias | -0.072 V, 0 % |
| *R134* | *D15* | Bottom | *46.8000, 16.8000* | 0 | *46.5000, 16.8000* | *47.1000, 16.8000* | 9.05 mm, 3 vias | -0.039 V, 0 % |

Notes on the table:
- *Italic* = added by the D13-D15 pass. R132 is 0.0035 mm north of the 0.05 grid (the mask-web nudge, decision 14).
  R133 and R134 sit at the U1 end, so their "U3 pin -> R" copper is most of the route; the U1 side is a short
  Bottom track into the existing through via next to U1.
- **Bold** = changed by the D10 pass. R129 is new. R130 was at (39.20, 14.90) in the 12-resistor plan.
- R119, R120, R122 and R123 sit 0.04 mm south of the judge's positions (fix F2). The D10 pass simulated that
  geometry for the first time; D0 and D12 (fix F1) stayed within 0.02 V of the unshifted run.
- Rotations follow the board's own Bottom-side R0201/C0201 parts. The DFM review checked this against 34 resistors
  and 40 capacitors. The adversarial D13 review re-checked pad 1 orientation on all 16 parts, and the U3 pin of
  each re-netted pad against the TSOP-54 DQ map.
- Ball values are from `d13/sim/sim_final.md` §2a (fab stack, max corner, 0201 parasitic model); D0-D12 are
  bit-identical to the 13-resistor run. "Copper U3 pin -> R" is from `d13/fold/check_fixed.log` §1.

### 6.2 Copper per net

Counts are from `dq_series_r_plan.json`. Coordinates in mm.

| Net | Removed | Added | Existing copper moved to SDRAM-Dn |
|---|---|---|---|
| D0-D7 (each) | The Bottom pad-to-first-via stub (0.125 mm). | A Bottom 0.125 mm feed straight off the pad toe to R pad 1. Then a Bottom 0.10 mm three-segment return from R pad 2, back through the 0.35 mm gap between two U3 pads, to the **existing** first through via. L3/L4/Top are untouched. | none |
| D8 | Top (38.5,13.6)-(39.6455,13.6) | Top 0.0762 mm (38.5,13.6)-(38.9,13.6) and (39.5,13.6)-(39.6455,13.6). No vias. Keep 39.6455 exactly: it is +0.0003 mm from UDQM. | U3-42, Bottom stub, through vias (29.25,16.65) and (38.5,13.6), and the L4 run: 3 tracks, 2 vias |
| D9 | L4 (41.75,13.275)-(42.425,12.60) | L4 0.125 mm (41.75,13.275)-(41.75,12.95) and (42.35,12.95)-(42.425,12.60). Two stacked columns, L4>L5 + L5>Bottom 0.30/0.15, in R128-1 and R128-2 (via-in-pad). | U3-44, Bottom stub, through via (30.825,16.65), 7 L4 segments: 8 tracks, 1 via |
| D10 | Top (38.5,14.5)-(39.9785,14.5) | Top 0.0762 mm: (38.5,14.5)-(38.77,14.5)-(38.91,14.36) on the U3 side and (39.51,14.36)-(39.65,14.5)-(39.9785,14.5) on the U1 side, 45-degree jogs ending under the pads. The last piece lies on the original centreline. No vias. The vertical (39.9785,12.21)-(39.9785,14.5) and the rest of the run to U1-K2 are kept. | U3-45, Bottom stub (31.5501,17.53)-(31.65,16.65), through vias (31.65,16.65) and (38.5,14.5), and the L3 run: 3 tracks, 2 vias |
| D11 | Top (38.5,14.95)-(40.145,14.95) | Top 0.0762 mm: (38.5,14.95)-(39.1,14.95)-(39.1,14.92) on the U3 side and (39.7,14.92)-(39.7,14.95)-(40.145,14.95) on the U1 side. No vias. (The 12-resistor plan ended these at x 38.9 and 39.5 for R130 at x 39.2.) | U3-47, stub, vias (33.25,16.65) and (38.5,14.95), L3 run: 3 tracks, 2 vias |
| D12 | L4 (37.25,16.025)-(40.9,15.1) | U3 side: L4 (37.25,16.025)-(38.854,15.6185)-(38.9,15.8), then a column in R131-1 at (38.9,15.8) made of Top>L2 0.30/0.15, L2>L3 0.30/0.15 and L3>L4 0.27/0.15 (buried). U1 side, **fix F1**: the same column centred in R131-2 at (39.49,15.81), plus L4 (39.49,15.81)-(40.9,15.1). | U3-48, stub, via (34.025,16.65), 2 L4 segments: 3 tracks, 1 via |
| D13 | L3 (35.625,16.65)-(36.275,16.025) and (36.275,16.025)-(38.65,15.3) | U3 side: Top 0.0762 mm (35.625,16.65)-(36.345,17.64)-(38.185,17.62)-(38.505,17.28)-(39.05,16.3035) into R132-1. It runs about 1 mm under U2's body corner, between USB5V0 and U2-48 (decision 15). U1 side: a column in R132-2 at (38.45,16.3035) made of Top>L2 + L2>L3 microvias 0.30/0.15, then L3 0.125 mm (38.45,16.3035)-(38.11,16.46)-(37.77,16.76)-(37.07,16.88)-(36.89,16.64)-(36.8471,15.8504)-(38.65,15.3), re-joining the kept L3 route to U1-H1. The net grows by about 6.6 mm. | U3-50, Bottom stub (35.5501,17.53)-(35.625,16.65), through via (35.625,16.65): 1 track, 1 via |
| D14 | L4 (38.0,17.25)-(47.9,17.15) | L4 0.125 mm (38.0,17.25)-(45.3,17.15) into a column in R133-1 at (45.3,17.15): L4>L5 + L5>Bottom microvias 0.30/0.15. U1 side: Bottom 0.10 mm (45.9,17.15)-(47.9,17.15) into the **existing** through via at (47.9,17.15). | U3-51, Bottom stub, through via (36.125,16.65), L4 (36.125,16.65)-(36.725,17.25)-(38.0,17.25): 3 tracks, 1 via |
| D15 | L4 (38.35,16.725)-(48.9,16.8) | L4 0.125 mm (38.35,16.725)-(46.5,16.8) into a column in R134-1 at (46.5,16.8): L4>L5 + L5>Bottom microvias 0.30/0.15. U1 side: Bottom 0.10 mm (47.1,16.8)-(48.9,16.8) into the **existing** through via at (48.9,16.8). | U3-53, Bottom stub (37.9499,17.53)-(38.35,16.725), through via (38.35,16.725): 1 track, 1 via |

Other nets the south row needs re-laid. This is decoupling and JTAG rework, and every net is proven single-island.
The D10 change re-lays no other net: D8, UDQM, CKE and the UART_FT vias beside R129/R130 are untouched. The D13-D15
change re-lays one other net, GND at U2-47 (last row below).

| Net | Change |
|---|---|
| VCC3V3 (U3-9 VDDQ) | The toe track to C38 is removed. A new heel track (32.35,6.17)-(32.35,7.0) runs at 0.2 mm to a new Bottom>L5 microvia at (32.35,7.0). C138-2 gets its own Bottom>L5 microvia at (28.80,4.40), and its old 0.3/0.2 mm feed at y 4.85 is removed. |
| GND (U3-6) | The 0.41 mm heel run becomes 0.25 mm (34.75,6.17)-(34.75,8.6)-(34.475,9.0). |
| GND (U3-12) | The toe run is re-routed (30.05,6.0)-(30.05,4.9)-(29.54,4.9)-(29.54,4.3) at 0.10/0.115 mm. |
| FT-VCORE | The 0.5 mm trunk at y 4.55 becomes 0.16 mm at y 4.28, with 0.2 mm cap stubs and a 0.15 mm finger at x 30.35. The Width_PWR_RAILS minimum is 0.15, so this has +0.01 mm of margin. |
| TMS | The L3>L4>L5>Bottom stack at (32.15,8.125) is removed (3 vias). A new L4>L5 + L5>Bottom stack is added at (33.45,8.15), with a new L4 stub and Bottom re-run. The crossing moves from gap 9-10 to gap 7-8. |
| TDO | One jog: (28.75,5.55)-(28.75,4.95)-(29.15,4.8). |
| GND (U2-47, "gnd47" unlock for R132) | The Top run (38.175,17.125)-(38.175,18.2)-(38.35,18.4) (0.21 / 0.28 mm) is removed. A Top 0.18 mm stub (38.175,17.125)-(38.22,17.16) goes to a new Top>L2 microvia 0.30/0.15 at (38.22,17.16), a shorter ground path. The GND through via at (38.35,18.4) stays, because it still serves U3-54. |

**Totals** (13-resistor plan in brackets).
- Tracks: -44 / +82 (-38 / +67). Vias: -3 / +21 (-3 / +14). The D13-D15 pass adds 7 microvias (GND 1, D13 2, D14 2,
  D15 2) and no through or buried via.
- Renames, done as remove-then-re-add so `tools/emit_copper.py` can apply them: 25 tracks and 11 vias (20 and 8).
- Pads: 16 U3 pads re-netted by the ECO, and 32 new pads (13 and 26).
- In emit_copper terms the plan file is 69 tracks removed / 107 added and 14 vias removed / 32 added (58 / 87 and
  11 / 22).
- New vias typed as microvias: 21 (19 microvia 0.30/0.15 + 2 buried 0.27/0.15) (14: 12 + 2).
- Via-in-pad sites: 7 (R128-1, R128-2, R131-1, R131-2, R132-2, R133-1, R134-1) (4). The plan lists them under
  `vippo`.
- Silk: U1's designator moves (`designator_moves`, decision 13).

### 6.3 Parts moved

No existing part moves. Designators R119-R134 are hidden, as on the board's other Bottom parts. One existing text
moves: U1's visible designator, from (39.2168, 16.6251) to (39.70, 16.55), rot 0 (decision 13).

### 6.4 DFM verdict: PASS WITH FIXES (fixes folded in)

Source: `si/series_r/dfm_check.py`, written independently of the judge's checker. Logs: `dfm_check.log` and
`dfm_check_fixed.log`. The D10 delta has its own adversarial review: verdict **PASS, no geometry fix**
(`d10/verify/adversary_final.log`; it re-ran `dfm_check.py --variant FIXED` on a copy, byte-identical output). The
D13-D15 delta has its own too: verdict **PASS WITH FIXES** (`d13/verify/adv13_final.log`); its one required fix is
folded in.

| Item | Status in this plan |
|---|---|
| D13-D15: R132-R134 added, gnd47 unlock | **Folded in 2026-11-13.** Copper, hole-to-hole, width, mask, connectivity, split and pour checks all pass. Tightest new copper: L3 +0.0032 (D13 re-join to SD-DAT2), L3 +0.0036 (D13 L3 to the SDRAM-D15 via), L3/L4 +0.0040 (SDRAM-D13 via to a VCC3V3 via), Top +0.0044 (SDRAM-D13 to U2-48), L4 +0.0156 (SDRAM-D15 to the GND via at (41.4,16.4)), Bottom +0.025 (R134-1 to VCC1V0). Narrowest new mask web: R131-1 to R132-1, 0.1035. Mask cover under 0.05 mm: U2-48 to the SDRAM-D13 Top track 0.044 (plan estimate; 0.025 on the released GTS) (decision 15), R132-2 to the SDRAM-D15 via 0.047. The gnd47 microvia is 0.279 mm hole to hole from the SDRAM-D15 via. |
| D13 fix F1: U1 designator | **Folded in.** Moved to (39.70, 16.55) (decision 13). Before the fix it was 0.045 mm from R132-1's opening, which fails Silk To Solder Mask (0.254) in the batch DRC. |
| CHAN7 / SDRAM-D14 stacks | Advisory. The CHAN7 Top>L2>L3 stack at (45.4,17.2) and the new SDRAM-D14 L4>L5>Bottom stack at (45.3,17.15) overlap in projection (hole edges -0.038 mm). They share no layer, so this is not an Altium hole-to-hole hit; the L3 and L4 capture pads couple about 15 fF into the XADC input across the core. The board already has 6 such different-net pairs, two of them fully coaxial (`tools/fab_facts.json` different_net_projected_hole_overlaps; corrected 2026-11-13). If PCBWay objects, R133 needs a pose that clears (45.4,17.2) by at least 0.15 mm; none is proven yet. |
| Tombstoning, R132-R134 | Advisory. Each has a via in one pad only. Filled and capped (VIPPO), the solder areas are equal; unfilled, the asymmetry is 19.6 %. The heat-path imbalance is large (79-84 % by a crude measure), but the columns go to isolated signal copper, not to a plane. |
| D10: R129 added, R130 re-sited | **Folded in 2026-11-13.** Tightest new copper: R129 pads to the UDQM Top track +0.032, R130 pads to the UART_FT_CTS# microvia +0.035. R129-R130 mask web 0.16, pad gap 0.26 (decision 12). Tombstoning: R129 and R130 are symmetric (two 0.0762 tracks per pad, no via-in-pad). No new via, no pour change, no new tracks over a void. |
| F1: D12 line-side column moved from (39.3,15.9) to (39.49,15.81) | **Folded in.** The hole now sits fully inside R131-2. Pad-area asymmetry falls from 15.3 % to 1.6 %, and the Top jog over a new L2 void is gone. The L3 margins are +0.0052 to the UART_FT_TXD via and +0.0089 to CTS#. Centring the column at (39.5,15.8) fails: 0.0947 mm against 0.10. |
| F2: R119, R120, R122 and R123 moved 0.04 mm south | **Folded in.** Copper to the other-net U3 toes goes from 0.21 to 0.25 mm, and the mask web from 0.11 to 0.15 mm. R119-1 to CHAN18 is +0.0093. R126 cannot move: at -0.04 mm it is 0.070 mm from the TDO via and the U3-12 GND re-run. |
| Via types | **Required.** All 19 new 0.30/0.15 vias must be typed as microvias, and the two 0.27/0.15 L3>L4 vias as buried. Otherwise HoleSize (min 0.20) fails; of the 7 D13-D15 microvias, the 4 that reach Top or Bottom would fail untyped. |
| Pours | **Required.** Re-pour L2-GND and L5-VCC3V3, because Modified Polygon is in the batch DRC. This leaves 4 L2 slivers of about 0.001-0.008 mm² at D12, 2 L5 slivers of about 0.001-0.002 mm² at D9, and 2 new L2 slivers of about 0.0004 mm² at (38.22,16.39) and (38.62,16.49) beside the R132 column and the gnd47 microvia. Accept them or enable neck removal. The D9 L5 openings merge with the AIN16_N antipad (web -0.057); the D12 L2 openings merge with each other. The D13 L3 re-join runs 0.19 mm over its own new L2 void, and the SDRAM-D14/D15 L4 runs end over their own L5 voids (0.24 mm). |
| VIPPO | **Required.** Add R128-1, R128-2, R131-1, R131-2, R132-2, R133-1 and R134-1 (7 sites) to the fab notes' via-in-pad list, filled and capped. Filling also makes R132-R134's solder areas symmetric. |
| Net class | **Required.** Add SDRAM-D0..D15 (16 nets) to SDRAM_DATA. Otherwise Width_SDRAM and Clearance_SDRAM_INNER silently stop covering them and nothing fails. |
| Designators | **Required.** Hide all 16. Move U1's (decision 13). |
| Courtyard / ComponentClearance | Advisory. See decision 9 (south row vs U3), decision 12 (R129-R130) and decision 14 (R131-R132, R132-U2); ask PCBWay. |
| U3-12 ground path +0.41 mm | Advisory. See decision 10. |
| Margins under 0.011 mm | D8 Top +0.0003 to UDQM (inherited). D10 Top (39.65-39.9785, y 14.5) +0.0003 to the D11 vertical at x 40.145 (inherited). The x 38.5 via column (UDQM / SDRAM-D10 / SDRAM-D11) exactly 0.100 against Clearance_SDRAM_INNER on L3/L4 (+0.000, inherited). SDRAM-D10's renamed L3 run +0.0011 to the UART_FT_RXD via and +0.0022 to N$LD0G (inherited). D9 L4 +0.0025 to the DONE via. TMS hole-to-hole 0.25 (+0.010). Mask sliver +0.010 at U3-5/R121-1. Altium rounds to 2.54 um, so its DRC is the judge. |

## 7. Simulation of the placed resistors

Three runs, same physics.
- **12-resistor run:** `si/series_r/bus_sim_placed.py`, a copy of `si/spice/bus_sim.py` with a PLACED mode. 356
  cases, 0 errors. Runs at R=0 and with the resistor at the pin reproduce `si/spice/wave` with 0 V difference.
  Results: `sim_placed.json` and `sim_placed.md`. It also holds the 15/33 ohm and ideal-R comparisons below.
- **13-resistor run:** `si/series_r/d10/sim/bus_sim_final.py`, the same simulator with a plan-JSON reader and no
  physics change, on `dq_series_r_plan_13.json` md5 `f2949630`. 190 cases, 0 errors. Results: `d10/sim/`.
- **16-resistor run (this plan):** `si/series_r/d13/sim/bus_sim_final.py`, a byte copy of the 13-resistor simulator,
  on the combined plan `d13/final_plan.json` (md5 `6bd34bd7`), whose copper and parts are identical to
  `dq_series_r_plan.json` (the fold adds only the designator move and the VIPPO list). 306 cases: all 16 nets x 2
  stacks x 2 corners x read/write at 22 ohm, the no-R base runs, and a 15/33 ohm sweep on the PcbDoc stack. 0
  errors; every run reached t_end and was connected. Two cases reproduce `d10/sim` sample by sample (0 V), and all
  64 D0-D12 runs are bit-identical to the 13-resistor run, as expected for a per-net model without coupling.
  Results: `d13/sim/sim_final.json` (md5 `e35f3339`) and `sim_final.md`. It is also the first whole-bus run on the
  PcbDoc stack (the 13-resistor run covered only 6 nets there).
- In all of them, each net with a resistor is split into SDRAM-Dn and Dn, both built from the exact planned copper.
  The resistor model is 22 ohm with 0.5 nH, 0.05 pF across the part and 0.08 pF from each pad to ground.

Reads at the U1 ball, as a share of the DS181 Table 4 budget at UI 7.5 ns, 16-resistor run. Fab stack: L3/L4 43.4
ohm; PcbDoc stack: 49.1 ohm. "No R" is today's copper at the max corner; "off table" means the peak lies beyond the
table's last row. *Italic* = added by the D13-D15 pass.

| Net | R | Fab, no R, max | Fab, max: ball (Vmin) / die | Fab, typ: ball / die | PcbDoc, no R, max | PcbDoc, max: ball (Vmin) / die | PcbDoc, typ: ball / die |
|---|---|---|---|---|---|---|---|
| D0 | R119 | 33760 % | 0.5 % (-0.206 V) / 0.0 % | 0.0 % / 0.0 % | 73534 % | 1.3 % (-0.244 V) / 0.0 % | 0.0 % / 0.0 % |
| D1 | R120 | 15.0 % | 0.0 % (-0.091 V) / 0.0 % | 0.0 % / 0.0 % | 34.7 % | 0.0 % (-0.091 V) / 0.0 % | 0.0 % / 0.0 % |
| D2 | R121 | 17296 % | 0.0 % (-0.140 V) / 0.0 % | 0.0 % / 0.0 % | 44732 % | 0.0 % (-0.142 V) / 0.0 % | 0.0 % / 0.0 % |
| D3 | R122 | off table | 0.0 % (-0.200 V) / 0.0 % | 0.0 % / 0.0 % | off table | 1.0 % (-0.218 V) / 0.0 % | 0.0 % / 0.0 % |
| D4 | R123 | off table | 0.0 % (-0.137 V) / 0.0 % | 0.0 % / 0.0 % | off table | 0.0 % (-0.166 V) / 0.0 % | 0.0 % / 0.0 % |
| D5 | R124 | 65513 % | 0.8 % (-0.218 V) / 0.0 % | 0.0 % / 0.0 % | off table | 0.0 % (-0.191 V) / 0.0 % | 0.0 % / 0.0 % |
| D6 | R125 | 11271 % | 0.0 % (-0.186 V) / 0.0 % | 0.0 % / 0.0 % | 8718 % | 0.2 % (-0.203 V) / 0.0 % | 0.0 % / 0.0 % |
| D7 | R126 | 338.9 % | 0.0 % (-0.181 V) / 0.0 % | 0.0 % / 0.0 % | 1861 % | 0.7 % (-0.211 V) / 0.0 % | 0.0 % / 0.0 % |
| D8 | R127 | 4950 % | 0.0 % (-0.185 V) / 0.0 % | 0.0 % / 0.0 % | 1498 % | 1.4 % (-0.286 V) / 0.0 % | 0.9 % / 0.0 % |
| D9 | R128 | 7618 % | 0.0 % (-0.160 V) / 0.0 % | 0.0 % / 0.0 % | off table | 0.0 % (-0.168 V) / 0.0 % | 0.0 % / 0.0 % |
| D10 | R129 | 3059 % | 1.2 % (-0.272 V) / 0.0 % | 0.6 % / 0.0 % | 12844 % | 1.3 % (-0.292 V) / 0.0 % | 0.7 % / 0.0 % |
| D11 | R130 | 499.1 % | 0.0 % (-0.120 V) / 0.0 % | 0.0 % / 0.0 % | 257.0 % | 0.0 % (-0.132 V) / 0.0 % | 0.0 % / 0.0 % |
| D12 | R131 | 155.1 % | 0.0 % (-0.157 V) / 0.0 % | 0.0 % / 0.0 % | 1032 % | 0.0 % (-0.169 V) / 0.0 % | 0.0 % / 0.0 % |
| *D13* | *R132* | 93.8 % | 0.0 % (-0.166 V) / 0.0 % | 0.0 % / 0.0 % | 507.5 % | 0.0 % (-0.175 V) / 0.0 % | 0.0 % / 0.0 % |
| *D14* | *R133* | 62.9 % | 0.0 % (-0.072 V) / 0.0 % | 0.0 % / 0.0 % | 31239 % | 0.0 % (-0.164 V) / 0.0 % | 0.0 % / 0.0 % |
| *D15* | *R134* | 42.9 % | 0.0 % (-0.039 V) / 0.0 % | 0.0 % / 0.0 % | 368.0 % | 0.0 % (-0.052 V) / 0.0 % | 0.0 % / 0.0 % |

Max corner, fab stack, worst over the nets with a resistor:

| Case | Worst ball | Worst die | Ringback (ball) | Read 10-90 % at die | Write pin Vmin / Vmax |
|---|---|---|---|---|---|
| No R | off table (D3), 11 fails | 52.7 % | 0.535 V | 0.31-0.34 ns | -0.385 / 3.642 V |
| 22 ohm at pin, ideal (12 nets) | 17.1 % (D8) | 0 % | 0.139 V | 0.62-0.97 ns | -0.344 / 3.539 V |
| 22 ohm placed, 12 resistors | 0.85 % (D5), -0.218 V | 0 % | 0 | 0.60-0.81 ns | -0.358 / 3.548 V |
| 22 ohm placed, 13 resistors | 1.2 % (D10), -0.272 V | 0 % | 0 | 0.60-0.81 ns | -0.359 / 3.548 V |
| **22 ohm placed, 16 resistors (this plan)** | **1.2 % (D10), -0.272 V** | **0 %** | **0** | **0.56-0.81 ns** | **-0.359 / 3.548 V** |
| 15 ohm placed, 12 resistors | 6.6 % (D3) | 2.1 % | 0 | 0.41-0.65 ns | -0.373 / 3.570 V |
| 33 ohm placed, 12 resistors | 0 % | 0 % | 0.169 V (D7) | 0.72-1.35 ns | -0.307 / 3.520 V |

Whole bus, 16 resistors, all four stack and corner cases:

| Stack / corner | Worst ball | Worst die | Worst ball Vmin | Ringback | Write U3 pin Vmin / Vmax |
|---|---|---|---|---|---|
| fab typ | 0.55 % (D10) | 0 % | -0.213 V (D10) | 0 | -0.249 / 3.326 V |
| fab max | 1.18 % (D10) | 0 % | -0.272 V (D10) | 0 | -0.359 / 3.548 V |
| PcbDoc typ | 0.95 % (D8) | 0 % | -0.240 V (D8) | 0 | -0.267 / 3.338 V |
| PcbDoc max | 1.35 % (D8) | 0 % | -0.292 V (D10) | 0 | -0.367 / 3.554 V |

Value check on the PcbDoc stack, worst over D8, D10, D0, D3, D13 and D14 at both corners (`d13/sim/sim_final.md`
§4):

| R | Worst ball | Worst die | Worst ball Vmin | Ringback (ball) | Die t10-90 | Read delay | Write delay |
|---|---|---|---|---|---|---|---|
| 15 ohm | 8.68 % | 3.19 % | -0.435 V | 0 | 0.41-0.58 ns | +0.024..+0.081 ns | +0.063..+0.142 ns |
| 22 ohm | 1.35 % | 0 % | -0.292 V | 0 | 0.56-0.77 ns | +0.034..+0.097 ns | +0.091..+0.183 ns |
| 33 ohm | 0 % | 0 % | -0.143 V | 0.025 V (D8) | 0.69-0.96 ns | +0.050..+0.126 ns | +0.137..+0.242 ns |

Supporting results:
- With the R at the pin and the same 0201 model, the worst is 2.07 % (D5, max) and 7.71 % (D8, typ). The planned
  positions are at least as good as the pin. R133 and R134 at the U1 end agree with the earlier sweeps: the
  position along the route barely matters at these edges.
- Package sensitivity at 22 ohm: ideal R 1.50 %, light model 0.51 %, parts model 0.85 %.
- No ringback into 0.8-2.0 V at any node, corner, direction or stack.
- Writes pass the SDRAM's -1.0/4.6 V limits on all 16 nets. Worst at the U3 pin is -0.367 / 3.554 V (D3, PcbDoc,
  max); at the U3 die -0.475 / 3.563 V.
- Delay cost against today's copper, all 16 nets, both stacks: reads +0.032..+0.097 ns at the U1 die, writes
  +0.091..+0.183 ns at the U3 die. D13 is the largest (read +0.083..+0.097, write +0.146..+0.183 ns), because its
  route is about 6.6 mm longer. D14: read +0.044..+0.062, write +0.091..+0.141 ns. D15: read +0.048..+0.065, write
  +0.098..+0.147 ns. With the R, the receiving die settles past VIH/VIL about 0.1-0.17 ns later.
- **All 16 nets pass at the ball and at the die on both stacks and both corners.** Without any R, 15 of 16 nets fail
  at the ball on the PcbDoc stack at the max corner (only D1 passes, 34.7 %).

### D13 impedance sweep (2026-11-13, `si/series_r/d13/zsweep/README.md`)

D13 was re-simulated with the L3/L4 impedance swept from 39.1 to 49.1 ohm on PCBWay's geometry (all else unchanged;
controls reproduce the fab 93.8 % and PcbDoc 507.5 % runs exactly). Without a resistor, D13 passes at the max corner
only between about 42.6 and 45.3 ohm (-2 % / +4 % around the nominal 43.4 ohm): 153 % at 39.1, 250 % at 41, 101 % at
42.5, 131 % at 45.5, 112-128 % from 46 to 49 ohm. Its ball peak sits right on Table 4's -0.55 V row, so a few mV decide
the result. A +-10 % impedance tolerance fails over most of its range. With R132, D13 reads 0.0 % at every point and
on the PcbDoc stack, with the ball minimum at -0.17..-0.19 V. This is the basis for keeping R132 (decision 14).

## 8. Implementation sequence

Each step has a gate. Do not start a step until the previous gate passes. Keep a dated backup of the PcbDoc and
SchDoc before steps 1 and 3 (the `History/` zips also restore any save).

| # | Step | Tool | Gate |
|---|---|---|---|
| 0 | Answer the decisions in §2. Commit the pending sheet 3-5 SI-model saves on their own (decision 8). The D10 and D13-D15 passes are already merged into `dq_series_r_plan.json` (md5 `7c2b8ae6`). | — | `git status` is clean for the SchDocs. `md5` of the PcbDoc is still `2a616c1c`; if not, re-extract (`si/series_r/extract.py`), then rebuild in this order: `plan_export.py` (it writes the **12-resistor** plan into `dq_series_r_plan.json`), copy that to `dq_series_r_plan_12.json`, run `d10/relocate/design.py` (it reads `dq_series_r_plan_12.json`), copy `d10/relocate/plan.json` to `dq_series_r_plan_13.json` and over `dq_series_r_plan.json`, then `python d10/fold/check.py --plan ../../dq_series_r_plan.json --tag <name>` and `d10/fold/judge_fold.py`. Then the D13-D15 pass: re-run the three site searches in `d13/u3_end`, `d13/inner_run` and `d13/u1_end` against the 13-resistor plan, then in `d13/combine` run `python rank.py` and `python combine.py` (it rewrites `d13/final_plan.json`), then `d13/fold/fold.py` (it checks the md5 of `final_plan.json`; update it), `python run_check.py --plan plan_fixed.json --tag <name>` and `judge_fixed.py` in `d13/fold`, and copy `d13/fold/plan_fixed.json` over `dq_series_r_plan.json`. Every check must show 0 violations, 0 apply errors and 0 opens, and R129/R130 and R132-R134 must still be found legal; if not, that pass needs a new design run. |
| 1 | Schematic edit (§5) with Altium's sheet closed. | New append-only script modelled on `stitch_caps.py`, writing sheet 3 only | Every record ends in NUL. Weight equals the record count. 0 duplicate UniqueIDs on sheet 3. Reopen in Altium; Compile shows no new ERC messages (read Messages after Validate; ERC is not scriptable). The exported netlist shows 16 new nets SDRAM-Dn, each {U3 pin, Rn-1}, and each Dn as {Rn-2, U1 ball}. |
| 2 | Export the Protel netlist to `Project Outputs for Zulu_a7_no_pmod/Zulu_a7_no_pmod.NET`. | Altium | `python tools/bom_audit.py` passes, including `sdram_ok()`. |
| 3 | ECO: Design > Update PCB. | Altium | Untick the deletion of the **10 PCB-only net classes** and of the **USB differential pair**, plus any room it offers to add or remove. Accept only these changes: add 16 components, add 16 nets, and change the 16 U3 pad nets. Save, close and reopen the PcbDoc, because a pad re-net needs it. A second ECO preview must be empty. |
| 4 | Net class: add SDRAM-D0..D15 to SDRAM_DATA. | Design > Classes, or a small DelphiScript | Re-extract; `net_classes['SDRAM_DATA']` holds 32 nets (16 Dn plus 16 SDRAM-Dn). |
| 5 | Place the 16 parts: absolute X/Y/rotation/side from `dq_series_r_plan.json` `parts`, designator hidden. In the same script, move U1's designator to (39.70, 16.55), rot 0, from `designator_moves` (decision 13). | New generated DelphiScript, loaded as its **own .PrjScr** (a procedure added to an already-compiled .pas is a silent no-op). Set `Cm.Layer := eBottomLayer` for Bottom parts. Do not use relative moves. | Re-extract: all 32 R pads within 2 um of the plan's pad1/pad2 coordinates and on the right nets. Pad 1 must be on SDRAM-Dn on every part, which checks the rotation and flip. R130 must be at (39.40, 14.92), not the 12-resistor position (39.20, 14.90). R132 must be at y 16.3035 (off the 0.05 grid on purpose) with rot 180. U1's designator text is at (39.70, 16.55). |
| 6 | Copper: `python tools/emit_copper.py si/series_r/dq_series_r_plan.json SeriesR`, which writes `tools/FabBCopper_SeriesR.pas/.PrjScr`. Run `PlaceSeriesR` with the PcbDoc focused. Save, close Altium, then run `tools/mark_microvias.py` on the 19 new 0.30/0.15 vias. | Existing tools | The script must report "removed 69 tracks and 14 vias, placed 32 vias and 107 tracks, Missing nets: (none)". It refuses and changes nothing if any removal is missing. Then confirm in Altium that the 19 vias show as uVia and the two 0.27/0.15 L3>L4 vias as buried (21 typed vias in all; the 11 renamed through vias, D10's two and D13-D15's three among them, stay untyped). emit_copper itself does not handle `parts`, `renet_pads`, `net_class_add`, `designator_moves` or `vippo`; those are steps 3-5 and 9. |
| 7 | Re-pour L2-GND and L5-VCC3V3. Rebuild the ratsnest. Run `tools/prune_stubs.py` on a fresh extract. | `tools/NoPmod_Repour.PrjScr`, `tools/FabB_RebuildConnR2.PrjScr` | Altium batch DRC: **0 violations in every rule, including Un-Routed, Short-Circuit, Modified Polygon, HoleSize, Width_SDRAM, the SDRAM clearances and Silk To Solder Mask.** Watch the R131-1 to R132-1 mask web (0.1035 against 0.10) and R132's L3 / Top margins (+0.0032 / +0.0044). prune_stubs finds 0 dead copper. The saved ratsnest has 0 lines. Save the DRC report as `docs/drc_series_r.drc`. |
| 8 | Re-extract the board with `si/series_r/extract.py`. Compare the extract object by object with the plan applied to the old extract (the plan-JSON reader in `d13/fold/check.py` on `dq_series_r_plan.json`): 2 um tolerance, same nets. Then re-run the bus simulation on the fresh copper for all 16 nets, both stacks, both corners and both directions (`d13/sim/bus_sim_final.py` already reads a plan JSON; point it at the fresh extract). | Comparison script (to be written) and bus_sim_final | 0 differences. Every net at 22 ohm, max corner: ball no worse than about 2 % (the planned worst is 1.18 % on the fab stack, D10, and 1.35 % on the PcbDoc stack, D8), die 0 %, no ringback, writes inside -1.0/4.6 V. |
| 9 | Fab outputs: Gerbers, drills, IPC-2581 if used. Update the FAB NOTES via-in-pad list from the plan's `vippo` (+7 sites: R128-1/2, R131-1/2, R132-2, R133-1, R134-1, all filled and capped; R129 and R130 add none; recount the no_pmod total with `tools/fab_facts.py`, since 68 is Fab B's figure). Add the PCBWay EQ questions from decisions 9, 12, 14 and 15 (and the CHAN7 / SDRAM-D14 projected stack overlap if wanted), and confirm the stack. | `tools/package_fabrication_release.py` | The drill file lists the 21 new microvia/buried vias in their span files. The VIPPO count in the notes equals the counted sites. |
| 10 | Assembly: BOM and CPL. | `python tools/generate_jlcpcb_assembly.py --assembler pcbway` | +1 BOM line (RC0201FR-0722RL x16). +16 CPL rows: 11 Bottom (R119-R126, R128, R133, R134) and 5 Top (R127, R129, R130, R131, R132), with rotations matching the PcbDoc. Both assembly drawings show the new refs, and the Top drawing shows U1's designator at its new place. |
| 11 | Refresh the stale copies: `si/altium_si` schematic and PCB, `Zulu_a7_no_pmod_schematic.pdf`, and docs/si_analysis.md (pointer to this file). | — | — |

## 9. Risks and what is not covered

1. **R132 is the one D13 site, and it is tight.** It sits 0.2035 mm (pad box) from R131 with a 0.1035 mm mask web
   and overlapping courtyards, its courtyard overlaps U2's by about 0.05 mm, and its new copper has margins of
   +0.0032 (L3) and +0.0044 (Top) mm. It needs U1's designator moved (decision 13) and the gnd47 GND re-tie. Its
   U3-side Top track runs under U2's body corner with a 0.025 mm mask cover to U2-48 (measured on the released GTS; decisions 14 and 15). If
   PCBWay rejects it, `dq_series_r_plan_15.json` (`d13/fallback15/`, fully proven) keeps R133/R134 and leaves D13
   without a resistor (it then passes on the fab stack at 93.8 % and fails on the PcbDoc stack at 507.5 %).
2. **R129-R130 assembly spacing.** About 0.23 mm body to body at maximum tolerance, courtyards overlapping by
   0.04-0.07 mm, ComponentClearance 0.26 against 0.254 (6 um margin) on Altium's pad-box measure. A GUI DRC with
   that rule on sits at the edge. Five 0201s now sit in a column at x 38.45-39.7 on Top beside U1 (R127, R129-R132),
   with 0.10-0.16 mm mask webs and 45-degree jogs ending under the pads. Fallback: `d10/stagger/plan.json`
   (decision 12).
3. **Not simulated:**
   - coupling between adjacent new R pads, the fold-back returns and the Top column R127/R129-R132 with its parallel
     runs at x 38.5-40.2;
   - coupling of the new SDRAM-D13 Top track under U2 to USB5V0 and the U2 leads;
   - the CHAN7 / SDRAM-D14 projected stack overlap at (45.4,17.2) / (45.3,17.15), about 15 fF into an XADC input;
   - the new L2 openings at D12 and D13 and the L5 openings at D9, D14 and D15 (bus_sim treats the planes as ideal);
   - the IBIS slow corner;
   - the DC and decoupling effect of the south re-work: FT-VCORE trunk 0.5 -> 0.16 mm, U3-9 VDDQ now via L5, U3-12
     +0.41 mm.
4. **Estimated values:**
   - the 0201 parasitics are estimates, but the sensitivity runs show they barely matter;
   - the body proxies are pads plus Mech3/Mech4, because the board has no 3D bodies and the PcbLib has no TSOPII-54;
   - U3's body is assumed centred on its pad field.
5. **Checker vs Altium.** Several margins are under 0.011 mm, including the inherited +0.000 at the x 38.5 via
   column on L3/L4, the two +0.0003 Top corners and R132's new +0.0032 / +0.0036 / +0.0040 / +0.0044. Every margin
   below Altium's 2.54 um resolution is inherited from the 13-resistor plan. The independent checkers are calibrated
   to the board's DRC 0, but Altium's own DRC at gate 7 is what decides, including its 2.54 um rounding after
   remove/re-add.
6. **Net class.** If any SDRAM-Dn is left out of SDRAM_DATA, nothing fails, but Clearance_SDRAM_INNER and
   Width_SDRAM silently stop covering it (gate 4).
7. **Via-in-pad.** Seven sites need VIPPO, filled and capped: R128-1/2, R131-1/2, R132-2, R133-1, R134-1. R132-R134
   each have the via in one pad only; unfilled, their solder areas differ by 19.6 % (tombstoning).
8. **D14 and D15 through vias.** The existing through vias at (47.9,17.15) and (48.9,16.8) now join only Top and
   Bottom: the signal comes up from R133/R134 on the Bottom and leaves on the Top, so it uses the full barrel. The
   simulation models them as connected.
9. **D13 is longer.** Its route grows by about 6.6 mm and its new U3-side path is Top microstrip. Its read delay
   (+0.083..+0.097 ns) is the largest on the bus but well inside the budget in §3.
10. **Read timing.** It cannot be closed without an SDRAM controller. Direct capture already fails without the
   resistor.
11. **Snapshot.** Everything is based on PcbDoc md5 2a616c1c and `dq_series_r_plan.json` md5 7c2b8ae6 (16
   resistors; the 13-resistor plan is `dq_series_r_plan_13.json`, md5 f2949630). Unsaved edits in Altium invalidate
   the plan until gate 0 is re-run. Re-running `plan_export.py` on its own overwrites the plan with the 12-resistor
   one; follow the order in gate 0.

## 10. Files

All under `si/series_r/` unless stated.

| File | Content |
|---|---|
| `dq_series_r_plan.json` / `dq_series_r_plan.png` | The 16-resistor implementation plan in emit_copper format, plus `parts`, `renet_pads`, `net_class_add`, `microvias`, `designator_moves` and `vippo` (byte copy of `d13/fold/plan_fixed.json`, md5 7c2b8ae6); figure (drawn by `d13/fold/draw_plan.py`) |
| `dq_series_r_plan_13.json` / `d13/dq_series_r_plan_13.png` | The 13-resistor plan (md5 f2949630, byte copy of `d10/relocate/plan.json`) and its figure |
| `d13/` | The D13-D15 pass: `u3_end/`, `inner_run/`, `u1_end/` site searches; `combine/` (exhaustive selection, combined plan `final_plan.json` md5 6bd34bd7, checker and judge runs, delta report); `verify/` (adversarial DFM `adv13.py`, U1 designator search `u1_silk.py`); `sim/` (16-resistor whole-bus simulation, `sim_final.md`); `fold/` (fix F1 folded: `fold.py`, `plan_fixed.json`, `check_fixed.log`, `judge_fixed.log`, figure script, the doc's §7 table generator in `doc/`) |
| `dq_series_r_plan_12.json` / `plan_export.py` | The 12-resistor plan (md5 21972745) and its generator. `plan_export.py` writes to `dq_series_r_plan.json`, so see gate 0 before re-running it |
| `d10/` | The D10 pass: `stagger/`, `relocate/`, `d10_elsewhere/` designs; `judge/` (checker copy, judge runs, delta); `verify/` (adversarial DFM); `sim/` (13-resistor bus simulation); `fold/` (re-proof of the folded plan: `check_folded.log`, `judge_fold.log`; figure script). `dq_series_r_plan_12.png` is the old figure. Scripts there other than `relocate/design.py` read `dq_series_r_plan.json` as the 12-resistor base and are records of that run; point them at `dq_series_r_plan_12.json` before re-running |
| `board_extract.json` / `extract.py` / `region_map.png` | PcbDoc extract (md5 2a616c1c), rules, free area |
| `dfm_check.py` / `dfm_check_fixed.log` / `.json` | Independent DFM/DRC proof of the FIXED plan |
| `judge_check.py` / `.log`, `judge_sim_d9*.json` | Judge's checker and the D9 design |
| `design_arrays.*`, `design_top.*`, `design_bottom.*` | The three source designs |
| `sim_placed.md` / `.json`, `bus_sim_placed.py` | Placed-R simulation |
| `premise_check.md`, `timing.*`, `sweep*`, `rout.*`, `clamp_writes.*` | Premise and value study |
| `parts.md`, `parasitic_sim.py` | Part choice and 0201 parasitics |
| `schematic_plan.md`, `schematic_probe.*` | Schematic recipe and measured label map |
