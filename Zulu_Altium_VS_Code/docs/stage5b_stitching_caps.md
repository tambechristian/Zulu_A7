# Stage 5b: five VCC3V3↔GND stitching capacitors — placed 2026-09-24

**Status: PLACED, SAVED, DRC LINE-FOR-LINE IDENTICAL TO THE BOARD BEFORE IT, VERIFIED FROM THE SAVED FILE.**
Schematic: `tools/stitch_caps.py` (sheet 3). Placement: `PlaceStitchCaps` in `tools/ZuluPlacement.pas`.
Copper: `PlaceStage5b` / `RemoveStage5b` in `tools/ZuluSetup.pas`.
`tools/stage5b/gen.py --check` reproduces `placement.json` and `route.json` (route md5
`da807e98c872da5ba786432aa360c7f7`): 10 vias, 10 tracks, additions only.

## Why

Stage 5 made L5 the VCC3V3 plane (`docs/stage5_l5_plane.md`). Top and L3 reference L2-GND; L4 and
Bottom reference L5-VCC3V3. **52 signal vias join one side to the other, and 39 of them are the
AS4C32M16SB bus** (143 MHz, LVCMOS33, unterminated), so their return current can cross between the
planes only through a VCC3V3↔GND capacitor. All 46 existing ones sit in the y 3.0–4.2 row, in the
x 41–57 cluster round U1, or at x 2.6–7.6 — **none anywhere in x 12–39, y 6–25.4, which is where U3
sits.** The median hop was 3.30 mm and the worst 12.70 mm, against a median 1.62 mm to a GND via
before the plane change. Interplane capacitance does not help: L2 and L5 are 1.3512 mm apart, about
44 pF over the whole board, 25 Ω at 143 MHz.

## What was added

Five **Murata GRM033R61A104KE15D**, X5R 10 V 0.1 µF 0201 — already the board's 0201 100 nF on eleven
positions, so **the BOM gains no line**; that line goes from eleven to sixteen.

| ref | centre | layer | rot | VCC3V3 via | GND via | stitch loop | tie | serves |
|---|---|---|---|---|---|---|---|---|
| C155 | 26.000, 20.250 | Top | 180 | 25.700, 20.675 | 26.300, 20.675 | 0.600 | 0.850 | UDQM 12.70→3.75, CKE 11.66→4.73, A12 12.23→4.86 |
| C156 | 29.550, 20.000 | **Bottom** | 180 | 28.925, 20.375 | 29.525, 20.400 | 0.601 | 1.012 | D10 10.54→3.95, D11 9.11→4.99; also U3-43's supply pin 11.80→2.50 |
| C157 | 39.050, 18.000 | Top | 180 | 38.825, 18.425 | 39.350, 18.425 | 0.525 | 0.857 | D13 6.93→3.68, and the best remaining path for D3 and D6 |
| C158 | 18.100, 16.650 | Top | 270 | 17.675, 16.200 | 17.525, 16.725 | 0.546 | 1.068 | A5 12.45→1.45, A7 12.69→3.00, A9 12.32→3.75 |
| C159 | 23.300, 7.500 | Top | 180 | 22.575, 7.500 | 23.600, 7.950 | 1.119 | 0.875 | BS0 3.10→0.51, A0 3.36→2.20, RAS# 3.07→2.31, A1 3.41→2.98 |

**The placement is the specification, not the capacitance.** With roughly 2 nH of mounting inductance
a 100 nF 0201 self-resonates near 11 MHz, so at the bus clock and above the impedance is set entirely
by the loop — the barrel across the 1.3512 mm L2↔L5 cavity plus the pad-to-via tie, which is the only
term a layout can shorten. These five are tied in **0.85–1.07 mm**, against a **2.43 mm median** for
the 46 already on the board. Do not move them, lengthen their stubs, delete either via, or substitute
a larger case size.

## Measured on the saved board, before → after

| | stage 5 | stage 5b |
|---|---|---|
| VCC3V3↔GND capacitors | 46 | 51 |
| **SDRAM crossings beyond 5.0 mm** | **11 of 39** | **2 of 39** |
| worst SDRAM hop | 12.70 mm | **5.47 mm** |
| median / mean SDRAM hop | 3.30 / 4.71 mm | **3.00 / 2.88 mm** |
| free routing area (4 layers) | 4212.8 mm² | 4199.6 mm² (**−13.2**) |
| north band lanes (y 19.6) | 669 | **669** |
| U1 east lanes (x 52.9) | 382 | **382** |

**Zero lanes lost on either cut-line** — the two corridors stage 4b still has to cross are untouched.
The unconstrained optimum would have taken six Bottom lanes off the north band; the capacitor was
moved instead. The −13.2 mm² is 0.31 % of the board's free area and 6 % of what stage 5 bought back.

The two crossings that remain beyond 5 mm are **D6 (30.975, 8.925) at 5.47 mm and D3 (33.975, 8.925)
at 5.03 mm, both unchanged.** D6 cannot be fixed by any capacitor anywhere: it is sandwiched between
U3's moulded body on the Bottom and U2's pad ring on the Top, and an exhaustive search over the full
0.025 mm grid found no legal capacitor site with a legal via pair within 5 mm of it. Both still improve
on the return-path model (1.608 → 1.381 and 1.540 → 1.455 nH, both through C157) because C157 is well
tied, not because anything got nearer. Closing them properly is a component move, not a capacitor.

Two bonuses came free on ordinary decoupling: **U3-43's supply pin goes 11.80 → 2.50 mm** from a
VCC3V3↔GND capacitor and U3-49 7.37 → 4.33. U3's north-side supply pins had none. The 8 XADC crossings
(worst 4.53, median 2.14) and the 5 LED/charger ones (DC) are unchanged; that was checked, not assumed.

## Gates, on the board as saved

```
python tools/stage5/tie_check.py --net VCC3V3      129 SMD pads, tied 129, untied 0; 86 vias   exit 0
python tools/stage5/plane_islands.py --net VCC3V3 --plane L5   133/133 pads, 86/86 vias on the main island
python tools/stage5/plane_islands.py --net GND --plane L2      216/216 pads, 133/133 vias on the main island
python tools/stage5/gnd_check.py    206 GND pads, 203 tied, the same 3 untied as before (no regression)
python tools/route_reach.py         140 / 140 routable
python tools/route_emit.py tools/stage5b/route_anchored.json Stage5b    clean with NO free_end flags
```

That last one is the connectivity proof: `route.json` carries `free_end` on every stub because the
five pads did not exist when it was written, but `route_anchored.json` is the same copper with the
flags stripped, and it checks clean against the real board once the parts are placed.

Verified from the saved PcbDoc: all ten lands within **0.00 µm** of `placement.json`, correct layers,
pad 1 GND and pad 2 VCC3V3 on all five; copper +10 tracks (5 VCC3V3, 5 GND) and +10 vias, **nothing
removed**, no other net touched.

## DRC

`docs/drc_stage5b_2026-09-24.drc` is **line for line identical** to `docs/drc_stage5_2026-09-23.drc`:
144 Un-Routed Net, 50 Net Antennae, 7 Width, 3 Clearance, 3 Dead copper, 1 Starved Thermal, 1 each of
Silk to Silk, Silk To Solder Mask, Short-Circuit, Modified Polygon, Minimum Solder Mask Sliver and
Hole Size. No new violation of any kind — in particular no silkscreen or solder-mask-sliver problem,
which the planning workflow had flagged as unresolved and could not settle from the files.

## Two things the workflow got wrong, and one it got right that no gate could

1. **PAD 1 IS GND, NOT VCC3V3 — and placing on the wrong convention would have shorted the planes.**
   The judge took pad 1 = VCC3V3 from the all-capacitor majority (28 of 46). It is the wrong majority:
   every 0201 of this family reads the other way (C133–C138, C38), and C155–C159 are clones of C136.
   The ECO confirmed it — "C155-1 to GND, C155-2 to VCC3V3". `tools/stage5b/gen.py` keeps the lands,
   the vias and `route.json` byte-identical and turns each part half a revolution instead (H 180,
   V 270), so pad 1 lands on the GND side. `eco.py` swaps the pad numbers to match.
2. **All three planners put a capacitor under U3's moulded body, and no shipped gate can see it.**
   `block_place`'s courtyard test uses the **pad-extent** box, but a TSOP-II-54's body runs past its
   end pads: fitted from the EAGLE package at rms 0.0001 mm, U3's body is (17.175, 7.075)–(39.525,
   16.625) against a pad box of (17.725, 5.570)–(38.975, 18.130) — **0.5499 mm of overhang at each x
   end**. `tools/stage5b/bodies.py` fits all 157 parts and `chk.py` applies the test. The five as
   placed clear every moulded body, worst gap **0.150 mm** (C156 to R80).
3. `block_place` is **not** fixed. It is Bottom-side throughout (`apply_moves`, `legality` and the
   Pascal emitter all index `bottom_pads` only) and the courtyard regions in `ShapeBasedRegions6`
   carry no component link, so making it side-aware and body-aware is its own job. Four of these five
   parts are on the Top, so the placement went through `Place()` in `tools/ZuluPlacement.pas` — the
   same helper that placed all 157 components — and was proved by re-measuring every land from the
   saved file.

## Open

- **Four of the five are on the Top side, and they are the board's first Top-side 0201s** (all 71
  existing 0201-size two-pad parts are on the Bottom). This is forced, not preferred: in the band the
  SDRAM crossings live in, the Bottom is U3's moulded body and the Top over U3 is free. It is ordinary
  double-sided reflow for a part this light, but **the assembly house should be told**.
- D3 and D6 stay beyond 5 mm; see above. A Bottom-only alternative reaches 2 / 5.47 / 3.27 — 0.27 mm
  of median worse — if the Top-side parts are ever refused.
- Unchanged from stage 5: U2-5, R15-1 and R13-2 are still the three untied GND pads, and stage 4b is
  still to be routed as one global plan on the freed board.
