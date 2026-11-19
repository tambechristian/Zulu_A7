# Zulu_a7_no_pmod: PMOD removed, board cut to 2.4 x 1.0 in (2026-11-08)

Copy of Zulu_A7_Fab_B. Goal: 60.96 x 25.40 mm by removing the Pmod J1 and finding the JTAG holes a new home.

## State of the board
Outline 60.96 x 25.40 mm, DRC 0 warnings and 0 violations, every net routed. See the last section for the final numbers.

## Schematic
`tools/no_pmod_schematic.py` deleted J1, R26-R33, their wires, labels, ports, junction and the note frame on sheet 2, the
eight JA labels with stubs and the 'Pmod JA' heading on sheet 5, and the Pmod box and arrow on sheet 0.
`tools/no_pmod_noerc.py` put No-ERC markers on the eight freed U1 balls: U18, U19, W18, C17, R19, W19, V19, U17.
Compile succeeds, 29 warnings, nothing on those balls.

The sheet 4 notes on JP3/JP4 were reworded once the JTAG spot was settled.

## PCB
- `tools/no_pmod_prep.py` rips the copper and defines the moves; the plan is `tools/route/no_pmod/final.json`.
- Applied with `FabBCopper_NoPmod.pas`: 7 parts moved, 240 tracks and 130 vias removed, 211 tracks and 58 vias added.
- `NoPmod_Board.pas`: board outline, R5 turned 180 degrees, L2/L5 polygons pulled back and repoured.
- `mark_microvias --expect 980` marked the 39 new lasers.

| Part | Before | After | Why |
|---|---|---|---|
| R25 | 61.10, 5.65 | 56.30, 14.05 | clock, next to its surviving copper |
| R24 | 59.05, 5.65 | 59.35, 21.20 | CLK-12M-FT arrives on Top from the north |
| R5  | 61.10, 14.17 | 56.70, 20.10, turned 180 | FPGA-TCK via, GND tie via |
| R90 | 63.15, 14.17 | 58.95, 13.15 | past the new edge |
| R92 | 61.10, 17.01 | 60.20, 17.01 | past the new edge |
| R93 | 63.15, 17.01 | 60.20, 17.80 | past the new edge |
| R99 | 61.10, 19.85 | 60.20, 19.85 | past the new edge |

ECO: only J1, R26-R33 and their nets were executed. The ten PCB-only net classes, the USB differential pair and the
stale U1/LD0 comment, description and parameter changes were unticked.

## Why routing took several attempts
- The old east strip (x > 60.66) carried the long north-south runs, so the survivors have to run inside the strip now.
- TDI's old route runs along y = 0.30, inside the router's 0.30 mm edge keep-out; it was kept and extended by hand.
- R4's east pads sit against the new edge, so R4-3 and R4-4 fan out west, between the array's pad columns.
- Nets routed one at a time, hardest first, closed where the batch orders did not.

## Gate lessons
- `route_check` caught a hand track shorted to GND and FLASH-D02. Hand copper must go through the gate.
- `compose_plan` prunes against the base model: a rotated part must be rotated in that base too, or live copper is pruned.
- `prune_stubs` treated a via touching a track off-centre as no junction and pruned whole nets back to the pad; the trim
  test now accepts a via land overlapping the track body.
- Altium caught a new via placed exactly on an existing GND via (hole-to-hole); `NoPmod_Dedupe.pas` removed one.

## JTAG and final state (2026-11-08)
JP3 (TCK, TMS, GND) on the north strip beside the X2 row, pad 1 (11.755, 22.045); JP4 (TDI, TDO, VCC3V3) on the west edge,
rotation 90, pad 1 (1.60, 12.10). `FabBCopper_NoPmodJtag`, `NoPmod_Jtag`, `NoPmod_JtagFix` and `NoPmod_JtagFix2` placed it.
R24-1 closed by a through via at (59.20, 21.35) and an L3 run; one section of LED0_R was re-routed around it.
X2 labels 16/15/14 moved down, C13/C12/C11 below them (C12, C11 also moved right, off X3-G4). R34 and JP3 designators hidden.
Final DRC: 0 warnings, 0 violations. 1006 microvias verified. Compile succeeds, 29 warnings. PcbDoc md5 9d589d76.
JP3/JP4 descriptions and notes on sheet 4 reworded; the descriptions in the PCB still match the old text until a future ECO.
