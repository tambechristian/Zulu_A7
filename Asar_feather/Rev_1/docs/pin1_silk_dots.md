# Pin-1 and cathode silkscreen dots (2026-11-20)

PCBWay held an earlier Zulu A7 HDI order to ask where pin 1 and the LED cathodes were, because that board's silkscreen
had no polarity marks. The no-PMOD Rev 2 and Fab B Rev 2 boards got dots first; the method and its rules are in
`Zulu_A7_no_pmod/Rev_2/docs/pin1_silk_dots.md`. Before this change, only U2 and U10 on this board had a pin-1 mark
(ticks). It now carries a dot beside pin 1 of every polarized top-side part and beside each LED cathode. Silkscreen
only: copper, solder mask, paste and drills are unchanged.

## The dots

Each dot is a full-circle arc (radius = diameter / 4, line width = diameter / 2) owned by its part, on Top Overlay.

| Part | Marks | Dot centre (mm) | Diameter (mm) | Gap to the marked pad (mm) | Dot edge to exposed copper (mm) | Dot edge to the mask opening (mm) |
|---|---|---|---|---|---|---|
| BTN | pin 1 | (39.975, 5.950) | 0.40 | 0.525 | 0.325 | 0.275 |
| RESET | pin 1 | (20.825, 5.300) | 0.40 | 0.525 | 0.325 | 0.275 |
| LD0 | cathodes (pads 2/4/6) | (37.925, 3.225) | 0.40 | 0.525 | 0.325 | 0.275 |
| LD1 | cathode K | (30.550, 3.825) | 0.25 | 0.447 | 0.322 | 0.256 |
| LD2 | cathode K | (33.750, 3.825) | 0.25 | 0.447 | 0.322 | 0.256 |
| LD3 | cathode K | (7.305, 2.655) | 0.40 | 0.525 | 0.325 | 0.275 |
| LD4 | cathode K | (7.305, 3.955) | 0.40 | 0.525 | 0.325 | 0.275 |
| Q1 | pin 1 | (15.435, 16.625) | 0.40 | 0.525 | 0.325 | 0.275 |
| U1 | ball A1 | (29.125, 6.130) | 0.40 | 0.682 | 0.482 | 0.427 |
| U2 | pin 1 | (8.525, 11.675) | 0.40 | 0.537 | 0.337 | 0.267 |
| U3 | ball A1 | (31.425, 6.755) | 0.40 | 1.287 | 1.087 | 1.031 |
| U4 | pin 1 | (40.975, 18.275) | 0.40 | 0.520 | 0.320 | 0.270 |
| X4 | pin 1 (battery +) | (12.825, 14.100) | 0.40 | 0.525 | 0.325 | 0.275 |
| X5 | pin 1 | (44.425, 8.350) | 0.40 | 0.525 | 0.325 | 0.275 |

- **Clearances:** every dot clears the Silk To Solder Mask rule (0.254 mm, measured to exposed copper) and also clears
  the mask opening itself by 0.254 mm. The opening is the pad grown by 0.05 mm on each axis, measured corner-exact.
  U1's and U3's lands are round, so their figures are lower bounds.
- **No dot:**
  - U7 (SOT-23-5) and U8 (QFN-28) on the bottom: the planner finds no legal spot that points at pin 1. The nearest is
    1.8-1.9 mm away, among other parts. The assembly drawings mark their pin 1.
  - U10 keeps its tick west of pad 1 (2026-11-16).
  - X1, X2 and X3 are keyed or hand-placed.
- **RESET:** it is the same PTS810 switch as BTN, so it is marked too. Both read the same way and share one
  footprint-relative spot, so the library keeps a single PTS810.
- **LEDs:** LD1/LD2 and LD3/LD4 face opposite ways (rotation groups), so they have different footprint-relative
  spots. LD1 and LD2 sit between the "SCK"/"MO" labels and their K pads, where only a 0.25 mm dot fits.

## How the spots were chosen

`tools/route/pin1_dots/plan_marks.py` is the no-PMOD planner with a CONFIG block for this board:
- it reads the release Gerbers from before the dots out of git (commit 257867d, the earlier 2026-11-20 fabrication
  ZIP);
- it reads each part's side, rotation and pattern from the board;
- the edge check follows the rounded GM outline.

Three fixes were made here before the dots went on the board; the first is now in the no-PMOD and Fab B copies too:
1. **Corner-exact mask check.** The first version took the copper gap minus the 0.05 mm expansion, which overstates the
   clearance near a corner by up to 0.02 mm. It now measures to the pad grown on each axis, with 0.254 mm as the limit.
   Before placement this moved BTN, LD1, LD2 and U2 by 0.14 mm at most.
2. **Text boxes.** The first placement failed the DRC: the X4 dot was 0.222 mm from the "U2" text and the X5 dot
   0.232 mm from the "BTN" text, against Silk to Silk 0.254 mm. Altium measures to a text's box; the Gerber raster
   sees only the strokes. The planner now also keeps 0.254 + 0.01 mm from every text box, read with
   `tools/board_pictures.py read_texts`. That model gives 0.221 and 0.230 mm for those two, matching the DRC. X4 and
   X5 moved 0.05 mm up; LD1 and LD2 dropped to 0.25 mm.
3. **RESET added,** see above. BTN's dot moved to the spot it shares with RESET.

After each re-plan the placed dots were removed with `RemovePin1Dots` and added again. The script project was closed
and re-opened each time, so Altium compiled the new text. `marks.json` is the record of the dots on the board, and a
re-run of the planner reproduces it.

`tools/pin1_dots_emit.py` writes `tools/AsarPin1Dots.pas`, with AddPin1Dots and RemovePin1Dots. Its guards are the
same as the no-PMOD script's, and its path guard is this board.

## Board

`AddPin1Dots` reported "Added 14 of 14".
- **DRC:** 0 warnings, 0 violations, 35 rules including Silk To Solder Mask, Silk to Silk and the five Component
  Clearance rules (Component Clearance ticked for batch) (2026-11-20 21:15:18; `docs/drc_pin1_dots.drc`).
- **Saved:** 21:15:10. MD5 **35871b35350907565314831ca84ad389**, SHA-256 64C179D1...7F40BDA0 (was c304041a).
- **Read back from the file:** 14 overlay arcs (there were 0), each owned by its part, at the planned centre and size.
- **Microvias:** `mark_microvias.py --expect 1168 --verify` gives 1168 verified.
- **Backup:** `backups/asar_feather.PcbDoc.pre-pin1-dots` (c304041a).

## Library

The library keeps footprints the board does not use, 53 in all, so Make PCB Library cannot replace it. The steps:
1. Make PCB Library ran on the board and wrote `asar_feather1.PcbLib`. That file was excluded from the project and
   moved out. It held the 39 board footprints plus seven `_2` duplicates from 0.0001 mm origin differences, as on
   2026-11-19.
2. The 9 footprints whose dot sits at one footprint-relative spot on every instance (32X25, EVERLIGHT-19-337,
   FBGA-54-8X8-P0.8, JST-S2B-PH-SM4-TB, JST-SM04B-SRSS-TB, PTS810, QFN-64-9X9-P0.5-EP4.35, WSON-8-6X5-P1.27,
   XC7A35T-CPG236) were copied from it into the existing library. The copy is whole OLE footprint storages, made with
   pythoncom (`MoveElementTo`, copy mode), and the file was then compacted.
3. **LED0603 stays without a dot.** Its two rotation groups need different spots. "Update from PCB library" on an LED
   would therefore remove its board dot; re-run AddPin1Dots afterwards.

Checks on the result:
- **KiCad 10's Altium reader:** the same 53 footprints. The 9 gain exactly one silkscreen circle each; their pads and
  models are unchanged, and every other footprint is identical.
- **3D bodies:** they are shape-based extrusions with no embedded model data. Their outlines are equal; only the
  per-body GUIDs, checksums and 2D reference points differ, as in the board's copy.
- **Library tables:** the library-level tables (ComponentParamsTOC, Models) are unchanged.
- **Altium:** it opens the library and shows the dot (32X25 checked). Closing it left the file unchanged.

The library is now MD5 4f3c9b4f5529a04778b6e89c8b2e0a92; it was 9cce7aa8, kept as
`backups/asar_feather.PcbLib.pre-pin1-dots`.

## Release

**Gerbers** (21:16:06), rendered against the earlier 2026-11-20 export:

| Layers | Result |
|---|---|
| All copper, both masks, both pastes, the outline, GBO | pixel-identical |
| GTO | gains exactly the 14 dots |

**NC drill** (21:16:34; "separate plated / non-plated" and G85 ticked):
- every drill file and the LDP are byte-identical;
- the DRR differs only in its date and processing-time lines.

**Packages** (still PROVISIONAL):
- `fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-20_PROVISIONAL.zip`: **PASS**, 25 entries, body gate 0 fail /
  5 warn; SHA-256 3CDD611A...BCAA35B41.
  - The packager is retargeted to the new board hashes.
  - The notes gain a paragraph: this package replaces the earlier 2026-11-20 one, adds only the dots, and leaves
    copper, mask, paste and drills unchanged.
  - The via-in-pad CSV and `tools/fab_facts.json` are unchanged.
- `assembly/Asar_Feather_PCBWay_Assembly_2026-11-20_PROVISIONAL.zip`: **ASSEMBLY_RELEASE PASS (PROVISIONAL)**;
  SHA-256 60E3596D...971C33F4.
  - The CPL is unchanged.
  - The notes say the silkscreen marks pin 1 and the LED cathodes, and that U7 and U8 have no room for a dot. They
    also note BTN/RESET pin 1.
  - LD0's mark on the drawings is a red bar across its cathode column (`LED_CATHODE_PADS`) instead of a dot on pad 1,
    an anode.
  - The BOM changes only in the LD0 line note.
- The earlier 2026-11-20 packages had the same file names; they remain in git history (257867d).
