# X2 power pins re-ordered (2026-10-07)

The user asked for the four supply pins at the end of X2's top row to be re-ordered. Pin 16 (CHAN13) and every
other X2 pin are unchanged.

| Pin | x (mm) | Before | After |
|---:|---:|---|---|
| 16 | 11.43 | CHAN13 | CHAN13 |
| 17 | 8.89 | VCC3V3 (+3.3V) | GND |
| 18 | 6.35 | VCC1V8 (+1.8V) | VCC3V3 (+3.3V) |
| 19 | 3.81 | VCC1V0 (+1.0V) | VCC1V8 (+1.8V) |
| 20 | 1.27 | GND | VCC1V0 (+1.0V) |

The header's grounds are now pins 1, 17 and 21. 3.3 V is on pin 18 alone.

## Schematic (`zulu_a7_2.SchDoc`)

`tools/x2_power_pins.py` follows the method of `x2_top_row_order.py`, the sixth pass of 2026-09-09:
- The four gate copies (+3.3V, +1.8V, +1.0V, GND) move to the rows of their new pins, each with its wire and net label.
- All 41 copies of the multi-gate part get their pin records renumbered: 17->18, 18->19, 19->20, 20->17.
- The X2 NOTE and the sheet's text frame are reworded.

The script refuses to run twice. Its built-in verify passed: pins 1-40, every gate on the row of its pad, and both
landings clear. The same script was run on the HDI_Optimized copy's sheet, which was byte-identical. Both sheets
now have identical streams.

## Board (`zulu_a7.PcbDoc`)

`tools/X2PowerPins.pas` was loaded as its own `.PrjScr`; the read-only `X2PinsCanary` ran first, then `FixX2PowerPins`.
It does three things:
- **Pad nets:** the four pads are re-netted with `P.Net` plus `Net.AddPCBObject` (without `AddPCBObject` the net
  does not save).
- **VCC1V8, L3:** the 0.30 mm stub moves from pin 18 to pin 19, at x 3.81, y 23.05-24.13. The L3 trunk at y 23.05
  already passed under pin 19.
- **VCC1V0, Bottom:** the 0.20 mm run at y 23.05 now starts at x 1.27 instead of 3.81. Its stub moves from pin 19
  to pin 20, at x 1.27, y 23.05-24.13.

GND (pin 17) and VCC3V3 (pin 18) reach their pads through the L2 and L5 planes, so all polygons were repoured.

The first DRC after the script showed 4 un-routed connections. They were stale net membership: Altium still listed
the moved pads in their old nets. Saving, closing and reopening the board, then repouring, cleared them.

The ECO preview (Design > Import Changes) then listed no net changes, only the X2 NOTE parameter. That one change
was executed. The ten PCB-only net classes and the USB differential pair it also offers to remove were left
unticked, as always.

- **Altium DRC** 2026-10-07 14:28, after the final save: 0 warnings, 0 rule violations.
- **Board hash:** PcbDoc SHA-256 `517b553e53d2148f2704600bb90345a12782c01b58199dc36e62376971a67054` (was
  `4f73e1a2...`; superseded by the X2 pin labels, `x2_pin_labels.md`).
- **Object counts:** tracks, vias, pads, nets, classes, rules and polygons are the same as before (4,828 / 1,787 /
  839 / 177 / 30 / 63 / 2).

## Outputs

Gerbers and NC drill were regenerated with G85 slots ticked. Altium wrote them to `Project Outputs for zulu_a7/`,
and they were copied over the release files in `Imported zulu_a7.PrjPcb/`.

Against the previous release:
- **Drill files:** all seven are byte-identical.
- **Copper changes:**
  - G2 (L3): one draw, the VCC1V8 stub.
  - GBL: two draws, the VCC1V0 run and stub.
  - L2 and L5 fills: only inside x -0.5..16.5, y 21.5..25.5.
- **Unchanged geometry:** every other layer, including masks, paste, silkscreen and the profile.

The release files were updated as follows:
- `fabrication/PCBWAY_FAB_NOTES.txt`: board hash and DRC time.
- `fabrication/Zulu_A7_PCBWay_Fabrication_2026-10-07.zip`: rebuilt with the same 23 entries, each byte-identical
  to its source. SHA-256 `FD44329E99735988F4353921D5E475DA6D2AE82D376192CDE338037E41BB097D` (rebuilt since;
  see `x2_pin_labels.md`).

## Assembly

`tools/generate_jlcpcb_assembly.py --release-date 2026-10-07` was re-run.
- **BOM and CPL:** byte-identical; the pin swap moves no part.
- **Notes:** new date, source commit and board hash, plus the X1 slot line the generator already carried.
- **Drawings:** regenerated.

## Other copies and documents

- **HDI_Optimized:** same schematic script and the same `X2PowerPins.pas`. DRC 14:34 0/0; board
  `71e75c10...`. See its `HDI_OPTIMIZATION_NOTES.md`.
- **KiCad:** `Zulu_kicad/tools/apply_x2_pins_sch.py` and `apply_x2_pins_pcb.py`. The board values were taken from
  KiCad's import of this board. See `Zulu_kicad/CONVERSION.md`.
- **Master BOM:** `docs/zulu_a7-bom.csv` was regenerated with `tools/master_bom.py`.
  - It changed in two lines: the X2 note, and the 0.1 uF line, which gains C155-C159.
  - C155-C159 are the stage 5b stitching caps that the master BOM had been missing.
- **Text:** `component_validation.md`, `power_budget.md` and `tools/power_budget.py` now carry the new pin numbers.
