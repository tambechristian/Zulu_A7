# Sheet 3 (zulu_a7_3.SchDoc, Memory): U4 drawing fixes (2026-11-18)

The same three drawing fixes around U4 (W25Q128JVSIQ, the SPI boot flash) that the user marked up on the Asar Feather
sheet (Asar_feather/Rev_1/docs/u4_schematic_tidy.md) and that the no-PMOD board got (Zulu_A7_no_pmod/Rev_2, 5e0eed9);
the U4/R2/R6/R7/C11 geometry here is identical. Made by `tools/u4_tidy_schematic.py`, applied to BOTH Fab B revisions
(their sheet 3 was the same file, md5 9b5ff6f3). Schematic drawing only: no connection changed.

- **R2 (WP# pull-up):** the VCC3V3 port pointed right from the bottom of a wire hanging under R2's left pin. The wire
  now rises 10 units from the pin and the port points up, like R7's.
- **R2 designator:** was 32 units under the resistor; now just under the body, centred (211, 964).
- **C11 (drawn as U4's bypass):** its GND port hung from C11's east pin straight over the FLASH-D03 wire. C11 moved up
  30 units on a jog of the pin-8 VCC wire (375,997 -> 415,997 -> 415,1027 -> C11); its GND text now sits ~12 units above
  FLASH-D03. The VCC3V3 port and junction at pin 8 are unchanged.

## Proof

- Script: sheet nets identical before/after (56 nets, 122 pins). Rev_1 9b5ff6f3 -> 7da720e4, Rev_2 9b5ff6f3 -> c56c0c1d
  (the two files differ only in the OLE container; their FileHeader streams are identical, and identical to the dry run
  whose 20-record change set matches the reviewed no-PMOD edit, workflow wf_9770d73e-cc6). Backup
  `backups/zulu_a7_3_before_u4_tidy.SchDoc`.
- Altium (Rev_2 project): baseline taken with the original sheet 3 loaded -- Validate = Compile successful, 34 warnings,
  Protel netlist e5d33386 (Rev_1's baseline was the same e5d33386); fixed sheet loaded and checked on screen -- Validate
  34 warnings, Protel netlist BYTE-IDENTICAL (e5d33386).
