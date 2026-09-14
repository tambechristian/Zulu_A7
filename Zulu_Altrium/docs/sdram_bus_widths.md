# SDRAM bus on L3/L4 — width, spacing and what the bus actually needs, 2026-09-14

**Status: APPLIED AND PROVEN, 2026-09-15.** Three analyses (signal integrity,
routability, fab and yield), each adversarially refuted, then a judge — 1.28 M tokens, all
numbers below survived refutation from the files or are marked general knowledge. The
implementation is `SetSdramRules` in `tools/ZuluSetup.pas`; `tools/verify_widths.py` carries
the targets.

## What the bus needs — and it is not 50 Ω

The 39 nets (`SDRAM_DATA` 16, `SDRAM_ADDR` 15, `SDRAM_CTRL` 8 incl. `SDRAM-CLK`) run from
XC7A35T LVCMOS33 outputs to an AS4C32M16SB-7TCN (143 MHz max, 3.3 V LVTTL, no termination) over
**9.2–18.9 mm (data) and up to 33 mm (A4)**, `SDRAM-CLK` 22.6 mm — measured from `Pads6`, not the
"4 mm shortest" the fact sheet assumed. Flight 65–235 ps. With that:

- **Z0 is not the constraint.** On L3/L4 every candidate width from 3 mil to 0.15 mm lies between
  60 and 45 Ω, and an unterminated bus this short with an 8 mA (~50 Ω, UG483 p.48) driver cannot
  tell them apart. **Overshoot is set by DRIVE, not width**: 8 mA gives ≤ +0.24 V at the open
  SDRAM input on the 33 mm run at *any* width; 12/16 mA FAST gives +0.7 to +1.0 V at 60 Ω and
  still +0.56 V at 39 Ω — widening cannot rescue a strong-fast driver.
- **Crosstalk is a spacing lever, nearly width-independent:** saturated NEXT coefficient ≈ 0.11–0.12
  at a 0.09 gap, 0.083 at 0.125, 0.051–0.054 at 0.20; realised over a 25 mm run at 1 ns ≈ 4 %
  of swing per neighbour at 0.09 (≈ 130 mV) against 0.8 / 1.3 V DC margins. Broadside L3/L4
  coupling 0.008 — no inter-layer offset needed.
- DC resistance 0.46 Ω (3 mil) → 0.28 Ω (0.125) on 31 mm; skew 192 ps across the bus, 69 ps within
  the data group, width-independent; against tIS 1.5 / tIH 0.8 ns — non-issues.
- **Timing is silicon-bound, not copper-bound:** CL3 direct capture at 143 MHz is
  tAC 5.4 + TD 0.22 + TIOPI 1.41 = 7.03 ns > tCK 7.0 before the IOB flop setup, so the board runs
  ~100 MHz or with a phase-shifted capture clock; copper is 0.2 ns of a 7–10 ns budget.
- **`SDRAM-CLK` is the one net where Z0 is a target:** a two-pin net (U1 M1 → U3 pad 38, no
  series resistor) that wants the driver's ~50 Ω — 0.10–0.125 mm — and a monotonic edge; the
  datasheet's tAC penalty [(tr+tf)/2 − 1] ns is zero up to a 2.0 ns edge.

So the width is chosen on **driver match, etch tolerance, yield and lanes**, and the answer is
0.125 mm: 49–50 Ω (the figure `stack_switch_3313E.md` already carried, verified within 2–3 %),
the best return against JLC's ±0.3–0.5 mil (±4.4 Ω vs ±7 Ω at 3 mil; diminishing past 0.125), and
above JLC's 3.5 mil baseline for ~591 mm of inner copper that cannot be reworked after
lamination — while the 3/3 mil +20 % tier is already bought by the BGA escape.

## Z0 on L3 (L4 mirrors it to the ohm)

Buried microstrip: 0.0152 mm copper on 0.100 mm Dk 4.6 over the L2 plane; the L5 plane 1.236 mm
below moves Z0 by 0.25 Ω. Three independent 2-D FD solves, two validated to < 1 % against Cohn.
Velocity 140.4–140.9 mm/ns at every width. Hammerstad-Jensen buried-microstrip agrees within
1 %; **Wadell's parallel combination reads 7 Ω high at this 12:1 asymmetry — do not use it here.**

| width mm | Z0 Ω | ±0.5 mil etch band | role |
|---|---|---|---|
| 0.0762 (3 mil) | 60 | 57–64 | Top escape only (geometry admits w ≤ 0.095 between lands) |
| 0.100 | 54 | 51–57.5 | inner / Bottom **min** — the neck |
| 0.125 | 49.5 | 47.3–51.9 | inner / Bottom **preferred** |
| 0.150 | 45.5 | 43–47.6 | **max** everywhere |
| 0.200 | 39 | 37.4–40.8 | rejected: 20 % below its neighbours, blocked in U3's 0.35 mm street |

## The rules

| rule | scope | Top | L3-SIG | L4-SIG | Bottom |
|---|---|---|---|---|---|
| `Width_SDRAM` | the three classes | 0.0762 / 0.0762 / 0.15 | 0.10 / **0.125** / 0.15 | 0.10 / **0.125** / 0.15 | 0.10 / 0.125 / 0.15 |
| `Clearance_SDRAM_INNER` 0.10 mm | the three classes **And** (OnLayer L3-SIG Or L4-SIG) vs All | — (global 0.09) | 0.10 | 0.10 | — |
| `Clearance_SDRAM_CLK` 0.20 mm | InNet('SDRAM-CLK') **And** (OnLayer L3-SIG Or L4-SIG) vs All | — | 0.20 | 0.20 | — |

*(min / preferred / max, mm)* — one Width table for all three classes so the only skew is the
length-dependent 192 ps; `SDRAM-CLK` gets the same width (≈ 50 Ω = the driver) and its own
clearance.

- **Top preferred must equal the 3 mil min**: the router lays the preferred and never necks on its
  own, and the ring-0/1 escape admits w ≤ 0.095 — a 0.10 preferred on Top was the readiness
  review's blocking defect. Max 0.15 lets a moat-via entry widen.
- **Inner min 0.10, not 3 mil**: no inner-layer passage needs a neck below 0.10 (0.5 mm via cells
  pass nothing at any width; 1.0 mm cells pass two 0.10–0.15 lanes). 3 mil on L3/L4 would be a
  DRC hole nothing needs.
- **Bottom min 0.10**: only the via-to-U3-pad stubs live there (< 2 mm into 0.45 mm pads on 0.8
  pitch); outer 3 mil in 0.035 mm plated copper is the hardest etch on the board and nothing
  forces it. Drop one cell to 0.0762 later if routing proves otherwise — costs nothing.
- **The two Clearance rules are scoped to L3/L4 only, never to Top or Bottom.** The ring-1 escape
  on Top has 0.0994 mm to each neighbouring land; any bus clearance ≥ 0.10 on Top closes the
  escape. `Clearance_SDRAM_INNER` is yield insurance, not SI: after JLC's +0.5–0.8 mil etch
  compensation a 0.09 space is tooled at 0.070–0.077 mm, a 0.10 space at 0.080–0.087, and at
  0.125 width it costs zero strip lanes. `Clearance_SDRAM_CLK` is the one clearance that is
  *derived*: the clock is the only always-switching aggressor beside 38 victims and the only
  victim whose threshold crossing is the timing — 0.20 halves the coupling (128 → 60 mV per
  aggressor over 25 mm). Price: about one to two strip lanes on the single inner layer it
  crosses.

## Channel budget at 0.125 / 0.10

U3 east copper 38.975 → U1 west land 41.7875 = 2.8125 mm, via land 0.35. North–south strip lanes
per layer with 0/1/2/3 vias at that y: **12 / 10 / 8 / 6** (11 / 9 / 7 / 5 on the clock's layer);
necked to 0.10 / 0.10: 13 / 11 / 9 / 6 — that is the relief if the strip ever binds, not 3 mil.
The strip's N–S count is moot for the bus at every width: the 17-net west-face sort needs 17
lanes and the strip holds 16 even at 3 mil, so `routing_readiness.md` already puts the sort in
U3's 20.8 mm pocket (~92 N–S lanes per layer at 0.125 / 0.10). East–west, the bus's real
direction: ~94 lanes per layer over the full cut (188 on L3 + L4 for 39 nets, 4.8×); over U1's
span with five fan-out vias in the column, 30 per layer, 60 against the 27 nets that cross there
(2.2×). Moat: adjacent 0.5 mm cells pass nothing at any width; 1.0 mm cells pass 2 lanes at
0.125 (3 at 3 mil); vias serving 0.5 mm-adjacent balls go to different columns — stagger, never
stack.

**Versus the 3 mil / 0.09 default:** strip 16 → 12 lanes (unused by the bus), E–W 127 → 94
(4.8× the need), Z0 60 → 49.5 Ω onto the driver, etch band 7 → 4.4 Ω, overshoot at 8 mA on the
33 mm run +0.24 → +0.10 V, NEXT 0.12 → 0.10 (bus) and 0.05 (clock). Fab cost: none — the +20 %
tier is already paid, impedance control is $0 and **the bus is not designated for it** (the width
tolerance already delivers ±5 % at 0.125; designating 39 nets would put CAM adjustments on
0.10 mm spaces).

## Preconditions outside the board

1. **XDC: DRIVE 8 (SLOW or FAST) or DRIVE 12 SLOW on all 39 outputs. Never 12/16 FAST** — that
   is +0.6–1.0 V on the SDRAM inputs at any width; the fix for a strong-fast driver is a series
   resistor, i.e. a schematic change, not a trace width.
2. Do not designate the SDRAM nets for impedance control in the JLC order — the USB pair stays
   the only designated net.
3. The one number no file settles: **read-direction overshoot at the FPGA** (VIN abs max
   VCCO + 0.55 = 3.85 V) from the SDRAM's LVTTL driver — IBIS/SPICE when the fan-out exists. The
   9–19 mm data lines and the 49.5 Ω line both help; one more reason for 0.125 over 3 mil.

## Corrections carried from the refuters, for the record

DS181 gives no output impedance or edge rate (the ~50 Ω driver figure is UG483's); VOH is
VCCO − 0.400, so pull-up and pull-down source resistance are equal (the 0.45 V was the LVCMOS18
row); SLOW adds 0.53–0.84 ns of TIOOP; the shortest run is 9.2 mm, not 4; the old-stack-to-new Z0
drop is 9–12 %; "127 lanes" is the full cut, not the 7.78 mm corridor.

## Verification — 2026-09-15, from the saved file and a preserved DRC report

1. `SetSdramRules` read back both clearance gaps and all twelve width values `ok` (the first
   attempt, on 2026-09-14, ran while Altium had silently dropped to viewer mode after a licence
   lapse — it logged but changed nothing; re-run after sign-in on a fresh instance).
2. Saved `Rules6`: **53 rules** (50 + 3). `Clearance_SDRAM_CLK` GAP = GENERICCLEARANCE = 7.874 mil
   at priority 1, `Clearance_SDRAM_INNER` 3.937 mil at 2, the global `Clearance` 3.5433 mil at 3,
   all `NETSCOPE=DifferentNets`, scopes byte-exact including the `OnLayer('L3-SIG')`/`'L4-SIG'`
   terms. `Width_SDRAM` at Width priority 1 with the five power rules and the global `Width`
   shifted to 2–7 and their values intact. `tools/verify_widths.py` **PASS** (7 Width + 3
   Clearance targets); `verify_stack.py` PASS; pads, tracks and texts identical to the previous
   commit as multisets.
3. **DRC proof** — `PlaceSdramProbes`, 15 tracks under U1 where L3/L4 carry no other copper
   (the first attempt in the x 60–62 corner sat on JP4-1's through-hole pad and drowned in noise).
   The report is kept as `docs/drc_probe_sdram_2026-09-15.drc`. Result: **exactly the designed
   set** — `Clearance_SDRAM_INNER` 1 (D0/D1 on L3-SIG, 0.095 < 0.10), `Clearance_SDRAM_CLK` 1
   (SDRAM-CLK/D4 on L4-SIG, 0.15 < 0.20), `Width_SDRAM` 3 (0.095 on L3-SIG under the 0.10 min,
   0.16 on L3-SIG over the 0.15 max, 0.095 on Bottom under the 0.10 min). The pass cases are
   proven by their absence at those exact counts: the 0.105 pair on L3, the 0.21 clock pair on
   L4, the 0.09 pair on **Top** (the inner-only scope holds), 0.0762 on Top and 0.125 on L4.
   Short-Circuit 0; the only other movement was the global 0.09 rule seeing the two Top probes
   against U1's lands.
4. `RemoveWidthProbes` deleted 15; saved file `Tracks6` 630 with none on a signal layer; DRC
   back to **605** (Un-Routed 603, every SDRAM rule 0), parsed from the report's own
   `Rule Violations` lines.
