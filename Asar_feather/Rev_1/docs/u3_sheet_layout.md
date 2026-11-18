# Sheet 4 (asar_a7_3.SchDoc, Memory): U3 re-laid out as one block (2026-11-17)

Same layout as the no-PMOD board's sheet (Zulu_A7_no_pmod/Rev_2/tools/sheet3_u3_layout.py), ported to this board by
`tools/sheet3_u3_layout.py`. Schematic drawing only: no connection changed.

## What changed

- U3 (AS4C32M16SB-7BIN, 54-ball FBGA; 55 EAGLE parts, one pin each) is one box, x 555-875, y 610-1010:
  - left: A0-A12, BA0/BA1 (nets BS0/BS1), CS#, RAS#, CAS#, WE#, CKE, CLK, NC (ball E2, open), labels on 10-unit stubs;
  - right: DQ0-DQ7, LDQM, DQ8-DQ15, UDQM straight to their D0-D15 / LDQM / UDQM labels (this board has no DQ series
    resistors, unlike the no-PMOD board);
  - top: the 7 supply balls, each WIRED to its 0.1 uF cap (C3-C9 keep their old pairing) and on to one VCC3V3 rail;
  - bottom: the 7 ground balls, each under the supply ball it mirrors in its FBGA row (A9-A1, A7-A3, B3-B7, E7-E3,
    J9-J1, C7-C3, D3-D7: the pairing the sheet's U3 DECOUPLING note gives; the no-PMOD TSOP used pin 55-n).
- C3-C9 values hidden (a 3-line caption gives them); U3 designator/comment bottom-centre justified in the box.
- microSD note frame narrowed (x 70-500, y 600-755); the X3 note re-wrapped to four lines, its stale "needs its own
  footprint" replaced by "PCB footprint DM3D-SF".

## Proof

- Script: sheet nets identical before/after (56 nets, 122 pins); SRC md5 053ed08c -> a999eb30.
  Backup `backups/asar_a7_3_before_u3_layout.SchDoc`.
- Independent review (workflow wf_7e4046ae-1ad: connectivity with its own extractor, layout, file integrity,
  electrical/datasheet ballout, each finding verified by a skeptic): no problem introduced. Its two cosmetic points
  (U3 text off-centre, caption wording) were fixed before applying.
- Altium: sheet closed in the Projects tree, written, reopened; Validate PCB Project = Compile successful, 28 warnings,
  none on asar_a7_3 (undriven-net warnings on sheets 2/4/5 and X2's unused sub-part); Protel netlist
  BYTE-IDENTICAL to the one exported just before the change (181 components, 155 nets).

## Pre-existing findings from the review (not changed)

- **C11 / U4 bypass (board):** the sheet draws C11 as the SPI boot flash U4's VCC bypass and C12/C13 at X3, but the
  board (and the U3 DECOUPLING note) put C11, C12, C13 under U3 with C3-C9: U4 had no capacitor within ~11.5 mm of its
  VCC pin. FIXED the same day: C11 moved to the top beside U4 pin 8 and the note updated (docs/c11_move.md).
  C12/C13 are still drawn at X3 but placed under U3 (C3 is 1.7 mm from X3-4).
- U3's ComponentDescription still describes the TSOP-II ("pin 40 is NC"); the BOM generator overrides it, the NOTE
  parameter is right.
- Three X3 wire stubs have a free left end at x 255 (y 847/827/817); connectivity is correct.
- The MASTER SPI BOOT and U3 = AS4C32M16SB frames overlap by 22 units (x 710-732, y 1130-1195).
