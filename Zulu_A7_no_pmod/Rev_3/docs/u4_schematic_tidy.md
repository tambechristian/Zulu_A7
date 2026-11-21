# Sheet 3 (zulu_a7_3.SchDoc, Memory): U4 drawing fixes (2026-11-18)

The same three drawing fixes around U4 (W25Q128JVSIQ, the SPI boot flash) that the user marked up on the Asar Feather
sheet (Asar_feather/Rev_1/docs/u4_schematic_tidy.md); the U4/R2/R6/R7/C11 geometry here is identical. Made by
`tools/u4_tidy_schematic.py`. Schematic drawing only: no connection changed.

- **R2 (WP# pull-up):** the VCC3V3 port pointed right from the bottom of a wire hanging under R2's left pin. The wire
  now rises 10 units from the pin and the port points up, like R7's.
- **R2 designator:** was 32 units under the resistor; now just under the body, centred (211, 964).
- **C11 (drawn as U4's bypass):** its GND port hung from C11's east pin straight over the FLASH-D03 wire (Altium draws
  the GND stem, bars and text ~28 units below the hot spot; the wire was 10 units below). C11 moved up 30 units on a
  jog of the pin-8 VCC wire (375,997 -> 415,997 -> 415,1027 -> C11); its GND text now sits ~12 units above FLASH-D03.
  The VCC3V3 port and junction at pin 8 are unchanged. (The jog also clears C11's plates off the FLASH-D03 label.)

## Proof

- Script: sheet nets identical before/after (72 nets, 154 pins); SRC md5 a0c928e4 -> 983ba4f1.
  Backup `backups/zulu_a7_3.SchDoc.pre-u4-tidy`.
- Independent review (workflow wf_9770d73e-cc6, on the dry run; the applied file's FileHeader stream is identical to
  it): an extractor of its own with mutation tests found every pin on the same net with the same partners and no new
  contact; exactly the 20 intended records changed (C11 and its children +30 in Y, R2 designator, the two ports, three
  wires), record count, Weight and OwnerIndex unchanged, other OLE streams byte-identical; layout boxes from Altium's
  own render show no new overlap (R2's pin number "2" sits ~2 units beside the new riser, still legible).
- Altium: sheet closed in the Projects tree, written, reopened, new drawing checked on screen. Validate = Compile
  successful, the same 29 warnings as just before; Protel netlist BYTE-IDENTICAL to the one exported just before
  (129c7ff3).
