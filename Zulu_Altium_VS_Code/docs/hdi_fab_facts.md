# HDI fab and tool facts, fetched 2026-09-29 (three research agents, ~750k tokens)

Kept verbatim so the numbers do not have to be re-fetched. Decision context: docs/stage9_decision.md; the user chose HDI microvias on 2026-09-29.

# JLCPCB HDI facts (fetched 2026-09-29, USD). JLC HDI launched Sep 14 2026; 2025 third-party pages saying "no blind/buried" are STALE.

## Structures at 6 layers
- Quote tool "HDI Structure": 1-step / 2-step selectable; 3-step DISABLED at 6L. 1st order = 1 lamination + 1 laser; 2nd = 2 + 2.
- 8-layer example (only one published): 1st order connects L1-L2 / L7-L8; 2nd achieves L1-L3 / L6-L8. No 6L example; by analogy 2-step = L1-L3 / L4-L6. (OPEN Q)
- 1+N+1 and 2+N+2 supported; laser microvias staggered AND stacked; stacked requires copper fill ("filled and planarized by electroplating", dimple <= 10 um).
- Skip via L1-L3 = "split into stacked blind and buried vias" (forces 2-step in effect).
- Buried vias offered (mechanical, epoxy filled & capped, 0.15-0.55 mm; core across buried span >= 0.30 mm). Quote shows "Buried Via Fee: Manual Quote", "Lamination Fee: Manual Quote".
- Stackup on an HDI order: "Subject to Review" only (engineer-generated, emailed for confirmation). Calculator HDI board type lists named JLCH stacks.
- PCBA unavailable for HDI. Inner copper 1 oz FORCED on HDI quotes (0.5 oz disabled; calculator still accepts 0.5 oz).
- Laminates: Nan Ya NP-175F TG170 / Shengyi S1000-2M TG170 (+$6.76).

## Named 6L HDI stacks (calculator, 1.6 mm)
- JLCH061611N2-2116 (2+2+2, no buried, 1.58 +/-10%): L1 0.035 / PP2116 0.112 / L2 0.030 / PP2116 0.112 / L3 0.030 / core 0.930 / L4 0.030 / PP2116 0.112 / L5 0.030 / PP2116 0.112 / L6 0.035 (mm).
- JLCH061611N1-2116D (1+4+1 recommended, 1.53): L1 0.035 / PP 0.112 / L2 0.030 / core 0.100 / L3 0.030 / PP 0.112 / bare 0.700 / PP 0.112 / L4 0.030 / core 0.100 / L5 0.030 / PP 0.112 / L6 0.035.
- JLCH06161HN1-1078 (1+4+1, 0.5 oz inner, 1.59): L1 0.035 / PP1078 0.0784 / L2 0.0152 / core 0.550 / L3 0.0152 / PP7628 0.2008 / L4 0.0152 / core 0.550 / L5 0.0152 / PP1078 0.0784 / L6 0.035.
- JLCH061611Y1-2116 (1+4+1 + buried L2-L5, 1.57): L1 .035 / PP2116 .112 / L2 .030 / PP2116 .127 + PP7628 .201 / L3 .030 / core .500 / L4 .030 / PP7628 .201 + PP2116 .127 / L5 .030 / PP2116 .112 / L6 .035.
- PP library (Dk @1GHz): SY 2116 RC57% 0.127 mm Dk 4.29; SY 2313 RC58% 0.103 Dk 4.27; SY 1080 RC69% 0.086 Dk 3.99; SY 1078 RC69% 0.086 Dk 3.99; SY 106 RC72% 0.050 Dk 3.92; SY 1037 RC76% 0.055 Dk 3.86 (Nan Ya equivalents similar).

## Microvia / DFM (FAQ + DFM table)
- Laser hole default 0.10 mm; range 0.075-0.15. Pad >= hole + 0.15 mm (ring >= 0.075). Blind-via dielectric 0.05-0.127 mm; aspect <= 1:1 (hole >= dielectric).
- Hole-edge to hole-edge: >= 0.13 mm same net; >= 0.24 mm different nets (blind/buried/through alike).
- Hole edge to trace edge >= 0.15 mm (all via kinds). Blind via edge to board edge >= 0.35 mm.
- Through-hole >= 0.15 mm, pad >= hole + 0.10; AR <= 16:1; thickness 0.5-2.4 mm.
- Line/space 3/3 mil min (inner & outer), 3.5/3.5 preferred, 2.7/2.7 extreme (cost). Via-in-pad: "filled and capped" (FPOV); microvia-in-BGA-pad rule NOT published; via-in-pad blog: 0.1-0.15 uvia with 0.25-0.35 pads.
- Min BGA pad 0.2 mm (0.2-0.25 requires ENIG), BGA pad to trace >= 0.1 mm (general capabilities).
- Hole tolerance: via holes "not controlled"; PTH +/-0.076.
- Impedance on HDI: orderable, +/-10% (+/-5 ohm <50), IPC Class 2, NO report. Calculator supports HDI stacks.
- ENIG on HDI unrestricted ($16.80 qty 5).
- Quote via options same as standard: 0.2/(0.3/0.35) adds $16.77 + forced 4-wire Kelvin $16.66. 0.1 via only <= 1.0 mm boards.

## Pricing (70x26 mm, 6L, 1.6 mm, ENIG 1U, 1 oz outer, via 0.2/(0.3/0.35), impedance +/-10%)
| HDI 1-step (1 oz inner forced, NP-175F) | $208.96 (5) | $211.68 (10) | 12-13 days |
| HDI 2-step | $309.34 (5) | $313.19 (10) | 12-13 days |
| Standard 6L JLC06161H-3313E, 0.5 oz inner | $186.13 (5) | $201.97 (10) | 8-9 days |
Itemised HDI 1-step qty 5: eng $33, ENIG $16.80, material $6.76, inner Cu $16.62, board $1.20, HDI structure fee $66.92 (2-step: $167.30), buried/lamination "Manual Quote", impedance $33.08, min via $16.77, Kelvin $16.66, file confirm $1.05.
Holidays: Sep 25, 27, Oct 1-4 2026.

## Open questions for JLC sales
1. 6L "1-step"/"2-step" layer pairs (L1-L2/L5-L6 and L1-L3/L4-L6?). 2. Can a named JLCH stack be requested; 0.5 oz inner on request?
3. Buried Via Fee / Lamination Fee amounts; do they apply to N-type? 4. Microvia in 0.5 mm BGA pads: 0.225 land w/ 0.075 hole, or 0.25 pad w/ 0.10?
5. Skip via on 1-step? 6. Stacked L1-L2/L2-L3 on 2-step 6L and surcharge. 7. 2.7/2.7 mil online? 8. HDI expedite; does 12-13 d include stack review?
9. Impedance on HDI honours the 3 mil allowance? report at cost? 10. HDI-specific BGA pad & mask rules.


# PCBWay HDI facts (fetched 2026-09-29, USD, board 69.85 x 25.4 mm 6L 1.6 mm ENIG 1oz/1oz)

## Structures
- Orders offered: 1+N+1, 2+N+2 ... (>=6 orders need evaluation). Blind, buried, through. https://www.pcbway.com/hdi-pcb.html
- Advanced table: "HDI(7+N+7) staggered and stacked vias". https://www.pcbway.com/advanced-pcb-capabilities.html
- Online quote prices 1+N+1 ONLY: "Above is only the price of 1 + N + 1 HDI Structures." 2+N+2 not priceable online.
- Skip vias L1-L3: NOT FOUND as a capability. Buried L2-L5: offered generically, no layer-pair table.
- 6L HDI examples built: laser 2x / lamination 2x (HDI_6layer_03), min laser hole 0.2 mm on that example.

## Microvia specs
- Min laser drill: 4 mil (0.10 mm) standard, 3 mil (0.076) needs evaluation. Max 8 mil, dielectric <= 0.15 mm.
- Min annular ring for via: 3 mil (advanced). => derived min capture pad 0.10 + 2x0.076 = 0.252 mm (arithmetic, not a PCBWay statement).
- Blind hole aspect ratio 1:1 (2018 table); laser position tolerance +/-20 um.
- Copper-filled vias: hole <= 0.2 mm, laser/HDI applicable. Via-in-pad: resin fill + electroplated cap; "longer production time, higher cost".
- Min BGA pad: 0.25 mm prototype line, 0.20 mm advanced (0.15 sample). Min BGA pitch 0.4 mm.

## Stackup / impedance
- NO published 6L HDI stackup (1+4+1 or 2+2+2). Standard 6L: 0.11 mm PP Dk 4.29, core 0.53 mm Dk 3.96.
- Prepreg: 1080 = 3.1 mil Dk 4.21 (0.081 mm), 2116 = 5.4 mil Dk 4.45 (0.130 mm).
- Min dielectric for impedance 50 um. Impedance tolerance +/-10 % (+/-7 % HDI table 2018).
- Impedance control selectable with HDI; their calculator is generic (no stackups) -- "final values ... calculated by us".
- Custom stackup tick-box, extra cost after review.

## Line/space, through-vias
- Quote options 3/3 mil (sample), 3.5/3.5 bulk. HDI page: 0.065/0.065 mm. Advanced: 2/2 mil only "part" of board.
- Min mechanical drill 0.15 mm; annular ring 3 mil advanced; hole to inner conductor 6 mil (0.152 mm); via to copper 0.2 mm (prototype tolerances page).
- Aspect ratio max 14:1 (HDI page).

## Pricing (live calculators 2026-09-29)
Standard quote page, 6L 1.6 mm ENIG 1oz/1oz:
| case | qty 5 | qty 10 | days |
| HDI 3/3 mil 0.2 hole, impedance | $495.01 | $507.23 | 10-11 |
| FR-4 all-through 3/3 mil 0.2, impedance | $433.92 | $441.83 | 10-11 |
| FR-4 all-through 4/4 mil | $179.90 | -- | 5-6 |
Advanced calculator, 3/3 mil 0.15 mm, ENIG 2U", impedance:
| HDI | $510.36 | $523.42 | 10-11 |
| HDI + via-in-pad | $680.76 (+170.40) | | |
| HDI + via-in-pad + copper fill | $680.76 (no change) | | |
| Through-hole board | $365.15 | | |
| Through-hole + via-in-pad | $490.76 (+125.61) | | |
No structure selector on either form. "Final price subject to review."

## Open questions for PCBWay sales
1. 2+2+2 price/lead time. 2. Skip vias. 3. Buried L2-L5 inside 1+4+1. 4. Min laser capture/target pad.
5. Via-to-via and uvia-to-through spacing. 6. Copper-filled capped uvia-in-pad on 0.5 mm BGA with 0.225 mm lands.
7. Actual 6L 1+4+1 stack at 1.6 mm (PP thickness/Dk, core) and who runs impedance. 8. HDI lead time reality.
9. Via-in-pad adder per order or per qty. 10. 3/3 mil inner+outer on HDI. 11. Laser drill for 0.1 uvia vs 1:1 AR.
12. 0.254 mm "resin-filled via" min vs 0.1 mm laser plug.


# Altium 26 microvia mechanics (fetched 2026-09-29; official docs unless marked)

## Layer Stack Manager
- Via spans = "Via Types" tab of the LSM (Design > Layer Stack Manager, opens as a document tab). Default "Thru 1:6" cannot be deleted.
- "+" adds a type; Properties panel: First layer, Last layer, uVia checkbox (only when span is adjacent or adjacent+1 = Skip via), Mirror (if Stack Symmetry on). Name auto: "<Type> <First>:<Last>" e.g. "Thru 1:2", "Blind 1:2", "Buried 3:4". Software detects Thru/Blind/Buried from layers.
- Stacked uVias: NO separate type -- two via types used one above the other at the same XY ("automatically stacked when traversing multiple layers during interactive routing").
- Order of First/Last = laser drill direction. Via Types tab is Z-only; hole/diameter come from Routing Via Style rules.
- "Changes made in the LSM become available in the PCB editor after a Save is performed" -- save the LSM document, then Ctrl+S the PcbDoc.
- Stage 13 final implementation: L2/L5 are Signal layers with full power polygons. All six Via Types saved correctly;
  NC drill export produced Top-L2, L2-L3, L3-L4, L4-L5, L5-Bottom, and Top-Bottom files. The obsolete Internal Plane
  dropdown question no longer applies to this board.
- IPC-2226A uvia quoted by Altium: aspect <= 1:1, depth <= 0.25 mm.

## Rules
- Routing Via Style: scope by `IsMicroVia`, `IsSkipVia`, `IsThruVia`, `IsBuriedVia`, `IsBlindVia`, `IsStackedVia`; or `(StartLayer = 'Top Layer') and (StopLayer = '<LSM name>')`; or `InDrillLayerPair('Top Layer - <name>')`; `DrillPair = 'Start - Stop'`. Layer strings must match LSM names EXACTLY.
- Hole To Hole Clearance rule has "Allow Stacked Micro Vias" checkbox -- must be ticked or the stack violates.
- Layer Pairs rule (Manufacturing): "Enforce layer pairs settings" -- the ONLY check catching a script-placed via whose span is not a defined Via Type. RULEKIND string "LayerPairs".
- Hole Size / Minimum Annular Ring rules can be scoped `IsMicroVia` (min hole 0.075, ring 0.075 for JLC).
- Power Plane Connect Style advanced mode: separate via column; scope IsMicroVia for Direct connect on plane-landing uvias (inferred).
- No dedicated "microvia" rule kind exists.

## DelphiScript (documented API, DXP/NEXUS refs; post-2018 additions undocumented)
- IPCB_Via: X, Y, Size, HoleSize, LowLayer, HighLayer (TLayer), StartLayer/StopLayer (read, IPCB_LayerObject), IsConnectedToPlane[Layer], SizeOnLayer[], Cache. NO IsMicroVia / ViaType / DrillPair property. Official example sets only LowLayer/HighLayer; no drill-pair object assigned.
- Drill pairs READ-ONLY from script: Board.DrillLayerPairsCount, Board.LayerPair[i] (IPCB_DrillLayerPair: LowLayer, HighLayer, StartLayer, StopLayer). No creation API -> Via Types must be made in the GUI first.
- TLayer enums: eTopLayer, eMidLayer1..30, eBottomLayer, eInternalPlane1..16, eMultiLayer. For THIS stack (Top / plane / sig / sig / plane / Bottom) the mapping is INFERRED: eTopLayer, eInternalPlane1 (L2-GND), eMidLayer1 (L3-SIG), eMidLayer2 (L4-SIG), eInternalPlane2 (L5-VCC3V3), eBottomLayer -- confirm via Board.LayerStack.LayerObject[..].Name. The project's .pas already use eMidLayer1/eMidLayer2 for L3/L4.
- Stacked Top->L3 = two IPCB_Via objects at one XY: (eTopLayer -> eInternalPlane1) and (eInternalPlane1 -> eMidLayer1), each Size 0.25 / HoleSize 0.10, net set with Net.AddPCBObject too. Skip via = one object eTopLayer -> eMidLayer1 against a "Top->L3 uVia" type.
- IPCB_Pad.DrillType has eLaserDrilledHole; IPCB_Via does not (documented).

## File format (KiCad altium_parser_pcb.cpp + AltiumSharp, both agree)
- Vias6 record: byte 0 layer (74 multilayer), 3-4 net, 13 X, 17 Y, 21 diameter, 25 hole, **29 start layer, 30 end layer**, 31 plane connect style, 74 mode, 75.. per-layer diameters[32]; AltiumSharp only: 312 DrillLayerPairType (0 through,1 start,2 mid,3 end) -- single-source.
- Layer codes: TOP=1, MID_LAYER_1=2 ... MID_LAYER_30=31, BOTTOM=32, INTERNAL_PLANE_1=39..54, MULTI_LAYER=74. (Today all 377 vias: byte29=1, byte30=0?? -- our read showed (74,1,0); re-check: end layer byte may be 32 at a different offset; verify against KiCad offsets.)
- Where AD20+ stores Via Types in Board6 is NOT known to any open parser (LAYERPAIR0LOW/HIGH exist in our file; count key absent).
- KiCad does not know where the uVia FLAG is stored.

## Outputs
- NC Drill: a separate drill file per layer pair with a unique extension (pattern undocumented; community: .TXT thru, .TX1, .TX2...). .LDP = drill-pair report used by CAM to detect blind/buried. uVias: separate file per uVia drill pair; Gerber X2 entries per uVia plot; ODB++ separate drill per pair.
- JLCPCB standard-service page still says "we don't support blind/buried" -- quote the HDI service explicitly. PCBWay: blind/buried spans must cover an even number of copper layers; cannot start/end on the wrong side of a core.

## Recipe (GUI): LSM > Via Types > + : Top->L2 (uVia), L2->L3 (uVia), L4->L5 (uVia), L5->Bottom (uVia), optionally Top->L3 skip, L3->L4 buried (mechanical, uVia off). Save LSM, save PcbDoc. Rules: Routing Via Style per span, Hole Size + Annular Ring scoped IsMicroVia, Hole-to-Hole "Allow Stacked Micro Vias", Layer Pairs enforce.
