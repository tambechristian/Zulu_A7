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

**1. Sheet 5's ball annotations are stale on three rows in four.** Beside each FPGA pin row is a
grey `<ball>  <pin function>` caption. It names a ball that no longer carries that row's net on 94
of 137 rows. Two independent methods agree: matching each caption to the live pin on its row gives
42 right and 94 wrong; cross-checking each caption against the exported netlist gives 34 right and
102 wrong. The failures are coherent, which is what makes it certain -- `SD-DAT2`'s row is captioned
`W2`, a ball that really carries SDRAM-CS#; `CHAN0`'s row says `W3`, which carries CAS#; `CHAN2`
says `W5`, which carries D5. It is the fingerprint of a pin reshuffle where the captions were left
behind.

It gets worse in the Pmod block, where the captions claim balls A14, A15 and W7. Those three balls
carry SDRAM D14, D15 and D2. The real Pmod balls are U18, U19, G17, C17, T17, E19, V19 and U17, and
the symbol's own pin NAMES still read `IO_A14`, `IO_A15`, `IO_W7`, so the old assignment is baked
into the symbol as well as the caption. Three balls appear double-booked on one page.

The pin designators -- the authoritative ones -- are correct throughout. But sheet 5 is the page a
layout engineer opens to decide swaps, bank grouping and VCCO, and it is about to be used that way.
This is the only finding in the review that can put a wrong net on a wrong ball.

*Fix:* regenerate the caption column from the pin designators, or delete it. The netlist is already
exported and the ball-to-function mapping is in `Datasheet/xc7a35tcpg236pkg_pinout.txt`, which
`tools/bom_audit.py` already reads. The two notes on the same sheet that depend on the old pin map
need rewriting with it.

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

**3. Every net label hangs below its wire while every pin number sits above its own.** The labels
are `Justification=8` -- anchored at the top of the text box -- so although the anchor is exactly on
the wire, the visible text is drawn underneath it. The pin designators are drawn above theirs. The
result is that each net name lines up with the NEXT pin's number: on sheet 2 `CHAN0` (pin 3) renders
level with the number 4; on sheet 3 `LDQM` (pin 15) renders level with 16; on sheet 5 `JA1` (ball
U18) renders level with U19. It affects about 200 rows across sheets 2, 3 and 5 -- X2's forty rows
in both columns, the Pmod, U3's and U4's left columns, and all 138 FPGA pin rows.

Sheet 2 is the sheet the 40-pin footprint gets drawn from, and reading horizontally across a header
to find which pin a signal is on is exactly the operation this breaks. Usually the pin name inside
the symbol saves you; on the Pmod it does not -- pin 11's `GND` lands on the `PMOD-10` line and says
pin 10 is ground.

*Fix:* one justification property on the label class. `tools/fix_text_orientation.py` already
carries the helpers for exactly this kind of pass. Highest payoff per keystroke in the review.

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

Nothing here blocks it. The two findings that touch the connector work are the label justification on
sheet 2, which is the sheet the footprint is drawn from, and the stale captions on sheet 5, which is
where the ball assignments get read. Both are worth clearing first because both are cheap, and
because a footprint drawn against a misread row is expensive to find later.
