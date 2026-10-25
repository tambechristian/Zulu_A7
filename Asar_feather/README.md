# Asar A7 Feather

The Zulu A7 (Artix-7 XC7A35T + 64 MB SDRAM + FT2232H + LiPo charger) re-cut to the Adafruit Feather form
factor: 50.80 x 22.86 mm, 16-pin and 12-pin 0.1 in strips. Altium project:
`Asar_feather.PrjPcb/asar_feather.PrjPcb`. It was seeded on 2026-10-23 from the production project
`Zulu_Altium_VS_Code` (commit 8df3577) by `tools/make_project.py`. The board keeps the production 6-layer HDI
stack, via types, rules and net classes.

**State, 2026-10-23: schematic converted, footprints drawn, board outlined, first-pass placement done.
Not routed.** Everything below was checked from the files, not from the GUI.

## Design changes

| Item | Production Zulu A7 | Feather | Why |
|---|---|---|---|
| U3 SDRAM | AS4C32M16SB-7TCN, TSOP-II-54 (22 x 12 mm) | AS4C32M16SB-7BIN, 54-ball FBGA 8 x 8 mm | Same die. The TSOP does not fit across a 17.8 mm band. |
| U2 USB bridge | FT2232HL, LQFP-64 (12 mm over leads) | FT2232HQ, QFN-64 9 x 9 mm | Same die and pin numbers. Exposed pad left without a net: the datasheet says it is not internally grounded. |
| U4 flash | W25Q128JVSIQ, SOIC-8 208 mil | W25Q128JVPIQ, WSON-8 6 x 5 mm | Size. Exposed pad without a net ("can be left floating"). |
| U10 EEPROM, R96, R98 | 93LC46BT-I/SN, SOIC-8 | 93LC46BT-I/MNY, 2 x 3 mm TDFN (smallest package Microchip makes; same pin numbers), on the bottom. R96/R98 pull-ups kept. | It was removed at first and restored the same day: sheet 4 was re-taken from production and `apply_feather_schematic.py --sheet 4` re-run, then `FeatherPlaceU10.pas` placed the three parts. Without it, Vivado's hardware manager cannot use the bridge (`program_ftdi` needs an EEPROM), the board has no USB serial number, and the FT2232H declares only its default bus power while the charger draws up to about 495 mA. The land pattern is Microchip drawing C04-129-MN; the exposed pad has no net, which the datasheet allows. |
| X1 USB | Molex micro-B | HRO TYPE-C-31-M-12 (LCSC C165948) | USB-C. ID pin 4 becomes CC1 and shell pin MH1 becomes CC2, each with its own 5.1 k Rd (R27/R28). |
| J1 Pmod + R29-R33 | 2x6 header + series resistors | removed | No room. A Pmod could come back as a FeatherWing. |
| R26-R28 | Pmod series resistors | R26 = 100 k EN pull-up; R27/R28 = 5.1 k CC pull-downs | Re-used, so no new parts. |
| X2 | 40-pin XuLA2-style DIP | Feather 16 + 12 (footprint FEATHER-28, with the 4 corner holes) | Form factor. |
| SC189 EN (U5-U7) | tied to VIN (VU) | net EN, pulled to VU by R26, out on Feather EN | Feather meaning: grounding EN turns the board off. |
| RESET (new) | none | C&K PTS810, the same part and footprint as BTN, from RST# (FPGA PROGRAM_B) to GND, top side at (23.95, 4.55) mm along the 16-pin edge | A hardware reset: on release the FPGA reloads from flash whatever design is running, which a user button driven by HDL cannot do when the FPGA is blank or hung. R1 already pulls RST# up; R4's 100 ohm limits the current if the FT2232H drives the line while the button is held. Added by `tools/add_reset_button.py` and placed by `FeatherPlaceReset.pas`. |
| JP3/JP4 JTAG | 1x3 through-hole | 1x3 SMD test pads (TP-1X03-SMD) | Size; the bridge does JTAG. |

## Feather pin map (`tools/feather_map.py`)

| Pad | Feather | Net | | Pad | Feather | Net |
|---|---|---|---|---|---|---|
| 1 | RST | RST# (PROGRAM_B: reloads the FPGA) | | 17 | VBAT | VBATT |
| 2 | 3V3 | VCC3V3 | | 18 | EN | EN (SC189 enables) |
| 3 | AREF | AREF (open) | | 19 | VUSB | USB5V0 |
| 4 | GND | GND | | 20 | D13 | CHAN14 U1-C16 |
| 5 | A0 | ANALOG-IO0 -> XADC AD15 divider | | 21 | D12 | CHAN15 U1-A17 |
| 6 | A1 | ANALOG-IO1 -> XADC AD16 divider | | 22 | D11 | CHAN16 U1-B17 |
| 7 | A2 | CHAN0 U1-W13 | | 23 | D10 | CHAN17 U1-A18 |
| 8 | A3 | CHAN1 U1-W14 | | 24 | D9 | CHAN18 U1-B18 |
| 9 | A4 | CHAN2 U1-W15 | | 25 | D6 | CHAN19 U1-C17 |
| 10 | A5 | CHAN3 U1-W16 | | 26 | D5 | CHAN20 U1-D17 |
| 11 | SCK | CHAN4 U1-W17 | | 27 | SCL | CHAN21 U1-E19 |
| 12 | MOSI | CHAN5 U1-W18 | | 28 | SDA | CHAN22 U1-H19 |
| 13 | MISO | CHAN6 U1-W19 | | | | |
| 14 | RX | CHAN7 U1-V19 | | | | |
| 15 | TX | CHAN8 U1-U19 | | | | |
| 16 | D4 | CHAN-CLK U1-P18 (clock-capable) | | | | |

19 FPGA I/O plus 2 analog inputs (A0/A1 only; the board has two XADC dividers, not four). A2-A5 are digital.
Balls as swapped in the pre-routing pass (`tools/pin_swap.json`); Vivado constraints in `vivado/asar_feather_pins.xdc`,
where the header ports are named F_<Feather pin> (F_A2 ... F_SDA, F_D4).

## How it was done, and what checks it

| Step | Tool | Check |
|---|---|---|
| Copy the project | `tools/make_project.py` | md5 of every copied file |
| Schematic edit at file level (4 sheets) | `tools/apply_feather_schematic.py` (data in `feather_map.py`) | `tools/check_feather_schematic.py`: the netlist read from the SchDocs equals the proven Zulu A7 netlist transformed by `feather_map.py`. **PASS**: 155 named nets, 0 mismatches, no merged nets. The extractor `sch_netlist.py` reproduces all 177 multi-pin nets of `Zulu_kicad/reports/kicad.net` on the unedited copy. |
| SDRAM ball map | `feather_map.SDRAM_BALL` | AS4C32M16SB datasheet Rev 1.2, Figure 1.1, read with coordinates |
| Six new footprints | `tools/footprints.py` -> `FeatherFootprints.pas` (run in the PcbLib) | `tools/verify_footprints.py` reads the saved PcbLib through KiCad's Altium reader. **PASS**: 181 pads, including slots and non-plated holes. |
| Empty board + outline | `FeatherBoard.pas` (StripFeatherBoard), `FeatherOutline.pas` | `ReportFeatherOutline`: (0,0) (50.8,0) (50.8,22.86) (0,22.86). Writing `Board.BoardOutline` directly reported success but changed nothing; the Mechanical 1 track method worked. |
| ECO | Design > Import Changes, twice | The 10 PCB-only net classes and the USB differential pair were unticked. X1, U3 and X2 could not be footprint-swapped ("Cannot match pads"), so `FeatherRemove3.pas` deleted them and the second import added them back. |
| Rounded outline | `FeatherRound.pas` (ArcCanary, then RoundOutline): 4 lines + 4 arcs of 2.54 mm (0.1 in) radius on Mechanical 1, then the board shape is redefined from them | Board6 outline = the rounded 2000 x 900 mil shape; BoardRegions match. The nearest object to a corner arc is a mounting hole, 0.77 mm in. |
| L2/L5 pours | L2 and L5 are signal layers (MID3/MID4 in the file) with GND / VCC3V3 polygon pours, not Altium plane layers. Repour does not clip a pour to the board shape in this build. So, in the Polygon Manager: New Polygon from > Board Outline, every vertex moved 0.25 mm inboard (the production pullback), net GND, the original fill options (Pour Over All Same Net Objects, Remove Dead Copper), named L2_GND_FEATHER. Then New Polygon from > Selected Polygon gave L5_VCC3V3_FEATHER. `FeatherPour.pas` removed the two old pours. | Polygons6 holds exactly these two: 8 vertices each with corner arcs, 0.25..50.55 x 0.25..22.61 mm; KiCad's import fills both inside the edge. |
| Placement | `tools/plan_placement.py` -> `FeatherPlace.pas`; plan check `tools/check_placement.py` | `tools/verify_placement.py` on the re-dumped saved board. **PASS**: 169 parts at their planned side and position, 0 pad clashes (0.15 mm, through-hole pads on both sides), no pad within 0.25 mm of the edge. Picture: `docs/placement_v1.png`. |

**File loss, 2026-10-23 at about 16:30.** Altium restarted, and the 13:47 save of `asar_feather.PcbDoc` was found with about 20 % of its bytes zeroed (not an OLE file). It was replaced by Altium's own `History/asar_feather.~(4).PcbDoc.Zip`, the 13:38:56 placed board, which still passes `verify_placement.py`. The outline and pours were then redone as above. The damaged file was kept in the session's temp folder. This project is not under git yet.

## Placement (first pass)

- **Top:** USB-C flush with the left edge, with the LiPo JST above it, 0.425 in from the end (as on Feathers). FT2232HQ, then the FPGA, the SDRAM and the flash in a row along the board. The crystal sits between the bridge and the JST. Button, RGB LED and user/power LEDs are at the right end; the charge LEDs are by the USB. FPGA strap and XADC parts run in a band above the FPGA.
- **Bottom:** the three bucks as tight cells (input cap | SC189 | inductor) behind the USB, with the charger and its resistors under the USB. FT2232 passives and the R4 array sit under the bridge, the FPGA decoupling under the FPGA, and the SDRAM decoupling under the SDRAM. The microSD is at the right end, card slot opening at the right edge (contacts at x = 38.45 mm, inboard).
- The four Creative Commons logos are parked off the board, as on the production copy.

## Pre-routing pass (2026-10-23)

| Step | Tool | Result |
|---|---|---|
| Feather header balls | `tools/plan_pin_swap.py` -> `tools/pin_swap.json`; `tools/apply_pin_swap.py` renames U1's symbol pins (ball + pin name) in every U1 part | Minimum-total-distance assignment over the 37 header + freed balls on banks 14/16 (both 3.3 V); D4 keeps P18 (clock-capable). Straight-line ball-to-pad length 291.1 -> 168.8 mm: the south-strip pins take U1's W/V/U balls, the north strip its A-E balls. `check_feather_schematic.py` reads the permutation, **PASS**; Import Changes moved the 18 nets on U1's pads (the 11 class/diff-pair removals unticked); `sch_vs_board.py` **MATCH**. |
| XDC | `tools/make_xdc.py` -> `vivado/asar_feather_pins.xdc` | 82 pins, each ball checked against the schematic netlist; 19 ports of balls the Feather no longer connects dropped; `create_clock` moved to F_D4. |
| Buck loops | `plan_placement.py` FIXED | Two output 0805s beside each inductor (C80/C97 3V3, C93/C144 1V8, C85/C86 1V0), 1.75 mm apart for a 0.1 mm mask web. |
| FPGA decoupling | `plan_placement.py` FIXED | The production board's 24 under-BGA caps (C89-C92, C95/C96, C107-C124) at the same offsets from U1's centre, same sides and rotations (U1 is rot 0 on both boards). |
| SDRAM decoupling | `plan_placement.py` FIXED | C3-C8 in U3's empty centre ball columns at 1.15 mm pitch, C9/C11 at its ends. |
| U10 | `plan_placement.py` FIXED | Top, above U2's EECS/EECLK/EEDATA pins 61-63, with R96/R98 grouped beside it. |
| Placement on the board | `FeatherPlace3.pas` (generated as `FeatherPlace.pas`, renamed because Altium caches compiled scripts) | `verify_placement.py` **PASS** on the re-dumped board, `check_placement.py` **PASS**: 0 clashes. |
| Rules | `FeatherRules.pas` / `FeatherRules2.pas` (`FixFeatherRules`) | The 6-layer HDI stack, via types and production rules are unchanged. Fixed: `Clearance_Plane_ThruVia` scoped the production pour names and matched nothing (now L2_GND_FEATHER / L5_VCC3V3_FEATHER); new `HoleSize_X2` 0.20-2.60 mm for the 2.5 mm Feather corner holes; `HoleSize_X1` max 1.30 -> 1.80 mm for the 1.7 mm USB-C shell slots. |
| Silkscreen | `FeatherSilkFix2.pas` (FixFeatherSilk2), `FeatherSilkFix3.pas` (ShowSmaller), `FeatherSilkFix4.pas` (NudgeMarks); logs `docs/silk_fix*.log` | The first DRC had 65 silk-to-mask hits. U10 moved 0.25 mm north, off U2's top pad row. 18 straight overlay segments trimmed back to 0.254 mm from every mask opening. U4's pin-1 tick moved 0.2 mm. Four marks with no clean spot within 1 mm deleted: U10's pin-1 tick and south outline line, X1's mark at x 8.45 and L5's centre line, so **U10 has no silkscreen pin-1 mark now**. Designators were tried at the 8 auto-positions, then at 1.0 and 0.8 mm. 5 moved (X1 at 1 mm, X3, U2, U1, BTN). 10 hidden because no clean spot exists: U10, R96, R98, U3, R34, R4, R1, JP3, JP4, plus X2 (off the board, hidden on production too). Hidden names stay in the netlist, BOM and pick-and-place, as on production (HideCrowdedDesignators, 2026-09-11). |
| U2 mask slivers | `FeatherMask.pas` (AddU2Mask), `FeatherMaskProbe.pas` (read-only), `FeatherMaskCache.pas` (RefreshU2Mask) | U2's QFN corner pads (16/17, 32/33, 48/49, 64/1) are 0.16 mm apart in x and y. The board-wide 0.05 mm mask expansion left a 0.085 mm diagonal web, below the 0.1 mm minimum. New rule `SolderMaskExpansion_U2`, 0.035 mm, U2 only (as production's `SolderMaskExpansion_U1`), gives 0.127 mm. Altium ranked it priority 1, but the pads kept a cached 0.05 mm marked valid that the DRC used, so RefreshU2Mask invalidated U2's 65 pad caches. |
| DRC | Altium DRC, `docs/drc_prerouting.drc` | **595, all un-routed connections (nothing is routed yet).** No other violation of any kind. |

## Open items

1. **Routing**: stage 1 done. Production's U1 fan-out was transplanted (201 vias, 771 tracks; DRC: 465 un-routed + 115 antenna stubs, nothing else). The log and the open choice of router for the remaining 465 connections are in `docs/routing.md`.
2. **Compile errors: done (2cf527c).** The 22 single-pin nets are cleared by `tools/clear_single_pin_nets.py`: labels deleted plus no-ERC marks, and AREF keeps its label. Altium now reports "Compile successful, no errors found". 30 warnings remain, of the existing no-driving-source / unused sub-part kinds.
3. **Schematic cosmetics**: X2's gate names still read GND/+1.8V/+1.0V inside the symbol, and the sheet notes describe the XuLA2 40-pin header. U3's symbol text still says TSOP-II.
4. **Silkscreen**: DRC-clean. Not yet fixed: U10 lost its pin-1 tick (no clean spot beside pad 1), and 10 designators are hidden. Revisit after routing, when vias and copper fix what space is left.
5. **Not added yet**: USB ESD protection (none on the production board either). Four swapped header balls are configuration dual-purpose pins, harmless after DONE but active during configuration: W18 CSI_B (MOSI), U19 RDWR_B (TX), V19 DOUT/CSO_B (RX, can drive during configuration) and E19 EMCCLK (SCL). U1's symbol bank grouping is now mixed (banks 14 and 16 are both 3.3 V; cosmetic).
6. **Availability to check before ordering**: AS4C32M16SB-7BIN (FBGA) and FT2232HQ. The HQ was dry when last checked; the fallback is an FT232H, which keeps JTAG but loses the second channel used for the UART.
