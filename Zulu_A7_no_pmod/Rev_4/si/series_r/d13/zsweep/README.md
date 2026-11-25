# D13 inner-layer impedance sweep (2026-11-13)

`bus_sim_final.py` here is a copy of `d13/sim/bus_sim_final.py` (md5 3a9ba636) with one added block (marked ZSWEEP):
stack `fabZ<z>` keeps PCBWay's geometry everywhere (outer layers, via heights) and scales the L3/L4 line impedance so
that a 0.125 mm L3 track is `<z>` ohm, delay per mm unchanged; `fabZ<z>T<ps>` also sets the inner delay. Read, U3
drives, U1 receives; % = DS181 Table 4 budget used at the U1 ball (100 % = limit). Controls: `fabZ43.43` reproduces
`fab` exactly (93.8 %) and `pcbdoc` reproduces the 16-R study's base run (507.5 %).

Runs: `run_base.log`, `run_fine.log`, `run_fine2.log` (D13 without R), `run_r132.log`, `run_r132low.log` (D13 with
R132, plan `dq_series_r_plan.json` md5 7c2b8ae6). Raw: `zsweep_raw_*.json`, waves in `wave_z/`.

| L3/L4 Z0 (ohm) | no R, max | no R, typ | ball Vmin, no R max (V) | with R132, max | ball Vmin, R132 max (V) |
|---|---|---|---|---|---|
| 39.1 (-10 %) | **153.0 % FAIL** | | -0.548 | 0.0 % | -0.189 |
| 41.0 | **249.8 % FAIL** | | -0.581 | 0.0 % | -0.174 |
| 42.0 | **184.9 % FAIL** | 7.5 % | -0.564 | | |
| 42.5 | **100.6 % FAIL** | 7.7 % | -0.548 | | |
| 43.0 | 94.9 % | 8.3 % | -0.529 | 0.0 % | -0.167 |
| 43.43 (fab nominal) | 93.8 % | 8.6 % | -0.529 | 0.0 % | -0.166 |
| 44 | 88.8 % | 8.7 % | -0.536 | 0.0 % | -0.167 |
| 45 | 69.7 % | 8.1 % | -0.548 | 0.0 % | -0.168 |
| 45.25 | 61.7 % | | -0.550 | | |
| 45.5 | **131.0 % FAIL** | | -0.552 | | |
| 45.75 | **117.2 % FAIL** | | -0.554 | | |
| 46 | **112.5 % FAIL** | 19.7 % | -0.556 | 0.0 % | -0.171 |
| 47 | **112.3 % FAIL** | 20.9 % | -0.562 | 0.0 % | -0.175 |
| 47.8 (+10 %) | **123.2 % FAIL** | | -0.563 | | |
| 48 | **119.8 % FAIL** | 51.8 % | -0.564 | 0.0 % | -0.178 |
| 49 | **127.5 % FAIL** | 78.3 % | -0.585 | 0.0 % | -0.173 |
| 49.08 | **127.7 % FAIL** | 79.3 % | -0.586 | 0.0 % | -0.173 |
| 49.08, PcbDoc inner delay 7.133 ps/mm | 54.4 % | 20.8 % | -0.511 | 0.0 % | -0.185 |
| PcbDoc stack (all geometry) | **507.5 % FAIL** | 76.2 % | -0.618 | 0.0 % | -0.175 |

Findings:
- Without a resistor, D13 passes at the max corner only for L3/L4 Z0 of about 42.6-45.3 ohm, i.e. -2 % / +4 % around
  PCBWay's nominal 43.4 ohm. A normal +-10 % impedance tolerance (39.1-47.8 ohm) fails over most of its range, on
  both sides. The ball peak sits at -0.53..-0.59 V, right on DS181 Table 4's -0.55 V row, so a few mV decide pass or
  fail and the result is not monotonic in Z0 (it also moves with the line delay and the via geometry: compare the two
  49.08 rows and the PcbDoc row).
- With R132 (22 ohm), D13 uses 0.0 % at every point from 39.1 to 49.1 ohm and on the PcbDoc stack, with the ball
  minimum at -0.166..-0.189 V (about 0.36 V from the -0.55 V row). Writes stay within -0.29 / 3.53 V at the U3 pin.
- The die budget without R stays at 20-29 % (max corner) throughout; the failures are at the ball only.
