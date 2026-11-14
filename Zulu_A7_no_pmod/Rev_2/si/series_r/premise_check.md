# Series R on the SDRAM DQ nets: premise check (planning only, 2026-11-13)

Board: Zulu_a7_no_pmod Rev 2. Question: before 16 resistors go on D0-D15 at U3 (AS4C32M16SB-7TCN, Bottom), is
there a fix that needs no board change? Does the R hurt read timing? Is 22 ohm the right value? Do CLK, address
or control nets need one too?

Nothing in the PcbDoc, SchDoc, PcbLib or si/spice was changed. Every new file is in `si/series_r/`.

## Verdict

1. **No fix without a board change exists.** IN_TERM is not allowed on LVCMOS33. PULLDOWN and KEEPER are 10-50
   kohm, too weak to matter. The SDRAM has no drive-strength control. U1's input clamp is already what holds the
   die at about -0.5 V; the -1 V at the ball is package L ringing in front of that clamped die. Running the bus
   slower does not help either, because the ball peak is beyond the last row of DS181 Table 4 (0 % of UI
   allowed at any UI). The one option that changes no copper is to **accept the risk**: argue that Table 4
   applies at the die, where the bus passes at 69 %. AMD does not say whether it applies at the die or the ball.
2. **Read timing: the premise overstated the cost.** The 22 ohm R moves the 1.65 V crossing at U1's die by only
   **+0.04-0.05 ns**, not 0.3-0.5 ns. It shrinks the data-valid window by **<= 0.006 ns**. The 10-90 % time grows
   because the tail of the edge slows, but the LVCMOS33 threshold is crossed early in the edge. No SDRAM
   controller HDL exists for this board yet. With no clock feedback on the board, any 133 MHz CL3 controller
   needs a phase-shifted capture clock (MMCM) or IDELAY, with or without the R.
3. **22 ohm is a good choice.** The classic formula "Z0 - Rout" gives **~2-9 ohm**, but it does not apply here:
   the line is short (60-137 ps against a 0.3 ns edge), so the ringing is a lumped package-L/C resonance.
   Measured: 6 ohm fails 4/16 at the ball and 10 ohm fails 1/16 (max corner). 15 ohm passes at 30 % of the
   budget, 22 ohm at 17 %, 33 ohm at 15 % and 47 ohm at 13 %. **22 ohm is where the curve flattens:** it recovers
   about 90 % of the ball undershoot that 47 ohm recovers (-0.98 -> -0.35 V against -0.29 V), at +0.05 ns. 15 ohm is the lowest value with margin; 33 ohm buys almost nothing more.
4. **No R is needed on SDRAM-CLK, address or control.** Writes pass with wide margin against the SDRAM absolute
   maximum (worst -0.62 V / +3.69 V against -1.0 / 4.6 V). An R on SDRAM-CLK would slow its edge (0.63-0.92 ns
   now) toward the 1 ns point where the datasheet adds a tAC/tOH penalty (note 9).

## 1. Fixes that need no board change

| Lever | Source | Finding |
|---|---|---|
| IN_TERM / UNTUNED_SPLIT_40/50/60 | UG471 v1.10 (May 2018) p.33, "Uncalibrated Split Termination in High-Range I/O Banks (IN_TERM)", **Table 1-7** | Supported only for HSTL_I/II(_18), SSTL18_I/II, SSTL15(_R), SSTL135(_R) and their DIFF_ forms. **LVCMOS33/LVTTL are not in the table.** Vivado will not accept IN_TERM on these ports. The bank runs at VCCO 3.3 V for the SDRAM (and D14/D15 share bank 16 with the CHAN pins), so no SSTL/HSTL standard is possible. Even if it were allowed, a 50 ohm Thevenin to VCCO/2 at 3.3 V draws about 33 mA DC per pin, and only while the pin is an input. |
| PULLDOWN / PULLUP / KEEPER | UG471 p.49; DS181 v1.27.1 **Table 3** IRPU / IRPD | Weak: pad pull-down at VIN = 3.3 V is 68-330 uA, which is about 10-50 kohm. The undershoot is a ~1 ns event carrying tens of mA, so this changes nothing. |
| U1 input clamp | U1 IBIS `si/vivado/zulu_a7_no_pmod_u1.ibs`, model LVCMOS33_S_8_HR, [GND Clamp] (`rout.py` -> `rout.txt`) | Clamp current at the die: -0.4 V 0.85 mA, -0.5 V 6.5 mA typ (11.3 mA max corner), -0.6 V 17 mA. **The clamp is what holds the die at -0.50 V.** The ball goes to -0.98 V because U1's package (about 4.6-6.4 nH per ball, IBIS [Define Package Model]) rings between the line and the clamped die. Nothing in the clamp can be configured. From the saved die waveforms (`clamp_writes.py`, R = 0, max corner): **peak clamp current 11.7 mA on the worst line**, which is above DS181 **Table 2 IIN = 10 mA** ("maximum current through any pin ... when forward biasing the clamp diode"). That limit reads as a steady-state condition and this pulse lasts about 1 ns, so it is a flag, not a proven violation. Sum of the 16 peaks: 127 mA, under the 200 mA per bank of Table 4 note 1 (and the lines are split over banks 34, 35 and 16). **With R >= 15 ohm the clamp current is zero** (< 0.05 mA). |
| SDRAM drive strength | AS4C32M16SB B-die datasheet Rev 1.2 (March 2020), local `Datasheet/AllianceMemory_512M_SDRAM_Bdie_...Rev1.2_March2020.pdf`, **Table 5 Mode Register Bitmap** p.14 | **Verified: there is none.** The only register is the MRS. A0-A2 set burst length, A3 burst type, A4-A6 CAS latency, A7-A8 test mode ("Vendor Use Only"), A9 write burst; BA1/A10-A12 are RFU and BA0 must be 0. There is no extended mode register and no "drive" text anywhere in the datasheet. The vendor IBIS does carry DQ_72 % / DQ_39 % / DQ_11 % models, but nothing in the part can select them. |
| Lower clock rate | DS181 Table 4 | Does not help. At the ball the R = 0 peak is -0.98 V, beyond the last tabulated row (-0.95 V, 0.02 % of UI). Changing the UI does not move the peak. |
| Accept the die-level pass | DS181 Table 4 notes; XCN14014 | Reads pass at the die at 69 % of the budget. Neither DS181 v1.27.1, XCN14014 nor a web search says whether Table 4 applies at the die or the ball. This was also unresolved in docs/si_analysis.md. **It is the only way to avoid a board change, and it is a risk decision for the user.** |

## 2. Read timing

**No SDRAM controller HDL exists for this board.** I searched `C:/Users/tambe/Documents/Electronics/Zulu_A7` for
*.vhd, *.v, *.sv, *.xpr and SdramCntl, leaving out archives/. The only HDL files are `vivado/zulu_a7_top.v` and
`si/vivado/zulu_a7_no_pmod_top.v`. Both are pin-exercising stubs (shift registers) for `write_ibis`, with no
controller. XuLA2's XESS SdramCntl captured with an SDRAM clock fed back into the FPGA. **This board has no such
feedback:** in the board extract SDRAM-CLK is a two-pin net, U1 M1 to U3 pad 38. So the capture scheme is still
open, and it must be designed for the following.

Method (`timing.py` -> `timing.txt`, `timing.json`):
- tAC and tOH are specified at the SDRAM pin into the AC test load (datasheet Table 17 / Figure 18.2: 50 ohm,
  30 pF, measured at 1.4 V; the IBIS file says the same with Rref 50, Vref 1.4, Cref 30 pF, Vmeas 1.4). The
  script simulated the same DQ_100% IBIS driver and package as bus_sim.py into that load and measured the 1.4 V
  crossing.
- Board delay was measured from the saved read waveforms, at U1's die at **1.65 V**. That is DS181 **Table 19**
  VMEAS for LVCMOS33, the level TIOPI is specified at.
- Flight-time-compensated delay = board crossing - reference-load crossing. It covers 16 nets, the edges at
  8.5/16/23.5 ns, and both the first and the last crossing.

| R | corner | compensated delay, rise | fall | spread of all 16 nets x 3 edges | shift vs R = 0 | window loss vs R = 0 |
|---|---|---|---|---|---|---|
| 0 | typ / max | -0.03..+0.08 / -0.02..+0.09 ns | -0.16..-0.04 ns | 0.242 / 0.255 ns | - | - |
| 15 | typ / max | -0.01..+0.12 | -0.13..-0.01 | 0.246 / 0.255 | +0.03 ns | <= 0.004 ns |
| **22** | typ / max | +0.01..+0.13 | -0.12..+0.00 | 0.248 / 0.255 | **+0.04..+0.05 ns** | **<= 0.006 ns** |
| 33 | typ / max | +0.03..+0.16 | -0.10..+0.03 | 0.252 / 0.255 | +0.06..+0.07 | <= 0.010 |

The compensated delay is near zero or negative because the board load (about 10 pF) is lighter than the 30 pF
test load. The datasheet's tAC already assumes a slower load than the board presents, even with 22 ohm.
Sanity check: 22 ohm in series with the test load itself adds 0.07-0.17 ns.

Budget at 133 MHz, CL3, -7 part, -2 FPGA (sources: datasheet AC table p.22; DS181 v1.27.1 Tables 17 and 21):
- Valid window at U3's pin: tCK + tOH - tAC = 7.5 + 2.5 - 5.4 = **4.6 ns** (4.1 ns at 143 MHz).
- SDRAM-CLK at U3 has a 0.63-0.92 ns edge (results_all.json), which is under 1 ns, so note 9 adds no tAC/tOH
  adjustment.
- Minus the board DQ spread, 0.255 ns (R = 0 and R = 22 alike).
- Minus the IOB flip-flop setup/hold, TIDOCK/TIOCKD for -2: 0.01 / 0.29 ns.
- That leaves **4.05 ns** for the FPGA's own variation: the clock-out TIOOP plus the input TIOPI, fast against
  slow, plus MMCM jitter and the skew between banks. Data spans banks 34 (D0-D7), 35 (D8-D13, plus SDRAM_CLK) and
  16 (D14-D15).
- DS181 gives only the maximum values: TIOOP for LVCMOS33_F8 is 2.87 ns and TIOPI for LVCMOS33 is 1.34 ns (-2).
  **ASSUMED:** a fast corner at about 50 % of those, which is about 2.1 ns of variation. That leaves about 1.9 ns
  at 133 MHz and 1.4 ns at 143 MHz, before about 0.3-0.5 ns of jitter and skew (also assumed). Vivado's min/max
  analysis of a real controller replaces these guesses.
- **Direct capture on the next edge fails with or without the R.** Worst arrival = 2.87 (TIOOP) + 0.13 (CLK
  flight) + 5.4 (tAC) + 0.135 + 1.34 (TIOPI) + 0.01 (setup) = **9.88 ns** with 22 ohm, against **9.84 ns** at
  R = 0, and tCK is 7.5 ns. The controller needs an MMCM capture phase of about +2.4..+4 ns, or IDELAY. The 22
  ohm moves the centre of that phase by 0.04 ns.
- Correction to `Zulu_Altium_VS_Code/docs/sdram_bus_widths.md`: its "tAC 5.4 + TD 0.22 + TIOPI 1.41 = 7.03 ns"
  leaves out the clock-out delay of the forwarded SDRAM_CLK.
- Writes: the datasheet's note 10 adds [(tr+tf)/2 - 1] ns to tIS/tIH when input edges are slower than 1 ns. The
  write edges are already 1.1-1.5 ns at R = 0, and the R changes them by under 0.03 ns, so that adjustment
  applies with or without the R.

## 3. Value choice

The SDRAM driver's output resistance, from the vendor IBIS DQ_100% I-V tables (`rout.py` -> `rout.txt`), is
almost linear:

| corner | pulldown, 0-0.46 V secant / V/I at Vcc/2 | pullup, same | effective R launching into 43.4 ohm, rise / fall |
|---|---|---|---|
| typ (3.3 V) | 35.1 / 35.8 ohm | 37.0 / 38.1 ohm | 37.9 / 35.7 ohm |
| min (slow, 3.0 V) | 37.0 / 38.3 | 39.5 / 41.4 | 41.3 / 38.1 |
| max (fast, 3.6 V) | 34.0 / 34.5 | 35.6 / 36.3 | 36.2 / 34.5 |

The U3 package adds 0.5-1.05 ohm (IBIS [Pin]). On the fab-stack L3/L4 line (43.4 ohm, fieldsolve.py)
**Z0 - Rout is about 2-9 ohm**; on the PcbDoc stack (49.1 ohm) it is about 8-15 ohm. The DQ routes also run on
Bottom (53 ohm) and Top (63 ohm). That rule assumes a line long compared with the edge. Here the flight is
60-137 ps (results_all.json: D13 8.97 mm up to D6 20.74 mm) against a 0.3 ns edge. The overshoot is the
resonance of the U3 package L (3.6-7.1 nH), the line, U1's package (4.6-6.4 nH) and the C_comp at both ends
(4.7 and 5.2 pF), so it needs more damping than a matched source gives.

Read sweep, D0-D15, fab stack (`summary.py` -> `summary.txt`). R = 0/15/22/33 come from the existing waves in
si/spice/wave. R = 6/10/47 are new runs by `sweep.py`, which uses bus_sim.py unchanged with its output redirected
to series_r/wave. Re-running R = 22 through the wrapper reproduced results_r22.json to 0.0 V on all 32 cases.

| R ohm | ball Vmin typ / max | ball budget, max corner | ball fails, max corner | die Vmin, max corner | delay at 1.65 V vs R = 0 |
|---|---|---|---|---|---|
| 0 | -0.90 / -0.98 V | >> 100 % | 12/16 | -0.50 V | 0 |
| 6 (about Z0 - Rout) | -0.66 / -0.80 | 11843 % | 4/16 | -0.40 | +0.01 ns |
| 10 | -0.50 / -0.63 | 404 % | 1/16 | -0.29 | +0.02 |
| 15 | -0.32 / -0.42 | 30 % | 0 | -0.20 | +0.03 |
| **22** | -0.25 / -0.35 | **17 %** | 0 | -0.13 | **+0.04..+0.05** |
| 33 | -0.22 / -0.31 | 15 % | 0 | -0.11 | +0.06..+0.09 |
| 47 | -0.20 / -0.29 | 13 % | 0 | -0.09 | +0.09..+0.14 |

`python series_study.py` (si/spice) reproduces the earlier table exactly: `series_r/series_study_repro.txt`. It
reports 22 ohm read edges as 0.62-0.97 ns 10-90 %, the mean per net. summary.py's 0.48-1.22 ns is the min and max
over single edges.

**Recommendation: 22 ohm (E12/E24).** The two smaller values that look matched fail at the ball. 15 ohm is the
floor with margin, about 70 % of the budget left. 22 ohm leaves 83 %, which covers model error: the
via-inductance uncertainty of +-10-15 % and the vendor model's Ku/Kd problem. Above 22 ohm there is almost no
further gain.

Assumed, not modelled: the R is ideal and sits exactly at U3's pin (bus_sim's `ZULU_RSER`). The real part will sit
a few mm away, on the Bottom stub or at the via. Body parasitics and placement distance are not part of this
check; `parasitic_sim.py` in this folder belongs to another workflow step.

## 4. CLK, address and control

Write direction, R = 0, fab stack, from `si/spice/results_all.json` plus waves (`clamp_writes.py` ->
`clamp_writes.txt`). The limit is the AS4C32M16SB absolute maximum, 4.6 V / -1.0 V for pulses up to 3 ns
(datasheet note 2, p.22):

| group | corner | die min..max | pin overshoot / undershoot | 10-90 % | ringback into 0.8-2.0 V |
|---|---|---|---|---|---|
| D0-D15 | max | -0.55..3.69 V | +0.18 / -0.38 V | 1.10-1.19 ns | 0 |
| A0-A12, BS0/1 | max | -0.61..3.69 | +0.22 / -0.46 | 1.12-1.24 | 0 |
| control (CAS#, RAS#, WE#, CKE, CS#, LDQM, UDQM) | max | -0.62..3.69 | +0.17 / -0.46 | 1.12-1.15 | 0 |
| SDRAM-CLK (8 mA FAST) | max | -0.62..3.59 | +0.11 / -0.59 | 0.63 | 0 |

The worst margin is 0.38 V to -1.0 V, and 0.9 V to 4.6 V. This agrees with docs/si_analysis.md ("Writes pass
with wide margin ... worst 3.69 V / -0.62 V"). **No R is needed on these nets.** On SDRAM-CLK an R would also cost
tAC margin, because note 9 adds (tR/2 - 0.5) ns once the clock edge exceeds 1 ns. With the D-net R at U3, writes
pass through it too. They improve slightly: at 22 ohm the max-corner die reaches -0.43 / 3.56 V, against
-0.55 / 3.69 V at R = 0 (series_study).

## Limits of this check
- Every waveform comes from `tools/route/model.json`, saved 2026-11-12 03:15, before the last JTAG/C78 edits.
  **Assumed:** the D-net copper did not change in those edits. A fresh PcbDoc extract would confirm it.
- The IBIS min (slow) corner was not simulated; it rings less. L2/L5 are ideal planes, and there is no
  crosstalk or SSN.
- TIOPI may depend on the input edge rate, and DS181 does not state the edge used for Table 17. The 22 ohm edges
  (0.5-1.2 ns) are slower than R = 0. Only the analog crossing was measured, not any edge-rate effect inside
  the input buffer.
- Whether DS181 Table 4 applies at the die or the ball is unresolved. Only AMD can settle it (a support case).

## Files (all in si/series_r/)
`rout.py`/`rout.txt` (driver Rout, U1 clamp tables) - `timing.py`/`timing.txt`/`timing.json` (reference-load
and flight-compensated delays) - `clamp_writes.py`/`clamp_writes.txt` (die clamp current, write margins) -
`sweep.py`, `sweep_results.json`, `wave/` (R = 6/10/22/47 reads) - `summary.py`/`summary.txt` (the sweep table) -
`series_study_repro.txt` - `txt/` (pdftotext of UG471 v1.10, DS181 v1.27.1, the AS4C32M16SB Rev 1.2 datasheet, from
`Datasheet/`).

Sources: UG471 v1.10 (8 May 2018) Table 1-7 and p.49; DS181 v1.27.1 (3 July 2024) Tables 2, 3, 4, 17, 19, 21;
XCN14014; Alliance Memory AS4C32M16SB B-die Rev 1.2 (March 2020) Tables 5 and 17, the AC characteristics and notes
2, 9 and 10; Alliance Memory AS4C32M16SB-7TCN IBIS; U1 IBIS from Vivado write_ibis. Online copy of DS181:
https://cdn.sparkfun.com/assets/0/f/b/6/2/Artix_7_Data_Sheet.pdf (the local PDF was used for every number).
