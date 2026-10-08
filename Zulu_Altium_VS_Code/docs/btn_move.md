# BTN moved 0.5 mm left; X2 designator hidden (2026-10-07)

The user found BTN (PTS810, the user button) too close to the RGB LEDs and asked for it to move a little to the
left. They also asked for X2's designator to be hidden. Both changes were made on all three copies (production,
HDI_Optimized, KiCad).

BTN moved 0.5 mm west, from x 20.3 to 19.8 mm (y 12.92 and rotation 90 unchanged):

| Gap, pad edge to pad edge | Before | After |
|---|---:|---:|
| BTN pad 4 to LD5's A pad (east) | 0.40 mm | 0.90 mm |
| BTN pad 2 to C158 pad 2 (west, now the nearest) | 0.94 mm | 0.70 mm |

X2's designator had been printed off the board edge at (0.78, 26.6). It is now hidden (`NameOn := False`).

## Why it took copper work

BTN's four pads straddle via stacks that sit between its pad pairs. Any shift to the left lands pads on other nets'
copper, so a few stacks had to move:

| Object | Before | After |
|---|---|---|
| LED0_B Top>L3 stack (2 lasers) | (20.80, 10.60) | (21.50, 10.55) |
| N$BTN Top>Bottom stack (5 vias) | (22.00, 10.60) | (20.875, 10.47), inside pad 3 |
| FT-RESETN Top>Bottom stack (5 vias) | (18.45, 15.50) | (18.15, 15.50) |
| VCC3V3 through via for pad 1 | (18.50, 10.50), 0.35/0.20 | removed |
| VCC3V3 Top>L5 stack for pad 1 (3 lasers + 1 buried) | none | (18.47, 10.45), lands on the L5 plane |

Pad 1's through via had no legal through-via site left. The spot sits between FT-VPLL on L3 and FT-VPHY on L4, both
0.5 mm wide. A Top>L5 microvia stack fits, because it never reaches L6 and its lands are smaller.

Tracks: 14 were re-drawn and 3 FT-RESETN Top tracks were added. They belong to the routes that end on BTN's pads
or on the moved vias; some are middle segments of those routes.
- **LED0_B** now leaves its LED pad along y 11.61 to x 21.85, then drops to the new stack. Its L3 leg runs from
  the stack to (21.45, 9.95).
- **FT-RESETN's west branch** turns at (18.70, 13.90) and reaches its stack along x 18.15.
- **FT-RESETN's north branch** steps around pad 3 via (20.15, 10.35) and (20.55, 9.95).
- **N$BTN** reaches pad 3 through the stack in the pad. The Bottom track (21.30, 11.30) now ends there.

## Via-in-pad

Before the move no via touched any SMD pad on the board. After it, three filled Top-L2 microvias overlap BTN's pads:
- pad 3 holds the N$BTN stack (inside the pad);
- pad 1's new VCC3V3 stack crosses the pad edge;
- pad 4 overlaps the edge of the existing N$BTN stack at (20.50, 15.50).

All are stacked microvias, which are copper-filled and planarized anyway. Both fab notes now say this explicitly
and ask for them to be capped flat (VIPPO) so the pads take paste normally.

## How it was checked and applied

1. **Plan check.** Scratchpad `btn/btnplan.py` applied the plan to a model of every copper object and checked each
   edited object on every layer it spans. Rules checked: 0.09 mm clearance, 0.10/0.20 mm for the SDRAM classes on
   L3/L4, 0.24 mm hole to hole.
   - Result: 0 violations on both boards.
   - Tightest margin: 0.100 mm, between the moved FT-RESETN stack and NetLD3_A's Top track.
   - Connectivity: every track that ended at a moved or deleted via, or at a BTN pad, is in the plan.
2. **Script.** `tools/BtnMove.pas` (both copies) was generated from the checked plan by `btn/emit_pas.py`.
   - `BtnCanary` (read only) confirmed all 14 tracks and 13 vias at their expected places.
   - `MoveBtn` then refused to change anything unless all were found.
   - Ran on the HDI board, then on production.
3. **Microvia type.** Vias created by script default to the regular drill type. Each board was saved and closed,
   then `tools/stage13_mark_microvias.py` marked exactly the three new laser vias (expect 1,041 here, 1,016 on HDI).
   `--verify` passes. The moved stacks kept their microvia type.
4. **DRC.** Reopen, Repour All, DRC, save, DRC again:

| Board | DRC (after the final save) | PcbDoc SHA-256 |
|---|---|---|
| Production | 16:53, 0 warnings, 0 violations (27 rules tested, including the IsMicroVia and IsBuriedVia hole sizes) | `89a421b9060195d66bed82f7a4e7d80121bd0e9d679a3fee32289e8f541f4bde` |
| HDI_Optimized | 16:48, 0 warnings, 0 violations | `f97d0f4d6fb9439addf64bd6da2620e2bf3d35228e0cc4b053859f38bdb5e64b` |

5. **Saved file.** Read back with altium_monkey:
   - BTN pads at x 18.725 / 20.875;
   - X2 `name_on` false;
   - tracks 4,828 -> 4,831;
   - vias 1,787 -> 1,790 (HDI 1,768 -> 1,771).

Production via census after the move:

| Span | Count |
|---|---:|
| Through | 379 |
| Top-L2 | 297 |
| L2-L3 | 283 |
| L3-L4 | 370 |
| L4-L5 | 231 |
| L5-Bottom | 230 |

## Outputs

NC drill (G85 ticked) and Gerbers were regenerated at 16:54 and copied over the release files in
`Imported zulu_a7.PrjPcb/`. Geometry against the previous release:

| File | Change |
|---|---|
| `RoundHoles.TXT` (through) | -1 hole, (18.50, 10.50) |
| `TX3/TX6/TX7/TX9` (L3-L4, Top-L2, L2-L3, L4-L5) | stack holes moved, +1 hole each, (18.47, 10.45) |
| `TX10` (L5-Bottom) | stack holes moved only |
| `SlotHoles.TXT` | identical |
| GTL, G1-G4, GBL | changes only inside x 17.9-22.8, y 9.9-16.3 |
| GTS, GTP | BTN's four pad openings moved 0.5 mm |
| GTO | BTN designator moved 0.5 mm; X2 designator removed |
| GBO, GBS, GBP, GM | identical |

Outside the BTN area the L2 plane fill dropped five vertices that lie on straight edges (under 0.0001 mm off the
line). The repour simplified them; the copper is the same.

- `fabrication/PCBWAY_FAB_NOTES.txt`: source commit, board hash, the via-in-pad paragraph, the DRC time and the
  via counts.
- `fabrication/Zulu_A7_PCBWay_Fabrication_2026-10-07.zip` was rebuilt with the same 23 entries in the same order,
  each byte-identical to its source. SHA-256 `5CD6CF51D71D3FF0AF3D459530F76B4D871CC08D6757DDCFA2214FBAB287961E`.

## Assembly

`tools/generate_jlcpcb_assembly.py --release-date 2026-10-07` was re-run. Only BTN's CPL row changed
(19.8000 mm, was 20.3000 mm). The BOM is byte-identical. The notes carry the new board hash, and the drawings show
BTN in its new place.

## Other copies

- **HDI_Optimized:** same plan and script. Its fab notes, packager expectations and both zips were updated; see
  `HDI_OPTIMIZATION_NOTES.md`.
- **KiCad:** see the next section.

## KiCad

`Zulu_kicad/tools/apply_btn_move.py` copies the change from KiCad's import of this board. It takes the
track/via difference (matched on geometry, 14/17 tracks and 13/16 vias), BTN's position, X2's hidden reference and
the two plane fills.
- `geom_diff.py` against a fresh import: IDENTICAL.
- DRC with schematic parity: 0 parity issues, 0 unconnected items.

Details are in `Zulu_kicad/CONVERSION.md`.
