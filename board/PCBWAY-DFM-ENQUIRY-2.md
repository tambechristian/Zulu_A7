# Second DFM enquiry to PCBWay — DRAFT 2026-09-11, NOT YET SENT

The first enquiry (`PCBWAY-DFM-ENQUIRY.md`, sent 2026-08-26, answered 2026-08-27) asked about the
BGA **pad**. It was answered. The binding constraint was always the **space between** pads, and
that was never put to them. Since then the board has moved to Altium, the placement is finished
and verified, and three of PCBWay's published numbers now collide with what is drawn.

These are the three questions whose answers decide the build. Everything else is settled.

---

## The board, in one paragraph

69.85 × 25.40 mm, 6 copper layers, 1.6 mm nominal, **all through-holes — no blind, buried or
microvias**. The critical part is a Xilinx XC7A35T in **CPG236, 0.5 mm ball pitch, 238 balls**.
Lands are **0.225 mm** (8.86 mil) round, which leaves **0.2748 mm** between adjacent land edges —
that gap is the whole problem. One trace escapes between two lands: it needs
`width + 2 × clearance ≤ 0.2748 mm`. Finish is ENIG. Nothing is routed yet, so any of this can
still be designed around.

---

## Question 1 — fine line and space, local to the BGA, at your standard finished copper

Your Advanced capability table, item 15 (outer layer minimum width/space), row **18 µm**:

> Normal ≥4/5 mil · Medium ≥4/4 mil **or parts 3.5/3.5 mil** · Unable to make <3.5/3.5 mil
> Remark: *"Local 3.5/3.5mil, only the distance from the GBA chip area line to the PAD"*

and row **35 µm**: Normal ≥5/6 mil · Medium ≥5/5 mil · **Unable to make <4/4 mil**.

Every one of your published 6-layer 1.6 mm structures specifies **"Outer Base Copper 0.5 OZ
(Plating to 1 OZ)"**, and item 21 gives through-hole copper as 18–25 µm, so an 18 µm *finished*
outer layer cannot exist on a plated board. We therefore read the 18 µm row as **base foil**, i.e.
as describing your standard 0.5 oz-base / 1 oz-finished build.

**Please confirm or correct that reading, and answer directly:**

> On your standard 6-layer 1.6 mm build with 0.5 oz base outer copper plated to 1 oz finished,
> what is the minimum line **and** space you will hold **locally inside a 0.5 mm-pitch BGA
> fan-out**?

We need one of these, and the difference matters:

| line/space | needs | margin in the 0.2748 mm gap | verdict |
|---|---|---|---|
| 3.0 / 3.0 mil | 0.2286 mm | **+0.0462 mm** | comfortable |
| 3.5 / 3.5 mil | 0.2667 mm | **+0.0081 mm** | works, 4 µm per side |
| 4.0 / 4.0 mil | 0.3048 mm | **−0.0300 mm** | **impossible** |

Your sales reply of 2026-08-27 said *"the min trace wid/spa we can do is 3/3mil"*, your order form
lists 3/3 mil as a selectable option, and your BGA help page says *"the minimum BGA to line is
3MIL (the prototype limit can be 2.5MIL)"*. If 3/3 mil is available to us here, say so and we will
keep the 3 mil traces already drawn. If the answer is 3.5/3.5 mil we will widen them and accept
the tighter margin. **4/4 mil means you cannot build this part, so please be explicit.**

## Question 2 — annular ring on a 0.20 mm drill  ← THE ONE THAT DECIDES THE MOST

Every fan-out via is **0.20 mm drilled, 0.30 mm finished land — a 0.050 mm (2.0 mil) annular
ring**. Item 17 (35 µm, via hole) reads Normal ≥5 mil · Medium ≥4 mil · Non-standard review
<3 mil · (unable-to-make cell empty).

> **Will you run a 0.050 mm annular ring on a 0.20 mm drill on this board, and at what process
> tier and cost?**

This is not a detail. At your *medium* tier the ring becomes 4 mil and the land grows to
**0.4032 mm**, and then:

- a via can no longer sit in the **interstitial (diagonal) position** between four balls — that
  position allows a 0.3295 mm land and no more, so the entire fan-out strategy changes;
- every via's plane anti-pad grows by **27 %**, on a stack whose two internal layers are solid
  ground and are the return path for a 39-net SDRAM bus;
- vias must move to vacant positions on the ball grid, which is a different — and worse — escape.

If 0.050 mm is a non-standard-review item rather than a refusal, please tell us what the review
needs and what it costs, because we would rather pay than re-cut the fan-out.

## Question 3 — the stack, and two numbers that go with it

Asked for a 6-layer stackup on 2026-08-27 you answered: *"the stack-up can be customized based on
the impedance value, we don't have standard stack-up info for that."* So we are specifying one.

The board must have **each inner signal layer close to its adjacent ground plane, and the two
inner signal layers far from each other** — L3 and L4 carry a 39-net SDRAM bus and must not couple
to one another. Your published 6-layer entries do the opposite: 0.430 mm cores at L2/L3 and L4/L5
with only 0.175 mm of 7628 between L3 and L4. **That construction is not usable for this board.**

Layer order is: L1 signal / **L2 ground plane** / L3 signal / L4 signal / **L5 ground plane** /
L6 signal.

> **a.** Can you build a 6-layer 1.6 mm stack with roughly **0.10–0.13 mm** from L1 to L2 and from
> L5 to L6, roughly the same from L2 to L3 and from L4 to L5, and the **remaining ~0.9 mm as one
> core or bonded book between L3 and L4** — and if so, with which materials and what Dk?
>
> **b.** What is your tolerance on finished thickness, and what **thickness-to-drill aspect ratio**
> will you run? Our 0.20 mm drill through ~1.6 mm is 8:1, which your table puts on the boundary
> between normal and medium difficulty. If the stack lands thicker, we need to know where it stops.
>
> **c.** What is your minimum **inner copper to board edge**? We currently pull both ground planes
> back 0.51 mm from the outline and would like to reduce that to 0.25 mm.

Note for our own records: your 6-layer builds use **1 oz inner copper** with no 0.5 oz option,
which puts inner line/space on item 14's 35 µm row (**unable to make <3.5/4 mil**). The SDRAM bus
on L3/L4 will be drawn to **≥4 mil space** accordingly.

---

## Two things we will state on the order, please confirm both are right

1. **Advanced factory, not Prototype.** Your prototype-factory page requires *"BGA Pad to BGA Pad
   should be not less 0.35mm"* and *"the space between copper trace and BGA PAD should be at least
   0.15mm"*. Our pad-to-pad is 0.275 mm and our trace-to-pad will be ~0.09 mm, so the prototype
   factory cannot build this board at all.
2. **The 0.225 mm BGA land is to be built as drawn, with no DFM enlargement.** At 8.86 mil it sits
   in the medium band of your item 18 (BGA pad diameter, immersion gold: 8.0–11.0 mil); your
   normal-process figure of 11 mil would close the escape completely. Solder mask opening is
   0.325 mm, leaving a 0.175 mm dam between adjacent openings — please confirm you will hold that
   rather than joining the openings.

---

*Nothing in this file is a PCBWay statement. Every figure above is either measured from our own
design files or read off PCBWay's published pages on 2026-09-11, and the published figures are
cited so they can be re-checked. Replace each question with their verbatim answer when it arrives,
as `PCBWAY-DFM-ENQUIRY.md` does.*
