# Regulator / charger block: re-placement and loop copper, 2026-09-15

**Status: PLACED AND SAVED 2026-09-15 (user approved), DRC-CLEAN ON EVERY GEOMETRIC RULE, VERIFIED
FROM THE SAVED FILE.** See "Placement record" at the end.

![before and after](regulator_block.png)

Generator `tools/regblock_plan.py` → `tools/regblock_placement.json` (24 moves, one pad-net fix, one
hidden designator) and `tools/regblock_route.json` (27 vias, 102 tracks). The checker is
`tools/block_place.py`. The generator needs the **pre-placement** inputs now
(`git show 328a55e:Zulu_Altrium/tools/route_inputs.json`, passed with `--inputs`) and refuses the
moved board.

## Why the block had to move before its power feeds could be routed

All numbers below come from the saved PcbDoc (`tools/route_inputs.json`) and the two datasheets.

| Finding | Saved board | Requirement |
|---|---|---|
| SC189 LX pin to its inductor | pin 5 faces **away** from the inductor, behind its own VIN/GND/EN row (0.30 mm pin gaps); shortest Bottom routes 8.3 / 20.1 / 13.6 mm | SC189 p21 #2: LX traces as short as possible (2.5 MHz) |
| CIN to VIN (pad edge) | 3.10 / 3.31 / 3.58 mm | p21 #1: as close to VIN and GND as possible |
| COUT GND to IC GND | 4.70 / 6.97 / 8.48 mm | p21 #2: direct return to the GND pin |
| bq24232 IN / OUT / BAT caps | 8.98 / 4.43 / 6.23 mm | SLUS821J 11.1: as close as possible |
| U5/U6/U7 bodies | end to end with 0.30 mm pad gaps; the SOT23-5 body (p23, D 2.80–3.10) runs up to 0.30 mm past the end pads, so they touch at minimum D and overlap 0.30 mm at maximum | parts must not collide |
| R78 pad 1 | **no net** in every saved PcbDoc since 119e15b; the netlist says GND (VCC3V3–LD5–R78–GND). DRC cannot see a netless pad, so LD5 would never light | the netlist |

`tools/place_board.py` shelf-packed the PWR region by part size; the routing readiness review said
"the placement stands" without looking at the regulator loops.

## How the layout was chosen

Three independent layouts, each carrying its own loop copper and passing every gate: **row** (three
cells across the south), **column** (stacked down the west edge), **exits** (arranged around where
the currents enter and leave). Each was attacked by a power-integrity reviewer (SC189 p21 and
Figure 8, bq24232 11.1 and the pin table) and a manufacturing/routability reviewer. A judge chose
**exits** (review scores PI 7 / mfg 6 against 6 / 5 and 6.5 / 5) and repaired it:

- **row** lost on the X2 header: its VU trunk ran 0.103 mm from X2-34…39 for ~12 mm and the CIN
  pads sat 0.088 mm from the header's underside insulator; COUT's return went round the CIN
  (4.8 mm).
- **column** lost on bodies and a 25 mm VU spine along the board edge: R78/R106 over U3's TSOP
  body, C78's GND pad on the X2 insulator, the spine 0.25 mm from the edge and outside the plane
  pullback, and 0.1035 mm from L1's LX pad.
- **exits repairs** (in `regblock_plan.py`'s docstring): R1 COUT off the maximum SOT body (was
  0.002 mm); R2 L3 out from under U3's TSOP body (found by the judge alone); R3 bq24232 VSS pin 8
  grounded directly (it reached ground only through the thermal pad, which the pin table forbids);
  R4 a 0.14 mm GND spoke 0.093 mm from USB5V0 removed; R5 ILIM out from under C78; R6 a GND via
  0.55 mm from the thermal pad; R7 fine-pitch necks.
- Added afterwards (main session): **R8** the LD3_K / LD4_K cathode escape vias inside the EN2
  ring are placed now — the judge found those pockets routable only one net at a time and
  order-dependent.

## The layout

Everything is on Bottom except one 0.30 mm GND jumper on L4-SIG. The three SC189 cells use one
Figure 8 cell rotated to three orientations around a single VU node at (10.25, 10.50):

- **Cell:** CIN over pins 1–2, inductor over pins 5–4, COUT beside pins 3–4, each at the 0.30 mm
  land minimum. LX is one straight 0.80 mm track (2.01 mm). VIN is 0.80 mm and GND 0.50 mm. The
  sense track (0.40 mm) runs from pin 4 to the COUT pad, away from LX. A 0.50 mm GND channel under
  the body carries three plane vias from pin 2 to COUT GND, and a fourth sits at COUT.
- **Placement:**
  - U6 (1V8): rotated 270, inductor on the west edge.
  - U5 (3V3): rotated 180, inductor north.
  - U7 (1V0): rotated 90, inductor east, output facing U1.
- **bq24232:** U8 rotated 90 at (11.50, 5.90).
  - C78 VU pad over OUT 10/11 with its GND pad over the VSS corner; C151 under BAT 2/3;
    C150 beside IN 13.
  - R102–R106 at their pins.
  - GND: 8 vias on the thermal-pad island, and pin 8 has its own direct path.

| | LX-L | VIN-CIN | GND-CIN | L-COUT | COUT GND-IC GND | sense | GND vias |
|---|---|---|---|---|---|---|---|
| saved U5/U6/U7 | 3.44 / 4.03 / 4.72 | 3.10 / 3.31 / 3.58 | 2.90 | 2.87 / 2.58 / 10.32 | 4.70 / 6.97 / 8.48 | 3.72 / 4.37 / 5.09 | 0 |
| proposed (each) | 0.30 | 0.30 | 0.30 | 0.31 | 1.45 | 0.30 | 4 |

(pad-edge gaps, mm). bq24232: IN / OUT / BAT caps 0.30 mm each; R102–R106 0.30–2.05 mm.

## The gates (all pass on the committed files)

```
python tools/block_place.py tools/regblock_placement.json --plan tools/regblock_route.json --write-inputs M.json
python tools/route_emit.py tools/regblock_route.json RegLoops --inputs M.json
python tools/route_foreclosure.py --inputs M.json tools/regblock_route.json
python tools/block_place.py tools/regblock_placement.json --plan tools/regblock_route.json --write-inputs G.json --merge-plan
python tools/route_reach.py --inputs G.json
```

1. Legal placement: land gaps ≥ 0.30, edge ≥ 0.30, SOT23-5 max bodies. All 31 datasheet loop
   connections are made.
2. Geometry and connectivity check clean.
3. No U1 escape and no nearby pad foreclosed.
4. Merged-inputs file written: the plan copper added as board copper.
5. **323 / 323** un-routed connections still routable, the block's own power nets included.

The judge's extra checks (`work/judge.py` in the run): no maximum-tolerance body within 0.10 mm of
another body or 0.15 mm of a foreign pad, including U3's TSOP body and the X2 underside insulator.
Nothing in the plan is under 0.12 mm to foreign copper. GND tracks ≤ 0.50 mm.

Exits, at real widths, from a width-aware raster:

| Net | Route | Max width (mm) |
|---|---|---|
| VU | → X2-22 | 1.588 (1.225 on Bottom only) |
| USB5V0 | ← X1-1 | 0.725 |
| VBATT | ← X4-1 | 1.00 |
| VCC3V3 / VCC1V8 / VCC1V0 | → X2-17/18/19 | 1.588 |
| VCC1V0 | → U1, via L3+L4 in parallel through the north band | 1.588 on L3 |

## Open decisions and residual risks

- **Thermal: via-in-pad under U8's thermal pad.** The no-via-in-pad rule leaves the nearest plane via
  land 0.55 mm from the pad; the charger dissipates 0.36–0.61 W. JLC's resin-filled, capped
  via-in-pad (e.g. 4 × 0.20/0.35) would restore the datasheet's thermal model. This is the user's call.
- L2's pads are 0.302 mm from the west edge, inside the 0.508 mm plane pullback. Keep panel rails
  and V-scores off x = 0 for y 6.5–11.5.
- C150's GND joins U8's copper through its plane vias plus an L4 jumper. Electrically that is the
  plane return; it is not a surface trace.
- U5/U6/U7 at three rotations on Bottom: check the CPL rotations, and put pin-1 marks and the Z/L/A
  variants on the assembly drawing. The 0.30 mm gaps leave no room for designators.
- Later stages: keep non-GND vias ≥ 1 mm from the three LX nodes (U7/L3 sit under X3's SD contacts,
  shielded by L2/L5).

## Placement record, 2026-09-15

1. **`PlaceRegBlock`**. The script reported "24 parts on their targets and 1 pad net(s) set". After
   saving, every one of the 829 pads read back from the file at its planned position (block pads
   within 0.0001 mm), and no track or via changed. **R78-1 still read net −1 in Pads6.**
2. **The R78-1 net.** A probe (`ProbeR78Net`, `tools/ZuluProbe.pas`) showed the live board had
   R78-1 on GND, with a single GND net object and R78-1 pointing at it. So the value was right in
   memory but was not being saved.
   - `JoinR78ToGndNet` then added `G.AddPCBObject(P)` after `P.Net := G`. The document turned dirty,
     and after saving, **Pads6 wrote GND**.
   - `P.Net := G` alone had failed three times: `TieR78ToGnd` (119e15b), Altium's Import Changes
     ECO (0a7bdda) and the first `BlkPadNet`.
   - `BlkPadNet` in `tools/block_place.py` now calls `AddPCBObject`.
3. **DRC after the move** (453 un-routed, +1): the extra connection is R78-1, now correctly
   unrouted on GND. There was one new Silk To Solder Mask violation, U5's designator on L1-1.
   `hide_designators: ["U5"]` was added and `PlaceRegBlock` re-run: the moves were skipped as
   already on target, and the designator was hidden.
4. **Loop copper.** `route_emit`, the loop-join check, `route_foreclosure` and `route_reach` were
   re-run against the saved board: clean; 31/31; none foreclosed; 323/323. **`PlaceRegLoops`**
   reported "removed 0, added 27 vias and 102 tracks".
5. **DRC** (`docs/drc_regblock_2026-09-15.drc`): **479 = 400 un-routed + 2 waived X2-20 thermals +
   77 net antennae.**
   - Zero on all three Clearance rules, Short-Circuit, all seven Width rules, the via plane
     connect, hole size, hole-to-hole, mask sliver, Silk To Solder Mask, Silk to Silk and height.
   - Un-routed fell 453 → 400. The block nets left un-routed are only the far feeds (VU → X2-22,
     USB5V0 ← X1, VBATT ← X4, the LED nets and the rails' distribution).
   - Antennae went 75 → 77: the LD3_K / LD4_K escape vias, awaiting their LED routes.
6. **Saved file.** Vias 181 → 208 and tracks 825 → 927: exactly the plan's 27 vias (all 0.20/0.35)
   and 102 tracks, nothing lost. Pads are unchanged since step 1, R78-1 is GND, and U5 has
   `NAMEON=FALSE`. `verify_widths.py` and `verify_stack.py` PASS.

`RestoreRegBlock` would undo the moves, leaving R78-1 on GND and the designator hidden;
`RemoveRegLoops` deletes the 129 loop primitives.

### Independent verification (two verifiers, their own parsers, read-only)

**Confirmed from the saved PcbDoc against git 328a55e:**
- All 72 block pads sit within 0.000064 mm of target; sizes swap exactly on the 90/270 parts.
- No other pad changed in any byte of its geometry. The only pad-net change is R78-1: −1 → GND.
- Vias6 and Tracks6 hold the old records byte-identical plus exactly the plan's 27 vias and 102
  tracks. The moved parts' own mechanical-layer lines moved with them.
- Components6 rotations change by exactly each move's turn, and U5 has `NAMEON` FALSE.

**Confirmed by measurement:**
- LX: one 0.80 mm × 2.014 mm track per regulator; nothing but its own GND within 0.48 mm; the
  nearest non-GND via 4.2 mm away.
- VIN and GND to CIN: 1.74 and 1.60 mm of Bottom copper, no vias.
- COUT GND returns to pin 2 on Bottom copper: 4.30 / 3.95 / 3.95 mm. The table's 1.45 is the pad
  gap.
- bq24232: IN / OUT / BAT caps each by ≤ 1.37 mm of Bottom copper. VSS pin 8 reaches GND vias
  without the thermal pad (1.30 mm).
- No via within 0.8 mm of the edge, and none in the X3 keep-outs.

**Recorded, not changed:**
- **C150's GND** returns through its two plane vias. Its only copper path to U8 is the L4 jumper,
  8.3 mm. The bq24232 is a linear charger, so this is not a switching loop, but it is looser than
  SLUS821J 11.1's "short trace runs to GND".
- **R103 (ILIM) shares C150's GND pad** and vias. The other set resistors have their own vias.
  11.1 bullet 2 prefers low-current grounds kept separate; the error is microvolts.
- Pre-existing, outside the block: **the fan-out's GND via at (51.40, 11.40) is 0.040 mm from
  C111-2's pad**, inside the pad's mask expansion, which risks solder wicking. It is the same net,
  so DRC is silent. It predates route_emit's "no via within 0.09 mm of any SMD pad" check; move it
  before fab.
- ComponentClearance stays out of the batch DRC by the earlier decision (EAGLE courtyards, X2's
  full-board rectangle; `tools/ZuluFixDrc.pas`). The imported outline boxes of C147/C148/C149
  overlap by 0.116 mm. The placement's own check is the 0.30 mm land gap plus maximum bodies.
