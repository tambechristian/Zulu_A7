# Second user button (BTN2): study, not adopted (2026-11-26)

A second FPGA user button was tried on a copy of this board (Rev_5, since deleted). The decision was to **keep one
button**, so Rev_4 stays the release. This note records why, so the question doesn't have to be re-checked.

## What was tried

The user's choice was "Wide pair (6.35/19.05)":

| Part | Side | Rot | Centre (mm) | Note |
|---|---|---|---|---|
| BTN | Top | 90 | (18.475, 6.35) | moved; symmetric with BTN2 about y 12.70 |
| BTN2 | Top | 90 | (18.475, 19.05) | new, PTS810 (same part as BTN) |
| C158 | Top | kept | (18.10, 12.65) | moved between the buttons |
| R137 | Bottom | 0 | (18.00, 22.00) | new, 10K series into the FPGA |
| R138 | Bottom | 90 | (16.40, 20.10) | new, 10K pull-down on N$BTN2 |

The circuit was the same as BTN: VCC3V3 to BTN2 to N$BTN2, with a 10K pull-down and a 10K series resistor to the
ball. Placement, labels, schematic and ECO all went in cleanly. Only the route to the FPGA failed.

## Why it was dropped

- **The spare balls can't escape.** The free U1 balls are W19, W18, U18, U17 and C17. V19 is CSO_B and was avoided.
  - **W19, W18 and U18:** no via site at all. W19's only Top channel sits between the GND stub (x 50.65) and UART_FT_TXD
    (x 51.1), which is too narrow for any via, and L3 under the ball carries FPGA-TMS.
  - **U17 (49.85, 8.35) and C17 (50.05, 15.55):** one Top-L2 + L2-L3 microvia stack each.
- **The spare balls are walled off.** A flood fill of BTN2's free space, using the router's rules, found them in a
  pocket sealed on all four routing layers. The thinnest walls are the AIN15_P/N XADC pair on Bottom and one
  UART_FT_RXD segment on L4.
- **The long route doesn't close.** A route to W19 is 78 mm with 23 via sites; one to U17 is 82 mm with 28. Both need
  the UART_FT_RXD L4 segment (x 43.55 to 48.0, y 17.5) removed. UART_FT_TXD re-routes after that, but **UART_FT_RXD
  cannot**: BTN2 takes the only lane.
- **A direct route costs too much.** A ~40 mm, 3-via route needs 15-19 nets around U1 re-routed: FPGA-TCK/TMS, DONE,
  the SD bus, LED0, the UART lines and the header CHANs.
- **Moving the button doesn't help.** Every button site near the FPGA needs 4-23 nearby tracks moved.

**Verdict.** A second button only fits with a re-layout of U1's south and east fan-out, for example the proposed
floorplan (commit 75b88ba) or a BGA SDRAM that frees room around U1.
