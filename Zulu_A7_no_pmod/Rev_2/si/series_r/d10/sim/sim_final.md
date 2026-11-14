# Whole-bus SI with the final D10 plan (13 series R)

Plan `d10/final_plan.json` (md5 f2949630ce86fb4640eb860d481d579a, PcbDoc md5 2a616c1c): R119-R131 at 22 ohm with the 0201 parasitic model (0.5 nH, 0.05 pF across, 0.08 pF per pad). D13, D14 and D15 have no R. They run on the plan-applied copper, which is identical to today's: the largest |dV| against the no-R run is 0 V. The simulator is `d10/sim/bus_sim_final.py`, a copy of the judge's `bus_sim_judge.py` (which is bus_sim_placed.py plus a plan-JSON reader). It differs only in paths, a per-task plan argument and the no-R handling; `make_sim.py` lists every edit.

Cases: 190 (placed_fab 64, base_fab 64, placed_pcbdoc 24, base_pcbdoc 24, repro12 10, repro_base 4). Errors: 0. Runs not reaching t_end 32 ns: 0. One case per process, at most 6 workers.

## Findings

1. **Fab stack, whole bus (16 nets): every read passes at the U1 ball and at the die, at both corners.**
   - Worst ball: 93.8 % (D13, max) and 18.1 % (D14, typ). Both are nets without an R.
   - Worst die: 29.1 % (D13, max).
   - Worst of the 13 nets with an R: 1.18 % (D10, max) and 0.55 % (D10, typ).
2. **D10 is fixed.**
   - Ball: 3059.2 % -> 1.2 % at max and 2608.8 % -> 0.6 % at typ. Die: 0.0 % at both corners.
   - PcbDoc stack: 1.3 % max / 0.7 % typ.
   - These are the judge's numbers exactly.
3. **No ringback** into 0.8-2.0 V at any node, corner, direction or stack.
4. **Writes pass on every net.** Worst at U3 pin: -0.359 / 3.620 V (fab, max), against limits of -1.0 / 4.6 V.
5. **Delay cost on the 13 nets with an R**, against the no-R run:
   - Reads at the U1 die: +0.032..+0.088 ns.
   - Writes at the U3 die: +0.097..+0.177 ns.
6. **PcbDoc stack: D13, D14 and D15 (no R) fail at the U1 ball.**
   - Max corner: D14 31238.8 %, D13 507.5 %, D15 368.0 %. Typ corner: D14 168.9 %.
   - Their die passes (worst 42.5 %).
   - These are the only failures in the run, and the D10 plan does not change them: their copper is identical to today's (0 V difference).
   - The fab stack, which is what PCBWay builds, passes them.
   - R132, R133 and R134 are the reserved designators for these three nets.

## 0. Reproduction of sim_placed.json

`repro_cmp.py` runs the adapted simulator on `dq_series_r_plan.json` (the 12-R plan) and on today's copper. It compares the waveforms sample by sample with `si/series_r/wave_placed/`.

| case | copper mm (new / sim_placed) | ball Vmin (new / sim_placed) | ball budget (new / sim_placed) | max abs dV |
|---|---|---|---|---|
| D8 read max placed | 15.771 / 15.771 | -0.1852 / -0.1852 | 0.00 % / 0.00 % | 0 V (identical) |
| D9 read max placed | 15.926 / 15.926 | -0.1595 / -0.1595 | 0.00 % / 0.00 % | 0 V (identical) |
| D12 read max placed | 12.597 / 13.372 | -0.1565 / -0.1412 | 0.00 % / 0.00 % | copper differs |
| D0 read max placed | 14.775 / 14.695 | -0.2058 / -0.2058 | 0.50 % / 0.50 % | copper differs |
| D5 read max placed | 22.564 / 22.564 | -0.2179 / -0.2179 | 0.85 % / 0.85 % | 0 V (identical) |
| D0 write max placed | 14.775 / 14.695 | -0.3196 / -0.3193 | - / - | copper differs |
| D8 write max placed | 15.771 / 15.771 | -0.2081 / -0.2081 | - / - | 0 V (identical) |
| D9 write max placed | 15.926 / 15.926 | -0.2062 / -0.2062 | - / - | 0 V (identical) |
| D12 write max placed | 12.597 / 13.372 | -0.2837 / -0.2922 | - / - | copper differs |
| D5 write max placed | 22.564 / 22.564 | -0.3332 / -0.3332 | - / - | 0 V (identical) |
| D10 read max base | 14.481 / 14.481 | -0.7161 / -0.7161 | 3059.19 % / 3059.19 % | 0 V (identical) |
| D13 read max base | 8.971 / 8.971 | -0.5288 / -0.5288 | 93.76 % / 93.76 % | 0 V (identical) |
| D10 read typ base | 14.481 / 14.481 | -0.7038 / -0.7038 | 2608.82 % / 2608.82 % | 0 V (identical) |
| D13 read typ base | 8.971 / 8.971 | -0.4379 / -0.4379 | 8.56 % / 8.56 % | 0 V (identical) |

- D5, D8, D9, D10 and D13 match to 0 V.
- D0 and D12 differ because their copper differs. sim_placed.json simulated the judge's FINAL plan before the DFM fixes. `dq_series_r_plan.json` includes both fixes:
  - F2 moves R119 0.04 mm south, so D0's U3 feed is 1.00 mm instead of 0.96.
  - F1 re-centres D12's U1-side column in R131-2, so D12 is 12.60 mm instead of 13.37.
- dq_series_resistors.md says the F1/F2 geometry "was not simulated". This run is its first simulation, and both nets stay within 0.02 V of the old values.

## 1. Bus summary

| stack | corner | nets | READ worst ball (net) | ball fails | worst die (net) | ringback ball / die V | WRITE U3 pin Vmin / Vmax | abs-max | write ringback V | read delay die ns (R nets) | write delay die ns (R nets) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fab | typ | 16 | 18.1 % (D14) | none | 21.4 % (D13) | 0.000 / 0.000 | -0.281 / 3.343 | PASS | 0.000 | +0.035..+0.086 | +0.101..+0.177 |
| fab | max | 16 | 93.8 % (D13) | none | 29.1 % (D13) | 0.000 / 0.000 | -0.359 / 3.620 | PASS | 0.000 | +0.032..+0.088 | +0.097..+0.156 |
| pcbdoc | typ | 6 | 168.9 % (D14) | D14 | 20.7 % (D13) | 0.000 / 0.000 | -0.301 / 3.360 | PASS | 0.000 | +0.037..+0.082 | +0.116..+0.145 |
| pcbdoc | max | 6 | 31238.8 % (D14) | D13, D14, D15 | 42.5 % (D14) | 0.000 / 0.000 | -0.356 / 3.620 | PASS | 0.000 | +0.034..+0.088 | +0.096..+0.136 |

The PcbDoc rows cover only the six nets run on that stack (section 3). A ringback value <= 0 means the waveform does not re-enter 0.8-2.0 V.

## 2a. Per net, fab stack, max corner

| net | R | U3->R mm (vias) | R0 ball | ball budget | die budget | ball Vmin | ringback ball / die V | read t10-90 die ns | read delay die ns | write U3 pin Vmin / Vmax | write die Vmin / Vmax | abs-max | write ringback V | write delay die ns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | R119 Bottom | 1.00 (0) | 33760.2 % | 0.5 % | 0.0 % | -0.206 | 0.000 / 0.000 | 0.63 | +0.063..+0.075 | -0.320 / 3.548 | -0.441 / 3.538 | PASS | 0.000 | +0.097..+0.134 |
| D1 | R120 Bottom | 1.00 (0) | 15.0 % | 0.0 % | 0.0 % | -0.091 | 0.000 / 0.000 | 0.74 | +0.057..+0.070 | -0.256 / 3.527 | -0.306 / 3.524 | PASS | 0.000 | +0.119..+0.140 |
| D2 | R121 Bottom | 0.96 (0) | 17295.7 % | 0.0 % | 0.0 % | -0.140 | 0.000 / 0.000 | 0.73 | +0.061..+0.076 | -0.283 / 3.526 | -0.333 / 3.531 | PASS | 0.000 | +0.124..+0.145 |
| D3 | R122 Bottom | 1.00 (0) | off table | 0.0 % | 0.0 % | -0.200 | 0.000 / 0.000 | 0.81 | +0.057..+0.075 | -0.359 / 3.548 | -0.455 / 3.558 | PASS | 0.000 | +0.104..+0.132 |
| D4 | R123 Bottom | 1.00 (0) | off table | 0.0 % | 0.0 % | -0.137 | 0.000 / 0.000 | 0.76 | +0.061..+0.080 | -0.339 / 3.522 | -0.412 / 3.553 | PASS | 0.000 | +0.105..+0.134 |
| D5 | R124 Bottom | 0.96 (0) | 65513.2 % | 0.8 % | 0.0 % | -0.218 | 0.000 / 0.000 | 0.76 | +0.059..+0.088 | -0.333 / 3.530 | -0.393 / 3.551 | PASS | 0.000 | +0.114..+0.139 |
| D6 | R125 Bottom | 0.96 (0) | 11271.4 % | 0.0 % | 0.0 % | -0.186 | 0.000 / 0.000 | 0.74 | +0.059..+0.083 | -0.321 / 3.530 | -0.374 / 3.543 | PASS | 0.000 | +0.116..+0.141 |
| D7 | R126 Bottom | 0.96 (0) | 338.9 % | 0.0 % | 0.0 % | -0.181 | 0.000 / 0.000 | 0.74 | +0.058..+0.087 | -0.299 / 3.514 | -0.327 / 3.524 | PASS | 0.000 | +0.123..+0.139 |
| D8 | R127 Top | 11.13 (2) | 4949.9 % | 0.0 % | 0.0 % | -0.185 | 0.000 / 0.000 | 0.62 | +0.032..+0.054 | -0.208 / 3.495 | -0.244 / 3.498 | PASS | 0.000 | +0.108..+0.131 |
| D9 | R128 Bottom | 13.87 (3) | 7618.3 % | 0.0 % | 0.0 % | -0.160 | 0.000 / 0.000 | 0.64 | +0.047..+0.065 | -0.206 / 3.497 | -0.228 / 3.489 | PASS | 0.000 | +0.119..+0.139 |
| D10 | R129 Top | 8.65 (2) | 3059.2 % | 1.2 % | 0.0 % | -0.272 | 0.000 / 0.000 | 0.60 | +0.035..+0.054 | -0.215 / 3.504 | -0.252 / 3.492 | PASS | 0.000 | +0.100..+0.124 |
| D11 | R130 Top | 7.15 (2) | 499.1 % | 0.0 % | 0.0 % | -0.120 | 0.000 / 0.000 | 0.60 | +0.038..+0.063 | -0.165 / 3.480 | -0.211 / 3.479 | PASS | 0.000 | +0.109..+0.126 |
| D12 | R131 Top | 6.21 (4) | 155.1 % | 0.0 % | 0.0 % | -0.157 | 0.000 / 0.000 | 0.68 | +0.072..+0.087 | -0.284 / 3.534 | -0.304 / 3.529 | PASS | 0.000 | +0.140..+0.156 |
| D13 | none | - | 93.8 % | 93.8 % | 29.1 % | -0.529 | 0.000 / 0.000 | 0.33 | +0.000..+0.000 | -0.299 / 3.617 | -0.444 / 3.669 | PASS | 0.000 | +0.000..+0.000 |
| D14 | none | - | 62.9 % | 62.9 % | 18.0 % | -0.528 | 0.000 / 0.000 | 0.32 | +0.000..+0.000 | -0.298 / 3.620 | -0.495 / 3.665 | PASS | 0.000 | +0.000..+0.000 |
| D15 | none | - | 42.9 % | 42.9 % | 16.4 % | -0.544 | 0.000 / 0.000 | 0.34 | +0.000..+0.000 | -0.292 / 3.593 | -0.466 / 3.663 | PASS | 0.000 | +0.000..+0.000 |

## 2b. Per net, fab stack, typ corner

| net | R | U3->R mm (vias) | R0 ball | ball budget | die budget | ball Vmin | ringback ball / die V | read t10-90 die ns | read delay die ns | write U3 pin Vmin / Vmax | write die Vmin / Vmax | abs-max | write ringback V | write delay die ns |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | R119 Bottom | 1.00 (0) | 843.3 % | 0.0 % | 0.0 % | -0.166 | 0.000 / 0.000 | 0.65 | +0.062..+0.070 | -0.215 / 3.326 | -0.283 / 3.335 | PASS | 0.000 | +0.132..+0.144 |
| D1 | R120 Bottom | 1.00 (0) | 4.7 % | 0.0 % | 0.0 % | -0.063 | 0.000 / 0.000 | 0.75 | +0.060..+0.070 | -0.137 / 3.306 | -0.190 / 3.306 | PASS | 0.000 | +0.119..+0.153 |
| D2 | R121 Bottom | 0.96 (0) | 312.9 % | 0.0 % | 0.0 % | -0.102 | 0.000 / 0.000 | 0.74 | +0.061..+0.074 | -0.155 / 3.307 | -0.209 / 3.307 | PASS | 0.000 | +0.128..+0.157 |
| D3 | R122 Bottom | 1.00 (0) | 28934.3 % | 0.0 % | 0.0 % | -0.145 | 0.000 / 0.000 | 0.83 | +0.058..+0.072 | -0.249 / 3.325 | -0.302 / 3.340 | PASS | 0.000 | +0.132..+0.140 |
| D4 | R123 Bottom | 1.00 (0) | 1396.0 % | 0.0 % | 0.0 % | -0.106 | 0.000 / 0.000 | 0.78 | +0.061..+0.075 | -0.224 / 3.315 | -0.274 / 3.320 | PASS | 0.000 | +0.130..+0.132 |
| D5 | R124 Bottom | 0.96 (0) | 37641.3 % | 0.0 % | 0.0 % | -0.142 | 0.000 / 0.000 | 0.78 | +0.065..+0.085 | -0.221 / 3.308 | -0.259 / 3.309 | PASS | 0.000 | +0.130..+0.139 |
| D6 | R125 Bottom | 0.96 (0) | 745.8 % | 0.0 % | 0.0 % | -0.121 | 0.000 / 0.000 | 0.75 | +0.062..+0.079 | -0.207 / 3.305 | -0.244 / 3.306 | PASS | 0.000 | +0.125..+0.144 |
| D7 | R126 Bottom | 0.96 (0) | 79.3 % | 0.0 % | 0.0 % | -0.123 | 0.000 / 0.000 | 0.79 | +0.063..+0.082 | -0.173 / 3.305 | -0.209 / 3.307 | PASS | 0.000 | +0.109..+0.146 |
| D8 | R127 Top | 11.13 (2) | 268.1 % | 0.0 % | 0.0 % | -0.152 | 0.000 / 0.000 | 0.63 | +0.035..+0.052 | -0.112 / 3.305 | -0.141 / 3.306 | PASS | 0.000 | +0.111..+0.147 |
| D9 | R128 Bottom | 13.87 (3) | 49.7 % | 0.0 % | 0.0 % | -0.108 | 0.000 / 0.000 | 0.64 | +0.049..+0.061 | -0.106 / 3.307 | -0.131 / 3.306 | PASS | 0.000 | +0.122..+0.162 |
| D10 | R129 Top | 8.65 (2) | 2608.8 % | 0.6 % | 0.0 % | -0.213 | 0.000 / 0.000 | 0.61 | +0.038..+0.052 | -0.124 / 3.305 | -0.152 / 3.306 | PASS | 0.000 | +0.112..+0.140 |
| D11 | R130 Top | 7.15 (2) | 28.1 % | 0.0 % | 0.0 % | -0.085 | 0.000 / 0.000 | 0.60 | +0.041..+0.058 | -0.086 / 3.306 | -0.119 / 3.306 | PASS | 0.000 | +0.101..+0.143 |
| D12 | R131 Top | 6.21 (4) | 218.7 % | 0.0 % | 0.0 % | -0.104 | 0.000 / 0.000 | 0.69 | +0.075..+0.086 | -0.152 / 3.308 | -0.190 / 3.308 | PASS | 0.000 | +0.135..+0.177 |
| D13 | none | - | 8.6 % | 8.6 % | 21.4 % | -0.438 | 0.000 / 0.000 | 0.33 | +0.000..+0.000 | -0.247 / 3.321 | -0.375 / 3.375 | PASS | 0.000 | +0.000..+0.000 |
| D14 | none | - | 18.1 % | 18.1 % | 8.3 % | -0.473 | 0.000 / 0.000 | 0.33 | +0.000..+0.000 | -0.281 / 3.343 | -0.393 / 3.421 | PASS | 0.000 | +0.000..+0.000 |
| D15 | none | - | 6.3 % | 6.3 % | 8.2 % | -0.439 | 0.000 / 0.000 | 0.34 | +0.000..+0.000 | -0.254 / 3.328 | -0.377 / 3.395 | PASS | 0.000 | +0.000..+0.000 |

## 3. PcbDoc stack: the four worst fab nets (D13, D14, D15, D10), plus D0 and D5

| net | R | corner | R0 ball | ball budget | die budget | ball Vmin | ringback ball / die V | read delay die ns | write U3 pin Vmin / Vmax | abs-max |
|---|---|---|---|---|---|---|---|---|---|---|
| D13 | none | typ | 76.2 % | 76.2 % | 20.7 % | -0.516 | 0.000 / 0.000 | +0.000..+0.000 | -0.257 / 3.326 | PASS |
| D13 | none | max | 507.5 % | 507.5 % | 27.6 % | -0.618 | 0.000 / 0.000 | +0.000..+0.000 | -0.302 / 3.620 | PASS |
| D14 | none | typ | 168.9 % | 168.9 % | 14.9 % | -0.572 | 0.000 / 0.000 | +0.000..+0.000 | -0.301 / 3.360 | PASS |
| D14 | none | max | 31238.8 % | 31238.8 % | 42.5 % | -0.836 | 0.000 / 0.000 | +0.000..+0.000 | -0.323 / 3.599 | PASS |
| D15 | none | typ | 21.5 % | 21.5 % | 12.8 % | -0.469 | 0.000 / 0.000 | +0.000..+0.000 | -0.259 / 3.341 | PASS |
| D15 | none | max | 368.0 % | 368.0 % | 17.0 % | -0.560 | 0.000 / 0.000 | +0.000..+0.000 | -0.282 / 3.599 | PASS |
| D10 | R129 | typ | 4605.3 % | 0.7 % | 0.0 % | -0.224 | 0.000 / 0.000 | +0.037..+0.052 | -0.134 / 3.305 | PASS |
| D10 | R129 | max | 12844.5 % | 1.3 % | 0.0 % | -0.292 | 0.000 / 0.000 | +0.034..+0.053 | -0.234 / 3.508 | PASS |
| D0 | R119 | typ | 1055.3 % | 0.0 % | 0.0 % | -0.193 | 0.000 / 0.000 | +0.061..+0.068 | -0.225 / 3.331 | PASS |
| D0 | R119 | max | 73534.3 % | 1.3 % | 0.0 % | -0.244 | 0.000 / 0.000 | +0.062..+0.072 | -0.331 / 3.554 | PASS |
| D5 | R124 | typ | 31269.3 % | 0.0 % | 0.0 % | -0.152 | 0.000 / 0.000 | +0.061..+0.082 | -0.231 / 3.317 | PASS |
| D5 | R124 | max | off table | 0.0 % | 0.0 % | -0.191 | 0.000 / 0.000 | +0.059..+0.088 | -0.356 / 3.537 | PASS |

## Method and limits

- **Copper.** board_extract.json (PcbDoc md5 2a616c1c) with final_plan.json applied by the judge's plan-JSON reader (renames = remove + re-add; 0 apply errors). Each net with an R is split at the R into SDRAM-Dn and Dn. Each half is netlisted by bus_sim's net_elements(), and both halves are connected in every case.
- **R model.** 22 ohm plus 0.5 nH in series, 0.05 pF across, and 0.08 pF from each pad to ground (the parts.md estimate).
- **Stacks.**
  - Fab: the PCBWay construction. L3/L4 at 0.125 mm is 43.4 ohm.
  - PcbDoc: the stack stored in the PcbDoc. Its inner dielectrics are thicker, so L3/L4 at 0.125 mm is 49.1 ohm.
- **Delay.** The shift of the first 1.4 V crossing at the receiver die, compared with the no-R run on today's copper (same net, scenario, corner and stack). Reported as min..max over the 8.5 ns fall, 16 ns rise and 23.5 ns fall edges.
- **Not modelled.**
  - Coupling, including the R127/R129/R130 column and the parallel Top runs at x 38.5-40.2.
  - Plane openings: L2 and L5 are treated as ideal planes.
  - The IBIS slow corner.
  - Uncertainty in the 0201 package values.
