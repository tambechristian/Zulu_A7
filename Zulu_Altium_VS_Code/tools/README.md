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
* `x2_lipo_corner.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09: room for
  the LiPo connector at the right-hand end of X2. Sheet 2: +5V-INPUT (pad 44)
  with D2/D3, VEXT and GND5 (pad 23) deleted; +3.3V2/GND3 swapped with
  CHAN12/CHAN13 (pads 2/3 <-> 25/26) as a net-label, GATE-label and GateName
  swap; the two dead sub-parts removed from all 43 gate copies and parts
  renumbered 1-43 (PartCount 44, AllPinCount 42); displayed pins 2/3 retyped
  passive and 25/26 power; MANF#/SPEC/NOTE and the text frame rewritten for
  the split bottom row (PRPC020 + PRPC002). Sheet 1: charger note updated.
  Verifies the result and refuses to run twice. Its sub-part deletion also took the
  seven catalogue parameters of two copies whose serial OwnerPartId was 35 or 45
  (found by the review workflow); `x2_restore_params.py` put them back.
* `x2_restore_params.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"` -
  2026-09-09: re-appends DeviceName/LibraryName/DeviceSetName/MANF/MANF#/SPEC/NOTE
  to any X2 gate copy missing them, cloned from a healthy copy.
* `x2_jst_gap.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09, second pass:
  GND3 deleted, the bottom row closed up and re-numbered by position (23 RST#,
  24 +3.3V, 25-27 CHAN14-16, 28-30 empty for the LiPo header, 31-44 CHAN17..
  ANALOG-IO1), gate copies/wires/labels moved to the rows of their new pads,
  designators remapped in all 42 copies, sub-parts renumbered 1-42, catalogue
  parameters exempt from the sub-part deletion; MANF#/SPEC/NOTE and the text
  frame rewritten (PRPC007 + PRPC014 on the bottom row); U8 NOTE on sheet 1
  loses its D2 sentence. Verifies rows against pad numbers; refuses to run twice.
* `x2_drop_3v3.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09, third pass:
  +3.3V2 (pad 24) deleted, its position left empty like the LiPo gap; sub-part
  removed from all 41 copies and parts renumbered 1-41 (PartCount 42,
  AllPinCount 40); no pin slides, so the only netlist effect is X2-24 leaving
  VCC3V3. MANF#/SPEC/NOTE and the text frame rewritten (bottom row now 1x3 +
  1x3 + 1x14). The header takes 3.3 V from pad 17. Refuses to run twice.
* `x2_renumber_40.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09, fourth
  pass: CHAN14-16 slide one position right into the hole +3.3V2 left, so the LiPo
  landing widens to four positions and matches the USB landing (12.70 mm between
  neighbouring pin centres, 11.176 mm clear); the field is then renumbered 1-40
  straight through, skipping both landings. Designators remapped in all 41 gate
  copies, three gate copies with their wires and labels shifted, MANF#/SPEC/NOTE
  and the text frame rewritten (1x6 + 1x14 on the bottom row). Connectivity is
  untouched: the netlist differs only in X2 pad names. Refuses to run twice.
* `x2_move_landing.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09,
  fifth pass: CHAN17-19 (pins 27-29) slide four positions towards the corner, so
  the LiPo landing moves to between pins 29 and 30, on the same four x values as
  the USB landing above it, and the two rows become mirror images (9 + landing +
  11 each). Pin numbers do not move, so the exported netlist is byte-identical;
  only geometry, MANF#/SPEC/NOTE and the text frame change (strips become 2x 1x9
  + 2x 1x11). Refuses to run twice.
* `sc189_pin_ids.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"` -
  2026-09-09: the fifteen pins of U5, U6 and U7 all carried one UniqueID
  (PDYAEPSY, from cloning a pin record in sc189_power_section.py); each gets a
  fresh one, clear of the others on the sheet. Only the UniqueID field changes,
  which verify() proves by masking it and comparing byte for byte, so the
  netlist is unaffected. Refuses to run twice.
* `x2_top_row_order.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09,
  sixth pass: the top row put in channel order (1 GND, 2 CHAN-CLK, 3-9 CHAN0-6,
  USB landing, 10-16 CHAN7-13, 17-20 the supplies), so CHAN12/CHAN13 leave the
  corner. Sixteen gate copies move with their wires and labels and every pin
  designator is remapped in all 41 copies; connectivity is unchanged, only which
  X2 pad each net lands on. Refuses to run twice.
* `sheet0_pmic_block.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09:
  the block diagram gains PMIC BQ24232 between the USB port and the voltage
  regulators, with LiPo Connect on its right; the +5V riser is extended into the
  charger, VU drops from the charger into the regulators and VBATT runs to the
  battery block. Drawing furniture only (RECORD=4 text, RECORD=6 lines), so the
  netlist cannot change. Refuses to run twice.
* `jp_dns.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` - 2026-09-08:
  JP3/JP4 (bare JTAG holes) get DNS = Yes and a SPEC line, inserted after
  their NOTE with OwnerIndex renumbering; bom_audit lists them as DNS
  positions instead of parts. Refuses to run twice.
* `u2_ft2232hl.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09: U2 from
  the FT2232HQ (QFN-64, dry until April 2027) to the FT2232HL (LQFP-64, same
  die and pin numbering): part number, comment, label, device names,
  description, footprint model FT2232HL-LQFP64, SPEC/NOTE inserted, the EP
  pin and its ground stub removed (bus wire shortened), sheet-4 title and
  sheet-0 block renamed. Refuses to run twice.
* `bq24232_charger.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"` -
  2026-09-09: D1 (USB VBUS Schottky) replaced by a TI bq24232 LiPo charger and
  power path (U8), JST PH battery connector X4, C150/C151, R102-R108, LD3/LD4:
  deletes D1 and its cathode wire by content, appends the new symbols, wires,
  labels, ports and notes. Values from SLUS821J section 9.2.1 (495 mA input
  limit, 244 mA charge, 36 mA termination, 7.5 h timer, TS disabled).
  Footprints VQFN16-3X3-RGT and JST-B2B-PH-SM4-TB are for the PCB stage.
  Refuses to run twice.
* `sheet1_rearrange.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"` -
  2026-09-09 re-layout of sheet 1: the charger block up under the USB
  connector (+460), the SC189 blocks and the LD5 power-good circuit down
  (-500), X1's VBUS pin wired straight into U8 IN, C78 moved onto U8 OUT
  (pins 10/11) with its own ground, C151 nudged left. Netlist unchanged.
  Refuses to run twice.
* `d2_note.py` - D2 gets the NOTE parameter (D1 removal, SOD323F footprint)
  as a hidden parameter, so the master BOM's note for it comes from the sheet
  like every other note.
* `ft_vcore_caps.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` -
  2026-09-09: C152, C153 and C154, three 0.1uF 0201 GRM033R61A104KE15D cloned
  from C136, hung off the FT-VCORE rail beside C39 with their own ground ports,
  one per FT2232H VCORE pin, after connectivity_check.py found that rail carrying
  bulk only. The rail is extended left and junctioned; no net label is added
  because the extension is one wire with the rail. Refuses to run twice.
* `tck_pullup_out.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` -
  2026-09-09: R89, the 10 K pull-up on TCK, is removed.  It sat on the BRIDGE
  side of the damping resistor and fought R5, 5.1 K to ground on the FPGA side,
  so with ADBUS0 tri-state -- power-up, and any time no USB host has opened the
  MPSSE -- the FPGA's clock input rested at 3.3 x 5100/(10000+100+5100) = 1.11 V,
  between VIL and VIH.  Dropping the pull-up and keeping the pull-down leaves TCK
  idling low, which is the JTAG convention and the safe level for a clock.  R89's
  rail drop goes with it and so does the junction at (692,1072), which was a
  three-wire branch and is now a corner; the wire carrying U2 pin 16 out to the
  column is SHORTENED rather than deleted, because it holds the TCK net label.
  Netlist: pads 785 -> 783, TCK keeps JP3-1, R4-6 and U2-16.  Refuses to run twice.
* `resistor_packs.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` -
  2026-09-09: the six 100 ohm JTAG/config series resistors (R9 PROG#, R38 DONE,
  R8 TDI, R37 TDO, R4 TMS, R36 TCK) become one CTS 742C163101JP and the two 4.7 K
  configuration pull-ups (R1 INIT_B, R3 PROGRAM_B) one CTS 742C043472JP, drawn the
  way R34 is: one RECORD=1 per placed element, all sharing a designator, each
  carrying the whole pin set, differing only in CurrentPartId, PartCount = elements
  + 1.  They read R4A..R4F and R1A/R1B.  Isolated arrays pair pad k with pad 2N+1-k,
  so the bridge side lands on pads 1-6 and the FPGA side on 16-11; the two spare
  elements hold pads 7-10.  A genuine 6-element part exists (CTS 753123101GP,
  12-SRT) but Digi-Key holds none at 28 weeks and MOQ 1000, and its body is bigger
  than the 8-element chip array, so the six go into an eight.  Every pin gets a
  fresh PinUniqueId and the stale HiddenNetName parameters are dropped.  Nets and
  placed pad count come out unchanged (178 and 785); component count 190 -> 184.
  Run sheet4_layout.py first.  Refuses to run twice.
* `sheet4_layout.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` -
  2026-09-09, four cosmetic moves that leave the netlist identical.  R3, the
  PROGRAM_B pull-up, is mirrored about its own origin so it stands ON the RST#
  wire with the rail above it instead of hanging below on a 110-unit stub with
  VCC3V3 at the bottom, which read like a pull-down; its rail label becomes a
  horizontal font-3 one like R1's, and the stub wire is deleted.  R1 moves up 60
  to clear it.  C41 turns over (orientation 3 -> 1, pin conglomerates swapped)
  and drops 50 so both FT2232H bypasses hang the same way with their ground
  symbols side by side, and C40 slides 40 right, with its FT-VPHY label, to make
  the room.  Everything around C40 carries sub-unit _Frac offsets from the EAGLE
  import -- three junctions and a 0.04-unit wire hold that node together at three
  different fractional positions -- so that cluster is translated by whole units
  with every _Frac untouched.  Refuses to run twice.
* `r3_pullup_c39_out.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"` -
  2026-09-09, two changes.  R3 4.7K moves from GND to VCC3V3: connectivity_check.py
  solved the resistor network on every configuration pin and found PROGRAM_B (ball
  V10, net RST#) resting at 1.63 V, in the undefined band, because R3 pulled it
  down and its only pull-up sat behind R9's 100 ohm on a net the FT2232H tri-states
  until a host opens the bridge.  UG470 wants that pin pulled up to VCCO_0; the
  lower end is redrawn the way R1, the INIT_B pull-up on the same sheet, is drawn
  (ground symbol removed, VCC3V3 net label on the stub end).  Both resets survive:
  X2-23 and the bridge through R9.  C39 4.7uF goes: DS_FT2232H Figures 4.1 and 6.1
  show ONE 4.7 uF on the core rail beside the 100 nF parts, and C139 is it, so with
  C152-C154 added the rail now matches the reference exactly.  Its stub, ground
  symbol, net label and rail junction go with it.  Deletes records, so every later
  OwnerIndex is renumbered and the header count rewritten.  Refuses to run twice.
* `sheet0_fixes.py <this folder> "Imported zulu_a7.PrjPcb/zulu_a7_0.SchDoc"` -
  2026-09-09: five things the block diagram said that were not true.  CHAN-I/O
  (28) -> (29), because the netlist holds CHAN0..CHAN28 and the sheet has already
  taught the reader that a bracket is a bus width.  The SDRAM-CLK return branch
  and its arrowhead into the FPGA are deleted -- it implied a feedback path on a
  net that is two pads, U1-M1 and U3-38.  The microSD note's "six bank-34 balls"
  becomes banks 34, 16 and 35, which is what the package file and the sheet-5 pin
  designators say.  The XADC link loses its header-end arrowhead, since the two
  analogue signals only go one way.  The LED/Button link gains an arrowhead into
  the block, because five of its six signals are FPGA outputs.  The Pmod link was
  checked and left alone: the review said it had one arrowhead, it has two.  Ten
  lines deleted and two added, so OwnerIndex is renumbered and the header count
  rewritten -- this is the sheet that was left unopenable once by skipping that.
* `label_justification.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09:
  254 net labels stop hanging below their wires.  Altium's Justification is a 3x3
  anchor grid (h = j%3, v = j//3); a label with v=2 is anchored at the TOP of its
  text box, so the anchor sits on the wire and the glyphs are drawn underneath it,
  while pin designators are bottom-anchored and sit above theirs.  Rows are 10
  units apart and the text is ~6.8 tall, so every net name landed on the NEXT
  pin's line: CHAN0 (X2 pin 3) rendered at PDF y 100.88..104.00 against the digit
  4 at 101.60..104.72.  Subtracting 6 (6->0, 7->1, 8->2) moves the anchor to the
  bottom and leaves the horizontal half alone; CHAN0 now renders at 97.29..100.40,
  character for character its own digit 3.  Locations are untouched, so the
  netlist is unchanged.  Eight ROTATED top-anchored labels are left alone and
  listed on every run - for those the same flip moves the glyphs sideways.
* `sheet5_ball_captions.py <this folder> "Imported zulu_a7.PrjPcb"` - 2026-09-09:
  the grey "<ball>  <pin function>" captions beside each FPGA pin row on sheet 5
  are regenerated from the pin each one annotates, with the function name read
  from Datasheet/xc7a35tcpg236pkg_pinout.txt.  They had survived the re-pin: 94 of
  137 named a ball that no longer carried that row's net (SD-DAT2's row said W2,
  which really carries SDRAM-CS#), and the Pmod block claimed A14/A15/W7, which
  carry SDRAM D14/D15/D2.  99 rewritten, 37 already right, one left alone and
  reported.  Only pins whose OwnerPartId equals their placement's CurrentPartId
  count as live -- U1 is placed 139 times and every placement carries all 236
  balls, so a naive search finds thousands.  Text only; the netlist is unchanged.
* `schematic_review.py > docs/schematic_review.md` - readability and labelling
  hygiene over the seven sheets, read from the .SchDoc records so it sees what
  Altium sees rather than what the PDF renders.  Checks that every net label and
  power port lands on a wire or a pin (a label one unit off names nothing and the
  netlist never complains), that no wire end dangles, that no two net names differ
  only in case or separator, that every label text became a real net and no net
  has a single pad, that every part can be named by a reader, and how much of the
  printed page the drawing actually gets.  Read-only.  It says where it stops:
  whether a sheet READS well is a judgement it cannot make, so the judgement half
  lives in `schematic_review_notes.md` beside it and is appended verbatim to the
  output -- re-running the tool never overwrites it.
* `connectivity_check.py > docs/connectivity_check.md` - power and ground
  architecture plus bus and differential-pair mapping, read from the exported
  netlist and the datasheets. Traces every supply and ground pin of every IC to
  its rail (the FPGA against the whole CPG236 package pin list, not just the
  symbol), counts the decoupling by value tier against UG483 Table 2-2 and the
  FTDI reference circuit, and verifies every bus line against the pin the part's
  datasheet gives. Read-only. It cannot judge placement, and says so.
* `master_bom.py` - rewrites ../docs/zulu_a7-bom.csv (the master BOM, formerly
  from the root tools/bom.py and the EAGLE schematic) from the Altium sheets,
  keeping its column layout and line order; notes come from the NOTE
  parameters, DNS parts are marked DNP. Run after any sheet change that
  touches parts.
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
  Protel) against the EAGLE schematic, pad by pad.  It last agreed on
  2026-09-07 (190 components, 175 nets, 799 pads, no differences) and has
  since been left behind on purpose: the Altium side has taken the SC189
  regulators, the bq24232 charger, the X2 pin field, the C39 removal and the
  two resistor arrays, none of which exist in ../zulu_a7.sch.  As of
  2026-09-09 it reports 184 components against the EAGLE 190.  Keep it for
  the day the EAGLE source is regenerated; do not read its output as a fault.

Import Wizard settings that matter: untick "Do not translate hidden net
names" (else 16 nets named without a label lose their names).  Pins that
own several pads in EAGLE (BTN 1/2 and 3/4, X1 5+shell, X3 G1/G3 and
G2/G4) become single Altium pins named "1,2" etc.; split them before
matching to the imported board.
