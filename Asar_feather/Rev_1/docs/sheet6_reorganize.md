# Sheet 6 (asar_a7_5.SchDoc, FPGA Connections): U1 ball rows filed by net (2026-11-17)

Same reorganization as the no-PMOD board's sheet 5 (Zulu_A7_no_pmod/Rev_2/tools/sheet5_reorganize.py, third pass
1166f8c), ported by `tools/sheet6_reorganize.py`. Both sheets come from the same EAGLE import with identical geometry;
only the ball -> net assignment differs (the Feather re-pins). Schematic drawing only: no connection changed.

## What changed

- The 138 U1 ball rows are filed by NET into ten headed blocks on one grid, two columns:
  - A: CONFIG (with the R20-R22 straps beside it), CLOCK, JTAG, FLASH / microSD, FT2232H, LED / BUTTON, ANALOG (XADC);
  - B: FEATHER HEADER (CHAN-CLK, CHAN0-8, CHAN14-22), SDRAM, UNCONNECTED BALLS (spare user I/O, GTP TX/REFCLK
    floating, GTP RX to GND, thermal diode to GND).
  Rows move rigidly with the parts wired to them (R23 on PUDC_B; L6/L7/C123/C124 on the XADC supply).
- Rows that were filed by where they used to be now sit with their net: U17 (LED0_R) out of CONFIG; K17 (UART_FT_TXD)
  and ten no-net balls out of the header; G17 (CHAN7) out of the spares; P19 (FT-PWREN#) out of LED / BUTTON.
- Pin names (96 changed): a user-I/O ball shows its port in `vivado/asar_feather_pins.xdc`, so the header balls now
  show their Feather pin (CHAN0 = F_A2 ... CHAN22 = F_SDA, CHAN-CLK = F_D4); the script checks every XDC comment's
  net against the sheet net, and that all 82 ports have a row. Dedicated pins keep their function name; G3/G2/H2/J2
  show AD4P/AD4N/AD12P/AD12N; no-net balls show IO_<ball>. The hidden GateName_<part> follows.
- Ball texts checked against AMD's xc7a35t_cpg236.pkg; U17 gets its missing text, C13 reads VCCADC_0.
- Old rotated headings, the 'Spare I/O, G17=CHAN7' note and the two notes are replaced; the master-SPI and microSD
  notes are rewritten from the rows. The XADC sub-heading now says net AIN15 = VAUX4 (G3/G2), AIN16 = VAUX12 (H2/J2)
  (inherited net names; the XDC header says the same).
- Inherited drawing fixes (pretouch, from the no-PMOD review): R23 and C123/C124 branch from the label side instead of
  through the pin names; the GNDADC/GND tie rows get a stub + label; the GTP RX GND ports become GND labels.

## Proof

- Script: sheet nets identical before/after (130 nets, 154 pins), also re-checked with
  `sheet3_u3_layout.py --verify`. SRC md5 79d5e784 -> 6ba41efc. Backup `backups/asar_a7_5_before_reorganize.SchDoc`.
- Independent review (workflow wf_1d1c79ad-e33: own connectivity extractor with mutation tests, layout against
  Altium's PDF text metrics, names/notes against the XDC, .pkg, BSDL, UG470/UG480/UG482, OLE/record integrity; each
  finding checked by a skeptic): all 154 pins on the same nets with the same partners, 27 No-ERC markers on the same
  pins, other OLE streams byte-identical, owners intact. One new cosmetic issue confirmed and fixed: C123's
  designator had dropped onto L7's baseline ('L7 C123') and the VCCADC port's junction sat 4 units from the branch
  junction -> L7's designator moved left of its coil, the port + junction 5 units west on the same wire. Also fixed:
  U17's added ball text now carries the same 0.504 fraction as its neighbours; the XADC channel note above.
  Rejected by the skeptics: the 0.504-unit offset of column A (inherited from a label's fraction; harmless, the sheet's
  own snap grid is 100 mil and the hot-spot grid catches it; the no-PMOD sheet has it too), R23's vertical VCC3V3
  label near RST# (5.4 units clear by Altium's PDF metrics).
- Altium: sheet closed in the Projects tree, written, reopened; Validate = Compile successful, 28 warnings (same as
  before: undriven nets, X2's unused sub-part); Protel netlist BYTE-IDENTICAL to the one exported just before
  (181 components, 155 nets); `tools/sch_vs_board.py` MATCH.

## Pre-existing, not changed

- U1's ComponentDescription (all U1 records on sheets 6 and 7) still says "Replacement for the Spartan-6" and calls
  the config/JTAG/power balls unverified placeholders; every ball now checks against AMD's .pkg/BSDL.
- EAGLE value texts drawn across their own parts: C123 '100nF', R23/R20 '1K', L6 'FB 600R'.
- The master-SPI note's "only ones" ignores the optional EMCCLK (E19) and DOUT_CSO_B (V19), both spare here.
