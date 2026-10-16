# Stackup and trace impedance (2026-10-15)

Impedance of every routed trace width on the production board, `Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc`
(SHA-256 `89a421b9...`). The numbers come from `tools/stackup_impedance.py`, which reads the layer stack from the
saved PcbDoc and solves each cross-section with a 2-D field solver. The HDI_Optimized copy has a different stack;
see its `HDI_OPTIMIZATION_NOTES.md`.

## Which fabricator these numbers are for

The table is computed for the stack stored in the board file: JLCPCB's catalogue stack JLCH061611N2-2116, with
JLC's layer thicknesses and its 2116 prepreg library Dk of 4.29.

The board is fabricated at PCBWay. `fabrication/PCBWAY_FAB_NOTES.txt` sends this same stack as the target, but it
also asks PCBWay to propose its own buildable stack (pressed thicknesses and Dk) and to return the USB pair
calculation for approval. The real board will therefore differ slightly from this table.

PCBWay quoted Dk 4.45 for its 2116 prepreg (`hdi_spec.md`). With only that change, every value falls by about
1 ohm:

| Trace | JLC stack (prepreg Dk 4.29) | PCBWay prepreg (Dk 4.45) |
|---|---:|---:|
| 3 mil, Top / Bottom | 67.8 ohm | 66.9 ohm |
| 3 mil, L3 / L4 | 60.0 ohm | 59.2 ohm |
| SDRAM bus, 0.125 mm, L3 / L4 | 50.4 ohm | 49.7 ohm |
| USB pair, 0.150 / 0.150 mm | 87.9 ohm differential | 86.8 ohm differential |

The core Dk (4.6, assumed) and the solder-mask model carry more uncertainty than the choice of fab; see "Method and
assumptions". When PCBWay returns its stack:
1. Enter it in the board's Layer Stack Manager.
2. Update the expected stack in `tools/verify_stack.py`, which checks against the JLC stack today, and run it.
3. Regenerate this table with `tools/stackup_impedance.py`.

## Stack

JLCH061611N2-2116 as stored in the PcbDoc (`tools/verify_stack.py` passes):

| Layer | Thickness (mm) | Dk | Role |
|---|---:|---:|---|
| Top solder mask | 0.0305 | 3.8 | |
| L1 Top | 0.035 | | signal |
| Prepreg 2116 | 0.112 | 4.29 | |
| L2 | 0.030 | | GND plane |
| Prepreg 2116 | 0.112 | 4.29 | |
| L3 | 0.030 | | signal |
| Core | 0.930 | 4.6 (assumed) | |
| L4 | 0.030 | | signal |
| Prepreg 2116 | 0.112 | 4.29 | |
| L5 | 0.030 | | VCC3V3 plane |
| Prepreg 2116 | 0.112 | 4.29 | |
| L6 Bottom | 0.035 | | signal |
| Bottom solder mask | 0.0305 | 3.8 | |

The laminate is 1.568 mm thick, or 1.629 mm with the mask.

Reference planes:
- **Top:** microstrip over L2 GND, 0.112 mm below.
- **Bottom:** microstrip over L5 VCC3V3, which is an AC ground through the decoupling. Bottom mirrors Top.
- **L3:** L2 GND is 0.112 mm above it, and L5 is 1.072 mm below it, across the core.
- **L4:** L5 is the near plane and L2 the far one; it mirrors L3.

## Signal traces

| Trace | Layer | Width | Z0 | Delay | Routed length |
|---|---|---|---|---|---|
| General signals (JTAG, flash, SD card, CHAN I/O) | Top, Bottom | 0.0762 mm (3 mil) | 67.8 ohm | 6.12 ps/mm | 716 + 720 mm |
| General signals | L3, L4 | 0.0762 mm | 60.0 ohm | 6.98 ps/mm | 946 + 995 mm |
| SDRAM bus | L3, L4 | 0.125 mm | 50.4 ohm | 6.98 ps/mm | 276 + 332 mm |
| SDRAM escapes | Top | 0.0762 mm (3 mil) | 67.8 ohm | 6.12 ps/mm | 121 mm |
| SDRAM escapes | Bottom | 0.125 mm | 56.8 ohm | 6.15 ps/mm | 49 mm |
| LED and resistor nets | Top, Bottom | 0.100 mm | 61.9 ohm | 6.13 ps/mm | 131 + 15 mm |
| USB D+/D- (differential pair) | Top | 0.150 mm, 0.150 mm gap | 87.9 ohm differential | 5.97 ps/mm | 17.08 mm each, 15.36 mm coupled |

USB pair modes: odd 43.9 ohm, even 60.2 ohm, common 30.1 ohm, single-ended 52.6 ohm. The target is 90 ohm
+/-10 % (81-99 ohm).

## Power and other wide traces

These traces carry DC rails, so their impedance does not matter. It is listed for completeness.

| Width (mm) | 0.15 | 0.20 | 0.30 | 0.40 | 0.50 | 0.60 | 0.80 | 1.00 | 1.50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Top / Bottom (ohm) | 52.6 | 45.9 | 36.8 | 30.8 | 26.5 | 23.3 | 18.8 | 15.7 | 11.2 |
| L3 / L4 (ohm) | 46.7 | 40.9 | 33.0 | 27.8 | 24.0 | 21.2 | 17.2 | - | - |

## Method and assumptions

- **Solver:** a 2-D quasi-static finite-difference field solve on a graded grid, 1.5 um at the conductor edges.
  C comes from the field energy, Z0 = 1 / (c0 sqrt(C x C_air)), and pairs are solved in odd and even mode.
  Traces are rectangular and lossless. The planes are assumed solid, and the other signal layer's copper is treated
  as prepreg resin.
- **Dielectric constants:** 4.29 is the 2116 prepreg library figure at 1 GHz. The core's 4.6 is an assumption: JLC
  does not publish it.
- **Solder mask:** modelled as a conformal 1.2 mil (0.0305 mm) coating with Dk 3.8, as in the PcbDoc. This
  model gives the lowest figures; other mask models only raise them. Computed with the same tool:

  | Mask model | 3-mil Top | USB pair |
  |---|---:|---:|
  | PcbDoc, 1.2 mil, Dk 3.8 | 67.8 ohm | 87.9 ohm |
  | Altium stock, 0.4 mil, Dk 3.5 | 71.5 ohm | 93.2 ohm |
  | No mask | 74.7 ohm | 97.2 ohm |

  The pair stays inside 81-99 ohm in every case. `hdi_spec.md` section 5 shows the same spread on the old
  stack.
- **Convergence:** the scheme converges from below, so the values are about 0.1-0.15 ohm low. Refining the edge
  cell to 0.8 um raises them by about 0.05 ohm. An independent finite-volume solve gives 67.9 / 50.5 / 88.1 ohm
  against the 67.8 / 50.4 / 87.9 here.
- **Cross-checks:**
  - On this stack the solver reproduces the project's earlier figures:
    - SDRAM 0.125 mm: 50.4 against 50.2-50.4 ohm (the three-solver table in `hdi_spec.md` section 5);
    - USB pair: 87.9 against 87.8 ohm (same table);
    - 3-mil Top: 67.8 against 68.0 ohm (section 8).
  - Run on the HDI_Optimized copy's JLC06161H-3313E stack, it gives 85.4 / 49.0 ohm, against 85.3 / 49.0 in the
    section-5 table.
- **Authority:** the fabricator's own stack and calculation decide the USB pair. `fabrication/PCBWAY_FAB_NOTES.txt`
  asks PCBWay to return it.

## Reproduce

```
python tools/stackup_impedance.py ["Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc"]
```

It prints the stack, the table below and the differential-pair line. It takes about 20 s and needs `numpy`,
`scipy`, `olefile` and `altium-monkey`.

## Appendix: every routed width

Generated by the tool. The class column lists up to three net classes, longest first. "(no class)" covers nets
without one, such as the CHAN I/O and the LED nets.

| Layer | Width (mm) | Z0 (ohm) | eps_eff | Delay (ps/mm) | Length (mm) | Net classes (by length) |
|---|---:|---:|---:|---:|---:|---|
| Top Layer | 0.0762 | 67.8 | 3.364 | 6.12 | 837.1 | (no class), CFG_FLASH, JTAG |
| Top Layer | 0.0800 | 66.7 | 3.367 | 6.12 | 1.0 | PWR_RAILS |
| Top Layer | 0.1000 | 61.9 | 3.381 | 6.13 | 130.8 | (no class) |
| Top Layer | 0.1050 | 60.8 | 3.384 | 6.14 | 1.3 | (no class) |
| Top Layer | 0.1100 | 59.7 | 3.388 | 6.14 | 0.3 | (no class) |
| Top Layer | 0.1300 | 55.9 | 3.404 | 6.15 | 1.0 | (no class) |
| Top Layer | 0.1400 | 54.2 | 3.412 | 6.16 | 0.7 | (no class) |
| Top Layer | 0.1450 | 53.4 | 3.416 | 6.16 | 9.7 | PWR_RAILS, (no class) |
| Top Layer | 0.1500 | 52.6 | 3.420 | 6.17 | 58.5 | USB_DATA, PWR_RAILS, (no class) |
| Top Layer | 0.1800 | 48.4 | 3.443 | 6.19 | 0.4 | (no class) |
| Top Layer | 0.2000 | 45.9 | 3.459 | 6.20 | 99.7 | (no class), PWR_RAILS |
| Top Layer | 0.2100 | 44.8 | 3.467 | 6.21 | 1.1 | (no class) |
| Top Layer | 0.2200 | 43.8 | 3.474 | 6.22 | 0.7 | (no class) |
| Top Layer | 0.2400 | 41.8 | 3.489 | 6.23 | 0.9 | (no class) |
| Top Layer | 0.2450 | 41.3 | 3.493 | 6.23 | 1.7 | (no class) |
| Top Layer | 0.2500 | 40.8 | 3.496 | 6.24 | 5.7 | PWR_RAILS |
| Top Layer | 0.2600 | 40.0 | 3.503 | 6.24 | 11.5 | PWR_RAILS, (no class) |
| Top Layer | 0.2700 | 39.1 | 3.510 | 6.25 | 0.7 | (no class) |
| Top Layer | 0.2750 | 38.7 | 3.514 | 6.25 | 0.7 | PWR_RAILS |
| Top Layer | 0.2800 | 38.3 | 3.517 | 6.26 | 13.5 | (no class), PWR_RAILS |
| Top Layer | 0.3000 | 36.8 | 3.530 | 6.27 | 24.4 | PWR_RAILS, (no class) |
| Top Layer | 0.3650 | 32.6 | 3.570 | 6.30 | 1.6 | (no class) |
| Top Layer | 0.3800 | 31.8 | 3.579 | 6.31 | 1.1 | (no class) |
| Top Layer | 0.4000 | 30.8 | 3.590 | 6.32 | 10.1 | PWR_RAILS, (no class) |
| Top Layer | 0.4250 | 29.6 | 3.603 | 6.33 | 0.8 | (no class) |
| Top Layer | 0.4300 | 29.4 | 3.606 | 6.33 | 1.3 | (no class) |
| Top Layer | 0.4500 | 28.5 | 3.616 | 6.34 | 9.0 | PWR_RAILS |
| Top Layer | 0.4600 | 28.1 | 3.621 | 6.35 | 0.7 | PWR_RAILS |
| Top Layer | 0.4650 | 27.9 | 3.623 | 6.35 | 0.3 | (no class) |
| Top Layer | 0.5000 | 26.5 | 3.640 | 6.36 | 34.9 | (no class), PWR_RAILS |
| Top Layer | 0.5500 | 24.8 | 3.661 | 6.38 | 2.8 | PWR_RAILS |
| Top Layer | 0.6000 | 23.3 | 3.681 | 6.40 | 11.9 | PWR_RAILS |
| Top Layer | 0.7000 | 20.8 | 3.717 | 6.43 | 17.3 | PWR_RAILS |
| Top Layer | 0.8000 | 18.8 | 3.748 | 6.46 | 11.4 | PWR_RAILS |
| Top Layer | 1.0000 | 15.7 | 3.797 | 6.50 | 7.3 | PWR_RAILS |
| Top Layer | 1.2000 | 13.6 | 3.836 | 6.53 | 10.5 | PWR_RAILS |
| Top Layer | 1.4000 | 11.9 | 3.868 | 6.56 | 1.9 | PWR_RAILS |
| Top Layer | 1.5000 | 11.2 | 3.881 | 6.57 | 21.1 | PWR_RAILS |
| L3-SIG | 0.0762 | 60.0 | 4.379 | 6.98 | 945.8 | (no class), JTAG, SDCARD |
| L3-SIG | 0.1250 | 50.4 | 4.375 | 6.98 | 276.2 | SDRAM_ADDR, SDRAM_DATA, SDRAM_CTRL |
| L3-SIG | 0.1500 | 46.7 | 4.373 | 6.98 | 2.0 | PWR_RAILS |
| L3-SIG | 0.2000 | 40.9 | 4.369 | 6.97 | 16.6 | PWR_RAILS |
| L3-SIG | 0.3000 | 33.0 | 4.362 | 6.97 | 37.1 | PWR_RAILS |
| L3-SIG | 0.3900 | 28.2 | 4.357 | 6.96 | 1.5 | PWR_RAILS |
| L3-SIG | 0.4000 | 27.8 | 4.357 | 6.96 | 25.8 | PWR_RAILS |
| L3-SIG | 0.5000 | 24.0 | 4.352 | 6.96 | 31.9 | PWR_RAILS |
| L3-SIG | 0.6000 | 21.2 | 4.349 | 6.96 | 14.3 | PWR_RAILS |
| L3-SIG | 0.8000 | 17.2 | 4.343 | 6.95 | 24.0 | PWR_RAILS |
| L4-SIG | 0.0762 | 60.0 | 4.379 | 6.98 | 995.4 | (no class), SDCARD, JTAG |
| L4-SIG | 0.1250 | 50.4 | 4.375 | 6.98 | 331.6 | SDRAM_ADDR, SDRAM_DATA, SDRAM_CTRL |
| L4-SIG | 0.1500 | 46.7 | 4.373 | 6.98 | 10.6 | (no class) |
| L4-SIG | 0.2000 | 40.9 | 4.369 | 6.97 | 12.7 | PWR_RAILS |
| L4-SIG | 0.3000 | 33.0 | 4.362 | 6.97 | 3.4 | (no class) |
| L4-SIG | 0.3700 | 29.1 | 4.358 | 6.96 | 1.3 | PWR_RAILS |
| L4-SIG | 0.3900 | 28.2 | 4.357 | 6.96 | 1.3 | PWR_RAILS |
| L4-SIG | 0.4000 | 27.8 | 4.357 | 6.96 | 32.9 | PWR_RAILS |
| L4-SIG | 0.5000 | 24.0 | 4.352 | 6.96 | 14.1 | PWR_RAILS |
| Bottom Layer | 0.0762 | 67.8 | 3.364 | 6.12 | 719.8 | (no class), JTAG, CFG_FLASH |
| Bottom Layer | 0.1000 | 61.9 | 3.381 | 6.13 | 15.3 | (no class) |
| Bottom Layer | 0.1050 | 60.8 | 3.384 | 6.14 | 0.8 | (no class) |
| Bottom Layer | 0.1100 | 59.7 | 3.388 | 6.14 | 3.6 | (no class) |
| Bottom Layer | 0.1150 | 58.7 | 3.392 | 6.14 | 1.3 | (no class) |
| Bottom Layer | 0.1250 | 56.8 | 3.400 | 6.15 | 48.7 | SDRAM_DATA, SDRAM_ADDR, SDRAM_CTRL |
| Bottom Layer | 0.1300 | 55.9 | 3.404 | 6.15 | 2.3 | (no class) |
| Bottom Layer | 0.1450 | 53.4 | 3.416 | 6.16 | 0.2 | (no class) |
| Bottom Layer | 0.1500 | 52.6 | 3.420 | 6.17 | 22.3 | PWR_RAILS, (no class) |
| Bottom Layer | 0.1600 | 51.1 | 3.428 | 6.18 | 1.7 | (no class), PWR_RAILS |
| Bottom Layer | 0.1750 | 49.0 | 3.439 | 6.19 | 0.5 | PWR_RAILS |
| Bottom Layer | 0.1800 | 48.4 | 3.443 | 6.19 | 0.4 | (no class) |
| Bottom Layer | 0.2000 | 45.9 | 3.459 | 6.20 | 150.0 | PWR_RAILS, (no class) |
| Bottom Layer | 0.2050 | 45.4 | 3.463 | 6.21 | 1.5 | PWR_RAILS, (no class) |
| Bottom Layer | 0.2100 | 44.8 | 3.467 | 6.21 | 1.8 | (no class), PWR_RAILS |
| Bottom Layer | 0.2300 | 42.7 | 3.482 | 6.22 | 6.6 | PWR_RAILS, (no class) |
| Bottom Layer | 0.2350 | 42.2 | 3.485 | 6.23 | 0.5 | PWR_RAILS |
| Bottom Layer | 0.2400 | 41.8 | 3.489 | 6.23 | 5.3 | PWR_RAILS, (no class) |
| Bottom Layer | 0.2500 | 40.8 | 3.496 | 6.24 | 4.6 | PWR_RAILS |
| Bottom Layer | 0.2550 | 40.4 | 3.500 | 6.24 | 0.4 | (no class) |
| Bottom Layer | 0.2600 | 40.0 | 3.503 | 6.24 | 1.0 | (no class) |
| Bottom Layer | 0.2650 | 39.5 | 3.507 | 6.25 | 0.9 | (no class) |
| Bottom Layer | 0.2800 | 38.3 | 3.517 | 6.26 | 0.2 | (no class) |
| Bottom Layer | 0.2850 | 37.9 | 3.520 | 6.26 | 1.2 | (no class) |
| Bottom Layer | 0.2900 | 37.5 | 3.524 | 6.26 | 2.8 | PWR_RAILS, (no class) |
| Bottom Layer | 0.2950 | 37.2 | 3.527 | 6.26 | 0.7 | (no class) |
| Bottom Layer | 0.3000 | 36.8 | 3.530 | 6.27 | 75.8 | PWR_RAILS, (no class) |
| Bottom Layer | 0.3450 | 33.8 | 3.559 | 6.29 | 0.5 | PWR_RAILS |
| Bottom Layer | 0.3500 | 33.5 | 3.562 | 6.30 | 0.5 | PWR_RAILS |
| Bottom Layer | 0.3600 | 32.9 | 3.567 | 6.30 | 0.8 | (no class) |
| Bottom Layer | 0.3700 | 32.4 | 3.573 | 6.31 | 1.8 | PWR_RAILS, (no class) |
| Bottom Layer | 0.3800 | 31.8 | 3.579 | 6.31 | 0.7 | (no class) |
| Bottom Layer | 0.3900 | 31.3 | 3.585 | 6.32 | 1.1 | PWR_RAILS |
| Bottom Layer | 0.4000 | 30.8 | 3.590 | 6.32 | 30.2 | (no class), PWR_RAILS |
| Bottom Layer | 0.4100 | 30.3 | 3.595 | 6.32 | 2.9 | (no class) |
| Bottom Layer | 0.4500 | 28.5 | 3.616 | 6.34 | 14.2 | (no class), PWR_RAILS |
| Bottom Layer | 0.4700 | 27.7 | 3.626 | 6.35 | 0.7 | PWR_RAILS |
| Bottom Layer | 0.5000 | 26.5 | 3.640 | 6.36 | 32.0 | (no class), PWR_RAILS |
| Bottom Layer | 0.6000 | 23.3 | 3.681 | 6.40 | 1.5 | PWR_RAILS |
| Bottom Layer | 0.7000 | 20.8 | 3.717 | 6.43 | 2.2 | PWR_RAILS |
| Bottom Layer | 0.8000 | 18.8 | 3.748 | 6.46 | 19.4 | PWR_RAILS, PWR_SWITCH |
| Bottom Layer | 0.9600 | 16.3 | 3.788 | 6.49 | 0.6 | PWR_RAILS |
| Bottom Layer | 1.0000 | 15.7 | 3.797 | 6.50 | 26.0 | PWR_RAILS |
| Bottom Layer | 1.0400 | 15.2 | 3.806 | 6.51 | 0.6 | PWR_RAILS |
| Bottom Layer | 1.0600 | 15.0 | 3.810 | 6.51 | 4.4 | PWR_RAILS |
| Bottom Layer | 1.0950 | 14.6 | 3.817 | 6.52 | 1.3 | PWR_RAILS |
| Bottom Layer | 1.1400 | 14.1 | 3.826 | 6.52 | 1.3 | PWR_RAILS |
| Bottom Layer | 1.1500 | 14.0 | 3.828 | 6.53 | 0.9 | PWR_RAILS |
| Bottom Layer | 1.1600 | 13.9 | 3.829 | 6.53 | 1.7 | PWR_RAILS |
| Bottom Layer | 1.2000 | 13.6 | 3.836 | 6.53 | 4.7 | PWR_RAILS |
| Bottom Layer | 1.3550 | 12.2 | 3.861 | 6.55 | 1.9 | PWR_RAILS |
| Bottom Layer | 1.4250 | 11.7 | 3.871 | 6.56 | 1.8 | PWR_RAILS |
| Bottom Layer | 1.5000 | 11.2 | 3.881 | 6.57 | 21.6 | PWR_RAILS |
