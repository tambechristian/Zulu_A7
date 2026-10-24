# Zulu A7 Feather -- routing log

Stack: the production 6-layer HDI stack, unchanged: Top / L2-GND (pour) / L3-SIG / L4-SIG / L5-VCC3V3 (pour) / Bottom,
through 0.20/0.35, laser 0.15/0.30 (Top-L2, L2-L3, L4-L5, L5-Bottom), buried L3-L4 0.15/0.27.

## Stage 1 -- U1 fan-out transplanted from production (2026-10-23)

U1 (XC7A35T, CPG236) is at rot 0 on both boards, and the Feather's 24 under-U1 decaps sit at the production
offsets. So production's DRC-clean escape copper inside U1's footprint is valid Feather geometry: shift it by
the U1-centre offset and re-net it ball by ball.

| Step | Tool | Result |
|---|---|---|
| Production copper | `tools/transplant_u1.py --dump` (KiCad python) -> `tools/route/prod_u1_copper.json` | 4,203 tracks, 1,790 vias, 238 U1 balls |
| Ball map | same | 193 balls keep their net, 18 swapped header balls take the new CHAN net, 19 now unconnected, 8 unconnected on both boards. Every production net maps to one Feather net. |
| Plan | `tools/transplant_u1.py --r 5.5` -> `tools/route/stage1_u1.json` | Window: +-5.5 mm around U1's centre (24.40, 11.43), all layers. Tracks crossing its edge are clipped there, and their outer ends become stage-2 starting points. Every piece is checked against every Feather pad of another net at 0.09 mm, with BGA lands modelled as circles. Copper not connected back to a pad of its own net is pruned. **201 vias + 771 tracks on 103 of U1's 104 nets.** CHAN1 has none: its production copper left the window. |
| Placement for it | `plan_placement.py`, `FeatherPlace6/7.pas` | Bulk parts are banned from the window on the bottom (new zones `B_u1n`/`B_u1s`). Ten 0805 bulk caps had been packed under U1, on production's through-via sites; they moved to the north and south bands, the column east of the window, and C94 by the buck cells. C92 and C123 now use production's rot 180; at rot 0 their pad nets swapped sides. The buck output caps are at x 16.705/18.455 (0.1 mm mask webs to the inductors). |
| Place | `tools/emit_copper.py` -> `FeatherCopper_Stage1U1.pas` (PlaceStage1U1) | 201 vias, 771 tracks, every net found |
| Microvias | `Zulu_Altium_VS_Code/tools/stage13_mark_microvias.py <pcbdoc> --expect 87` (board closed) | Scripted laser vias save as regular blind vias. 87 were marked (Vias6 byte 312) and verified. |
| Verify | `tools/verify_copper.py tools/route/stage1_u1.json` | **PASS**: 201/201 vias, 771/771 tracks, nothing missing or extra |
| DRC | `docs/drc_stage1_u1.drc` (after Repour All) | **580 = 465 un-routed + 115 net antennae**, nothing else. Un-routed went from 595 to 465. The antennae are the clipped stubs at the window edge, where stage 2 continues. 0 clearance, short, width, hole, mask or silk violations. |

Dropped at the window edge for Feather pad conflicts: one Top-L2 microvia (UART_FT_RTS#, on R16), two west
through vias (AIN16_N, GND, on C86/C144), and stubs into the strap row, RESET and the buck caps. These nets
are routed onward in stage 2.

X3's designator has no clean spot after C146 moved, so it is now hidden too (11 hidden designators).

## Remaining

465 connections: SDRAM U1 -> U3 (east), FT2232HQ U2 <-> U1 (JTAG, UART, FIFO), flash U4, header pins, USB pair
X1 -> U2, microSD X3, LEDs, buck feeds and plane ties, U8 charger, the XADC dividers.

RESET sits 0.85 mm south of U1's south ball row, in the path of the south-row escapes. That is where the SE
header balls (W13-W19, V19, U19) and several SDRAM balls exit.

## Stage 2 -- Freerouting through KiCad (2026-10-23/24)

Tools, installed without admin rights:
- Freerouting 2.5.0 jar in `%LOCALAPPDATA%\Programs\freerouting`.
- Temurin 25 JRE zip in `%LOCALAPPDATA%\Programs\temurin25`, checksum-verified against Adoptium's published value.
- Freerouting's native `freerouting-cli.exe` crashes 12 s in (a ComponentOutline serialization error) and then hangs, so it is not used.
- Always pass `--usage_and_diagnostic_data.disable_analytics=true`; otherwise it tries to send usage data to its servers.

| Step | Tool | Notes |
|---|---|---|
| Board -> DSN | `tools/fr_prepare.py <wd>`, then the same with `--export` | Every existing track and via is locked and exports as `(type fix)`. L2/L5 become power layers. Per-layer width classes come from the board's Width rules: sdram, v33, u8, v10, sw, rails, usb, default 0.0762. Clearance 0.09. The six board via types. 0.3 mm keepout band inside the board edge. KiCad's python exits 127 right after SaveBoard; the file is complete. |
| Route | `java -jar freerouting-2.5.0.jar --gui.enabled=false --usage_and_diagnostic_data.disable_analytics=true --router.automatic_neckdown=false -de feather.dsn -do run.ses --router.autorouter.max_passes=100 -mt 22` | About 70 min. Pass 1 is always the best; later passes score worse and it stops early. Fan-out escapes only 47-49 % of SMD pins. It uses through vias, and microvias essentially never. |
| SES -> plan | `tools/fr_import.py <wd> run.ses tools/route/stage2_fr.json` | The new copper is everything not locked |
| Place | `emit_copper.py` -> `FeatherCopper_Stage2FR5.pas`; `FeatherWidthFix.pas` (WidenPowerTracks) | 126 vias, 1,496 tracks. 46 neck-downs of 0.057 mm were widened to 0.0762 in the plan, and 21 power tracks to their per-layer minimum on the board. |
| Verify | `verify_copper.py stage1_u1.json stage2_fr.json` | **PASS** 327/327 vias, 2,267/2,267 tracks; 87 microvias still marked |

| Run | Rules | Unrouted after (KiCad, planes refilled) | Placed? |
|---|---|---|---|
| 3 | single power class, no edge keepout | 179 | no (copper on the board edge) |
| 4 | + edge keepout | 180 | placed, then rolled back (334 width violations) |
| 5 | + per-layer width classes, neck-down off | 190 | **on the board** |

Altium DRC with run 5 on the board (`docs/drc_stage2_fr.drc`): **340 = 190 un-routed + 144 net antennae +
6 clearance**. The 6 clearance violations are VCC3V3 fan-out stubs on Bottom: by L4-1 (14.0, 4.2) and at
(20.2, 17.0)-(20.8, 15.5). Freerouting narrowed them to fit, and they collide once widened to the 0.2 mm
Bottom minimum. No width, short, hole or mask violations.

The 190 open connections are spread over about 120 nets: GND 22 and VCC3V3 19 (plane ties), most of the SDRAM
bus with one connection each, JTAG, flash, microSD, FT2232 control, clocks, header CHAN nets, USB pair, LEDs, XADC.
