# Stage 6: the 140 signals on the freed board — 86 of 140, NOT PLACED (2026-09-28)

**Status: NOT PLACED. The board is untouched at commit `a87c4af`**, PcbDoc md5
`33aece2b03e9037466e366447c81a32d`. The final plan is kept in the session scratchpad
(`stage6/judge/plan.json`, md5 `b9d65ab43a30afab43ec633a93876a16`, 139 vias / 916 tracks / 1531.99 mm;
`gen.py --check` reproduces it). The toolkit is committed under `tools/stage6/`.

## What was run

One workflow, 18 agents: a shared fix base, then three routers each in four sequenced stages —
a global assignment with **no geometry**, two routing stages, a repair stage — then two adversarial
reviewers per router and a judge. The structure was chosen against the way the stage-4b attempt failed
(`docs/stage4b_attempt.md`): seven regions planned in parallel with nothing arbitrating the corridors
they shared.

| | closed of 140 | route_reach left routable | foreclosed pads |
|---|---|---|---|
| escape-first | 78 | 25 of 54 | 13 |
| corridor-first | 88 | **0 of 43** | 15 |
| hardest-first | 86 | 43 | — |
| **judge (hardest-first + 7 fixes)** | **86** | **21 of 46** | **14** |
| *for comparison, stage 4b (2026-09-22)* | *92* | *0 of 35* | *10* |

**Verdict: DO-NOT-PLACE.** 86 of 140 closed, 25 connections permanently walled off, 14 pads of nets
the plan does not own foreclosed. The board it produces cannot be configured, clocked over JTAG, or
talked to over UART or USB.

## Why this is a structural result and not a routing failure

The premise going in was that stage 5 and 5b had freed the board. Measured, they had: the worst-loaded
cut-line is U1 west at 45 crossings against 276 lanes (**16.3 %**), straight-line demand over all 140
is 2115 mm against roughly 25 000 mm of capacity, and the north band went from 439 lanes to 669 with
L4 alone going 0 → 205. **No corridor is close to full, and three independent routers still could not
close more than 88.**

- **26 of the 140 are open in ALL THREE plans.** 114 is therefore the ceiling of any composition of
  them — and **0 of 34+ attempted grafts survived `route_emit`**, so the real ceiling of composition
  is 88.
- **U1's east face is finished as a routing surface.** Of the 17 east ball rows still owing a
  connection, the widest legal straight Top run east out of the board's own fan-out stub end is
  **negative on all 17**, and 13 of those are walled by board copper that may not be touched (GND vias
  at 51.400/16.400, 51.400/11.400, 51.900/8.900; VCC3V3 vias at 51.400/15.900, 51.950/12.450,
  51.850/11.850; GND tracks at 51.900–52.000). All three routers reached this independently.
- **The closure/foreclosure curve is steep and unfavourable.** Four re-measured points: 86 closed /
  25 walled, 88 / 44, 88 / 43, 90 / 44. **Every closure past 86 costs roughly five connections that
  can never be routed afterwards.** The judge chose 86/25 because a walled-off connection is
  permanent and an open one is not.

## The three-way contention at U2's west face

**FT-REF (U2-6 → R18-2), the USB differential pair, and U2-5's GND tie want one corridor, and closing
any two costs the third.** Proved in both directions with `route_width`, with and without the approved
FT-VPHY re-cut. The judge kept the pair and left FT-REF open and U2-5 untied — but **FT-REF is the
FT2232H's PHY bias: without it USB will not enumerate however good the pair is**, so that choice is
not worth much on its own. Closing FT-REF needs a placement change.

**The FT-VPHY re-cut does not help, and the reason I gave for it earlier was wrong.** Legal 0.35 mm
via sites in x 23.5–28.6, y 14.4–17.5 are **0 before the re-cut and 0 after**, for GND, FT-REF and
FT-VPHY alike. What makes that band via-dead is copper that may not be touched: the Bottom VCC1V0 rail
(1.500 mm, y 13.715–15.240) forbids via centres up to y 15.505, the L3-SIG VCC1V8 rail (0.800 mm,
y 17.100–17.900) forbids them from y 16.835, and the surviving 1.33 mm strip is taken by LD3-K, U2's
own pad column and the CKE / SDRAM-CLK / UDQM / GND vias at their 0.44 mm pitch. The re-cut frees
exactly **one Top track lane**, and FT-VPHY's only legal replacement paths at its 0.15 mm
`Width_PWR_RAILS` minimum all cross the USB pair's only corridor. Cost was never the objection:
the cheapest east option is +24 mΩ, +1.4 mV at 60 mA on a bead-isolated rail with C40 local.

## What did hold

- **Board integrity, everywhere it was measured**: `tie_check` VCC3V3 129/129; `gnd_check` 203 tied,
  the same three pads as the bare board; L5 one island at 100.0 % with 133/133 pads and 86/86 vias on
  it; L2 one island at 100.0 % with 216/216 pads and 133/133 vias.
- **Buildability of the judge's plan**, audited independently of `route_emit`: 0 duplicate primitives,
  0 track ends mid-span, 0 segments below the 0.0762 mm minimum, 0 clearance violations with both
  nets' rules applied, tightest clearance 0.0908 mm against a 0.09 rule.
- **The USB pair passes `DiffPairsRouting`** as the PcbDoc states it: 0.150 mm wide, 2.068 mm of
  16.38 mm uncoupled against a 3.0 mm limit, skew 0.527 mm. Neither of the other two plans' does.

## A gate bug this found, now fixed (commit `84b6812`)

`tools/route_emit.py`'s track-vs-track loop compares against `max(own clearance, the other net's)`,
but its **track-vs-via and track-vs-TH-pad loops used the track's own clearance alone**. A non-SDRAM
track passing an SDRAM via on L3/L4 was checked at 0.09 where `Clearance_SDRAM_INNER` needs 0.10
(0.20 for SDRAM-CLK), and the gate passed it — reproduced on a CHAN21 L3-SIG segment 0.0986 mm from
the D0 via at (45.250, 4.400). `tools/stage6/segw.py` had the same hole twice: `gap_for()` was defined
*below* the via, through-hole and SMD-pad loops and used only by the track loop, and it ignored the
routed net's own class.

**The placed board is unaffected**: every one of its 1498 tracks was audited against every via and
through-hole pad using both nets' clearances — **0 violations**. Stage 5's plan still checks clean
against its own pre-board with the fix in place.

## What has to change, and it is a placement decision

Three independent routers on a board with 16 % corridor load, plus the earlier stage-4b attempt and
Altium's own Situs, have now all stopped between 86 and 92 of 140. **The board cannot be finished by
routing alone.** The levers, in the order they were measured to matter:

1. **U1's east face** — the 17 east ball rows with no legal straight escape. This is the big one and
   it is a re-pin or a placement change, not a route.
2. **FT-REF versus the USB pair versus U2-5** — needs R18 moved next to U2-6, or the
   CKE/SDRAM-CLK/UDQM via cluster or LD3/LD5 moved out of the y 15.5–16.8 strip.
3. **The unspent approvals** are still available and still measured good: the AIN16_N via move at
   (43.300, 3.200) takes ANALOG-IO1's corridor from 0.119 to 0.397 mm and lets **both** R13-2 and
   R15-1 be tied (1.45 mm to a new via at (43.275, 3.525) and 3.23 mm to one at (44.575, 3.200)).

## One contradiction to settle before any further routing

The PcbDoc's `DiffPairsRouting` rule says `MINLIMIT = MAXLIMIT = MOSTFREQGAP = 0.150 mm`.
`docs/` and the stage briefs say **0.15 wide at a 0.125 gap**, and 0.125 is the number the 87.4 Ω
2-D FEM figure came from. The judge routed to the file. **If 0.125 is what is wanted, the RULE is
wrong and must be edited — not the copper** — because a 0.125 gap will DRC-error on every segment of
the pair.
