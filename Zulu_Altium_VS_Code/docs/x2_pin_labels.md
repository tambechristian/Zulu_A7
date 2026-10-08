# X2 pin labels on the top silkscreen (2026-10-07)

The user asked for X2's pin numbers and pin names on the board. No earlier version of the board had them: neither
the Altium boards nor the EAGLE originals; the EAGLE `ZULU-DIP37` package carried only `>NAME`/`>VALUE`.

The labels are on the **top** silkscreen. The strips mount on the underside and the board plugs into a breadboard
or socket, so the bottom side faces down and cannot be seen.

## What is on the board

Each label is stroke text 0.8 mm high with a 0.15 mm stroke, which is PCBWay's minimum legend character height
and width. Names are shortened to fit the 2.54 mm pitch:
- CHAN*n* becomes C*n*.
- CHAN-CLK becomes CLK; VCC3V3, VCC1V8 and VCC1V0 become 3V3, 1V8 and 1V0.
- RST# becomes RST; ANALOG-IO0 and ANALOG-IO1 become AI0 and AI1.

| Pins | Label |
|---|---|
| 3, 10-20, 22-29, 31-40 (30 pins) | two lines: the number nearest the pin, then the name |
| 2, 21, 30 | one vertical line, `2 CLK`, `21 GND`, `30 C20` (no room for two lines) |
| 1, 4-9 | none: U4 (flash), Q1 and R4 leave only 0.9-1.5 mm (the user chose to leave them unlabelled; pin 1 keeps its square pad) |

The left-edge groups (pins 10-20 and 31-40) sit 0.127 mm right of centre to stay 0.25 mm inside the board edge.

**Moved to make room:**
- U2's designator, from (25.309, 21.239) to (23.509, 19.639).
- X3's designator, from (3.383, 20.050) to (1.083, 19.250).
- Both were set to manual autoposition.

## How

- **Plan:** a planner (scratchpad `x2labels/plan_labels.py`) measured the free top-side space beside each pin and
  placed every label.
  - Font metrics were measured on the HDI board's title: advance 1.0 x height, glyph width 0.667 x height.
  - It checked each label against the top pads (mask + 0.254 mm), all top silkscreen (0.254 mm), every top part
    body, and the board edge (0.25 mm).
  - It then found the nearest legal spot for each displaced designator.
- **Script:** `tools/X2PinLabels.pas` is generated from that plan, one guarded procedure per board.
  - The order is `X2LabelsCanary`, then `PlaceX2LabelsProd`.
  - It adds 63 text objects and moves the two designators.

## Verification

- **Altium DRC:** 2026-10-07 15:51, after the final save: 0 warnings, 0 rule violations. Silk To Solder Mask
  (0.254) and Silk to Silk (0.254) are among the rules checked.
- **Board hash:** PcbDoc SHA-256 `bd7cbfd775b741521d8ab8ac197ff58d2a7674c2757522fa4702cb32f46489c2` (was
  `517b553e...`; superseded by the BTN move, `btn_move.md`).
- **Outputs:** regenerated with G85 ticked. Against the previous release only the GTO layer changed: 25 old strokes
  went (U2 and X3 moved) and the labels were added. Every other layer has identical geometry, and the drill files
  are identical.
- **Release:** `fabrication/PCBWAY_FAB_NOTES.txt` has the new hash.
  `Zulu_A7_PCBWay_Fabrication_2026-10-07.zip` was rebuilt (23 entries). After the U1 via wording fix in the fab
  notes, its SHA-256 is `7EEACEFC6055E9F04CC54571B018060404EB98106EF0EA88291D98F20F1BD448` (rebuilt
  since; see `btn_move.md`).
- **Other copies:**
  - HDI_Optimized: same labels, U2 moved, and the title moved, finally to (37.5, 5.0). See its notes.
  - KiCad: `Zulu_kicad/tools/apply_x2_labels.py` copies the 63 texts and the two references from KiCad's import of
    this board.
