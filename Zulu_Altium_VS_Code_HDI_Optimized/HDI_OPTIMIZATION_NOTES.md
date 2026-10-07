# Zulu A7 conservative HDI optimization

## Scope

This is an isolated, same-outline derivative of the fully routed Zulu A7
production board. The production board was not edited.

The optimization is deliberately conservative:

- No components were moved.
- No nets, track widths, layer assignments, keepouts, or board-outline
  geometry were changed.
- Thirteen existing HDI transition sites were replaced by genuine mechanical
  through vias using the existing 0.35 mm land / 0.20 mm drill rule.
- L2-GND and L5-VCC3V3 polygons were repoured in Altium so they clear the new
  through vias.
- `ZULU A7` was added to Top Overlay at X=6.0 mm, Y=20.0 mm using 2.0 mm
  stroke text with a 0.25 mm stroke width.
- X1-MS1 and X1-MS2 were corrected from 0.60 mm round holes to the Molex
  105017-0001 requirement: plated 0.60 mm x 1.30 mm vertical slots.
- A short CHAN12 corridor and its two stacked vias were moved locally to clear
  the corrected X1 slot. Net, width, layers, and total track/via counts remain
  unchanged.
- The `HoleSize_X1` rule permits the 1.30 mm X1 slot length without weakening
  the global hole-size rule, and the X1 designator was moved clear of solder
  mask.

This remains an HDI board. It is not the full placement/layer-function/reroute
redesign that would be required to approach zero buried vias, and it does not
make the design eligible for JLCPCB assembly.

## Files and fingerprints

| Item | SHA-256 |
|---|---|
| Historical production source used for the optimization | `72E9A716E03616D9464C0040A7B1187561E740C551104720DD288EA147B4E30B` |
| Current production `zulu_a7.PcbDoc`, not written by the X1 correction | `181B1A8CC47D591023BFB5E683A1D7FC3F66063C18EC0D94D65964AD3BB25504` |
| Via-only intermediate, before Altium repour | `FB9CE613BED4512F1B3B67D9AB6BFB29A3CFA007ED5AE46BBEAC22C5E7F620C7` |
| Optimized board before the X1 footprint correction | `60294BF7E6B159569DF3BF40E12B51081653BCD40C5434E55782723CB1B5F80B` |
| Final corrected `zulu_a7_hdi_optimized.PcbDoc` | `5E885D522F27F39FE3042062336B2A9D71FBCC85A11B77017C1D22DBD5F929C8` |

The current production board hash was rechecked after the isolated X1
correction and remained `181B...`; only the optimized derivative was written.

## Board and routing invariants

- Outline: 69.85 mm x 25.40 mm, unchanged.
- Layer stack: JLC06161H-3313E, unchanged.
- Modeled signal tracks: 4,196, unchanged.
- Signal tracks: 4,196, unchanged in count. Four CHAN12 endpoints were adjusted
  locally near X1.
- Physical via locations: 1,081, unchanged.
- Via objects: 1,768, unchanged by the X1 correction.
- X1 slot centers: (29.5199, 23.9585) mm and (36.5201, 23.9585) mm.
- X1 slot geometry: plated 0.60 mm x 1.30 mm, vertical.
- Pad centers, pad nets, net classes, keepouts, and outline match the
  pre-correction optimized model.

## Via census

| Via type/span | Production | Optimized | Change |
|---|---:|---:|---:|
| Top-Bottom through | 380 | 393 | +13 |
| Top-L2 microvia | 296 | 291 | -5 |
| L2-L3 microvia | 282 | 278 | -4 |
| L3-L4 buried | 369 | 362 | -7 |
| L4-L5 microvia | 230 | 222 | -8 |
| L5-Bottom microvia | 230 | 222 | -8 |
| Total via objects | 1,787 | 1,768 | -19 |

Laser-microvia records fell from 1,038 to 1,013. Physical HDI sites fell from
701 to 688.

## Converted sites

| Net | X (mm) | Y (mm) |
|---|---:|---:|
| CHAN19 | 53.2 | 23.5 |
| CHAN23 | 36.3 | 7.1 |
| CHAN25 | 47.9 | 2.0 |
| CHAN27 | 38.825 | 4.075 |
| CHAN28 | 16.5 | 6.0 |
| CHAN7 | 49.4 | 13.45 |
| CHAN9 | 49.4 | 12.4 |
| CLK-12M-FT | 61.1 | 13.0 |
| EE-CLK | 24.4 | 20.0 |
| GND | 45.9 | 11.8999 |
| JA1 | 61.35 | 6.2 |
| PMOD-4 | 63.5 | 9.9 |
| TDI | 62.75 | 12.7 |

## Validation

The final saved board passed:

- Altium full Design Rule Check: 0 warnings, 0 rule violations.
- X1-MS1/MS2: exactly two plated 0.60 mm x 1.30 mm vertical slots.
- Fresh NC Drill output: exactly two 0.60 mm G85 slot records, each using a
  0.70 mm route centerline for 1.30 mm overall length.
- Top-Bottom round-hole output: 393 x 0.20 mm vias, 2 x 0.85 mm X1 holes,
  and 58 x 1.016 mm component holes.
- CHAN12 stacked vias: two records at (35.80, 23.35) mm.
- X1 designator: (37.442, 22.250) mm.
- Top Overlay title: one `ZULU A7` record at X=6.0 mm, Y=20.0 mm,
  2.0 mm height, 0.25 mm stroke, and 0 degree rotation.
- Refreshed Top Overlay Gerber: title stroke aperture and coordinates verified.
- Clearance: 0.
- Short-circuit: 0.
- Un-routed net: 0.
- Net antennae: 0.
- Hole size: 0.
- Hole-to-hole clearance: 0.
- Modified polygon: 0.
- Saved-file geometry comparison: 4,196 tracks and 1,768 via objects, with
  no missing or extra objects.
- Stack verification: all V9, V8, legacy, plane, and via-type checks passed.
- Microvia metadata: all 1,013 remaining laser-via records verified.
- Signal connectivity: all 174 routed non-plane signal nets joined.
- GND plane ties: 206/206 SMD pads tied.
- VCC3V3 plane ties: 129/129 SMD pads tied.

The signal-only island checker reports VCC3V3 as split because it does not
model the full-board L5 polygon as routed copper. The independent VCC3V3 plane
tie check is the authoritative result and passes 129/129.

The final reports are:

- `Imported zulu_a7.PrjPcb/Project Outputs for zulu_a7_hdi_optimized/Design Rule Check - zulu_a7_hdi_optimized.html`
- `Imported zulu_a7.PrjPcb/Project Outputs for zulu_a7_hdi_optimized/Design Rule Check - zulu_a7_hdi_optimized.drc`

## Reproduction

1. Start from a byte-identical copy of the production board whose SHA-256 is
   the guarded value above.
2. Run `tools/apply_through_via_optimization.py`.
3. Open `zulu_a7_hdi_optimized.PrjPcb` in Altium Designer.
4. Repour all polygons.
5. Run `tools/AddZuluTitle.pas` with the optimized PcbDoc focused.
6. Run `tools/CorrectX1Slots.pas` procedures `CorrectX1Slots`,
   `ResolveX1SlotClearances`, and `RefineX1SlotClearances` in that order.
7. Run the full Design Rule Check.
8. Require 0 warnings and 0 rule violations, then save the optimized PCB.

The optimizer uses `altium-monkey==2026.6.9` and refuses an input board whose
source hash or planned via-span multiset does not match the verified baseline.

## Release artifacts

Fresh Gerbers and NC Drill files were generated from the final corrected
PcbDoc on 2026-10-07. Altium emits six `RoundHoles` drill files plus a
dedicated plated `SlotHoles` file. `tools/package_fabrication_release.py`
validates the PCB fingerprint, all round-hole drill counts, both X1 G85 slot
records and their geometry, all seven drill-file layer mappings, the exact
23-file flat archive manifest, archive integrity, output freshness, and byte
equality between every archive entry and its source.

- Fabrication archive:
  `fabrication/Zulu_A7_HDI_Optimized_JLCPCB_Fabrication_2026-10-07.zip`
- Archive SHA-256:
  `1112753FB789E04003BBE0A7BBFDBD7F7A5C8B9F2B48B562E930EBC7BEA37353`
- Assembly release: `assembly/`
- Assembly contents: 58 BOM lines, 172 fitted designators
  (32 top / 140 bottom), assembler-neutral notes, and three-page top and
  bottom assembly drawings. The notes carry the final PcbDoc hash and the
  X1 plated-slot seating requirement.

The fabrication archive is for JLCPCB bare-board fabrication after manual HDI
engineering review. The assembly release is intentionally separate because
JLCPCB does not support assembly of this HDI design.

A separate PCBWay release uses the same verified Gerber and NC Drill sources
with PCBWay-specific CAM, stackup, impedance, copper-weight, and HDI
instructions:

- PCBWay fabrication archive:
  `fabrication/Zulu_A7_HDI_Optimized_PCBWay_Fabrication_2026-10-07.zip`
- Archive SHA-256:
  `9B5CB933131FB0BD1DE8451D689593C0A4A30D29499CFEBBE4A8889165FF26F3`

PCBWay must return its proposed manufacturable stack and calculated 90-ohm USB
differential impedance for approval. The PCBWay package does not authorize a
silent substitution of a standard six-layer stack. The superseded 2026-10-04
archives contain the old round X1 rear holes and must not be fabricated.
