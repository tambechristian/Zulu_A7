# C11 back beside U4 pin 8 (2026-11-17)

## Why

The schematic (sheet 4, asar_a7_3) draws C11 (0.1 uF 0402) as the SPI boot flash U4's VCC bypass, but the placement
planner had put it on the bottom under U3 with C3-C9 (pads (32.93, 7.23) GND / (34.23, 7.23) VCC3V3). U4 (W25Q128JVPIQ,
WSON-8, top) had no capacitor within 11.5 mm of its VCC pin 8: its fast switching and program/erase current came through
the planes from caps under U3. The no-PMOD / Fab B boards are fine by accident (three 4.7 uF 0603 sit 1.5-1.9 mm from
their U4 pin 8). Found by the sheet-4 review (docs/u3_sheet_layout.md); the user chose to move C11 ("Yes, move C11").

## Change (`tools/route/c11move/build.py`, `tools/AsarC11Place.pas`, `tools/FeatherCopper_C11Move.pas`)

- C11 flipped to the TOP, horizontal (CPL rotation 180): VCC3V3 pad 2 at (48.30, 17.505), 0.30 mm east of U4-8;
  GND pad 1 at (49.60, 17.505). Designator and comment hidden.
- Removed C11's old copper under U3: VCC3V3 laser L5>Bottom 0.30/0.15 at (33.95, 6.875) (in pad 2), GND through via
  0.35/0.20 at (32.675, 6.85) and its 0.025 mm Bottom stub. Neither was shared (C106 has its own).
- Added: VCC3V3 Top 0.40 mm U4-8 -> C11-2 (U4-8's own via-in-pad already reaches the L5 plane); GND Top 0.40 mm C11-1 ->
  Top>L2 laser 0.30/0.15 at (49.60, 18.35) into the L2 GND plane.
- Gates on the plan: route_check 0 violations / 0 open, hole spacing (nearest same-dielectric hole 2.9 mm), pad_gate
  PASS, no pad-less copper. Nearest other-net copper U4-7 0.57 mm, right edge 0.85 mm, X2 pad 0.55 mm from the via.
- Altium: placement + copper scripts, Repour All, File > Save (19:07:18); the saved board matched the plan exactly
  (4788 tracks, 1575 vias, 840 pads); PcbDoc closed, `mark_microvias.py --expect 1168` (1 marked, 1168 verified;
  the 12:38 X1 backup kept as `.pre-microvia-2026-11-17-x1`), reopened.
- **DRC 0 / 0** over the same 30 rules (`docs/drc_c11_move.drc`, 19:09:52). sch_vs_board MATCH.
- Board: MD5 **c4bf0b71cc7362c33762083bf29810b1**, SHA-256 E356AB95...785BEB. Backup
  `backups/asar_feather_before_c11_move.PcbDoc` (295cdfc5).

## Schematic

Sheet 4's U3 DECOUPLING note no longer lists C11 under U3 (`tools/c11_note_schematic.py`, nets identical; sheet md5
a999eb30 -> eef0ab05, backup `backups/asar_a7_3_before_c11_note.SchDoc`). The drawing already showed C11 at U4.

## Outputs

Gerbers 19:13 and NC drill 19:15 regenerated (the split plated/non-plated and G85 options had reset again and were
re-ticked). Drill deltas: through 156 -> 155, Top-L2 0.15 lasers 208 -> 209, L5-Bottom 0.15 lasers 242 -> 241;
microvia total 1168. `tools/package_fabrication_release.py` retargeted (hash, drill counts); `tools/fab_facts.py` re-run.
Both PASS, same file names (`*_2026-11-17_PROVISIONAL.zip`, the 13:5x X1 versions are in git at 1282dd1):
fabrication zip md5 4b16b28e, assembly zip md5 641c1b83 (after the review's panel note below). CPL: C11 Top (48.95, 17.505) rot 180; 46 top / 128 bottom.
Assembly notes: via-in-pad contacts 275 -> 274 laser, 115 -> 114 through; C11 listed 0.85 mm from the right edge.

## Independent review (workflow wf_9d7bf0d1-08c: diff, DFM, electrical lenses; findings verified by a skeptic)

- Diff: only the planned changes (C11 record + its footprint primitives, 1 track and 2 vias removed, 2 tracks and 1 via
  added, L5 pour lost the one hole of the removed through via, +0.389 mm2); Rules6, Nets6, Polygons6, stack, outline
  byte-identical; 0 unconnected before and after (KiCad and route_conn); nothing left at the old site.
- Electrical: U4's decoupling loop about 0.6-0.8 nH, roughly 4x lower than the ~3 nH plane path to C3 before; the GND
  via 0.85 mm north is fine (L2 is 0.112 mm under Top). U3 keeps eight 0.1 uF (C3-C9, C12) for seven supply balls plus
  C13 10 uF and nearby 4.7/22 uF: adequate.
- DFM: mask web C11-2/U4-8 0.20 mm (same net), U4-7 0.51 mm, new laser tented, bodies >= 1.05 mm apart, mounting-hole
  copper >= 0.93 mm. **Verified minor (new):** C11 is 0.85 mm from the right edge with its long axis perpendicular to
  it (MLCC flex-crack risk at a break-off tab). Fixed in both package notes: no tab or V-cut on the right short edge
  between y 15.5 and 20.3 mm. (Rotating C11 parallel to the edge was judged not worth a re-route.)
- Pre-existing, not changed: U4 has no courtyard/3D body and the C0402 courtyard is oversized (30 such intrusions on
  the board); C8/C9/C12 reach GND through 0.45-0.72 mm of 3 mil track (C12 via an L4 detour) -- widen at the next
  copper edit.
