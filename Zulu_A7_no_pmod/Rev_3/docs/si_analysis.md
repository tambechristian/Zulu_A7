# Signal integrity, Zulu_a7_no_pmod Rev 2 (Altium SI, 2026-11-12)

## Status
Two passes. (1) Altium SI: models assigned, screening on all nets; Altium drives every model to 5.000 V (see Limits),
so it is a screening pass only. (2) **Independent ngspice + IBIS cross-check of the SDRAM bus at 3.3 V** (section
below): the result to use for the SDRAM bus.

## Models
| Part | Source | Notes |
|---|---|---|
| U1 XC7A35T-2CPG236I | Vivado 2026.1 `write_ibis` on the Rev 2 pinout (`si/vivado/`) | IBIS 4.2, 238 pins, per-ball IOSTANDARD/DRIVE/SLEW from `zulu_a7_no_pmod.xdc` (= `vivado/zulu_a7_pins.xdc` minus the 8 JA ports; all other user-I/O balls match the board). SDRAM = LVCMOS33 8 mA SLOW, SDRAM_CLK 8 mA FAST. Converter: 0 errors. |
| U3 AS4C32M16SB-7TCN | Alliance Memory official IBIS 5.0 | Altium's checker rejects the vendor `[File name]` line (upper case, differs from the file name); `si/ibis/as4c32m16sb/altium/as4c32m16sb-7tcn.ibs` is a copy with only that line changed. DQ selector = DQ_100 % (full drive). |
| U10 93LC46B | Microchip official IBIS 3.2 (3.3 V set) | fine |
| U2 FT2232HL | none: FTDI publishes no IBIS for any device | generic Altium **LVC** (24 mA class, stronger than the FT2232H's default 4 mA, so pessimistic) |
| U4 W25Q128JVSIQ | Winbond publishes one, but behind a login | generic **LVC** until the user downloads it (needs their Winbond sign-in) |
| Q1 ECS-3225SMV | none published | not modelled |

Vendor files live in `si/ibis/` (git-ignored: vendor licences, public repo).

## Board changes made for SI
- Production board: the six 'Schematic Supply Nets' rules had 0 V; set GND/GNDADC 0, VCC3V3 3.3, VCC1V8 1.8,
  VCCADC 1.8, VCC1V0 1.0 (`tools/NoPmod_SupplyV.pas`). Sheets 3/4/5: SI models added to U3, U10, U1.
- **SI copy** `si/altium_si/` (separate project; production PcbDoc untouched): L2-GND and L5-VCC3V3 are signal layers
  carrying whole-layer pours (no tracks), and Altium SI only uses Plane-type layers as references. On the production
  board it warned "No plane layers defined - plane layers assumed" and modelled SDRAM-CLK at **222-247 ohm**. In the
  copy the two pours were removed (`SI_ClearPlaneLayers.pas`) and the layers set to Plane (GND / VCC3V3) in the Layer
  Stack Manager: SDRAM-CLK is now **49.5-72.7 ohm (avg 56)**, which is the expected range.

## Results (SI copy, `si/results/screening_planes.tsv`)
- 141 nets screened, **all pass**; 17 not analysed (power/feedback nets, TMS, LED0_B, N$BTN: no modelled driver).
- SDRAM bus (U1 to U3): overshoot/undershoot 9-43 mV on A/BA/control/CLK, D0 worst at 111 mV.
- Highest anywhere: UART_FT_RXD / SD-DAT2 / FLASH-D02 268 mV, FPGA-TCK 244 mV, CHAN21 231 mV, TDI 191 mV.
- A9 reflection waveform at U3-34: clean monotonic edges, no visible ringing (rise ~3 ns, SLOW 8 mA).
- The first run on the production board (no planes) failed UART_FT_*, FT-PWREN#, EE-CLK, TDO, FLASH-D01, D0 and the
  buck-boost switch nodes; all of these pass once the planes are real, so those failures were the missing reference.

## Limits / open items
1. **5 V top value.** Every driver (Vivado IBIS, generic LVC alike) settles at 5.000 V in both copies, whatever the
   supply rules say (also with the rules detached from the schematic). The same behaviour is reported on
   EDABoard ("Altium Signal Integrity - defaults to 5V"). The swing is 1.5x too large, so the ringing figures are
   pessimistic in amplitude, but edge rates and timing are not trustworthy.
2. **Identical results:** 29 unrelated nets (A9, RAS#, WE#, CHAN0, BTN, LED1...) report exactly 40.72/72.60/67.50/127.6
   mV, and 3 nets 139.9/81.33/267.8/147.4 mV. Looks like a screening default, not a per-net result; A9's real
   reflection waveform is clean. Verify these by reflection, not screening.
3. **D0 reflection** stops with "Unexpected error occurred in simulation". It is the only tried net whose receiver is the
   SDRAM DQ model (IBIS 5.0 Model Selector, '%' in model names); SDRAM-CLK and A9 (SDRAM Input model) simulate fine.
4. **Copper loops** reported on the production board: NODE_P0 at (45.29, 2.18) and FLASH-D03 at (51.13, 20.02) mm
   ("Loop found, cannot analyse net"). Not a DRC error; worth a look on the board.
5. FT2232H and flash use generic models; Q1 none.

## Files
`si/vivado/` (U1 IBIS + Tcl), `si/ibis/` (vendor models, ignored), `si/altium_si/` (SI-only project + scripts),
`si/results/` (screening tables, failure report from the no-plane run).

## Independent SDRAM-bus cross-check (ngspice + IBIS, 2026-11-12) -- `si/spice/`
Built because Altium drives everything to 5 V. KiCad's `ngspice.dll` driven from Python (`ngs.py`).
- **Lines:** `fieldsolve.py`, 2D finite-difference field solver (checked against Cohn and Hammerstad-Jensen to
  0.3 %, and independently re-derived to 0.1 % by a reviewer's finite-volume solver). Default stack = the construction
  PCBWay builds (fab notes: 3313 0.1015 / 1080 0.0713 / core 1.065, Dk 4.27 / 3.99 / 4.5): **L3/L4 0.125 mm = 43.4
  ohm, 6.77 ps/mm** (PCBWay quoted 43 ohm); Top 0.0762 mm 63.3 ohm, Bottom 0.125 mm 53.0 ohm. The PcbDoc's own stack
  gives 49.1 ohm on L3/L4 and is run as a second case.
- **Buffers:** `ibis2spice.py`, standard IBIS behavioural model (I-V tables + Ku/Kd from the two V-T waveforms per
  edge, C_comp, per-ball package from U1's [Define Package Model]). Golden test (`test_golden.py`): all 36 vendor
  waveforms reproduced within 20 mV. Both parts on one VCC3V3 rail per corner (3.3 V typ, 3.465 V max).
- **Board:** `bus_sim.py` turns every track of the 39 nets into T-lines / pi sections, every via into a ladder with
  field-solved capacitance (stubs included), L2/L5 ideal planes. Writes: U1 drives (LVCMOS33 8 mA SLOW, CLK 8 mA FAST)
  into U3; reads: U3 DQ (full drive) into U1. Edges at 133 MHz data rate.
- **Verification:** an independent 5-agent review (field solver, IBIS, netlist, physics, judge) found 5 real defects
  (truncated runs accepted, wrong stack, generic U1 package, per-model rails, via C 1.45x); all fixed before the final
  run. 220 cases (39 writes + 16 reads, typ/max, fab/PcbDoc stack), all complete to 32 ns, no ringback into the
  0.8-2.0 V band anywhere.

### Results (fab stack)
| Direction | Corner | Overshoot | Undershoot | Edge 10-90 % at receiver |
|---|---|---|---|---|
| Write (U1 -> SDRAM inputs) | typ | +0.06 .. +0.16 V | 0.27 .. 0.43 V | 0.9-1.5 ns |
| Write | max | +0.12 .. +0.23 V | 0.43 .. 0.62 V | 0.6-1.2 ns |
| Read (SDRAM DQ -> FPGA) | typ | +0.28 .. +0.44 V | 0.38 .. 0.51 V | 0.3 ns |
| Read | max | +0.36 .. +0.48 V | 0.41 .. 0.50 V | 0.3 ns |
(measured at the receiver die; SDRAM-CLK typ +0.10 / 0.27 V, max +0.12 / 0.62 V)

- **Writes pass with wide margin** against the AS4C32M16SB B-die absolute maximum (VIN -1.0 .. 4.6 V, pulse <= 3 ns):
  worst 3.69 V / -0.62 V. DRIVE 8 in the XDC is confirmed adequate.
- **Reads, at the FPGA die: pass** DS181 v1.27.1 Table 4 (AC overshoot/undershoot % of UI, time beyond 0.20 V):
  worst 69 % of the allowance (D10, max corner, UI 7.5 ns). This answers the open item in sdram_bus_widths.md.
- **Reads, at the FPGA ball: fail** without series resistance: the SDRAM's full-drive 0.3 ns edges ring to -0.85 ..
  -1.05 V at the ball for about 1.1-1.3 ns (12 of 16 data lines at the max corner). The package L/C filters this to
  -0.5 V at the die. AMD's DS181/XCN14014/AR 61125 do not say whether Table 4 applies at the die or the ball, so this
  is an open risk, not a proven violation.
- The SDRAM has **no drive-strength setting** (no extended mode register in the B-die datasheet), so the DQ_72/39 %
  IBIS variants are not usable. **Series resistors at the SDRAM DQ pins** fix the ball case (`series_study.py`):
  15 ohm -> ball worst -0.42 V, 30 % of budget; 22 ohm -> -0.35 V, 17 %; 33 ohm -> -0.31 V, 15 %. Read edges slow to
  0.4-1.3 ns; writes barely change. This is a schematic + layout change (16 resistors, U3 is on the Bottom).
- PcbDoc-stack runs (49 ohm) give the same picture (die pass <= 79 %, ball fail).

### Remaining uncertainty
Via inductance (isolated-rod formula, about +-10-15 %), the vendor DQ_100 % model (its V-T tables disagree with its own
C_comp: Ku/Kd leave 0..1), plane-gap crossings not modelled (L2/L5 ideal), no crosstalk, no SSN. Dk values are
library values, not PCBWay's measured ones.

Sources: DS181 v1.27.1 (2024-07-03) Table 1 and Table 4; AS4C32M16SB datasheet Rev 1.2 (March 2020) Table 12 and
notes; XCN14014 (undershoot threshold GND - 0.20 V).
