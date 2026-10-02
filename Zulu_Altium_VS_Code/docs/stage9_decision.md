# Stage 9: route again, or re-pin? Neither — the answer is the hard set (2026-09-29)

**Nothing was placed.** This stage produced a measured decision, on board
`210a6f2b7669980309fb2472a125ad98` with 140 open connections. Nine agents, 1.93M tokens:
four independent measurements, one adversarial verifier each, one judge.

## The question

> should we do the 140 open signal connections next? or the placement/re-pin decision next?

## The answer

**Neither as posed.** Route connections next — but only the **52 that make the board work**, and as
**four named keystone knots**, not a fifth global route. **The re-pin question needs no answer**: a
re-pin of the 57 permutable balls can move **4 of those 52**.

### Why the re-pin dissolves

Of the 52 MUST connections, a 57-ball re-pin reaches **4** — CLK-12M-FPGA (L17, and only among the
9 clock-capable P-half balls), UART_FT_TXD (K18), UART_FT_RXD (G19, 2). **22 are on nets with no U1
ball at all**; 17 sit on dedicated or fixed-function balls; and **three of the four blocking hubs are
unreachable by a re-pin**. Its reach is 60 of the 88 non-MUST connections — almost exactly the work
that can wait.

Scored on the only instrument that can score it, paired over 16 identical commit orders, a re-pin is
worth **mean +3.4 connections** (best order 93 vs 87; union 107 vs 105 = +2). A random relabelling of
the same 57 balls scores **+0.00**, so the effect is real — and tiny.

Its cost is the only irreversible option on the table: 57 XDC lines, 10 659 net-name occurrences
across 7 SchDocs, 59 fan-out tracks and 19 vias to re-net, the EAGLE `zulu_a7.sch` to follow, and the
stage-5-to-8 verification chain to redo.

### Why "route again now" is also wrong, measured rather than assumed

Every attempt so far — 4b, Situs, 6, 7, 8 and all three of this stage's controls — routed all 140 as
one undifferentiated set. This stage split them by function and gave the hard set absolute priority,
free to take any corridor the deferrable set wanted, refusable only for walling off another hard-set
connection. That is the most favourable scoping this board admits:

| scope | connections | demand |
|---|---|---|
| **MUST** (configure, clock, JTAG, UART, USB) | **52** | 636.4 mm, 30.1 % |
| NICE | 13 | — |
| DEFER (CHANx 30, Pmod 16, microSD 11, LED 10, button 4, XADC header 2, NODE_P0 2) | 75 | 1479 mm, 69.9 % |

**It closes 26 of 50** (the other 2 MUST are GND ties no router can see). Clocked yes; **configure no,
JTAG no, UART no, USB no**. So routing again now — even perfectly scoped — yields a board that cannot
be configured, programmed, or talked to. Scoping alone does not rescue it.

### But the 24 failures are 4 problems, not 24

Each failure names its blocker. They reduce to **17 pairwise exclusions with four hubs**:

| hub | connections it blocks |
|---|---|
| **FLASH-D00** | FLASH-D01, FLASH-D02, FLASH-D03, PUDC_B, UART_FT_RXD (5) |
| **CFG-M0** | CFG-M1, FPGA-TMS, FPGA-TDI, RST# (4) |
| **FT-RESETN** | TCK, PROG#, DONE (3) |
| **FT-REF** | USB_D_P, USB_D_N (2) |

That is the same shape stage 7 found when it named NODE_P1 as vetoing 19 commits — and stage 8 untied
and **placed** that one, in the cheapest stage on record. Untying FLASH-D00 and CFG-M0 alone returns
9 of the 24.

**The binding resource is via slots, not corridor lanes.** "Left it its via slot and took another"
appears 47 times in the log; 12 of the 24 failures end in "no route on the lattice". Every corridor-load
number this project has quoted — 16.1 %, 21.7 %, 27.5 % — tracks the wrong resource.

### The cost argument, measured from scratchpad volume

| stage | closed | placed? | scratchpad |
|---|---|---|---|
| 4b | 92 | **no** | 123 621 KB / 1209 files |
| 6 | 86 | **no** | 26 605 KB / 845 files |
| 7 | 62 | **no** | 11 123 KB / 210 files |
| **8** | **3** | **YES** | **1 394 KB / 92 files** |

The only stage that put copper down is 89x smaller than the largest that did not.

## What to do next

1. **A keystone stage on the four hubs**, exactly as stage 8 ran the XADC knot: locate where each
   exclusion physically bites, raise the router budget past (90, 36) for that pair alone, try a
   dedicated per-net layer and via assignment.
2. **Place what closes, in small gated batches** — `route_emit --require-complete`, `route_reach`,
   `route_foreclosure`, `route_width`, `stage6/islands.py`.
3. **Fix `tools/route_reach.py:197` as hygiene, not as a lever** (see corrections), and refresh
   `tools/stage6/segw.py`'s stale guard in the same pass.
4. **One dedicated experiment on the USB corner** — all eight connections arbitrated at once, the gap
   the u2west verifier named as untested.
5. **Close the 2 GND ties (R15-1, U2-5) by hand.** No router on this board can see them.
6. **Do not** route the 75 deferrable connections, **do not** re-pin, **do not** run a fifth global
   route. Placement earns a stage only if the keystone work and the USB experiment both fail — and then
   it is a move of the U2/X1/R18 cluster, not a re-pin.

## Corrections to the project record

These were found by the verifiers and the judge, and several are mine from the stage-9 brief.
All are measured.

1. **`tools/route_reach.py:197` forbids vias across the whole of U1's land field** — 85.1 mm², hiding
   3058 via-legal cells / 1.91 mm² / **25 legal 0.44 mm slots** that clear the nearest land edge by
   ≥ 0.774781 mm against the 0.265 mm required. 80 vias already sit inside that rectangle on 37 nets.
   `stage7`/`stage8`'s router inherits it (`router.py:40`, `:112`), so **every routing number ever
   measured on this board carries it**, including `route_foreclosure`'s verdicts. Lifting it was tested
   and closes **28 of 50 instead of 26** — a real defect, but worth 2, not a lever. *Confirmed by
   direct read.*
2. **`tools/stage6/segw.py` refuses today's board** — its guard demands 1498 tracks / 371 vias and the
   board is 1518 / 377. **No width gate ran on any route measured in this stage.** *Confirmed by
   direct read of `segw.py:26`.*
3. **"route_reach reports 140/140" is loose** — it reports **138/138** and excepts the 2 GND ties.
   `RR.parse_connections` excludes GND/GNDADC, so no router can see them.
4. **`docs/repin_study.md`'s 411 mm is unadoptable**: **0.0 mm of 410.7** can be taken without ripping
   routed copper — all five "independent" cycles move already-routed SDRAM nets (19/13/2/1/2).
5. **"the 57 permutable balls touch no placed copper" is wrong** — **37 of the 57 do**: 59 tracks,
   19 vias, 28.5888 mm, all Top fan-out, furthest piece 1.5207 mm from its own ball.
6. **"738.5 mm = 25.6 % of the board's copper" is 35.1 %** of 2105.449 mm, and there are 39
   SDRAM-class nets, not 37.
7. **`tools/stage7/escape_audit.py`'s stub-end walk is single-hop**, so "L17 CLK-12M-FPGA is the only
   dead ball owing a connection" is **wrong**. L17's fan-out is a two-track dog-leg — ball
   (49.90,11.40) → (49.4001,11.40) → via (48.90,11.8999). **Zero balls owing a connection are dead.**
8. **"stage 7's congestion map found 0 oversubscribed resources" no longer holds** — the same tool,
   byte-identical apart from metadata, reports **13 tiles above local lane capacity** at the 2.5 mm
   window on today's board (0 at 5 mm). A board change, not a tool change.
9. **The USB rule contradiction resolves TO THE FILE.** `Rules6/Data`, `RULEKIND=DiffPairsRouting`,
   `ENABLED=TRUE`, `MINLIMIT = MAXLIMIT = MOSTFREQGAP = 5.9055 mil = 0.150 mm` exactly.
   **The docs' 0.125 is wrong.** This long-open contradiction is settled.
10. **The FT-VPHY band's blocker is the Bottom VCC1V0 rail specifically**, not five co-equal blockers:
    leave-one-out opens 1586 cells alone vs 514 / 292 / 138 / 112. The "0 legal via sites before and
    after" conclusion stands.
11. **The SDRAM via cluster is not at 0.44 mm pitch** — closest measured pair 0.5551 mm; tightest pair
    anywhere in that window 0.4750 mm.
12. **"16 fixed balls" is 17** by the files: 11 dedicated + 6 fixed-function.
13. **`tools/stage5b/bodies.py` returns no body box for U2 or the LED 0603s**, so any placement search
    trusting it — including `tools/block_place.py` — can place parts inside U2's outline. *The design
    itself is fine*: the PCB carries `FT2232HL-LQFP64`, `zulu_a7_4.SchDoc`'s live footprint is the
    same, the QFN64 entry is a leftover alternate model, and `board_preflight` resolves all 790 pad
    references. This is a tooling gap, not a design defect.
14. **The congestion measurement's own headline was refuted by its verifier** — 12 of 12 probed
    connections DO route alone, and Bottom demand across the XADC divider row is 0 of 138 against
    9 lanes. Its "9 of 12 cannot be laid alone" and "the crux is the 0.300 mm pad gaps" must not be
    quoted forward. The exclusion it found is real but 2-of-4, and caused by a shared Bottom
    south-edge channel.
15. **`tools/stage6/corr.py` is a heapq maximin widest-path finder** and `tools/sdram_route_plan.py`
    records a negotiated-congestion A* plan being rejected on this board — so "no path search exists
    in the toolkit" is wrong.

## Open user decisions this raises

1. **Confirm the MUST set of 52.** Membership was argued by function, which is a judgement, not a
   measurement. Specifically: is UART flow control (RTS#/CTS#/DTR#, 4 connections) deferrable, and is
   the FT2232H config EEPROM (EE-*, 8 connections) deferrable? The FT2232H runs from internal defaults
   without it, but then it has no custom VID/PID or descriptors.
2. **Approve or refuse the land-field raster change** (correction 1). It relaxes a constraint the user
   set, and the blanket rectangle is the assumption every gate in this project was built on.
3. **May USB ship broken in rev A?** Two independent routers now say FT-REF and the USB pair cannot
   coexist on this placement, and no priced component move or fabrication lever changes it. If USB must
   work in rev A, the U2/X1/R18 corner needs a placement change and that cannot be deferred behind the
   keystone work.
4. Still open from before: the 2 untied GND pads, teardrops, and whether the 0.35 mm via land stays.

## Caveats the judge stated about its own result

- The router **proves existence, never impossibility**. "Mutually exclusive at every detour tried" at
  budget (90, 36) is not proof that a pair cannot coexist — which is exactly what the keystone stage
  tests, cheaply, before anything is placed.
- **26 and 28 of 50 are single commit-order samples.** The lane model shows a spread of 11 connections
  across orders on the full set, so the hard-set number could move either way.
- The USB-corner figure rests on 3 of 24 permutations.
- Where each of the 17 exclusions physically bites was **not** located; the keystone stage starts with
  that diagnosis.
