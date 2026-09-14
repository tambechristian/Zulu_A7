# Power-rail Width rules — the per-layer table, 2026-09-14

**Status: see the Verification section at the end.** The rule set below was designed on
2026-09-14 from the files (three independent designs, three adversarial checks, one judge —
`tools/verify_widths.py` is the acceptance test) and applied by `SetPwrRailWidths` in
`tools/ZuluSetup.pas`.

## Why one rule could not do it

The plan in `stack_switch_3313E.md` said *"raise Width_PWR_RAILS preferred 0.400 → 0.500 mm,
max 1.000 → 1.500 mm"*. Half of that is right and half of it does nothing:

- **Altium's Width rule DRC-checks only min and max. Preferred is router guidance.** Raising the
  preferred to 0.500 changes no DRC outcome, and 0.500 mm on the new 0.0152 mm inner copper is
  **32 °C** for VCC3V3 at 662 mA and **36 °C** for VU at 697 mA. It is not a thermal answer.
- The min could not simply be raised either, because the rule's ten nets include four with
  balls under U1, and a BGA escape needs 3 mil on Top.
- The max 1.000 → 1.500 part is right: the inner floors below are 1.05 and 1.10 mm and must be
  expressible.

So the enforcement has to be a **per-layer min**, and the ten nets do not share one table.

## What the files said, that the plan had wrong

**Only VCC3V3 physically needs the 3 mil neck.** Read from `Pads6`, U1's 238 lands and their
nets (K10 is unpopulated):

| rail | balls | boxed by foreign nets on all four sides |
|---|---|---|
| VCC3V3 | 28 | **C18, V6, V9, V11** — ring 1, every neighbour a signal |
| VCC1V0 | 8 | none — G10/N10/N11 face empty positions, H10/M10/M11 each touch a same-net ball |
| VCC1V8 | 3 | none — C9, H13, J13 each face an empty position |
| VCCADC | 1 | none — C13 faces D13, empty |

So VCC1V0, VCC1V8 and VCCADC can be routed ball-to-ball and out without a neck, and giving
them a 3 mil min would only open a DRC hole they never need. If routing ever proves a neck
necessary on one of them, dropping that rule's Top min to 0.0762 costs nothing.

**The scalars are not aggregates.** `MINLIMIT / MAXLIMIT / PREFEREDWIDTH` in the file are the
uniform write-through values. `tools/ZuluRules.pas` writes them *after* the per-layer values,
which re-uniforms the table — it is now guarded to touch only the global rule named `Width`.
Before this change no Width rule on the board had ever carried a non-uniform table, so
whether one persists in the file was **unknown**; that is what the verification below proves.

## The rule set

IPC-2221, `I = k · ΔT^0.44 · A^0.725`, k 0.024 inner / 0.048 outer, at each rail's **MAX**
current from `tools/power_budget.py`, on 0.0152 mm inner and 0.035 mm outer copper. Inner mins
are the 10 °C widths **rounded up** to 0.05 mm; outer mins the 10 °C outer widths or the 0.15 mm
etch floor (JLC's −20 % leaves 0.12). Preferred is pad entry, not thermal.

| rule | scope | Top | L3 / L4 | Bottom | prio |
|---|---|---|---|---|---|
| `Width_PWR_VCC3V3` | `InNet('VCC3V3')` | **0.0762** / 0.20 / 1.5 | **1.05** / 1.05 / 1.5 | 0.20 / 0.30 / 1.5 | 1 |
| `Width_PWR_U8` | `InNet('VU') Or InNet('USB5V0') Or InNet('VBATT')` | 0.20 / 0.30 / 1.5 | **1.10** / 1.10 / 1.5 | 0.20 / 0.20 / 1.5 | 2 |
| `Width_PWR_VCC1V0` | `InNet('VCC1V0')` | 0.15 / 0.20 / 1.5 | **0.50** / 0.50 / 1.5 | 0.15 / 0.30 / 1.5 | 3 |
| `Width_PWR_SWITCH` | *(untouched)* | 0.20 / 0.50 / 1.5 uniform | | | 4 |
| `Width_PWR_RAILS` | `InNetClass('PWR_RAILS')`, edited in place | 0.15 / 0.20 / 1.0 | 0.15 / 0.20 / 1.0 | 0.15 / 0.30 / 1.0 | 5 |
| `Width` | *(untouched)* | 0.0762 / 0.0762 / 0.5 uniform | | | 6 |

*(min / preferred / max, mm)*

Where each number comes from:

| rail | max mA | 10 °C inner width | rule inner min | rise at it | 10 °C outer | rule outer min | rise at it |
|---|---|---|---|---|---|---|---|
| VCC3V3 | 662 | 1.0187 | **1.05** (1.00 = 10.3 °C) | 9.5 °C | 0.170 | 0.20 | 7.7 °C |
| VU | 697 | 1.0937 | **1.10** | 9.9 °C | 0.183 | 0.20 | 8.6 °C |
| USB5V0 | 495 | 0.682 | 1.10 (rides with VU) | 4.6 °C | 0.117 | 0.20 | 4.0 °C |
| VBATT | 244 | 0.257 | 1.10 (rides with VU) | 0.9 °C | 0.045 | 0.20 | 0.8 °C |
| VCC1V0 | 367 | 0.4515 | **0.50** (0.45 = 10.05 °C) | 8.5 °C | 0.075 | 0.15 | 3.2 °C |
| VCC1V8 | 77 | 0.052 | 0.15 floor | 1.8 °C | — | 0.15 | 0.1 °C |
| FT-VCORE | 70 | 0.047 | 0.15 floor | 1.4 °C | — | 0.15 | 0.1 °C |
| FT-VPHY | 60 | — | 0.15 floor | 1.0 °C | — | 0.15 | — |
| VCCADC | 25 | — | 0.15 floor | 0.1 °C | — | 0.15 | — |
| FT-VPLL | few | — | 0.15 floor | — | — | 0.15 | — |

**Why four rules.** Every distinct (Top, inner, Bottom) triple needs its own table: VCC3V3 is
the only one with a 3 mil Top; VU/USB5V0/VBATT share U8's 0.24 mm VQFN pads and the same
Bottom-pour strategy, and USB5V0/VBATT have no inner-layer pad, so riding at 1.10 costs them
nothing; VCC1V0 would be over-constrained 2× by either of those. The class rule is **edited, not
deleted**, so a net added to `PWR_RAILS` later falls to a 0.15 floor and not to the global
rule's 3 mil.

**Preferred widths.** 0.20 under the 0.225 mm U1 land and the 0.28 mm LQFP-64 pad — a 0.50 mm
track into a 0.28 pad on 0.5 mm pitch leaves 0.11 mm to the neighbour and fails JLC's 0.09 mm
mask-to-trace rule; 0.30 at the 0.300 mm 0201 pads on Bottom; 0.20 at U8's VQFN. Inner
preferred equals inner min so the router never lays 1.5 mm on a signal layer by accident.

**Priority.** `IPCB_Rule.Priority` is read-only; a new rule lands at 1. The three were created
VCC1V0, then U8, then VCC3V3, which yields the column above. Their scopes are disjoint so their
mutual order is cosmetic; what matters is that all three outrank `Width_PWR_RAILS`, and that is
read back from `Rules6`.

## What DRC still cannot see — stated, not hidden

- **A whole-rail 3 mil VCC3V3 track on Top** (37.5 °C at 662 mA) is legal under
  `Width_PWR_VCC3V3`, because DRC cannot tell a one-pitch ball escape from a 20 mm run. A
  preflight check should list every Top track in VCC3V3 under 0.20 mm whose midpoint is outside
  U1's land field. Not yet written; nothing is routed.
- **Solid pours are not width-checked** — a pour neck is reviewed by eye or script. Pours on
  these rails must be **solid**: a hatched pour is tracks, and every hatch line would fail the
  inner floor.
- **Via current** is not a Width matter at all.
- **IPC-2221 on 0.0152 mm inner copper is an extrapolation below its data set**, with the inner
  k halved by convention. Quote these as conservative screening figures, not temperatures.
  IPC-2152, with GND planes 0.1 mm away on L2/L5, would put the 10 °C inner widths at very
  roughly half — a reason not to widen further, not a licence to keep 0.400. At JLC's −20 % etch
  the inner floors give VCC3V3 13.7 °C and VU 14.3 °C; accepted on the same grounds.

**Two corrections to earlier prose, for the record.** `stack_switch_3313E.md` quoted *"VU
(495–720 mA) … 19.1 °C on 0.400 inner"* — 19.1 °C is at 495 mA on the old stack; the budget's
figure is 697 mA, which is 52.4 °C on 0.400 mm of the new inner copper. And *"0.240 mm 0201
lands"* (memory, `ZuluSetup.pas` comment) was wrong: every rail 0201 pad in `Pads6` is
0.300 × 0.300 mm; 0.240 mm is U8's VQFN16 pad.

## If JLC answer "3.5 mil"

Only `Width_PWR_VCC3V3`'s Top min changes, to 0.0889 mm; the escape margin drops from
+0.0186 to +0.0059 mm, still positive. Nothing else in the set moves.

## Verification

*(filled in as each step is done)*

1. `SetPwrRailWidths` read every one of the 48 per-layer values back through the same property
   it wrote — result: **pending**
2. Saved file, `tools/verify_widths.py --dump` — the per-layer keys Altium actually writes:
   **pending**
3. `tools/verify_widths.py` — **pending**
4. DRC proof with `PlaceWidthProbes` (13 tracks, 7 must violate, 6 must pass) — **pending**
5. Probes removed, `Tracks6` back to 630 records, DRC back to the 605 baseline — **pending**
