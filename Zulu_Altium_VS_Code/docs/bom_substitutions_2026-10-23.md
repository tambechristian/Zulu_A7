# BOM substitutions (2026-10-23)

PCBWay's quotation T-3P7W1150632A (2026-10-21, HDI_Optimized BOM, 2 units) offered two parts in place of ours. The
user approved both, and they are now the parts of record on every copy.

| Ref | Was | Now | Manufacturer |
|---|---|---|---|
| U1 | XC7A35T-1CPG236C | XC7A35T-2CPG236I | AMD/Xilinx |
| LD0 | EAST1616RGBA8 | 19-337/R6GHBHC-A01/2T | Everlight |

## Why they fit

**U1.**
- Same die, CPG236 package and pinout. Only the speed grade (-2, faster) and the temperature grade (industrial,
  Tj -40 to 100 C) differ, so a design that meets -1 timing also meets it on a -2 part.
- The Vivado project still targets `xc7a35tcpg236-1`; retargeting it to `-2` is optional.
- Buy only from an AMD-authorized distributor. The generator's LCSC code for it is C1552335, the identity the
  2026-09 sourcing audit recorded for this grade.
- U3 (AS4C32M16SB-7TCN, TA 0 to 70 C) is now the board's narrowest temperature grade; AS4C32M16SB-7TIN is its
  industrial alternate. U3's NOTE still says "matching the -1C FPGA". That sits in a dated 2026-09-08 entry, was
  true then, and is left as history.

**LD0.** It is the water-clear twin of the diffused part (= EAST1616RGBA4), on the same Everlight 19-337 land the
board already uses.
- Wavelengths: 624 / 525 / 470 nm, against 624 / 525 / 468 nm for the A8.
- VF at 20 mA: 1.7-2.4 / 2.7-3.8 / 2.7-3.8 V, against a maximum of 2.4 / 3.7 / 3.7 V for the A8. Green and blue
  behind 33 ohm from 3.3 V were already marginal, and they stay marginal.
- Pin numbering depends on the datasheet revision:
  - The footprint numbers anodes 1 B, 3 R, 5 G and cathodes 2 B, 4 R, 6 G.
  - Everlight's DSE-0002657 Rev.4 (2013, the sheet LCSC links) numbers the cathodes 1/2/3 and the anodes 4/5/6.
  - Rev.6 (2016) numbers them like the footprint.
  - Either way the cathodes are in the cathode-mark column, on the board's WEST side. Both assembly notes and the
    PCBWay BOM line say to follow the cathode mark, not the pad numbers. The drawings' red dot ("pin 1/A1") sits
    on footprint pad 1, an anode; the notes say so. The drawings themselves carry no LD0 caveat.
- LCSC C264519 was checked on 2026-10-23 on its part page. The generator says so (`LCSC_SOURCES`) instead of
  crediting the September audit.

## Where it was applied

The schematics are the BOM source (`bom_audit.load_components()`), so the change was made there. Only fields
changed: no symbol, footprint, pin, wire or net.

- **Altium, production and HDI_Optimized:** `tools/apply_bom_substitutions.py` updated 143 component records per
  copy, 142 for U1's parts and 1 for LD0, on `zulu_a7_2/5/6.SchDoc`.
  - Fields changed: MANF#, Comment, DeviceName and ComponentDescription on U1; MANF#, Comment, NOTE and SPEC on LD0.
  - A record-level diff against git HEAD shows nothing else changed.
  - LD0's SPEC was corrected by the script's `RESPEC` table afterwards.
  - The script runs against the HDI folder from this copy's `tools/`.
- **KiCad:** `Zulu_kicad/tools/apply_bom_subs_kicad.py` changed the same fields in the three sheets, the board and
  `ctambe.kicad_sym`. It copies LD0's NOTE and SPEC from the Altium General IO sheet, so both copies carry
  identical strings.
  - `--resync-ld0` copies them again after an Altium-side correction, and is repeatable.
  - The library symbol names (`XC7A35T-CPG236-1CPG236C`) were left, since renaming them would re-link symbols.

**Not changed, on purpose: the PcbDocs.** Their hashes are cited by the fabrication notes and archives, which stay
valid. Both PcbDocs still carry the old values:
- U1's Comment, MANF#, DeviceName and description;
- LD0's Comment, MANF#, SPEC and NOTE.

A schematic-to-PCB ECO (Design > Import Changes) will offer every one of these parameter changes. Leave them
unticked until a new fabrication release. `Zulu_Altrium/` and `Altium_backup/` were not touched.

## Tools and documents brought along

| File | Change |
|---|---|
| `tools/generate_jlcpcb_assembly.py` | Notes and BOM line notes read U1's and LD0's MPNs from the schematic. The LD0 pin-numbering caveat is in both the PCBWay and the assembler-neutral notes (`LD0_NUMBERING`). The neutral notes also give the cathode side and the red dot. |
| `tools/bom_audit.py` | Supply rows for the two new MPNs (PCBWay quote prices; not a Digi-Key lookup). The U1/LD0 labels follow MANF#. Second-source and derating rows were updated: U1 is Tj -40 to 100 C. |
| `docs/component_validation.md` | Dated note at the top; the false "same pads and numbering" claim for the RGBA4 corrected. The rest stays the 2026-09 audit. |
| `README.md` | The FPGA is named XC7A35T-2CPG236I. |
| `docs/power_budget.md`, `tools/power_budget.py` | U1's junction limit is 100 C (industrial), not 85 C (commercial). |
| `tools/README.md`, `apply_bom_substitutions.py` docstring | The 2026-10-23 round and the fields the script now edits. |

## Regenerated outputs

| Output | Result |
|---|---|
| Production PCBWay release (`assembly/`) | BOM and notes changed; the drawings were redrawn; the CPL is unchanged (it carries no part numbers) |
| HDI_Optimized neutral release | BOM (now with C1552335 and C264519) and notes changed; the drawings were redrawn |
| HDI_Optimized PCBWay release | BOM and notes changed; CPL unchanged (see the drawings note below) |
| `docs/zulu_a7-bom.csv` (`tools/master_bom.py`) | U1 and LD0 rows changed |
| KiCad `reports/` | Netlist, ERC and DRC reports updated |

- **HDI_Optimized PCBWay drawings:** they were not rewritten, because a PDF viewer held them open. A scratch
  regeneration produced drawings with identical extracted text, so the committed PDFs are current. The release date
  is not printed on them.
- **Upload ZIP:** `Zulu_A7_HDI_Optimized_PCBWay_Assembly_2026-10-23.zip` replaces the 2026-10-21 ZIP. It holds the
  same 5 files, each byte-identical to its source. SHA-256:
  `1E4098F26ABA6C20D5B66D400E421FEC96221EB75D1A709ED7F306ADD0064572`.
- **Release date:** each release now says 2026-10-23.

## Verification

- Generator validation: PASS on all three releases. It checks the BOM columns and quantities, the DNS rows, the
  SMT-only CPL, and the notes' text rules.
- Altium: a record-level diff shows only the fields above.
- KiCad:
  - The netlist differs from the committed one only in U1 and LD0 field values.
  - `pcb drc --schematic-parity`: 0 unconnected items, 0 parity issues.
  - The DRC violation total moves run to run (2022 before, 2032 now). Only the clearance and hole_clearance counts
    move; every other category is identical.
  - ERC: 1,648, as before.
- X2 in PCBWay's quotations: each board needs 2 x PRPC009SAAN-RC and 2 x PRPC011SAAN-RC. The 2026-10-21
  quotation bought only PRPC009. The 2026-10-23 re-quote adds item 59, PRPC011SAAN-RC at $0.430 (2 per board), so X2
  is now fully bought. That re-quote still lists U1 and LD0 under their old part numbers, with the substitutes in
  its purchase column, because it was made from the 2026-10-21 BOM.
