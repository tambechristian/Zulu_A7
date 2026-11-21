# Zulu_a7_no_pmod Rev 3: STEMMA QT and the PCBWay release (2026-11-21)

Rev 3 is no-PMOD Rev 2 (as committed on 2026-11-20) plus a STEMMA QT / Qwiic I2C connector.

## Design change

- **X5** = JST SM04B-SRSS-TB (1.0 mm pitch, 4-pin, side entry, SMT) on the Top at the east short edge, rotation 90,
  origin (58.28, 8.15) mm, cable opening facing east. Pins 1 GND, 2 VCC3V3, 3 I2C-SDA, 4 I2C-SCL; MP1/MP2 GND.
  Its metal hold-down tabs end 0.30 mm from the east edge. The footprint and 3D body come from Asar's library
  (`tools/lib_add_x5.py`).
- **Schematic.** X5 is on sheet 2 (`tools/add_stemma_qt.py`). On sheet 5, FPGA balls U19 and R19 now carry
  I2C-SDA / I2C-SCL instead of No-ERC marks (`tools/stemma_sheet5.py`).
- **C141, C142, C144, C145** (22 uF 0805) moved from Top to Bottom at the same XY. The user chose "keep them
  underneath" over moving them between U1 and U2.
- **Routing.** 23 connections were re-routed (`tools/route/stemma/`; plan applied by `FabBCopper_StemmaQT.pas`).
  Microvias were re-marked and the planes repoured.
- **Silkscreen.**
  - X5's designator is hidden: it sat on C85/C86's pads.
  - The X2 '21 GND' label became '21': its GND part sat under X5's MP1 tab. The illustration therefore rings
    pin 21 as unlabelled.
  - The board title became **ZULU A7 2.4** (user decision 2026-11-21; Rev 2 reads 2.3), via `NoPmodTitle24.pas`.

## Board state

| Check | Result |
|---|---|
| Board save | 13:55:37, MD5 `8ba56533`, SHA-256 `346D121C...` |
| DRC (13:55:47) | 0 violations, Component Clearance run (`docs/drc_title_24.drc`; before the title change: `docs/drc_stemma_qt.drc`) |
| Open connections | 0 (route_model + route_conn on the saved board) |
| Body gate | PASS: 0 fail, the same 15 warnings as Rev 2 |

## Fabrication outputs

| Output | When / where | Notes |
|---|---|---|
| Gerbers | 13:57:11 | Re-exported after the title change |
| NC drill | 14:00:11 | "Use drilled slot command (G85)" had to be ticked again: the setting copied from Rev 2 was off |
| Protel netlist | 12:47:58 | X5 and the I2C nets present |
| Schematic PDF | 12:50:55, `Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod_schematic.pdf` | 7 sheets, schematics only, no BOM |

`tools/fab_facts.py` measured the saved board:

- Every drill file: 0 missing / 0 extra.
- Through vias in SMD pads: the 2 accepted ones (U2-EP, X4-2).
- Via counts (Rev 2 -> Rev 3):

  | Via type | Rev 2 | Rev 3 |
  |---|---|---|
  | Through | 318 | 315 |
  | Top-L2 | 337 | 351 |
  | L2-L3 | 302 | 311 |
  | L3-L4 buried | 398 | 402 |
  | L4-L5 | 300 | 296 |
  | L5-Bottom | 321 | 317 |
  | **Total** | **1,976** | **1,992** |

  Microvias total 1,275.
- Via-in-pad sites went from 143 to 151, all microvias except the two accepted ones. The new sites include the
  moved caps C144-1 and C145-1.

The routing added these items, all inside existing precedent and all listed in the fab note:

- One more through-via land tangent to a same-net pad: R1-1, FPGA-INIT#, land overlap 0.04 um, hole 0.075 mm
  outside the pad.
- One more unstacked L2-L3 microvia: LED0_R at (60.4, 13.1).
- Top copper is now 0.30 mm from the east edge (X5's tabs; it was 0.36 mm).

## Packages

**Fabrication.** `tools/fab_notes.py` and `tools/package_fabrication_release.py` were retargeted to Rev 3:

- The fab note gains a "CHANGES FROM NO-PMOD REV 2" section and says plainly that this is a new revision, not
  a replacement for the Rev 2 files.
- **NO_PMOD_REV_3_PCBWAY_FABRICATION_RELEASE PASS**: `fabrication/Zulu_A7_no_pmod_Rev_3_PCBWay_Fabrication_2026-11-21.zip`,
  23 entries.

**Assembly.** `tools/generate_jlcpcb_assembly.py --assembler pcbway`:

- **ASSEMBLY_RELEASE PASS**, 68 BOM lines (X5 added as SM04B-SRSS-TB(LF)(SN)), 189 fitted parts (32 top / 157 bottom).
- Output files: `assembly/Zulu_A7_no_pmod_Rev_3_PCBWay_*`.

**Traps found on the way:**

- The working copy of `si/series_r/dq_series_r_plan.json` had CRLF line endings (git autocrlf on the copy), so
  its md5 check failed. It was restored to LF, which matches the committed blob.
- The Rev 2 release files that were copied into Rev_3 were deleted from Rev_3's `assembly/` and `fabrication/`.
  Each was first checked to be a byte or line-ending copy of a committed Rev_2 file.

The board illustrations were redrawn from this board (title 2.4).
