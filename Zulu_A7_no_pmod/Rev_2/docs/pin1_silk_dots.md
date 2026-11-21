# Pin-1 and cathode silkscreen dots (2026-11-20)

PCBWay held an earlier Zulu A7 HDI order to ask where pin 1 and the LED cathodes were, because that board's silkscreen
had no polarity marks. The assembly drawings showed them, but the assembler works from the silkscreen first. This board
had the same gap: only U2 (a tick), U10 (a tick below pin 1) and X4 (a 0.7 mm tick at x = 29.54, y 8.65-9.35) were
marked. It now carries a dot beside pin 1 of every polarized part and beside each LED cathode, so PCBWay should not need
to ask. Silkscreen only: copper, solder mask, paste and drills are unchanged.

The same work was then done on Fab B Rev 2 and the Asar Feather (their own `docs/pin1_silk_dots.md`); the planner fixes
found there are folded back into this board's copy of the tools (see "Planner versions" below).

## The dots

Each dot is a full-circle arc (radius = diameter / 4, line width = diameter / 2) owned by its part, on that part's
overlay layer.

| Part | Side | Marks | Dot centre (mm) | Diameter (mm) | Gap to the marked pad (mm) | Dot edge to exposed copper (mm) | Dot edge to the mask opening (mm) |
|---|---|---|---|---|---|---|---|
| BTN | Top | pin 1 | (16.350, 9.870) | 0.40 | 0.515 | 0.315 | 0.247 |
| LD0 | Top | cathodes (pads 2/4/6) | (20.600, 9.285) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD1 | Top | cathode K | (23.950, 11.560) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD2 | Top | cathode K | (23.950, 13.160) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD3 | Top | cathode K | (23.950, 16.360) | 0.40 | 0.515 | 0.315 | 0.256 |
| LD4 | Top | cathode K | (23.950, 17.960) | 0.40 | 0.515 | 0.315 | 0.256 |
| Q1 | Top | pin 1 | (39.600, 22.000) | 0.40 | 0.515 | 0.315 | 0.247 |
| U1 | Top | ball A1 | (41.675, 17.225) | 0.40 | 0.721 | 0.521 | 0.465 |
| U2 | Top | pin 1 (beside its existing tick) | (25.325, 18.850) | 0.40 | 0.556 | 0.356 | 0.285 |
| U3 | Bottom | pin 1 | (39.485, 5.495) | 0.40 | 0.515 | 0.316 | 0.261 |
| U4 | Top | pin 1 | (42.985, 22.490) | 0.40 | 0.517 | 0.317 | 0.259 |
| U7 | Bottom | pin 1 | (7.825, 20.400) | 0.30 | 0.475 | 0.325 | 0.260 |
| U8 | Bottom | pin 1 | (6.300, 11.250) | 0.40 | 0.925 | 0.325 | 0.275 |
| X4 | Top | pin 1 (battery +), beside its existing tick | (29.040, 8.375) | 0.40 | 0.850 | 0.650 | 0.600 |

- **The two clearance columns:**
  - The board rule Silk To Solder Mask (0.254 mm) measures to exposed copper (CLEARANCETOEXPOSEDCOPPER=TRUE); that is
    the first column. Every dot clears it by at least 0.06 mm, and the DRC passes.
  - The second column is to the solder-mask opening: the pad grown by the board's largest expansion, 0.05 mm, on each
    axis, so the corners stay square. It is measured exactly here (`pad_gap(..., MASK_EXP)` in the planner). BTN and Q1
    sit 0.247 mm from an opening corner, 0.007 mm under 0.254; that is accepted, see "Planner versions".
  - U1's lands are round; the square model overstates their reach, so U1's figures are lower bounds.
- **No dot:** U10 keeps its existing tick below pin 1, which already fills the only free spot. X1 and X3 are keyed:
  their footprints fit one way only.
- **U7:** a 0.40 mm dot does not fit there, so it has 0.30 mm.
- **LEDs:** LD1-LD4 share the LED0603 footprint, so their dots sit at the same footprint-relative spot: the outer
  corner of pad K, on the side away from the anode. A different spot per LED would have split the footprint into
  variants in Design > Make PCB Library.

## How the spots were chosen

`tools/route/pin1_dots/plan_marks.py` reads the board and the 2026-11-19 release Gerbers (that ZIP is read out of git
commit 427960e; the 2026-11-20 release replaced it in the tree), and writes `marks.json`.

For every polarized SMT part it takes the nearest legal spot to pin 1 that passes all of these:

| Check | Requirement |
|---|---|
| Pad openings (rule Silk To Solder Mask) | 0.254 mm to the exact pad shapes grown by the largest mask expansion (0.05 mm) on each axis; the GTS/GBS raster screens via openings too. |
| Other silkscreen (rule Silk to Silk) | 0.254 mm |
| Part bodies (tools/body_check.py, maximum-tolerance boxes) | outside every body on that side, by at least 0.05 mm |
| Board edge | 0.30 mm |
| Pointing at pin 1 | Either pin 1 (A1; the LED cathodes) is the part's nearest pad by at least 0.15 mm, or, on multi-pin parts, the dot sits within 1.3 mm of the body corner nearest pin 1 and at least 0.5 mm closer to it than to any other corner. |
| Ownership | No other marked part's pads or body may be as close as the part's own, plus 0.15 mm. |

Among the legal spots it favours ones away from pin 1's neighbours. It uses 0.40 mm where that fits, else 0.30 or
0.25 mm.

`tools/pin1_dots_emit.py` turns the plan into `tools/NoPmodPin1Dots.pas`:
- `AddPin1Dots` checks each part's side and the position of its reference pad (to 0.002 mm), and refuses if a dot is
  already there.
- `RemovePin1Dots` undoes `AddPin1Dots`.

**The first pass failed the DRC.** The four LED dots came out 0.225 mm from the exposed copper of their K pads,
against the 0.254 mm rule. The planner had placed the mask raster up to 0.05 mm off. Two fixes:
- the planner now aligns the raster on the board's own pads (top -0.025 mm, bottom -0.050 mm in x) and checks
  clearance against the exact pad shapes;
- the dots were removed with `RemovePin1Dots` and placed again.

A second re-plan then gave the four LEDs their shared spot.

### Planner versions

The dots on this board, and `marks.json`, come from the first version of the exact pad check. That version took the
copper gap minus the 0.05 mm expansion, which overstates the clearance near a corner by up to 0.02 mm, and asked for
0.264 mm. The corner-exact version (grown rectangles, limit 0.254 mm) was written during the Fab B and Asar work and is
the one in the planner now.

Re-run on this board, the corrected planner moves BTN, Q1, U3 and U4 by 0.1-0.3 mm. A looser or tighter limit re-ranks
the spots, so no single limit reproduces the placed set. The placed dots are kept:
- all of them clear the board rule by at least 0.06 mm;
- the DRC passes;
- the worst, BTN and Q1, are 0.247 mm from a mask-opening corner, 0.315 mm from copper. A fab clips silkscreen at
  mask openings anyway.

`marks.json` stays the record of what is on the board. A re-run overwrites it, so restore it from git afterwards.

## Board

`AddPin1Dots` reported "Added 14 of 14 pin-1 dots".
- **DRC:** 0 warnings, 0 violations on the saved board (2026-11-20 20:16:52; `docs/drc_pin1_dots.drc`). It ran the
  same 32 rules as before, including Silk To Solder Mask, Silk to Silk and the three Component Clearance rules.
- **Saved:** 20:16:22. MD5 **8741442752384bc0bc7adf49c4c16f5f**, SHA-256 B2E9716F...0424DB2 (was 9b0341ba).
- **Read back from the file:** exactly 14 overlay arcs (there were 0), each owned by its part, at the planned centre
  and size.
- **Microvias:** `mark_microvias.py --expect 1260 --verify` gives 1260 verified.
- **Backup:** `backups/Zulu_a7_no_pmod.PcbDoc.pre-pin1-dots` (9b0341ba).

## Library

Design > Make PCB Library made a new library from the board. That library was excluded from the project and put in
place as `zulu_a7.PcbLib`, which is now SHA-256 DC5AE49A... (MD5 fbc461b9; it was c61b83db). The old one is kept as
`backups/zulu_a7.PcbLib.pre-pin1-dots`.

Read back with KiCad 10's Altium reader:
- the same 31 footprints;
- the 11 marked footprints each gained exactly one silkscreen circle;
- every pad and 3D model, and every other footprint, is unchanged;
- there are no `_2` variants.

## Release

**Gerbers** (20:17:37), compared with the 2026-11-19 export by rendering both:

| Layers | Result |
|---|---|
| All copper, both masks, both pastes, the outline | pixel-identical |
| GTO | gains exactly the 11 top dots |
| GBO | gains exactly the 3 bottom dots (text diff: three arcs, apertures renumbered) |

**NC drill:** re-exported at 20:24:20 with G85 ticked; the packager needs drill files newer than the board. The drill
files and the LDP are byte-identical; in the DRR only the date and processing-time lines changed.

**Packages:**
- `fabrication/Zulu_A7_no_pmod_Rev_2_PCBWay_Fabrication_2026-11-20.zip`: **PASS**, 23 entries, body gate 0 fail /
  15 warn as before; SHA-256 D2CCE374...B83AAA55.
  - `package_fabrication_release.py` was retargeted to the new board hashes and date.
  - `fab_notes.py` dates the notes 2026-11-20. Its CHANGES section lists the dots and says copper, mask, paste and
    drills are unchanged from the 2026-11-19 package, which this one supersedes.
  - `fab_notes.py` now reads the Fab B Rev 2 board it compares placements with out of git (eb0fbfe, MD5 33023787, the
    2026-11-12 release). The live Fab B board took the no-PMOD sync on 2026-11-20, and comparing against it had
    dropped 11 parts from "parts placed differently" (C87, C88, C94, C99, C106, R1, R34, U2, U4, U10, X4). The notes now
    differ from the 2026-11-19 ones only in the release date, the board hashes, the supersede sentence, the silkscreen
    sentence and the DRC/export times.
- `assembly/Zulu_A7_no_pmod_Rev_2_PCBWay_Assembly_2026-11-20.zip`: **ASSEMBLY_RELEASE PASS**; SHA-256
  1C09B08E...04346E12. The CPL is unchanged.
  - The notes say the silkscreen now marks pin 1 and the LED cathodes.
  - LD0's mark on the drawing is now a red bar across its cathode column (`LED_CATHODE_PADS`), where the silkscreen
    dot is. Before, it was a dot on pad 1, an anode.
  - The BOM changes only in the LD0 and X4 line notes.
- The 2026-11-19 packages are superseded and removed; they remain in git history.
