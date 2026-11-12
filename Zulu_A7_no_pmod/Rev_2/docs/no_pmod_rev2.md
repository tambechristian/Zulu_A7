# Zulu_a7_no_pmod Rev 2: Pmod removed (2026-11-12)

Copy of Zulu_A7_Fab_B/Rev_2 (board md5 33023787), renamed to Zulu_a7_no_pmod: PrjPcb, PcbDoc, PrjPcbStructure, the
.pre-microvia backups, the schematic PDF and the Project Outputs/Logs folders; 75 scripts and the project file now point
at Zulu_A7_no_pmod/Rev_2. The fabrication/ and assembly/ release files still describe Fab B Rev 2 and must be regenerated.

## Schematic
Same edit as Rev 1 (`tools/no_pmod_schematic.py`, record counts identical): J1, R26-R33, their wires/labels/ports/junction
and the note frame on sheet 2; the eight JA labels + stubs and the 'Pmod JA' heading on sheet 5; the Pmod box and arrow
on sheet 0. `tools/no_pmod_noerc.py`: No-ERC on U18, U19, W18, C17, R19, W19, V19, U17. Compile successful, 29 warnings
(the usual no-driving-source set).

## PCB
- `NoPmod_RemoveCopper.pas`: 128 tracks + 73 vias on the 16 Pmod nets (plan `tools/route/no_pmod/final.json`, route_check
  PASS, no dead copper or opens on any other net).
- ECO: removed J1, R26-R33, the 16 nets and their pins/class members. Unticked: 16 'Change Component Design Item ID'
  entries inherited from Fab B Rev 2, the 10 PCB-only net classes, the USB diff pair, and 'Add U7 to zulu_a7_1'.
- `NoPmod_Repour.pas` (both planes), `FabB_RebuildConnR2.pas` (0 stale connection objects).
- Result: DRC 0 warnings / 0 violations; pads 863 -> 835, tracks 4917 -> 4789, vias 1961 -> 1888; 0 open, 0 dead copper;
  microvia marks verified; md5 16064205.

The board is still 69.85 x 25.40 mm (2.75 in) with JP3/JP4 at the east end; no resize or JTAG move yet. Title is still 'ZULU A7 2.2'.

## Resize to 2.4 x 1.0 in and JTAG (2026-11-12)
Copper east of x 43 mm is identical to Rev 1's, so Rev 1's resize plan was reused as it stands (`tools/no_pmod_resize_prep.py`:
all 112 removals matched this board; the duplicate GND tie via at (57.55, 20.30) was dropped; route_check 0 violations).
Rev 1's JTAG sites are blocked here (VCC1V0/VU Bottom copper, R108), so a clean-site scan (`route/resize/jtag_sites.py`)
picked the only free spots:
- JP3 (TCK, TMS, GND): upright on the west edge, rotation 90, pad 1 at (1.10, 14.89).
- JP4 (TDI, TDO, VCC3V3): south-west corner above the X2 row, rotation 0, pad 1 at (1.50, 3.00).
The R24-1 clock leg and the LED0_R detour came from Rev 1's stage 2 (east copper identical); TCK/TMS/TDI/TDO routed fresh
(TMS needed a 2.5M-expansion run). Applied with FabBCopper_NoPmodResize, NoPmod_Board (R5 turn, outline, planes),
FabBCopper_NoPmodJtag and NoPmod_Jtag (JP3 turn, repour); 67 new lasers marked (1183 verified).
DRC passes then fixed: JP3 0.027 mm too close to R108-1 and a 0.003 mm mask web at its square pin 1 (JP3 moved to the
values above; a TMS L4 stub re-joins the moved pad); JP4's designator hidden (it sat on X2's pads); X2 labels 40/39/38 and
AI1/AI0/C28 restacked above JP4 at 0.6 mm text (the only room before the microSD pads); '1V0' at 85 % height.
Final: DRC 0 warnings / 0 violations, 0 open, 0 dead copper, ratsnest empty, md5 3e191e8d. Sheet 4 JP3/JP4 notes reworded.
Title changed to 'ZULU A7 2.3' (tools/NoPmod_Title23.pas; DRC 0/0, copper unchanged, md5 50552912). Not done: fabrication/ and assembly/ outputs are Fab B Rev 2's.
