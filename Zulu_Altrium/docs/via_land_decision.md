# Via land: 0.30 mm or 0.35 mm on a 0.20 mm drill — 2026-09-14

**Decision, 2026-09-14 (the user): 0.35 mm everywhere, with teardrops.** Applied by `SetViaLand035` in `tools/ZuluSetup.pas`; see the note at the end for the verification. Prompted by JLCPCB's unasked-for advice in their
2026-09-14 reply (`board/JLCPCB-DFM-ENQUIRY-2.md`): *"our standard recommendation is a minimum
annular ring of 0.075 mm (3 mil), which corresponds to a 0.20 mm drill on a 0.35 mm pad. While
0.20/0.30 mm can be produced with high-precision registration, adding teardrops … is strongly
recommended."* The board's `RoutingVias` rule is 0.20 / 0.30, min = max = preferred, and
`Vias6` is empty — nothing is routed, so the choice is free.

Two advocates, one neutral quantifier, a refuter on each, and a judge (2026-09-14, 1.13 M
tokens); every number below survived refutation from `Pads6`/`Rules6` or is marked as general
knowledge. My own independent census of the ball map gave the same structural answer.

## The fact that decides it: this package never needs an interstitial via

`Pads6`, U1's 238 lands on a 19 × 19 grid: rings 0–2 fully populated (72 + 64 + 56), a
**three-ring-wide vacant moat** (rings 3–5, 120 sites), a 7 × 7 core (46 balls; K9/K10/K11
empty). The core is **entirely GND and power**. Every signal ball is in rings 0–2: it either
escapes on Top (rings 0–1, one 3 mil lane per ring-0 gap; the eight no-net balls are all in
rings 0–1) or dog-bones one pitch *inward* into the moat and vias there (ring 2). Core power and
GND chain ball-to-ball and via in ring-5 sites.

| via position | centre → nearest ball-land edge | 0.30 land needs 0.240 | 0.35 land needs 0.265 |
|---|---|---|---|
| vacant grid cell (moat, K9–K11) | 0.387350 mm | **+0.147** | **+0.122** |
| interstitial (diagonal) | 0.240941 mm | +0.00094 (0.9 µm — already rejected as unmanufacturable) | **−0.024, impossible** |

Moat capacity 108 legal cells at 0.35 (110 at 0.30; the Bottom 0201 caps block the rest);
verified lattice demand 51–59 vias. **Vias geometrically forced to 0.30: zero.** So the
"0.35 where it fits, 0.30 where it doesn't" mix has nothing to do.

## Pros and cons, by topic

| topic | 0.30 mm land (0.05 mm ring) | 0.35 mm land (0.075 mm ring) | decisive? |
|---|---|---|---|
| **Reliability** | Ring equals JLC's published floor. JLC's capability page gives hole-position tolerance ±0.05 mm — that alone takes a 0.05 ring to **zero** on one side; layer-to-layer registration is unpublished and adds to it. 8.25:1 holes, 0.0152 mm inner copper, every via sees two reflows (138 parts Bottom / 35 Top). Ordering against the fab's written advice. | JLC's own recommendation, volunteered. Keeps **0.025 mm of ring at a 0.05 mm shift**; breaks out only at 0.075. The only option with any IPC Class 3 external window *(general knowledge)*. Teardrops still wanted — they protect the trace-to-land junction, the ring protects the barrel: different failure modes. | **yes** |
| **Escape inside U1** | fits every moat cell (+0.147); interstitial legal by 0.9 µm | fits every moat cell (+0.122); interstitial impossible — and never needed | **yes** |
| **Lane density outside** | binding via pitch **0.40 mm** (hole-to-hole 0.20 governs) | binding pitch **0.44 mm** (land + 0.09): +10 %; 16–24 % fewer via slots in every band — west corridor ~150 vs ~185, east 46 vs 61, bottom ~90 vs ~116, SDRAM strip ~150 vs ~183. **Every band still holds 2–8× the quoted demand** (west ~18 forced, east 26, north-face 18; 64–105 outside-array vias total, land-independent). SDRAM strip lanes per layer at a y with 0/1/2/3 vias: 16/14/11/9 → 16/13/11/8. One lane between via rows needs pitch ≥ 0.556 → ≥ 0.606; at exactly 0.60 pitch 0.35 loses the lane. | no — headroom, not capacity |
| **Plane erosion L2/L5** | anti-pad 0.20 + 2 × 0.25 = **0.70 mm**; GND relief void 1.716 mm | **identical** — PlaneClearance is hole-referenced. (Top/Bottom pour voids are land-referenced and grow 0.05 mm.) | no |
| **Via-to-pad elsewhere** | no via fits between 0201s (0.300 streets), U8 pins (0.41), U2 (0.22), U3 (0.35) | same list impossible; +0.025 mm standoff per via beside a pad | no |
| **Mask under U1** | web between adjacent-cell vias 0.0999 mm vs the 0.100 sliver rule — tenting / 0-expansion via rule needed by 0.13 µm | web 0.0499 — same rule needed, by 50 µm | no (needed at both) |
| **Cost** | inside JLC's "0.2/0.25 mm hole with via diameter < 0.45 mm costs more" line | **same tier** | no |
| **Altium** | nothing to edit | one value in `RoutingVias` (0.30 → 0.35) plus `tools/ZuluRules.pas` lines 188/420 so a re-run does not revert it | no |

## Recommendation

**0.20 / 0.35 everywhere, min = max = preferred, teardrops on every via; no per-position mix.**
The mix existed only to keep 0.30 where 0.35 cannot fit, and no via needs such a position. What
0.30 was supposed to protect — plane copper, price — does not move with the land. What 0.35
buys is the only thing a land is for: a ring that survives JLC's published ±0.05 mm hole
position where a 0.05 ring goes to tangency, on the one package the board cannot afford to
lose. The measured cost is 10 % on via pitch in bands that hold several times their demand.

Keep 0.30 as a **documented, DRC-scoped exception** — a second Routing Via Style rule inside a
drawn Room — to be created only if detailed routing shows one band binding (the SDRAM strip is
the candidate). Never board-wide, never at an interstitial position.

## If adopted — the steps

1. `Design ▸ Rules ▸ Routing ▸ Routing Via Style ▸ RoutingVias`: via diameter min = max =
   preferred **0.35 mm**; hole stays 0.20. Then `tools/ZuluRules.pas` lines 188 and 420: 0.3 → 0.35.
2. Router settings: via-to-via pitch ≥ 0.44 mm; adjacent 0.5 mm moat cells stay legal (0.150 land
   gap, 0.300 hole gap).
3. Add a solder-mask rule for vias under U1 (0 expansion or tented) above the global 0.05 rule;
   also for any 0.44-pitch via column. Needed at either land.
4. After routing, before Gerbers: `Tools ▸ Teardrops` on all vias and pads, *Force teardrops* OFF so
   the 0.09 Clearance DRC still catches one that does not fit (tight spots: moat via to ring-2 land
   0.212 mm; 0.44-pitch columns). Teardrops are primitives, not a rule — a checklist item.
5. Verify: one test via on a moat cell, one beside a ring-2 ball, two at 0.44 pitch; DRC clean;
   open the L2 plane preview and confirm the 0.70 mm anti-pad (settles hole- vs land-edge for good).
6. Refresh `docs/routing_readiness.md`: its 0.39 mm via pitch violates HoleToHole 0.20 by 0.01 at
   *either* land; the west corridor is 3.8375 mm (U2 moved), not 2.3625; the anti-pad is 0.70, not 0.80.

## What would change the answer

- A band that binds at 0.44 pitch in detailed routing → the scoped 0.30 Room rule for that band.
- JLC confirming drill-to-pad registration ≤ ±0.025 mm on this line, or that 0.20/0.30 orders
  are routed to the high-precision process automatically → 0.30's 10 % becomes worth taking.
- JLC confirming their +0.13/−0.08 mm through-hole size tolerance applies to 0.20 mm via drills →
  a +0.13 drill eats *both* rings; the answer moves **up** (0.40), not down.
- The anti-pad turning out land-referenced in this Altium build → +0.05 mm per plane void under
  U1 at 0.35; real but small. Step 5 settles it.

Two questions worth sending JLC without blocking on them: the layer-to-layer registration
tolerance on the 6-layer line, and whether the hole-size tolerance applies to via drills.

## Applied

`SetViaLand035` sets `RoutingVias` to hole 0.20 / land 0.35 mm, min = max = preferred, and
`tools/ZuluRules.pas` now writes the same so a re-run cannot revert it. **Verified from the saved `Rules6` 2026-09-14:** `RoutingVias` MINWIDTH = WIDTH = MAXWIDTH =
13.7795 mil (0.35 mm), holes 7.874 mil (0.20 mm); it is the only rule that changed against the
previous commit (50 rules before and after); pads, tracks and texts identical as multisets;
`verify_widths.py` and `verify_stack.py` still PASS. The mask-tenting rule for vias (step 3) and the
teardrops (step 4) are routing-stage items and go with the fan-out.
