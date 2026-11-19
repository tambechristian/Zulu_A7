# Handoff: Feather-style flat LiPo JST (X4) between X2 pins 30 and 31

Date: 2026-11-16, updated 2026-11-19. Board: `Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc` (Rev_2, 2.4 x 1.0 in, 6-layer HDI).

**Status 2026-11-19: SOLVED, applied in Altium with no PCB notch (FT2232HQ, QFN-64), accepted by the user, and the
release data (Gerbers, drills with G85 slots, fab notes, assembly package, fabrication ZIP) regenerated from the saved
board.** Read "Final solution" first. The edge-tab section further down is superseded and the FT2232HL is no longer used.

## Goal
- Fit **JST S2B-PH-SM4-TB** (SMD, side entry, lying flat, cable plugs in parallel to the board) for the LiPo (nets VBATT pin 1, GND pin 2).
- This is the same connector and orientation as Adafruit Feather boards. The board does **not** use the Feather form factor.
- Location: on the bottom edge, in the slot between X2 pins 30 and 31. The opening faces off-board.
- Part: LCSC C295747 (in stock).

## Why it does not fit today
- **S2B-PH-SM4-TB land** (datasheet frame, origin at the body centre):
  - Signal pads 1.0 x 3.5 at (±1.0, -2.85).
  - Mounting pads 1.5 x 3.4 at (±3.35, +2.9).
  - Body x ±3.95, y -3.2 .. +4.4.
  - It needs about **9.5 mm of depth** from the board edge.
- **Free depth at the 30/31 slot:** only about **6.9 mm**. U2 (FT2232HL, **LQFP-64**) has its south pin row starting at y = 7.125 mm.
- **The column at that x is over-full:** X1 4.4 + U2 12.95 + S2B 9.7 = **about 27 mm**, on a 25.4 mm board.
- **Today's board instead has** the B2B-PH-SM4-TB, a top-entry upright SMD part. The earlier PCBWay HDI order uses it too.
  - It also has a body overlap with U2 pins 17-29.
  - `tools/body_check.py` finds that overlap. DRC does not check bodies.

## Final solution (2026-11-19): notchless, U2 = FT2232HQ (QFN-64)

The outline is the original flat 60.96 x 25.40 mm rectangle (no tab, no notch). U2 is the **FT2232HQ-QFN64**, the
same device as the Cmod. Its QFN body needs less board depth than the LQFP-64, so the side-entry S2B-PH-SM4-TB
fits in the column between X2 pins 30 and 31.

Placement (mm):
- U2 FT2232HQ-QFN64 at (30.50, 14.55). X4 S2B-PH-SM4-TB at (31.39, 4.90), cable exiting south (the footprint's
  mirror was fixed in `zulu_a7.PcbLib`). U10 moved by (+2.50, +1.60).
- `tools/body_check.py --refs U2,X4,U10,U3` (with `tools/route/x4_feasibility/qfn/comps_final.json`): 0 findings
  at the 0.10 mm gap.

Copper and vias:
- USB pair: P = N = 12.1863 mm, Top only, 0.15/0.15 mm, no vias.
- USB5V0 is 0.2 mm wide (it was 0.4-1.0 mm). Rule: 0.2 mm minimum.
- SDRAM-D8 and SDRAM-D9 are 0.125 mm on L4 and Bottom. Two D8 segments on L4 are 0.12 mm, near (30.6-30.85, 15.6),
  to keep 0.10 mm to UART_FT_RTS# (the SDRAM class rule). Do not narrow them below 0.12 mm: Altium stores
  coordinates in 1/10000 mil, so 0.10 mm can round just under the 0.10 mm rule.
- 2 GND through vias lie in SMD pads: U2-EP at (32.35, 16.575) and X4-2 at (32.475, 9.025). The user accepted them.
  The fab notes ask PCBWay to resin-fill and cap them (VIPPO, IPC-4761 type VII), and the release checks
  (`fab_notes.through_in_pad_problem`) block on any other through via in an SMD pad.
- 1,982 vias by span: 322 through, 400 buried L3-L4, and 1,260 microvias (Top-L2 336, L2-L3 302, L4-L5 301,
  L5-Bottom 321; 0.30/0.15 or 0.25/0.10 mm, adjacent layers). 406 vias of 0.27/0.15 mm are intentionally left as
  regular vias.
- Fab requirement: every QFN via-in-pad must be filled and capped. There are 138 via-in-pad sites on 127 pads of
  54 parts (136 microvias, 2 through). The EP pad carries 10 sites: nine microvias and the through via. Use a
  windowed stencil aperture on the EP pad (assembly recommendation).

Saved board: 2026-11-19 09:01:27, 4,638,720 bytes, SHA-256 `62312183A342...`.

Verification of that saved board:
- Altium DRC 09:00:52: **22 violations, none electrical.** Un-Routed 0, Short-Circuit 0, every Clearance rule
  (including the SDRAM class and the 0.09 mm general rule) 0, Width 0, Modified Polygon 0, Hole/Annular 0.
  The 22 are:
  - 5 net antennae, all present in the original board: Top track (32.9, 22.225)-(34.325, 22.225) on USB5V0, and
    vias at (50.05, 13.75), (51.05, 13.55), (53.2, 12.7), (55.7, 13.3).
  - 4 solder-mask slivers of 0.085 mm (rule 0.10 mm) between U2 corner pads 1/64, 16/17, 32/33 and 48/49.
  - 11 silk-to-mask and 2 silk-to-silk items, cosmetic, near U2 (C8 and C9 designators against U2's) and U3-33.
- Independent offline checks on the extracted board: extraction equals the judged final model (5,876 tracks,
  1,982 vias, 868 pads, 0 mismatches), width check 0 of 5,876 tracks, no orphan copper, SDRAM-class clearance 0,
  body check 0, 1,260 microvias verified by `mark_microvias.py --expect 1260 --verify`.

How it was applied (all in `tools/`, run in this order through File > Run Script, saving only the PCB each time):
`NoPmodX4TabUndo`, `NoPmodQfnPlace`, `FabBCopper_NotchlessHQ`, then `mark_microvias.py` and a repour. The first
Altium DRC found orphan fragments left by the delta and D8/D9 on L4/Bottom at 0.0762 mm, so `FabBCopper_NotchlessHQFix`
removed 66 tracks and 14 vias and added 36 tracks. The next DRC found 3 SDRAM clearance violations of 0.0994 mm, so
`FabBCopper_NotchlessHQFix2` narrowed the two D8 L4 segments to 0.12 mm. The generated delta scripts refuse to run
unless each object to remove matches exactly one object on the board.

**Router bug (fixed 2026-11-19).** `tools/router.py` defined its `SDRAM` set with bare names (`D0`..`D15`, ...), but
the board's data nets are `SDRAM-Dn` (U3 side) and `Dn` (U1 side), all in the SDRAM_DATA class. `route_check.py` therefore gave the
`SDRAM-Dn` nets only the 0.09 mm general clearance and missed the 0.10 mm SDRAM-class rule (it hid the D8 gap that
Altium's DRC found). The set now includes `SDRAM-D0`..`SDRAM-D15`, and `route_check` flags the old D8 plan and passes the
corrected one. The Altium DRC is still the authority for the SDRAM class; keep running an independent L3/L4
clearance check after any SDRAM re-route.

Open items after this change:
- **Release data regenerated 2026-11-19** from the saved board (SHA-256 `62312183A342...`): Altium Gerbers 09:31 and
  NC drills 09:44 (with "Use drilled slot command (G85)", so the two X1 plated slots are `G85` records), then
  `fab_facts.py`, `fab_notes.py`, `generate_jlcpcb_assembly.py` (BOM, CPL, notes, drawings, assembly zip) and
  `package_fabrication_release.py` (`fabrication/..._PCBWay_Fabrication_2026-11-19.zip`, 23 entries). Both release
  gates print PASS. The assembly package describes U2 as the QFN-64 (EP stencil window, filled/capped via-in-pad),
  X4 as the SMD S2B-PH-SM4-TB (LCSC C295747), and U10 as 93LC46BT-I/MS (MSOP-8) at its new position. The 2026-11-13
  BOM had the SOIC-8 U10.
- **Sourcing.** Buy the FT2232HQ-REEL only from FTDI-authorized distributors. On 2026-11-16 none had stock until
  about Mar-Apr 2027, so re-check lead time before ordering.
- **U2 footprint record (fixed 2026-11-19).** Sheet 4's U2 footprint model record had `ModelDatafileEntity0` still on
  `FT2232HL-LQFP64` while `ModelName` was `FT2232HQ-QFN64`. `tools/u2_ft2232hq.py` now sets both and
  `tools/u2_model_entity.py` repaired the sheet (only record 267 changed).
- **Left as is.** Sheet 4 has a `93LC46B_I_SN_3V3` record with no entity (it predates this work), and
  `tools/bom_audit.py` still has FT2232HL text from the first release.
- The U2 mask slivers (0.085 mm) and the silk items were accepted. They are raised as engineering question 3 in the fab
  notes, because a fab whose minimum mask dam is 0.10 mm may ask about them.

## Superseded: edge-tab solution (2026-11-16, FT2232HL + PCB tab)

This was the earlier plan: keep U2 as the original FT2232HL LQFP-64 and add a tapered south-edge PCB tab between
X2 pins 30 and 31 for the S2B-PH-SM4-TB. It was applied once, then removed again (`NoPmodX4TabUndo`) when the
FT2232HQ was chosen instead.

- X4 centre: `(30.00, 1.20)` mm, top side, rotated 180 degrees so the cable exits south.
- Tab outline, clockwise from the original south edge:
  `(25.30, 0.00)`, `(25.60, -3.70)`, `(34.40, -3.70)`, `(34.70, 0.00)` mm.
- The tab is 9.40 mm wide at the board, 8.80 mm wide at its outer edge, and extends 3.70 mm.
- X4 mounting-pad clearance to the tab is 0.300 mm at the outer edge and at least 0.324 mm at the tapered sides.
- X4 signal-pad clearance to U2 is 1.325 mm. `body_check.py` reports no X4 body findings at a 0.10 mm gap.
- The initial footprint conflict removes only the old X4 fan-out: 7 tracks, 5.80 mm total, and no vias.
- The composed copper plan removes 8 tracks and 1 obsolete GND microvia, then adds 23 track segments and 1 GND
  microvia. It reuses the existing VBATT through-via and closes every connection.
- Model gates passed: `route_check` 0 violations, `widthcheck` 0 violations, `route_conn` 0 opens,
  `prune_stubs` 0 dead objects, independent full-board judge 0 new violations, `planeweb` 0 power-plane objects
  off the main pour, and `body_check` 0 X4 findings.

Evidence is in `tools/route/x4_feasibility/edge_tab/`.

## Other options studied (evidence in `tools/route/x4_feasibility/`)
Option 1 below became the final solution (U2 at (30.50, 14.55) after the full re-route; the figures here are the
first feasibility run). The others were not verified to route completely.

1. **qfn/** Swap U2 to the **FT2232HQ (QFN-64)** at (30.375, 14.675) rot 0. **Chosen.**
   - S2B centre (31.39, 4.90), unmirrored.
   - Pad positions:
     - Pin 1 VBATT at (30.39, 7.75).
     - Pin 2 GND at (32.39, 7.75).
     - Mounting pads at (28.04, 2.0) and (34.74, 2.0).
   - Clearances: 0.325 mm to the S2B, 1.008 mm to X1. D6 needs a via move.
   - Rework: about 55 connections and 720 mm of track to re-route. The USB pair must be re-coupled by hand and the power widths restored.
   - **Blocked on stock:** there is no FT2232HQ at FTDI-authorized distributors until about Mar-Apr 2027 (DigiKey/Mouser backorders). Brokers are banned by the BOM rule because FTDI clones exist.
2. **u2-west/** Move U2 west to (21.75, 15.75) rot 270 and move about 10 small parts.
   - About 1 m of re-routing, with at least 18 connections left open in the best run.
   - SDRAM reference stitching gets worse.
3. **Ruled out:**
   - **u2-bottom:** U2 on the bottom side.
   - **x1-move:** moving X1.
   - **u1-shift:** shifting U1.
   - **other-slot:** another edge slot.

## Traps to know
- **KiCad footprints are y-down.** Rotating 180° in a y-up frame mirrors the part. Place the S2B at rot 0 with y negated. Some early feasibility models were mirrored.
- **Stock land vs the board edge:** the stock S2B land puts the body face 0.5 mm from the edge, and the mounting pads stick out 0.2 mm past the body face.
- **Copper under the S2B:**
  - The VU trunk passes through the S2B area and needs a rip.
  - Vias for D5-D7 sit under the S2B signal pads.
- **Altium flips a part about its centre**, not about its origin. A layer flip moves it. The fix is in `tools/NoPmodU10Fix.pas`.
- **Do not trust DRC for bodies.** Run `python tools/body_check.py`.

## Pipeline used so far (tools/)
1. `route/route_model.py` builds the model (KiCad python, env FABB_MODEL).
2. `bodies_fix_prep.py` does the rips and moves.
3. `router.py` routes; flags: --nets, --rip, --pops, --seed, --soft, --slack, --checkpoint.
4. `compose_plan.py` composes the plan.
5. Gates: route_check, widthcheck, judge, prune_stubs, route_conn, planeweb, body_check.
6. `emit_copper.py` writes a DelphiScript `.pas`, which you run in Altium (File > Run Script).
7. Save the board.
8. `mark_microvias.py` (board file closed).
9. Repour, rebuild connectivity, DRC, then the fab and assembly release (`generate_jlcpcb_assembly.py --assembler pcbway`).

## State on 2026-11-17 (SUPERSEDED, kept for history; see "Final solution")
Everything in this section predates the notchless FT2232HQ work. The live PcbDoc, sheet 1, sheet 4 and the PcbLib
were all updated on 2026-11-18/19; the notes about `generate_jlcpcb_assembly.py` are still true.
- **PcbDoc on disk = 24de4472.** This is the last committed, DRC-0 board.
  - Altium has an **unsaved** ECO open on it: X4 -> S2B-PH-K-S through-hole side entry, and U10 -> MSOP.
  - Discard it, do not save it, if you change X4 again.
- **Sheet 1 on disk** has X4 = JST-S2B-PH-K-S (through-hole side entry, which the user rejected).
  - The pre-change copy is `backups/zulu_a7_1.SchDoc.pre-x4-side`. The B2B through-hole version is `.pre-x4-tht`.
  - **The original top-entry SMD sheet is the committed git version.**
- **Sheet 4 on disk** has U10 = 93LC46BT-I/MS (MSOP-8, bottom side).
  - The user approved this change to fix the U10-under-X2 collision. Keep it.
- **PcbLib** has the new footprints JST-B2B-PH-K-S, JST-S2B-PH-K-S and MSOP-8_3X3_P0.65. It has **no** S2B-PH-SM4-TB footprint yet.
- **`tools/generate_jlcpcb_assembly.py`** has X4 notes that describe the through-hole side entry. They are stale.
- **Other collision fixes still open:**
  - U4/U1 overlap: deferred.
  - R34/U7: move planned, not saved.
  - U10 MSOP placement: not saved.
- None of the above is committed. The last commit is 1166f8c.

## Standing rules
- Never push PCBWay order numbers or order files. The GitHub repo is PUBLIC.
- Buy FTDI parts only from FTDI-authorized distributors.
- In Altium, save only the active document, never Save All. Leave the Fab B project, which is also open, untouched.
