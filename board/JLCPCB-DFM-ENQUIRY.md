# DFM enquiry to JLCPCB — RESOLVED 2026-08-27

> ## Answered. The board needs nothing agreed.
>
> They replied by pointing at their capability table, row **Min. track width and
> spacing (1 oz)**:
>
> > 1- and 2-layer: 0.10 / 0.10 mm (4 / 4 mil)
> > **Multilayer: 0.09 / 0.09 mm (3.5 / 3.5 mil). 3 mil is acceptable in BGA fan-outs.**
>
> | our rule | vs the 1 oz multilayer standard | concession needed |
> |---|---|---|
> | spacing **0.0900 mm** | 0.09 — **meets it exactly** | **none** |
> | width **0.0762 mm** | 0.09 — below | the 3 mil BGA allowance, in the same sentence |
>
> **Even on the narrowest reading of "3 mil" — width only — this design is inside
> their published table as printed.** The spacing was never a concession; framing
> the question as "3.5 mil" is what obscured that.
>
> **And it is the 1 oz row**, so the allowance holds at standard copper weight.
> The 2 oz row drops to 0.15 / 0.15 multilayer, so the weight does matter — and
> PCBWay puts its 3.5 / 3.5 only on the 18 µm row. That is a genuine advantage to
> JLCPCB, not a paper one.
>
> **Still unstated**, and now only an optional upgrade: whether "3 mil" covers
> spacing too. It is **not free** — at a 0.250 land the gap is 0.250 mm and the
> present 0.0762 / 0.0900 does not fit it (0.2562), so it would force 3 mil
> spacing through the whole fan-out and re-cut the escape, for 0.91:1 instead of
> 0.82:1 against the package pad. **Recommendation: stay at 0.225 and order.**
>
> The message below was drafted before they answered. Questions 4, 5 and 6 in it
> — ENIG pad, via land, mask bridge — are still worth asking and are still
> unanswered.

> **Why they asked "which 3.5 mil?"** Because there are two of them, and the
> question as put did not say which. My fault — the suggestion to ask was written
> loosely.
>
> | figure | mm | what it is |
> |---|---|---|
> | 3.5 mil | 0.0889 | JLCPCB's general multilayer **line and space**, published as 0.09 / 0.09 |
> | 3 mil | 0.0762 | their BGA fan-out exception — *"3 mil is acceptable in BGA fan-outs"* |
>
> And this board uses **one of each**: 0.0762 mm width with 0.0900 mm clearance.
> So "3.5 mil" in my question meant the **clearance**, not the width.
>
> **Give them millimetres.** 0.09 mm is really 3.54 mil, so every mil figure here
> is a rounding of a metric number that JLCPCB's own tables state in mm. Quoting
> mils is what created the ambiguity in the first place.

## The one thing worth leading with

**The clearance is not the ask.** 0.0900 mm is *exactly* JLCPCB's published
multilayer minimum, and the design holds it everywhere including inside the ball
field. The only figure below their standard is the trace **width**, 0.0762 mm
against 0.09 — which is precisely what their BGA fan-out note exists to permit.

That turns a request for two concessions into a request for one, and the one is
the one they already publish.

## The arithmetic, for the message

XC7A35T-CPG236, 238 balls, 0.5 mm pitch, PCB land 0.225 mm round:

    gap between two adjacent lands       0.500 - 0.225   = 0.2750 mm
    one trace through it                 0.0762 + 2 x 0.0900 = 0.2562 mm
    margin                                                   +0.0188 mm

| width / clearance | needs | vs 0.2750 gap |
|---|---|---|
| **0.0762 / 0.0900 — what the board uses** | 0.2562 | **fits by 0.0188** |
| 0.0889 / 0.0889 (3.5 / 3.5) | 0.2667 | fits by 0.0083 |
| 0.0762 / 0.0762 (3 / 3) | 0.2286 | fits by 0.0464 |
| 0.1016 / 0.1016 (4 / 4) | 0.3048 | short by 0.0298 |

**If they allow 0.0762 mm clearance as well**, the land can go back up to
**0.250 mm** (0.91:1 against the package pad, better solder-joint reliability)
and still clear by 0.0214 mm. That is the answer worth having, and it is
question 2 below.

---

Subject: **Re: BGA fan-out — clarification, in millimetres**

Hello, and apologies for the ambiguity — there are two different figures in play
and I did not say which. In millimetres there is no room for confusion:

My design uses **0.0762 mm trace width** and **0.0900 mm clearance**.

So the 3.5 mil I mentioned was the **clearance**, not the width.

To be clear about what I am and am not asking for:

- **I am not asking for reduced clearance.** 0.0900 mm is exactly your published
  multilayer minimum and I hold it everywhere, including between the BGA balls.
- **The only figure below your standard is the trace width**: 0.0762 mm against
  your published 0.09 mm. That is what I understood your note *"3 mil is
  acceptable in BGA fan-outs"* to allow.

The geometry, so you can see why it is needed:

| | |
|---|---|
| Part | AMD/Xilinx **XC7A35T-CPG236**, 238 balls, **0.5 mm pitch** |
| Board | 6 layer, FR-4, 1.6 mm, ENIG, 69.85 × 25.40 mm |
| PCB land | **0.225 mm** round NSMD |
| Gap between two adjacent lands | 0.500 − 0.225 = **0.275 mm** |
| One trace between them | 0.0762 + 2 × 0.0900 = **0.2562 mm** |
| Margin | **0.0188 mm** |

The middle ring of balls is fully enclosed, so those signals have no way out
except between two lands on the outer layer. At 0.09 mm width the same trace
would need 0.2689 mm and the margin drops to 0.006 mm, which I would not want to
build to.

**My questions:**

1. Please confirm **0.0762 mm trace width at 0.0900 mm clearance in the BGA
   fan-out area** on a 6-layer board. Is that the correct reading of your 3 mil
   allowance?

2. Does the allowance extend to **clearance as well**, i.e. 0.0762 mm both? If it
   does I would rather **increase the land to 0.250 mm** for better solder-joint
   reliability — at 0.250 mm the gap is 0.250 and 0.0762 + 2 × 0.0762 = 0.2286
   still clears by 0.0214 mm. A larger land is the better board if you allow it.

3. Does the BGA fan-out allowance depend on **outer copper weight**? I have
   assumed your standard 6-layer build and have not asked for anything unusual.

While I have you, three smaller ones on the same board:

4. **BGA pad 0.225 mm with ENIG** — your table gives 0.2 mm as the minimum for
   ENIG, so I believe this is comfortable. Please confirm.

5. **Via 0.2 mm drill with a 0.3 mm land.** I avoided 0.15 mm deliberately: on a
   1.6 mm board that is 10.7:1 aspect, over the 10:1 I understand you work to.
   0.2 mm is 8:1. Is 0.3 mm land on 0.2 mm drill acceptable?

6. **Solder mask.** At a 0.325 mm opening on a 0.225 mm land the mask bridge
   between adjacent openings is 0.175 mm. Will you hold that, or do you prefer to
   drop the mask between balls in the fan-out area?

Thank you —

**[YOUR NAME]**

---

## Notes for me, not for JLCPCB

- **Answer to Q1 = yes** changes nothing. `board/zulu_a7-6layer-jlcpcb.dru` is
  already exactly 0.0762 / 0.0900 and the board is routed to it.
- **Answer to Q2 = yes** is the good outcome: land 0.225 → 0.250 across all 238
  pads. `make_board.py --fab` owns the land and asserts the count at 238, so it
  is a one-line change and a regenerate. It would also widen the escape's
  margins everywhere and may relax the fan-out.
- **Answer to Q1 = no** would be serious: the land would have to drop to about
  0.200 mm to fit 0.0889 / 0.0889, and that is at JLCPCB's own ENIG floor of
  0.2 mm with nothing to spare.
- Q5 matters for the stage-2 moat: the escape currently uses a 0.2 mm drill with
  a 0.30 mm land and 54 of them land in the moat.
- Ask PCBWay Q2 as well — it is the same question and their answer is still
  outstanding. See `board/PCBWAY-DFM-ENQUIRY.md`.
