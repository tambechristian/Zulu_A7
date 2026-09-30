# HDI specification — the judge's full reasoning (2026-09-29, workflow wf_d61d6c0f, 7 agents, 1.29M tokens)

Structured result: docs/hdi_spec.json. Proposed tools/hdi.json: docs/hdi.proposed.json. Fab facts: docs/hdi_fab_facts.md.

# Zulu A7 HDI specification (judge, 2026-09-29)

Board `Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc` md5 `210a6f2b7669980309fb2472a125ad98` (= brief). `tools/route_inputs.json`
md5 `e166d74aa85467675801e6e7802c7104` (the brief's `f5903da8` is stale: the `hdi` block was added; geometry identical to the
PcbDoc within 0.044 um -- three independent regenerations agree). Live `tools/hdi.json` md5 `b05f58bb` = the through-only
default. This directory: `hdi.json` (md5 `dab6ffb3`, the exact content for `tools/hdi.json`), `arith.py`/`arith.out` (every
derived number), `exercise_hdi.py`/`.out` (the live `tools/hdi.py` loading that JSON), `remeasure/sites_0p12.out` (U1 site
count re-measured at 0.12/0.27, 0.15/0.30 and 0.10/0.25 with a copy of the u1_sites enumerator; COMBOS swapped, nothing else).

Inputs judged: the three measurements and their verifier verdicts (impedance, dfm_rules, u1_sites), the three fact sheets,
`docs/stack_switch_3313E.md`, `docs/sdram_bus_widths.md`, `docs/pwr_rail_widths.md`, `docs/via_land_decision.md`,
`docs/stage9_decision.md`, `docs/hdi_fab_facts.md`, `board/JLCPCB-DFM-ENQUIRY-2.md`, `tools/hdi.py`, `tools/verify_stack.py`,
Rules6 (55 rules, `dfm_rules/rules_all.json`). Where a verifier refuted a claim the verifier wins; the only re-measurement I
made myself is the U1 site count at 0.12/0.27 (`remeasure/`), because no sibling had measured that combination.

## 1. The decision in one paragraph

**JLCPCB, HDI 2-step, Structure B on the named stack `JLCH061611N2-2116` exactly as JLC publish it** (2+2+2, 1 oz inner
forced), **laser microvia 0.15 mm hole / 0.30 mm land (ring 0.075)**, stacked Top->L2-GND->L3-SIG and Bottom->L5-VCC3V3->L4-SIG,
buried mechanical L3-SIG->L4-SIG 0.15/0.27 through the 0.930 core only once JLC have priced it, through vias 0.20/0.35 unchanged,
**no via-in-pad anywhere, no placed copper changes width** (0 of 1518 tracks). The one fab question that can improve the spec
before ordering is a **0.12 hole / 0.27 land** on the same stack (rule-legal at 0.93:1, ring 0.075; it turns the 47 U1
interstitial sites from a 0.9 um margin into 15.9 um). Cost: **$309.34 (qty 5) / $313.19 (qty 10), 12-13 days** plus the
buried-via and lamination fees JLC only quote manually, against $186.13 / $201.97 and 8-9 days today.

Why this and not the two siblings' preferred 0.10/0.25: on this board the microvia hole/land does not change the U1 site
count (87 legal at 0.075/0.225, 0.10/0.25, 0.12/0.27 and 0.15/0.30 alike, because the board's own 0.09 clearance to the
placed Top fan-out and to the placed 0.35 lands binds first everywhere), while the only stacks that admit a 0.10 hole put a
thin 1080/1078 prepreg under the SDRAM bus and drop the **placed** L3/L4 copper to 43.1-45.2 ohm (wanting 0.092-0.105 mm on
607.8 mm of it = a re-route), and the hybrid that keeps the bus (1078 on L1-L2 only) still needs hole >= 0.112 for the L2-L3
member of every signal stack, so it buys no U1 signal site and costs the USB pair 7.4 ohm plus a custom stack. 2116 as named
costs +2.5 ohm on the (unplaced) USB pair, +1.2 ohm on the placed SDRAM bus, and nothing else.

## 2. Fab and structure

- **Fab: JLCPCB** (HDI launched 2026-09-14; fact sheet `jlcpcb_hdi_facts.md`). PCBWay is out: only 1+N+1 is priceable
  ($495.01 qty 5, 10-11 d, +$185.67 over JLC's 2-step), 2+N+2 "not priceable online", no published 6L HDI stack, via-in-pad
  +$125.61-170.40, and the project already priced and rejected PCBWay for the standard board (memory).
- **Structure: 2-step at 6 layers = Structure B of the brief**: stacked laser microvias Top->L2->L3 and Bottom->L5->L4, through
  vias stay legal, buried L3->L4 "as needed". JLC's 6L 2-step layer pairs are by analogy with their 8L example (L1-L3 / L4-L6):
  **open question 1 of the fact sheet, first fab question below.** 1-step (1+4+1, $208.96) is Structure A's path and rips 288
  inner tracks / 857.8 mm / 50 nets incl. all 39 SDRAM nets (brief) -- refused. Plain 1+4+1 with the planes as they are converts
  97 of 377 vias (brief) -- not enough.
- **Stacked, not staggered**: JLC do both; stacked "requires copper fill (filled and planarized by electroplating, dimple <= 10 um)"
  with an unstated surcharge (fab question 3). Staggered would spend two of U1's 87 legal sites per stack; sites are the binding
  resource (`docs/stage9_decision.md`: "the binding resource is via slots").
- Buried L3->L4: JLC offer mechanical buried 0.15-0.55 mm, epoxy filled and capped, core across the span >= 0.30 (0.930 here,
  aspect 6.2:1); the quote shows "Buried Via Fee: Manual Quote" and "Lamination Fee: Manual Quote" and the named stack is
  listed "no buried". The span is in `hdi.json` so plans can be measured with it, but **no plan may depend on it until JLC price
  it** (user decision 4).

## 3. Stack: named, and the exact per-layer request under "Subject to Review"

Order **by name: `JLCH061611N2-2116`**, 1.58 mm nominal, selected in the HDI impedance flow, and get the engineer-generated
stack onto the order acknowledgement (the lesson of `docs/stack_switch_3313E.md`: a free-text remark is not a binding channel).
The per-layer request, so the emailed stack can be checked line by line:

| # | layer | thickness (mm) | material / Dk | note |
|---|---|---|---|---|
| L1 Top | copper | 0.035 finished (1 oz) | | unchanged |
| PP | 2116 x1 | **0.112 pressed** | Dk 4.29 @1 GHz (JLC PP library) | JLC named-stack figure; library nominal 0.127 |
| L2-GND | copper | **0.030** (1 oz, forced) | | today 0.0152 |
| PP | 2116 x1 | **0.112 pressed** | Dk 4.29 | the SDRAM reference gap; today a 0.100 core Dk 4.6 |
| L3-SIG | copper | 0.030 | | |
| core | | **0.930** | Dk unmeasured (4.6 assumed in every solve; sensitivity 0.9 ohm on the SDRAM far-plane term, 0 on the pair) | today 1.1208 (7628+0.7+7628) |
| L4-SIG | copper | 0.030 | | |
| PP | 2116 | 0.112 | Dk 4.29 | |
| L5-VCC3V3 | copper | 0.030 | | |
| PP | 2116 | 0.112 | Dk 4.29 | |
| L6 Bottom | copper | 0.035 | | |

Laminate 2x0.035 + 4x0.030 + 4x0.112 + 0.930 = **1.568 mm** (JLC round it to 1.58 +-10 %); with the two 1.2 mil masks
1.629 mm; today's laminate 1.65038. Through-via aspect 1.568/0.20 = 7.84:1 (JLC <= 16:1). Laminate TG170 (NP-175F or S1000-2M,
+$6.76 already in the quote). Copper-face-to-copper-face convention for every gap must be confirmed (fab question 4) -- the
whole impedance solve pivots on it.

Refused stacks, with the number that refuses each: `JLCH061611N1-2116D` (1+4+1: Structure A, converts too little; SDRAM
47.0 ohm would be fine); `JLCH06161HN1-1078` (L3 sits 0.550 from L2: placed 0.125 bus reads 83 ohm, 0.545 mm to restore, not
routable in U3's 0.35 mm street); 2+2+2 with 1080/1078 on L1-L2 **and** L2-L3 (bus 45.2 ohm at 0.086 / 43.1 at 0.0784 pressed,
at or below the 45-60 band; restoring 0.105/0.092 mm on 607.8 mm of placed L3/L4 copper = re-route); hybrid 1078 L1-L2 / 2116
L2-L3 (bus stays 50.2, pair 77.9, rule 0.1235/0.150, custom stack, and the 0.10 hole is legal only on the Top->L2 span while every
signal stack's L2->L3 member still needs >= 0.112, so it gains no U1 signal site); 106/1037 outers for a 0.075 hole (custom
stack, USB 63-67 ohm, 90 ohm unreachable at >= 3 mil on 106).

## 4. Microvia

- **Hole 0.15 / land 0.30 mm, laser, ring 0.075.** Forced by JLC's aspect <= 1:1 (hole >= dielectric = 0.112) using their
  default sizes (0.10 default, range 0.075-0.15) and pad >= hole + 0.15. 0.112/0.15 = 0.75:1; if JLC count the 0.035 outer foil
  in the laser depth (unstated), 0.147/0.15 = 0.98:1 still passes, while 0.12 would fail (1.23:1) -- one more reason 0.15 is the
  guaranteed baseline and 0.12/0.27 is a question, not an assumption.
- **Alternative to ask for: 0.12 hole / 0.27 land** (0.933:1, ring 0.075, inside the 0.075-0.15 range; whether JLC laser
  non-default sizes is unstated). Same 87 U1 sites, same 84 max simultaneous, same 51 stackable, but the interstitial margin
  to the 0.09 rule becomes +0.0159 mm (+0.0059 under a "BGA pad to copper 0.10" reading, all 87 kept) instead of +0.0009 /
  -0.0091 (87 -> 40) at 0.15/0.30 (`remeasure/sites_0p12.out`, `arith.out`). Rule values in Altium and `hdi.json` change in
  four places if JLC say yes (`_alternates["0.12_0.27"]`: pitch 0.36, antipad 0.45, laser-to-mechanical 0.40).
- **Spans**: Blind Top->L2-GND, Blind L2-GND->L3-SIG, Blind L4-SIG->L5-VCC3V3, Blind L5-VCC3V3->Bottom (all uVia); Buried
  L3-SIG->L4-SIG (mechanical 0.15/0.27); Thru 1:6. No skip via type: JLC split a Top->L3 skip into a stacked pair anyway and
  Altium has no separate stacked type -- a stack is two objects at one XY.
- **Stacked** (same net, one XY, `stacked_same_xy: true`), copper-filled and planarized per JLC.
- **Via-in-pad: NO, nowhere.** 0.15 in U1's 0.225 land = 0.0375 ring (0.12 -> 0.0525), below JLC's 0.075. The only via-in-pad
  combinations that exist (0.075-in-0.225 on 106/1037; 0.10-in-0.225 on 1078 with a 0.0625-ring waiver) each need a different,
  custom stack; they reach ring 0 (40 of the 42 ring-0 signal balls) but cost 7.4-22 ohm on the USB pair. Not in this order; user
  decision 5 says whether to ask JLC about it as a rev-B option.
- Pitches (different nets, centre to centre, `arith.out`): microvia-microvia 0.39, microvia-through 0.415, microvia-buried
  0.39, buried-buried 0.39, through-through 0.44 (unchanged). Same-net stacks need no pitch (one XY).
- Plane void for a foreign-net microvia on L2-GND / L5-VCC3V3: **0.48 mm** = 2 x max(0.075 + 0.15, 0.15 + 0.09); through vias
  keep 0.70. Two foreign-net voids in adjacent 0.5 mm sites leave a **0.02 mm web** (< 3 mil): foreign-net stacks must not
  occupy two adjacent interstitials/cells; diagonal neighbours (0.7071) keep 0.227. The site matching below did not apply this
  constraint (unmeasured impact on the 41).

## 5. Why the combination is one decision, resolved

The brief's collision (2116 at 0.112 makes a 0.10 hole illegal) resolves as: the hole follows the prepreg, the prepreg follows
the placed SDRAM bus, and the bus is placed. Numbers, all under the file's mask model (1.2 mil / Dk 3.8) with three solvers
agreeing within 0.4 ohm:

| stack (outer PP L1-L2 / L2-L3) | legal laser hole | USB 0.150/0.150 | SDRAM 0.125 L3/L4 (placed) | placed copper |
|---|---|---|---|---|
| today 3313E 0.0994 / 0.100 core | -- | 85.3 | 49.0 | -- |
| **N2-2116 0.112 / 0.112** | **0.15 (0.12 if accepted)** | 87.8 (+2.5) | 50.2 (+1.2; 50.4 with the slot as PP resin) | **none** |
| 2313 0.103 / 0.103 | 0.15 (0.103 > 0.10) | 85.3 | 48.3 | none, but no named stack |
| 1080 0.086 / 0.086 | 0.10 | 81.2 (-4.1) | 45.2 (-3.8) | re-route 607.8 mm |
| 1078 0.0784 / 0.0784 | 0.10 | 77.9 (-7.4) | 43.1 (-5.9) | re-route |
| hybrid 1078 / 2116 | 0.10 on L1-L2 only | 77.9 | 50.2 | none, custom stack, no site gain |
| HN1-1078 (1+4+1) | 0.10 | 77.9 | 83.2 | 0.545 mm to restore: out |

The +2.5 on the pair is a one-solver but not a one-Dk-source delta (today's 4.10 is JLC's 3313E table, 2116's 4.29 is the PP
library at 1 GHz): +1.4 at Dk 4.45, +3.8 at Dk 4.10 (verifier). U2 is an FT2232HL, USB 2.0 Hi-Speed, so 1 GHz Dk is the right
frequency. Absolute pair values carry +-5 ohm of mask-model spread (no mask 94.4, file mask 85.3, Altium stock mask 91.1); the
stack-to-stack deltas are the robust numbers. The docs' 87.37 was reproduced by no model and its two "independent 2-D FEM
solvers" exist nowhere on disk nor in git history.

## 6. `tools/hdi.json` -- exact content: `judge/hdi.json` (md5 dab6ffb3)

Loaded through the live `tools/hdi.py` (`exercise_hdi.out`): spans T-L2 / L2-L3 / L4-L5 / L5-B laser 0.15/0.30 pitch 0.39
antipad 0.48; L3-L4 mechanical 0.15/0.27 pitch 0.39; through 0.20/0.35 pitch 0.44; `laser_to_mechanical_pitch` 0.415;
`disjoint_span_pitch` 0.0 (JLC state no rule for spans that share no layer -- fab question 11); `stacked_same_xy` true. Pitch
matrix as intended (0.39 / 0.415 / 0.44, `None` for disjoint spans); `antipad_r` 0.24 -> 0.48, through 0.70; `punches` void for
foreign nets only; `stacked()` accepts T-L2 over L2-L3 and L2-L3 over the buried L3-L4 on one net, rejects different nets and
non-adjacent spans.

Two things the JSON cannot fix and the tools workflow must (not mine to edit):
1. `via_in_pad` is false on every span (correct: no via-in-pad), but `hdi.field_ban()` lifts U1's land-field ban only for
   via-in-pad spans, so **as hdi.py stands every span here is banned inside the field** (conservative, verified in
   `exercise_hdi.out`). The JSON carries a new key `field_ok` (true on Top->L2, L2->L3, L4->L5, L3->L4; false on L5->Bottom and
   through); `field_ban()` must become `return not bool(self.params(span).get('field_ok', False))`. This is the land-field
   raster change stage 9 left open (user decision 7).
2. `hdi.usable('Top','SIG')` returns only the through span: a Top->L2 via alone reaches no second signal layer, so **the gates
   never propose a stack**; stack planning must pair Blind 1:2 + Blind 2:3 explicitly. Also `route_reach.py:197` bans vias
   across the whole land field and `route_inputs.py EDGE_CLEARANCE = 0.25` is 0.025 short of JLC's 0.35 hole-edge for vias
   (0.275 land-edge at ring 0.075; the project convention 0.80 binds anyway).

## 7. Altium: Via Types and rules

LSM > Via Types (GUI only; save the LSM, then Ctrl+S the PcbDoc): **Blind 1:2** Top Layer -> L2-GND uVia; **Blind 2:3** L2-GND ->
L3-SIG uVia; **Blind 4:5** L4-SIG -> L5-VCC3V3 uVia; **Blind 5:6** L5-VCC3V3 -> Bottom Layer uVia; **Buried 3:4** L3-SIG -> L4-SIG
(uVia off); **Thru 1:6** stays. Whether the AD26 dropdowns offer the Internal Plane layers L2-GND / L5-VCC3V3 is UNVERIFIED
(`altium_microvia_facts.md`) -- the first thing to check on screen. Script side: a stack = two `IPCB_Via` objects at one XY
(eTopLayer -> eInternalPlane1, eInternalPlane1 -> eMidLayer1), each Size 0.30 / HoleSize 0.15, `Net.AddPCBObject` too; drill pairs
are read-only from script, so the Via Types come first in the GUI.

Rules (name | kind | scope | value | status). Values in brackets are the 0.12/0.27 alternative.

| rule | kind | scope | value | status |
|---|---|---|---|---|
| RoutingVias_uVia | RoutingVias | `IsMicroVia` | hole 0.15 min=max=pref, diameter 0.30 min=max=pref [0.12 / 0.27], priority 1 | new; optional per-span split `IsMicroVia And (StartLayer = 'Top Layer') And (StopLayer = 'L2-GND')` etc. |
| RoutingVias_Buried | RoutingVias | `IsBuriedVia` | hole 0.15, diameter 0.27 (ring 0.06: 0.06 + 0.09 = JLC's 0.15 hole-to-trace), priority 2 | new |
| RoutingVias | RoutingVias | `All` -> `IsThruVia` | 0.20 / 0.35, priority 3 | exists (13.7795 / 7.874 mil, "Through Hole") |
| HoleSize_uVia | HoleSize | `IsMicroVia` | 0.15-0.15 absolute [0.12], priority 1 | new: the existing HoleSize All 0.20-1.02 would flag every microvia |
| HoleSize_Buried | HoleSize | `IsBuriedVia` | 0.15-0.55, priority 2 | new |
| HoleSize | HoleSize | `All` | 0.20-1.02 | exists, drops to priority 3 |
| MinimumAnnularRing_uVia / _Buried / (All) | MinimumAnnularRing | `IsMicroVia` / `IsBuriedVia` / `All` | 0.075 / 0.06 / 0.075 | new (no rule of this kind exists today) |
| HoleToHoleClearance | HoleToHoleClearance | All, All | 0.20 -> **0.24**, "Allow Stacked Micro Vias" TRUE (already TRUE) | exists; audit: 0 pairs below 0.24 today, 8 same-net pairs at exactly 0.2400 (0.44 pitch) -- if the first DRC flags them by rounding, 0.2399 is a rounding artefact, not a JLC concession |
| LayerPairs | LayerPairs | | ENFORCE TRUE | exists; the only check catching a script-placed via whose span is not a Via Type |
| PlaneClearance_uVia | PlaneClearance | `IsMicroVia` | 0.165 mm (hole-edge model) -> 0.48 void [0.45], priority 1 | new; if AD26 measures from the pad edge (unmeasured) the value is 0.09 -- one DRC on a test via settles it |
| PlaneClearance | PlaneClearance | All | 0.25 (0.70 void on through vias) | exists, priority 2 |
| PlaneConnect_Vias | PlaneConnect | `IsVia` | Direct | exists: GND microvias landing on L2-GND / VCC3V3 on L5-VCC3V3 connect through it |
| BoardOutlineClearance_Vias | BoardOutlineClearance | `IsVia` | 0.80 mm | new (no outline rule exists); JLC need 0.275 land-edge; closest via land-edge today 0.825 -> 0 violations |
| Clearance | Clearance | All, All | 0.09 unchanged | ring 0.075 + 0.09 = 0.165 hole-edge >= JLC 0.15, so the board's rule binds |
| SolderMaskExpansion_Vias | SolderMaskExpansion | `IsVia` | tented both sides | exists, unchanged |
| Fanout_BGA | FanoutControl | `IsBGA` | Centered | exists, unchanged |
| DiffPairsRouting | DiffPairsRouting | All | 0.150 / 0.150 provisional (see widths) | exists |

Scope keywords `IsBuriedVia` / `IsThruVia` are documented for Routing Via Style; that they work in HoleSize / MinimumAnnularRing /
PlaneClearance / BoardOutlineClearance scopes is inferred (unverified). `IsMicroVia` in HoleSize / MinimumAnnularRing is documented.

**Gate before any stacked signal via is planned (10 minutes, one test via + a Gerber of L2):** L2-GND / L5-VCC3V3 are negative
Internal Plane layers; a foreign-net microvia stopping or stacking on L2 may get a void and no landing pad in the L2 Gerber. If
confirmed, L2/L5 must become Signal layers with full polygons (then the 0.09 Clearance and the polygon pour clearance give the
same 0.48 void and PlaneConnect_Vias becomes a PolygonConnect Direct rule scoped IsVia). The same test settles whether
PlaneClearance measures from the hole edge or the pad edge.

## 8. Width changes -- rules and placed copper, before / after

Placed copper: **0 of 1518 tracks change** (SDRAM 39 nets: L3 81 tracks / 276.2 mm, L4 127 / 331.6 mm, Bottom 45 / 48.7 mm at
0.125, Top 147 / 121.1 mm at 0.0762; the only placed inner rail copper is VCC1V0 on L3, 5 tracks / 13.6 mm at exactly the 0.50
floor; USB_D_P / USB_D_N have zero tracks).

| what | before | after | reason |
|---|---|---|---|
| `Width_SDRAM` L3/L4/Bottom | 0.10 / 0.125 / 0.15 | **unchanged** | placed 0.125 reads 50.2 ohm on N2-2116 (etch band 48.24-52.28) vs 49.0 today, nearer the 8 mA (~50 ohm) driver; inside the docs' 45-60 band |
| `Width_SDRAM` Top | 0.0762 / 0.0762 / 0.15 | unchanged | the 3 mil escape reads 68.0 ohm single-ended vs 65.4 today (number, not a constraint) |
| `DiffPairsRouting` USB | 0.150 / gap 0.150 | **0.150 / 0.150 provisional** | 87.8 ohm on N2-2116 (today 85.3), nearer the 90 nominal, inside JLC's +-10 % (81-99); 0.162/0.150 would hold today's 85.3, 0.141/0.150 gives 90 in our model. Freeze only after JLC's calculator figure (fab question 5); the pair is not placed, so this is rule-only |
| `Width_PWR_VCC3V3` inner min | 1.05 | **1.05 now; 0.55 optional** once 1 oz inner is on the acknowledgement | IPC-2221 10 C width 1.0187 -> 0.5161 at 0.030 Cu (ratio 0.5067); DRC-only, no copper moves |
| `Width_PWR_U8` inner min | 1.10 | 1.10 now; 0.60 optional | 1.0937 -> 0.5541 |
| `Width_PWR_VCC1V0` inner min | 0.50 | 0.50 now; 0.25 optional | 0.4515 -> 0.2288; the 5 placed L3 tracks at 0.50 stay |
| every other Width / Clearance rule | | unchanged | |

If the floors are relaxed, `tools/verify_widths.py` (the acceptance test) and `SetPwrRailWidths` in `tools/ZuluSetup.pas` carry
the same values. The relaxation is void if JLC honour 0.5 oz inner on request (fab question 6): on 0.0152 Cu the floors stand.

## 9. U1 via sites under 0.15/0.30 on N2-2116 (`remeasure/sites_0p12.out`, u1_sites verifier)

- **87 of 447 positions legal today** (40 vacant cells: E6-E15, F5, F14, G5, G15, H5, H15, J5, J15, K5, L5, L6, L15, M5, M6,
  M14, M15, N5, P5, P15, R5-R15; 47 interstitials: 42 ring-1/2 + 5 moat/core); **max simultaneous 84** (diagonal
  cell/interstitial pairs 0.3536 apart are exclusive: land gap 0.0534 < 0.09, hole gap 0.2034 < 0.24); **51 of the 87 also
  clear the placed L3 copper** for the L2->L3 member (stackable), **45** also clear L3+L4 for a buried via beneath. Identical
  at 0.12/0.27 and 0.10/0.25 (87 / 84 or 87 / 51 / 45): the placed copper and the 0.09 rule bind, never JLC's hole rules.
- Interstitial margin to the 0.09 rule: **+0.0009 mm at 0.30** (grid minimum 0.240946 - 0.150 - 0.09), **-0.0091 under a
  "BGA pad to copper 0.10" reading (87 -> 40)**; at 0.27: +0.0159 / +0.0059 (87 kept). This is the quantified reason for the
  0.12/0.27 question and for fab question 9.
- Signal balls served by in-field sites: at most **41 of 117** (18 ring-1 + 23 ring-2 by maximum matching; 37 of 40 ring-1
  alone); **ring 0: 0 of 42** at every combination without via-in-pad; restricted to L3-stackable sites 16. Of the 82 ring-0/1
  balls that need an outside via today, 64 still do.
- The **24 signal-net Top-only vias** (107 Top-only in all) convert in place at every combination (nearest foreign through via
  0.5 mm: hole and land margins +0.085 at 0.15/0.30); far ends 8 Bottom-only / 8 through-hole / 8 Top or Top+Bottom nets.
- Through via 0.20/0.35: 41 sites (40 cells + 1 interstitial).
- Plane web: foreign-net stacks in two adjacent 0.5 mm sites cut L2 to 0.02 mm -- alternate sites; the effect on the 41 is
  unmeasured.

## 10. `tools/verify_stack.py` must become

1. `EXPECT` for `JLCH061611N2-2116`: Top Layer 0.035; Dielectric 2 **0.112 Dk 4.29 PREPREG**; L2-GND **0.030**; Dielectric 4
   **0.112 Dk 4.29 PREPREG** (today 0.100 core 4.6, type CORE=1 -> 2); L3-SIG 0.030; Dielectric 1 **0.930, type CORE (1)**, Dk =
   JLC's emailed value (4.6 assumed; today 1.1208 / 4.523 / GENERIC because it was a merged row -- now a single core, so CORE is
   the honest label); L4-SIG 0.030; Dielectric 5 0.112 / 4.29 / PREPREG; L5-VCC3V3 0.030; Dielectric 3 0.112 / 4.29 / PREPREG;
   Bottom 0.035; masks unchanged 1.2 mil / 3.8 / SURFACE. `INNER_CU_MM = 0.030`. Dk values are placeholders until the stack
   review: keep `TOL_DK` and print the emailed figure beside them.
2. Laminate line: **1.568 mm <- JLC 1.58 +-10 %** (not 1.65040); total with mask 1.629.
3. Legacy `LAYERn` table expectations: Top 0.112/4.29, L2 0.112/4.29, L3 0.930/Dk core, L4 0.112/4.29, L5 0.112/4.29; PASS string
   `JLCH061611N2-2116`.
4. Section [4] unchanged (PLANE1NETNAME GND, PLANE2NETNAME VCC3V3, 20 mil pullbacks, the six LAYERIDs) -- the edit must again be
   in place, row by row, Stack Symmetry OFF, never a rebuild (stack_switch_3313E.md's warning stands).
5. **New section [5]: the Via Types.** After the GUI save, read Board6/Data for the drill-pair keys (`LAYERPAIR0LOW/HIGH` exist
   today; the count key and any uVia flag are unknown to every open parser) and assert the five spans Top-L2, L2-L3, L4-L5, L5-Bottom,
   L3-L4 plus Thru; fail if a pair is missing or a plane layer is not offered. Section [6] (or `verify_widths.py`): the new
   Rules6 entries -- RoutingVias_uVia 0.15/0.30, HoleSize_uVia, MinimumAnnularRing_uVia, HoleToHole 0.24, PlaneClearance_uVia,
   BoardOutlineClearance_Vias.
6. `Vias6` census: bytes 29/30 per via must now be one of (1,39), (39,2), (3,40), (40,32), (2,3), (1,32) once microvias exist
   (layer codes TOP 1 / MID1 2 / MID2 3 / BOTTOM 32 / PLANE1 39 / PLANE2 40 per the KiCad offsets; the fact sheet's "(74,1,0)" is
   wrong, byte 30 is 32 on all 377 today).

## 11. Cost and lead time (fact sheets, 70x26 mm, 6L, 1.6 mm, ENIG, 3 mil tier, impedance)

- **JLC HDI 2-step: $309.34 qty 5 / $313.19 qty 10, 12-13 days**; standard 6L today $186.13 / $201.97, 8-9 days: **+$123.21
  (+66.2 %) / +$111.22 (+55.1 %), +4 days**; vs 1-step ($208.96) +$100.38. Itemised: HDI structure fee $167.30 (1-step $66.92),
  eng $33, impedance $33.08 (the standard stack had it at $0 per JLC's 2026-09-14 reply -- ask), ENIG $16.80, inner Cu 1 oz
  $16.62, min via $16.77, Kelvin $16.66, material $6.76, board $1.20, file confirm $1.05 (sum 308-309, matches).
- **Not in the quote: Buried Via Fee and Lamination Fee ("Manual Quote"), the stacked-via copper-fill surcharge (unstated), and
  whether the 12-13 days include the "Subject to Review" stack round trip.** JLC holidays Sep 25, 27, Oct 1-4 2026.
- PCBWay 1+N+1 $495.01 / $507.23, 10-11 days; 2+N+2 not priceable; via-in-pad +$125.61-170.40 -- not chosen.

## 12. Questions to send JLC before ordering (in the order they decide the spec)

1. On `JLCH061611N2-2116` ordered as HDI 2-step, confirm the layer pairs: L1-L2 and L2-L3 laser (stacked, copper filled and
   planarized) and L6-L5 / L5-L4 likewise; surcharge for stacked vs staggered; may a stack sit on an epoxy-filled buried via?
2. Laser hole sizes on the 0.112 mm 2116 outer PP: is 0.12 mm (0.93:1, pad 0.27) accepted, or only 0.10/0.15 -- which discrete
   sizes do you laser between 0.075 and 0.15? Does the 1:1 aspect count the 0.035 mm outer foil (0.147 mm)? Via-hole and
   laser-position tolerance ("not controlled" on the capability page) and layer-to-layer registration.
3. Buried via L3-L4 (0.15 hole, 0.27 pad, 0.930 mm core) on this stack: Buried Via Fee and Lamination Fee amounts; do they apply
   to the N-type named stack; may we keep the stack name with buried vias added?
4. The engineer-generated stack: PRESSED thickness and Dk (state the frequency) of each 2116 (we assume 0.112 / 4.29; your
   3313E table used 4.10 and PCBWay quote 4.45 for 2116 -- the USB pair moves 2.4 ohm across that range) and of the 0.930 core;
   confirm gaps are copper-face to copper-face; 1.58 mm total.
5. Impedance on HDI: your calculator's figure for a 0.150/0.150 Top-layer pair on this stack (we solve 87.8; 85 at 0.162/0.150;
   90 at 0.141/0.150), the mask thickness/Dk you model (1.2 mil / 3.8?), the +-10 % promise, the $33.08 line item (standard
   stacks were $0), and whether the 3 mil / 0.09 BGA allowance (+20 % tier, 2026-09-14 reply) still stands on an HDI order with
   impedance control; fine-line tolerance +-8-12 % on HDI outer layers.
6. Is 0.5 oz (0.0152 mm) inner copper honoured on a 6L HDI order or is 1 oz truly forced? (Our inner power floors halve at 1 oz.)
7. Plane anti-pads: is a 0.48 mm void around a 0.15/0.30 microvia on an inner plane acceptable (hole-edge to plane copper
   0.165); is a plane web narrower than 3 mil between two adjacent voids rejected, or merged by CAM?
8. Hole-edge rules: 0.24 different-net / 0.13 same-net applies laser-to-mechanical too (0.15 microvia vs 0.20 through = 0.415
   pitch)? Is a same-net trace entering its own via exempt from the 0.15 hole-to-trace figure?
9. Does "BGA pad to trace >= 0.10" apply to a microvia land at an interstitial of the 0.5 mm BGA? A 0.30 land clears the 0.225
   lands by 0.0909 (0.27: 0.1059) against our 0.09 rule.
10. "Blind via edge to board edge >= 0.35": hole edge or pad edge; the through-via-to-edge minimum on HDI.
11. Any minimum spacing between two vias whose spans share no layer (a Top-L2 microvia directly over an L5-Bottom one)?
12. Lead time: do 12-13 days include the stack review; the forced 4-wire Kelvin test; expedite options; Oct 1-4 holiday effect.
13. (Rev B, not this order) Filled-and-capped microvia in a 0.225 mm BGA land: 0.10 hole (ring 0.0625) or 0.075 hole (ring
    0.075) -- accepted, on which outer prepreg, at what cost?

## 13. User decisions

1. **Approve the stack + microvia**: `JLCH061611N2-2116` as named with 0.15/0.30 as the rule-guaranteed baseline; authorise
   asking for 0.12/0.27 and switching the four rule values if JLC say yes.
2. **DiffPairsRouting**: keep 0.150/0.150 (87.8, nearer 90) or move to 0.162/0.150 (hold today's 85.3); either way freeze only
   after JLC's own figure. Stage 9's "may USB ship broken in rev A" decision is still open and interacts: if USB is deferred the
   value is moot for rev A.
3. **Inner power floors**: keep 1.05/1.10/0.50 or relax to 0.55/0.60/0.25 once 1 oz inner is on the acknowledgement (DRC-only;
   no copper moves; void if 0.5 oz is honoured).
4. **Buried L3-L4 via**: keep it in the structure (unknown fee, +lamination) or drop it (plain 2+2+2 with stacks only); no plan
   depends on it until priced.
5. **Via-in-pad at ring 0**: not in this order; ask JLC question 13 for rev B, or not.
6. **Budget**: +$123 (+66 %) and +4 days over the standard board, plus the unpriced buried/lamination/copper-fill items.
7. **Lift the U1 land-field via ban for microvia spans only** (`field_ok`): the blanket rectangle was the user's constraint and
   every gate was built on it (stage 9 decision 2).
8. **If the L2 test via shows no landing pad for a foreign-net stack**: convert L2-GND / L5-VCC3V3 to signal layers with full
   polygons (a structural edit of the file with its own verification chain), or restrict stacks to GND/VCC3V3 nets and use
   Structure A's spans for signals -- decide after the 10-minute test, not before.
9. Still open from stage 9: the MUST 52, the 2 GND ties (R15-1, U2-5) by hand, teardrops, final DRC, IBIS, fab outputs.

## 14. Corrections to the record

1. Brief: `route_inputs.json` md5 `f5903da8` -> `e166d74a` (hdi block added; geometry identical). Brief: 1518 tracks is the
   JSON's copper-layer count; the PcbDoc holds 1526 track records (+4 on L2-GND, +4 on L5-VCC3V3: split-plane boundary lines).
2. Brief: via census 155/136/86 holds only with GNDADC (2) counted as GND and VCC1V8/VCC1V0/VCCADC (20) as "signal"; by net name
   157 / 134 / 86.
3. Brief: "203 at a 0.35 land" IS a grid count (123 vacant cells + 80 moat interstitials, pre-copper), and "447 at <= 0.30" is
   pre-copper too; with today's placed copper the counts are 87 (<= 0.30) and 41 (0.35).
4. Brief: 0.241124 mm is the 0.5001-pitch maximum; the binding minimum is 0.240946 (0.4999 pitch); `docs/via_land_decision.md`'s
   0.240941 is 5 nm off.
5. Brief: "a 0.10 mm microvia is ILLEGAL on N2-2116; it needs a 0.15 hole (pad 0.30)": the rule's minimum is hole >= 0.112, so
   0.12/0.27 is legal if JLC laser non-default sizes; 0.15/0.30 is the default-size choice.
6. Brief: "26 placed Top-only stubs" -> 24 signal-net Top-only vias (107 in all), invariant to endpoint tolerance 0.2-50 um.
7. `docs/stack_switch_3313E.md`: the "two independent 2-D FEM solvers" exist nowhere on disk nor in git history; 87.37 ohm is
   reproduced by no width/gap/mask combination (file mask 85.3, Altium stock mask 91.1, substrate-only 87.9); "bit-for-bit
   unchanged on both stacks" has no surviving instrument. Absolute pair values carry +-5 ohm of mask-model spread.
8. `altium_microvia_facts.md`: "(74,1,0)" is wrong -- byte 30 = 32 (Bottom) on all 377 vias; the KiCad offsets hold.
9. u1_sites finding: its impedance table (z0.py) was grid-biased (1080 solved at an effective 0.090 mm); corrected 1080 shift on
   the pair -4.1 ohm (-4.7 %), not -2.1; 90-ohm width on 1080 0.118-0.128, not 0.140; 2116 +1.7 (aligned z0.py) / +2.5
   (impedance solvers).
10. u1_sites finding: "(b) reaches 16 ring-0 signal balls / 49 of 82" -> 0 ring-0 signal balls (the 16 are GND, VCC3V3 and
    no-net); (b) serves 33 ring-1 + 35 ring-2 = 68. Its "all 42 ring-0" under (a) is 40 (T1, U1 refused). Far ends 8/8/8, not
    8/9/7. Pads6 shape byte is 49, not 72 (all 238 lands circles; the rectangular-land uncertainty is dropped).
11. u1_sites recommendation "(c) 0.10/0.25 on a 1080-outer 2+2+2 as the nothing-waived baseline" is refuted by the impedance
    workflow: 1080 on L2-L3 drops the placed SDRAM bus to 45.2 ohm (0.086) / 43.1 (0.0784) and wants 0.105 / 0.092 mm on
    607.8 mm of placed copper; its hdi.json laser-to-mechanical 0.44 -> 0.39 (0.10/0.25) / 0.415 (0.15/0.30).
12. dfm_rules finding: "hdi.json = the exact tools/hdi.json content" -> the live file is still the through-only default
    (b05f58bb); its proposal (39a1f943) and now this one (dab6ffb3) are proposals. Its headline "zero margin" -> the placed
    different-net minimum is 0.2430 hole-edge; the 8 pairs at 0.2400 are same-net (JLC 0.13). Its 0.2411 interstitial figure is
    the first cell; the grid minimum is 0.2410.
13. impedance finding: the Cohn calibration numbers are not what its validate.py prints (K(k)/K(k') inverted); correct Cohn
    67.52 / 48.47 / 31.54, solvers within 1.8 %; the thick-copper microstrip cases rest on three-solver agreement, not on a closed
    form; "USB full-speed" -> U2 is an FT2232HL, USB 2.0 Hi-Speed (docs/zulu_a7-bom.csv line 44, in Zulu_A7/docs, not
    Zulu_Altrium/docs as memory says); "w = g has no solution on 1080" -> crosses 85.3 at about 0.115-0.120 (bracketing
    failure); N2-2116 SDRAM slot should be PP resin (50.39, +0.2); "every comparison is a delta under one model" -> one solver
    but two Dk sources (+1.4..+3.8 on the pair).
14. `tools/route_inputs.py EDGE_CLEARANCE = 0.25` is 0.025 short of JLC's 0.35 hole-edge for a 0.075-ring via (land-edge 0.275);
    harmless while the 0.80 convention binds. `tools/route_reach.py:197` (stage 9 correction 1) still bans the whole land field.
15. `tools/hdi.py`: `field_ban()` conflates via-in-pad with field permission, and `usable()` never proposes a stack -- both must
    change before any gate can use the 87 in-field sites.

## 15. Unmeasured, stated as such

Whether AD26's Via Types dropdown offers plane layers; whether a foreign-net microvia stacking on a negative plane layer gets a
landing pad in the Gerber; whether PlaneClearance measures from hole or pad edge; whether `IsBuriedVia`/`IsThruVia` work outside
Routing Via Style scopes; JLC's 6L 2-step layer pairs, discrete laser sizes, foil-in-aspect reading, buried/lamination/copper-fill
fees, stack-review lead time; the 0.930 core's Dk; the pressed 2116 thickness; whether 1 oz inner really ships; the effect of the
L2 plane-web constraint on the 41-ball matching; JLC's laser position tolerance against the 0.9 um interstitial margin at
0.30 (the reason 0.27 is asked for).
