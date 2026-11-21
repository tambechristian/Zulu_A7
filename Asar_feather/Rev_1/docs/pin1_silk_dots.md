# Pin-1 and cathode silkscreen dots (2026-11-20, U7 added 2026-11-21)

PCBWay held an earlier Zulu A7 HDI order to ask where pin 1 and the LED cathodes were, because that board's silkscreen
had no polarity marks. The no-PMOD Rev 2 and Fab B Rev 2 boards got dots first; the method and its rules are in
`Zulu_A7_no_pmod/Rev_2/docs/pin1_silk_dots.md`. Before this change, only U2, U8, U10 and JP4 on this board had a pin-1
mark (ticks). It now carries a dot beside pin 1 of every other polarized part and beside each LED cathode. Silkscreen
only: copper, solder mask, paste and drills are unchanged.

## The dots

Each dot is a full-circle arc (radius = diameter / 4, line width = diameter / 2) owned by its part, on that part's
overlay layer.

| Part | Side | Marks | Dot centre (mm) | Diameter (mm) | Gap to the marked pad (mm) | Dot edge to exposed copper (mm) | Dot edge to the mask opening (mm) |
|---|---|---|---|---|---|---|---|
| BTN | Top | pin 1 | (39.975, 5.950) | 0.40 | 0.525 | 0.325 | 0.275 |
| RESET | Top | pin 1 | (20.825, 5.300) | 0.40 | 0.525 | 0.325 | 0.275 |
| LD0 | Top | cathodes (pads 2/4/6) | (37.925, 3.225) | 0.40 | 0.525 | 0.325 | 0.275 |
| LD1 | Top | cathode K | (30.550, 3.825) | 0.25 | 0.447 | 0.322 | 0.256 |
| LD2 | Top | cathode K | (33.750, 3.825) | 0.25 | 0.447 | 0.322 | 0.256 |
| LD3 | Top | cathode K | (7.305, 2.655) | 0.40 | 0.525 | 0.325 | 0.275 |
| LD4 | Top | cathode K | (7.305, 3.955) | 0.40 | 0.525 | 0.325 | 0.275 |
| Q1 | Top | pin 1 | (15.435, 16.625) | 0.40 | 0.525 | 0.325 | 0.275 |
| U1 | Top | ball A1 | (29.125, 6.130) | 0.40 | 0.682 | 0.482 | 0.427 |
| U2 | Top | pin 1 | (8.525, 11.675) | 0.40 | 0.537 | 0.337 | 0.267 |
| U3 | Top | ball A1 | (31.425, 6.755) | 0.40 | 1.287 | 1.087 | 1.031 |
| U4 | Top | pin 1 | (40.975, 18.275) | 0.40 | 0.520 | 0.320 | 0.270 |
| U7 | Bottom | pin 1, **under the body** | (5.925, 12.700) | 0.40 | 0.525 | 0.325 | 0.260 |
| X4 | Top | pin 1 (battery +) | (12.825, 14.100) | 0.40 | 0.525 | 0.325 | 0.275 |
| X5 | Top | pin 1 | (44.425, 8.350) | 0.40 | 0.525 | 0.325 | 0.275 |

- **Clearances:** every dot clears the Silk To Solder Mask rule (0.254 mm, measured to exposed copper) and also clears
  the mask opening itself by 0.254 mm. The opening is the pad grown by 0.05 mm on each axis, measured corner-exact.
  U1's and U3's lands are round, so their figures are lower bounds.
- **U7 (SOT-23-5, bottom):** pin 1 is boxed in by neighbouring pads and vias. Outside the body, the only legal spots are
  beside pin 3 or the far pads, which would point at the wrong pin. The user chose (2026-11-21) to put the dot under
  U7's body, between its pad rows, level with pin 1: 0.525 mm from pin 1 and 0.84 mm from the other pins. It is in the
  silkscreen and the GBO Gerber, which is what PCBWay checks, but it is hidden once U7 is placed. The planner allows
  this through CONFIG `under_body`.
- **Existing ticks, no dot:**
  - U8 (QFN-28, bottom): its footprint's tick at x 7.85, y 15.40-15.70, 0.4 mm west of pad 1.
  - U10: its tick west of pad 1 (2026-11-16).
  - JP4 (DNS JTAG test pads, bottom): its tick at x 3.92, y 2.75-3.55.
  - U2 also has its own tick.
- **Not marked:** X1, X2 and X3 are keyed or hand-placed.
- **RESET:** it is the same PTS810 switch as BTN, so it is marked too. Both read the same way and share one
  footprint-relative spot, so the library keeps a single PTS810.
- **LEDs:** LD1/LD2 and LD3/LD4 face opposite ways (rotation groups), so they have different footprint-relative
  spots. LD1 and LD2 sit between the "SCK"/"MO" labels and their K pads, where only a 0.25 mm dot fits.

## How the spots were chosen

`tools/route/pin1_dots/plan_marks.py` is the no-PMOD planner with a CONFIG block for this board:
- it reads the release Gerbers from before the dots out of git (commit 257867d, the first 2026-11-20 fabrication ZIP);
- it reads each part's side, rotation and pattern from the board;
- the edge check follows the rounded GM outline;
- `skip` names the parts whose existing tick counts (U8, U10);
- `under_body` names the parts whose dot may sit under their own body (U7).

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

## Stale ratsnest line (2026-11-21)

The board file still held one saved connection object (ratsnest line) in `Connections6`: CLK-12M-SHARED, from
(15.375, 12.650) to (16.325, 13.750). It was already in the 257867d board, before any dot. It showed in Altium as a
thin diagonal line, but it was not copper or silkscreen and never reached the Gerbers. Altium's DRC found 0 un-routed
nets. It broke the gate in `docs/routing.md` (a fully routed save must have an empty `Connections6`).
- `tools/AsarRebuildConn.pas` is the Rev_1 copy of `FeatherRebuildConn.pas`; the old copy's path guard predates the
  move to Rev_1.
- It re-analysed all 156 nets. 0 connection objects remain, and the saved `Connections6` is empty.
- The log is in "Project Logs for asar_feather/rebuild_conn.log".

## Board

`AddPin1Dots` reported "Added 15 of 15"; RebuildConnections left 0 connections.
- **DRC:** 0 warnings, 0 violations, 35 rules including Silk To Solder Mask, Silk to Silk and the five Component
  Clearance rules (Component Clearance ticked for batch) (2026-11-21 08:38:20; `docs/drc_pin1_dots.drc`).
- **Saved:** 2026-11-21 08:38:08. MD5 **9be75ad9896cf164cd04443e79d76f32**, SHA-256 C7A5AB32...6B5CC698.
- **Read back from the file:** 15 overlay arcs, each owned by its part, at the planned centre and size.
- **Microvias:** `mark_microvias.py --expect 1168 --verify` gives 1168 verified.
- **Stream diff against the 2026-11-20 board:**
  - Arcs6 gains the U7 arc and `Connections6` is empty.
  - The other changes are bookkeeping: the save date and 2D view settings, texture centre/rotation display values normalised on
    seven bodies (no texture is used), cached MANHATTANLENGTH fields dropped from the net records, and Altium's re-saved embedded fonts.
- **Backups** (backups/ is gitignored):
  - `asar_feather.PcbDoc.pre-pin1-dots` (c304041a, before any dot);
  - `asar_feather.PcbDoc.pre-u7-dot` (35871b35, the 2026-11-20 board).

## Library

The library keeps footprints the board does not use, 53 in all, so Make PCB Library cannot replace it. The steps:
1. Make PCB Library ran on the board and wrote `asar_feather1.PcbLib` (the name `asar_feather.PcbLib` is taken). That
   file was excluded from the project and moved out. It held the board's footprints plus `_2` duplicates from
   0.0001 mm origin differences, as on 2026-11-19.
2. The 10 footprints whose dot sits at one footprint-relative spot on every instance were copied from it into the
   existing library: 32X25, EVERLIGHT-19-337, FBGA-54-8X8-P0.8, JST-S2B-PH-SM4-TB, JST-SM04B-SRSS-TB, PTS810,
   QFN-64-9X9-P0.5-EP4.35, SOT23-5 (2026-11-21), WSON-8-6X5-P1.27 and XC7A35T-CPG236.
   - The copy is whole OLE footprint storages, made with pythoncom (`MoveElementTo`, copy mode), and the file was then
     compacted.
3. **LED0603 stays without a dot.** Its two rotation groups need different spots. "Update from PCB library" on an LED
   would therefore remove its board dot; re-run AddPin1Dots afterwards.

Checks on the result:
- **KiCad 10's Altium reader:** the same 53 footprints. The 10 gain exactly one silkscreen circle each; their pads and
  models are unchanged, and every other footprint is identical. On 2026-11-21 only the SOT23-5 storage changed.
- **3D bodies:** they are shape-based extrusions with no embedded model data. Their outlines are equal; only the
  per-body GUIDs, checksums and 2D reference points differ, as in the board's copy.
- **Library tables:** the library-level tables (ComponentParamsTOC, Models) are unchanged.
- **Altium:** it opens the library and shows the dot (32X25 checked on 2026-11-20). Closing it left the file unchanged.

The library is now MD5 9cc2ac8efd49ef66be2256b727519dea. Backups: `backups/asar_feather.PcbLib.pre-pin1-dots`
(9cce7aa8) and `backups/asar_feather.PcbLib.pre-u7-dot` (4f3c9b4f).

## Release (2026-11-21)

**Gerbers** (08:39:36), rendered against the 2026-11-20 21:16 export:

| Layers | Result |
|---|---|
| All copper, both masks, both pastes, the outline, GTO | pixel-identical |
| GBO | gains exactly the U7 dot |

Against the export before any dot, GTO gains the 14 top dots and GBO the U7 dot.

**NC drill** (08:40:04; "separate plated / non-plated" and G85 ticked): every drill file and the LDP are byte-identical;
the DRR differs only in its date line.

**Packages** (still PROVISIONAL), dated 2026-11-21; they replace both 2026-11-20 packages, which remain in git history
(257867d, 38f86b6):
- `fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-21_PROVISIONAL.zip`: **PASS**, 25 entries, body gate 0 fail /
  5 warn; SHA-256 7F48DA33...F8FA8958.
  - The packager is retargeted to the new board hashes and date.
  - The notes' paragraph lists the top-side dots and U7's dot under its body, notes U8's tick, and says copper, mask,
    paste and drills are unchanged.
  - The via-in-pad CSV and `tools/fab_facts.json` are unchanged in content.
- `assembly/Asar_Feather_PCBWay_Assembly_2026-11-21_PROVISIONAL.zip`: **ASSEMBLY_RELEASE PASS (PROVISIONAL)**;
  SHA-256 54244030...39964875.
  - The CPL and BOM are unchanged from 2026-11-20.
  - The notes say the silkscreen marks pin 1 and the LED cathodes, that U7's dot is under its body, and that U8 and
    U10 have ticks. The U7, U8 and BTN/RESET lines say the same.
  - LD0's mark on the drawings is a red bar across its cathode column (`LED_CATHODE_PADS`) instead of a dot on pad 1,
    an anode.
