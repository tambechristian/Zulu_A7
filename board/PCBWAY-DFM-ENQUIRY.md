# DFM enquiry to PCBWay — SENT 2026-08-26, ANSWERED 2026-08-27

## Their reply, in full

> Hi Christian,
>
> Glad to hear from you. The bga pad we could build is 8mil and pitch 0.4mm. So
> your design would be okay for us to handle. And both 0.5 oz and 1oz would work.
> For impedance calculate, please follow this page:
> https://www.pcbway.com/pcb_prototype/impedance_calculator.html
> The cost depends on the complete design, I'm unable to tell right now.
>
> HDI structure would add the manufacturing a lot, so planA would be recommended
> to use if you want to save the cost.

## What it settles

| # | question | answer |
|---|---|---|
| 3 | is a small land acceptable on a 0.5 mm-pitch BGA | **yes** — they build down to **8 mil = 0.2032 mm**, at pitches down to 0.4 mm. Our 0.225 mm land has 0.022 mm of margin over their floor |
| 5–7 | HDI: laser via, cost, stackup | **HDI is out.** "would add the manufacturing a lot… planA would be recommended". The 1+4+1 worry about landing every ball on L2 dies with it |
| 8 | would you build this differently | no — "your design would be okay for us to handle" |
| 1 (part) | does 3.5/3.5 mil require 18 µm outer copper | they say **0.5 oz and 1 oz both work**, which are heavier than the 18 µm row their 3.5/3.5 remark sits on. See the contradiction below |

**Acted on:** the PCBWay variant is now **Plan A** — conventional through-hole,
HDI dropped, land **0.275 → 0.225**, the same as JLCPCB. The two fab boards now
differ *only* in the rules file, and the escape geometry is identical for both.

## What it does not settle, and it is the one that matters

**They answered the PAD. The binding constraint is the SPACE BETWEEN pads.**

At 0.500 mm pitch, a trace escaping between two lands needs `w + 2s ≤ pitch − land`:

| land | gap | 3.5/3.5 mil needs 0.2667 | 4/4 mil needs 0.3048 |
|---|---|---|---|
| 0.275 (UG475 1:1) | 0.225 | short by 0.042 | short by 0.080 |
| **0.225 (ours)** | 0.275 | **fits by 0.008** | short by 0.030 |
| 0.2032 (their floor) | 0.297 | fits by 0.030 | **still short by 0.008** |

So **3.5/3.5 mil or finer is required whatever the land is** — even at the
smallest pad they will build. Shrinking the land does not get us to 4/4 mil.

And their two statements do not sit together comfortably: their published
3.5/3.5 mil sits only on the **18 µm outer copper** row (Advanced PCB item 15),
while the reply says **0.5 oz and 1 oz** both work — both heavier. Either the
3.5/3.5 is available at 1 oz after all, or the reply means "either copper weight
is fine for the board generally" and says nothing about the BGA area.

Questions **2, 4 and 9** also went unanswered: the 6-layer stackup (they pointed
at their impedance calculator instead of naming one), the 0.15 mm drill with a
3 mil annular ring, and whether the medium-difficulty parameters compound.

**ANSWERED 2026-08-27 — see "The follow-up, answered" below.** The line/space
question is settled and `board/zulu_a7-6layer-pcbway.dru` now carries PCBWay's own
numbers instead of JLCPCB's placeholder.

---

> **Original status banner, kept as it was written.**
>
> Research done while waiting has **changed the recommended answer**, and the
> full working is in `STACKUP.md` under "What the research found". The short
> version, so you can read PCBWay's reply against it:
>
> - The land was never the fixed quantity. At **0.225 mm** (0.82:1 against the
>   package pad, still legal under UG475's *maximum* of 0.275) the gap becomes
>   0.275 mm and a 3 mil trace at 3.5 mil clearance fits with 0.019 spare.
> - **JLCPCB publishes "3 mil is acceptable in BGA fan-outs"**, a minimum via of
>   0.15/0.25 mm, and 0.2 mm minimum BGA pads. PCBWay publishes none of those.
>   On paper the cheapest route that works is **back at JLCPCB**, for +20 % on
>   the order.
> - PCBWay's one unbeatable card is **HDI**, which JLCPCB does not do at all. It
>   is the only route that keeps the full 0.275 mm land, so **question 5, 6 and 7
>   below are now the ones that matter most.** If HDI comes back close in price,
>   it buys back the 1:1 land ratio and is worth it.
> - Their reply to **question 1** also settles something JLCPCB's wording leaves
>   ambiguous: whether a fab's "3.5 mil in the BGA area" means width and spacing
>   or width alone. Ask JLCPCB the same question before ordering there.
>
> Nothing in that research is a fab's confirmation — it is published capability
> tables plus this package's geometry.

**The text as sent** follows, with the quantity and name placeholders filled in
on the way out. Every figure in it was checked against `STACKUP.md`; that file
has since moved on, so read the banner above before acting on anything here.

**It went BEFORE routing, deliberately.** There are two separate things called
DFM and they happen at opposite ends of the job:

- **This enquiry** is a pre-layout capability question. It goes to a person —
  sales rep or engineering — not through the order flow. Its answer decides the
  BGA land diameter, the outer copper weight, the stackup and therefore every
  impedance width. A 0.275 mm land and a 0.200 mm land are different boards.
- **Their DFM review** is what happens automatically after you upload Gerbers
  with a real order. That one checks the files you actually drew.

Routing first and asking second means routing a board whose footprint may be
wrong, at the one spot — 238 balls at 0.5 mm pitch — where redoing it is
expensive.

The core of it: **their finest published rigid geometry does not escape this
package**, so the enquiry does not ask "can you do 2 mil" — it puts three
concrete build options in front of them and asks which one they will actually
make, and at what price.

---

Subject: **DFM enquiry — 6-layer, 0.5 mm-pitch BGA escape, three build options**

Hello,

I am laying out a small 6-layer board around a 0.5 mm-pitch BGA and I have
reached the point where your capability table and the package geometry do not
meet. I would rather ask before I commit the layout than send you something you
have to reject. Three build options are below; I would like to know which of
them you will make, and roughly what each costs relative to the others.

## The board

| | |
|---|---|
| Size | 69.85 × 20.32 mm |
| Layers | 6, FR-4, 1.6 mm class |
| Quantity | **[FILL IN]** |
| Surface finish | ENIG — the 0.5 mm pitch needs the coplanarity, please confirm |
| Preferred stackup | your standard 6-layer 1.6 mm, 1 oz outer / 1 oz inner, 70 % inner residual copper (the first entry in your multi-layer laminated structure list) |
| Layer use | L1 signal · L2 solid GND · L3 signal · L4 solid GND · L5 split power · L6 signal |
| Impedance | 50 Ω single-ended and one 90 Ω differential pair (USB) — I will send target widths for you to confirm |

## The part and the problem

Xilinx/AMD **XC7A35T-CPG236**: 238 balls, 0.5 mm pitch, package solder-mask-
defined pad 0.275 mm. UG475 Table A-1 gives a maximum PCB solder land of
0.275 mm and asks for a 1:1 ratio to the package pad "for improved board level
reliability", so my footprint is currently **0.275 mm round NSMD land with a
0.375 mm mask opening**.

That leaves **0.225 mm between two adjacent lands**. The ball field is three
complete rings (72, 64 and 56 balls) around an empty centre, so the middle ring
is fully enclosed — 64 balls whose only way out crosses one populated row.

Against your Advanced PCB item 15, *min width/spacing of outer layer*:

| rule | w + 2s needed | vs 0.225 mm available |
|---|---|---|
| 5/5 mil — 35 µm outer, medium | 0.3810 | short by 0.156 |
| 4/4 mil — 18 µm outer, medium | 0.3048 | short by 0.080 |
| **3.5/3.5 mil — 18 µm outer, local to BGA** | **0.2667** | **short by 0.042** |

A through via in the diagonal space between four balls does not help either: at
a 0.275 land with 3.5 mil clearance there is 0.2543 mm of room, and your
smallest via — 0.15 mm drill with a 3 mil annular ring — needs a 0.3024 mm land.

So I need to change something. Three options, in my order of preference:

## Option A — shrink the BGA land to 0.200 mm

Keep an ordinary through-hole 6-layer build, and give up the 1:1 land ratio.
0.200 mm round NSMD land, 0.300 mm mask opening, gap between lands 0.300 mm.
Then **3.5/3.5 mil clears by 0.033 mm** and a 0.15 mm via with a 3 mil ring
clears the diagonal void by 0.027 mm.

**Questions:**

1. Will you run **local 3.5/3.5 mil in the BGA area** on this board, and does it
   require **18 µm finished outer copper** (1/3 oz base plated up)? My reading of
   item 15 is that the 3.5/3.5 remark sits only on the 18 µm row, and that your
   standard 6-layer 1.6 mm builds are all 0.5 oz base plated to 1 oz.
2. If 18 µm finished outer is needed, **which 6-layer 1.6 mm stackup would you
   build?** It is not in your published list, so I need the dielectric
   thicknesses and Dk values to recalculate my impedance widths — the change in
   outer copper alone moves my 50 Ω microstrip by about 12 %.
3. Is a **0.200 mm land on a 0.5 mm-pitch BGA** acceptable to you, with a 0.300 mm
   mask opening (0.200 mm mask bridge between adjacent openings)? Any concern
   from your side on solder-joint reliability at that land size?
4. **0.15 mm drill with a 3 mil annular ring** is listed under high difficulty in
   item 17. Is it available on this board, and what does it add?

## Option B — HDI, laser via in pad

Keep the 0.275 mm land and put a laser via inside every ball land, so nothing
routes between balls at all. Your item 2 lists `HDI(1+1+…+N+…+1+1)` under normal
process, so I assume 1+4+1 is routine for you.

**Questions:**

5. What **laser via diameter and capture pad** would you use inside a 0.275 mm
   land, and is the via **filled and capped** (plated over) as I would need for a
   BGA?
6. Roughly what does 1+4+1 HDI cost against Option A at my quantity? If it is
   close, I would rather have the reliability of the full-size land.
7. Does HDI change the stackup? I need L2 and L4 to stay solid ground planes
   where possible, and a 1+4+1 build lands every ball on L2.

## Option C — do neither

8. If you would build this a different way, please say so. I am open to being
   told that a 0.5 mm-pitch 238-ball BGA on a 6-layer 1.6 mm board is the wrong
   idea at my volume.

## One more, independent of the option

9. Three of the parameters above sit in your **medium difficulty** or
   **non-standard review** columns — outer copper weight, local BGA line/space,
   and annular ring. Do they compound, i.e. does combining them push the whole
   board into a different class or a longer lead time, or are they priced
   individually?

To be clear about where I am: the board is **placed but deliberately not routed
yet**, and there are no Gerbers. I am asking now precisely because your answer
changes the BGA footprint itself — a 0.275 mm land and a 0.200 mm land are
different boards, and I do not want to route one and then find I needed the
other. I can send the placed board, the footprint, or a test coupon in whatever
form is most useful to you. Thank you —

**[YOUR NAME]**

---

## Notes for me, not for PCBWay

- Every number above is from `STACKUP.md`; the escape arithmetic is in "The
  number, recomputed against what PCBWay actually publishes" and the option
  table is "Three ways out".
- Question 2 is the one that determines real work: if they name a stackup, the
  trace-width table in `STACKUP.md` gets a third column and the `.dru`
  `mtIsolate` changes again.
- Do not let the reply talk us back to 2/2 mil. It is not in their tables and
  `check_board.py` section 7 now guards the `.dru` floor against it.

---

# The follow-up, answered — 2026-08-27

> I'm not sure about your question but the min trace wid/spa we can do is 3/3mil.
>
> As for the stack-up, it can be customized based on the impedance value, we
> don't have standard stack-up info for that.

Two sentences, and between them they answer all three questions.

| # | question | answer |
|---|---|---|
| 1 | is 3.5/3.5 mil available at 1 oz, or only at 18 µm outer? | **moot — their floor is 3/3 mil**, stated with no copper-weight qualifier at all. 3.5/3.5 at 1 oz is coarser than their minimum, so it is inside it |
| 3 | does "3.5 mil" mean width *and* spacing? | **both** — "trace wid/spa … 3/3mil" |
| 2 | the 6-layer stackup, for impedance widths | **they hold no standard stackup**: it is customised to an impedance target |

**Question 1 was the one blocking the order, and it clears.** The contradiction
this file recorded — their published 3.5/3.5 sitting only on the 18 µm outer row
while the reply said 0.5 oz and 1 oz both work — dissolves once 3/3 mil is the
floor. The BGA escape needs 3.5/3.5 at worst and has 0.008 mm of margin there;
at 3/3 it has 0.046 mm.

`board/zulu_a7-6layer-pcbway.dru` now carries **0.0762 mm** clearance in place of
the 0.09 mm inherited from JLCPCB, and `check_board`'s PCBWAY row expects it.

**One caveat, not yet decided.** A `.dru` clearance of 0.0762 mm *permits* 3 mil
everywhere; it does not require it. Sub-4-mil is an advanced-process tier at most
fabs and pricing it board-wide is not the same as pricing it in the BGA fan-out.
Nothing on the board currently uses tighter than 0.09 mm outside the escape. If
the SDRAM router starts exploiting 3 mil across the whole board, that is a cost
decision, not just a geometry one — check the quote before assuming it is free.

**Question 2 does not clear, it changes shape.** See `board/STACKUP.md`: the
stackup table there comes from PCBWay's *published* standard-stackup list, but
their DFM contact will not stand behind a standard build and works from an
impedance target instead. So the table is a planning assumption, not a
commitment, and controlled impedance needs a target stated before they can
answer.

---

# Follow-up — the text as drafted and sent

Short on purpose. Their first reply answered the pad; this asks the one thing
that decides whether the board can be routed at all. Everything else can wait.

---

Subject: **Re: DFM enquiry — one follow-up on line/space inside the BGA**

Hello, and thank you — that helps a lot. HDI is off my list on your
recommendation, and I have shrunk the BGA land to **0.225 mm**, comfortably above
the 8 mil you can build.

Two corrections to my first message, both since it was sent: the board is now
**69.85 × 25.40 mm** (it was 20.32 mm wide), and the BGA land is 0.225 mm rather
than the 0.275 I quoted. Everything else — 6 layers, 1.6 mm, ENIG, the layer
plan — is unchanged.

One thing your reply did not cover, and it is the number that decides whether I
can route the part at all. My constraint is not the pad, it is the **gap between
two adjacent pads**, because 64 of the 238 balls are fully enclosed and their
only way out is a trace passing between two lands on the outer layer.

At 0.5 mm pitch with a 0.225 mm land that gap is **0.275 mm**, and one trace
through it needs `width + 2 × clearance`:

| | needs | vs 0.275 mm |
|---|---|---|
| 3.5 mil / 3.5 mil | 0.2667 mm | fits, 0.008 to spare |
| 4 mil / 4 mil | 0.3048 mm | does not fit, short by 0.030 |

Shrinking the land further does not rescue 4/4 mil: even at your 8 mil minimum
pad the gap is 0.297 mm and 4/4 mil is still 0.008 mm short. So I need **3.5/3.5
mil or finer, locally in the BGA area**, whatever the land.

**My questions:**

1. **Will you run 3.5 mil line / 3.5 mil space locally in the BGA fan-out area
   on this board?** Your Advanced PCB item 15 lists 3.5/3.5 mil for a BGA area,
   but only on the **18 µm finished outer copper** row — and your reply says
   0.5 oz and 1 oz both work, which are heavier. Which is it for the BGA area?

2. If 3.5/3.5 mil requires 18 µm finished outer, is that available on this
   6-layer 1.6 mm board, and what does it change in the stackup? I need the
   dielectric thicknesses and Dk values to compute impedance widths — your
   calculator asks for them and I do not want to guess.

3. Does "3.5 mil" mean **width and spacing both**, or width only with spacing
   held at a coarser figure? Different fabs word this differently and it changes
   my answer by 0.038 mm, which is more margin than I have.

For reference, my current design rules are **0.0762 mm width / 0.090 mm
clearance** (3 mil / 3.5 mil), which clears the 0.275 mm gap by 0.019 mm. If you
will run that, the board is finished and I can send Gerbers.

Thank you —

**[YOUR NAME]**

---

## Notes for me

- If they say **yes to 3.5/3.5 at 1 oz**: nothing changes. `board/zulu_a7-6layer-pcbway.dru`
  is already correct and the two fab boards stay identical apart from the rules name.
- If they say **3.5/3.5 needs 18 µm outer**: the stackup changes, and with it
  every impedance width in `STACKUP.md`. That is question 2 and it is real work.
- If they say **4/4 mil only**: PCBWay cannot build this part on a rigid board at
  any land, and the answer is JLCPCB, who publish "3 mil is acceptable in BGA
  fan-outs" outright.
- Ask JLCPCB question 3 as well. Their wording has the same ambiguity and the
  active board is built on their number.
