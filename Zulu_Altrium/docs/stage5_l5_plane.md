# Stage 5: L5 becomes the VCC3V3 plane — placed 2026-09-23

**Status: PLACED, SAVED, DRC-EQUIVALENT TO THE BOARD BEFORE IT, VERIFIED FROM THE SAVED FILE.**
`PlaceStage5` / `RemoveStage5` in `tools/ZuluSetup.pas`; `AssignL5ToVCC3V3` in `tools/ZuluPlaneNets.pas`.
`tools/stage5/gen.py --check` rebuilds `tools/stage5_route.json` (md5 `9929b08288e4238eb24696f3f8ab442f`):
44 vias, 98 tracks (107.044 mm), removing 14 vias and 289 tracks (411.981 mm), all on VCC3V3.

## Why

Stage 4b ran out of routing room. Our planners closed 92 of the last 140 signal connections; Altium's
own Situs closed 90 and failed a *different* 50 — a global capacity shortage, not one blockage
(`docs/stage4b_attempt.md`). VCC3V3's routed trunks blocked 370 mm2 of a 1774 mm2 board, 213 mm of it
inside the U1 surround and 88 mm in the north band, exactly where the open flash, LED, SD and CHANx
connections have to pass. Moving VCC3V3 onto L5 returns that area.

## Why it is electrically sound on THIS board

The stack is Top / L2-GND / L3-SIG / L4-SIG / L5 / Bottom with copper-face gaps 0.0994 / 0.1000 /
1.1208 / 0.1000 / 0.0994 mm, so **Top and L3 reference L2, and L4 and Bottom reference L5**.

Read from the pad list, not from prose: **every I/O bank on this board is 3.3 V.** U1's rails are
VCC3V3 on 28 balls, VCC1V0 on 8 (G10 H10 J10 L10 M10 M11 N10 N11), VCC1V8 on just **3** (C9, H13, J13
— the CPG236 VCCAUX pins, not a bank) and VCCADC on one (C13). **U3, the SDRAM, runs on VCC3V3 and GND
alone.** So L4 and Bottom end up referenced to the same potential as the I/O supply of the signals on
them, which is the textbook arrangement provided the VCC3V3-to-GND decoupling is distributed — and
46 capacitors sit between the two rails. See "What this costs" for where that argument is weakest.

## What changed

| | before | after |
|---|---|---|
| PLANE2 (`L5-GND`) net | GND | **VCC3V3** |
| PLANE1 (`L2-GND`) net | GND | GND (unchanged) |
| VCC3V3 tracks | 354 (468.09 mm) | **163 (163.15 mm)** |
| VCC3V3 vias | 51 | **81** |
| board tracks / vias | 1679 / 331 | 1488 / 361 |
| every other net | — | **byte-identical**: GND 336 tracks / 128 vias, VCC1V0 74/7, VCC1V8 46/10, VU 53/2, FT-VCORE 33/3, FT-VPHY 21/3, FT-VPLL 16/3, VCCADC 13/3, GNDADC 17/2 |

The plane net lives on the **split-plane polygon**, not in the Layer Stack Manager — Altium 26 exposes
no net field for a plane layer. `AssignL5ToVCC3V3` sets it and reports back
`Internal Plane 2 -> VCC3V3` twice and `Internal Plane 1 -> GND` twice: **four polygon objects, two per
plane**, which is what `ZuluPlaneNets.pas`'s header predicted (the pour comes back as ObjectId 11, a
region, alongside the stored Split Plane polygon). After it, `Tools > Split Planes > Rebuild Split
Planes on All Layers`, then Ctrl+S.

## What it buys (`tools/stage5/capacity.py`, measured on the saved board)

| | before | after | gain |
|---|---|---|---|
| Top | 812.7 mm2 | 864.9 | +52.1 |
| L3-SIG | 1205.9 | 1197.4 | **-8.5** |
| L4-SIG | 1183.0 | 1262.5 | +79.5 |
| Bottom | 791.5 | 888.1 | +96.6 |
| **total free for a 3 mil track** | **3993.1** | **4212.8** | **+219.7 mm2** |

Lanes for a 0.0762 mm track at 0.09 clearance (centres 0.1662 mm apart) across the two corridors the
open stage-4b nets must cross:

| cut-line | Top | L3 | L4 | Bottom | total |
|---|---|---|---|---|---|
| north band y 19.6, x 5-39 — before | 141 | 203 | **0** | 95 | 439 |
| north band — after | 150 | 202 | **205** | 112 | **669** |
| U1 east x 52.9, y 2-24 — before | 15 | 115 | 114 | **4** | 248 |
| U1 east — after | 46 | 121 | 121 | **94** | **382** |

Stage 3's 1.50 mm L4 spine had blocked L4 **completely** across the north band, and its 1.30 mm Bottom
column left Bottom 4 lanes down the U1 east corridor. The ceiling — strip *all* VCC3V3 copper, which no
legal plan can do because the pad ties must stay — is 671 and 391, so this plan takes 99.7 % and 96.6 %
of what is available. The U1-east shortfall is geometric: C119-1, C121-1 and C122-1 are Bottom 0201s at
x 53.2501 and there is no legal via site east of them, so three crossings of that line are forced.

L3-SIG is the one layer that ends worse: -8.5 mm2 and 203 -> 202 lanes, the cost of 44 new through-hole
barrels through a layer that gains nothing back.

## Gates, on the board as saved

```
python tools/stage5/tie_check.py --net VCC3V3
    VCC3V3: 124 SMD pads, tied 124, untied 0; 81 vias, 4 TH pads        exit 0
python tools/stage5/plane_islands.py --net VCC3V3 --plane L5
    338 anti-pads; 128/128 pads over the main island; 81/81 vias on it  exit 0
python tools/stage5/plane_islands.py --net GND --plane L2
    285 anti-pads; 211/211 GND pads; 128/128 GND vias on the main island exit 0
python tools/stage5/gnd_check.py        198 tied, the same 3 untied as before (no regression)
python tools/stage5/verify.py           18 of 18 checks pass
python tools/route_reach.py             140/140 routable, none walled off
python tools/route_foreclosure.py       none foreclosed, 207 pads audited
python tools/route_width.py --net USB_D_P/USB_D_N   0.539 mm both rows (floor 0.45), unchanged
python tools/route_stitch.py            whole board 25462 -> 31042 sites (121.9 %)
```

`route_emit` reports VCC3V3 as "DISJOINED BY THE PLAN" and that is correct: it models VCC3V3 as a
routed net and cannot see planes. `tie_check.py` is what proves VCC3V3 complete now — a pad is
connected when its copper island holds a via, because the via reaches the plane by the Direct
`PlaneConnect_Vias` rule. For the same reason `gnd_check.py` and `signals_check.py` exit 1: both did
so on the board before this stage too, for the same three GND pads and with VCC3V3 as the only net
whose island count changed.

## DRC, side by side (`docs/drc_stage5_2026-09-23.drc` against `docs/drc_stage4a_2026-09-21.drc`)

| rule | stage 4a | stage 5 |
|---|---|---|
| **Un-Routed Net** | **144** | **144** |
| Net Antennae | 53 | **50** |
| Width Constraint | 7 | 7 |
| Clearance Constraint | 3 | 3 |
| Dead copper | 2 | **3** |
| Starved Thermal | 2 | **1** |
| Silk, Short-Circuit, Hole Size, Solder Mask Sliver, Modified Polygon | 1 each | 1 each |

**Un-Routed Net staying at 144 is the confirmation that matters**: VCC3V3's 113 connections did not
become unrouted when its trunk was deleted, because the plane closes them. Three antennae went away
with the trunk stubs; the starved thermal on L5-GND went away because X2-20's GND relief no longer
exists there (its L2 relief, still 3 of 4 entries blocked, is unchanged and pre-dates this stage). The
extra dead-copper region is 0.125 sq. mm — see below.

## What this costs, honestly

1. **THE REFERENCE-PLANE CHANGE, and it is not fixed by copper.** 52 signal vias join a layer
   referenced to L2-GND to one referenced to L5-VCC3V3, so their return current can now only cross
   through a VCC3V3-to-GND capacitor. Counted on the placed board: **39 SDRAM**, 8 XADC, 5
   LED/charger. Median distance to the nearest such capacitor **3.36 mm, worst 12.70 mm**, against a
   median 1.62 mm to a GND via before. There is **no VCC3V3-to-GND capacitor anywhere in the band
   x 12-39, y 6-25.4** — the 46 of them sit in the y 3.0-4.2 row, the x 41-57 cluster round U1, and
   three at x 2.6-7.6 — while U3's north-side vias sit at y 15.6-17.15. Interplane capacitance does
   not rescue it: L2 and L5 are 1.3512 mm apart, about 44 pF over the whole board, 25 ohm at 143 MHz.
   *Mitigation priced (five 0201 100 nF on Bottom/Top at (37.000,8.350), (26.000,8.875),
   (17.925,7.525), (25.100,19.200), (17.875,16.825), each with a free 1.10 x 0.70 envelope, a legal
   via site 0.55 mm away and a GND via within 1.6 mm): the SDRAM median goes 3.30 -> 2.75 mm, the worst
   12.70 -> 8.54 mm, and the count beyond 5 mm falls from **11 to 3** (D11, D10, D13 on U3's north data
   row). That is a schematic change and is the open user decision.*
2. **A 0.125 sq. mm region of dead plane copper**, reported by Altium's own Split-Plane DRC, added to
   the two already accepted. `tools/stage5/plane_islands.py` finds it 4-connected as a 0.48 mm2 patch
   at x 48.648-49.148, y 12.208-13.588, walled in by the VCC1V8, CHAN and GND vias that punch L5 only
   once it stops carrying GND. **No plan creates it and none can remove it** — the bare board with
   L5=VCC3V3 and no plan at all gives the identical stray list — and it holds no VCC3V3 via and no
   VCC3V3 pad. It is floating copper, not a connectivity fault. A new via cannot fix it: it lies
   inside U1's land field.
3. **Seventy-five of the 78 tied pad islands now have exactly one barrel.** Thermally that is nothing
   (a 0.20 mm hole with 25 um plating carries 200 mA at about 0.13 C), but each is a single plated
   barrel where a redundant copper mesh used to be. The worst is **(27.9300, 4.8500) with nine pads**
   behind it — C135-2, C136-2, C137-2, C138-2, C3-2, C4-2, U2-20, U2-31 and U3-14. It cannot be split:
   `corr.via_sites` returns zero legal via cells within 2.2 mm.
4. **Four long ties that could not be shortened**, each with a measured reason and each fixable only by
   a component move or a schematic part: U2-31 9.145 mm / 28.104 mohm, U2-50 6.672 / 12.900, U3-9
   6.371 / 15.655 (3.5 mm *longer* than before this stage), C113-1 6.308 / 15.175 — the worst
   decoupling loop on the board, a 0201 on U1's VCCO grid.
5. **Two GND stitching windows end below 100 %**: Bottom channel x 12-28, y 2.1-2.6 at 62.2 % (45 -> 28
   sites) and south band x 11-31, y 2.0-4.6 at 84.9 %. Three new vias sit inside them, placed there
   because the 1.50 mm Top VU rail at y 4.949 rules out y 3.93-5.97. Board-wide, stitching is +21.9 %.

## What it gains electrically

The plane is a far better conductor than the trunk it replaces. A nodal solve over the plane mesh at
0.05 mm (Rs 1.1316 mohm/sq for 0.0152 mm inner copper, vias 0.9733 mohm/mm, source at L1-2) puts the
worst DC drop at a load pad at **3.667 mV (U2-50 at 70 mA)** against stage 3's measured 14.3 / 14.6 /
15.6 mV — a factor of about four. The regulator reaches the plane through **three** barrels beside the
output capacitor C80-2 carrying 260.0 / 246.9 / 238.1 mA, each under 1 C rise, and **no current crosses
U5-4, the SC189's VOUT sense pad** (the first draft put 253.5 mA across it). The load model is the
745 mA sum of `tools/stage3/parts/regions.json`; `docs/stage3_vcc3v3.md` says 667 mA for the same rail
and one of the two is wrong — 745 is the conservative figure and the drop conclusion holds either way.

## How it was planned

One workflow, 13 agents: three surveyors (the removal set, the tie vias, the electrical audit and rule
list), three planners in parallel biased maximal / balanced / conservative, two adversarial reviewers
per plan on an electrical and a manufacturing lens, then a judge that rebuilt the winner and re-ran
every gate. The judge took the **balanced** plan because it is the only one of the three that passes
`route_emit` with zero problems against the rules *as they stand* — the maximal plan needs
`Width_PWR_VCC3V3`'s Bottom floor dropped from 0.20 mm to 0.0762 mm board-wide for 59 stubs, and the
conservative plan leaves six Net Antennae and 3.015 mm of floating copper and still needs that same
relaxation for one stub — while reaching the same 669 north-band lanes as the maximal plan.

Four repairs the judge grafted, each re-measured: board tracks 93 and 96 restored so U2-31 and U2-20
join end to end instead of by a 0.075 mm pad overlap; the in-field via (44.4001, 9.8999) restored so
all 14 VCC3V3 vias inside U1's land field survive; the regulator's second plane entry moved off U5-4
onto C80-2; and C111-1 given its own barrel instead of sharing one with three other 100 nF parts.

**A gate bug the reviewers caught and I fixed:** `tools/stage5/plane_islands.py` labelled the raster
8-connected, so two plane regions meeting at a single diagonal pixel — a pinch of zero width that
conducts nothing — counted as one island. It is the failure the gate exists to find. It now labels
4-connected, reports the stray area, and also checks that every via of the plane net lands on the main
island, which is the substantive test since a pad reaches the plane through a barrel and not by lying
over copper.

## Still open

- **The five stitching capacitors** (cost 1 above) — a schematic change, awaiting a decision. Doing it
  before stage 4b is much cheaper than after, because the five sites are free space today.
- The **layer is still named `L5-GND`** while carrying VCC3V3. No design rule names it
  (checked: zero rules reference `L5-GND` or `L2-GND`), but `tools/verify_stack.py` hard-codes the
  string in three places and a fab reading the layer name would be misled. Rename to `L5-PWR`.
- U2-5, R15-1 and R13-2 are still the three untied GND pads from stage 4a's open decision.
- Then: stage 4b as one global route, the NODE_P1 hop, teardrops, final DRC, IBIS, fab outputs.
