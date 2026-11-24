# Zulu_a7_no_pmod Rev 3: X2 headers shipped loose (2026-11-21)

> **2026-11-24:** the assembly package was re-issued as `assembly/Zulu_A7_no_pmod_Rev_3_PCBWay_Assembly_2026-11-24.zip`
> for the silkscreen change (`docs/x2_label_swap.md`). The ship-loose content is unchanged. The ZIP named below is
> now in `backups/` as `*_silk-swap_superseded.zip`.

> **Revised the same day.** The first 2026-11-21 issue described below was re-issued after a review (see "Review
> fixes" at the end). Where the two differ, the "Review fixes" section is current: the notes wording, the
> short-edge list, the drawing footer and the package hashes.

The board owner asked on 2026-11-21: "let's also have the headers be shipped loose on all boards".

The pattern comes from the Asar Feather (`Asar_feather/Rev_1/tools/generate_pcbway_assembly.py`, `LOOSE_PARTS`). It
was ported to Fab B Rev 2 the same day, and this change ports Fab B's version to Rev 3.

This board has no J1, so X2 is its only through-hole part. X2 is four Sullins PRPC010SAAN-RC 1x10 strips, mounted
from the bottom.

PCBWay still **buys** X2: the same MPN, maker and quantity per board (4). PCBWay does **not** solder it: the strips
are packed loose with each board, and X2's 40 plated holes stay empty. X1, X3, X4 and X5 are SMD and are still
placed. JP3 and JP4 stay DNS.

The PcbDoc and SchDocs were not touched: PcbDoc MD5 `8ba56533`, SHA-256 `346D121C...`, the same as before. The
fabrication release did not change either.

## Script: `tools/generate_jlcpcb_assembly.py` (PCBWay mode)

- **New tables:** `LOOSE_PARTS = {"X2": [("PRPC010SAAN-RC", "Sullins", 4)]}`, `LOOSE_TYPE = "Ship loose"`,
  `LOOSE_INSTRUCTION` and `loose_note()`. They follow the Asar wording, with X2's own hole count.
- **New sets:** `loose_refs()` (empty outside PCBWay mode), `fitted_refs()` (placed = not DNS and not loose) and
  `dns_refs()`. The CPL, the counts, the notes, `validate()` and `main()` now use them.
- **`check_loose()`**, run in PCBWay mode, holds `LOOSE_PARTS` to:
  - the schematic: MANF# `4x PRPC010SAAN-RC` and MANF `Sullins`;
  - `X2_STRIPS`;
  - through-hole-only parts that are not DNS.

  It also fails if any placed part has no SMD pads, so the through-hole count stays 0.
- **BOM:** X2's line keeps its Item #, MPN, maker, Qty and description. Three things change:
  - Type becomes `Ship loose`.
  - The package gets ` (not placed: shipped loose)`.
  - The instruction becomes the SHIP LOOSE note. `X2_NOTE` (the underside-THT hand-solder note) is gone.
- **Notes:**
  - Number of Through-Hole Parts = 0.
  - There is a new "Loose parts" form line.
  - The scope counts cover placed parts only.
  - The X2 paragraph says SHIPPED LOOSE.
  - The only hand soldering left is X1's shell stakes.
  - The housing fit check, "leave X2 unpopulated" and "depanel before fitting X2" were removed.
    `x2_housing_neighbours()` is gone; the release body gate still checks the housings.
- **Drawings:**
  - X2's two bottom labels now read "X2 holes left empty - upper/lower strips shipped loose", in red.
  - X2 has no pin-1 dot.
  - The footer reads "Red dot = pin 1/A1 of a placed part ... Dashed red label = DNP or shipped loose".
- **`validate()`** was updated, not reduced:
  - The fitted, loose and DNS sets partition the parts.
  - The Ship loose lines equal `LOOSE_PARTS` (designator, MPN, maker, Qty) and carry the instruction and the
    package mark.
  - No placed line is thru-hole.
  - X2's lines equal `X2_STRIPS`, with Type Ship loose and 4 strips.
  - No loose designator is on a placed line or in the CPL.
  - The notes say `Number of Through-Hole Parts = 0`, name `X2 = PRPC010SAAN-RC x4` and have an X2 SHIPPED LOOSE
    paragraph. They never say "selective".
  - The bottom drawing labels X2's holes, and both drawings explain the dashed red label.
  - The fabrication ZIP named in the notes exists in `fabrication/` and carries the current FAB_NOTES, and that
    FAB_NOTES' PCB SHA-256 equals this PcbDoc's.
- **Release dating:** `RELEASE_DATE` stays 2026-11-21, because this re-issue is on the same day as the first Rev 3
  release. So the assembly ZIP keeps its name, `Zulu_A7_no_pmod_Rev_3_PCBWay_Assembly_2026-11-21.zip`.
  `FAB_ARCHIVE` still names the unchanged `Zulu_A7_no_pmod_Rev_3_PCBWay_Fabrication_2026-11-21.zip`.
- The JLCPCB and neutral modes are unchanged: they still list X2 as fitted THT.

## Output diff (against the 89f9662 release)

Before the change, the unmodified script re-generated the 89f9662 files. They were byte-identical except for one
notes line, and therefore the ZIP that carries the notes: `Source:` now names commit 89f9662, which holds the
PcbDoc.

| File | Before (SHA-256) | After (SHA-256) | Change |
|---|---|---|---|
| BOM.csv | `65F6043F...` | `7FED476D...` | Only item 65 (X2) changed; the header and the other 69 rows are byte-identical. In X2's row, Type `thru-hole` became `Ship loose`; Package `1x10 through-hole strip` gained ` (not placed: shipped loose)`; the instruction became "SHIP LOOSE - do not solder, pack with each board. Buy 4 per board and pack 4 with each finished board (one strip each for X2 pins 1-10, 11-20, 21-30 and 31-40); X2's 40 plated holes stay EMPTY at assembly (no paste, no solder; we fit the strips ourselves). Not in the CPL." Designator, Qty 4, Sullins, PRPC010SAAN-RC and the description are unchanged. |
| CPL.csv | `C7CB74DF...` | `C7CB74DF...` | Byte-identical, 188 rows. X2 was never in it. |
| Assembly_Notes.txt | `3CE3D33F...` | `A3DF993B...` | See the list below. |
| Drawing_Top.pdf | `638B3EE1...` | `A59EFBEE...` | The footer on all 3 pages; nothing else. |
| Drawing_Bottom.pdf | `6526775F...` | `1232BA75...` | All 3 pages: the footer, and X2's two labels became red "X2 holes left empty - upper/lower strips shipped loose" in the same position (their white boxes are wider). X2's pin-1 pad dot was removed. The vector diff shows no other change. |
| Assembly ZIP | `677CFC61...` | `73386A47...` | Same name and the same 5 members, stamped 2026-11-21, each identical to its loose file. The superseded ZIP is in `backups/Zulu_A7_no_pmod_Rev_3_PCBWay_Assembly_2026-11-21_pre-ship-loose.zip` (MD5 `fa463b18`). `backups/` is gitignored; the old ZIP stays in git at 89f9662. |

Notes changes:

- **Source line:** `working copy after commit b224209` became `Source commit: 89f9662...`.
- **Form settings:**
  - `Number of Through-Hole Parts = 4 (four X2 strips, 40 joints)` became
    `= 0 (the four X2 strips are shipped loose, not soldered; X1's two shell stakes ... hand-soldered)`.
  - A new "Loose parts" line names `X2 = PRPC010SAAN-RC x4` and says what to put in "Detailed information of
    assembly".
- **Scope:**
  - Fitted designators: 189 / 32 top / 157 bottom became 188 / 32 / 156.
  - `Physical parts per board: 192` became `placed 188; plus 4 shipped loose`.
  - `BOM purchase lines: 68` became `68 (67 placed + 1 ship-loose)`.
  - "then hand soldering" became "then hand soldering of X1's shell stakes".
- **Panel:**
  - X2 left the short-edge list (it was at 0.51 mm from both edges).
  - The X2 housing sentence was reworded: "X2's holes run along both long edges and we seat its housings there
    later".
  - "Depanel before fitting X2" was dropped.
- **CPL text:** "X2 is hand-soldered" became "X2 is shipped loose, not placed".
- **Drawing legend:**
  - It now says "pin 1/A1 of a placed part".
  - The dashed red label is "DNP, or a header shipped loose (its holes left empty)".
  - The silkscreen parenthesis reads "X1 and X3 are keyed; X2 is shipped loose".
- **Special instructions:**
  - The reflow line now says to hand-solder only X1's shell stakes.
  - The X2 underside-THT paragraph, its fit check (C3, C7, C8, C36, C37, C139, L4-L7, R10, R11 within 0.1 mm)
    and "leave X2 unpopulated" became one SHIPPED LOOSE paragraph.
- **Order review:** "hand soldering of X2's four strips and X1's stakes, or X2 left unpopulated" became "hand
  soldering of X1's stakes; X2's four strips bought, NOT soldered, packed loose with each board, their holes left
  empty".
- Everything else is identical. The longest line is 86 characters.

## Verification

- `python tools/generate_jlcpcb_assembly.py` gives **ASSEMBLY_RELEASE PASS**: 68 purchase lines (67 placed + 1
  ship-loose: X2 PRPC010SAAN-RC x4), 2 DNS, 188 fitted (32 top / 156 bottom), 188 CPL rows.
  - A trial run into a scratch folder and the release run wrote identical bytes.
  - Body gate: 0 fail, the same 15 warnings.
- `--assembler jlcpcb`: the original and the modified script write byte-identical files.
- Mutation test: 20 tampered outputs were all refused by `validate()`, and the untouched set passed. The tampering:
  - X2 Type, Qty, MPN, maker, instruction, package mark or the whole line;
  - an extra loose line, or a placed line marked thru-hole;
  - X2 added to the CPL;
  - in the notes: Through-Hole = 4, the loose line not named, the SHIPPED LOOSE paragraph gone, "selective" back,
    another fabrication ZIP named;
  - a missing fabrication ZIP, a stale FAB_NOTES in the ZIP, or FAB_NOTES with another PCB SHA-256;
  - the old bottom drawing, or the old top drawing's footer.

  `check_loose()` refused a wrong quantity, a wrong maker, an empty table, an SMD part made loose, and X2 made DNS.
- No PCBWay order number appears in the outputs, the script or this file. The Fab B `fab_notes.names_order`
  SHA-256 check and a plain `W` + 7-digit scan were both run.

## Open points

- **Same ZIP name.** The new assembly ZIP has the same name as the one committed in 89f9662 (both are dated
  2026-11-21). If that ZIP was already sent to PCBWay, the two cannot be told apart by name, only by SHA-256.
- **Label overrun.** On the bottom detail pages (2 and 3), X2's longer labels run about 30 pt past the
  detail-window edge. They are still readable; the old labels overran by a few points.
- **Body gate warnings.** The gate still warns that X2's bottom housings are within 0.10 mm of C3, C7, C8, C36,
  C37, C139, L4-L7, R10 and R11. This now matters only for our own fitting of the strips. The fitting method we
  will use is no longer written in the notes; it stays in git history (89f9662): housings on the bottom, short
  post end up through the board, solder on top.
- **No built-in order-number check.** Rev 3's `validate()` has no order-number check (Fab B Rev 2 has one through
  `fab_notes.names_order`); it was checked by hand here.
- **Stale record.** `docs/rev3_release.md` still describes the superseded package (189 fitted).
- Nothing is committed.

## Review fixes (2026-11-21, second issue the same day)

A review of the first issue found four problems. All four are fixed in `tools/generate_jlcpcb_assembly.py` (PCBWay
mode only), ported from the same fixes on Fab B Rev 2, and the release was re-run.

1. **`validate()` could not stop the old wording coming back.** New `loose_notes_problems()` reads the notes as
   items: a bullet or paragraph with its continuation lines.
   - No item may name X2 and also contain solder, fit, mount, populate or depanel wording (`FIT_WORDS`, plus
     "install" and "insert"). The check covers the whole bullet, so a later sentence with an implied subject is
     caught too.
   - The exceptions are the X2 SHIPPED LOOSE paragraph and the "Loose parts" form line. Inside them, that wording
     may appear only as the controlled phrases in `LOOSE_NOTE_PHRASES`, such as "do NOT solder them", "do not
     solder" and "we fit the strips on the underside and solder them ourselves".
   - `validate()` also requires the "Loose parts" line.

   Four lines of the first issue paired X2 with such a word and were reworded:
   - THT count: now "Parts = 0 (no through-hole part is placed: the header strips are shipped loose, see the next
     line; X1's two shell stakes ... hand-soldered, see below)".
   - Reflow line: now ends "nothing else is soldered by hand." (the X2 SHIPPED LOOSE paragraph follows it).
   - Order review: now two bullets, "- hand soldering of X1's stakes;" and "- X2's four strips bought, not placed,
     packed loose with each board, their holes left empty;".
   - Panel bullet: "Confirm the depanelizer and support fixture" became "Confirm the V-cut separating tool and
     support fixture". The bullet now names X2, so "depanelizer" would trip the check.
2. **The board-edge warning lost X2.** X2's plated holes stay on the board, so the short-edge list includes it
   again, marked `LOOSE_EDGE_MARK`: "X2 0.51 mm from the left edge (bare plated holes, header shipped loose); X2
   0.51 mm from the right edge (bare plated holes, header shipped loose)". These are the same distances and the same
   place in the list as in the release before the ship-loose change. `validate()` requires each such entry.
3. **The legend did not match the drawing.**
   - What is drawn: a DNP part (JP3, JP4) has a dashed grey outline and a red "DNP" label. X2 has a red label in a
     white box and no outline.
   - Drawing footer: "Red dot = pin 1/A1 of a placed part. Red bar = LED cathode (pad K). Dashed grey outline + red
     "DNP" label = not placed (DNS); red "holes left empty" label = header shipped loose. Verify ..." It still fits
     on one line.
   - Notes legend: 'dashed grey outline + red "DNP" label = not placed (DNS); red "holes left empty" label (in a
     white box, no outline) = header shipped loose'.
   - `validate()` requires the legend on all 3 pages of both drawings and in the notes. It refuses "dashed red
     label" in either.
4. **Stray bytes:** Reverted: the first issue had changed the spacing before the comment on the `BOARD_WIDTH =
   60.96` line. That line is back to its committed bytes. It was the only whitespace-only change against `HEAD`. The
   three blank lines after `fitted_refs()` are now two. The script uses LF line endings and ends with a newline, as
   committed.

**Result:** `ASSEMBLY_RELEASE PASS`. The counts are as before: 68 purchase lines (67 placed + 1 ship-loose: X2
PRPC010SAAN-RC x4), 2 DNS, 188 fitted designators (32 top / 156 bottom), 188 CPL rows. Body gate: 0 fail, 15 warn. A
trial run into a scratch folder and the release run wrote identical bytes. The ZIP keeps its name; its five members
are stamped 2026-11-21 and are identical to the loose files. The new package's SHA-256 is E336F827...F7E6.

**Outputs compared with the first 2026-11-21 issue:**

| File | Before | After | Change |
|---|---|---|---|
| BOM.csv | | | none (byte-identical) |
| CPL.csv | | | none (byte-identical) |
| Assembly_Notes.txt | `A3DF993B` | `59F8A616` | 241 -> 244 lines; only the items listed in 1-3 changed; the longest line is still 86 characters |
| Drawing_Top.pdf | `A59EFBEE` | `FB3D0A3C` | the footer text only, on all 3 pages; the vector objects are identical |
| Drawing_Bottom.pdf | `1232BA75` | `15616E39` | the footer text only, on all 3 pages; the vector objects are identical |
| Assembly ZIP | `73386A47` | `E336F827` | same name and members |

**JLCPCB and neutral modes** (`--assembler jlcpcb` / `neutral`, `--release-date 2026-11-21`): both write files
byte-identical to the `HEAD` (89f9662) script's.

**Mutation test.** 23 copies of the release were each fed to `validate()`: 21 tampered ones and 2 controls.
All 21 tampered copies were refused by the intended check, none by the 88-character line limit, and both
controls passed. The cases are run by `mutate_review.py` in the session scratchpad (not kept in the repo).

| # | Tampering | Result |
|---|---|---|
| 00 | none (control) | PASS |
| 01 | old reflow line "Then hand-solder X2 and X1's shell stakes." | REFUSED |
| 02 | new bullet "- Hand-solder X2's four strips on top after depanel." | REFUSED |
| 03 | old "If you cannot quote X2, leave it unpopulated, ..." under the X2 SHIPPED LOOSE paragraph | REFUSED |
| 04 | "If you cannot quote X2, leave it unpopulated ..." as its own bullet | REFUSED |
| 05 | old "Depanel before fitting X2." | REFUSED |
| 06 | old order-review line "hand soldering of X2's four strips and X1's stakes, or X2 left unpopulated;" | REFUSED |
| 07 | the first issue's order-review line "... X2's four strips bought, NOT soldered, ..." (strict rule) | REFUSED |
| 08 | the first issue's THT line "(the four X2 strips are shipped loose, not soldered; ...)" (strict rule) | REFUSED |
| 09 | the first issue's reflow line "... soldered by hand (X2 is shipped loose)." (strict rule) | REFUSED |
| 10 | X2 SHIPPED LOOSE paragraph: "do NOT solder them" -> "solder them" | REFUSED |
| 11 | Loose parts line: "buy, do not solder," -> "buy, solder on top," | REFUSED |
| 12 | old underside paragraph without "selective" ("... Solder on top by hand, after both reflows and depanel.") | REFUSED |
| 13 | "- X2: four 1x10 strips, housings on the bottom side. Hand-solder after both reflows." (implied subject) | REFUSED |
| 14 | "- Please mount X2's strips on the underside." | REFUSED |
| 15 | "- Populate X2 with the four strips." | REFUSED |
| 16 | "- Insert X2's strips from the bottom side." | REFUSED |
| 17 | a harmless X2 bullet "- X2's strips come as four separate parts." (control) | PASS |
| 18 | X2's left-edge entry dropped from the short-edge list | REFUSED |
| 19 | X2's "(bare plated holes, header shipped loose)" mark dropped | REFUSED |
| 20 | notes legend back to "dashed red label = DNP" | REFUSED |
| 21 | the first issue's top drawing (old footer) | REFUSED |
| 22 | the first issue's bottom drawing (old footer) | REFUSED |

**Limits of the check:** it works on designators. A sentence that asks for "the strips" to be soldered without
naming X2 anywhere in its bullet would not be caught. The JLCPCB and neutral drawing footers still say "Dashed red
label = DNP"; they were left unchanged so that those modes stay byte-identical.
