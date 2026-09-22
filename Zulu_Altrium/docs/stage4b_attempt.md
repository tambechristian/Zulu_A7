# Stage 4b attempt: the signal nets hit a capacity wall (2026-09-22)

**Status: NOT PLACED.** The plan is kept in the session scratchpad (`stage4b/s4b_final/plan.json`, md5
d18e1aea23633d669dcfec979d7ca28d; `gen.py --check` reproduces it). The shared helpers it used are
committed under `tools/stage4b/`.

## What the attempt did

Two workflow runs (the first cut off by a session end after the XADC and USB regions), 12 + 5
agents: an XADC region first (the AIN16_N via move you approved, the last two GND ties, NODE_P0/P1,
the two analog header lines), the USB pair, a u2west fix for FT-REF/U2-5, then six regions in
parallel, a merge, two reviews and a judge.

| | Result |
|---|---|
| Connections closed | **92 of 140** |
| Signal nets in one island | 131 of 175 (44 split) |
| Copper | 213 vias, 1377 tracks (1351 at 0.0762 mm), removals only the approved 1 via + 6 tracks |
| `route_emit` | clean, 67/67 modelled nets |
| `route_reach` on the connections still open | **0 / 35** — the plan walls off every one |
| `route_foreclosure` | 10 pads sealed, all on open nets |
| `gnd_check` | 200/201 (U2-5 open) |
| GND stitching sites | whole board 53.7 %, U1 surround **5.6 %**, north band **5.3 %** |
| Reviews | SI/analog 3/10, manufacturing 2/10 |

Closed: xadc 6/6 (NODE_P1 closed copper-only by re-routing AIN16_P's local run — no placement
change needed), USB pair 2/2 (0.15 / 0.125 gap, no vias), JTAG 29/30, and parts of the rest.

**Still open (47 connections, 43 nets):** FLASH-CS# and FLASH-D00…D03 (the FPGA cannot boot from
flash), FT-REF (the USB PHY does not bias), DONE, FT-PWREN#, UART_FT_RXD, JA1/7/8/9/10, BTN, the five
LED lines, SD-CLK/CMD/DAT0/DAT1, CHAN5–13, CHAN15 and CHAN19–28. On the final copper each returns
NO PATH, after four guarded rip-up passes.

## Why it should not be placed

It would lock the board: with this copper in place the 35 remaining connections of untouched nets
have no path at all, and the planes around U1 and in the north band keep almost no stitching sites
(126-plus of the new vias change reference plane with no GND via within 1 mm).

## Where the room went

- **The JTAG loop.** U2 → JP3/JP4 → the R4 buffer → U1's west balls crosses the board twice: 391 mm of
  inner-layer copper and 75 vias (TDO 105.5 mm / 7 vias, PROG# 80.4 / 9, TCK 75.2 / 11, TMS 75.2 / 5).
- **VCC3V3 as routed trunks.** Stage 3 carries the 3.3 V rail on a 1.5 mm L4 spine along the north band,
  a 1.5 mm Top run at y 22.5 and Bottom columns round U1 (441 mm of copper). The north band and the
  U1 surround are where the open nets had to pass.
- **Pinout against placement.** The CHANx header lines leave U1 on balls whose escapes face away from
  their header pins, so they cross each other and the flash/LED/SD lines north and east of U1. The
  flash pins (D00–D03, FCS_B, CCLK) are dedicated balls and cannot move.
- **Region-parallel planning.** Each region planned greedily against the base copper only; nothing
  arbitrated the shared corridors.

## Options recorded for the decision

1. Re-pin the freely permutable FPGA I/O for routability (CHANx, JA, LEDs, SD, UART, BTN,
   FT-PWREN#; flash/config stay) plus the small placement moves already pending (R18 next to U2-6,
   R24/R25 next to Q1, C40/C41 next to U2 pins 4/9, the LD5 nudge), then re-route stage 4b as one
   global plan rather than seven parallel regions.
2. Make L5 a VCC3V3 plane (Sig / GND / Sig / Sig / PWR / Sig): rip up stage 3's VCC3V3 trunks (the FT
   rails stay), tie the VCC3V3 pads to L5 by via as the GND pads are tied to L2. Frees the north band
   and the U1 surround on the inner layers.
3. Try Altium's autorouter (Situs) on the open nets as an experiment, without saving, to measure what
   a global rip-up router closes on the current copper.
