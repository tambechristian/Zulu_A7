# U2 pin-1 silk mark restored (2026-11-20)

U2 (FT2232HQ, QFN-64-9X9-P0.5-EP4.35) had no pin-1 mark on the silkscreen, and since the 2026-11-19 library rebuild
(docs/body_fixes.md) the library footprint had none either. Both now carry the original mark again.

## What the mark is and why it was gone

- The footprint generator put it there from the first commit (05e1dd5, `tools/footprints.py` line 54,
  "pin-1 tick beside pad 1"): one Top Overlay line, 0.15 mm, footprint-relative (-5.25, +3.25) -> (-5.25, +3.75)
  (Altium axes, y up), 0.45 mm outside the toe of pads 1 and 2 and spanning their centres.
- `tools/FeatherSilkFix4.pas` deleted it on 2026-10-23 (commit 18f5d3a). Its log says "X1 mark at x 8.45: no clean spot
  within 1 mm, deleted", but the track belonged to U2. The old USB-C X1 (HRO TYPE-C-31-M-12) had pads reaching
  close to the mark, and the DRC flagged X1-2 and X1-3 against it (docs/drc_prerouting.drc at e187bb4). That X1 is now the
  micro-B at (4.125, 11.43), whose nearest pad is 3.6 mm away, so the reason is gone. (The old X1's copper reached
  x 8.42; its mask openings touched the mark.)
- U2 has not moved since: origin (13.7, 7.4), rotation 0, Top, in 05e1dd5, e187bb4 and today's board. On the board
  the mark is (8.45, 10.65) -> (8.45, 11.15).

Checked before placing (workflow wf_e7a53689-c93, two independent agents, both OK):

| Check | Value | Rule |
|---|---|---|
| Silk to U2-1 / U2-2 mask opening (U2's own expansion 0.035 mm, GTS-confirmed) | 0.340 mm | 0.254 |
| same with the default 0.05 mm expansion | 0.325 mm | 0.254 |
| Silk to exposed copper | 0.375 mm | |
| Silk to other silk (U2's NW corner tick) | 0.728 mm | 0.254 |
| Nearest Top body (U2's own) | 0.675 mm | |
| Board edge | 8.375 mm | |

No via overlaps the mark. The nearest are buried L4-L5 / L5-Bottom vias 0.079 and 0.199 mm from its edge (no Top
copper), and the nearest Top vias are 0.32 mm away and tented, so no mask opening clips it. X4's comment text, hidden
today (COMMENTON false), has a box over the mark: leave it hidden.

## Board

`tools/AsarU2Pin1.pas` RestoreU2Pin1 (refuses unless U2 is at (13.7, 7.4), rotation 0, Top, on QFN-64-9X9-P0.5-EP4.35
with its 8 corner ticks) adds the track to U2: "U2 now owns 9 Top Overlay tracks". DRC before saving: 0. Saved
07:07:20; 1168 microvias verified (`mark_microvias.py --verify`).

Board MD5 **c304041a1984b9034f27d4055a241c9c**, SHA-256 11C361CC...FB0E91E (was 091a3b6e).

**DRC 0 warnings / 0 violations, 35 rules including Silk To Solder Mask, Silk to Silk and Component Clearance**
(`docs/drc_u2_pin1.drc`, 07:15:27 on the saved board).

## Library

Altium 26.11.1 cannot add primitives in a PcbLib script, so one of QFN-64-9X9-P0.5-EP4.35's corner ticks was
duplicated in the editor (Edit > Duplicate), and `tools/AsarLibU2Pin1.pas` MovePin1Mark moved that one track (the only
Top Overlay track that is not a corner tick; coordinates measured from pad 1) to (-5.25, +3.25) -> (-5.25, +3.75),
0.15 mm. Saved 07:14:17, `asar_feather.PcbLib` MD5 **9cce7aa87f5771b87c62fd207e52a56f** (was 600f9b7b). Read back with
KiCad: the same 53 footprints; QFN-64 has the 8 corner ticks and the mark, the line the old library
(`backups/asar_feather.PcbLib.pre-bodies3d`) had. A later Update from library on U2 keeps the mark.

The other footprints whose silk Make PCB Library trimmed on 2026-11-19 (TDFN-8, WSON-8, FBGA-54) are unchanged.

## Release files

Gerbers 07:15:56 and NC drill 07:16:27 (same setup: split plated / non-plated, G85). Against the 2026-11-19 release
`asar_feather.GTO` gains exactly one stroke (X8.45 Y10.65 -> Y11.15, aperture D10 = 0.15 mm round); apart from that,
every Gerber differs only in its `TF.SameCoordinates` GUID comment, the drill files are byte-identical, and the DRR
differs only in its date line.

- `package_fabrication_release.py` retargeted (hash, date 2026-11-20):
  `fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-20_PROVISIONAL.zip` PASS (body gate 0 fail, 5 warn as before).
- `generate_pcbway_assembly.py` (date): `assembly/Asar_Feather_PCBWay_Assembly_2026-11-20_PROVISIONAL.zip` PASS.
  BOM, CPL and the via-in-pad CSV are unchanged. The fabrication notes change in date, board hashes and DRC time; the
  assembly notes in date, board SHA-256 and fabrication ZIP name, and they no longer say U10 has no silkscreen polarity
  mark (it has had a pin-1 tick since 2026-11-16, `docs/x4_jst_entry.md`; that sentence was stale in every release
  since). The drawing PDFs differ only in the date.
- The 2026-11-19 packages are superseded and removed (they stay in git history).
- `tools/fab_facts.json` is unchanged (silk is not in it).
- Board pictures redrawn from c304041a (the mark shows left of U2's top-left corner); the top title now gives the
  PcbDoc's save date instead of a fixed 2026-11-18.

## Other parts' marks

U10 (93LC46B EEPROM, TDFN-8) lost its tick in the same 2026-10-23 clean-up and got one back on 2026-11-16 (west of
pad 1 at (4.15, 17.35) -> (4.15, 17.55); `docs/x4_jst_entry.md`). The 0603 LEDs (LED0603, EVERLIGHT-19-337) have no
polarity mark; the assembly notes tell PCBWay to orient them from the drawings.

## Save side effects (independent review, workflow wf_42c7914c-765)

The review compared both files with master stream by stream. Board: Tracks6 gained only the mark (byte-identical to the
original record in 05e1dd5 / e187bb4 except the component index), and every other track is unchanged though Altium
re-ordered them. The rest is save bookkeeping: Board6 date and viewport; the four script-made Component Clearance
rules normalised from LAYER=UNKNOWN to LAYER=TOP; 58 bodies' TEXTUREROTATION 0 -> 360; font-buffer padding in Texts6;
the glyph cache; PrimitiveGuids (+1). Library: only QFN-64 gained a primitive (the mark, byte-identical to the old
library's). The re-save cleared pad cache bytes, dropped trailing default pad-shape entries on XC7A35T-CPG236 and
AMPHENOL (now identical to the board's), reset MODEL.2D.X/Y on 20 extruded bodies (outlines and heights identical) and
reversed the record order of 1X03-NOSILK (same geometry and GUIDs). KiCad's reader finds every footprint's pads and
graphics identical except the new QFN-64 line.
