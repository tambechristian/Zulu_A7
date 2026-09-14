# DRC RESULT — 2026-09-11, FINAL: 605, and both remaining classes are accounted for

| rule | count | |
|---|---|---|
| Un-Routed Net Constraint | **603** | airwires — nothing is routed yet |
| Power Plane Connect (starved thermal) | **2** | X2-20 on both planes; cleared by the plane pullback |
| **Silk To Solder Mask** | **0** | was 37 |
| everything else | **0** | clearance, short-circuit, all three width rules, hole size, hole-to-hole, mask sliver, silk-to-silk, net antennae, height, modified polygon, routing topology |
| Warnings | **0** | |

**2026-09-14, re-run after the power-rail Width rules (`docs/pwr_rail_widths.md`): still 605,
same breakdown.** There are now SIX Width rules (VCC3V3, U8, VCC1V0, PWR_SWITCH, PWR_RAILS,
Width), all at 0; a 13-track probe placed on purpose produced exactly the 7 violations the
per-layer floors predict and was removed again.

**This is as clean as the board gets before routing.** The only non-airwire item left is the
X2-20 pair, and it is gated on question 1 of `board/JLCPCB-DFM-ENQUIRY-2.md`.

### How the silk went 37 -> 0

The 37 were never 37 objects. They were **sixteen designators**, each printed on a *different*
component's pads, because every one had been left 2–12 mm from the part it names — "U3" was
11.8 mm from U3, sitting on R97 and R98. The silkscreen was **mislabelling the board**; the DRC
was only the symptom.

1. `AutoPositionOrphans` — `ChangeNameAutoposition(eAutoPos_TopCenter)` on all sixteen put them
   back on their own parts. **37 → 28.**
2. `HideCrowdedDesignators` — the 13 that then had nowhere to go came off the silkscreen, on the
   user's instruction. **28 → 0.** Verified in the saved file: all 13 read `NAMEON=FALSE`.

The 13 are LD0, X4, U3, L1, L2, L3, U6, U7, U8, U10, J1, U4, Q1. **They are hidden, not deleted**
— every one still appears in the netlist, the BOM and the pick-and-place, and the assembly
drawing is where a human reads them, which was already true of the 145 chip passives
`HideChipDesignators` took earlier. Hiding was the only option left: 22 of the 28 were hard
collisions rather than near-misses, so relaxing the 0.254 mm rule would have cleared nothing, and
the text was already at 0.8 mm, JLCPCB's minimum silkscreen height, so there was no shrink room.

### A trap worth remembering about Altium text

Two facts out of `Texts6`, both of which defeat the obvious offline model: the designator font is
**Arial**, not Altium's stroke font, so glyph widths differ per character; and **byte 35 is a
mirror flag**, set on every Bottom Overlay string, so a bottom-side designator draws **leftward**
from its anchor. `tools/fix_silk.py` records this, and records that its own box model is *not*
calibrated — `place_board.rects()` returns one merged rectangle per SMD component rather than one
per pad, which is right for component clearance and wrong for silk.

---

# DRC RESULT — 2026-09-11, after the pre-routing setup pass (superseded by the block above)

**642 violations, and 640 of them are not defects. Every actionable class is zero.**

| rule | count | |
|---|---|---|
| Un-Routed Net Constraint | **603** | airwires — nothing is routed yet |
| Silk To Solder Mask (0.254 mm, IsPad) | **37** | designator *text* over a neighbouring pad's mask opening |
| Power Plane Connect (starved thermal) | **2** | both on X2-20, and both already diagnosed |
| Clearance 0.09 mm (All,All) | 0 | |
| Short-Circuit | 0 | |
| Width — generic, PWR_SWITCH, PWR_RAILS | 0, 0, 0 | all three |
| Hole Size / Hole To Hole | 0 / 0 | |
| Minimum Solder Mask Sliver | 0 | |
| Silk to Silk | 0 | |
| Net Antennae / Height / Modified Polygon / Routing Topology | 0 | |
| **Warnings** | **0** | |

This is the first DRC since the setup pass — four rule edits, the grid change to
0.025 mm, two keep-out fills under X3, seven parts moved west, ten net classes, two
power width rules, the PcbLib strip and `Fanout_BGA` disabled. **None of them
introduced a violation.**

### The two plane violations are verbatim what the readiness review predicted

```
Starved Thermal on L2-GND: Pad X2-20(1.27mm,24.13mm) on Multi-Layer. Blocked 3 out of 4 entries.
Starved Thermal on L5-GND: Pad X2-20(1.27mm,24.13mm) on Multi-Layer. Blocked 3 out of 4 entries.
```

At the current **0.51 mm** plane pullback that pad has 0.7595 mm to two plane edges
against the **0.8068 mm** a 45° relief spoke corner needs. At a **0.25 mm** pullback it
has 1.020 mm and both clear in one edit. That edit is gated on question 1 of
`board/JLCPCB-DFM-ENQUIRY-2.md` — minimum inner copper to board edge — and it is now
**the only thing standing between this board and a fully clean pre-routing DRC.**

### The 37 silk hits are designator text, not silkscreen outlines

The offenders are the *inductor* designators and a handful of others, sitting over
pads that belong to neighbouring parts:

```
Text "L1" (5.551, 11.368) Bottom Overlay  vs  C147-2, C148-1, C150-1
Text "L2" (9.638, 11.368) Bottom Overlay  vs  C149-1, C149-2, C151-1, C151-2
```

plus single hits on U2 (6), X2 (5), L3, JP3, Q1, LD1–LD4, R97, R98, C78, C82.
`ZuluFixDrc.pas` already carries `HideChipDesignators` and `ShrinkVisibleDesignators`;
these are what survived them, because L1/L2/L3 are not chip parts. The fix is to move
or hide these specific designators, not to loosen the rule — 0.254 mm is a real
manufacturing number and silk printed over a mask opening lands on the solderable pad.

---

## MUST FIX BEFORE ROUTING

**1. Three copper-on-copper shorts under the USB receptacle — 3 physical defects, 6 report lines (3 in `short_circuit.txt`, 3 duplicated in `clearance.txt`).**

X1 (MOLEX-105017-0001) has four drilled Multi-Layer pads. MH1 and MH2 are 1.4501 mm round lands on 0.8499 mm holes at board (30.5199, 21.2585) and (35.5199, 21.2585) mm, all on GND, so their copper exists on the Bottom layer. Three bottom-side 0402 lands sit in it: R84-2 (N$LD2A) penetrates MH1 by 0.166 mm, R85-1 (N$BTN) by 0.076 mm, R86-2 (N$BTN) by 0.055 mm on the exact round geometry. These are component lands, not routing — no amount of copper laid later removes them. Two of the three kill the same net.

Move exactly three components on the Bottom layer, rotation 0. Coordinates are the centre of the pad bounding box, which for an R0402 coincides with the component origin:

- R84: (29.550, 20.250) → **(32.550, 20.250) mm** = 1281.4961, 797.2441 mil. Move +3.000 x.
- R85: (31.850, 20.250) → **(37.550, 20.250) mm** = 1478.3465, 797.2441 mil. Move +5.700 x.
- R86: (34.150, 20.250) → **(32.550, 21.450) mm** = 1281.4961, 844.4882 mil. Move **−1.600 x, +1.200 y**.

Nothing else moves. Resulting gap to X1's drilled copper is 0.3051 / 0.3048 / 0.3051 mm rectangle-to-rectangle (0.447 mm for R84 and R85 against the true round land), against a 0.09 mm Clearance rule.

**Correction to the procedure as originally written, and this one matters:** the regeneration command is `python tools/emit_placement.py`, **not** `python tools/place_board.py --emit`. I checked: `--emit` appears exactly once in `tools/place_board.py`, at line 35, inside a stale docstring; the file never reads `sys.argv` and contains no file write at all. `tools/emit_placement.py` exists, imports `place_board`, runs its checks and refuses to write unless clean (lines 303-305). Running the documented command would print `PLACEMENT CLEAN`, regenerate nothing, and leave `tools/ZuluPlacement.pas` holding its current pre-fix table — I read lines 336-338 and they are `Place('R84',1,0.0,'1',28.9000,20.2499)`, `R85 31.2000`, `R86 33.5000`, which are the pad-1 targets of the three shorting positions. After regeneration those become pad-1 targets 31.900/20.2499, 36.900/20.2499 and 31.900/21.4498. Three manual drags in Altium give the identical result.

Also correct the second delta line: R86's move is −1.600 x and +1.200 y. The "+1.600, −1.200" in the original write-up is `verify_copper.py`'s as-built-minus-intended delta, which is the negation. I re-ran `verify_copper.py` just now and it prints `R86 +1.6000 −1.1999`. Following that as a move would land R86 at (35.750, 19.050), where its pad 2 overlaps R83 pad 1 (LED1 against N$BTN) — a brand-new short.

Verification state as of now, run read-only: `python tools/place_board.py` prints `PAIRS CLOSER THAN 0.30 mm: 0` / `PLACEMENT CLEAN`; `python tools/verify_copper.py` prints `components whose copper is more than 0.003 mm from the intended centre: 3` (R85 −5.7000, R84 −3.0000, R86 +1.6000/−1.1999) and `pairs closer than 0.30 mm: 3` / `NOT CLEAN`. The tooling is already repaired at HEAD (df444aa, "The collision check is per PAD now"); only the board is stale. `zulu_a7.PcbDoc` saved 09:13:00 and `ZuluPlacement.pas` 09:12:03, both before `place_board.py` at 09:25:21.

**Conclusions that changed here, and why.** The clearance-class triage proposed adding `MOLEX-105017-0001` to a `THRU` set at `place_board.py` line 152 and re-cutting the SDR region to y1 = 20.40 with R84/R85/R86 reassigned to SDL. Both verifiers refuted this independently and they are right: `grep -n THRU tools/place_board.py` returns one hit, line 185, inside the `lib_holes()` docstring explaining that the hand-maintained set was removed *because* it omitted MOLEX-105017-0001. The edit is unapplicable. More decisively, one verifier simulated the re-cut in memory and it leaves components unplaced in every variant tried (SDR alone → R84/R85/R86 overflow; → SDL → R98 overflows; → UNDER → C38/C40/C41 overflow), so `emit_placement.py` would refuse to write. The premise was also wrong: X1's drilled copper blocks only two ~1.63 mm x-windows of SDR's 10.85 mm, and the repaired packer threads all three parts into the gaps between the shell pads. Do not edit `THRU`, do not re-cut SDR, do not reassign anything.

**2. Strip the EAGLE keepout art off the copper layers — 8 report lines today (`clearance.txt`), plus roughly 64 of the 289 component-clearance lines, plus an unquantified latent routing obstacle.**

`Regions6` in the PcbDoc holds 601 records and exactly one is on a copper layer: layer byte 0x20 (Bottom), keepout flag 0x02, `KEEPOUTRESTRICTIONS=31`, component index 44 = R34, vertices (10.220, 17.790)–(13.420, 20.790) mm. It comes from `zulu_a7.brd` package 742C083, which carries `<rectangle x1="-0.8" y1="-1.5" x2="2.4" y2="1.5" layer="39"/>` — EAGLE layer 39 is tKeepout, a *placement* keepout, which Altium has no concept of, so the Import Wizard turned it into a routing keepout region on the component's copper layer. R34's eight pads (10.370..13.270 × 17.940..20.640 mm) sit 0.150 mm inside it on every side, hence exactly 8 violations.

The same import put 584 keepout **tracks** on Top (76) and Bottom (508) copper across 13 patterns and 143 of 175 components — the other packages' layer-39 outlines, which came in as 2 mil hairlines rather than a filled slab. They raise zero violations today only because nothing is routed and an outline misses its own pads. They do not stand off the land: minimum distance from a part's own pad to its own keepout line is +0.0075 mm on R0201/C0201, +0.0077 on R0402/C0402, and **0.0000 mm** on TSOPII-54 (U3, the SDRAM), SOIC-8_208MIL (U4) and 32X25 — the line cuts its own pads. Board-wide, 456 keepout-segment/foreign-pad pairs sit under the 0.09 mm Clearance rule and 155 physically overlap.

Fix in the library, once: in `Imported zulu_a7.PrjPcb/zulu_a7.PcbLib`, delete the single Top Layer region with `KEEPOUTRESTRICTIONS=31` at (−0.800, −1.500)–(2.400, 1.500) mm in footprint 742C083 (it is the only `KEEPOUTRESTRICTIONS` primitive in all 41 patterns, and R34 is the only 742C083 instance — R1 is 742C043, R4 is 742C163), and delete the 584 Top/Bottom keepout tracks across the 13 patterns that carry them (1X03-NOSILK 4, 32X25 4, C0201 4, C0402 4, C0603 4, C0805 4, DM3AT-SF-PEJM5 4, MOLEX-105017-0001 4, R0201 4, R0402 4, SOIC-8_208MIL 4, TSOPII-54 4, ZULU-DIP37 16, times their instance counts). Then Design > Update PCB From Libraries. If the placement outline is wanted for documentation, move it to Mechanical 11/12 rather than clearing the restriction flag. In the board itself, Find Similar Objects on one keepout track with Keepout = Same, Layer = Any also works.

**Conclusion that changed here.** The component-clearance triage put "disable the ComponentClearance rule" first and this library cleanup last, as an optional durable improvement. Its verifier refuted the ordering and I agree with the verifier: the keepout region is demonstrably live in the DRC — it is 8 of the only 11 clearance violations on the board — so the category is not inert, and disabling the one rule that currently surfaces the family would hide it until a router is in hand. Reverse the order: sweep first, then decide about the rule. The verifier was honest that it could not prove Altium's *interactive router* refuses to cross a keepout track (the batch DRC demonstrably does not pair keepout tracks with pads — 155 physical overlaps, zero reported), and that uncertainty stands; the asymmetry decides it, since deleting costs nothing and 143 of 175 components are affected if they are honoured.

Also correct one number in that triage's supporting argument: R35's clearance to the R34 region was given as 0.0098 mm and is actually **0.14994 mm**. 20.8898 is the solder-mask boundary from `placement_report.txt`, which is inflated by the 0.05 mm mask expansion; R35's real copper bottom is 20.94004 mm. Both verifiers caught this independently, and the report disproves the small number by itself — at 0.0098 mm R35 would be a ninth line in `clearance.txt` and it is not there. There is no hair-thin margin to protect; R34 simply does not need to move.

**3. Add the two Hirose "no conductive traces" keep-outs under X3 — 0 report lines, an omission rather than a violation.**

`docs/footprint_lands.md` lines 228-231 record two hatched zones from note 3 of the DM3D-SF figure that are not pads and are not in the footprint: (a) 8.500 × 2.000 mm centred at (−0.650, +0.525) and (b) 2.500 × 2.000 mm centred at (−0.700, +4.725) in the footprint frame. X3 is placed rotation 90 with its origin at (8.800, 12.475) mm — I derived that from pad 8 at (14.150, 7.975) and pad G1 at (14.025, 6.775) in the DRC, and cross-checked it against `placement_report.txt` line 3 (`X3|Top Layer|90|…|5570866|6171220`, pad 1 at 14.150, 15.675 mm), which puts the eight contacts on a 1.1 mm pitch along x = 14.150, the correct microSD pitch. In board coordinates the zones are therefore:

- zone (a): x **7.275..9.275**, y **7.575..16.075** mm (2.000 wide × 8.500 tall, centre 8.275, 11.825)
- zone (b): x **3.075..5.075**, y **10.525..13.025** mm (2.000 × 2.500, centre 4.075, 11.775)

Place these as route keep-outs on all layers before routing, or the router will lay copper through them. Both fall inside X3's own footprint extent (2.525..15.075 × 6.075..18.925 mm), which is a consistency check on the transform, but the transform is mine and worth eyeballing once in the PCB editor.

## DEFER UNTIL AFTER ROUTING

**Silkscreen: 1100 lines — 724 `silk_to_mask` plus 376 `silk_to_silk`. One cause, not a defect, and routing provably cannot change it.**

Every one of the 724 is Pad-vs-Text and every one of the 376 is Text-vs-Text; there are zero tracks and zero arcs on layers 33/34, so the only objects on either overlay are 350 designator and comment strings. All 175 components carry `NAMEON=TRUE`, `COMMENTON=FALSE`, `NAMEAUTOPOSITION=1`, and every one of the 350 overlay strings is at Altium's stock 60 mil height / 10 mil stroke. A two-character designator occupies 109.97 mil — measured from four independent near-miss pairs — against a 47.24 mil 0201 shelf pitch. The silk-to-mask rule's scope is `(IsPad),(All)`, so vias are out of scope and tracks have no mask opening: routing cannot add a line to that class. Silk-to-silk operands are both overlay text, and routing does not move components. The count only changes if a part moves or if the mechanical outlines get mapped into the overlay.

Do the silkscreen pass immediately before Gerber output, in this order:

1. **Settle the overlay mapping first**, or the work is done twice. The footprint outlines are not on the overlays — they are on Mechanical 3 (217 tracks, 6 arcs, 228 regions), Mechanical 4 (120, 228), Mechanical 7 (128, 11) and Mechanical 8 (150). Hide all the designators and the silkscreen Gerber is empty. No OutJob exists in the project yet, so nobody has decided what feeds the silk layer.
2. **Hide the designators on the 145 chip passives** (all C0201/R0201/C0402/R0402/C0603/IND0603/LED0603/C0805 parts). This removes 370 of the 376 silk-to-silk pairs and most of the 724 silk-to-mask ones. Set `NameOn := False`, or untick Designator > Show for that selection.
3. **Then** shrink the survivors to 31.5 mil height / 6 mil stroke (JLCPCB's floor).
4. Hand-place the stragglers: C139 (17 hits), C86 / LD1 / C150 (12 each), C148 / LD0 / LD2 / C151 (11 each), L5 / C6 / C85 (10 each); and of the six silk-to-silk survivors, U5/U6, U6/U7, U7/U8, L1/Q2, JP3/R4, and U$3/U$4 — the last being the Creative Commons marks parked off the board at y = −5.02 mm, which can simply be waived or deleted.
5. Leave `COMMENTON=FALSE`. Comment strings average 1.84× designator length and run to 33 characters.
6. Do not relax the 10 mil rule.

**Conclusion that changed here.** The silk-to-mask triage put shrinking first and hiding last, as a reluctant concession. Its verifier modelled the shrink against real pad geometry (a model that reproduces all 724 reported clearances to a median error of 0.000 mil) and found that 31.5 mil / 6 mil clears only **half** the class — 363 of 724 survive, 202 of them still hard collisions, and 298 of the survivors still overlap a pad in x, which no legal font size fixes. Hiding is the load-bearing step, not the fallback. The verifier's reasoning is stronger because it is a measured sweep rather than a linear extrapolation, so it wins.

One thing you may want to do **now** rather than later: step 2 is position-independent (a per-component boolean that survives any later move) and would strip about 1100 of the 2013 lines out of every DRC report you read while routing. The zero-risk alternative is to untick Silk to Silk and Silk to Solder Mask in the batch DRC for the duration of routing.

**Component Clearance: about 225 lines remaining after the keepout sweep, out of 289.**

The rule is `GAP=10mil`, `COLLISIONCHECKMODE=3`, `LAYERKIND=SameLayer`. Mode 3 reduces each component to one axis-aligned rectangle — the union of the bounding rectangle of every child primitive on every layer — and tests Euclidean rectangle distance. That was reproduced exactly: 289 predicted, 0 missing, 0 extra. The rectangle is far bigger than the land because Altium's `Pad.BoundingRectangle` adds the 0.05 mm mask expansion per side on SMD pads and the 0.504 mm plane anti-pad on through-hole pads (C100's real land 39.800..42.600 mm reports as 39.750..42.650; X2's 0.508..60.452 reports as 0.004..60.956, i.e. the whole 60.96 × 25.40 mm card, which is why X2 alone accounts for 29 hits against every top-side part but J1). With a 0.30 mm design pitch, two SMD parts present to Altium as 0.200 mm = 7.87 mil apart; 163 of the 289 pairs sit at exactly that design minimum. The class cannot be satisfied by moving anything: clearing 10 mil would need land-to-land gaps of 1.25 mm (R0201), 1.38 (C0402), 2.13 (CPG236), 2.69 (Molex micro-USB) on a 69.85 × 25.40 mm card with 175 parts. `GAP=0mil` still leaves 178 of the 289, and Full Check does not help either.

So after the keepout sweep and the R84/R85/R86 move, re-run the DRC, confirm the keepout-driven subset is gone, and then disable the rule — set `ENABLED=FALSE` on the `ComponentClearance` record in `Rules6`, or drop it from `RULESETTOCHECK` in Design Rule Checker Options6. Do not move a single component for it. Every one of the 289 pairs passes the real test: `place_board.py`'s 0.30 mm land-to-land minimum, 3.3× the 0.09 mm electrical clearance rule.

Expect the R86 move to add a pair here: R84 and R86 end up same-x, 47.24 mil apart in y, geometrically identical to R80/R84 today, which `component_clearance.txt` line 271 already reports as a collision. The original short-circuit triage claimed this pair "passes the 10 mil Component Clearance by 1.8 mil"; that is wrong and the verifier is right — it will not pass, because the rule measures inflated bounding rectangles, not lands. It is not a reason to change the fix.

**X3 solder-mask margin (optional, at the rules pass).** Add a scoped SolderMaskExpansion of 0.04 mm on X3 — query `InComponent('X3')`, alongside the 0.07 mm bq24232 rule already queued in `docs/component_validation.md` line 168. That takes the X3-8/X3-G1 dam from 0.099898 mm to 0.119898 mm, a real 20% margin. Use the plain `InComponent` form; `InPad('8')` as originally proposed is not an Altium query keyword. The bq24232 rule is safe to add in the same pass — VQFN16-3X3-RGT's tightest pair has a 0.259842 mm copper gap, so 0.07 mm expansion leaves 0.119842 mm.

## NO ACTION

**605 un-routed connections.** Correct and expected, and the number is a positive result rather than noise. Altium reports one violation per missing connection in each net's spanning tree, so with nothing routed the count is sum over nets of (pads − 1). `zulu_a7.NET` has 179 nets and 795 pad entries, giving 616. GND is short by 11 because 12 of its 211 pads are already joined by copper that exists: ten drilled pads punching through both GND planes (X2-1, X2-20, X2-21, J1-5, J1-11, JP3-3, X1-MH1, X1-MH2, X1-MS1, X1-MS2) plus two SMD shell pads that physically sit on top of drilled ones (X1-MP1 over MS1, X1-MP4 over MS2). 616 − 11 = 605, exactly. A union-find over the 199 GND edges gives five components each containing exactly one of those representatives, which is the structural proof. One verifier went further and parsed Pads6/Nets6 directly out of the PcbDoc: 834 pads, 795 with a net, and the pad→net map matches `zulu_a7.NET` with zero mismatches on all 179 nets. The 39 netless pads are genuinely unconnected (eight unbrought-out CPG236 transceiver balls, unused FT2232H pins, U3-40, U10-6/7, X1-4, X3-A/B, X4-MP1/MP2). Route the board and this goes to zero.

**2 isolated-copper (dead copper) items on the GND planes.** 193.315 sq mil = 0.125 sq mm of floating copper in a board corner, on a buried plane, one per plane. Waive it. It is not cured by routing — a 30 mil corner cannot take a stitch via — but it is harmless. The mechanism, as corrected by the verifier: the split-plane polygons (`Polygons6`, two records, `POLYGONTYPE=Split Plane`, NET=78=GND) run 20.0968 mil in from a 2750 × 1000 mil outline, each X2 pad centre is 29.9032 mil from that edge, and an unconnected through-hole pad's void is hole/2 + PlaneClearance = 20 + 9.8425 = 29.8425 mil — so the plane is squeezed to a 1.54 µm neck at all 40 X2 pads on both planes, which Altium's chorded circles close. That sounds alarming and is not: adjacent X2 pads are 100 mil apart, leaving a 40.315 mil channel of plane copper running the full board height, so the strip outboard of the connector stays attached regardless. Only the bottom-left corner strands, at X2-40 (ANALOG-IO1, plain 29.8425 mil void); the top-left corner at X2-20 is GND and its 50 mil relief void swallows the corner entirely. If you want it gone, the pullback must satisfy (50 − p)·√2 ≤ 29.8425, i.e. **p ≥ 28.898 mil — 30 mil works, 25 mil does not** — and because the boundary is stored as polygon vertices, the edit is the four VX/VY pairs in the two `Polygons6` records as well as `PLANE1PULLBACK`/`PLANE2PULLBACK` and the two `V9_STACK_LAYERn_PULLBACKDISTANCE` keys. Cost: both GND planes retreat 0.254 mm further from the edge all the way round. "Remove Dead Copper" is not available on a split plane. The original triage's "0.09% area match" was two compensating errors; the honest agreement is 0.7%, and the corner's identity is reconstructed, not observed.

**2 starved thermals on X2-20.** Not a defect, and not an unrouted artefact either — a permanent, benign geometric condition. X2-20 is the top-left corner pin of the 40-pin header; its 60 mil pad edge lands 20.000 mil from the outline while both plane polygons are pulled back 20.0968 mil, so the pad sits 2.46 µm outside the plane on both its left and top sides, blocking three of four 45-degree spokes on each plane. The spoke angle and Altium's ">half blocked" reporting threshold are both pinned by the board itself: X2-1 and X2-21 each lose two of four and neither is reported, which orthogonal spokes could not produce. This is not recoverable by tuning — the relief boundary sits at pad_edge − 20 mil expansion = exactly the board outline, and the verifier closed the last escape hatch by finding four free 40 mil-wide outline tracks on each internal plane (`Tracks6`, layers 39 and 40, net 65535) that void plane copper to exactly 20.000 mil inboard regardless of what the polygon does. Electrically it is fine: the surviving spoke is 0.25 mm × 17.5 µm ≈ 0.98 mΩ, two in parallel = 0.49 mΩ, 0.24 mV at the board's 495 mA input cap, and `unrouted.txt` shows Altium's own connectivity engine already counts X2-20 as connected to both planes. Waive it and record why. If you want a clean log instead, add one rule above the default PlaneConnect scoped to `InComponent('X2') and InNet('GND')` with `PLANECONNECTSTYLE = Direct`, at the cost of making those three pins hard to rework.

**1 mask sliver, X3-8 to X3-G1.** A 102 nanometre shortfall — 3.932992 mil against 3.937008 mil. Hirose's own recommended pattern puts the copper gap at exactly 0.200 mm (the "0.55" callout minus half of contact 8's 0.70 mm width), and 0.05 mm mask expansion per side makes the dam exactly 0.100 mm. The design *ties* the rule; it does not fail it. The EAGLE import then quantised every coordinate onto a 0.01 mil grid and four roundings went the wrong way together, costing 102 nm. Both pads belong to one footprint, so no placement can change it, and nothing routable fits in a 0.199898 mm neck (2 × 0.09 clearance + 0.0762 minimum width = 0.2562 mm; a via land is 0.3 mm), so routing cannot change it either. JLCPCB's mask registration tolerance is around ±50 µm, roughly 500× the shortfall. Do not edit the footprint, do not touch the CPG236 0.225 mm land, do not raise MinSolderMaskSliver. A board-wide sweep of all 834 pads confirms this is the only pair under 0.100 mm; the next band is 0.119964 mm (48 pairs inside U2's LQFP64).

## COUNT RECONCILIATION AND REMAINING UNCERTAINTY

The 2013 accounts for exactly: 607 un-routed (605 connections + 2 dead copper) + 724 silk-to-mask + 376 silk-to-silk + 289 component clearance + 11 clearance (8 R34-vs-keepout-region + 3 duplicates of the shorts) + 3 short circuit + 2 plane connect + 1 mask sliver. The 3 shorts are double-reported by two rules, so 2013 report lines correspond to 2010 distinct findings. Genuine physical defects: **three** (the R84/R85/R86 lands), plus **one** library primitive that blocks R34 and **584** latent copper-layer keepout tracks that raise nothing today. Everything else is either the board being unrouted or a rule measuring geometry that is not copper.

After the two must-fix actions, expect `short_circuit.txt` → 0, `clearance.txt` → 0, `component_clearance.txt` → roughly 225, and the silk classes unchanged until the post-routing pass.

Still uncertain, honestly: (a) whether Altium's interactive router actually refuses to cross a keepout **track** — the batch DRC does not pair them with pads, and only the keepout **region** is proven live, so the case for sweeping them rests on the cost asymmetry rather than on an observed failure; (b) the ~225 post-sweep component-clearance figure is an estimate from the family breakdown, not a re-run; (c) the two verifiers disagree on the net component-clearance effect of the R84/R86 move (one modelled −7 pairs, the other +1) — it is cosmetic either way, but do not be surprised by whichever you get; (d) JLCPCB's true minimum solder-mask dam is nowhere established from a primary source in this repo — `ZuluRules.pas` asserts 0.1 mm without a citation, which matters for X3 at 0.0999 mm and for U2's LQFP64 at 0.1200 mm, and is worth one look at JLC's capability sheet before release; (e) the dead copper's corner is reconstructed from area and pullback, not seen; (f) the X3 keep-out board coordinates are my own transform of the footprint-frame figures, cross-checked two ways but not eyeballed in the editor.

One tooling note, unrelated to the board: `tools/render_placed.py` still references `pb.THRU` at lines 94, 114 and 119, which commit df444aa deleted, so it will raise AttributeError the next time the as-placed view is rendered. `tools/verify_placement.py` keeps its own correct set including MOLEX-105017-0001 and is unaffected. The stale `--emit` line at `place_board.py:35` should be deleted or corrected while you are in there.