# Component bodies: collisions fixed, 3D bodies, Component Clearance and a release gate (2026-11-19)

The user saw BTN against X5's housing and U8 over C151 in the 2026-11-18 board pictures and asked, as on the no-PMOD
board, for 3D bodies on the footprints and `body_check.py` as a release gate. Altium's batch DRC had never run
Component Clearance on this board, so "DRC 0" said nothing about parts sitting on each other.

## The check and the gate

- `tools/body_check.py` (ported from Zulu_A7_no_pmod/Rev_2): every body as a datasheet box (nominal and maximum)
  centred on the part's pads; X1, X3, X4, X5 from the outlines in `tools/body_mech.json`; X2 as two bottom-side
  header housings (the Feather headers ship loose and go in from the bottom). Reports body over body, body over a
  pad, and gaps under 0.10 mm.
- Sizes and heights from the manufacturer drawings, researched and independently cross-checked (workflow
  wf_5eafb72e-ea7): `tools/body_heights.json` holds every height with its source. Two corrections came out of it:
  X1's shell is 7.50 mm wide (the footprint's Mechanical 3 outline used the 6.90 mouth opening), and the Sullins
  header insulator is 2.54 +-0.20 wide (checked at its nominal 2.54, as on no-PMOD; a part 0.10 away could touch the
  2.74 extreme by up to 0.01 mm).
- `tools/release_body_gate.py` re-reads the saved PcbDoc (`route_model.py` and `comps_from_board.py` with KiCad's
  reader) and FAILs on any overlap or on a footprint with no body model; warnings do not stop a release.
  `tools/package_fabrication_release.py` and `tools/generate_pcbway_assembly.py` now run it before writing anything,
  and the fabrication package also refuses a DRC report that did not run Component Clearance.

## What the check found on board c4bf0b71 (37 failures)

| Finding | Before | Fix | After |
|---|---|---|---|
| U8 (LTC3556 QFN-28) body over C151 pad 2 | -0.150 mm | C151 0.50 mm east; the VU through via it would land on moved into C147-2 (via-in-pad) with a new 0.4 mm Top track; a 0.4 mm VBATT track keeps a full-width joint to U8-23 | pads 0.20 mm from U8's body |
| BTN pad 2 vs X5 (STEMMA QT) housing | 0.10 mm (bodies 0.35) | BTN 0.50 mm west; N$BTN and N$LD0B re-laid on Top (4 tracks out, 6 in); BTN's via-in-pads stay inside the moved pads | pad 0.36 mm, bodies 0.85 mm |
| X2 south header housing over the 0201 row C40 C41 C152 C153 C154 R19 C155-C159 C38 | -0.020 mm (-0.035 at maximum) | the row 0.125 mm north, still straight; vias stay, 21 Bottom jogs (0.20 mm GND / VCC3V3 / FT-VPLL, 0.15 mm FT-VPHY / FT-VCORE); R18 (+0.02, +0.05) opens the TDI lane; FT-RESETN moves to L4 with a laser stack in R19-1; the TDI through via 0.125 mm north | 0.105 mm (0.090 at maximum) |

Each fix was designed and independently verified (workflow wf_15b49ce3-839), then merged and re-gated:
`tools/route/bodyfix/` (`btn/`, `c151/`, `x2row/` plans and READMEs, `merge.py`, `gates.py`, `model0.json` = the
saved board). Merged plan: 15 parts moved, 20 tracks + 6 vias removed, 37 tracks + 6 vias added (every removed via
replaced by one of the same span and hole). `gates.py`: route_check 0 violations / 0 open, hole_gate PASS, pad_gate
PASS for all 15 parts, moved pads at least 0.093 mm from other-net copper, body_check 0 overlaps.

The four remaining warnings are the saved board's own and not overlaps: U7's body 0.025 mm from L3 pad 1, X2's
housing 0.040 mm from the C101, C102 and C139 pads.

## Altium

1. `tools/FeatherCopper_BodyFix.pas` (from `tools/emit_copper.py`, now with no-PMOD's component moves and
   span-matched via removal): "Moved 15 parts, removed 20 tracks and 6 vias, placed 6 vias and 37 tracks"; every
   part's pad 1 landed where planned. Repour All, saved 21:40:25. The saved board matched the plan exactly (840 pads,
   4805 tracks, 1575 vias). Altium then closed; `mark_microvias.py --expect 1168` marked the 4 new lasers (backup
   `asar_feather.PcbDoc.pre-microvia`; the 11-17 one renamed `.pre-microvia-2026-11-17-c11`).
2. `tools/AsarBodies3D.pas` (from `tools/emit_bodies.py`): 178 extruded bodies on 175 parts, Mechanical 13 (unused
   before), heights from `body_heights.json`. X4 is three bodies (housing and the two legs beside the pad notch), X2
   two bottom-side housings. No body by design: the Creative Commons artwork and the JP3/JP4 test pads.
3. `tools/AsarCCRules.pas`: Component Clearance exceptions above the 0.254 mm default: `ComponentClearance_X2`
   (X2 vs All, 0.05 mm, as no-PMOD: the row at 0.105, C101/C102 at 0.14, C139 at 0.24 do not touch the housing) and
   0.15 mm for the three chip pairs closer than 0.254 since their placement (C165/R117 0.20, R1/R34 0.22,
   C166/R118 0.25).
4. Component Clearance ticked for batch DRC. The first run flagged only the Creative Commons artwork off the board
   (U$2-U$5 4.0 mm apart, overlapping boxes); `tools/AsarCCArtwork.pas` respaced U$3/U$4/U$5 to the no-PMOD
   spacing (nothing on the board moved).
5. **DRC 0 warnings / 0 violations, 35 rules including Component Clearance** (`docs/drc_body_fix.drc`, 22:05:09 on
   the saved board). sch_vs_board MATCH, route_conn 0 open, 1168 microvias verified.

Board: MD5 **091a3b6e509edbf72ec42e6fadcd7a2d**, SHA-256 EF32A488...E802BD, saved 21:51:49.
Backup before: `backups/asar_feather_before_body_fix.PcbDoc` (c4bf0b71).

## Library

`asar_feather.PcbLib` now holds the board's footprints with their bodies: Design > Make PCB Library on a scratch copy
of the board, `tools/AsarLibDropUsed.pas` DropVariants removed the seven `_2` duplicates it wrote (0.0001 mm origin
differences), and the 21 footprints the board does not use (FT2232HL-LQFP64, USB-C-HRO, TSOPII-54, ...) were copied
in from the old library (DropUsed on a scratch copy, then copy/paste). Result: the same 53 footprints as before, 27
with bodies (30 bodies). Old library: `backups/asar_feather.PcbLib.pre-bodies3d` (19422b95); new 600f9b7b.

## Release files

Gerbers 22:02:01 and NC drill 22:02:59 (split plated / non-plated and G85 re-ticked after the restart, as before).
Drill counts unchanged. `fab_facts.py` re-run; `package_fabrication_release.py` retargeted (hash, date):
`fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-19_PROVISIONAL.zip` PASS with the body gate; the notes say
Component Clearance and the body gate passed. `generate_pcbway_assembly.py`: PASS,
`assembly/Asar_Feather_PCBWay_Assembly_2026-11-19_PROVISIONAL.zip`; the BOM is unchanged and the CPL changes are
exactly the 15 moved parts. The 2026-11-17 packages are superseded and removed (they stay in git history).

The board pictures (`docs/pin_labels_proposal.png`, `docs/pin_labels_bottom.png`) were redrawn from this board.

## Independent review (workflow wf_b7726389-b47) and what changed after it

Confirmed: board vs backup object by object (only the planned changes, the repour, 178 bodies matching
`tools/route/bodies3d/bodies.json` and `body_heights.json`, the 4 rules, the artwork moves), the DRC report really ran
Component Clearance on the saved board, the library holds the same 53 names with identical pads, the CPL changes are
exactly the 15 moved parts and the BOM is unchanged.

Fixed after the review:
- **NPTH figure in both release notes.** Since the 2026-11-17 releases the notes said the non-plated holes are
  "9.000 mm" from the nearest track: `fab_facts.py` looked for tracks only in the grid cell of the hole centre, so a
  2.5 mm hole never found one and the start value came out. It now searches every cell the hole covers: **0.240 mm**
  (N$LD0G Top track to the hole at (48.26, 2.54); rule 0.127 mm). Laser / buried / through values unchanged.
- The notes' fixed phrase "centred in the pad (U1 balls and one resistor pad)" is now built from the data:
  "149 U1 balls, R108-1, R19-1, X4-2".
- `body_check.BODY` maxima raised to the fitted parts' datasheets (C0402 1.15 x 0.65, C0603 1.85 x 1.05, C0805 2.20,
  SC189 2.95 / 3.10, CTS 742C +-0.20). No new overlap.
- A maximum-tolerance body over another part's pad is now reported (`body_pad_max`, a warning in the gate; nominal
  overlaps still fail). It shows **U7's body (SC189 at its 3.10 maximum) over L3 pad 1 by up to 0.075 mm**; at the
  2.95 nominal it just touches the pad edge. This placement predates today.
- The gate fails if X1, X3, X4 or X5 change side, rotation or footprint (their outlines are fixed offsets).
- The board's U7 3D body stays 2.90 mm long (the nominal when the bodies were placed); the gate now uses 2.95.

Open, not changed (pre-existing):
- **U2 (FT2232HQ, QFN-64) has no pin-1 silk mark on the board.** `FeatherSilkFix4.pas` deleted it in the silk
  clean-up (logged as an "X1 mark"); restored, it would be 0.325 mm from U2's pad mask, above the rule. Make PCB
  Library copied the board's trimmed silk into four library footprints: QFN-64 (no pin-1 mark, shorter corner ticks),
  TDFN-8 (side lines gone, pin-1 tick moved), WSON-8 (pin-1 tick moved, south line shortened), FBGA-54 (two edges
  shortened). The old library's silk is in `backups/asar_feather.PcbLib.pre-bodies3d` and git.
- X2's Sullins insulator is 2.54 +-0.20: at its 2.74 extreme it would overhang the C101, C102 and C139 pads by
  0.06 mm (checked at nominal, as on no-PMOD).
- JP3 lacks one silk line that the library's TP-1X03-SMD (taken from JP4) has; the schematic's U10, JP3 and JP4 name a
  different footprint as model datafile entity (SPI-8_SOIC_150, 1X03-NOSILK) than as model (both kept in the library).
