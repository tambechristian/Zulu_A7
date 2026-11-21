## 7. Simulation of the placed resistors

Three runs, same physics.
- **12-resistor run:** `si/series_r/bus_sim_placed.py`, a copy of `si/spice/bus_sim.py` with a PLACED mode. 356
  cases, 0 errors. Runs at R=0 and with the resistor at the pin reproduce `si/spice/wave` with 0 V difference.
  Results: `sim_placed.json` and `sim_placed.md`. It also holds the 15/33 ohm and ideal-R comparisons below.
- **13-resistor run:** `si/series_r/d10/sim/bus_sim_final.py`, the same simulator with a plan-JSON reader and no
  physics change, on `dq_series_r_plan_13.json` md5 `f2949630`. 190 cases, 0 errors. Results: `d10/sim/`.
- **16-resistor run (this plan):** `si/series_r/d13/sim/bus_sim_final.py`, a byte copy of the 13-resistor simulator,
  on the combined plan `d13/final_plan.json` (md5 `6bd34bd7`), whose copper and parts are identical to
  `dq_series_r_plan.json` (the fold adds only the designator move and the VIPPO list). 306 cases: all 16 nets x 2
  stacks x 2 corners x read/write at 22 ohm, the no-R base runs, and a 15/33 ohm sweep on the PcbDoc stack. 0
  errors; every run reached t_end and was connected. Two cases reproduce `d10/sim` sample by sample (0 V), and all
  64 D0-D12 runs are bit-identical to the 13-resistor run, as expected for a per-net model without coupling.
  Results: `d13/sim/sim_final.json` (md5 `e35f3339`) and `sim_final.md`. It is also the first whole-bus run on the
  PcbDoc stack (the 13-resistor run covered only 6 nets there).
- In all of them, each net with a resistor is split into SDRAM-Dn and Dn, both built from the exact planned copper.
  The resistor model is 22 ohm with 0.5 nH, 0.05 pF across the part and 0.08 pF from each pad to ground.

Reads at the U1 ball, as a share of the DS181 Table 4 budget at UI 7.5 ns, 16-resistor run. Fab stack: L3/L4 43.4
ohm; PcbDoc stack: 49.1 ohm. "No R" is today's copper at the max corner; "off table" means the peak lies beyond the
table's last row. *Italic* = added by the D13-D15 pass.

| Net | R | Fab, no R, max | Fab, max: ball (Vmin) / die | Fab, typ: ball / die | PcbDoc, no R, max | PcbDoc, max: ball (Vmin) / die | PcbDoc, typ: ball / die |
|---|---|---|---|---|---|---|---|
| D0 | R119 | 33760 % | 0.5 % (-0.206 V) / 0.0 % | 0.0 % / 0.0 % | 73534 % | 1.3 % (-0.244 V) / 0.0 % | 0.0 % / 0.0 % |
| D1 | R120 | 15.0 % | 0.0 % (-0.091 V) / 0.0 % | 0.0 % / 0.0 % | 34.7 % | 0.0 % (-0.091 V) / 0.0 % | 0.0 % / 0.0 % |
| D2 | R121 | 17296 % | 0.0 % (-0.140 V) / 0.0 % | 0.0 % / 0.0 % | 44732 % | 0.0 % (-0.142 V) / 0.0 % | 0.0 % / 0.0 % |
| D3 | R122 | off table | 0.0 % (-0.200 V) / 0.0 % | 0.0 % / 0.0 % | off table | 1.0 % (-0.218 V) / 0.0 % | 0.0 % / 0.0 % |
| D4 | R123 | off table | 0.0 % (-0.137 V) / 0.0 % | 0.0 % / 0.0 % | off table | 0.0 % (-0.166 V) / 0.0 % | 0.0 % / 0.0 % |
| D5 | R124 | 65513 % | 0.8 % (-0.218 V) / 0.0 % | 0.0 % / 0.0 % | off table | 0.0 % (-0.191 V) / 0.0 % | 0.0 % / 0.0 % |
| D6 | R125 | 11271 % | 0.0 % (-0.186 V) / 0.0 % | 0.0 % / 0.0 % | 8718 % | 0.2 % (-0.203 V) / 0.0 % | 0.0 % / 0.0 % |
| D7 | R126 | 338.9 % | 0.0 % (-0.181 V) / 0.0 % | 0.0 % / 0.0 % | 1861 % | 0.7 % (-0.211 V) / 0.0 % | 0.0 % / 0.0 % |
| D8 | R127 | 4950 % | 0.0 % (-0.185 V) / 0.0 % | 0.0 % / 0.0 % | 1498 % | 1.4 % (-0.286 V) / 0.0 % | 0.9 % / 0.0 % |
| D9 | R128 | 7618 % | 0.0 % (-0.160 V) / 0.0 % | 0.0 % / 0.0 % | off table | 0.0 % (-0.168 V) / 0.0 % | 0.0 % / 0.0 % |
| D10 | R129 | 3059 % | 1.2 % (-0.272 V) / 0.0 % | 0.6 % / 0.0 % | 12844 % | 1.3 % (-0.292 V) / 0.0 % | 0.7 % / 0.0 % |
| D11 | R130 | 499.1 % | 0.0 % (-0.120 V) / 0.0 % | 0.0 % / 0.0 % | 257.0 % | 0.0 % (-0.132 V) / 0.0 % | 0.0 % / 0.0 % |
| D12 | R131 | 155.1 % | 0.0 % (-0.157 V) / 0.0 % | 0.0 % / 0.0 % | 1032 % | 0.0 % (-0.169 V) / 0.0 % | 0.0 % / 0.0 % |
| *D13* | *R132* | 93.8 % | 0.0 % (-0.166 V) / 0.0 % | 0.0 % / 0.0 % | 507.5 % | 0.0 % (-0.175 V) / 0.0 % | 0.0 % / 0.0 % |
| *D14* | *R133* | 62.9 % | 0.0 % (-0.072 V) / 0.0 % | 0.0 % / 0.0 % | 31239 % | 0.0 % (-0.164 V) / 0.0 % | 0.0 % / 0.0 % |
| *D15* | *R134* | 42.9 % | 0.0 % (-0.039 V) / 0.0 % | 0.0 % / 0.0 % | 368.0 % | 0.0 % (-0.052 V) / 0.0 % | 0.0 % / 0.0 % |

Max corner, fab stack, worst over the nets with a resistor:

| Case | Worst ball | Worst die | Ringback (ball) | Read 10-90 % at die | Write pin Vmin / Vmax |
|---|---|---|---|---|---|
| No R | off table (D3), 11 fails | 52.7 % | 0.535 V | 0.31-0.34 ns | -0.385 / 3.642 V |
| 22 ohm at pin, ideal (12 nets) | 17.1 % (D8) | 0 % | 0.139 V | 0.62-0.97 ns | -0.344 / 3.539 V |
| 22 ohm placed, 12 resistors | 0.85 % (D5), -0.218 V | 0 % | 0 | 0.60-0.81 ns | -0.358 / 3.548 V |
| 22 ohm placed, 13 resistors | 1.2 % (D10), -0.272 V | 0 % | 0 | 0.60-0.81 ns | -0.359 / 3.548 V |
| **22 ohm placed, 16 resistors (this plan)** | **1.2 % (D10), -0.272 V** | **0 %** | **0** | **0.56-0.81 ns** | **-0.359 / 3.548 V** |
| 15 ohm placed, 12 resistors | 6.6 % (D3) | 2.1 % | 0 | 0.41-0.65 ns | -0.373 / 3.570 V |
| 33 ohm placed, 12 resistors | 0 % | 0 % | 0.169 V (D7) | 0.72-1.35 ns | -0.307 / 3.520 V |

Whole bus, 16 resistors, all four stack and corner cases:

| Stack / corner | Worst ball | Worst die | Worst ball Vmin | Ringback | Write U3 pin Vmin / Vmax |
|---|---|---|---|---|---|
| fab typ | 0.55 % (D10) | 0 % | -0.213 V (D10) | 0 | -0.249 / 3.326 V |
| fab max | 1.18 % (D10) | 0 % | -0.272 V (D10) | 0 | -0.359 / 3.548 V |
| PcbDoc typ | 0.95 % (D8) | 0 % | -0.240 V (D8) | 0 | -0.267 / 3.338 V |
| PcbDoc max | 1.35 % (D8) | 0 % | -0.292 V (D10) | 0 | -0.367 / 3.554 V |

Value check on the PcbDoc stack, worst over D8, D10, D0, D3, D13 and D14 at both corners (`d13/sim/sim_final.md`
§4):

| R | Worst ball | Worst die | Worst ball Vmin | Ringback (ball) | Die t10-90 | Read delay | Write delay |
|---|---|---|---|---|---|---|---|
| 15 ohm | 8.68 % | 3.19 % | -0.435 V | 0 | 0.41-0.58 ns | +0.024..+0.081 ns | +0.063..+0.142 ns |
| 22 ohm | 1.35 % | 0 % | -0.292 V | 0 | 0.56-0.77 ns | +0.034..+0.097 ns | +0.091..+0.183 ns |
| 33 ohm | 0 % | 0 % | -0.143 V | 0.025 V (D8) | 0.69-0.96 ns | +0.050..+0.126 ns | +0.137..+0.242 ns |

Supporting results:
- With the R at the pin and the same 0201 model, the worst is 2.07 % (D5, max) and 7.71 % (D8, typ). The planned
  positions are at least as good as the pin. R133 and R134 at the U1 end agree with the earlier sweeps: the
  position along the route barely matters at these edges.
- Package sensitivity at 22 ohm: ideal R 1.50 %, light model 0.51 %, parts model 0.85 %.
- No ringback into 0.8-2.0 V at any node, corner, direction or stack.
- Writes pass the SDRAM's -1.0/4.6 V limits on all 16 nets. Worst at the U3 pin is -0.367 / 3.554 V (D3, PcbDoc,
  max); at the U3 die -0.475 / 3.563 V.
- Delay cost against today's copper, all 16 nets, both stacks: reads +0.032..+0.097 ns at the U1 die, writes
  +0.091..+0.183 ns at the U3 die. D13 is the largest (read +0.083..+0.097, write +0.146..+0.183 ns), because its
  route is about 6.6 mm longer. D14: read +0.044..+0.062, write +0.091..+0.141 ns. D15: read +0.048..+0.065, write
  +0.098..+0.147 ns. With the R, the receiving die settles past VIH/VIL about 0.1-0.17 ns later.
- **All 16 nets pass at the ball and at the die on both stacks and both corners.** Without any R, 15 of 16 nets fail
  at the ball on the PcbDoc stack at the max corner (only D1 passes, 34.7 %).

