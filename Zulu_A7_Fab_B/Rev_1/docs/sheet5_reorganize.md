# Sheet 6 (zulu_a7_5.SchDoc, FPGA Connections): U1 ball rows filed by net (2026-11-18)

User: "organize the sheet 6 fpga connections like you did on zulu a7 no pmod". Port of
Zulu_A7_no_pmod/Rev_2/tools/sheet5_reorganize.py (with the Asar port's generalisations) as `tools/sheet5_reorganize.py`,
applied to BOTH Fab B revisions (same file, md5 5602d2d1). Schematic drawing only: no connection changed.

## What changed

- The 138 U1 ball rows are filed by NET into headed blocks on one grid, two columns, as on the no-PMOD sheet:
  - A: CONFIG (R20-R22 straps beside it), CLOCK, JTAG, FLASH / microSD, FT2232H, LED / BUTTON, ANALOG (XADC);
  - B: PROTOTYPING HEADER, **PMOD JA** (new: JA1 U18, JA2 U19, JA3 W18, JA4 C17, JA7 R19, JA8 W19, JA9 V19, JA10 U17 --
    the only nets Fab B has that the no-PMOD board does not), SDRAM, UNCONNECTED BALLS (GTP TX/REFCLK floating, GTP RX
    to GND, thermal diode to GND; no spare user I/O is left on Fab B).
- Pin names (72 changed): a user-I/O ball shows its port in the repository's vivado/zulu_a7_pins.xdc (all 101 ports
  checked ball by ball: comment net = sheet net, ball function = AMD's .pkg, every port has a row; it is the no-PMOD
  XDC plus the 8 JA lines). The JA balls now read JA1..JA10 (they showed IO_A14, CHAN13, CHAN28, IO_N2, ...). Dedicated
  pins keep their function names; G3/G2/H2/J2 show AD4P/AD4N/AD12P/AD12N.
- P17 gets its missing ball text; C13 reads VCCADC_0; the XADC sub-heading names VAUX4/VAUX12.
- The master-SPI note is rewritten for Fab B (EMCCLK E19 carries CHAN12; DOUT_CSO_B V19 carries JA9, unused in x4
  mode); the old 'Pmod JA (bank 16 x5)' heading is dropped (7 of the 8 JA balls are in bank 14).
- Drawing fixes carried over: R23 and C123/C124 branch from the label side; GNDADC/GND tie rows get a stub + label; GTP RX
  GND ports become GND labels; L7's designator moved clear of C123's; the VCCADC port and its junction 5 units west.

## Proof

- Script: sheet nets identical before/after (130 nets, 154 pins); 159782 -> 159796 records. Both revisions -> 9c7543e6.
  Backup `backups/zulu_a7_5_before_reorganize.SchDoc`.
- Independent review (workflow wf_0f527bcc-c01): own connectivity extractor with mutation tests (no pin changed net or
  partners), layout matched object by object against the no-PMOD result (same positions; SDRAM and UNCONNECTED shifted
  as a block for the new PMOD JA block; no new overlap), names/notes against the XDC/.pkg, file integrity. No finding
  survived.
- Altium (Rev_2 project): sheet reopened and checked on screen; Validate = 34 warnings, unchanged; Protel netlist
  BYTE-IDENTICAL to the baseline (e5d33386).

## Sheet 2's Pmod note (fixed the same day)

Sheet 2 (zulu_a7_2.SchDoc)'s "Digilent 12-pin Pmod (JA)" note gave the JA pin-out of an earlier pin plan (JA1-JA4 = A14 A15
B15 A16 in bank 16, JA7 = C15, JA8/JA9/JA10 = W19/N2/W7). Its last three lines now read: JA1-JA4 = U18 U19 W18 C17
(banks 14/14/14/16), JA7-JA10 = R19 W19 V19 U17 (bank 14), U19/W18/V19 double as RDWR_B/CSI_B/DOUT_CSO_B which master SPI
x4 does not use (UG470 table 2-2), banks 14 and 16 both VCCO=3.3V. `tools/sheet2_pmod_note.py` checks the pin-out against
sheet 6's own nets and proves sheet 2's nets unchanged (72 nets, 116 pins); Rev_1 4c11e618 -> 4e078eac, Rev_2 7d532b7d ->
d58a2c11, backup `backups/zulu_a7_2_before_pmod_note.SchDoc`. Altium (Rev_2): note checked on screen, Validate 34
warnings, netlist e5d33386 identical.

## Not changed

- The hidden GateName_<n> copies on the other 138 U1 records keep their old text (same as the no-PMOD and Asar sheets).
