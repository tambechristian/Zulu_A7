# X1 shell-stake slots (2026-10-07)

X1 is a Molex 105017-0001 micro-USB-B. Its two front shell legs (MS1/MS2, at the mating-face end; the earlier text said "rear") were drilled as 0.60 mm round holes,
but the Molex land pattern (SD-105017-001, "Recommended P.C.B. pattern layout") calls for 0.60 x 1.30 mm slots
with full-radius ends. The legs are 0.60 +/- 0.10 mm wide and 0.30 mm thick, so they cannot enter a 0.60 mm round
hole and the connector would sit high on its SMT joints.

## Source of the fix

The fix was first made in `Zulu_Altium_VS_Code_HDI_Optimized` (`tools/CorrectX1Slots.pas`, notes in
`HDI_OPTIMIZATION_NOTES.md`). That copy was only read, never written. Its geometry was ported to this board unchanged.

## What changed on `Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc`

Scripts: `tools/ProdX1Slots.pas` (`CorrectX1Slots`) and `tools/ProdX1Slots2.pas` (`ResolveX1SlotClearances`,
`RefineX1SlotClearances`), each loaded as its own `.PrjScr`. They differ from the reference only in the document
guard, which accepts this board only, and in the X1 designator guard. On this board the designator was off-board at
(28.829, 27.259), not at the reference's (37.167, 22.300).

- **X1-MS1/MS2:** plated slots, hole 0.60 mm, length 1.30 mm, rotation 90, centred at (29.5199, 23.9585) and
  (36.5201, 23.9585). The pad copper stays at 0.90 mm round.
- **CHAN12:** the CHAN12 route was moved clear of the slots.
  - Bottom run moved from y 23.20 to 23.15 (x 16.25 to 35.80).
  - The L4-L5 and L5-Bottom stacked microvias moved from (36.15, 23.25) to (35.80, 23.35), with their Bottom and
    L4 stubs.
  - The four tracks and two vias are byte-identical to the reference board's records.
- **X1 designator:** moved to (37.442, 22.250), the reference's final position.
- **Rule `HoleSize_X1`:** `InComponent('X1')`, 0.20 to 1.30 mm. It admits the 1.30 mm slot length without
  widening the global hole-size rule.
- **Planes:** the L2 and L5 polygons re-poured around the slots and the moved vias. The fill changes are local to X1
  apart from one L2 vertex at (36.759, 6.668) that moved by 1.9 um.
- **Save side effects, not design changes:** X1's designator autoposition flag cleared; three HoleSize rule
  priorities renumbered; one stale CHAN12 connection record dropped; drill-manager and GUID caches updated.

## Verification

- **Altium DRC** 2026-10-07 08:11: 0 warnings, 0 rule violations. The report is `Design Rule Check - zulu_a7.drc`.
- **`tools/verify_stack.py`:** PASS (JLCH061611N2-2116).
- **NC drill:**
  - `zulu_a7-SlotHoles.TXT` has exactly two G85 slots, 0.60 mm tool, ends 0.70 mm apart, so 1.30 mm overall.
  - The round-hole counts are unchanged. Top-Bottom has 440 holes: 380 vias, 2 x 0.85 and 58 x 1.016. The laser
    and buried pairs are 296 / 282 / 369 / 230 / 230.
  - The old 0.60 mm round tool is gone.
- **Gerbers versus 2026-10-02:**
  - Top copper, both masks, both pastes, Bottom silk and the profile are identical.
  - L2, L4, L5, Bottom copper and Top silk differ only at X1's slots, CHAN12 and the designator, plus the 1.9 um
    L2 vertex above.
- **New board hash:** PcbDoc SHA-256 `e91c148d92b3d73828f69b7a5623f56d86d6e40dd546c6b97d5ce94c9e88d4b7`. The
  pre-fix hash was `181b1a8c...`. (Superseded by the later changes below and in `x2_power_pins.md` and
  `x2_pin_labels.md`.)

## Release files

- `fabrication/Zulu_A7_JLCPCB_Fabrication_2026-10-07.zip` replaced the 2026-10-04 archive, which had the round
  holes. It has itself been superseded by the PCBWay package below.
- The drill files are now named `zulu_a7-RoundHoles.*` plus `zulu_a7-SlotHoles.TXT`. The old `zulu_a7.TXT` and
  `zulu_a7.TX*` files were removed.

## Not changed

- **PcbLib footprint:** the `MOLEX-105017-0001` footprint in `zulu_a7.PcbLib` still has round MS holes, as in the
  reference copy. An "Update from PCB Libraries" would revert the slots until the library is updated too.
- **Assembly release:** `assembly/` was not regenerated. X1's position and rotation are unchanged.

## Lands and clearances fixed for PCBWay (2026-10-07, later)

Verification of the slot fix found two problems, inherited from the reference geometry: no ring at the slot ends,
and copper under 0.15 mm from the slot walls. Fabrication moved to PCBWay, so the fix targets PCBWay's published
"Normal" class. The sources are capabilities.html items 10, 11, 13, 17 and 19, and the hole-to-edge and hole-spacing
engineering-question pages; the full list is in the session's research notes.

**Pads.** `tools/ProdX1Pads3.pas` (`FixX1PadsAndClearances`, after the read-only `X1PadsCanary`) switched the MS1/MS2
padstack to top/middle/bottom mode:
- Top and Bottom: oblong 1.11 x 1.81 mm. The ring is 0.255 mm, against PCBWay's component-hole ring of at least
  0.254 mm on 1 oz outer copper.
- Inner layers: 0.90 x 1.60 mm. The ring is 0.15 mm.

**CHAN12.** The route was re-done:
- The Bottom run now stops at x 27.95.
- It rises west of MS1 to (28.72, 23.92) and (28.72, 24.62).
- It crosses over both slots at y 25.02.
- It drops to the moved L4-L5 / L5-Bottom stacked microvias at (37.45, 24.40).
- L4 goes straight down from there to the existing run at (37.45, 23.15).

**Planes.** All polygons were re-poured.

Measured on the saved board (KiCad import of the PcbDoc, `scratchpad x1fix2/verify_saved.py` and `check.py`; exact values from
the independent verification):

| Check | Result | PCBWay normal |
|---|---|---|
| MS ring, Top/Bottom | 0.255 mm | >= 0.254 |
| Slot hole to inner copper | L5 VCC3V3 plane 0.240 mm (was 0.090); tracks >= 0.2477 mm (CHAN13 on L4) | >= 0.203 |
| Slot hole to outer copper | >= 0.3608 mm (FPGA-TCK on Bottom) | >= 0.152 (old engineering-question page 0.35) |
| Hole to hole, different nets | >= 0.559 mm | PTH >= 0.45, via >= 0.30 |
| Slot hole to board edge | 0.791 mm | >= 0.5 |
| New copper to board edge | 0.342 mm (CHAN12 at y 25.02); via land 0.85 mm | >= 0.25 |
| New copper to copper | 0.0900 mm (re-poured L5 plane to the MS inner lands and the moved via lands); >= 0.1058 mm on Bottom (MS2 to FPGA-TCK); 0.0977 mm MS1 to CHAN13 on L4 | board rule 0.09 |

The only object changes against the slot-fix board:
- the MS1/MS2 land sizes;
- 4 CHAN12 tracks changed and 4 added;
- 2 CHAN12 vias moved;
- the plane fills.

No pad moved or changed net.

- **Altium DRC** 2026-10-07 09:40: 0 warnings, 0 violations. It was re-run at 10:03, after the 09:41 save, on the
  unchanged board: 0 / 0. `verify_stack.py` passes. The PcbDoc SHA-256 is
  `4f73e1a215a21d19623c0956719072aeaa8c6b258501a21de8923bfff705f688` (superseded by the X2 changes:
  `x2_power_pins.md`, then `x2_pin_labels.md`).
- **Fab outputs** regenerated. The slot file is unchanged: two G85 slots. The round-hole counts are unchanged
  (440 / 369 / 296 / 282 / 230 / 230). Gerbers changed only at the MS lands, CHAN12 and the planes; GM and GBP differ
  only by aperture numbering.
- **Release:** `fabrication/PCBWAY_FAB_NOTES.txt` and `Zulu_A7_PCBWay_Fabrication_2026-10-07.zip` replace the JLCPCB
  notes and zip.
- **KiCad:** the copy was updated the same way (`Zulu_kicad/tools/apply_x1_pads.py`).

### Board-wide items PCBWay must review (not X1-specific; listed in the fab notes)

- Track/space 0.0762 / 0.09 mm. capabilities.html items 14/15 put 1 oz under 4 mil in "unable"; their order form
  allows 3/3 mil.
- Via rings: 0.075 mm (through and laser) and 0.06 mm (buried). PCBWay's via ring minimum is 3 mil (0.076 mm).
- Different-net via hole-to-hole down to 0.24 mm. PCBWay asks for 0.30 mm.
- 0.20 mm through-via drills in a board about 1.63 mm thick. capabilities.html item 5 caps a 0.20 mm drill at 1.6 mm.

## Library footprints updated (2026-10-07)

- **Altium `zulu_a7.PcbLib`:** footprint `MOLEX-105017-0001`, MS1/MS2 changed by `tools/ProdX1Lib2.pas`
  (`FixX1LibFootprint`, after the read-only `X1LibCanary`). They are now plated 0.60 x 1.30 slots at rotation 90 with
  top/middle/bottom lands 1.11 x 1.81 / 0.90 x 1.60 / 1.11 x 1.81. A first load, `ProdX1Lib.pas`, refused: its
  position guard subtracted the library origin, but library pad coordinates are footprint-relative.
- **Altium check:** with KiCad's Altium loader, MOLEX-105017-0001 is the only one of the 41 footprints that changed,
  and only MS1/MS2 within it changed. They now equal X1 on the board. The footprint graphics are unchanged. Pad 2 was
  already 10 nm off the board before this edit.
- **KiCad `zulu_a7.pretty/MOLEX-105017-0001.kicad_mod`:** the MS1/MS2 pad blocks were replaced with copies of the
  board's padstack (`Zulu_kicad/tools/apply_x1_libpads.py`, then a splice that keeps the pad UUIDs). The file differs
  from the old one only in those two blocks.
- **KiCad check:** MS1/MS2 now equal X1 on the board. MH1/MH2 already differed between library and board, as
  CONVERSION.md records for X1.
