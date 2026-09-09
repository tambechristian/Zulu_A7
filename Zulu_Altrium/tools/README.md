# Altium import checks

Scripts used to convert `zulu_a7.sch` (EAGLE 9.7 XML, written by Fusion 360)
into `Imported zulu_a7.PrjPcb` with Altium Designer's EAGLE Import Wizard,
and to check the result.  They edit the SchDoc files directly (OLE compound
documents, `FileHeader` stream of `|RECORD=n|Key=Value|` records), so close
the project in Altium before running the two fix scripts.

    pip install olefile pywin32

* `verify_import.py zulu_a7.sch "Imported zulu_a7.PrjPcb"` - every EAGLE
  part, gate, supply symbol and named net has its Altium counterpart.
* `fix_text_orientation.py <SchDoc...>` - EAGLE draws R180/R270 text
  readable; Altium draws Orientation 2/3 upside down.  Turns them into
  0/90 with mirrored justification, so anchors and text boxes stay put.
* `fix_labels.py <this folder> "Imported zulu_a7.PrjPcb"` - the label
  placements adjusted after reviewing the Smart PDF export (see docstring).
* `fix_gate_labels.py <this folder> <SchDoc...>` - the one-pin-per-gate
  parts (X2, U3, U4, U1) show their gate names through EAGLE's >GATE text;
  the importer gives every such label OwnerPartId=1, so Altium hides all but
  one per part.  Re-owns each label to its gate.
* `add_noerc.py <this folder> "Imported zulu_a7.PrjPcb"` - No-ERC markers on
  the nine pins that are open on purpose (the eight GTP balls the sheet
  marks "float per UG482", and the USB ID pin X1-4).
* `fix_pin_types.py <this folder> "Imported zulu_a7.PrjPcb"` - the EAGLE
  library types the supply/ground pins of U2, U3, U4, U10 and all of X2's
  pins as "io"; makes them Power and Passive so the ERC pin-type rules mean
  something.
* `swap_vcc3v3_to_sw1.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"` -
  the 2026-09-06 design change: VCC3V3 onto the LTC3569's 1.2 A channel
  (SW1) and VCC1V0 onto SW3, by swapping the two rail labels after L1/L3,
  the R65/R66 and R71/R73 divider values and the EN1/EN3 wiring. Applied
  once; the docstring is the change record. Not reflected in zulu_a7.sch
  (EAGLE), which is now history.
* `sc189_power_section.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"` -
  the 2026-09-06 regulator change: the LTC3569 section (U8, dividers, the
  EN_BIAS network) replaced by three fixed SC189 bucks U5/U6/U7 with L1-L3
  at 1.5 uH, C80/C82/C84 as 22 uF outputs, new C147-C149 10 uF inputs, C78
  at 10 uF. Rewrites the sheet record by record; run once, on the sheet as
  committed in bedd4a7 (its delete list is keyed to that file). SC189 pin
  numbers (1 VIN, 2 GND, 3 EN, 4 VOUT, 5 LX) were checked against the Semtech
  datasheet (Datasheet/SC189-datasheet 08 27 10.pdf, p2 and p14) on 2026-09-06.
* `fix_sc189_bom.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"` -
  follow-up to the above: the hidden MANF#/SPEC parameters that the value
  edits had left stale (L2/L3 still named the 3.3/2.2 uH inductors, C82/C84
  a 10 uF part under a 22 uF value, C78 the 22 uF part under 10 uF) and the
  three input caps moved to a 10 V 0805 part (GRM21BR61A106KE19L) because a
  6.3 V 0603 is under the datasheet's 4.7 uF at 5 V. Keyed by designator,
  safe to re-run.
* `x3_dm3d_sf.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_3.SchDoc"` -
  2026-09-06: X3 (microSD) from the Hirose DM3AT-SF-PEJM5 push-push socket to
  the DM3D-SF push-pull one (HRS 609-0025-8, DM3 catalog p9 in
  Datasheet/DM3AT-SF-PEJM5.pdf). Same eight contacts; the two 'G1,3'/'G2,4'
  multi-pad shell pins become G1-G4 on the GND bus; new pins A/B for the
  card-detect switch, left open with No-ERC markers; footprint model renamed
  DM3D-SF (to be drawn at the PCB stage). Refuses to run twice.
* `btn_pts810.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"` -
  2026-09-08: BTN from the PTA-142 (no maker, no distributor) to the C&K /
  Littelfuse PTS810SJM250SMTR LFS (4.2 x 3.2 mm J-lead, 1.6 N). Parameters,
  an inserted MANF parameter (OwnerIndex renumbering) and the footprint model
  name PTS810; pins 1,2 / 3,4 already match the datasheet's 1-2 / 3-4 pairing.
  Refuses to run twice.
* `ld0_east1616.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"` -
  2026-09-08: LD0 from the Victory VS NRD8 (maker-direct only) to the Everlight
  EAST1616RGBA8 (19-337/R6GHBHW-A01/2T), the same body, pads and arrangement
  with different pad numbers: pins renumbered 1/2/3 -> 2/4/6 (cathodes) and
  4/5/6 -> 1/3/5 (anodes), nets untouched, footprint model EVERLIGHT-19-337.
  Refuses to run twice.
* `x2_sullins.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"` -
  2026-09-08: the ZULU-CONN pin field X2 gets MANF, MANF#, SPEC and NOTE
  (Sullins PRPC024SAAN-RC + PRPC009SAAN-RC + PRPC011SAAN-RC, one of each per
  board) inserted into all 45 placed gates with OwnerIndex renumbering;
  comment and footprint ZULU-DIP37 unchanged. Refuses to run twice.
* `jp_dns.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` - 2026-09-08:
  JP3/JP4 (bare JTAG holes) get DNS = Yes and a SPEC line, inserted after
  their NOTE with OwnerIndex renumbering; bom_audit lists them as DNS
  positions instead of parts. Refuses to run twice.
* `bom_audit.py > docs/component_validation.md` - component and BOM validation
  (2026-09-06): BOM from the sheets; FPGA balls and power tree against AMD's
  CPG236 pinout file; FT2232H, SDRAM, flash, EEPROM, oscillator, USB, RGB LED
  and resistor-array pads against their datasheet tables; EAGLE package
  geometry against the datasheet land patterns; capacitor voltage and
  resistor power derating from the nets; a dated Digi-Key snapshot of
  status/stock/price and a second-source table typed in from the lookups.
* `apply_bom_substitutions.py <this folder> "Imported zulu_a7.PrjPcb"` - the
  part-number replacements the audit recommends (obsolete, mistyped and dry
  parts), NOT applied; edit the table, run with the project closed, re-run
  the audit. Rounds applied so far: 2026-09-07 (44 components), 2026-09-08
  (GRM188R61C475KE11D, ECS-3225SMV, the 4.7 uF 0402) and 2026-09-08 U3
  AS4C32M16SB-6TIN -> AS4C32M16SB-7TCN (the -6 grade is dry until October;
  U3 has no SPEC parameter, so the timing text is appended to its NOTE),
  and 2026-09-08 L4-L7 BLM18PG601SN1D (a number Murata never made) ->
  BLM18KG601SN1D.
* `power_budget.py [--fpga-int mA --fpga-io mA --header mA ...]` - rail-by-rail
  power budget from the schematic and the datasheets; writes markdown
  (docs/power_budget.md is its default output). The FPGA dynamic currents
  are assumptions until Vivado's report_power replaces them.
* `erc_summary.py erc.txt` - groups a Messages-panel export (right-click,
  Save...) by message kind.
* `eagle_netlist.py zulu_a7.sch eagle.json` then
  `compare_netlists.py "Imported zulu_a7.PrjPcb/Project Outputs for zulu_a7/zulu_a7.NET" eagle.json`
  - connectivity of the Altium project (Design > Netlist For Project >
  Protel) against the EAGLE schematic, pad by pad.  Last result:
  190 components, 175 nets, 799 pads, identical names, no differences.

Import Wizard settings that matter: untick "Do not translate hidden net
names" (else 16 nets named without a label lose their names).  Pins that
own several pads in EAGLE (BTN 1/2 and 3/4, X1 5+shell, X3 G1/G3 and
G2/G4) become single Altium pins named "1,2" etc.; split them before
matching to the imported board.
