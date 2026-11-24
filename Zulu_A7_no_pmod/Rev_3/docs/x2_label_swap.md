# X2 pin names in the number row; title, U1 and U4 labels lowered (2026-11-24)

Silkscreen only. Copper, mask, paste, drill, outline, stack-up, parts, BOM and placement are unchanged.
The same change was made on Fab B Rev 2 (`Zulu_A7_Fab_B/Rev_2/docs/x2_label_swap.md`).

## Why

PCBWay's assembly photos of the first Zulu A7 order showed two things:

- The FPGA U1 and the flash U4 look as if they overlap. On that ordered board, U4's body really does overlap U1's
  by 0.14 mm (nominal). On this board, U4 was moved 0.4 mm north on 2026-11-14 and clears U1 by 0.26 mm. The
  printed "U1" sat beside U4 and read as U4's label.
- X2's strips, fitted with the housing on the bottom, hit U10 (see "X2 header housings" below).

The board owner asked to remove the channel-label row and lower U1, U4 and the title. In answer to the follow-up
questions, they chose:

- **Silkscreen only**, with no part moves.
- **Names into the numbers' place:** "swap channel names with pin numbers, and remove pin numbers". This covers the
  power and control names too.
- **Boards:** this one and Fab B Rev 2.

## The change

Later the same day R4's label also moved: see "R4 label" below. The final board is MD5 `66148256`.


| Item | Before | After |
|---|---|---|
| X2 pin names (1V0, 1V8, 3V3, GND, C7-C13, C0, AI0, AI1, C14-C28, RST, VU) | inner row (y 20.939 top / 3.661 bottom) | the pin-number row next to the pins (y 22.189 / 2.411), x unchanged |
| X2 pin numbers (30 texts: 3, 10-40) | printed | removed |
| '2 CLK' (vertical) | | 'CLK', letters where they were (anchor y 19.255 -> 20.855) |
| '30 C20' (vertical) | | 'C20' in 30's place |
| Pin 21 | '21' only (a vertical 'GND' hits X5's MP1 tab) | horizontal 'GND' at (58.45, 2.411) in the name row |
| Title 'ZULU A7 2.4' | y 5.00 | y 3.77 (down 1.23 mm) |
| U1 label | designator at (39.70, 16.55), beside U4 | free text 'U1' at (45.867, 5.63), centred under the FPGA; the designator is hidden |
| U4 label | designator hidden | free text 'U4' at (52.60, 19.40), right of U4 at its mid-height |

Pins 1 and 4-9 (GND, C1-C6) had no label before and still have none: the row there sits on U4 and R4.

The printed U1 and U4 are free texts because in this Altium a designator's XLocation write does not hold (see
memory `altium-delphiscript-traps`). If U1's designator is ever switched back on, it reappears at (39.70, 16.55)
as a second "U1".

The labels are spread evenly between the name row and the FPGA body: name row, 0.32 mm, title, 0.39 mm, U1 label,
0.47 mm, U1 body.

## Clearances (tightest, Altium stroke-font ink)

| Pair | Gap (mm) | Rule |
|---|---|---|
| Name rows to the X2 pad mask | 0.254 | silk-to-mask 0.254, same as the old number rows |
| Adjacent names | 0.257 | silk-to-silk 0.254, unchanged x spacing |
| 'C20' to the title | 0.305 | silk-to-silk |
| Name row to the title | 0.324 | silk-to-silk |
| Title to the 'U1' label | 0.385 | silk-to-silk |
| 'U1' label to the FPGA body | 0.475 | (not a DRC rule) |
| 'U4' label to U4's pads | 0.569 | silk-to-mask |
| Pin-21 'GND' to the east board edge | 0.302 | no DRC rule (see below); the west-edge 'AI1' / '1V0' are 0.255 as before |

The SilkToBoardRegionClearance rule has no gap value, and the DRC report never runs it, so legend-to-edge is
checked by script. The first plan put pin 21's 'GND' at x 58.623, which is 0.129 mm from the edge. The
independent review caught it and the label moved to 58.45.

## How it was done

The plan and tools are in `tools/route/x2_label_swap/`:

- `geom.py`: the overlay dump.
- `check_silk.py`: the clearance checker. It reproduced DRC 0 on the unedited board, including Rev 3's 'AI1'/'AI0',
  which pass only with the ink model.
- `swap_edits.py` and `final_edits.py`: the plan.
- `emit_silk_pas.py`: the script generator.
- `verify_applied.py`: the file-level check.
- `render.py`: draws `before_right_half.png` and `after_right_half.png`.

Steps:

1. **Review before applying.** Workflow `wf_8a5e36a8-232` re-derived every clearance with its own parser. It
   found the pin-21 edge problem and suggested spreading the title/U1 slack evenly; both were taken.
2. **Script.** `tools/NoPmodSilkSwap24.pas` ran via Run Script > Browse > From file. It reported "36 texts changed,
   28 deleted, U1 designator hidden". Every text was found by its exact text and position before anything changed.
3. **Save** at 09:47:44: MD5 `2b655383d4653cfc5cbeab7898e39700`, SHA-256 `746DDC71...99574D88` (was `8ba56533`).
   Backup: `backups/Zulu_a7_no_pmod_before_silk_swap.PcbDoc`.
4. **File check.** `verify_applied.py` compared all 426 overlay texts of the saved board with the plan, exactly:
   PASS.
5. **DRC** at 09:48:19: 32 rules, 0 warnings, 0 violations, silk and Component Clearance included
   (`docs/drc_x2_label_swap.drc`). The board was not saved again.
6. **Exports.** Gerbers 09:49:35; NC drill 09:51:22, unsplit, with "Use drilled slot command (G85)" ticked again.
   This board has no non-plated holes. Ticking "separate plated & non-plated" renames the files `-Plated` and the
   packager would not find them.

Against the 2026-11-21 package, only the GTO changed. Every other Gerber differs only in G04 header lines: Altium
is now 26.12.2 (it was 26.11.1), and the SameCoordinates GUID is new. The drill files and LDP are byte-identical;
the DRR differs only in its date line.

## Release (2026-11-24)

- **`tools/fab_notes.py`:**
  - RELEASE_DATE 2026-11-24.
  - A new "SUPERSEDES THE 2026-11-21 PACKAGE OF THIS REVISION (SILKSCREEN ONLY)" section.
  - A gate: against the superseded package, only the GTO may differ. It finds that ZIP in fabrication/, then in
    backups/, then in git history; backups/ is not in git.
- **`fabrication/Zulu_A7_no_pmod_Rev_3_PCBWay_Fabrication_2026-11-24.zip`:** NO_PMOD_REV_3_PCBWAY_FABRICATION_RELEASE
  PASS, 23 entries, body gate 0 fail / 15 warn, the same as before.
- **`assembly/Zulu_A7_no_pmod_Rev_3_PCBWay_Assembly_2026-11-24.zip`:** ASSEMBLY_RELEASE PASS.
  - BOM and CPL are byte-identical to 2026-11-21.
  - The notes change only in date, PCB SHA-256 and the fabrication ZIP name.
  - The drawings draw no silkscreen; only their PDF date changed.
- **Superseded:** the 2026-11-21 ZIPs moved to `backups/*_2026-11-21_silk-swap_superseded.zip`.
- **Board pictures redrawn** by `tools/board_illustration.py`. Its labelled-pin reach went from 4.5 to 3.0 mm, so the
  new 'U4' text is no longer taken for pin 4's name.
- **Review:** workflow `wf_07cda02a-485` (release plus an adversarial check). Its findings were fixed: the git-history
  fallback, this record, and the 1.23 mm figure in the script header.

## X2 header housings (owner question: do the strips interfere?)

The model treats each strip as a Sullins PRPC010SAAN-RC housing, 2.54 mm wide and 1.27 mm past each end pin, on
the Bottom (drawing 11635 rev B; width tolerance ±0.20, post 0.64 mm square in a 1.016 mm hole). It was checked
against the photographed order: there it finds U10's SOIC-8 body under the housing (-0.19 mm) and nothing else,
which is what PCBWay reported.

- **U10:** clear. It is an MSOP-8 here; its body is 1.115 mm and its pads 1.44 mm from the 11-20 housing, and still
  0.72 mm in the worst tolerance case.
- **Tightest Bottom items:**
  - C3, C7, C8, C36, C37, C139, L4-L7, R10, R11: 0.06 mm at the pad. For R10 and R11 the body is also at 0.06 mm;
    for L4-L7 the body is at 0.11 mm.
  - C87, C88, C94, C99, C106, R1: 0.16 mm at the pad.
  - This is the same geometry PCBWay fitted on the ordered board without comment.
- **Worst-case tolerance:** with the housing at its widest and the post floated, the edge can ride onto R10/R11 and
  L4-L7.
  - Practical fix: push each strip toward the board edge while soldering, which takes up the float.
  - Proper fix, at the next layout spin: about 0.25-0.3 mm more clearance there.

## R4 label (same day, owner: "Yes, move R4")

R4's designator sat in the X2 name row beside pin 1, so it read as pin 1's name ("C0  CLK  R4").

**The change:**
- R4's designator is hidden.
- A free 'R4' (0.8 mm, 0.15 mm stroke) now sits at (58.633, 13.85), centred under the R4 array (742C163).

**Clearances:**
- R4-1 and R4-16 pad masks: 0.378 mm.
- C86's pads: 1.16 mm.
- X5: 2.6 mm.
- East edge: 0.92 mm.

**How it was done:**
- **Independent check:** PASS.
- **Script:** `tools/NoPmodR4Label.pas` (from `tools/route/x2_label_swap/emit_r4_pas.py`). It uses the text-creation calls from Asar's `FeatherBtnLabel.pas`.
- **Saved** at 12:47:45: MD5 **66148256** (`661482566444257d69feddf68a83f94e`), SHA-256 511482C3...034E6A1F. Backup: `backups/Zulu_a7_no_pmod_before_r4_label.PcbDoc` (2b655383).

**Checks on the saved board:**
- `verify_applied.py` with `ops_with_r4.json`: all 427 overlay texts match.
- The new text's Texts6 record matches the X2 names' record except for its string index and unique ID, so it uses the same stroke font.
- The copper streams are unchanged.
- **DRC** at 12:47:58: 32 rules, 0 violations (`docs/drc_x2_label_swap.drc`).

**Outputs and release:**
- **Exports:** Gerbers 12:51:44, NC drill 12:52:17 (unsplit, G85). Against this morning's export, only the GTO changed.
- **Packages:** the 2026-11-24 packages were rebuilt under the same names.
  - Fab: PASS, zip md5 `c4b76bfa`.
  - Assembly: PASS, zip md5 `8e09f88d`.
  - BOM and CPL are byte-identical.
  - The fab notes now say the R4 label moved.
- **Pictures:** redrawn.

## Open

- The printed U1 and R4 labels are free texts. If either designator is switched back on, it prints a second label
  in its old place.
- The release was built from uncommitted files; commit before anything goes to PCBWay.
