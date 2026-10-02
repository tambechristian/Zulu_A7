# HDI routing gain, measured: 26 -> 32 / 35 of 50 -- the order is NOT worth placing on this evidence (2026-09-30)

**Nothing placed.** Workflow wf_0161d538, 6 agents, 1.05M tokens: stage 9's router reproduced exactly (26 of 50,
same 24 open lines, same 35-via plan), then made via-span aware, then run on two Structure-B arms with identical
commit order and budget, each adversarially verified, then judged. Structured result: docs/hdi_gain.json.

| arm | MUST closed of 50 | hubs untied | route_reach after the plan | via objects |
|---|---|---|---|---|
| through (today) | **26** | 0 of 4 | 105 -> 104 (CHAN7) | 35 |
| B-banned (U1 land-field ban kept) | **32** | 1 (FT-REF) | 101 -> 95 (6 walled off) | 91 |
| B-field (ban lifted, spec decision 7) | **35** (34 gate-clean) | 1 (FT-REF) | 100 -> 93 (7 walled off) | 112 |

Still open in the best arm (15): CFG-M0, CFG-M1, PUDC_B (every configuration strap), FLASH-D00/D01/D02 x2,
FPGA-TDI, TDO, PROG#, DONE, RST#, FT-RESETN (U2's RESET# pull-up), UART_FT_RXD x2. **A board that cannot be
configured is not worth fabricating in any technology.** Both HDI plans also seal the U2-5 GND tie.

**The survivors are three LOCAL knots, identical on every via model:** U1's SW corner balls W10/W11/V10/V12 (a
1.0 x 0.5 mm patch) carrying CFG-M0/CFG-M1/FPGA-TDI/RST# to R20/R21/R4/X2-23; U1's NE corner balls
D18/D19/E18/G18/G19 carrying the flash bus, PUDC_B and UART_FT_RXD to U4 directly north; U2's south row pins
14/18/21/22 carrying FT-RESETN/TDO/PROG#/DONE 31-36 mm east through the south band. None of the field arm's
in-field microvias served a knot net. The bottleneck is not board-wide via slots after all; it is three placements.

## Corrections to my own record
- "The only guaranteed lever is more routing resource" (2026-09-29, to the user) is MEASURED WRONG for microvias on
  this placement: +6..+9 of 50, one hub of four.
- Stage 9's "the binding resource is via slots" was true of the through plan's failure strings but is not what
  caps the MUST set: three local placement knots are.

---

# What does HDI buy on the Zulu A7? The judge's decision (2026-09-30)

Directory: `scratchpad/hdi_gain/judge/` (this file, `knots.py`/`knots.log`, `diffs.py`/`diffs.log`,
`signals_must_{bare,through,banned,field}.log`, `emit_through.log`, `stitch_through.log`,
`reach_through_after.log`, `foreclosure_field.log`). Board: `tools/route_inputs.json` md5
`70f2061c95c4ae81133580e60e010539`, geometry hash `d81a5a9413dffe2e7f8d30dda7df0731` (every log header).
Instrument: stage 9's own router (`repro/mustroute.py` + `r/`), made span-aware, scope=must, order=index,
budget `BUDGET = (90, 36)` (`repro/r/engine.py:27`), identical in all three arms. Nothing placed, nothing
written outside the scratchpad, no Altium, no git, no `--write`, `tools/` untouched.

## 1. The answer in one paragraph

**HDI turns 26 of 50 into 32 of 50 with today's U1 land-field ban, and into 35 of 50 (34 gate-clean) with the
ban lifted for microvia/buried spans (user decision 7). It does not turn it into 50, or 40. One of the four
hubs unties (FT-REF: FT-REF + USB D+/D- all close); FLASH-D00, CFG-M0 and FT-RESETN stay knotted. Lifting
the land-field ban is worth +3 connections (+2 gate-clean). On the same plans HDI walls off 6-7 deferrable
connections where the through plan walls off 1, and seals the U2-5 GND tie, so the whole-board ledger
against through is about 0 (banned) to +2 (field). The board that HDI produces still cannot be configured
from flash, cannot be JTAG-programmed, and cannot hold its USB bridge out of reset. The JLC HDI 2-step
order ($309.34 qty 5, +$123.21 / +66 % / +4 days over the $186.13 standard board, plus unpriced buried-via
and lamination fees) is NOT worth placing on this evidence. HDI does not close the MUST set; nothing in
this evidence does. What is left is three local knots, and they are the same knots on every via model.**

## 2. The three arms, side by side (every number from a file or a run)

| | through | B-banned | B-field |
|---|---|---|---|
| via model | all through | laser stacks Top/L2/L3, L4/L5/Bottom, buried L3/L4, through; ban on every span | same, ban lifted for Top/L2/L3 and L3/L4 |
| CLOSED line (router) | 26 of 50, 1325 s | 29 of 50, 674 s | 32 of 50, 461 s |
| **copper in plan (island arithmetic)** | **26** (50 -> 24 open) | **32** (50 -> 18 open) | **35** (50 -> 15 open), **34 gate-clean** |
| MUST nets still split | 22 | 16 | 13 |
| route_emit | clean (`emit_through.log`) | clean (`arm_B-banned/gate_route_emit.log`) | **1 PROBLEM: vias 53 and 55 0.1414 apart** (TDO R91-1<->R4-4) |
| route_reach with plan | **104 / 105, CHAN7 walled off** (my run, `reach_through_after.log`, 422 s warm) | 95 / 101, 6 walled off (JA8, CHAN22/23/25/26/27) | 93 / 100, 7 walled off (JA8, CHAN4/5/7/8/10, SD-DAT0) |
| route_foreclosure pads | none (`arm_B-banned/cmp_through_foreclosure.log`) | **U2-5 GND sealed** | **U2-5 GND sealed** (my re-run, `foreclosure_field.log`) |
| via objects / sites | 35 / 35, 0 in field | 91 / 70, 0 in field | 112 / 92, **10 in field** (8 buried + 2 laser) |
| tracks / length | 175 / 410.6 mm | 200 / 438.8 mm | 256 / 492.4 mm |
| plane L2 GND | -- | one island 100.0 %; C120-2 OFF-PLANE (plan-caused) | one island 100.0 %; C91-2 + C120-2 OFF-PLANE |
| plane L5 VCC3V3 | -- | one island 100.0 %, exit 0 | one island 100.0 %, exit 0 |
| route_stitch U1 surround | 52.2 % (`stitch_through.log`) | 44.0 % | 52.5 % |

Sources: the three router logs (`repro/must_through.log`, `arm_B-banned/must_bannedM.log`,
`arm_B-field/must_fieldM.log`); island arithmetic from my four runs of
`python tools/stage6/signals_check.py [--inputs <arm>] --nets <33 MUST nets> [<plan>]` -- bare board 33 split,
sum(islands-1) = 50; through 22 split, sum 24; banned 16 split, sum 18; field 13 split, sum 15
(`signals_must_*.log`). The "copper in plan" row is the number the question asks for: the CLOSED line
skips the three connections that won an arbitration and were laid first (USB_D_N U2-7<->X1-2, FLASH-D03
track<->U4-7, TMS U2-19<->R4-5; `engine.run` skips `i in r.routed`), which is why both verifiers corrected
the headlines (29 -> 32, 32 -> 35). `diffs.py` reproduces it from the results JSONs: through 50 records,
0 arbitrated; banned 47 records + 3 arbitrated; field 47 + 3.

Through-only reproduction: `repro/step1` (frozen stage-9 code) gives the same 26 of 50, the same 24 open
lines and the same 35-via plan as stage 9 (1075 s vs 1035 s); the span-aware copy on the through model
gives it again (1325 s), so the three arms differ only in the via model.

## 3. What HDI buys, connection by connection (`diffs.log`)

B-banned vs through -- newly closed (8): FLASH-D03 track<->U4-7 (arbitration, 6.61 mm, 2 vias), FPGA-TMS
U1-W9<->R4-12 (20.27 mm, 4 vias), FT-REF R18-2<->U2-6 (15.86 mm, 6 vias), TCK U2-16<->R4-6 (41.36 mm,
9 vias), TDI R4-3<->R90-1 (5.25 mm, 2), TDO R91-1<->R4-4 (1.63 mm, 1), USB_D_N U2-7<->X1-2 (arbitration,
11.56 mm, 2), USB_D_P U2-8<->X1-3 (12.58 mm, 4). Newly open (2): TDO U2-18<->JP4-2 (was 51.95 mm, 2 vias
in through; now "conflicts with FT-RESETN ... no route on the lattice"), FPGA-DONE R4-15<->R4-7 (was 4.71
mm; now on FPGA-TDI). Net +6.

B-field vs through -- newly closed (10): the 8 above plus FLASH-CS# U4-1<->U1-K19 (15.23 mm, 3 vias) and
UART_FT_TXD U2-38<->track (29.10 mm, 10 vias). Newly open (1): TDO U2-18<->JP4-2. Net +9 (+8 gate-clean).

B-field vs B-banned: +3 (FLASH-CS#, UART_FT_TXD, FPGA-DONE R4-15<->R4-7), 0 lost.

Via spend: 35 through objects become 91 / 112 objects (2.6x / 3.2x); the longest closed connections use
9-10 vias (TCK, UART_FT_TXD). HDI buys via slots exactly as the brief predicted -- a Top>L3 stack blocks
nothing on L4/Bottom -- and the router spends them freely. It is not enough.

## 4. The four hubs (`knots.log`)

- **FT-REF: UNTIED** in both HDI arms. FT-REF R18-2<->U2-6, USB_D_N, USB_D_P all close (through: all
  three open, "conflicts with FT-REF"). Two costs: (a) both HDI plans seal U2-5 GND ("board: reaches U2-1;
  with plan: sealed: no via slot and no own-net copper reachable", `route_foreclosure`), one of the two
  router-invisible MUST GND ties, which the through plan leaves tie-able; (b) **FT-RESETN R19-1<->U2-14
  stays open in every arm, and R19-2 is VCC3V3** (`tools/route_inputs.json` bottom_pads), i.e. it is U2's
  RESET# pull-up. Untying FT-REF does not make USB usable while U2 has no defined reset.
- **FT-RESETN: NOT untied -- a trade.** Through: FT-RESETN, TCK, PROG#, DONE open (4). HDI: TCK closes,
  TDO U2-18<->JP4-2 opens on FT-RESETN, PROG#/DONE become mutually exclusive with each other (4 open).
- **CFG-M0: NOT untied.** CFG-M0 track<->R20-1 and CFG-M1 U1-W11<->R21-2 are mutually "no route on the
  lattice" in all three arms; FPGA-TDI and RST# stay open. FPGA-TMS closes (+1); in B-banned FPGA-DONE
  R4-15<->R4-7 is lost instead (net 0 there, +1 in B-field).
- **FLASH-D00: NOT untied.** FLASH-D00 track<->U4-5 (2.70 mm straight) vs FLASH-D01 U4-2<->U1-D19 mutual;
  FLASH-D02 (both connections) vs UART_FT_RXD (both) mutual; PUDC_B open, in every arm. FLASH-D03 closes
  by arbitration (+1); B-field also unties the separate FLASH-CS#/UART_FT_TXD pair (+2).

Where the 15 survivors of the best arm physically bite (pad centres from `tools/route_inputs.json`):
1. **U1's south-west corner**: balls W10 (46.40,7.40), W11 (46.90,7.40), V10 (46.40,7.90), V12 (47.40,7.90)
   -- a 1.0 x 0.5 mm patch -- carry CFG-M0, CFG-M1, FPGA-TDI, RST# (4 open) towards R20-1 (52.35,3.95
   Bottom), R21-2 (51.55,4.25 Bottom), R4-14 (58.45,16.98 Top), X2-23 (54.61,1.27 TH).
2. **U1's north-east corner + U4**: balls D18 (50.40,14.90), D19 (50.90,14.90), E18 (50.40,14.40), G18
   (50.40,13.40), G19 (50.90,13.40) carry FLASH-D00, D01, D02 (x2), PUDC_B, UART_FT_RXD (x2) (7 open); U4's
   pads sit directly north at x 43.85 / 51.15, y 17.50-21.30.
3. **U2's south row**: U2-14 (25.77,10.85), U2-18 (28.23,7.90), U2-21 (29.73,7.90), U2-22 (30.23,7.90) carry
   FT-RESETN (10.57 mm to R19-1 on Bottom), TDO (36.32 mm to JP4-2), PROG# and DONE (31 mm to R4-1/R4-2)
   (4 open); the east-bound three share the south band (x 31..58, y 2.0..4.6: stitch 63-69 % in every
   arm) with TMS (38-40 mm, laid by arbitration) and TCK (41-42 mm), which already took it.

The B-field arm placed its 10 in-field via objects on UART_FT_TXD (3), FPGA-TDO (2), TMS (2), FPGA-CCLK (2),
CLK-12M-FT (1) -- **none on a knot net**. The knots are not for want of via sites under U1.

## 5. What lifting the U1 land-field ban is worth

+3 connections in copper (FLASH-CS# U4-1<->U1-K19, UART_FT_TXD U2-38<->track, FPGA-DONE R4-15<->R4-7),
nothing lost; +2 gate-clean, because the B-field plan's TDO R91-1<->R4-4 carries the one route_emit
PROBLEM (a Bottom->L3 chain at one lattice node and a Top->L3 stack at the diagonal neighbour, 0.1414 mm
apart against 0.415 required) -- an instrument gap (same-path via pitch is never checked), and B-banned
proves a legal 1-via route for that connection exists under the stricter model. It costs one more
walled-off deferrable (6 -> 7), one more GND pad centre in a laser void on L2 (C91-2 at (49.41,11.05),
under UART_FT_TXD's stack), and it reaches none of the three knots. Stage 9 measured the same lift at +2
on the through model (26 -> 28). **User decision 7 is worth +2..+3 of 50 and does not change any
conclusion; it can stay open.**

## 6. Is the JLC HDI 2-step order worth placing?

**No.** `docs/hdi_fab_facts.md` lines 38-39: HDI 2-step $309.34 (5) / $313.19 (10), 12-13 days; standard 6L
JLC06161H-3313E $186.13 / $201.97, 8-9 days; `docs/hdi_spec.md` 259-262: +$123.21 (+66.2 %), +4 days,
HDI structure fee $167.30, and buried-via / lamination fees "Manual Quote" (unpriced). The order's premise
was that microvias get the board routed. Measured: they close 6-9 more of the 50 MUST connections, untie 1
of 4 hubs, leave 15-18 open including every configuration strap (CFG-M0, CFG-M1, PUDC_B), three of the
four flash data lines, FPGA-TDI, PROG#, DONE, FT-RESETN and UART RXD, and on the same plans wall off 5-6
more deferrable connections and seal a MUST GND tie. A board that cannot be configured is not worth
fabricating in any technology, so the order is moot until the three knots are untied -- and if they untie
on the through model, the $186.13 board is the one to order. Keep the six via types and HDI rules in the
Layer Stack Manager (commits c62c24d / faf26a2): they cost nothing until an order names them.

## 7. What closes the MUST set -- and what does not

Does not (measured): HDI Structure B (+6); HDI with the land-field lift (+9, +8 clean); the land-field lift
alone (+2..+3, both models). Stage 9 already measured: a 57-ball re-pin reaches 4 of the 52 (of the 15
survivors only UART_FT_RXD's G19, 2 connections); a fifth global route; scoping alone.

What the evidence points at (unmeasured -- this stage produces the number, not the fix):
1. The 15 survivors are three local knots (section 4), the same three on every via model, all ending in
   "no route on the lattice" at budget (90, 36) in a single commit order (index). Stage 9's keystone plan
   applies unchanged: per-knot hand routing with the budget raised for that pair alone, plus a
   commit-order search over the MUST set (a run is 8-22 min), **on the through model first**.
2. If a knot resists on through: a small, reversible placement move before any fabrication change -- U4
   (the flash) so its pins face U1's north-east flash balls instead of sitting 2.7-8.7 mm north of them;
   the R20/R21/R23 straps (0402s on Bottom at y 4); R19 (FT-RESETN's pull-up, 10.57 mm from U2-14). Stage 9
   said placement earns a stage only if the keystone work fails; that still holds, but it is a move of
   these parts, not a re-pin and not the U2/X1/R18 cluster (HDI has shown FT-REF/USB coexist there).
3. The 2 GND ties (R15-1, U2-5) by hand, and before any copper near U2-5 -- both HDI plans seal it.
4. Any plan meant for placing must be re-cut with full witnesses (scope=all) so route_reach does not drop;
   re-measure the MUST count under that protection (the +6/+9 were bought with scope=must freedom).

## 8. Corrections to the record

1. B-banned arm: "OFF-PLANE C120-2 is a board condition" is wrong -- the bare board gives 216/216, exit 0
   (`arm_B-field/base_plane_L2.log`, `verify_B-banned/gate_plane_L2_bare.log`); the void is the plan's
   CLK-12M-SHARED laser stack at (42.8,17.7). Verifier B-banned's correction stands. gnd_check's two UNTIED
   pads (U2-5, R15-1) are pre-existing.
2. B-field headline 32 -> 35 in plan copper (34 gate-clean); B-banned 29 -> 32. The router's CLOSED line
   gives no record to arbitration-laid connections. Reproduced independently by island arithmetic.
3. The through plan's route_reach after was unmeasured by both arms; measured now: 105/105 -> 104/105,
   CHAN7 walled off (`judge/reach_through_after.log`, 03:06:45 -> 03:13:47). Permanence comparison 1/6/7.
4. "U1 surround drops to 44.0 % / 52.5 %" reads as HDI's doing; the through plan drops it to 52.2 %
   (`judge/stitch_through.log`). B-banned is worse, B-field equal.
5. Verifier B-field's "unmeasured: what route_reach does with land_field_ban=false": by direct read,
   `tools/hdi.py:158-166` returns the model's per-span `land_field_ban`, and `tools/route_reach.py:260`
   applies the land-field raster only when `H.field_ban(S)` -- the reach numbers used the router's ban.
6. The FT-RESETN hub does not shrink under HDI; it trades TCK for TDO U2-18<->JP4-2 (4 open in every arm).
7. "FT-REF untied, USB works" would be wrong: R19-2 is VCC3V3; FT-RESETN is U2's RESET# pull-up, open.
8. Verifier B-banned's route_reach after finished after its cut-off (03:03:14): 95/101, the same six --
   the permanence failure of B-banned is now independently reproduced. Its router re-run was cut at 27/50,
   line-identical to there including all three arbitrations; the arm's log and plan are byte-identical
   between `repro/` and `arm_B-banned/` (md5 32cd1171f06687ed3096a45024a110fb).
9. B-field's route_foreclosure re-run by me (`judge/foreclosure_field.log`, 166 s): CHAN10 CHAN7 CHAN8 JA8
   UART_FT_TXD foreclosed, U2-5 PAD FORECLOSED, exit 1 -- verbatim as the arm reported.

## 9. Risks and limits of this evidence

- Single commit order and fixed budget: stage 9 saw an 11-connection spread across orders on the full
  set; every arm's count could move. The between-arm deltas are paired at identical order and budget,
  which is the designed comparison. "No route on the lattice" proves nothing impossible.
- Merged-span model only (one 3-layer span per laser stack), because the gates accept only that form as a
  Top<->L3 join; the two-object form (Altium's uVia 1:2 + 2:3) was built byte-identical to repro's and not
  run. Blocking, pitch, antipad and layer set are identical by construction from the model files; the
  emitted record and route_emit's object count are not.
- Neither HDI plan is placeable: B-field fails route_emit; both fail the permanence rule (-6/-7) and seal
  U2-5; two GND pad centres sit in L2 laser voids (plane one island, 100.0 %, both arms). Evidence only.
- The router's same-path via-pitch gap (B-field TDO) must be fixed before an HDI plan is quoted again.
- Fab facts outside the model: JLC's 6L 2-step layer pairing (open fab question 1), the manual-quote
  buried/lamination fees, the 0.075 ring on a 0.225 land (via_in_pad false everywhere, correctly).
- Timings are contended (both arms and a verifier ran on the same 24-core box); the through reach was a
  warm run (board pass from cache).
