# Zulu A7: Altium to KiCad 10 conversion (2026-10-06)

Source: `Zulu_Altium_VS_Code/Imported zulu_a7.PrjPcb` working copy (includes the
uncommitted HDI stack), imported with KiCad 10.0.5 *Import Non-KiCad Project > Altium*.

Open `kicad_project/zulu_a7.kicad_pro`.

## What was fixed after the import (tools/, in run order)

| Step | Script | Why |
|---|---|---|
| 1 | `fix_hierarchy.py` | Altium project is Flat (HierarchyMode=0): net labels are project-wide, but KiCad imported them as sheet-local, which broke every cross-sheet net. All 351 labels are now global labels. KiCad 10 also imported the 7 sheets as 7 top-level sheets, which kicad-cli could not read. They now sit under a classic root sheet (`zulu_a7.kicad_sch`; old page 1 is `zulu_a7_0.kicad_sch`). The 119 `#PWR?` symbols are annotated. |
| 2 | `link_board.py` | Footprints were not linked to symbols (178 parity errors). Each footprint now has its symbol path, and `zulu_a7.pretty` holds the 32 footprints as placed on the board. |
| 3 | `finish_libs.py` | Symbol Footprint fields point to `zulu_a7:*`. The embedded symbols are written out as project libraries (`ctambe`, `rcl`, `pinhead`, `zulu_a7-altium-import`), and the lib tables are native. |
| 4 | `sync_nets.py`, `copy_fields.py` | 12 auto-named nets are renamed to the schematic names, no-connect pads get `unconnected-*` nets, symbol fields are copied to footprints, and the title-block FRAME symbols are set to not-on-board. |

Steps 2 and 4 read the schematic netlist from `kicad.net` in this folder. The last copy is in `reports/`.

## Verification

- `compare_nets.py`: all 177 multi-pad nets have identical pad membership and identical names on the schematic and the board. Every pin missing from the board is on a single-pin no-connect net.
- DRC schematic parity: **0 issues**. Unconnected items: **0** (with the zone fills from the import).
- `geom_diff.py`: footprints, pads, tracks/vias and zones are identical to the raw import, so no copper or placement was changed.

## Known open items

- **Design rules were not translated.** Altium rules do not import, so KiCad checks the board against its defaults: Default netclass 0.2 mm clearance and default via/drill limits. That gives about 2,000 DRC violations (clearance, microvia drill/annular, track width). If zones are refilled under these defaults, 5 plane connections drop (VCC3V3 to X2/JP4/J1, plus one GND stub). The JLC/HDI rules need to be set up as netclasses and custom rules before anyone refills zones or trusts KiCad DRC.
- ERC: 39 errors, all carried over from the design. They are unused FT2232H pins with no no-connect flags, power pins with no PWR_FLAG, and U1 G17. The 1,494 off-grid warnings come from the Altium coordinates.
- 94 `lib_symbol_mismatch` warnings: these are per-instance symbol variants created by the importer (mostly U1 and the SDRAM). They are kept embedded on purpose.
- 7 `lib_footprint_mismatch` warnings (X1, JP3, JP4, J1, X2, U5, U7): the library copy is normalised to the top side at 0 degrees. This is cosmetic.
- The HDI vias come in as plain blind/buried vias, not as KiCad *microvia* types. There are 380 through vias (0.2 mm drill) and 1,407 vias with a 0.15 mm drill: blind F.Cu-In1 296, In4-B.Cu 230; buried In1-In2 282, In2-In3 369, In3-In4 230. Each stacked microvia is split into one via per layer pair. Check them against JLC's stack before fabricating from KiCad. Altium remains the fabrication master.

## Update 2026-10-07: X1 shell-stake slots

The production Altium board got the X1 slot fix (see `Zulu_Altium_VS_Code/docs/x1_slot_fix.md`). The same change
was applied here by a scratch copy of `tools/apply_x1_slots.py` (same logic; the tools copy only adds file paths
and comments). Every new value comes from KiCad's own import of the corrected Altium board.

What changed:
- X1-MS1/MS2: drill changed to `oval 0.6 1.3`.
- Four CHAN12 tracks and two CHAN12 vias moved.
- The X1 reference text moved.
- The GND (In1) and VCC3V3 (In4) zone fills were replaced by the imported fills. The zones were not refilled,
  so the warning above still applies.

Verification:
- Re-loaded board versus the import: tracks, vias, pads, texts and both fills are geometrically identical.
- Re-loaded board versus before: net membership is identical.
- The text diff shows only these objects plus fill vertices.
- The library footprint in `zulu_a7.pretty` still has round MS holes. (Fixed later the same day; see below.)

## Update 2026-10-07 (later): X1 slot lands and clearances, fabrication at PCBWay

The production board got oblong X1-MS1/MS2 lands and a local CHAN12 re-route (see
`Zulu_Altium_VS_Code/docs/x1_slot_fix.md`). `tools/apply_x1_pads.py` applied the same change here, again copying
every value from KiCad's import of the corrected Altium board:
- MS1/MS2 padstack front/inner/back: Top and Bottom 1.11 x 1.81 oval, inner 0.90 x 1.60 oval.
- Four CHAN12 tracks changed and four added.
- Two CHAN12 vias moved to (37.45, 24.40) Altium.
- GND (In1) and VCC3V3 (In4) fills replaced.

Re-loaded, the board's tracks, vias, pads, reference texts and both fills are geometrically identical to the
import. All pad nets are unchanged.

Library footprint `zulu_a7.pretty/MOLEX-105017-0001.kicad_mod`:
- MS1/MS2 now match the board (slot drill and front/inner/back lands).
- The change was made with `tools/apply_x1_libpads.py`, then a splice that keeps the pad UUIDs.
- The X1 entry in the 7 `lib_footprint_mismatch` warnings remains, for MH1/MH2's inner-layer sizes as before.

## Update 2026-10-07 (later): X2 power pins re-ordered

At the user's request X2's supply pins were re-ordered on all three copies: 17 GND, 18 VCC3V3, 19 VCC1V8,
20 VCC1V0 (was 17 VCC3V3, 18 VCC1V8, 19 VCC1V0, 20 GND). Pin 16 (CHAN13) is unchanged. The Altium side is
recorded in `Zulu_Altium_VS_Code/docs/x2_power_pins.md`.

Schematic (`tools/apply_x2_pins_sch.py`):
- ZULU-CONN units 15/14/17/16 (gates +3.3V/+1.8V/+1.0V/GND) now carry pins 18/19/20/17. The change was made both in
  `zulu_a7_2.kicad_sch`'s embedded symbol and in `ctambe.kicad_sym`.
- The four placed units moved to the rows of their new pins with their global labels. The row wires are identical,
  so they stayed.
- The X2 NOTE (41 copies) and the sheet's text box are reworded as on the Altium sheet.
- `kicad-cli sch export netlist` before and after differs in exactly the four X2 pins.

Board (`tools/apply_x2_pins_pcb.py`, values from KiCad's import of the changed production PcbDoc `517b553e...`):
- X2-17..20 re-netted.
- The VCC1V8 In2 stub moved to pin 19.
- The VCC1V0 Bottom run extended to pin 20, with its stub moved there.
- GND (In1) and VCC3V3 (In4) fills replaced from the import.
- X2's NOTE field updated.

Verification:
- `geom_diff.py` against a fresh import of the changed production board: footprints, pads, tracks/vias and zones are
  IDENTICAL. The same check on the pre-change pair was also identical.
- DRC with schematic parity: 0 parity issues, 0 unconnected items.
- The total stays at about 2,026 violations under KiCad's default rules. That count varies by a few between runs of
  the same unchanged board (2,021-2,030 seen), all in `clearance` and `hole_clearance`.
- ERC: 1,648, the same types and counts as before.
- `reports/kicad.net`, `erc.rpt` and `drc.rpt` were regenerated.

## Update 2026-10-07 (later): X2 pin labels

X2's pin numbers and short names are now on the top silkscreen, as on the Altium boards
(`Zulu_Altium_VS_Code/docs/x2_pin_labels.md`): 63 texts covering 33 pins, plus the U2 and X3 references moved
clear of them. `tools/apply_x2_labels.py` copied them from KiCad's import of the labelled production PcbDoc
(`bd7cbfd7...`); it refuses to run twice and requires exactly 63 new texts.

Verification:
- DRC with schematic parity: 0 parity issues, 0 unconnected items.
- No silkscreen-type findings.
- The total stays at about 2,026 violations, in the noise band.
- `reports/drc.rpt` was regenerated.

## Update 2026-10-07 (later): BTN moved 0.5 mm left, X2 reference hidden

BTN (the PTS810 user button) moved 0.5 mm west, away from the RGB LEDs, and X2's reference is hidden, as on the
Altium boards (`Zulu_Altium_VS_Code/docs/btn_move.md`).

`tools/apply_btn_move.py` takes everything from KiCad's import of the moved production PcbDoc (`89a421b9...`):
- The tracks and vias that differ from that import are swapped in. The geometry match ignores net names, because
  this copy names some nets from the schematic. The swap was 14 tracks out and 17 in, 13 vias out and 16 in, all on
  VCC3V3, N$BTN, LED0_B and FT-RESETN and inside BTN's area.
- BTN takes its new position.
- X2's reference is set invisible.
- The GND (In1) and VCC3V3 (In4) fills are copied from the import; they are not refilled.

The script stops unless BTN is at its old place and the difference has exactly these counts.

Verification:
- `geom_diff.py` against a fresh import of the moved board: footprints, pads, tracks/vias and zones are IDENTICAL.
  The unmoved board against the same import differs, as a control.
- DRC with schematic parity: 0 parity issues, 0 unconnected items. The total is 2,022, in the noise band.
- The BTN-area findings that changed are the same default-rule types reported before (0.2 mm clearance, 0.3 mm
  minimum hole, stacked holes co-located), now at the moved objects. This copy's rules were never translated.
- `reports/drc.rpt` was regenerated. The schematic did not change, so `kicad.net` and `erc.rpt` stand.
- KiCad's python exits with code 127 after `SaveBoard` returns. The saved files are complete and load; the gate
  above was run on them.

