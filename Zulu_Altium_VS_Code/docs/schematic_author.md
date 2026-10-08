# Author in the schematic title blocks (2026-10-08)

The user asked for their name, Christian Tambe, to appear as author on the schematic sheets.

## What was wrong

The EAGLE title block (the DOCFIELD symbol) has the text "AUTHOR:" followed by `>AUTHOR`. In EAGLE, `>AUTHOR`
resolves to the schematic's global attribute, which is "Christian Tambe".

The Altium EAGLE importer turned `>AUTHOR` into a DOCFIELD parameter named AUTHOR whose text is the literal word
"AUTHOR". It also dropped the "AUTHOR:" label, whose name collided with that parameter. So every Altium sheet showed
just "AUTHOR" in the author row. "Christian Tambe" existed only as a hidden sheet parameter, `Author`. The KiCad
conversion inherited the same placeholder.

## Change

`tools/schematic_author.py` makes three edits to every SchDoc:
1. It sets the DOCFIELD's AUTHOR parameter to "Christian Tambe", at the `>AUTHOR` position.
2. It appends a sheet label "AUTHOR:" at the PROJECT: label's x and the author row's y, in PROJECT:'s font
   (FontID 2) and colour. The row now reads "AUTHOR: Christian Tambe", as in the EAGLE original.
3. It updates the header Weight to the new record count.

| Sheet | Title block | AUTHOR value at | Label at |
|---|---|---|---|
| zulu_a7_0 Block Diagram | (250, 112) | (330, 97) | (255, 97) |
| zulu_a7_1 Power | (250, 112) | (330, 97) | (255, 97) |
| zulu_a7_2 General IO | (380, 114) | (460, 99) | (385, 99) |
| zulu_a7_3 Memory | (380, 112) | (460, 97) | (385, 97) |
| zulu_a7_4 FT2232 | (262, 112) | (342, 97) | (267, 97) |
| zulu_a7_5 FPGA Connections | (380, 112) | (460, 97) | (385, 97) |
| zulu_a7_6 FPGA Power | (266, 112) | (346, 97) | (271, 97) |

Coordinates are Altium schematic units (10 mil).

The script refuses to run twice, and checks after writing that every other record is byte-identical. The same
script was run on the HDI_Optimized copy's sheets.

## Checks

- **Visual:** Altium opens the sheets, and the title blocks of sheets 1 and 3 read "AUTHOR: Christian Tambe",
  aligned under "PROJECT: zulu_a7".
- **ECO:** the preview (Design > Update PCB Document) lists only the usual baseline: the ten PCB-only net classes
  and the USB differential pair, never executed. The edit adds no schematic-to-PCB change.
- **Records:** in every sheet, every record header is consistent and every record is NUL-terminated.

## Scope

- **Edited:** `Zulu_Altium_VS_Code/` and `Zulu_Altium_VS_Code_HDI_Optimized/` (seven SchDocs each), and the KiCad
  copy (`Zulu_kicad/tools/apply_schematic_author.py`; see `Zulu_kicad/CONVERSION.md`).
- **Left as they were:** the superseded `Zulu_Altrium/` and the `Altium_backup/` snapshot, which still show
  "AUTHOR".
- **Already correct:** the EAGLE files.
- **Not affected:** the PcbDoc and the fabrication and assembly outputs.
