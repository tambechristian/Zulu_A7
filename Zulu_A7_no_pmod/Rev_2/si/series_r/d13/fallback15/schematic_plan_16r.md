# U3 DQ series resistors: schematic plan (Zulu_a7_no_pmod Rev 2)

2026-11-13. **This is a plan only.** No SchDoc, PcbDoc, PcbLib or Altium document was opened for writing. Every number below
comes from a file read with olefile. The read-only probe that prints them is `si/series_r/schematic_probe.py`, and its
output is saved in `si/series_r/schematic_probe.txt`. Each fact names its source. Where something is assumed, the text
says so.

## 0. Recommendation summary

| Item | Proposal |
|---|---|
| Sheet to edit | `zulu_a7_3.SchDoc` only. Sheet 5 (U1) and every other sheet stay as they are. |
| Names kept | **D0..D15 stay on the FPGA side.** The XDC, the Verilog top level and U1's IBIS do not change. |
| New net names (U3 side) | **SDRAM-D0 .. SDRAM-D15** |
| Designators | **R119..R134** (R119 = D0 ... R134 = D15) |
| Part | Clone of **R24** (sheet 4): `R-US_SMALLR0201`, footprint `R0201`, Yageo thick film. Value 22 ohm, MANF# `RC0201FR-0722RL` (the MPN is built from Yageo's code pattern and its stock is not checked; see §3.4). |
| Drawing | A block of 2 columns x 8 rows in the empty window x 45..540, y 340..698 of sheet 3 (0 objects in it, measured), plus a 2-line caption. The 16 U3 stub labels are renamed in place from `Dn` to `SDRAM-Dn`. No U3 record and no wire moves. |
| Edit method | Append-only, following `Zulu_Altrium/tools/stitch_caps.py` (which added C155-C159 to this same sheet). One existing field changes in each of 17 records: 16 label `Text` values plus the header `Weight`. |

## 1. How D0-D15 connect today (measured)

**Net scope.** `Zulu_a7_no_pmod.PrjPcb` has `HierarchyMode=0` (Automatic). None of the seven sheets has a port
(RECORD=18), a sheet symbol or a sheet entry (RECORD=15/16). Automatic mode therefore makes **net labels global**. The
board confirms this: D0-D15 are joined only by net labels on sheet 3 and on sheet 5, and the PcbDoc has one net per bit
(`Nets6`: D0..D15 present, 165 nets). Source: the `dump.py` survey (summarised in the probe) and `Nets6/Data`.

**Sheet 3 (`zulu_a7_3.SchDoc`, "Memory"). U3 = AS4C32M16SB-7TCN, `LibReference=SDRAM-X16-ALLIANCE-512M`.**
- U3 is drawn as an EAGLE pin-list symbol with 55 gates. Each pin is its own placed part (RECORD=1 with `CurrentPartId`),
  and every instance carries all 54 pins, of which only the pin with `OwnerPartId == CurrentPartId` is drawn. The body is
  a free rectangle (lines x 775..895, y 797..1077).
- Each DQ pin ends in a 10-unit wire stub to a net label. The left stubs run 745..755 and the right stubs 915..925.

| Net | U3 pin | pin hot end | label record # | label at | Justification |
|---|---|---|---|---|---|
| D0 | 2 | (755,1057) | 17156 | (745,1057) | 2 (text grows left) |
| D1 | 4 | (755,1037) | 17158 | (745,1037) | 2 |
| D2 | 5 | (755,1027) | 17172 | (745,1027) | 2 |
| D3 | 7 | (755,1007) | 17174 | (745,1007) | 2 |
| D4 | 8 | (755,997) | 17176 | (745,997) | 2 |
| D5 | 10 | (755,977) | 17178 | (745,977) | 2 |
| D6 | 11 | (755,967) | 17180 | (745,967) | 2 |
| D7 | 13 | (755,947) | 17182 | (745,947) | 2 |
| D8 | 42 | (915,947) | 17184 | (925,947) | 0 (text grows right) |
| D9 | 44 | (915,967) | 17186 | (925,967) | 0 |
| D10 | 45 | (915,977) | 17160 | (925,977) | 0 |
| D11 | 47 | (915,997) | 17162 | (925,997) | 0 |
| D12 | 48 | (915,1007) | 17164 | (925,1007) | 0 |
| D13 | 50 | (915,1027) | 17166 | (925,1027) | 0 |
| D14 | 51 | (915,1037) | 17168 | (925,1037) | 0 |
| D15 | 53 | (915,1057) | 17170 | (925,1057) | 0 |

All labels use FontID 3 (Courier New 8). The record numbers are list indices in the file as it is today, header = 0.
**Re-find the labels by Text and location; do not reuse these indices**, because any Altium save renumbers records.

**Sheet 5 (`zulu_a7_5.SchDoc`, "FPGA Connections") holds U1's SDRAM bank.** Its labels D0..D15 sit at x 715, y 462..312
and join U1 balls V8 V7 W7 W6 U5 W5 V5 U4 L1 K3 K2 J1 J3 H1 A14 A15 (D0..D15 in that order). That is **16/16 identical**
to `si/vivado/zulu_a7_no_pmod.xdc` lines 56-71 and to `vivado/zulu_a7_pins.xdc`. No other sheet has a D-label.

**Why the FPGA side keeps D0..D15.** The XDC ports are the net names (`get_ports {D0}` ... `{D15}`, plus line 111
`DRIVE 8 SLEW SLOW` on D0-D15). `si/vivado/zulu_a7_no_pmod_top.v` declares 16 `inout wire Dn` ports, and the Vivado IBIS
`si/vivado/zulu_a7_no_pmod_u1.ibs` names the signals D0..D15 on those balls. With U1 still on D0..D15, none of these
files changes, and neither does `ibis.tcl` nor the parent-board `vivado/` folder. (Aside for SI scripts: the U1 IBIS also
lists unused ball R19 under the pin-function alias "D15". Key U1 lookups by ball, not by signal name.)

**PcbDoc today** (`Classes6`, `Rules6`): net class `SDRAM_DATA` = D0..D15. The rules `Width_SDRAM` and
`Clearance_SDRAM_INNER` are scoped by `InNetClass('SDRAM_DATA') Or ...SDRAM_ADDR Or ...SDRAM_CTRL`, and no rule names an
individual D net.

**Working-copy state (important).** `zulu_a7_3/4/5.SchDoc` differ from git HEAD (22ee1dc). Altium re-saved them on
2026-11-12 18:21-18:23, and each gained exactly one `RECORD=45 ModelType=SI` (sheet 3: U3 `AS4C32M16SB_7TCN`; sheet 4:
U10 `93LC46B_I_SN_3V3`; sheet 5: U1 `ARTIX7_ZULU_NOPMOD`) together with its RECORD=41/46/48 entries. Net labels and power
ports are identical to HEAD, the parameter UniqueIDs were re-keyed, and the font tables were renumbered (sheet 3
FontIdCount 6->5, sheet 5 10->8). Measured by a record diff against `git show HEAD:...`. **The user should decide
whether to commit these SI-model edits before the resistor edit is applied**, so that the resistor change is its own
reviewable diff.

## 2. Net names on the SDRAM side: SDRAM-D0 .. SDRAM-D15

- This follows the project's own prefix for SDRAM-side copies of bus names: `SDRAM-CLK` and `SDRAM-CS#` already exist.
  It also follows the `-` separator style used everywhere (`FLASH-D00`, `SD-DAT0`, `CLK-12M-FT`).
- **`tools/bom_audit.py` passes unchanged with this name and fails with the alternatives.** `sdram_ok()` (line 111)
  removes `^SDRAM[-_]` from the pad's net and compares the rest with U3's pin function (DQn -> Dn). `SDRAM-D0` reduces to
  `D0`, which matches. `D0-SDRAM` (the suffix style of `CLK-12M-FT`/`CLK-12M-FPGA` around R24/R25) and `SDRAM-DQ0` (which
  reduces to `DQ0`) would both be reported as wrong pads.
- Collision check: none of SDRAM-D0..15 appears among the 164 label and port texts on the seven sheets or among the 165
  PCB nets. Because labels are global (§1), this check has to be repeated right before applying the edit.
- Vivado never sees these names, since no U1 ball sits on them.

## 3. Parts

### 3.1 Designators: R119-R134
The schematic and the PcbDoc each hold the same 51 R designators. The highest is R118, and R119..R134 are unused
everywhere (probe output). The gaps are left alone on purpose:
- R104-R106 and R109-R112 are in `STALE_REFS` of `tools/generate_jlcpcb_assembly.py`, so reusing them would fail the
  release check.
- R26-R33 were the Pmod's resistors, deleted by `tools/no_pmod_schematic.py`. Reusing them would collide with Rev 1 /
  Fab B documents.

| Ref | Net (pin 1, U1 side) | Net (pin 2, U3 side) | U3 pin |
|---|---|---|---|
| R119..R126 | D0..D7 | SDRAM-D0..SDRAM-D7 | 2,4,5,7,8,10,11,13 |
| R127..R134 | D8..D15 | SDRAM-D8..SDRAM-D15 | 42,44,45,47,48,50,51,53 |

### 3.2 Template part: R24 (sheet 4)
R24 and R25 are the board's existing 33 ohm 0201 series terminations (CLK-12M-SHARED -> CLK-12M-FT / CLK-12M-FPGA).

| Field | R24 today | New R119-R134 |
|---|---|---|
| LibReference / DesignItemId | R-US_SMALLR0201 | same |
| SourceLibraryName | rcl.IntLib | same |
| ComponentDescription | "RESISTOR, American symbol, small 2-zigzag variant (sheet 2 only)" | same, or drop the stale "(sheet 2 only)" |
| PartCount / AllPinCount | 2 / 2 | same |
| Implementation (RECORD=45) | ModelName=R0201, ModelType=PCBLIB, DatafileCount=1, ModelDatafileEntity0=R0201 | same |
| PCB footprint lib | zulu_a7.PcbLib (`Components6` SOURCEFOOTPRINTLIBRARY) | same |
| Comment (visible) | 33 | **22** |
| MANF (hidden) | Yageo | Yageo |
| MANF# (hidden) | RC0201FR-0733RL | **RC0201FR-0722RL** |
| SPEC (hidden) | thick film +-1%, 1/20W, 0201 | same |
| DeviceName / LibraryName / DeviceSetName / GateName_1 / SymbolName_1 (hidden) | R0201 / rcl / R-US_SMALL / G$1 / R-US_SMALL | same |
| NOTE (hidden) | none | **add** (text below) |
| Pin HiddenNetName (RECORD=41 under each pin) | CLK-12M-FT / CLK-12M-SHARED | **omit** (see trap 6) |

Symbol geometry (R24 measured): the body is at Location (cx,y). Pin 1's hot end is at (cx-10,y) and pin 2's at
(cx+10,y), with PinLength 0. The designator sits at (cx-7.5,y+5.9) and the comment at (cx-7.5,y-13). R24 uses only
FontIDs 1 and 3, and fonts 1 and 3 are identical on sheets 3 and 4 today (Times New Roman 10, Courier New 8), so the
cloned records need no font remap. **Re-check this at apply time**, because Altium renumbers font tables on save.

Proposed NOTE text: "SERIES TERMINATION AT THE SDRAM, NOT AT THE FPGA. U3 has no drive-strength register; its full-drive
DQ edges undershoot to -0.85..-1.05 V at U1's ball on reads (ngspice + IBIS, docs/si_analysis.md). A resistor right at
U3's DQ pad brings the ball to -0.35 V (17 % of the DS181 Table 4 budget at 22 ohm). Place each one on the Bottom
beside its U3 pad, with the stub from the pad as short as the layout allows; moving it toward U1 undoes the fix. D0-D15
(U1 side) keep the XDC names; SDRAM-D0..15 are the U3-side stubs."

### 3.3 Alternatives that keep a template in the project (decided by the PCB-side plan)
- **0402**: clone R80 (sheet 2, `R-US_SMALLR0402`, footprint R0402, MANF# `RC0402FR-0733RL` -> `RC0402FR-0722RL`;
  sheet 2's font table differs from sheet 3's, so FontIDs would need remapping). Bigger pads, easier rework.
- **4-element arrays** (4 parts instead of 16): clone R34 (sheet 3, `RES4742`, CTS 742C083 = 4 x 0603 elements, 4
  gates, footprint 742C083). The 22 ohm MPN would be `742C083220JP` per CTS's code pattern (assumed, not verified). The
  arrays are 5 % parts and the body is 1206-sized, so whether they fit under U3 is a layout question.
- **Value**: 15 ohm `RC0201FR-0715RL` (30 % of budget), 22 ohm `RC0201FR-0722RL` (17 %), 33 ohm `RC0201FR-0733RL`
  (15 %) (percentages from docs/si_analysis.md). **33 ohm adds no BOM line**: it merges into the existing
  `RC0201FR-0733RL` line (R24, R25). 22 ohm adds one new line.

### 3.4 MPN status
`RC0201FR-0722RL` follows the same Yageo RC-series code as `RC0201FR-0733RL` / `RC0201FR-0710KL` already on the BOM. It is
**not** in `LCSC_CODES` of the generator, and its stock and lifecycle have not been checked in this planning step.

## 4. Where they go on sheet 3

Sheet 3 is portrait (`CustomX=1063`, `CustomY=1343`, `WorkspaceOrientation=1`), and the drawing frame is free lines
x 40..1020, y 92..1302. The window **x 45..540, y 340..698 holds 0 objects** (probe, frame excluded). It lies between the
microSD notes (y >= ~700), the stitching caps C155-C159 (y 280..320) and the U3 decoupling note (x 546..1019,
y 372..420). On the PDF this is the empty left-middle area.

Layout (sheet units = 10 mil, snap grid 10):
- Column A, R119-R126 (D0..D7): cx = 150. Column B, R127-R134 (D8..D15): cx = 390.
- Row k = 0..7: y = 640 - 40k, giving 640, 600, 560, 520, 480, 440, 400, 360. The 40-unit pitch keeps a row's comment
  (y-13) clear of the next row's designator (y-34+11).
- Each row draws:
  - the resistor at (cx,y);
  - a wire (cx-30,y)-(cx-10,y) and the label `Dn` at (cx-30,y), Justification=2, FontID 3;
  - a wire (cx+10,y)-(cx+30,y) and the label `SDRAM-Dn` at (cx+30,y), Justification=0, FontID 3. Wire attributes are
    copied from the sheet's existing stubs (`LineWidth=1|Color=...`, taken from record 17155).
- Text extents, assuming Courier New 8 at 0.6 em = about 6.7 units per character: column A runs about x 105..234 and
  column B about x 333..480, so both stay inside x 45..540.
- Caption: RECORD=4, FontID 3, two lines at (60,684) and (60,672):
  "U3 DQ SERIES RESISTORS R119-R134 (22 ohm): Dn = U1 side (XDC names), SDRAM-Dn = U3 side." /
  "Place each at its U3 DQ pad on the Bottom -- see NOTE, docs/si_analysis.md."
- **At U3:** set `Text` on the 16 labels in the table of §1 from `Dn` to `SDRAM-Dn`. Positions and justification stay
  the same.
  - Left labels grow leftward to about x 691; the window x 670..744, y 935..1068 is empty.
  - Right labels grow rightward to about x 985, inside the frame at 1020; the window x 926..1019, y 935..1068 is empty.

An inline alternative was rejected: putting each resistor in the U3 stub itself would need the D-rows (10-unit pitch)
staggered into two columns to keep designators readable, and every stub wire would have to move. The block above
moves nothing and reads like the sheet-4 CLK-12M terminations.

## 5. Record recipe (for the later apply script; not written now)

Model it on `Zulu_Altrium/tools/stitch_caps.py`, the precedent for this exact sheet, and use the helpers in
`Asar_feather/Rev_1/tools/schdoc.py` (or `Zulu_Altrium/tools/fix_text_orientation.py`).
1. Back up `zulu_a7_3.SchDoc` to `Rev_2/backups/zulu_a7_3.SchDoc.pre-series-r`. `Rev_2/backups` is gitignored, and
   `tools/rev2_x2_sch.py` does the same.
2. Read `FileHeader`, `split()`, and assert all of the following:
   - `join(R) == data`;
   - every header byte 3 is 0 (no binary records);
   - Weight equals len-1;
   - every record ends in NUL;
   - R119..R134 and SDRAM-D0..15 are absent;
   - the window is empty;
   - template FontIDs are equal on sheets 3 and 4.
3. Template = R24's subtree from sheet 4: 28 records, `schdoc.subtree()`. Drop its two `HiddenNetName` RECORD=41s,
   leaving 26 records.
4. For each of the 16 parts:
   - shift the coordinates by (cx-427, y-272) (`stitch_caps.shift`);
   - give every record a fresh 8-letter `UniqueID`;
   - set each pin's `PinUniqueId` Text equal to that pin's new UniqueID (the invariant holds 3126/3126 on sheet 3 and
     278/278 on sheet 4 today);
   - remap `OwnerIndex` to the appended positions;
   - set the Designator Text, Comment = 22 and MANF# = RC0201FR-0722RL;
   - append NOTE as a hidden RECORD=41 (the `stitch_caps` form);
   - append the 2 wires and 2 labels.

   This adds 16 x (26 + 1 + 4) = 496 records, plus 2 for the caption: 498 in total.
5. Set the Text of the 16 U3 labels (found by Text + location, not by index). Use `set_field`, which handles a
   `%UTF8%Text` key; none was seen on these labels.
6. Set the header `Weight = len(out) - 1`, `write_stream`, read back and assert byte equality, then run a `verify()` that
   re-derives connectivity:
   - each `SDRAM-Dn` reaches exactly U3's pin and Rxxx pin 2;
   - each `Dn` on sheet 3 reaches only Rxxx pin 1;
   - sheet 5 is untouched;
   - UniqueIDs and PinUniqueIds are distinct, and all owners are valid.
7. In Altium: reopen the project → Compile → read Messages (ERC is not scriptable) → export a Protel netlist and
   diff it against one taken before the edit. The expected diff is 16 new components, 16 new nets and 16 U3 pins moved
   from Dn to SDRAM-Dn; everything else must be identical. That is the same proof used for the sheet-1 cleanup.

## 6. Traps when editing these SchDocs by script, and how the existing tools handled them

| # | Trap | Handled by / evidence |
|---|---|---|
| 1 | Each record is `[2-byte LE length][2 header bytes][|KEY=val...]` and must end in **NUL**. A missing NUL corrupts the file. | `schdoc.py` docstring; `stitch_caps.verify` asserts `endswith(b'\x00')`; `no_pmod_noerc.py` appends `+ b'\x00'`. All 7 sheets: 0 records without NUL today. |
| 2 | **Header `Weight=` is the record count Altium reads.** Records appended past it vanish silently. | memory "SchDoc header Weight"; `no_pmod_schematic.run` asserts `Weight == len-1` before and rewrites it after; `stitch_caps`, `no_pmod_noerc` rewrite it. |
| 3 | `OwnerIndex=k` means list index k+1 (the header is 0). Deleting or inserting records renumbers every later owner. | `schdoc.delete()` / `no_pmod_schematic.run` renumber; `stitch_caps` is **append-only** so nothing moves. Use append-only. |
| 4 | Duplicate `UniqueID` / `PinUniqueId` from cloning. | `stitch_caps.new_uid()` regenerates each one. An earlier careless clone left 16 duplicates on sheet 4 (stitch_caps comment). Today the duplicate UniqueIDs are 0 on sheets 0 and 2-6, and **1 pre-existing on sheet 1** (not ours). |
| 5 | **Altium saves re-key parameter UniqueIDs and renumber font tables.** | memory; measured in the working copy vs HEAD (sheet 3 FontIdCount 6->5, sheet 5 10->8 with FontIDs remapped). So verify by connectivity and text, never by bytes, and re-check the template's FontIDs against the target sheet at apply time. |
| 6 | EAGLE-import `HiddenNetName` params under pins. | `stitch_caps.py` and `ft_vcore_caps.py` drop them and draw explicit wires and labels ("the one that demonstrably produced the right nets"). U3's own visible pins all carry `HiddenNetName=A0` and the netlist is still correct, so Altium ignores it on visible pins, but clones should not rely on that. |
| 7 | Binary records (header byte 3 != 0). | `no_pmod_schematic.run` asserts none. 0 on all sheets today. |
| 8 | Record bodies are limited to 65,535 bytes (2-byte length). | Keep NOTE texts short. |
| 9 | **Altium must not hold the sheet open.** Its later save overwrites the scripted file, and `STGM_SHARE_EXCLUSIVE` fails on a locked file. | `no_pmod_schematic.py` docstring "sheets closed in Altium". Close the project (or at least sheet 3), write, then reopen. |
| 10 | A malformed SchDoc makes Altium spin and ignore input. | memory (Altium desktop control). Keep the backup from step 1 and use the `History/` zips. |
| 11 | Multi-gate U3: every gate instance carries all 54 pins. | Do not touch U3's records at all; only the 16 free labels change. |
| 12 | Labels are global (§1), so a new name that equals an existing one anywhere shorts two nets. | Collision check in the probe; repeat it at apply time. |
| 13 | Bash collapses `\\`. | memory; use forward slashes in paths. |
| 14 | ECO (Design > Update PCB) also offers to **delete the 10 PCB-only net classes and the USB diff pair**. | memory (Altium desktop control): untick them. The X2 re-net needed a save/close/reopen and an ECO preview as the sync check (memory, X2 power pins). |

## 7. Downstream files that change (or do not)

| File | Change |
|---|---|
| `Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc` | the edit above |
| `Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc` | ECO from the schematic: 16 R0201 components and 16 nets SDRAM-D0..15; U3 pads 2,4,5,7,8,10,11,13,42,44,45,47,48,50,51,53 move to SDRAM-Dn. **The ECO re-nets pads, not copper**: the existing U3-pad stubs and vias stay on Dn and will show as shorts or unrouted until the PCB plan re-routes pad -> R -> via. Add SDRAM-D0..15 to class **SDRAM_DATA** (32 members) so `Width_SDRAM` and `Clearance_SDRAM_INNER` cover them, or add a class to both rule scopes. The per-sheet component class `zulu_a7_3` gains R119-R134 if the ECO's class option is on. |
| `zulu_a7.PcbLib` | none: footprint R0201 already exists (R24 uses it from this lib) |
| `si/vivado/zulu_a7_no_pmod.xdc`, `zulu_a7_no_pmod_top.v`, `zulu_a7_no_pmod_u1.ibs`, `ibis.tcl`; `vivado/zulu_a7_pins.xdc` | **none** (U1 stays on D0..D15) |
| `tools/generate_jlcpcb_assembly.py` | It reads the BOM from the schematics (`bom_audit.load_components`) and placements from the PcbDoc, and draws its own assembly PDFs, so the 16 parts flow in automatically: +1 BOM line at 22 ohm (0 lines at 33 ohm), +16 CPL rows (SMT) and +16 refs on the Bottom drawing. Update the docstring md5 / RELEASE_DATE, and optionally add a `PCBWAY_LINE_NOTES` entry ("R119-R134 sit beside U3 on the Bottom"). No `LCSC_CODES` entry is needed in PCBWay mode. The no_pmod release has **not been generated yet**: `assembly/` still holds the `Zulu_A7_Fab_B_Rev_2_*` copies. |
| PCBWay BOM / CPL / notes / zip | regenerate with the generator after the layout (not before) |
| `tools/bom_audit.py` | no code change (§2). It needs a fresh Protel netlist at `Project Outputs for Zulu_a7_no_pmod/Zulu_a7_no_pmod.NET`, which **does not exist today**. |
| `si/spice/bus_sim.py`, `fieldsolve.py`, `lines.json` | `bus_sim` builds one net's graph with the U1 and U3 pads on it (line 179). After the change, Dn has U1 + R pad and SDRAM-Dn has U3 + R pad, so the graph has to join the two nets through a resistor element at its real place. That replaces `ZULU_RSER` at the pin. Then re-run the read study on the routed board. |
| `si/altium_si/` (copies of all 7 SchDocs + `Zulu_a7_no_pmod_SI.PcbDoc`) | stale copies: re-copy if the Altium SI flow is re-run; the new resistors need an Altium SI "Resistor" model (value 22) |
| `Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod_schematic.pdf` | re-print (already older than the 18:21 sheet saves) |
| fabrication release (`tools/package_fabrication_release.py`, Gerbers) | after the layout |
| docs | `docs/si_analysis.md` (close the open item), a new layout doc, MEMORY |

## 8. Decisions left to the user
1. Value: 22 ohm as proposed, or 33 ohm (no new BOM line, 15 % vs 17 % of budget).
2. Package: 0201 (template R24), 0402 (R80) or 4 x 742C083 arrays (R34). This depends on the PCB-side room under U3.
3. Commit the pending SI-model edits in sheets 3/4/5 first, or fold them into the resistor commit.
4. Net names `SDRAM-Dn` (recommended, passes `bom_audit` as is) or another style (then `sdram_ok()` needs an edit).
