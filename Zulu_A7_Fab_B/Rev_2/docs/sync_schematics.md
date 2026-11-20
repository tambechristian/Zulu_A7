# Schematic sync from Zulu_A7_no_pmod Rev 2 (2026-11-20)

**Status (2026-11-20):** the sheets are updated, compiled in Altium with no errors and committed with the no-PMOD
sync. The schematic PDF and the Protel netlist were re-exported at 14:20. The PCB, PcbLib and rule changes are in
`docs/sync_altium_steps.md` ("Result").

The no-PMOD Rev 2 board (`Zulu_A7_no_pmod/Rev_2`, HEAD 427960e) began at 31df8a8 as a copy of this board with the Pmod
removed. Since then it has gained schematic changes that apply here too. This sync brings them across. It keeps this
board's Pmod (J1, R26-R33, nets JA* / PMOD-*), its JTAG holes JP3/JP4 at the east end, and its own sheet-3 deviations.

## What changed, and why

| Sheet | Change | Why | No-PMOD origin |
|---|---|---|---|
| 1 | **X4** JST B2B-PH-SM4-TB (top-entry) -> **S2B-PH-SM4-TB** (side-entry SMD). Changes LibReference / DesignItemId, description, DeviceName, MANF#, SPEC, NOTE and the footprint model `JST-S2B-PH-SM4-TB`. Pins and nets are unchanged. | The top-entry housing sat over U2's south pins. The side-entry header sits between X2 pins 30 and 31 with its opening to the south edge. Both boards place it the same way. | 3b1817d, e6d23c6 |
| 4 | **U2** FT2232HL/LQFP-64 -> **FT2232HQ/QFN-64**. Adds an **EP pin tied to GND** (power pin with HiddenNetName GND, a stub at (532,552)-(532,562) and a wire to the U2 GND bus at (512,552)). Also changes the footprint model `FT2232HQ-QFN64`, MANF# FT2232HQ-REEL, SPEC/NOTE/description and the visible label. The sheet title becomes "FT2232HQ, JTAG, CLOCK". | The board now uses the notchless QFN. DS_FT2232H section 8.1 requires EP to be grounded. | 3b1817d |
| 4 | **U10** 93LC46BT-I/SN (SOIC-8) -> **93LC46BT-I/MS (MSOP-8)**. Footprint model `MSOP-8_3X3_P0.65`. | Same die and pinout. The SOIC body collided with X2's header housing. | 3b1817d |
| 0, 2, 4 | **Stale notes:** block-diagram label FT2232HL -> FT2232HQ (sheet 0). The X2 text frame and the 41 X2 NOTE parameters (sheet 2). OriginDescription and the Q1 comment (sheet 4). | The old X2 frame still gave pins 9/10 and 29/30 as the landing neighbours (pre-Rev-2). It also named the B2B header, the bq24232 4.4 V rail and "THE PCB FOOTPRINT MUST BE REDRAWN". VU is the LTC3556 (U8) PowerPath output on this board too. | e6d23c6 |
| 3 | **16 SDRAM DQ series resistors R119-R134**: 22 ohm 0201 (R-US_SMALLR0201, footprint R0201, RC0201FR-0722RL). Each Dn becomes SDRAM-Dn (U3 side, pin 1) and Dn (U1 side, pin 2; the XDC/HDL name). Also adds a 5-line caption. | On reads, U3's full-drive DQ edges undershoot past the DS181 limit at U1's ball. U1, U3 and the DQ fan-out are the same copper on both boards. | 51ffba0..06d9f27 (ab48eb8 + 04819de layout) |
| 3, 4 | **Altium SI models**: U3 part 3 gets `AS4C32M16SB_7TCN` (Alliance IBIS 5.0, DQ full drive) with SI_INPUT/OUTPUT_MODEL on 57 pin parameters. U10 gets `93LC46B_I_SN_3V3` (Microchip IBIS 3.2, 3.3 V) on pins 1-4. | These are the models the no-PMOD SI analysis ran with. | 51ffba0 |

### Not ported, on purpose

- The no-PMOD **JP3/JP4 notes** describe a west-edge JTAG column (22ee1dc). They are not ported. This board keeps its JTAG holes at the east end.
- **U1's SI model `ARTIX7_ZULU_NOPMOD`** (sheet 5) is not ported. It was built for the no-PMOD pin-out.
- The **Pmod removal** on sheets 0 and 2 (the "Pmod Header" block, J1, R26-R33 and their wires/labels) and the NoERC markers of `no_pmod_noerc.py` are not ported.
- **Sheet 5 drawing layout.** The no-PMOD sheet 5 had a third filing pass (1166f8c). This board filed its own sheet 5 by net (75379ea). The difference is drawing-only and was outside this sync.
- **Altium re-save artefacts on the no-PMOD sheets.** These are the font-table renumbering, the re-keyed HiddenNetName / PinUniqueId IDs, DatafileCount / ModelDatafileEntity0 / ModelDatafileKind0 on 84 footprint records, Orientation/NotAutoPosition flags and four extra X3 PinUniqueId parameters. Altium writes these itself on the next save.
- The no-PMOD **intermediate X4 note** ("tapered PCB tab ... 3.70 mm beyond the Feather outline") describes an abandoned tab, so it was never written here.

### Deliberate differences from the no-PMOD sheets

- **U10 description.** It reads "was the SOIC-8 -I/SN until **2026-11-20**", the date the change happened on this board. The no-PMOD sheet says 2026-11-14.
- **R119-R134 hidden NOTE and caption line 3.** They point at `Zulu_A7_no_pmod/Rev_2/docs/dq_series_resistors.md`. This board has no `docs/dq_series_resistors.md`, and the SI study and the placement it justifies live in that file.
- **Sheet 3 keeps this board's own deviations:** U3's Comment/PART text stays centred, and the X3 caption keeps "PCB footprint DM3D-SF".
- **The sheet 2 X2 frame uses the no-PMOD text unchanged.** That text describes only X2, and X2 is identical on both boards: pins at x 1.27..59.69, landings at x 34.29..26.67 between pins 10/11 and 30/31, and four 1x10 strips. This board's Pmod J1 and JTAG JP3/JP4 lie further east (x 64-67) and are not mentioned. The frame is clipped to its rectangle (ClipToRect) and already holds 14 lines, so no line was added for them. The pin -> net map in the text was checked against this project's netlist.

## Scripts (in `tools/`; run from `Rev_2`, in this order)

All scripts derive their paths from their own location. They write only the FileHeader stream; the other streams are
identical on both boards. Each one refuses to write unless `backups/<sheet>.pre-sync` exists. Each also refuses
anything unexpected: an old value that differs, a UniqueID already in use, or a second run (checked after the
sync: all six refuse). Every script dry-runs unless given `apply`.

1. `x4_smd_tab_sch.py apply`: sheet 1, port of the no-PMOD script, writing the final X4 NOTE. Afterwards sheet 1's FileHeader is **byte-identical** to the no-PMOD sheet 1.
2. `u2_ft2232hq.py apply`: sheet 4, port of the no-PMOD script, including its ModelDatafileEntity0 fix. It reuses the no-PMOD EP record UniqueIDs. U2's subtree then equals the no-PMOD one, apart from the HiddenNetName/PinUniqueId IDs that Altium re-keyed there.
3. `u10_msop_sch.py apply`: sheet 4.
4. `stale_notes_sch.py apply`: sheets 0, 2 and 4. It only verifies sheet 1. It changes the Text field only, and scans every written text for no-PMOD-only phrases.
5. `dq_series_r_sch.py apply`: sheet 3. This is a record copy from the no-PMOD sheet 3; the inventory prototype was `proto_dq_r_fabb.py`. It deletes the 18 right-edge stubs, their 18 labels and the 2-line C3-C9 caption. It appends the 16 resistor subtrees (432 records), 34 wires, 34 labels and the 5-line caption. Its output is identical to the prototype's except the 17 doc-path texts.
6. `si_models_sch.py apply`: sheets 3 and 4. It appends the SI parameters under the matching pins and the SI implementation under the ImplList. The U3/3 and U10 subtrees then equal the no-PMOD ones, modulo the re-save artefacts above and U10's dated description.
7. `sync_sch_proof.py [--write]`: runs the proofs below. `--write` regenerates `docs/sync_schematics_records.txt`.

Helpers: `sync_sch_common.py` (I/O, record helpers, insert-with-OwnerIndex-renumbering, structural check) and
`sch_recdiff.py` (semantic record diff; `--norm` hides re-save artefacts). The netlister is
`Asar_feather/Rev_1/tools/sch_netlist.py`.

Backups are in `backups/zulu_a7_0..4.SchDoc.pre-sync` (git-ignored). Sheets 5 and 6 are untouched.

| Sheet | md5 before | md5 after | Records |
|---|---|---|---|
| zulu_a7_0 | d7504ffb | 3e9db238 | 422 -> 422 |
| zulu_a7_1 | 03d2b9ee | d6ee6375 | 1386 -> 1386 |
| zulu_a7_2 | d58a2c11 | 216b9dc6 | 13248 -> 13248 |
| zulu_a7_3 | d8f81377 | 32486952 | 17397 -> 17926 |
| zulu_a7_4 | 2f89b1ba | 7a1354a7 | 2351 -> 2366 |

## Proofs (`python tools/sync_sch_proof.py`: ALL CHECKS PASSED)

**Netlist, before -> after** (whole project, `sch_netlist.py`; before = the backups plus the untouched sheets 5/6):
219 -> 235 nets. The delta is exactly the following, and every other net keeps its name and pins:
- GND gains U2-EP.
- R119-R134 appear. No other part appears or disappears.
- Each Dn = {U1 ball, U3 DQ pin} splits into SDRAM-Dn = {U3 DQ pin, R(119+n)-1} and Dn = {R(119+n)-2, U1 ball}.
  For example, D0 = {R119-2, U1-V8} and SDRAM-D0 = {R119-1, U3-2}; D15 = {R134-2, U1-A15} and SDRAM-D15 = {R134-1, U3-53}.

**Netlist, after vs the no-PMOD HEAD** (227 nets): the two are identical once the Pmod is taken out here. That means
dropping J1 and R26-R33 and nets JA1-4/JA7-10 and PMOD-1-4/7-10. The 8 U1 balls that carry JA* here (C17, R19, U17,
U18, U19, V19, W18, W19) are unconnected single-pin nets on the no-PMOD sheets, as expected.

**Record diff, before vs after**: an alignment of record bodies without OwnerIndex. Every matched record's owner maps
onto the matched owner, and Weight equals the record count. No new duplicate UniqueIDs appear; sheet 1's pre-existing
duplicate BWLGLMAY is on both boards. Every changed, inserted and deleted record is listed in
`docs/sync_schematics_records.txt`:

| Sheet | Changed | Inserted | Deleted |
|---|---|---|---|
| 0 | 1: label POZQZCRY | 0 | 0 |
| 1 | 6: X4 component, DeviceName, MANF#, SPEC, NOTE, footprint model | 0 | 0 |
| 2 | 42: X2 frame RQLMHDNL + the 41 X2 NOTE parameters | 0 | 0 |
| 3 | 0 | 567: R119-R134 subtrees (432), 34 wires, 34 labels, 5 caption lines, U3/3 SI (57 pin parameters + 5 implementation records) | 38: 18 stubs, 18 labels, 2 caption lines |
| 4 | 17: title label, OriginDescription, U2 (component, DeviceName, DeviceSetName, label parameter, MANF#, SPEC, NOTE, Comment, footprint model), U10 (component, DeviceName, MANF#, Comment, footprint model), Q1 Comment | 15: U2 EP pin + HiddenNetName + PinUniqueId, 2 EP wires, U10 SI (5 pin parameters + 5 implementation records) | 0 |

**Record diff, after vs the no-PMOD HEAD** (`sch_recdiff.py --norm --ignore-font`):
- Sheet 1 is identical.
- Sheet 4 differs only in the JP3/JP4 notes and descriptions (not ported) and U10's date. This holds even without `--norm`.
- Sheet 3 differs only in the doc-path texts, the U3 centred text, the X3 caption, the sheet header (font table) and X3's four re-save PinUniqueId parameters.
- Sheets 0 and 2 differ only in this board's Pmod material.

**Texts:** no written or inserted text names the no-PMOD board, the west-edge JTAG column, a missing Pmod, 60.96 mm,
the B2B header, the 4.4 V rail or the FT2232HL. The exceptions are the U2 texts that compare the QFN with it ("Pins 1-64
match FT2232HL") and the doc path above. The PCBWay order number appears in no written text.

## Follow-ups (all done 2026-11-20; see `docs/sync_altium_steps.md`, "Result")

- **Altium.** Altium reloaded the five sheets from disk (no in-memory copy was saved over them); the project compile
  reported no errors. `Imported zulu_a7.PrjPcb/zulu_a7_fab_b_schematic.pdf` was re-exported (8 pages).
- **PCB (ECO).**
  - Parts: R119-R134 (R0201) came in, SDRAM-D0..D15 are new nets, and U2 gained pad EP on GND. U2 -> `FT2232HQ-QFN64`, X4 -> `JST-S2B-PH-SM4-TB` and U10 -> `MSOP-8_3X3_P0.65` need the no-PMOD PcbLib footprints.
  - Net class: SDRAM-D0..D15 were added to the SDRAM_DATA class (SyncRules).
  - Vias: under this board's rules, U2-EP and X4-2 got laser microvia stacks, not the no-PMOD through vias.
  - ECO cleanup: the deletion of the PCB-only net classes the ECO offered was unticked.
