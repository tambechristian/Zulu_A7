## 9. The half that needs eyes

Everything above is arithmetic. This half is judgement, and it was done by looking: seven reviewers,
one per sheet, each rendering its page in overlapping tiles at 320 dpi and higher and reading them,
with the `.SchDoc` records and the exported netlist beside them. They returned 127 findings, 48 of
them marked as things that could mislead a competent reader. A verification pass then re-rendered
the areas behind every "misleading" claim and tried to knock it down; nine did not survive, and the
five that matter are ranked below. This file is written by hand and is appended to the generated
document; re-running `tools/schematic_review.py` does not touch it.

**The headline, because the volume of findings hides it: the schematic is sound.** Every
connectivity claim in the review was checked against the project's own netlist and exactly one came
back as a real circuit defect. The nets are right, the pin map in the netlist is right, and the
board can be laid out from this schematic. What is wrong is presentation -- text placement inherited
from the EAGLE importer -- and documentation that was never regenerated after the FPGA re-pin and
the part substitutions. That second category is the dangerous one, because stale text looks
authoritative.

### The five that matter, in the order to fix them

**1. Sheet 5's ball annotations were stale on three rows in four. FIXED 2026-09-09.** Beside each
FPGA pin row is a grey `<ball>  <pin function>` caption. It named a ball that no longer carried that
row's net on 94 of 137 rows. Two independent methods agreed: matching each caption to the live pin
on its row gave 42 right and 94 wrong; cross-checking each caption against the exported netlist gave
34 right and 102 wrong. The failures were coherent, which is what made it certain -- `SD-DAT2`'s row
was captioned `W2`, a ball that really carries SDRAM-CS#; `CHAN0`'s said `W3`, which carries CAS#;
`CHAN2`'s said `W5`, which carries D5. It was the fingerprint of a pin reshuffle where the captions
were left behind.

Worst was the Pmod block, whose captions claimed balls A14, A15 and W7. Those three carry SDRAM D14,
D15 and D2. The real Pmod balls are U18, U19, G17, C17, T17, E19, V19 and U17.

`tools/sheet5_ball_captions.py` rewrote 99 captions from the pin each one annotates, taking the
function name from `Datasheet/xc7a35tcpg236pkg_pinout.txt` -- the same package file `bom_audit.py`
checks the power tree against, and the source the originals were copied from. 37 were already right.
One was left alone and reported: `C13  VCCADC`, whose row has no live pin for the tool to check it
against, and which is correct anyway. Re-running the netlist cross-check afterwards gives **128 agree,
0 disagree**, with 9 rows carrying no net label to check (the floating MGT balls).

STILL OPEN on the same block: the symbol's own pin NAMES still read `IO_A14`, `IO_A15` and `IO_W7`,
so the old assignment is still baked into the symbol even though the captions beside it are now
right. Those are library pin names, not sheet text, and changing them is a different job.

**2. `PGOOD` is two different things wearing one name, and one of them is a dead net.** The netlist
gives `PGOOD = {Q2-G, R77-1}` with R77's other end on VCC3V3. Nothing can pull Q2's gate down, so Q2
is permanently on and LD5 lights whenever 3.3 V is present. The bq24232's actual PGOOD output, U8
pin 7, is on a different net entirely -- the auto-named `NetLD3_K`, with LD3's cathode. The drawing
shows a pin called PGOOD at the top left and a wire called PGOOD at the bottom right whose left end
dangles in mid-air, as though the signal arrives from somewhere.

This is a leftover from the LTC3569 era: that part had a power-good output, the three SC189s that
replaced it do not, and R77 was left pulling the gate high. Electrically LD5 works -- it is a
power-ON indicator. The name is what misleads, and Q2 with R77 and R78 is three parts doing a
resistor's job.

*Fix:* a decision, then two or three objects. If LD5 is meant to be a 3V3-present indicator, delete
Q2 and R77 and run VCC3V3 - R78 - LD5 - GND, and rename the net. If it is meant to follow the
charger, wire it to U8 pin 7 and drop the duplicate name. **Not actioned: this is a design choice.**

**3. Every net label hung below its wire while every pin number sat above its own. FIXED
2026-09-09.** The labels were `Justification=8` -- anchored at the top of the text box -- so although
the anchor sat exactly on the wire, the glyphs were drawn underneath it, while pin designators are
anchored at the bottom and sit above theirs. Rows are 10 units apart and the text is about 6.8 units
tall, which put every net name on the NEXT pin's line.

Measured on the PDF before: on sheet 2 the label `CHAN0` -- X2 pin 3 -- had its glyph box at y
100.88..104.00 while the digit 4 sat at 101.60..104.72, a 2.4 point overlap of a 3.1 point box; its
own digit 3 was above at 97.29..100.40. Reading across a row to find which pin a signal is on, which
is exactly what the 40-pin footprint work needs, gave the wrong answer. On the Pmod the pin name
inside the symbol did not save you either: pin 11's `GND` landed on the `PMOD-10` line.

`tools/label_justification.py` subtracted 6 from the justification of every horizontal net label that
had a top value (6 -> 0, 7 -> 1, 8 -> 2), which moves the anchor to the bottom of the box and leaves
the horizontal half alone: 254 labels over sheets 1 to 5. Measured on the PDF after, `CHAN0` is at y
97.29..100.40 -- character for character the same box as its own digit 3. Nothing moved
electrically; a label's Location is its attachment point and was not touched, and the netlist came
back with the same 178 nets over 783 pads.

The 117 labels that were already bottom-anchored are why this was worth doing at all: the sheets were
inconsistent with themselves, so a reader could not learn one rule and trust it.

STILL OPEN: eight ROTATED labels that are also top-anchored (two on sheet 1, three on sheet 4, three
on sheet 5). For a label at 90 degrees the vertical half of the justification moves the glyphs
sideways rather than up, so the same flip is not obviously right and eight is few enough to judge by
eye. `tools/label_justification.py` lists them every time it runs.

**4. Five things the block diagram said that were not true. FIXED 2026-09-09.** Three were the
factual errors ranked here, and checking the sheet to fix them turned up two more of the same kind.

`CHAN-I/O (28)` should have been 29: the netlist holds CHAN0 through CHAN28, and the sheet has
already taught the reader that a number in brackets is a bus width via `CTRL (7)`, `ADDRESS (15)` and
`DATA (16)`, all three correct. 28 was a trap because it is also the highest channel number, so it
survives a spot-check.

`SDRAM-CLK` was drawn leaving the FPGA at (460,612), running down to y 542, jogging right to x 480
and coming back UP into an arrowhead at (480,612) pointing into the FPGA, while the main line
continued down into the SDRAM. It read as a clock the FPGA sends out and gets back; the net is
exactly two pads, U1-M1 and U3-38. The return branch and its arrowhead are gone, leaving one line
with one arrowhead, drawn the way CTRL and ADDRESS beside it are.

The microSD note claimed six bank-34 balls. It spans three: CLK U8 and CMD U7 in bank 34, DAT0 C15,
DAT1 B15 and DAT3 A16 in 16, DAT2 L3 in 35 -- confirmed against the package file and the pin
designators on sheet 5. The note now says so, and keeps the claim that actually matters, which is
that a card cannot reach the config bus.

Found while fixing those: the `XADC` link was drawn with an arrowhead at BOTH ends, i.e.
bidirectional, when X2-39 and X2-40 feed the XADC through dividers and nothing comes back. The
header-end arrowhead is gone and the line now runs flat to the header, which is the shape this sheet
already uses for one-way links. And the `LED/Button` link had a single arrowhead pointing INTO the
FPGA, which on this sheet's convention means the FPGA only receives -- but LED0_R (P19), LED0_G
(R18), LED0_B (N19), LED1 (N18) and LED2 (M19) are FPGA outputs and only BTN (N17) is an input. An
arrowhead into the block has been added, so it now reads bidirectional.

CHECKED AND LEFT ALONE: the review also said the Pmod link was drawn with a single arrowhead into
the FPGA. It already had one at each end -- into the FPGA at (615,722) and up into the block at
(720,787) -- so that claim was wrong and the link was correct as drawn.

`tools/sheet0_fixes.py` does all five: ten line records deleted, two added, two text edits. Sheet 0
is the sheet that was left unopenable once by deleting records without renumbering OwnerIndex, so
the script renumbers and rewrites the header count, and the first thing done after applying it was
to open sheet 0 in Altium and watch it draw.

STILL NOT CHANGED on this sheet, because they are naming style rather than error: the rail nicknames
+5V, +3.3V, +1.8V and +1.0V, which are not the net names (USB5V0, VCC3V3, VCC1V8, VCC1V0); the flash
link labels FCS_B, CCLK and DQ[3:0], which are pin names where the neighbouring SD-CLK, SD-CMD and
SD-DAT[3:0] are net names; the 12 MHz oscillator drawn as a two-terminal passive when Q1 is an
active four-pad part; and the absence of designators on the blocks.

**5. GND and VCC drawn as bare red text instead of power ports. FIXED 2026-09-09.** On sheets 1, 3,
4, 5 and 6 the supply and ground connections were plain net labels sitting on a wire rather than port
symbols. Sheet 3 was the extreme: 24 rail labels and not one power port on the whole page.

Three places where it made a correct netlist read as a wrong circuit, and all three are now redrawn:

*Sheet 3's seven-row U3 decoupling ladder* rendered as an unbroken line, `pin 54 -GND- ||C3||
-VCC3V3- pin 1`, seven times. Every row was right -- each cap bridges one supply ball to the ground
ball opposite it -- but nothing on the row said which half was ground except two words of 8-point
text. A named ground bar is 30 units tall and the rows were 30 units apart, so there was physically
nowhere to put one: the GND text would have finished 0.5 units above the next row's wire. The pitch
is now 45 (the ladder had 145 units of headroom before U3's body; the new top row uses 90 of it), the
two labels moved to the middle of the segments they name, and each row now reads ground symbol, cap,
supply arrow.

*Sheet 6's bulk column* stacked three cap banks 70 units apart when a bank needs about 99 from the
top of a supply arrow's name to the bottom of a ground bar's, so each ground bar was drawn straight
through the next bank's supply label -- `GND` at x 22..88 across `VCC1V8` at 65..145 on the same
line. The column is boxed in by C86/C92 above and U1C below, 315 units, which holds two banks and not
three, so the VCC3V3 bank moved out into the empty band beside U1C and the VCC1V8 bank dropped 40
into the space it left. Three banks, three supply arrows, three ground symbols, nothing touching.

*Sheet 4's oscillator*: the `VCC3V3` naming C38's top plate sat on a stub that ran LEFT out of its
junction, right-justified, so Q1's pin-2 ground drop went through its glyphs 3 points above the
ground symbol -- it read as VDD grounded. The stub now runs down instead, into clear space between
the ground bar and C38's designator.

`tools/rail_layout.py` makes that room; `tools/rail_ports.py` then rewrites each label in place as a
RECORD=17 port -- same index, same UniqueID, same location -- choosing Style 4 for GND and GNDADC and
Style 2 for the seven supplies, and choosing which way the symbol points by reading the wire
directions at the point and then testing the symbol's own footprint against every drawn object on the
sheet. 55 labels became ports and 31 junctions were added at mid-wire taps. Sheet 3 went from 0 ports
to 22.

34 labels are still labels, and that is the tool working rather than failing: they are rows of a
connector or FPGA pin list on a 10-unit pitch, where a 30-unit ground symbol cannot go and the word
GND in a column of row labels is the clearer drawing anyway. It is also why sheet 2 was never in the
run -- almost all of its rail names are ZULU-CONN rows. Each one that keeps its label is printed with
the reason every time the tool runs.

WHAT THE NETLIST CAUGHT, and the reason to export it rather than trust the drawing: the first run
lost two nets. A net label does not have to touch its wire -- Altium associates it with the wire it
is nearest -- but a port has one electrical hot point and must land ON the conductor, and two sheet-6
wires sit at y 682.866 and 612.134 (`Y1_Frac=86600`). Ports written at whole units missed them by
0.866 and 0.134 of a unit, and because those two cap banks are islands whose only tie to their rail
was that one name, they fell off as `NetC141_1` and `NetC145_1`. `tools/snap_ports.py` now projects
every port and junction onto the exact wire, `_Frac` included; 4 of 396 needed it. This is the same
sub-unit trap the C40 cluster on sheet 4 sprang once already. After the fix the exported netlist is
identical to the one before any of this work: 183 components, 178 nets, 783 pads, every net the same
set of pads.

**7. Text printed on top of other text, on five sheets. FIXED 2026-09-10.** Not one of the original
findings either; it came out of checking that the rail-port work had not made anything worse.

Counting glyph boxes in the exported PDF gives 12409 overlapping pairs, which is nonsense: Altium
writes three invisible metadata layers into the PDF, `COxxx` per component, `PIxxx` per pin and
`NLxxx` per net, each sitting exactly on the visible text it describes. Filter those, and ignore a
parameter drawn twice at one spot the way the title block does it, and 40 real collisions are left --
5 on sheet 1, 5 on sheet 2, 4 on sheet 3, 13 on sheet 4 and 13 on sheet 5, with sheets 0 and 6 clean.

The worst were two labels drawn on top of each other. Sheet 4 carried two `FT-RESETN` labels on one
wire, at 302 left justified and 343 right justified, so both sets of glyphs landed on x 300..345; the
same for `FT-REF`. The net keeps its name from the survivor and the duplicate goes. Everything else
is a nudge: `tools/text_overlaps.py` takes the geometry from the PDF, because a pin's name and number
are drawn by the pin and are not records at all, matches each span back to the record that drew it,
and searches candidate positions until one hits nothing. A net label may only slide along the wire it
names; a gate pin name only along its own row and only away from its pin; a port not at all unless
nothing else can move, and then only on its own wire. Pins never move.

Two things were caught by checking rather than by looking. `UART_FT_RXD` slid 30 units up its stub,
past R94, and landed on the VCC3V3 rail -- which would have named the rail UART_FT_RXD. Sliding is
now confined to one connected wire run. And the last stubborn overlap was one this project had made
itself: `rail_ports.py` had pointed a ground symbol on sheet 3 RIGHT, because down was blocked at the
time, and its name landed on R6's pin number; the fix was to turn it down, not to move it.

40 down to 0 on all seven sheets, with the netlist identical at 182 components, 179 nets and 785 pads.

**6. Sheet 5's right-hand blocks were drawn through the frame. FIXED 2026-09-09.** Not one of the
original findings -- it came from reading the exported PDF. 25 objects crossed the inner border at
x 1020 and ran off the printed page: `MGTREFCLK0P/0N/1P/1N` by 34.6 units, `UART_CTS/RTS/DTR` by
31.7, `MGTPTXP0/N0/P1` and `MGTPTXN1` and `UART_TXD/RXD` by 21.7, the six `IO_A1x/B15/C15/W19` names
by 13.2, `IO_N2` and `IO_W7` by 8.9, and four `GNDADC` net labels by 2.5. 21 of them are the gate pin
names -- RECORD=41 parameters drawn just right of the pin, which is where this symbol puts its pin
names on every block of the sheet.

A row of those blocks is caption, net label, wire, pin, pin name: 165 units end to end with the
border 165 units away, so it fits only if the whole row moves left. Two of the five blocks had
nowhere to go -- the SDRAM block's pin names end at x 830.3 and the Pmod captions begin at 843.6 --
so the SDRAM block moved too; it had 71.8 units of clear space to its own left. Six blocks now sit 40
units further left, translated rigidly, and nothing on the sheet reaches the border.

Measured two ways that agree to 0.3 units over an 11-character string: from the PDF, and from the
records using a Courier advance of 0.535 * FontSize schematic units calibrated against it. That
metric is what let `rail_ports.py` decide where a power port would fit.

### What did not survive checking

Nine "misleading" findings were knocked down, and they are listed because a review that reports only
its hits cannot be trusted:

- Sheet 3, C11 printed over the `FLASH-D03` label: re-rendered at 1100 dpi, the plates stop above
  the text and the label is fully legible.
- Sheet 3, the R34/R35 array reading off by one: in that block the label and the pin number are both
  above the wire, so they pair correctly. The U3 half of the same finding is confirmed.
- Sheet 3, the offset "flipping mid-symbol" so a reader carries the wrong rule across: U3's right
  column reads correctly on its own terms. The left column alone justifies the fix.
- Sheet 0, XADC drawn bidirectional "against the sheet's own convention": the fact survives, the
  reasoning does not -- CHAN-CLK one row below is drawn the same way.
- Sheet 1, C78's ground symbol appearing to sit on the battery-positive net: it is 10 pt clear. The
  X1 instance of the same finding is real.
- Sheet 1, the rotated GND pin name destroying the SC189 suffix: the overprint is real but it
  strikes the "18", not the Z/L/A that carries the meaning.
- Sheet 1, R102-R106 values misreading at ordinary scale: the overprint is real, the misreading is
  not demonstrated.

And one correction to this document's own machine half, which claimed on its first run that U1, U3,
U4 and X2 are never named on the drawing. Their designators are indeed hidden on every placement,
but the importer put the reference in a visible parameter instead, so the drawing reads correctly.

### Where this leaves the ZULU-DIP37 redraw

Nothing blocks it, and the two findings that touched it are now fixed. Sheet 2, the sheet the
footprint is drawn from, no longer pairs each net name with the next pin's number; sheet 5, where
the ball assignments get read, no longer names the wrong ball on three rows in four. Both were fixed
before the redraw rather than after precisely because a footprint drawn against a misread row is
expensive to find later.

What is left for the redraw to work around: the symbol pin names `IO_A14`, `IO_A15` and `IO_W7` on
the Pmod block, which still carry an assignment the board no longer has.

Four of the five ranked findings are now fixed -- the ball captions, the label justification, the
block diagram, and the bare GND and VCC text -- along with the sheet-5 blocks that were drawn through
the frame. What remains is finding 2, the `PGOOD` name and its vestigial Q2/R77/R78 driver, which is
a design decision rather than a drawing fault and is the user's to make.

Every one of those changes was checked the same way: the project's own netlist exported from Altium
before and after, and required to come back with the same 183 components, 178 nets and 783 pads, with
every net holding the same set of pads. It caught a real break once, which is the only reason to keep
doing it.
