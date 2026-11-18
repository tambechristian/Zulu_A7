# Sheet 3 (zulu_a7_3.SchDoc, Memory): U3 re-laid out as one block (2026-11-18)

User: "rearrange U3 frame of fab b and connect the components like you did on zulu a7 no pmod". Port of
Zulu_A7_no_pmod/Rev_2/tools/sheet3_u3_layout.py as `tools/sheet3_u3_layout.py`, applied to BOTH Fab B revisions (their
sheet 3 had the same FileHeader stream, md5 951ed07c, after the U4 fix of docs/u4_schematic_tidy.md). Schematic drawing
only: no connection changed.

## What changed

- U3 (AS4C32M16SB-7TCN, TSOP-II; 54 EAGLE pin parts) is one box, x 555-875, y 610-1010, same pin plan as no-PMOD:
  - left: A0-A12, BA0/BA1, CS#/RAS#/CAS#/WE#, CKE/CLK, NC (open), labels on 10-unit stubs;
  - right: DQ0-DQ7, LDQM, DQ8-DQ15, UDQM on 10-unit stubs straight to their D0-D15 / LDQM / UDQM labels (Fab B has no
    DQ series resistors; the no-PMOD sheet routes them through R119-R134);
  - top: the 7 supply pins, each WIRED to its 0.1 uF cap (C3-C9) and on to one VCC3V3 rail with a single port;
  - bottom: the 7 ground pins, each under the supply pin it faces in the TSOP (pin 55-n), with GND ports.
- C3-C9 values hidden (the caption gives them); U3 designator/comment centred in the box (bottom-centre justified).
- microSD note frame narrowed (x 70-500, y 600-755); the X3 note re-wrapped to four lines, its stale "Needs its own
  footprint on the PCB" replaced by "PCB footprint DM3D-SF" (X3's footprint in the schematic and both PcbDocs).
- Deviations from the no-PMOD script: no resistors / SDRAM-Dn labels, caption without the R119-R134 lines, centred U3
  text, the X3 line above, input checked by FileHeader-stream md5 so the script runs on either revision.

## Proof

- Script: sheet nets identical before/after (56 nets, 122 pins); 17384 -> 17397 records. Both revisions -> d8f81377.
  Backup `backups/zulu_a7_3_before_u3_layout.SchDoc`.
- Independent review (workflow wf_0f527bcc-c01: own connectivity extractor with mutation tests, layout boxes against
  Altium's text metrics and the no-PMOD result, content + file integrity; findings checked by skeptics): every pin on
  the same net with the same partners, all 54 U3 pin hot ends and the cap/port positions identical to the no-PMOD
  sheet, no new overlap (the old X3-note-over-U3 collisions are gone), U4/R2/R6/R7/C11 untouched. Both findings raised
  were refuted.
- Altium (Rev_2 project, with sheet 5's change and the U4 fix): sheets reopened and checked on screen; Validate =
  Compile successful, 34 warnings (same as the baseline); Protel netlist BYTE-IDENTICAL to the baseline taken with the
  original sheets 3 and 5 (e5d33386).
