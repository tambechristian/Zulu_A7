# Sheet 4 (asar_a7_3.SchDoc, Memory): U4 drawing fixes (2026-11-18)

Three drawing fixes around U4 (W25Q128JVPIQ, the SPI boot flash) that the user marked up, made by
`tools/u4_tidy_schematic.py`. Schematic drawing only: no connection changed.

- **R2 (WP# pull-up):** its VCC3V3 port pointed right from the bottom of a wire hanging under R2's left pin. The wire
  now rises 10 units from the pin and the port points up, like R7's.
- **R2 designator:** was 32 units under the resistor; now just under the body, centred (211, 964).
- **C11 (U4's bypass):** its GND port hung from C11's east pin straight over the FLASH-D03 wire (Altium draws the GND
  stem, bars and text ~28 units below the hot spot; the wire was 10 units below). C11 moved up 30 units on a jog of the
  pin-8 VCC wire (375,997 -> 415,997 -> 415,1027 -> C11), so its GND port hangs in free space about 11 units above
  FLASH-D03. The VCC3V3 port and junction at pin 8 are unchanged.

## Proof

- Script: sheet nets identical before/after (56 nets, 122 pins); SRC md5 eef0ab05 -> 9f7849b3.
  Backup `backups/asar_a7_3_before_u4_tidy.SchDoc`.
- Altium: sheet closed in the Projects tree, written, reopened; the new drawing checked on screen. Validate = Compile
  successful, the same 28 warnings; Protel netlist BYTE-IDENTICAL to the one exported before (eb0c0d05, 181
  components, 155 nets); `tools/sch_vs_board.py` MATCH.
