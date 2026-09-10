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

**4. Three factual errors on the block diagram.** `CHAN-I/O (28)` should be 29: the netlist holds
CHAN0 through CHAN28, and the sheet has already taught the reader that a number in brackets is a bus
width via `CTRL (7)`, `ADDRESS (15)` and `DATA (16)`, all three correct. 28 is a trap because it is
also the highest channel number, so it survives a spot-check. `SDRAM-CLK` is drawn leaving the FPGA,
doubling back and re-entering it through a second arrowhead, which reads as a feedback path on a net
that is exactly two pads, U1-M1 and U3-38. And the microSD note claims six bank-34 balls when the
six span three banks -- CLK and CMD on 34, DAT0/DAT1/DAT3 on 16, DAT2 on 35.

The block diagram is the index a newcomer and the layout engineer both start from.

*Fix:* retype one label, delete one segment and one arrowhead, reword one sentence.

**5. GND and VCC drawn as bare red text instead of power ports.** On sheets 1, 3, 4, 5 and 6, some
supply and ground connections are plain text sitting on a wire rather than a port symbol. Two places
where this makes a correct netlist read as a wrong circuit: sheet 3's seven-row decoupling ladder,
where each row renders as one unbroken line `pin 54 -GND- ||C3|| -VCC3V3- pin 1` and reads as U3
powered THROUGH a capacitor; and sheet 6's bulk column, which renders as a single conductor running
VCC1V0 - GND - VCC1V8 - GND - VCC3V3. Sheet 4's oscillator is the same defect in miniature: a
`VCC3V3` text struck through by Q1's pin-2 ground drop and sitting 3 pt above a ground symbol, which
reads as VDD grounded.

*Fix:* a find-and-replace pass for most of it; the sheet-3 ladder and the sheet-6 column want
re-laying-out, each capacitor turned vertical between a supply port and a ground symbol.

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
