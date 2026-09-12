# Second DFM enquiry to JLCPCB — DRAFT 2026-09-11, NOT YET SENT

The first enquiry (`JLCPCB-DFM-ENQUIRY.md`) is marked RESOLVED, and it is — but only for the one
thing they answered. Their reply was the capability-table row *"Multilayer: 0.09 / 0.09 mm
(3.5 / 3.5 mil). 3 mil is acceptable in BGA fan-outs"*, and that settled line and space. The
message drafted in that file was written **after** they replied and was never sent, so its
questions 4, 5 and 6 are still open. Three more have accumulated since, and one of them is
blocking a change that is otherwise ready to make.

Fab choice re-confirmed 2026-09-11: **JLCPCB**, 6 layers, all through-holes, ball land 0.225 mm.
A full PCBWay alternative was priced the same day and rejected — they are worse on escape margin,
on annular ring and on inner line/space.

---

## The board, in one paragraph

69.85 × 25.40 mm, 6 copper layers, 1.6 mm nominal, **all through-holes — no blind, buried or
microvias**. The critical part is a Xilinx XC7A35T in **CPG236, 0.5 mm ball pitch, 238 balls**.
Lands are **0.225 mm** (8.86 mil) round, leaving **0.2748 mm** between adjacent land edges. One
trace escapes between two lands, so it needs `width + 2 × clearance ≤ 0.2748 mm`; at the 3 mil
width and 0.09 mm clearance you have already confirmed, that is 0.2562 mm and it clears by
**+0.0186 mm**. Finish is ENIG. Nothing is routed yet.

---

## Question 1 — minimum inner copper to board edge  ← THIS ONE IS BLOCKING

Both internal layers (L2 and L5) are solid ground planes. They are currently pulled back
**0.51 mm** from the board outline. We want to reduce that to **0.25 mm**.

> **What is your minimum inner-layer copper to board edge on a routed (not V-scored) outline?**

It is worth asking rather than assuming because at 0.51 mm the pullback is causing four real
defects on our own DRC, all in the same corner of the 40-pin header:

- pin 20 (GND, at 1.270 / 24.130) has **0.7595 mm** to two plane edges against the **0.8068 mm**
  a 45° relief spoke corner needs, so 3 of its 4 thermal entries are blocked on both planes;
- pin 40 (a signal pin, 0.758 mm void) traps a **~0.124 mm²** island of dead copper in the
  south-west corner of each plane.

At a 0.25 mm inset all four clear in one edit: 1.020 mm against 0.8068 (margin +0.213) and
against 0.758 (margin +0.262). If 0.25 mm is not acceptable, **what is the smallest inset you
will run**, and does the answer change if the outline is routed with a 2.0 mm cutter?

## Question 2 — 0.050 mm annular ring on a 0.20 mm drill

Every fan-out via is **0.20 mm drilled, 0.30 mm finished land — a 0.050 mm (2.0 mil) annular
ring**, and there are on the order of 250 of them, most inside or beside the BGA field.

Your published minimum via is 0.15 mm drill on a 0.25 mm land, which is the same 0.050 mm ring.
We use 0.20 mm rather than 0.15 mm deliberately: through 1.6 mm, a 0.15 mm hole is 10.7:1 and over
the 10:1 aspect ceiling, where 0.20 mm is 8.0:1.

> **Please confirm in writing that a 0.050 mm annular ring on a 0.20 mm drill is standard process
> for you at 6 layers, and that it carries no surcharge beyond the 3–3.5 mil line/space one.**

## Question 3 — the 0.225 mm BGA land, and its mask opening

> **a.** Will you build a **0.225 mm** ENIG land as drawn, with **no DFM enlargement**? The land
> is the one term in `width + 2 × clearance` that is ours to choose, and UG475 gives 0.275 mm as a
> *maximum*, not a requirement. If your process enlarges it, the escape closes and the board does
> not work.
>
> **b.** Solder mask expansion is 0.05 mm, so a 0.225 mm land gets a **0.325 mm opening**, leaving
> a **0.175 mm (6.9 mil) dam** between adjacent openings with the escape trace running underneath.
> **Will you hold that dam, or will your CAM join the openings?** If you will not hold 0.175 mm,
> say what you will hold, because the alternative is a mask-defined pad and we would rather know
> now.
>
> **c.** Is there a **minimum ENIG pad diameter** below which you decline? 0.225 mm is 8.86 mil.

## Question 4 — the stackup, which is custom

We are not using JLC06161H. Your stock 6-layer build puts the thick cores at L2/L3 and L4/L5 and
leaves only 0.1164 mm between L3 and L4 — but L3 and L4 are our two inner **signal** layers and
they carry a 39-net SDRAM bus, so that build couples the bus to itself rather than to a reference
plane. We have specified the opposite, using materials you stock:

| | material | thickness | Dk |
|---|---|---|---|
| Top | copper, 0.5 oz base plated to 1 oz | 0.0356 mm | |
| | prepreg **3313** | **0.0994 mm** | 4.1 |
| L2-GND | copper 0.5 oz | 0.0175 mm | |
| | prepreg **2116** | **0.1164 mm** | 4.1 |
| L3-SIG | copper 0.5 oz | 0.0175 mm | |
| | **FR-4 core** | **1.0173 mm** | 4.8 |
| L4-SIG | copper 0.5 oz | 0.0175 mm | |
| | prepreg 2116 | 0.1164 mm | 4.1 |
| L5-GND | copper 0.5 oz | 0.0175 mm | |
| | prepreg 3313 | 0.0994 mm | 4.1 |
| Bottom | copper, 0.5 oz base plated to 1 oz | 0.0356 mm | |

Total **1.610 mm** including 0.4 mil of solder resist each side.

> **a.** Will you press this, and if not, what is the nearest build you will press? A ~1.0 mm core
> between L3 and L4 with thin prepreg everywhere else is the requirement; the exact numbers are
> yours to set.
>
> **b.** We need **0.5 oz base outer copper plated to 1 oz finished**, not 1 oz base — at a 1 oz
> etch bias the fan-out clearance falls below your own minimum. Please confirm that is what your
> standard build does, since the design passes DRC on nominal geometry and etch bias is not in it.
>
> **c.** There is one **90 Ω differential pair** (USB 2.0) on the top layer, currently drawn at
> 0.15 mm wide with a 0.15 mm gap. On the stack above that computes to roughly **88 Ω** with the
> solder mask. **What does your impedance calculation give for the stack you actually press?** We
> will move the width and gap to whatever you return.

---

*Nothing in this file is a JLCPCB statement. Every figure is either measured from our own design
files or read off JLCPCB's published capability tables. Replace each question with their verbatim
answer when it arrives, the way `JLCPCB-DFM-ENQUIRY.md` records the 2026-08-27 reply.*
