# Zulu_a7_no_pmod Rev 4: UART activity LED LD6 (2026-11-25)

The user asked for an RX/TX activity LED, yellow, wired the Cmod A7 way. The Cmod (reconstructed in
`reference/cmod_a7_usb_prog`) ties FT2232H BCBUS3/RXLED# and BCBUS4/TXLED# straight to one LED cathode.

A ChatGPT proposal put a Schottky diode in each leg ("do not tie BCBUS3 and BCBUS4 together"). It was not used:
the Cmod netlist and FTDI's single-LED arrangement tie the pins directly.

Board: md5 658cf76c (saved 2026-11-25 22:47), DRC 0 violations (`docs/drc_rxtx_led.drc`). Backups:
- `backups/Zulu_a7_no_pmod.PcbDoc.rxtx-led-placed`
- `backups/Zulu_a7_no_pmod.PcbDoc.pre-rxtx-copper`
- `backups/Zulu_a7_no_pmod.PcbDoc.rxtx-led-final`

## Circuit (sheet 4)

```
VCC3V3 -- R136 1K -- LD6 yellow (A -> K) -- FT-RXTX-LED = U2 pin 54 (BCBUS3 RXLED#) + U2 pin 55 (BCBUS4 TXLED#)
```

| Part | MPN | Notes |
|---|---|---|
| LD6 | Lite-On LTST-C191KSKT | Yellow 591 nm AlInGaP 0603, the LD1-LD5 family and land; LCSC C125100 |
| R136 | RC0201FR-071KL, 1K | Same BOM line as R11/R135 |

- **Current:** about 1.3 mm while either pin pulses low.
- **Mode requirement:** channel B must stay in UART mode in the EEPROM for pins 54/55 to be RXLED#/TXLED#. A blank
  EEPROM defaults to UART. If the EEPROM is ever programmed (Vivado `program_ftdi`, FT_PROG), keep channel B as
  UART/VCP.

`tools/rxtx_led_sch.py`:
- deletes the two No-ERC crosses on U2-54/55;
- ties the two pins with a short wire carrying the label FT-RXTX-LED;
- clones R135 into R136 and LD5 into LD6 beside the DONE LED block.

The netlist diff shows only the intended change.

## PCB

1. **ECO:** Disable All, then enabled only:
   - add LD6/R136;
   - R136-1 to VCC3V3;
   - add nets FT-RXTX-LED and NetLD6_A.
2. **Site search** (`tools/route/rxtx_led/sites.py`): Top side, pads 0.15 mm from every pad and hole, bodies
   0.26 mm from every body, clear of all printed silk, 0 rips.
3. **Placement** (`tools/NoPmodPlaceRxTxLed.pas`), site 1, between U2's north edge and X1 (4.9 mm from the pins):
   - LD6 rotation 0, A (34.70, 20.00), K (36.30, 20.00), cathode east like LD1-LD5;
   - R136 rotation 0, pad 1 (33.05, 20.00) on VCC3V3, pad 2 (33.65, 20.00).
4. **Routing:** two passes. In one pass the router ties plane nets first, so R136's VCC3V3 via closed the only
   Top corridor out of pins 54/55 and the cathode net found no path. Fixed by routing FT-RXTX-LED first (`--nets`)
   and the rest seeded on it.
   - The cathode net runs north of LD6's anode, then through the 0.38 mm lane between R136 and X1's MH2 into
     pin 54. A short link at the inner end of the pads joins pins 54 and 55.
   - R136-1 joins the existing VCC3V3 copper at U2-50's via.
   - Totals: 13 tracks, 0 vias. route_check PASS; judge 0 new DRC; no via in any pad.
5. **Apply:** `tools/FabBCopper_RxTxLed.pas`, then connection rebuild (0 left) and DRC 0. There were no new vias,
   so no microvia marking was needed.

## Verified on the saved file

| Check | Result |
|---|---|
| Opens | 0 |
| Laser microvias | 1329 (unchanged) |
| Tracks | 6261 -> 6274 |
| Body gate | PASS, same 18 warnings as before |
| Nets | LD6/R136/U2-54/55 on the schematic nets |

## Release tooling

- `generate_jlcpcb_assembly.py` knows LTST-C191KSKT (LCSC C125100, "yellow 0603 SMD indicator LED"), and the LD0
  note now says LD1-LD6.
- The `bom_audit.py` LED row lists LD6.
- `board_illustration.py` draws LD6 yellow (RELEASED_MD5 658cf76c).
