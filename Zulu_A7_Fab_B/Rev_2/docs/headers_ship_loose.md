# Fab B Rev 2: headers shipped loose (2026-11-21)

> **2026-11-24:** the assembly package was re-issued as `assembly/Zulu_A7_Fab_B_Rev_2_PCBWay_Assembly_2026-11-24.zip`
> for the silkscreen change (`docs/x2_label_swap.md`). The ship-loose content is unchanged. The ZIP named below is
> now in `backups/` as `*_silk-swap_superseded.zip`.

> **Revised the same day.** The first 2026-11-21 issue described below was re-issued after a review (see "Review
> fixes" at the end). Where the two differ, the "Review fixes" section is current: the notes wording, the
> short-edge list, the drawing footer and the package hashes.

Request (board owner, 2026-11-21): "let's also have the headers be shipped loose on all boards." This follows
the pattern the Asar Feather has used since 2026-11-11 (`Asar_feather/Rev_1/tools/generate_pcbway_assembly.py`,
`LOOSE_PARTS`).

On this board the change covers both through-hole headers:

- **J1** is a Sullins PPTC062LFBN-RC, a 2x6 female Pmod socket on the top side (12 holes).
- **X2** is 4 x Sullins PRPC010SAAN-RC, 1x10 strips. Their housings go on the bottom side (40 holes).

PCBWay still **buys** both parts, with the same MPNs and quantities per board, but **does not solder** them. One set
is packed loose with each board. Their plated holes stay empty, and we fit the headers ourselves.

## Release

- Generator: `tools/generate_jlcpcb_assembly.py`, run with no arguments (PCBWay mode). Result: `ASSEMBLY_RELEASE
  PASS`, with 69 purchase lines (67 placed + 2 ship-loose), 2 DNS (JP3, JP4), 195 fitted designators (35 top /
  160 bottom) and 195 CPL rows. The body gate reports 0 fail and 15 warn, the same as before.
- Board: `zulu_a7_fab_b.PcbDoc` MD5 14a06f6d..., unchanged and not touched. PCB SHA-256 FBD5FD5B...889B.
- Assembly package: `assembly/Zulu_A7_Fab_B_Rev_2_PCBWay_Assembly_2026-11-21.zip`, SHA-256 992EE706...9F7B
  after the same-day review fixes (see "Review fixes" below; the first 2026-11-21 issue was 027A5A3E...0CAB). A
  second run writes byte-identical files.
- Fabrication: unchanged. The notes still point at `Zulu_A7_Fab_B_Rev_2_PCBWay_Fabrication_2026-11-20.zip`
  (new constant `FAB_RELEASE_DATE`). `RELEASE_DATE` (2026-11-21) now dates only the assembly release.
- The superseded `Zulu_A7_Fab_B_Rev_2_PCBWay_Assembly_2026-11-20.zip` (MD5 42d4d4b5...) moved to `backups/`.
  The older `..._Assembly_2026-11-11.zip` is still in `assembly/`, as it was before this release.

## What changed in the outputs (compared with the 2026-11-20 release)

**BOM** (71 rows before and after, same columns, same row order and Item #). 69 rows are byte-identical. Only
item 21 (J1) and item 67 (X2) changed, and in each of them only these columns:

- Type: `thru-hole` -> `Ship loose`.
- Package/Footprint: `(not placed: shipped loose)` was appended to the old text.
- Instructions: the hand/selective-solder text was replaced with "SHIP LOOSE - do not solder, pack with each
  board. Buy N per board and pack N with each finished board; <ref>'s <n> plated holes stay EMPTY at assembly (no
  paste, no solder; we fit the ... ourselves). Not in the CPL." On the X2 line the instruction also names the pin
  runs 1-10, 11-20, 21-30 and 31-40.
- Designator, Qty (1 and 4), Manufacturer, MPN and Description are unchanged.

**CPL**: byte-identical (SHA-256 60F6B875...). J1 and X2 were never in it because they have no SMD pads.

**Notes**:

- Release date is now 2026-11-21.
- Number of Through-Hole Parts went from 5 (52 joints) to 0. A new "Loose parts" form line lists J1 = PPTC062LFBN-RC
  x1 and X2 = PRPC010SAAN-RC x4, to paste into "Detailed information of assembly".
- Scope counts:
  - fitted designators: 197 -> 195
  - top side: 36 -> 35
  - bottom side: 161 -> 160
  - placed parts: 200 -> 195, plus 5 shipped loose
  - purchase lines: still 69, now split 67 placed + 2 ship-loose
- The only hand soldering left is X1's shell stakes. Hand-soldering J1 and X2 is gone from the scope line, the
  reflow-order line and the order-review list.
- "Depanel before fitting J1 and X2" is gone. The first issue also dropped J1 and X2 from the short-edge parts
  list; the review fixes put them back, marked as bare plated holes (see below).
- The X2 paragraph is now a SHIPPED LOOSE instruction: buy, do not solder, pack four with each board, leave the 40
  holes empty. The housing fit check and "if you cannot quote X2 leave it unpopulated" were removed.
- The J1 paragraph is now a SHIPPED LOOSE instruction: buy, do not solder, pack one, leave the 12 holes empty.
- The CPL and orientation text says J1 and X2 are shipped loose. Their pin-1 notes are gone.
- Unchanged: fabrication ZIP name, HDI gate, via-in-pad text, SOURCING and QUALITY. The longest line is 86 characters.

**Drawings** (3 pages each). The PDF creation date is now 2026-11-21. On every page the footer reads "pin 1/A1 of
every **placed** multi-pin part"; the first issue's "Dashed red label = DNP or shipped loose" was replaced by the
review fixes (see below). The other changes:

| Drawing | Pages | Change |
|---|---|---|
| Top | Overview, East | J1's solid green outline is now dashed grey. Its label "J1" now reads "J1 holes left empty / header shipped loose" in red. Its two pin-1 dots were removed. |
| Bottom | Overview, West | X2's labels now read "X2 holes left empty - upper/lower strips shipped loose" in red, at the same place. X2's pin-1 dot was removed. |

Nothing else moved: the vector-object diff shows only these objects.

## Script changes (validations updated, none removed)

- New: `LOOSE_PARTS`, `LOOSE_TYPE`, `LOOSE_INSTRUCTION`, `loose_note()`, `loose_refs()` (empty outside PCBWay
  mode), `fitted_refs()`, `dns_refs()` and `check_loose()`.
- `check_loose()` checks four things:
  - each table entry matches the schematic MANF# and MANF;
  - X2's entry matches `X2_STRIPS`;
  - each loose part is through-hole only;
  - every fitted part without SMD pads is loose.
- `validate()` adds these checks:
  - the fitted, loose and DNS sets partition the parts;
  - the ship-loose lines equal `LOOSE_PARTS` (designator, MPN, maker, Qty) and carry the instruction;
  - no placed line is through-hole;
  - X2's lines equal `X2_STRIPS` with Type Ship loose;
  - no loose designator is in the CPL or on a placed line;
  - the notes say "Number of Through-Hole Parts = 0", name every loose line, have a SHIPPED LOOSE paragraph per
    loose part, and never mention selective soldering;
  - each drawing labels its loose holes and explains the label;
  - the named fabrication ZIP exists, carries the current FAB_NOTES, and FAB_NOTES describes this PcbDoc's SHA-256.
- Removed: `X2_NOTE`, J1's `PCBWAY_LINE_NOTES` entry and `x2_housing_neighbours()`. The release body gate still
  checks the X2 housings.
- Mutation test (scratch copies): 13 tampered outputs were all refused by `validate()`. They included J1 as
  thru-hole, X2 Qty 3, J1 in the CPL, notes saying 5 THT parts or "selective", the old drawings, and a 2026-11-21
  fabrication ZIP name.
- JLCPCB mode, run with `--release-date 2026-11-20`, is byte-identical to its output before this change. It still
  treats J1 and X2 as fitted THT.

## Open points

- `Zulu_A7_Fab_B_Rev_2_PCBWay_Assembly_2026-11-11.zip` is still in `assembly/`. It is older than the release that
  was just superseded and was left there.
- The "holes left empty" labels appear on each part's own side only: J1 on the top drawing, X2 on the bottom drawing.
  This matches how Asar does it. The same holes on the other drawing are drawn but not labelled, as before.
- The comment at `tools/package_fabrication_release.py` RELEASE_DATE says it matches this generator. The two dates
  now differ by design (FAB_RELEASE_DATE). The fabrication script was not touched.

## Review fixes (2026-11-21, second issue the same day)

A review of the first issue found four problems. All four are fixed in `tools/generate_jlcpcb_assembly.py` (PCBWay
mode only), and the release was re-run.

1. **`validate()` could not stop the old wording coming back.** New `loose_notes_problems()` reads the notes as
   items: a bullet or paragraph with its continuation lines.
   - No item may name J1 or X2 and also contain solder, fit, mount, populate or depanel wording (`FIT_WORDS`,
     plus "install" and "insert"). The check covers the whole bullet, so a later sentence with an implied subject
     is caught too.
   - The exceptions are the two SHIPPED LOOSE paragraphs and the "Loose parts" form line. Inside them, that
     wording may appear only as the controlled phrases in `LOOSE_NOTE_PHRASES`, such as "do NOT solder them",
     "do not solder" and "we solder it ourselves".
   - `validate()` also requires the "Loose parts" line.

   Four lines of the first issue paired J1/X2 with such a word and were reworded:
   - THT count: now "Parts = 0 (no through-hole part is placed: the headers are shipped loose, see the next line;
     X1's two shell stakes ... hand-soldered, see below)".
   - Reflow line: now ends "nothing else is soldered by hand." (the SHIPPED LOOSE paragraphs follow it).
   - Order review: now two bullets, "- hand soldering of X1's stakes;" and "- J1 and X2's four strips bought, not
     placed, packed loose with each board, their holes left empty;".
   - Panel bullet: "Confirm the depanelizer and support fixture" became "Confirm the V-cut separating tool and
     support fixture". The bullet now names J1 and X2, so "depanelizer" would trip the check.
2. **The board-edge warning lost J1 and X2.** Their plated holes stay on the board, so the short-edge list includes
   them again, each marked `LOOSE_EDGE_MARK`: "X2 0.51 mm from the left edge (bare plated holes, header shipped
   loose)" and "J1 1.24 mm from the right edge (bare plated holes, header shipped loose)". These are the same
   distances as in the 2026-11-20 release. `validate()` requires each such entry.
3. **The legend did not match the drawing.**
   - What is drawn: a DNP part has a dashed grey outline and a red "DNP" label. X2 has a red label in a white box
     and no outline. J1 has the same red label inside a dashed grey outline.
   - Drawing footer (`LOOSE_LEGEND`): 'Dashed grey outline + red "DNP" label = not placed (DNS); red "holes left
     empty" label = header shipped loose.' The footer no longer fits on one line, so on Fab B it now has two lines.
     The second line is at 17 pt from the page bottom; the drawing objects did not move.
   - Notes legend: the same wording, plus "X2's label is in a white box with no outline, J1's inside a dashed grey
     outline."
   - `validate()` requires the legend on all 3 pages of both drawings and in the notes. It refuses "dashed red
     label" in either.
4. **Stray bytes:** none in this script. It has no whitespace-only change against `master`, uses LF line endings
   and ends with a newline.

**Result:** `ASSEMBLY_RELEASE PASS`. The counts are as before: 69 purchase lines (67 placed + 2 ship-loose: J1
PPTC062LFBN-RC x1, X2 PRPC010SAAN-RC x4), 2 DNS, 195 fitted designators (35 top / 160 bottom), 195 CPL rows. Body
gate: 0 fail, 15 warn. A trial run into a scratch folder and the release run wrote identical bytes. The ZIP's five
members are stamped 2026-11-21 and are identical to the loose files.

**Outputs compared with the first 2026-11-21 issue:**

| File | Before | After | Change |
|---|---|---|---|
| BOM.csv | `84D4398D` | `84D4398D` | none |
| CPL.csv | `60F6B875` | `60F6B875` | none |
| Assembly_Notes.txt | `66681576` | `05D4871F` | 236 -> 241 lines; only the items listed in 1-3 changed; the longest line is still 86 characters |
| Drawing_Top.pdf | `6E577753` | `68EAFF69` | the footer text only, on all 3 pages; the vector objects are identical |
| Drawing_Bottom.pdf | `5B262B0E` | `F9AD3B6E` | the footer text only, on all 3 pages; the vector objects are identical |
| Assembly ZIP | `027A5A3E` | `992EE706` | same name and members |

**JLCPCB and neutral modes** (`--assembler jlcpcb` / `neutral`, `--release-date 2026-11-20`): both write files
byte-identical to the `master` script's.

**Mutation test.** 26 copies of the release were each fed to `validate()`: 24 tampered ones and 2 controls.
All 24 tampered copies were refused by the intended check, none by the 88-character line limit, and both
controls passed. The cases are run by `mutate_review.py` in the session scratchpad (not kept in the repo).

| # | Tampering | Result |
|---|---|---|
| 00 | none (control) | PASS |
| 01 | old reflow line "Then hand-solder J1, X2 and X1's shell stakes." | REFUSED |
| 02 | new bullet "- Hand-solder X2's four strips on top after depanel." | REFUSED |
| 03 | old "If you cannot quote X2, leave it unpopulated, ..." under the X2 SHIPPED LOOSE paragraph | REFUSED |
| 04 | "If you cannot quote X2, leave it unpopulated ..." as its own bullet | REFUSED |
| 05 | old "Depanel before fitting J1 and X2." | REFUSED |
| 06 | old order-review line "hand soldering of X2's four strips and X1's stakes, or X2 left unpopulated;" | REFUSED |
| 07 | the first issue's order-review line "... X2's four strips bought, NOT soldered, ..." (strict rule) | REFUSED |
| 08 | the first issue's THT line "(the four X2 strips are shipped loose, not soldered; ...)" (strict rule) | REFUSED |
| 09 | the first issue's reflow line "... soldered by hand (X2 is shipped loose)." (strict rule) | REFUSED |
| 10 | X2 SHIPPED LOOSE paragraph: "do NOT solder them" -> "solder them" | REFUSED |
| 11 | Loose parts line: "buy, do not solder," -> "buy, solder on top," | REFUSED |
| 12 | old underside paragraph without "selective" ("... Solder on top by hand, after both reflows and depanel.") | REFUSED |
| 13 | old J1 paragraph without "selective" ("... Pin 1 is the square pad. Hand-solder after both reflows.") | REFUSED |
| 14 | J1 SHIPPED LOOSE paragraph: "do NOT solder it" -> "solder it" | REFUSED |
| 15 | J1 dropped from the short-edge list | REFUSED |
| 16 | "- X2: four 1x10 strips, housings on the bottom side. Hand-solder after both reflows." (implied subject) | REFUSED |
| 17 | "- Please mount X2's strips on the underside." | REFUSED |
| 18 | "- Populate X2 with the four strips." | REFUSED |
| 19 | "- Insert X2's strips from the bottom side." | REFUSED |
| 20 | a harmless X2 bullet "- X2's strips come as four separate parts." (control) | PASS |
| 21 | X2's left-edge entry dropped from the short-edge list | REFUSED |
| 22 | X2's "(bare plated holes, header shipped loose)" mark dropped | REFUSED |
| 23 | notes legend back to "dashed red label = DNP" | REFUSED |
| 24 | the first issue's top drawing (old footer) | REFUSED |
| 25 | the first issue's bottom drawing (old footer) | REFUSED |

**Limits of the check:** it works on designators. A sentence that asks for "the strips" or "the header" to be
soldered without naming J1 or X2 anywhere in its bullet would not be caught. The JLCPCB and neutral drawing
footers still say "Dashed red label = DNP"; they were left unchanged so that those modes stay byte-identical.
