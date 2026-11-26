# Zulu_a7_no_pmod Rev 4: DONE LED LD5 (2026-11-25)

The user asked for a DONE LED like the Digilent Cmod A7's (R30/R40/LD3). LD5 is an orange LED that lights once the
FPGA is configured, whatever bitstream is loaded. It is the quickest check when booting from flash fails.

Board: md5 94a95d15 (saved 2026-11-25 21:10, R135 = 1K), DRC 0 violations / 0 warnings (`docs/drc_done_led.drc`).
The first build with R135 = 140R was md5 8c34c6cc. Backups in
`backups/`:
- `.done-led-placed`: parts placed, no copper
- `.pre-done-led-copper`: with the ECO net change, before the copper
- `.done-led-final` (140R)
- `.done-led-1k` (final)

## Circuit

```
VCC3V3 -- R4 G+H (2 x 100R, existing) -- FPGA-DONE (U1 ball U12) -- R4-B 100R (existing) -- DONE (U2 FT2232HQ pin 22)
                                                                                              |
                                                                              R135 1K 0201 (new)  
                                                                                              |
                                                                              LD5 orange 0603 (new) -- GND
```

The FPGA holds DONE low until configuration completes, then releases it. The existing 200R pull-up raises it and
LD5 lights.

| Part | MPN | Notes |
|---|---|---|
| LD5 | Lite-On LTST-C191KFKT | Orange 605 nm AlInGaP, 0603, 0.55 mm high, same family and land as LD1-LD4. User's colour choice. LCSC C160478. |
| R135 | Yageo RC0201FR-071KL, 1K | Same BOM line as R11/R15/R20/R22/R23. 140R at first; 1K chosen by the user after the review for VIH margin. |

Operating point, taking VF about 1.8 V at 1 mA:

| Quantity | Value |
|---|---|
| LED current | (3.3 - 1.8) / (200 + 100 + 1000) = 1.2 mA (LD3/LD4 run at 1.5 mA) |
| FPGA-DONE high | 3.3 - 200 x 1.15 mA = 3.07 V |
| DONE at the FT2232H | 3.07 - 100 x 1.15 mA = 2.95 V |
| DONE sink while low | 3.3 / 200 = 16.5 mA (unchanged from before) |
| Added 3V3 load once configured | about 1.2 mA |

Both DONE levels are above VIH 2.0 V.

### Why the FT side of DONE

The first wiring tapped FPGA-DONE, the Cmod topology: 140R, about 4.1 mA, FPGA-DONE at 2.48 V. FPGA-DONE copper
exists only around U1 and R4 at the east end. The router found no path from the LED column, because the SDRAM bus
fields on L3/L4 under U3 block it ("nopath" after about 55 min).

The DONE net (U2 pin 22) is 9.6 mm away and routes in about 11 mm. The user approved the change. The extra R4-B 100R
lowers the LED current a little and raises both DONE high levels.

## Schematic (sheet 4, `zulu_a7_4.SchDoc`)

`tools/done_led_sch.py` clones R24 into R135 and LD3 into LD5 (font 8 remapped to 3), with wires, labels and a
3-line caption beside the R4 DONE pull-up. It is append-only, refuses to run twice, and its header Weight is
rewritten.

Then:
1. Colour set to orange (MANF#/Comment/SPEC).
2. The R135 label moved from FPGA-DONE to DONE, with the NOTEs and caption updated.

The netlist diff against the backup shows only R135 (1 = DONE, 2 = node with LD5 A) and LD5 (K = GND).

## PCB

1. **ECO:** run three times. Each time Disable All, then enable only the rows for this change:
   - add LD5/R135, their pins and NetLD5_A;
   - LD5 comment and parameters;
   - R135-1 FPGA-DONE -> DONE and the NOTEs.

   The pre-existing unrelated proposals (15 design-item-ID swaps, comment/description/parameter changes, net-class
   and diff-pair removals, rule changes) were never applied.
2. **Placement:** `tools/NoPmodPlaceDoneLed.pas`.
   - LD5 rotation 0 in the LED column's free slot between LD2 and LD3: A (21.400, 14.185), K (23.000, 14.185). The
     cathode is east, like every LED.
   - R135 rotation 90 in the BTN-to-LED gap.
   - `tools/NoPmodR135Nudge.pas` then moved R135 +0.08 mm east (pads at x 20.530) to clear DRC Component Clearance
     0.254 mm against BTN's 3D body.
   - Both designators are hidden, like every chip LED and passive.
3. **Routing:**
   - `tools/route/done_led/prep.py` ripped LD2's anode route (2 tracks, 3 vias), which sat under LD5.
   - The router laid DONE (Top/L3, six Top-L2-L3 microvia pairs) and LD5-K to a GND microvia in the pad. It also
     re-routed LD2's anode via a through via, nudged to (22.125, 12.55) so its land clears the LD2 anode pad.
   - Plan (`tools/route/done_led/trial_done/plan.json`): -2 tracks, -3 vias, +87 tracks, +16 vias. route_check
     PASS; judge 0 new DRC; no new through via in an SMD pad.
4. **Apply:** `tools/FabBCopper_DoneLed.pas`, then:
   - mark_microvias: 15 marked, 1329 verified;
   - repour;
   - connection rebuild: 0 remaining;
   - DRC 0.

## Verified on the saved file

| Check | Result |
|---|---|
| Opens | 0 |
| Laser microvias | 1329 |
| X3 keep-out strip | clear |
| Body gate | PASS, same 18 warnings as before this change |
| Duplicate tracks (41) and through-via/pad touches (4) | identical to the pre-LED board |

Two of those touches predate this change and should be looked at before release: X3-6 (GND via, 0.01 mm) and LD0-1
(N$LD0B, 0.025 mm).

## Independent review (2026-11-25, 3 lenses + adversarial verify)

**Fixed:**
- `generate_jlcpcb_assembly.py` still had `LD5` in STALE_REFS (the old charger LED), so validate() would have
  refused the release. It has been removed and the comment says the designator was reused.
- `bom_audit.py`'s LED row still described the old 1.8 mA LD5. It now gives the DONE LED's ~3.2 mA path.

**Toolchain hazard (pre-existing, made visible by the LED):** openFPGALoader's `digilent` cable profile (used by
`-b cmoda7_*`, `basys3`, `arty`, `nexys_a7`) sets ADBUS5 as an output driven high. This board wires ADBUS5 (U2
pin 22) to DONE through R4-B. With that profile the FT2232H fights the FPGA while it holds DONE low:
- about 35-41 mA into the DONE ball;
- LD5 lit on an unconfigured FPGA.

Program with `openFPGALoader -c ft2232` (ADBUS4-7 inputs) or a custom layout that keeps ADBUS5 an input. On the
first boards, bench-check every host tool (including Vivado hw_server if the EEPROM gets a Digilent image) with the
FPGA held in PROG_B reset: LD5 must stay dark.

**Margins with R135 = 140R (tolerance model):** VCC3V3 -3%, R4 +5%, R135 -1%, LED VF 1.65 V hot/low bin.

| Reader | Worst-case level | Margin over VIH 2.0 V |
|---|---|---|
| FPGA DONE ball | 2.48 V | 0.48 V (the one startup depends on; 2.95 V with the 1K) |
| FT2232H input | 2.13 V | 0.13 V (informational read; 2.82 V / 0.82 V with the 1K now fitted) |

**Applied (user's choice, 2026-11-25 21:10):** R135 = 1K (RC0201FR-071KL, an existing BOM line).
- Worst case is now 2.95 V at the ball and 2.82 V at the FT2232H, about 0.8 V of margin at both readers.
- LED current is about 1.2 mA.
- Applied as a schematic value change plus an ECO touching only R135's comment and parameters. No copper changed.
- DRC 0 (21:10:36). The PCB's PrimitiveParameters show RC0201FR-071KL x 6 (was 5) and RC0201FR-07140RL x 2 (R12/R16).

**Notes left for the release:**
- R4's SPEC/description still say "six elements used, two spare", but all eight are wired (G+H = the DONE
  pull-up).
- The schematic PDF predates the LED.
- The LD2 anode through via is tented under the LD2 body, 0.10 mm from the pad.
- The DONE feed uses 12 laser microvias. That is functional, but a cleaner route is possible if the area is
  re-routed.

## Release tooling

- `tools/generate_jlcpcb_assembly.py` knows LTST-C191KFKT (LCSC C160478, "orange 0603 SMD indicator LED"). The LD0
  polarity note now says LD1-LD5.
- `tools/board_illustration.py` draws LD5 orange (RELEASED_MD5 8c34c6cc). The illustrations are redrawn.
- The Rev 4 release (Gerbers, BOM/CPL, PDF) is not built yet.
