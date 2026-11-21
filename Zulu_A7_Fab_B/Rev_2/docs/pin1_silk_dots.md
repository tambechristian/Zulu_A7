# Pin-1 and cathode silkscreen dots (2026-11-20)

PCBWay held an earlier Zulu A7 HDI order to ask where pin 1 and the LED cathodes were, because that board's silkscreen
had no polarity marks. The no-PMOD Rev 2 board got dots first (`Zulu_A7_no_pmod/Rev_2/docs/pin1_silk_dots.md`, which
has the method and its rules). This board, synced with the no-PMOD board earlier the same day, had the same gap: only
U2, U10 and X4 had a tick. It now carries a dot beside pin 1 of every polarized part and beside each LED cathode.
Silkscreen only: copper, solder mask, paste and drills are unchanged.

## The dots

Each dot is a full-circle arc (radius = diameter / 4, line width = diameter / 2) owned by its part, on that part's
overlay layer. The placement matches the no-PMOD board except Q1, U2 and X4, whose surroundings differ here.

| Part | Side | Marks | Dot centre (mm) | Diameter (mm) | Gap to the marked pad (mm) | Dot edge to exposed copper (mm) | Dot edge to the mask opening (mm) |
|---|---|---|---|---|---|---|---|
| BTN | Top | pin 1 | (16.350, 9.870) | 0.40 | 0.515 | 0.315 | 0.247 |
| LD0 | Top | cathodes (pads 2/4/6) | (20.600, 9.285) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD1 | Top | cathode K | (23.950, 11.560) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD2 | Top | cathode K | (23.950, 13.160) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD3 | Top | cathode K | (23.950, 16.360) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD4 | Top | cathode K | (23.950, 17.960) | 0.40 | 0.515 | 0.315 | 0.256 |
| Q1 | Top | pin 1 | (39.400, 21.800) | 0.40 | 0.515 | 0.315 | 0.247 |
| U1 | Top | ball A1 | (41.675, 17.225) | 0.40 | 0.721 | 0.521 | 0.465 |
| U2 | Top | pin 1 (beside its existing tick) | (25.325, 18.875) | 0.40 | 0.574 | 0.374 | 0.304 |
| U3 | Bottom | pin 1 | (39.485, 5.495) | 0.40 | 0.515 | 0.316 | 0.261 |
| U4 | Top | pin 1 | (42.985, 22.490) | 0.40 | 0.517 | 0.317 | 0.259 |
| U7 | Bottom | pin 1 | (7.825, 20.400) | 0.30 | 0.475 | 0.325 | 0.260 |
| U8 | Bottom | pin 1 | (6.300, 11.250) | 0.40 | 0.925 | 0.325 | 0.275 |
| X4 | Top | pin 1 (battery +), beside its existing tick | (29.065, 8.375) | 0.40 | 0.825 | 0.625 | 0.575 |

- **Clearances:** the Silk To Solder Mask rule (0.254 mm) measures to exposed copper, the first clearance column. The
  second is to the mask opening: the pad grown by 0.05 mm on each axis, measured corner-exact. BTN and Q1 are 0.247 mm
  from an opening corner. As on the no-PMOD board, they were planned with the first version of the pad check and are
  kept; see "Planner versions" in the no-PMOD doc. U1's lands are round, so its figures are lower bounds.
- **No dot:**
  - U10 keeps its tick beside pin 1 (21.15-21.60, 18.60).
  - X1, X2, X3 and J1 are keyed or hand-placed.
- **LEDs:** LD1-LD4 share the LED0603 footprint and its footprint-relative spot.

## How the spots were chosen

`tools/route/pin1_dots/plan_marks.py` is the no-PMOD planner with a CONFIG block for this board:
- it reads the release Gerbers from before the dots out of git (commit ac173c1, the earlier 2026-11-20 fabrication ZIP);
- it reads each part's side, rotation and pattern from the board;
- the board-edge check follows the GM outline;
- footprints are grouped by footprint and side with rotation-aware offsets.

It writes `marks.json`, the record of the dots on the board. Like the no-PMOD planner, it now has the corner-exact
check, which came after these dots were placed; a re-run moves a few spots. Restore `marks.json` from git after a
re-run.

`tools/pin1_dots_emit.py` writes `tools/FabBPin1Dots.pas`, with AddPin1Dots and RemovePin1Dots. Its guards are the
same as the no-PMOD script's, and its path guard is this board.

## Board

`AddPin1Dots` reported "Added 14 of 14".
- **DRC:** 0 warnings, 0 violations, 32 rules including Silk To Solder Mask, Silk to Silk and Component Clearance
  (2026-11-20 20:44:33; `docs/drc_pin1_dots.drc`). Component Clearance was unticked for batch DRC in this
  board's DRC setup and was ticked for this run (Tools > Design Rule Check > Placement); check it before any release
  DRC.
- **Saved:** 20:44:07. MD5 **14a06f6db345784fc7db393c3387d243**, SHA-256 FBD5FD5B...A938889B (was 5fea1304).
- **File size:** the file shrank from 5.1 MB to 4.6 MB on this save, from Altium rewriting its embedded fonts. The
  stream diff against the backup shows +14 Arcs6 records; the other streams differ only in bookkeeping.
- **Microvias:** `mark_microvias.py --verify` gives 1293 verified.
- **Backup:** `backups/zulu_a7_fab_b.PcbDoc.pre-pin1-dots` (5fea1304).

## Library

Design > Make PCB Library made `zulu_a7_fab_b.PcbLib` from the board. It was saved, excluded from the project (not
deleted), closed, and moved over `zulu_a7.PcbLib`. The library is now MD5 04247a33, SHA-256 EE021FC0...F057D7519; it
was 2a305375, kept as `backups/zulu_a7.PcbLib.pre-pin1-dots`.

KiCad 10's Altium reader shows:
- the same 32 footprints;
- the 11 marked footprints (32X25, EVERLIGHT-19-337, FT2232HQ-QFN64, JST-S2B-PH-SM4-TB, LED0603, PTS810, QFN28-UFD-4X5,
  SOIC-8_208MIL, SOT23-5, TSOPII-54, XC7A35T-CPG236) each gained exactly one silkscreen circle;
- every pad and 3D model, and every other footprint, is unchanged;
- there are no `_2` variants.

## Release

**Gerbers** (20:45:26), rendered against the earlier 2026-11-20 export:

| Layers | Result |
|---|---|
| All copper, both masks, both pastes, the outline | pixel-identical |
| GTO | gains exactly the 11 top dots |
| GBO | gains exactly the 3 bottom arcs (U3, U7, U8). The raster extents moved with the new U8 dot, so this was checked by text diff: three arcs, apertures renumbered, one text block reordered. |

**NC drill** (20:46:04, G85 ticked):
- TX3, TX6, TX7, TX9, TX10, SlotHoles and the LDP are byte-identical.
- RoundHoles.TXT holds the same 389 holes, the same multiset of tool, x and y; only the drilling order changed.
- The DRR changed in its date line, T5's route length (260.40 -> 235.35 mm, the path between holes) and the processing
  time.

**Packages:**
- `tools/fab_facts.py` re-run: only its `source` block (board hashes and file size) changed.
- `fabrication/Zulu_A7_Fab_B_Rev_2_PCBWay_Fabrication_2026-11-20.zip`: **PASS**, 23 entries, body gate 0 fail /
  15 warn; SHA-256 AC041DE5...05DED9C3.
  - The packager is retargeted to the new board hashes. EXPECTED_MICROVIA_TOTAL stays 1293.
  - `fab_notes.py` says this package supersedes both the 2026-11-11 package and the earlier 2026-11-20 one, and adds a
    silkscreen sentence to CHANGES.
- `assembly/Zulu_A7_Fab_B_Rev_2_PCBWay_Assembly_2026-11-20.zip`: **ASSEMBLY_RELEASE PASS**; SHA-256
  6B894DDF...9755DD8ED.
  - The CPL is unchanged.
  - The notes say the silkscreen marks pin 1 and the LED cathodes.
  - LD0's mark on the drawings is now a red bar across its cathode column (`LED_CATHODE_PADS`) instead of the pin-1
    dots on pad 1, an anode.
  - The drawings also carry a pin-1 convention made the same day in another session (19:09, after "U4 is missing the
    red dot"): every multi-pin part gets a dot on pad 1/A1 plus a larger dot just outside its outline, and 2-pin
    R/C/L get none. That session could not regenerate the drawings (Acrobat had the PDF open), so this package is the
    first with it. Top page 0 went from 34 pad dots to 12 pad dots plus 12 outer dots. The notes describe it.
  - The BOM changes only in the LD0 and X4 line notes.
- The earlier 2026-11-20 packages had the same file names; they remain in git history (ac173c1).
