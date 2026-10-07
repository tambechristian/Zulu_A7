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
- Later on 2026-10-07 the MS1/MS2 lands and slot clearances were brought to
  PCBWay's "normal" class, matching the production board's fix. CHAN12 was
  re-routed around the slots. See "X1 lands and clearances" below.
- Also on 2026-10-07, at the user's request, X2's supply pins were re-ordered:
  17 GND, 18 VCC3V3, 19 VCC1V8, 20 VCC1V0 (was 17 VCC3V3, 18 VCC1V8,
  19 VCC1V0, 20 GND). See "X2 power pins" below.

This remains an HDI board. It is not the full placement/layer-function/reroute
redesign that would be required to approach zero buried vias, and it does not
make the design eligible for JLCPCB assembly.

## Files and fingerprints

| Item | SHA-256 |
|---|---|
| Historical production source used for the optimization | `72E9A716E03616D9464C0040A7B1187561E740C551104720DD288EA147B4E30B` |
| Production `zulu_a7.PcbDoc` when the X1 slot correction was made here, not written by it | `181B1A8CC47D591023BFB5E683A1D7FC3F66063C18EC0D94D65964AD3BB25504` |
| Production `zulu_a7.PcbDoc` after its own X1 slot and land fixes (never written from this copy) | `4F73E1A215A21D19623C0956719072AEAA8C6B258501A21DE8923BFFF705F688` |
| Production `zulu_a7.PcbDoc` now, after the X2 power-pin re-order | `517B553E53D2148F2704600BB90345A12782C01B58199DC36E62376971A67054` |
| Via-only intermediate, before Altium repour | `FB9CE613BED4512F1B3B67D9AB6BFB29A3CFA007ED5AE46BBEAC22C5E7F620C7` |
| Optimized board, 2026-10-04 (History `~(2)`) | `60294BF7E6B159569DF3BF40E12B51081653BCD40C5434E55782723CB1B5F80B` |
| Board just before the X1 slot correction (History `~(5)`, 2026-10-06) | `52E8438F649E04845077D82DEA01D3EB8FE0A85B03D1F2F668040158DBF87F8A` |
| After the X1 slot correction, round 0.90 mm lands (History `~(8)`); superseded | `5E885D522F27F39FE3042062336B2A9D71FBCC85A11B77017C1D22DBD5F929C8` |
| After the X1 land fix (slots plus PCBWay lands and clearances); superseded | `0CFFBF05E98EB0DCA85336350EE6244E748E4679B6C28E9545B0198F8F05D6C5` |
| Final `zulu_a7_hdi_optimized.PcbDoc`, after the X2 power-pin re-order | `71E75C10890AF834F98ECEB9E10981AA1AD6301A51087FBB7A328B4E49486D6E` |

The production board hash was rechecked after the isolated X1 slot correction
and was still `181B...`; only the optimized derivative was written. The
production board has since had its own fixes (`4F73...`, then `517B...`).

`~(2)` is not the board immediately before the slot correction. Between them,
History `~(3)` (2026-10-05) moved the X1 designator, and `~(4)` (2026-10-06)
moved the X3, U1, JP3 and JP4 designators; autoposition was cleared on all
five. `~(5)` is geometrically equal to `~(4)`. The slot correction first
appears in `~(6)` (2026-10-07 04:27).

## Board and routing invariants

- Outline: 69.85 mm x 25.40 mm, unchanged.
- Layer stack: JLC06161H-3313E, unchanged.
- Signal tracks: 4,200 (4,828 track objects in all). The land fix changed four
  CHAN12 tracks and added four; the slot correction before it only moved CHAN12
  endpoints.
- Physical via locations: 1,081, unchanged.
- Via objects: 1,768, unchanged by the X1 correction.
- X1 slot centers: (29.5199, 23.9585) mm and (36.5201, 23.9585) mm.
- X1 slot geometry: plated 0.60 mm x 1.30 mm, vertical.
- X1-MS1/MS2 lands: 1.11 x 1.81 mm oblong on Top and Bottom, 0.90 x 1.60 mm on
  L2-L5.
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
- CHAN12 stacked vias: two records at (37.45, 24.40) mm (at (35.80, 23.35) mm
  after the slot correction, before the land fix).
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
  no missing or extra objects (4,200 tracks after the land fix).
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
   This file was reconstructed after the board was saved: run on History
   `~(6)` it reproduces the saved geometry, but it is not byte-for-byte the code
   that ran.
7. Run the full Design Rule Check.
8. Require 0 warnings and 0 rule violations, then save the optimized PCB.
9. Apply the land fix: `tools/HdiX1Pads.pas` (`HdiX1Canary`, then `FixHdiX1`,
   then `AddX1Rules`) and `tools/HdiX1Rules.pas` (`FixX1RuleScope`), each
   loaded as its own `.PrjScr`. Then save, close and reopen the board, repour
   all polygons, run the DRC and save again.
10. Re-order X2's supply pins: run `Zulu_Altium_VS_Code/tools/x2_power_pins.py`
    on this copy's `zulu_a7_2.SchDoc`, then `tools/X2PowerPins.pas`
    (`X2PinsCanary`, then `FixX2PowerPins`) on the board. Save, close and
    reopen, repour, run the DRC, import the X2 NOTE change only (untick the
    ten net-class removals and the USB pair), and save again.

The optimizer uses `altium-monkey==2026.6.9` and refuses an input board whose
source hash or planned via-span multiset does not match the verified baseline.

## X1 lands and clearances (2026-10-07, later)

The slot correction above left two problems: no copper ring at the slot ends
(the 0.90 mm round lands were narrower than the 1.30 mm slot), and copper less
than 0.15 mm from the slot walls. Fabrication is at PCBWay, so the fix targets
PCBWay's published "normal" class. It is the same fix as the production board's
(`Zulu_Altium_VS_Code/docs/x1_slot_fix.md`), re-measured on this copy.

Changes, all on X1 and CHAN12:

- **MS1/MS2 padstack:** top/middle/bottom mode. Top and Bottom are 1.11 x 1.81
  mm oblong (0.255 mm ring; PCBWay asks for 0.254 mm on outer layers). L2-L5
  are 0.90 x 1.60 mm oblong (0.15 mm ring). Mask openings are 1.21 x 1.91 mm.
- **CHAN12 re-route:** the Bottom run stops at x 27.95, rises west of MS1 to
  (28.72, 23.92) and (28.72, 24.62), crosses north of both slots at y 25.02 and
  drops to the stacked L4-L5 / L5-Bottom microvias, which moved from
  (35.80, 23.35) to (37.45, 24.40). On L4 the route goes straight down from the
  vias to the existing run at (37.45, 23.15).
- **Rules:** `AnnularRing_X1` (`InComponent('X1')`, minimum 0.14 mm) and
  `Clearance_X1MS_L5Plane` (`InComponent('X1')` to
  `InNamedPolygon('L5_VCC3V3_PLANE')`, 0.10 mm), both priority 1.
- **Planes:** all polygons repoured. Because the plane rule is scoped to all of
  X1, the L5 voids around X1's MH1/MH2 holes also grew by 0.010 mm (plane to
  hole wall 0.390 -> 0.400 mm). Both planes are still one island each, and every GND and VCC3V3 via and THT pad
  still connects.
- **Library:** MOLEX-105017-0001 in `zulu_a7.PcbLib` got the same MS1/MS2
  padstack (`tools/HdiX1Lib.pas`). It is the only footprint that changed, and
  its MS1/MS2 now equal X1 on the board.

Measured from the released Gerbers and drill files:

| Check | Result | PCBWay normal |
|---|---|---|
| MS ring, Top/Bottom | 0.255 mm | >= 0.254 |
| Slot wall to other-net copper, inner | 0.2477 mm (CHAN13 on L4); L5 plane 0.2499 mm; L3 0.3608 mm | >= 0.203 |
| Slot wall to other-net copper, outer | Bottom 0.3608 mm (FPGA-TCK); Top 0.4034 mm (CHAN8) | >= 0.152 |
| CHAN12 microvia hole to slot | 0.559 mm | via >= 0.30, PTH >= 0.45 |
| CHAN12 copper to board edge | 0.342 mm | >= 0.25 |

Output differences against the slot-correction release: the MS flashes on all
six copper layers and both masks, the CHAN12 tracks on Bottom and L4, the moved
via on L4, L5 and Bottom (TX9/TX10), and plane fills on L2 and L5 near X1 and
around MH1/MH2. One extra L5 vertex at (45.061, 1.878) lies 0.05 um off its
neighbours' line, a repour artefact. Silkscreen, paste, profile, the slot file
and the other drill files are unchanged.

Altium DRC on the saved board, 2026-10-07 12:15: 0 warnings, 0 rule violations.

## X2 power pins (2026-10-07, later)

At the user's request the four supply pins at the end of X2's top row were
re-ordered; pin 16 (CHAN13) and the rest of X2 are unchanged. It is the same
change as on the production board (`Zulu_Altium_VS_Code/docs/x2_power_pins.md`).

| Pin | x (mm) | Before | After |
|---:|---:|---|---|
| 17 | 8.89 | VCC3V3 | GND |
| 18 | 6.35 | VCC1V8 | VCC3V3 |
| 19 | 3.81 | VCC1V0 | VCC1V8 |
| 20 | 1.27 | GND | VCC1V0 |

- **Schematic:** `zulu_a7_2.SchDoc` was edited by the production copy's
  `tools/x2_power_pins.py`. This sheet was byte-identical to production's, and
  after the edit its streams are still identical. The four gate copies moved
  with their wires and labels. All 41 copies were renumbered, and the X2 NOTE
  and the text frame were reworded.
- **Board:** `tools/X2PowerPins.pas` re-netted the four pads. It also moved the
  VCC1V8 L3 stub from pin 18 to pin 19, and extended the VCC1V0 Bottom run at
  y 23.05 from x 3.81 to 1.27, with its stub moved to pin 20. GND and VCC3V3
  reach pins 17 and 18 through the repoured L2 and L5 planes.
- **Sync:** the ECO preview listed no net changes. Only the X2 NOTE parameter
  was imported.
- **Outputs:** drill files are byte-identical to the previous release. The
  only copper changes are the VCC1V8 stub (G2), the VCC1V0 run and stub (GBL),
  and the L2/L5 fills inside x -0.5..16.5, y 21.5..25.5. Every other layer has
  identical geometry.

Altium DRC on the saved board, 2026-10-07 14:34: 0 warnings, 0 rule violations.

## Release artifacts

Fresh Gerbers and NC Drill files were generated from the final corrected
PcbDoc on 2026-10-07 at 14:35, after the X2 power-pin re-order. Altium emits six `RoundHoles` drill files plus a
dedicated plated `SlotHoles` file. `tools/package_fabrication_release.py`
validates the PCB fingerprint, all round-hole drill counts, both X1 G85 slot
records and their geometry, all seven drill-file layer mappings, the exact
23-file flat archive manifest, archive integrity, output freshness, and byte
equality between every archive entry and its source.

- Fabrication archive:
  `fabrication/Zulu_A7_HDI_Optimized_JLCPCB_Fabrication_2026-10-07.zip`
- Archive SHA-256:
  `9C3E89E2AD6A9738DC78A2C54CCAAE3EFBEAD70E2E7B74790692409B8D3038D6`
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
  `B679B6A3C824442F336A5351E2B9B3EA1440B566CE6C298C7AC5B01D2A965B71`

PCBWay must return its proposed manufacturable stack and calculated 90-ohm USB
differential impedance for approval. The PCBWay package does not authorize a
silent substitution of a standard six-layer stack. The superseded 2026-10-04
archives contain the old round X1 rear holes and must not be fabricated. The
earlier 2026-10-07 archives (`1112753F...` and `9B5CB933...`) have the slots but
not the land fix, and must not be fabricated either. The land-fix archives
(`C73C05F1...` and `CB9F6DB1...`) have the old X2 pin order and are superseded
too.
