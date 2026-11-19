# Series R at its planned position: SI re-simulation


## Findings

All figures below come from the tables in this file.

1. **The planned positions perform at least as well as an R at the pin.**
   - 22 ohm placed, fab stack: the worst read at the U1 ball uses 0.85 % of the DS181 Table 4 budget (D5, -0.218 V, max corner). Typ corner: 0 %. Die: 0 % at both corners.
   - With the R at U3's pin, the same bus is worse:
     - Ideal R (si/spice/wave *_r22): 17.1 % (D8, max).
     - With the same 0201 parasitics (parasitic_results_r22.json, variant 0201): 2.07 % (D5, max) and 7.71 % (D8, typ).
   - D8's R sits 11.1 mm of track down the line, close to U1. With an ideal R it scores 0 % there, against 17.1 % at the pin, so the position itself helps.
2. **Writes pass at every value.**
   - Worst U3 pin over all placed fab cases: -0.373 V / 3.570 V (15 ohm, max corner).
   - Limits are -1.0 / 4.6 V. Today's board (R0) reaches -0.385 / 3.642 V.
3. **Value choice:**
   - 15 ohm placed: passes with less margin. Worst ball budget is 6.6 % (D3, max), worst die 2.1 %; on the PcbDoc stack, 8.8 % (D3, max).
   - 22 ohm: no ringback into 0.8-2.0 V at any node, corner or stack.
   - 33 ohm: 0 % budget. But reads re-enter the 0.8-2.0 V band at the U1 ball on D5-D8 (up to 0.169 V, D7, max), and at the die by 0.003 V (D5, typ). Its read 10-90 % edge at the die reaches 1.35 ns.
4. **Timing cost at the 1.4 V crossing, compared with no R, 22 ohm placed:**
   - Reads, at U1's die: +0.032..+0.093 ns.
   - Writes, at U3's die: +0.097..+0.182 ns.
   - Read 10-90 % edge at the die: 0.31-0.34 ns -> 0.60-0.82 ns.
5. **D10 is still open.** As planned, the bus still fails at U1's ball on D10 at every R value (3059 % max, 2609 % typ). The die passes on all 16 nets. D13 (93.8 %), D14 (62.9 %) and D15 (42.9 %) pass unchanged. The optional R134 on D15 brings it to 0 %.
6. **The package model barely matters.** Ideal R gives 1.50 % (D3), the light set 0.51 % (D0), and the parts set 0.85 % (D5), all fab, max, 22 ohm.
7. **PcbDoc stack.** D0, D3, D5 and D6 are the four worst placed nets on the fab stack; D8 was added because the parts study flags it. At 22 ohm, max corner, the worst is 1.4 % (D8) and writes pass.

## Method and limits

- **Copper model.**
  - Each net is the judge's FINAL copper, applied with judge_check.py's own readers to board_extract.json (no apply errors).
  - It is split at the R into SDRAM-Dn (U3 pin .. pad 1) and Dn (pad 2 .. U1 ball). bus_sim's original net_elements() netlists each half: the new tracks get fieldsolve lines for their layer and width, and the new microvia columns get bus_sim's via ladder. Both halves are connected in every case.
  - The R is Rser - Lesl in series, with Cpar across and Cpad from each pad to ground.
- **Reproduction checks.**
  - Today's copper from the extract reproduces si/spice/wave (model.json) exactly: 64 R0 runs, max |dV| 0 V.
  - So does the R-at-pin mode: 8 runs at 22 ohm.
  - The placed 22 ohm read values equal the judge's and designers' own numbers (e.g. D0 -0.206 V, D8 -0.185 V, D9 -0.160 V, D12 -0.141 V).
- **Criteria.** Same as ds181_check.py / series_study.py:
  - Table 4 usage at the U1 ball and die, UI 7.5 ns.
  - Writes: SDRAM absolute maximum -1.0 / 4.6 V.
  - Ringback = re-entry into 0.8-2.0 V after the first threshold crossing (bus_sim measure()).
  - 10-90 % = bus_sim measure() at the receiver die.
  - Delay = shift of the first 1.4 V crossing, per edge (8.5 ns fall, 16 ns rise, 23.5 ns fall), compared with the no-R run of the same net, scenario, corner and stack.
  - Every run reached t_end = 32 ns. There was one case per process and at most 6 workers.
  - Wherever a waveform peak lies beyond the last row of Table 4 (0 % allowed), the table shows "off table" (ds181_check's infinite ratio).
- **Not modelled.**
  - Coupling between nets: adjacent new R pads, folded returns, and the Top bundle at x 38.5-40.2.
  - The plane openings the plan adds (the L2 openings at D12, the L5 openings at D9 that merge with the AIN16_N antipad). L2 and L5 are ideal planes.
  - The IBIS slow corner.
  - The south plan's changes to other nets (U3-9 VDDQ microvia, FT-VCORE trunk 0.5 -> 0.16 mm, TMS/TDO). These are power and decoupling questions, not part of this signal simulation.
- **Package values.** The 0201 package values are estimates, not datasheet values.
- **Board snapshot.** The board is the file on disk, PcbDoc md5 2a616c1c. Unsaved Altium edits are not included.

The source of every number is `sim_placed.json` (written by `sim_placed_report.py`) and the `sim_placed_raw_*.json` runs of `bus_sim_placed.py`. That script is a copy of `si/spice/bus_sim.py` with a PLACED option; the original is not edited. Board: `board_extract.json` (PcbDoc md5 2a616c1c) with the judge's FINAL copper edits applied by `judge_check.py`'s own plan readers. The R is the parts.md 0201 model unless stated: 0.5 nH ESL, 0.05 pF across, 0.08 pF per pad to ground.

Cases: 356, errors: 0, runs not reaching t_end 32 ns: 0. Each case ran in its own process, with at most 6 workers.

Reproduction check: 72 runs of today's copper (and the R-at-pin check cases) were compared with si/spice/wave. The largest |dV| at the receiver pin is 0 V.

## 1. Bus summary, fab stack (DS181 Table 4 at UI 7.5 ns; % = share of the allowed time used)

Columns: "R0 today" is the board as it is. "pin" is the R at U3's pin (ideal R, from si/spice/wave). "placed" is the R at the planned position with the 0201 model. Read rows cover the 12 nets that get an R; write rows cover the same 12 nets. The undershoot limit at U3 is the SDRAM's -1.0 / 4.6 V. Delay is the shift of the first 1.4 V crossing at the receiver die, compared with the no-R run (min..max over 3 edges and all nets).

| corner | case | READ worst ball budget (net) | ball fails | worst die budget | ball Vmin | ringback die / ball | t10-90 die ns | delay die ns | WRITE U3 pin Vmin/Vmax | abs-max | write ringback die / pin | write delay ns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| typ | R0_today | 37641.3 % (D5) | 8 | 47.3 % | -0.898 | 0.000 / 0.000 | 0.32-0.34 | +0.000..+0.000 | -0.336 / 3.389 | PASS | 0.000 / 0.000 | +0.000..+0.000 |
| typ | pin_r15 | 6.7 % (D8) | 0 | 0.0 % | -0.318 | 0.000 / 0.000 | 0.42-0.65 | +0.024..+0.039 | -0.264 / 3.332 | PASS | 0.000 / 0.000 | +0.063..+0.092 |
| typ | placed_r15 | 2.7 % (D0) | 0 | 1.1 % | -0.338 | 0.000 / 0.000 | 0.42-0.66 | +0.025..+0.076 | -0.284 / 3.342 | PASS | 0.000 / 0.000 | +0.074..+0.139 |
| typ | pin_r22 | 5.3 % (D8) | 0 | 0.0 % | -0.255 | 0.000 / 0.003 | 0.65-0.97 | +0.035..+0.060 | -0.229 / 3.321 | PASS | 0.000 / 0.000 | +0.089..+0.132 |
| typ | placed_r22 | 0.0 % (D0) | 0 | 0.0 % | -0.165 | 0.000 / 0.000 | 0.61-0.82 | +0.035..+0.091 | -0.248 / 3.326 | PASS | 0.000 / 0.000 | +0.101..+0.182 |
| typ | pin_r33 | 3.4 % (D8) | 0 | 0.0 % | -0.222 | 0.000 / 0.172 | 0.92-1.30 | +0.053..+0.104 | -0.177 / 3.307 | PASS | 0.000 / 0.000 | +0.127..+0.190 |
| typ | placed_r33 | 0.0 % (D0) | 0 | 0.0 % | -0.098 | 0.003 / 0.079 | 0.73-1.33 | +0.053..+0.123 | -0.187 / 3.308 | PASS | 0.000 / 0.000 | +0.139..+0.245 |
| max | R0_today | off table (D3) | 11 | 52.7 % | -0.981 | 0.000 / 0.535 | 0.31-0.34 | +0.000..+0.000 | -0.385 / 3.642 | PASS | 0.000 / 0.000 | +0.000..+0.000 |
| max | pin_r15 | 30.0 % (D8) | 0 | 0.0 % | -0.424 | 0.000 / 0.029 | 0.41-0.63 | +0.022..+0.042 | -0.360 / 3.562 | PASS | 0.000 / 0.000 | +0.048..+0.085 |
| max | placed_r15 | 6.6 % (D3) | 0 | 2.1 % | -0.435 | 0.000 / 0.000 | 0.41-0.65 | +0.022..+0.077 | -0.373 / 3.570 | PASS | 0.000 / 0.000 | +0.071..+0.125 |
| max | pin_r22 | 17.1 % (D8) | 0 | 0.0 % | -0.352 | 0.000 / 0.139 | 0.62-0.97 | +0.032..+0.066 | -0.344 / 3.539 | PASS | 0.000 / 0.000 | +0.074..+0.121 |
| max | placed_r22 | 0.8 % (D5) | 0 | 0.0 % | -0.218 | 0.000 / 0.000 | 0.60-0.81 | +0.032..+0.093 | -0.358 / 3.548 | PASS | 0.000 / 0.000 | +0.097..+0.161 |
| max | pin_r33 | 15.5 % (D8) | 0 | 0.0 % | -0.307 | 0.000 / 0.313 | 0.84-1.32 | +0.050..+0.114 | -0.284 / 3.510 | PASS | 0.000 / 0.000 | +0.117..+0.171 |
| max | placed_r33 | 0.0 % (D0) | 0 | 0.0 % | -0.136 | 0.000 / 0.169 | 0.72-1.35 | +0.048..+0.135 | -0.307 / 3.520 | PASS | 0.000 / 0.000 | +0.139..+0.215 |

A ringback value > 0 means the waveform re-enters the 0.8-2.0 V band by that many volts after its first crossing; a value <= 0 means it does not.

## 2. Whole bus as planned (12 placed R + D10/D13/D14/D15 unchanged), fab, READ

| corner | R | worst ball budget (net) | nets failing at the ball | nets failing at the die |
|---|---|---|---|---|
| typ | 15 | 2608.8 % (D10) | D10 | none |
| typ | 22 | 2608.8 % (D10) | D10 | none |
| typ | 33 | 2608.8 % (D10) | D10 | none |
| max | 15 | 3059.2 % (D10) | D10 | none |
| max | 22 | 3059.2 % (D10) | D10 | none |
| max | 33 | 3059.2 % (D10) | D10 | none |

## 3. Per net, fab, max corner (planned value 22 ohm)

| net | R ref / side | U3 pin to R copper mm (vias) | R0 ball budget | pin-R22 ball budget | placed-R22 ball Vmin | placed-R22 ball budget | die budget | read t10-90 ns | read delay die ns | write U3 pin Vmin/Vmax | write delay ns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | R119 Bottom | 0.96 (0) | 33760.2 % | 0.0 % | -0.206 | 0.50 % | 0.00 % | 0.63 | +0.063..+0.074 | -0.319 / 3.548 | +0.097..+0.133 |
| D1 | R120 Bottom | 0.96 (0) | 15.0 % | 0.0 % | -0.091 | 0.00 % | 0.00 % | 0.73 | +0.057..+0.070 | -0.255 / 3.527 | +0.119..+0.140 |
| D2 | R121 Bottom | 0.96 (0) | 17295.7 % | 0.0 % | -0.140 | 0.00 % | 0.00 % | 0.73 | +0.061..+0.076 | -0.283 / 3.526 | +0.124..+0.145 |
| D3 | R122 Bottom | 0.96 (0) | off table | 1.7 % | -0.198 | 0.00 % | 0.00 % | 0.81 | +0.056..+0.075 | -0.358 / 3.548 | +0.103..+0.131 |
| D4 | R123 Bottom | 0.96 (0) | off table | 0.0 % | -0.136 | 0.00 % | 0.00 % | 0.75 | +0.060..+0.080 | -0.339 / 3.522 | +0.105..+0.133 |
| D5 | R124 Bottom | 0.96 (0) | 65513.2 % | 0.0 % | -0.218 | 0.85 % | 0.00 % | 0.76 | +0.059..+0.088 | -0.333 / 3.530 | +0.114..+0.139 |
| D6 | R125 Bottom | 0.96 (0) | 11271.4 % | 0.0 % | -0.186 | 0.00 % | 0.00 % | 0.74 | +0.059..+0.083 | -0.321 / 3.530 | +0.116..+0.141 |
| D7 | R126 Bottom | 0.96 (0) | 338.9 % | 0.0 % | -0.181 | 0.00 % | 0.00 % | 0.74 | +0.058..+0.087 | -0.299 / 3.514 | +0.123..+0.139 |
| D8 | R127 Top | 11.13 (2) | 4949.9 % | 17.1 % | -0.185 | 0.00 % | 0.00 % | 0.62 | +0.032..+0.054 | -0.208 / 3.495 | +0.108..+0.131 |
| D9 | R128 Bottom | 13.87 (3) | 7618.3 % | 0.0 % | -0.160 | 0.00 % | 0.00 % | 0.64 | +0.047..+0.065 | -0.206 / 3.497 | +0.119..+0.139 |
| D10 | no R | - | 3059.2 % | 0.0 % | - | - | - | - | - | - | - |
| D11 | R130 Top | 6.97 (2) | 499.1 % | 0.0 % | -0.118 | 0.00 % | 0.00 % | 0.60 | +0.038..+0.063 | -0.166 / 3.480 | +0.110..+0.126 |
| D12 | R131 Top | 6.21 (4) | 155.1 % | 0.0 % | -0.141 | 0.00 % | 0.00 % | 0.69 | +0.077..+0.093 | -0.292 / 3.534 | +0.144..+0.161 |
| D13 | no R | - | 93.8 % | 0.7 % | - | - | - | - | - | - | - |
| D14 | no R | - | 62.9 % | 0.0 % | - | - | - | - | - | - | - |
| D15 (optional) | R134 Top | 1.35 (1) | 42.9 % | 0.0 % | -0.111 | 0.00 % | 0.00 % | 0.72 | +0.063..+0.078 | -0.290 / 3.529 | +0.126..+0.144 |

## 4. Package-model sensitivity (fab, max, 22 ohm, 12 plan nets)

| package | worst read ball budget (net) | ball Vmin | worst die budget | write U3 pin Vmin/Vmax |
|---|---|---|---|---|
| ideal R | 1.50 % (D3) | -0.228 | 0.00 % | -0.356 / 3.546 |
| light 0.3 nH / 0.03 pF / 0.04 pF | 0.51 % (D0) | -0.206 | 0.00 % | -0.358 / 3.548 |
| parts 0.5 nH / 0.05 pF / 0.08 pF | 0.85 % (D5) | -0.218 | 0.00 % | -0.358 / 3.548 |

## 5. PcbDoc stack, worst nets

| net | corner | case | read ball budget | read die budget | ball Vmin | write U3 pin Vmin/Vmax | abs-max |
|---|---|---|---|---|---|---|---|
| D0 | typ | R0 today | 1055.3 % | 37.5 % | -0.678 | -0.306 / 3.384 | PASS |
| D0 | typ | placed 15 | 3.4 % | 1.5 % | -0.335 | -0.265 / 3.341 | PASS |
| D0 | typ | placed 22 | 0.0 % | 0.0 % | -0.194 | -0.225 / 3.330 | PASS |
| D0 | typ | placed 33 | 0.0 % | 0.0 % | -0.104 | -0.159 / 3.312 | PASS |
| D0 | max | R0 today | 73534.3 % | 46.2 % | -0.889 | -0.382 / 3.611 | PASS |
| D0 | max | placed 15 | 8.6 % | 2.8 % | -0.422 | -0.337 / 3.575 | PASS |
| D0 | max | placed 22 | 1.3 % | 0.0 % | -0.244 | -0.331 / 3.554 | PASS |
| D0 | max | placed 33 | 0.0 % | 0.0 % | -0.143 | -0.278 / 3.516 | PASS |
| D3 | typ | R0 today | 53760.7 % | 38.6 % | -0.919 | -0.347 / 3.396 | PASS |
| D3 | typ | placed 15 | 2.9 % | 0.0 % | -0.379 | -0.301 / 3.354 | PASS |
| D3 | typ | placed 22 | 0.0 % | 0.0 % | -0.169 | -0.267 / 3.338 | PASS |
| D3 | typ | placed 33 | 0.0 % | 0.0 % | -0.097 | -0.206 / 3.313 | PASS |
| D3 | max | R0 today | off table | 43.6 % | -1.141 | -0.421 / 3.605 | PASS |
| D3 | max | placed 15 | 8.8 % | 2.0 % | -0.441 | -0.395 / 3.565 | PASS |
| D3 | max | placed 22 | 1.1 % | 0.0 % | -0.222 | -0.367 / 3.548 | PASS |
| D3 | max | placed 33 | 0.0 % | 0.0 % | -0.121 | -0.325 / 3.529 | PASS |
| D5 | typ | R0 today | 31269.3 % | 60.9 % | -0.851 | -0.326 / 3.388 | PASS |
| D5 | typ | placed 15 | 0.1 % | 0.0 % | -0.201 | -0.263 / 3.335 | PASS |
| D5 | typ | placed 22 | 0.0 % | 0.0 % | -0.152 | -0.231 / 3.317 | PASS |
| D5 | typ | placed 33 | 0.0 % | 0.0 % | -0.116 | -0.180 / 3.307 | PASS |
| D5 | max | R0 today | off table | 78.7 % | -0.956 | -0.376 / 3.623 | PASS |
| D5 | max | placed 15 | 2.1 % | 0.0 % | -0.313 | -0.380 / 3.552 | PASS |
| D5 | max | placed 22 | 0.0 % | 0.0 % | -0.191 | -0.356 / 3.537 | PASS |
| D5 | max | placed 33 | 0.0 % | 0.0 % | -0.144 | -0.281 / 3.515 | PASS |
| D6 | typ | R0 today | 1612.4 % | 52.0 % | -0.724 | -0.321 / 3.377 | PASS |
| D6 | typ | placed 15 | 0.7 % | 0.0 % | -0.221 | -0.249 / 3.329 | PASS |
| D6 | typ | placed 22 | 0.0 % | 0.0 % | -0.187 | -0.219 / 3.310 | PASS |
| D6 | typ | placed 33 | 0.0 % | 0.0 % | -0.138 | -0.171 / 3.308 | PASS |
| D6 | max | R0 today | 8717.8 % | 67.0 % | -0.822 | -0.370 / 3.621 | PASS |
| D6 | max | placed 15 | 1.0 % | 1.0 % | -0.246 | -0.373 / 3.551 | PASS |
| D6 | max | placed 22 | 0.2 % | 0.0 % | -0.203 | -0.345 / 3.535 | PASS |
| D6 | max | placed 33 | 0.0 % | 0.0 % | -0.145 | -0.264 / 3.512 | PASS |
| D8 | typ | R0 today | 39.8 % | 47.9 % | -0.496 | -0.323 / 3.371 | PASS |
| D8 | typ | placed 15 | 1.7 % | 1.1 % | -0.358 | -0.186 / 3.305 | PASS |
| D8 | typ | placed 22 | 0.9 % | 0.0 % | -0.240 | -0.127 / 3.305 | PASS |
| D8 | typ | placed 33 | 0.0 % | 0.0 % | -0.092 | -0.057 / 3.304 | PASS |
| D8 | max | R0 today | 1498.1 % | 49.2 % | -0.665 | -0.374 / 3.634 | PASS |
| D8 | max | placed 15 | 4.4 % | 2.0 % | -0.412 | -0.306 / 3.534 | PASS |
| D8 | max | placed 22 | 1.4 % | 0.0 % | -0.286 | -0.228 / 3.500 | PASS |
| D8 | max | placed 33 | 0.0 % | 0.0 % | -0.124 | -0.114 / 3.480 | PASS |
