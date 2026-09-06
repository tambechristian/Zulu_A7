# Zulu A7 board — stackup, rules and escape plan

Current decision (2026-09-02): **8 layers**, **PCBWay**, ball land **0.225 mm**,
3 mil trace and 3 mil clearance. The active board uses
`[5:(1+2+3+4+5*6+7+16):5]`:

| Fusion layer | Function |
|---|---|
| 1 Top | signal and local GND pour |
| 2 Route2 | uninterrupted GND plane |
| 3 Route3 | horizontal signal |
| 4 Route4 | vertical signal |
| 5 Route5 | VCC3V3 plane |
| 6 Route6 | vertical signal |
| 7 Route7 | horizontal signal |
| 16 Bottom | signal and local GND pour |

The dielectric values stored in the Fusion file are a symmetric, provisional
1.6 mm routing model. PCBWay must approve or replace the exact dielectric
materials and copper thicknesses before impedance calculation or fabrication.
U2's exposed-pad construction and the mandatory via-fill order note are in
`board/U2-THERMAL.md`.

The current routed candidate uses two via processes:

- 0.20 mm finished drill / 0.30 mm land for conventional mechanical and
  U2 thermal vias;
- 0.10 mm laser drill / 0.20 mm land for selective blind-via signal escapes.

This changes the production build from through-hole-only to an HDI/sequential-
lamination build. The laser vias require filled/plugged and copper-capped
construction where they land in pads. PCBWay must approve every blind-via span,
the lamination sequence, resin-fill/cap process, and the mixed-drill build before
release. Fusion's minimum drill rule is 0.10 mm; ordinary vias remain 0.20 mm.
Fusion's blind-via ratio is set to 5.0. PCBWay must still approve the 5:1 ratio
and dielectric stack before release. The older through-hole-only statements
below are retained as design history and do not describe the active board.

Current routing checkpoint:

- All twelve relocated Pmod/JTAG signal nets are connected.
- The offline board checker reports zero geometry, spacing, drill, or endpoint
  findings.
- A fresh Fusion Ratsnest reports 41 airwires, down from 52 after the connector
  relocation and 72 on the best verified 2.400-inch candidate.
- A fresh full Fusion DRC reports 83 errors: 63 Air Wire, 16 Drill Size,
  2 Copper Clearance, and 2 Overlap, with zero Drill Clearance errors. The higher
  DRC Air Wire count includes plane/island
  connectivity that Ratsnest does not report in the same way.
- This is an intermediate routing checkpoint, not a fabrication release.
- By 2026-09-05 the count came down to 48 under the honest model (76 before),
  26 split nets from 42, `check_board` at 0 findings and Fusion's four
  Overlap / Copper Clearance errors gone; see "Closing the airwires" below for
  what blocks the rest and why. `python tools/release_check.py` is the
  one-command gate.

## Closing the airwires -- 2026-09-04

Fusion reported 41 airwires from Ratsnest and 63 from DRC on the 8-layer board,
with 16 Drill Size, 2 Copper Clearance and 2 Overlap errors. Four things had
to be understood before any of them could be closed.

### The checker never saw a plane

`check_connectivity.py` joined the vias and plated pads of a net through an
inner pour only if the pour was written as `<polygon>`. Fusion writes
`<polygonpour>`. So on every board Fusion had saved, the checker saw no planes
at all: GND read as 65 pieces and VCC3V3 as 37. Fixed to match either tag.

Then the pour was rastered rather than assumed solid (`tools/plane_islands.py`):
a pour centreline must keep `isolate` from every foreign object, so the region
it may occupy is everything at least isolate + width/2 from foreign copper;
flood that and see which own through objects the main piece reaches. The L2
GND pour was in 113 pieces and 34 GND vias sat on islands or in isolation; the
L5 VCC3V3 pour was split nearly in half, 43 of 102 own objects off the main
piece. The cause was seven signals routed ON the plane layers with 0.10 mm
laser vias (CHAN8, CHAN18, CHAN23, LED2, D12, D6, FLASH-D00), each trace a slot
through the copper, plus the laser vias of LDQM, PUDC_B and PMOD-3. That is
what DRC's 63 against Ratsnest's 41 was reporting. `check_connectivity` now
takes the plane as the flood finds it (`plane_reach`), and only that.

### Twelve balls had no way out

Twelve BGA balls have no L1 escape: A10 (U3), BS1 (U1), WE# (V4), D10 (K2),
D11 (J1), CHAN13 (W18), FPGA-CCLK (C11), FT-PWREN# (P17), LED0_G (R18),
UART_FT_TXD (K18), UART_FT_RTS# (L18) and CFG-M0 (V12). Their pockets on L1 are
between 12 and 400 grid cells, walled in by neighbouring escapes, and a via in
the ball is blocked on the inner layers by the traces already under it (only
A10 would take a 0.25 mm land, none a 0.30). The earlier answer had been a laser
via in the pad down to L2 -- HDI, and the plane damage above. U3's SDRAM pads
on L16 were in the same state behind the stubs of the bus nets that had routed.

### Rails cannot be wide at the ring

The stage-3 ring vias sit at 0.39 mm centres. Nothing wider than 3 mil passes
between two of them on any layer, and a 0.25 mm trace cannot even START at a
via 0.32 mm from a ring via. The rails route at 0.25 mm where they can and the
router falls back through 0.20 / 0.15 / 0.10 mm only where it must.

### What closes them: `tools/close_airwires.py`

Every open net is stripped to what is worth keeping -- a piece joining two or
more pads whole, a single-pad piece only as far as its fan-out escape -- and the
debris of earlier attempts goes (PROG# alone had 14 vias out to x = 0.65). Then
every piece is flooded; a piece boxed in a pocket has the copper forming the
pocket's wall RIPPED, and the wall's net is stripped to its own escapes and
joins the negotiation. PathFinder routes the lot over L1/L3/L4/L6/L7/L16 with
every piece a set of seed cells, through vias only (0.20 / 0.30, 0.40 mm centre
to centre). GND and VCC3V3 go last: each stranded piece routes to the nearest
cell where a new via lands on the MAIN piece of its plane, the flood raster
being a routing layer. Ends are snapped onto pad and via centres so
`check_board`'s landing test agrees. A net that was whole and cannot be rerouted
is protected on the next attempt rather than restored into a layout routed
without it; nothing is ever left with more pieces than it began with.

Two grid facts cost a day between them. Foreign copper is dilated by the rule
plus 0.01 mm of margin, so a trace laid at exactly 3 mil from its neighbour has
every cell of its own centreline blocked -- seeds must be forced open on the
net's own copper. And a one-trace corridor between copper at exact 3 mil has
zero width on a 0.05 mm grid: a ripped wall net cannot thread back through the
hole it left, it has to be routed afresh.

### Result

Board written 2026-09-04 (`zulu_a7.brd`; backup `zulu_a7.brd.pre-close-airwires-20260904.bak`):

| | before | after |
|---|---|---|
| airwires, honest model (sum over nets of pieces - 1) | 76 | **48** |
| split nets | 42 | 26 |
| `check_board.py` findings | 0 (4 unseen) | **0** |
| Fusion DRC Overlap + Copper Clearance | 2 + 2 | **0** |

Closed, in five chained runs (each starts from the last one's board; the
negotiation is not deterministic, so a second pass over the same open nets
finds paths the first did not): AIN15_N, BS0, CAS#, CHAN-CLK, CHAN16, D11,
FB3_NODE, FLASH-D02, FPGA-TDI, N$BTN, N$LD0G, RST#, USB5V0, VCC1V8, VEXT and
VCC3V3, plus every piece of GND the plane pass could reach (20 pieces to 19).
CHAN15 and PMOD-3 were rerouted whole: CHAN15 because two of its vias sat on
U2's unconnected pins 58 and 30, which is what Fusion's two Overlap and two
Copper Clearance errors were (`check_board` skipped pads with no net; it no
longer does), PMOD-3 to lose its laser via. Every pocket that would still open
was tried, with the GND and VCC3V3 gang traces rippable too; the 26 left are
bounded by pads, by gang traces whose removal the plane pass could not make
good, or by copper whose owner could not be rerouted. Fusion's own Ratsnest will report FEWER than 48 because it counts GND
pads tied only through the L1/L16 pours as connected; DRC will report more than
Ratsnest for the same reason it did before. The 16 laser vias and 9 blind 0.20 mm
vias are untouched (`tools/unblind_vias.py`: no column is clear), so the build is
still HDI until CHAN8, CHAN18, CHAN23, LED2, D12, D6, FLASH-D00, LDQM, PUDC_B and
PMOD-3 are rerouted on signal layers -- `CLOSE_FORCE` names them, but each is
boxed in by the same walls as the balls above.

What did NOT work, so it is not tried again: negotiating 80-120 nets at once
after ripping every wall (never settles; legalisation drops ~30 nets that were
whole, and restoring their copper collides with every new route); ripping a
single wall segment (the hole it leaves has zero width on a 0.05 mm grid);
repairing tilted snap wires by geometry after the fact (Fusion's autorouter
draws slightly off-axis wires too, and the heuristic damaged 42 of them).

### Gate

    python tools/release_check.py zulu_a7.brd

## The build becomes 1+6+1 HDI -- decided 2026-09-05

Forty-eight airwires would not close on a through-hole build: twelve balls have
no L1 escape and U3's pads are walled in on L16, and every rip-up of the copper
around them ended in the same place, because the walls are the neighbouring
pads. The earlier sessions had reached for 0.10 mm laser vias in exactly those
pads, but they landed on L2 -- the GND plane -- and cut it to 113 pieces. The
decision is to do that properly:

| Fusion layer | was | now |
|---|---|---|
| 1 Top | signal, escape | signal, escape; **0.10/0.20 laser vias to L2** |
| 2 Route2 | GND plane | **HDI escape signal layer** |
| 3 Route3 | horizontal signal | **GND plane** |
| 4 Route4 | vertical signal | vertical signal |
| 5 Route5 | VCC3V3 plane | VCC3V3 plane |
| 6 Route6 | vertical signal | vertical signal |
| 7 Route7 | horizontal signal | horizontal signal; **laser vias from L16** |
| 16 Bottom | signal | signal; **0.10/0.20 laser vias to L7** |

`tools/hdi_swap.py` makes the change: the GND pour moves to L3, every L3 wire
is renumbered to L2 (through vias reach both, so nothing disconnects), the
nine nets that had been routed on the plane layers with deep 0.10 mm vias
(1-5, 2-16, 1-4, 1-7, 5-16 -- spans a laser cannot drill) are stripped to their
pads with a proper 1-2 or 7-16 microvia where each sat, every bare boxed ball
gets a 1-2 microvia and every bare boxed U3 pad a 7-16 microvia, land 0.20 mm
centred in the pad, and any moved copper a new land collides with is ripped so
its owner reroutes. `msMicroVia` becomes 0.10 mm, which is what stops Fusion
reporting each laser via as a Drill Size error. `close_airwires.py` then runs
with `CLOSE_LAYERS=1,2,4,6,7,16` and `CLOSE_PLANES=GND:3,VCC3V3:5`; the L1
stage-1 GND and VCC3V3 gang traces are rippable in that run.

What it costs, and what PCBWay has to approve before this can be ordered:
laser microvias 0.10 mm drill / 0.20 mm land on L1-L2 and L16-L7, filled and
capped where they sit in the BGA and TSOP pads (they all do), the 1+6+1
sequential lamination, and the three remaining 0.20 mm blind spans (1-5, 5-16,
6-16) if they are kept. PCBWay's DFM answer of 2026-08-27 called HDI a large
cost adder; the through-hole alternative was shown to be unroutable at this
pitch, so that is the trade. Signal-wise L1 now references L2 signals rather
than a plane, with the GND pour one dielectric further down; for a 166 MHz SDR
bus over runs under 25 mm that is ordinary HDI practice.

The two planes are immediately healthier for it: with no signals on the plane
layers, the GND pour on L3 has 17 of its own through objects off the main piece
against 34 on L2, and VCC3V3 on L5 has 7 against 46.

### Where the HDI board stands -- 2026-09-05

`zulu_a7.brd` is the HDI board (copy `zulu_a7.hdi-46.brd`; the last
through-hole board is `zulu_a7.closed-48.brd`, the start of all this
`zulu_a7.brd.pre-close-airwires-20260904.bak`).

| | through-hole, start | through-hole, best | HDI |
|---|---|---|---|
| airwires, honest model | 76 | 48 | **46** |
| split nets | 42 | 26 | 31 |
| `check_board.py` findings | 0 (4 unseen) | 0 | **0** |
| Fusion Overlap + Clearance | 4 | 0 | **0** |
| Fusion Drill Size | 16 | 15 | **0 expected** (msMicroVia 0.10 mm) |
| GND plane objects off the main piece | 34 (L2) | 33 (L2) | **14** (L3) |
| VCC3V3 plane objects off the main piece | 46 | 46 | **6** |
| laser vias | 16 deep spans | 15 | 30 microvias, 1-2 and 7-16 only |

Split nets are up on the HDI board because the nine nets that had been
routed on the plane layers are open again, honestly, instead of routed through
the GND plane. Twenty-one boxed balls and nine boxed U3 pads now carry
microvias; the BGA side of each such net floods the whole board from its
microvia, so the L1 escape problem is solved. What stops them now is the OTHER
end: the region under U3 on L7 and L16 is walled by the 0.25 mm GND and
VCC3V3 traces that ring the SDRAM and by the pad rows themselves, and the
frontier between the two floods is 40 to 50 nets wide with a plane net as the
largest wall. Runs 21 to 26 (`close_airwires.py` with L2 evicted under U1 and
L7 under U3, escalating rip-up, frontier walls) closed 13 of the 44 nets that
were open after the swap and no more.

### Fusion counts differently, and now the tools count like Fusion -- 2026-09-05

Fusion's own Ratsnest on the 46-airwire HDI board said **60**. Its list
(`tools/airwires.ulp` writes every layer-19 airwire with both ends to
`airwires.txt`; run it in Fusion with `/`, `RATSNEST;`, then
`RUN <path>/tools/airwires.ulp;`) showed why, net by net:

- **Connectivity is by end points, at exact coordinates.** Two wires are one
  piece only where an end of one equals an end of the other. A wire reaches a
  via only when it ends on the via's centre. A wire ending on the body of
  another wire (a T), 0.05 mm short of it with the copper plainly overlapping,
  or 0.0011 mm from another end (Fusion's unit is 1/320000 mm) is an open
  circuit. Fourteen nets had such joints, all written by tools that reasoned
  about copper overlap.
- **Every piece counts.** A leftover via, or the stump of an old route,
  earns an airwire of its own; TDI carried four floating pieces of 59 objects.
- **Outer pours are pieces too.** The L1 and L16 GND pours are cut into
  hundreds of pieces by the traces; each piece connects what it touches, and a
  capacitor's GND pad whose piece touches no via down to L3 is an airwire.

`check_connectivity.touches` now implements exactly these rules (tolerance
1e-5 mm; pour pieces from `plane_islands`, which floods the outer layers too
and treats the net's own wires as part of the pour), `components` counts
every piece, and `tools/fusion_model.py board.brd --airwires airwires.txt`
prints the per-net disagreement with Fusion -- empty now, apart from one GND
pad where the raster's idea of the pour differs from Fusion's.
`tools/fusion_connect.py` repairs joints (snaps ends a hair apart, splits a
host wire under a T, adds the hop to a via centre, bridges ends within
0.16 mm) and deletes floating pieces; `close_airwires.run_pass` calls it on
every net it routes, so the router cannot write an open joint again.
`tools/gnd_stitch.py` ties a stranded plane-net pad to the plane with one
via and one short wire, or a via in the pad when 3 mil traces box it in.

| board | Fusion airwires | model | note |
|---|---|---|---|
| `zulu_a7.hdi-46.brd` | 60 | 46 (overlap model) | 14 nets of T-joints and near misses |
| `zulu_a7.hdi-46d.brd` | 46 | 46 | 67 joints repaired; totals agreed, nets did not |
| `zulu_a7.hdi-46f.brd` | 35 | 36 | floating copper gone, ends snapped, exact tolerance |
| `zulu_a7.hdi-46h.brd` | 32 | 33 | 3 of 4 stranded GND pads stitched |
| `zulu_a7.hdi-46i.brd` | 31 | 32 | GND closed in Fusion; the model's one extra is a via cluster at (22.8, 0.55) the raster misjudges |
| `zulu_a7.hdi-46n.brd` | 31 | 32 | stub pass: Wire Stub warnings 39 -> 15 -> 4 |
| `zulu_a7.hdi-46o.brd` = `zulu_a7.hdi-31.brd` | 31 | 32 | Minimum Drill Size rule 0.1 mm in the file; fresh open, no Drill Size errors |
| `zulu_a7.hdi-46r.brd` | -- | 38 | 14 microvias in the bare passive pads, 22 foreign segments ripped under 4 of them |
| `zulu_a7.r5n.brd` | 34 | 35 | CHAN bus stripped and re-negotiated on 46r: CHAN8/10/11 closed, rip victims still open |
| `zulu_a7.r4n.brd` = `zulu_a7.hdi-27.brd` | 27 | 28 | pocket router phase A + evictions on 46r: PROG#, FLASH-D00, A10, FPGA-CCLK, RAS#, PUDC_B, D12 closed; DRC: Air Wire 27, Matched Lengths 1, Wire Stub 4 |
| `zulu_a7.r7n.brd` = `zulu_a7.hdi-26.brd` = **`zulu_a7.brd`** | **26** | 27 | pocket router phase A on r5n (CHAN re-plan first, then the passives): DRC Air Wire 26, Matched Lengths 1, Wire Stub 4 |

### The SDRAM bus re-plan, and what the floods say -- 2026-09-06

Decided by the user: re-plan the SDRAM bus on L2/L7 from scratch. Done
twice on `zulu_a7.r7n.brd` with all 39 U1-U3 nets stripped to their escapes
and negotiated together (`CLOSE_MODE=attempts`): confined to L2/L7 plus the
outer layers, 25 of 43 items routed; on all six routing layers, 34 of 43,
including five of the six open SDRAM nets -- but the seven previously routed
nets that failed (A6, A7, A9, BS0, CKE, D10, UDQM) took their copper back and
the five lost theirs. Three attempts each, every verification the same
six open (A5, BS1, D6, D12, LDQM, WE#). Zero-sum. A corridor rip of every
trace crossing the strip x 39.9..41.4 west of U1 (442 segments, 48 nets)
negotiated 33 of 71 and was reverted.

The floods (`scratchpad/flood_sizes.py`, the router's own grid) say why,
and they say the U3 move would not help: for A5, BS1, D6, LDQM and WE# the
**U3 pad already floods the whole board** (830 000 cells); it is the **BGA
ball** that is boxed, in one shared pocket on L2 under U1 (x 39..53,
y 4.8..15.6, 12 500 cells, nothing but the evicted escape layer) with **no
via site inside it**. The pocket's west wall at x 39 is the bus's own exit:
a single column of 23 through vias at 0.4 mm pitch (A0, A2, A3, A7, A11,
A12, CKE, D8, D11, SDRAM-CLK, TDI, TCK, DONE, FLASH-D02, AIN15_N, AIN16_N,
VCC3V3 x3, GND x2) and the N-S runs of A10, A2, A11, D8, UDQM on L2. The
strip between that column and U1's dogbones carries copper on all six layers
(A0/SDRAM-CS#/A2/A3/D11 escapes on L1, D9/A10/D10/D13/CAS# on L2, VU/D10/UDQM
on L4, CHAN11/RST#/FLASH-CS# on L6, CHAN10/D7/RAS#/SD-CLK on L7,
VCC3V3/GND/VU on L16) and holds U1's 0201 parts (R2, R6, R13, R20, R22,
C104, C107, C109, C111, C113, C140) on both sides. One via column serves
every westbound net; the six open ones have no site left. CHAN13, CHAN18
and CFG-M0 sit in the lower half of the same pocket; FT-PWREN# is boxed at
both ends in pockets of about 1000 cells.

What would change it, in order of cost: (1) move the corridor's 0201 parts
out of x 39..42 and re-plan the bus with a second via column -- a placement
change; (2) a full HDI fan-out of U1 (every ball on a 1-2 microvia, no
through via under the BGA, two rows of escapes per side on L2) -- the
redesign the 1+6+1 build was bought for; (3) route the 26 by hand in Fusion
from `airwires.txt`.

### Option 2, stage 1: the west ball columns on microvias -- 2026-09-06

Decided by the user: the full HDI fan-out of U1, staged, each stage
verified in Fusion. Stage 1 = the two west columns facing U3 (rings 1 and 2,
20 signal balls) on 1-2 microvias (`tools/bga_microvias.py --cols 42.0,42.5
--rip`; ring 3 cannot pass the 0.30 mm gaps between ring-1 lands, one 3 mil
trace per gap, so it keeps its through vias), the router's escape rule
changed so a ball with a via in it keeps only that via, and an explicit
escape zone for U3 (`CLOSE_EXTRA_ZONES=28.4,11.5,10.6`) so the U3-end stubs
stay. The 20 converted nets plus the six open SDRAM nets and D9 (ripped
under the balls) were then re-routed from the microvias, five ways:

| run | method | result |
|---|---|---|
| h4/h5 | negotiation, 33 nets, 20 and 40 iterations | 25 of 41 legal; no gain |
| h6 | negotiation, ring 1 only (9 nets) | 4 of 11 legal; no gain |
| h7/h8 | greedy, all stripped, failures restored after | 16 of 27 routed, then 344 shorts (h8) or the restore cascade (h7) |
| h9/h10 | rip-up-and-reroute one net at a time | 8 of 27; A3 and the other ring-1 balls: "no path" |
| h12 | all stripped, one at a time, trades kept | A5, BS1, D12 closed; D8, D10, AIN15_N opened; discarded |

Why: with only its own copper stripped, a ring-1 ball's L2 piece is the
sealed 12 700-cell pocket (the wall is the group's own exit column and N-S
runs); with the whole group stripped the pocket opens, but the corridor then
holds about 16 of the 27 -- the L1-stub-plus-column scheme it replaces
carried 21. The conversion moves capacity from L1 to L2; it does not add
any, because every westbound route still has to cross x 39..42 and drop to
L4/L6/L7 through the same few via sites. `zulu_a7.hdi-stage1-27.brd` is the
Fusion-verified stage-1 board (27 airwires, DRC clean apart from the length
match and 4 Wire Stubs): the 44 ball microvias and their L2 routes are valid
copper, one net behind the deployed board because D9 is still open.

What the fan-out would need to pay off: the through vias of rings 1-3
routed INWARD into the empty annulus (rings 4-6) so the outer band of the
footprint is via-free on L4/L6/L7, and the via column at x 39.2 moved into
that annulus. That is a re-plan of all 117 signal balls, not 20, and this
router's negotiation does not converge above about 20 nets; sequential
routing converges but cannot trade. It is at this point a job for a
different router or for hands in Fusion.

### The annulus is not empty -- 2026-09-06

Before generating the inward fan-out, `scratchpad/annulus_survey.py` checked
the ring-4 position directly inside each of the 35 ring-3 signal balls, the
only placement that leaves every annulus via a clear path outward. **Four of
the 35 are free.** The other 31 sit on the traces that already run under U1
between the balls and the centre power block: 2 to 20 segments each, on L4,
L6, L7 and L16, of up to five nets (A6's spot: nine L6 segments plus L7, L16
and L1 of AIN16_N, GND, LED0_B, LED0_R; CHAN4's: 26 segments of CHAN5,
FLASH-CS#, FLASH-D02, FPGA-DONE). The annulus has no balls because it is the
inner-layer highway; every route that crosses under U1 uses it. A via field
there means re-routing everything that crosses U1, which is most of the
board, and 117 vias at 0.5 mm pitch would leave no lanes between them in
any case (0.20 mm gaps, 0.23 needed). With one microvia layer the fan-out
that pays off needs a second escape layer -- L3 as signal under a 2+4+2
build -- or a coarser BGA. This is the stopping point for the router.

Order matters between the two moves: the CHAN bus re-plan on the board that
already carried phase A's seven closures (run 6) lost routed CHANs and gained
nothing, while phase A on the re-planned board (run 7) kept the three CHAN
closures and added eight nets. The pocket phase itself -- rip the largest wall
around a boxed piece, route, keep only if nothing lost -- closed nothing in
three hours on any of these boards; its wall ranking put plane-net gang
traces first even for a pocket on L2, which is fixed for the next runs.
Still open on `zulu_a7.brd`: CHAN7, CHAN13, CHAN18, CHAN23, CHAN24 (header
pins), A5, BS1, D6, D12, LDQM, WE# (U3), AIN15_P, CFG-M0, DONE (2), FB1_NODE,
FPGA-CCLK, FT-PWREN#, LED0_G, LED2, NODE_P0, PROG#, UART_FT_RTS#, UART_FT_TXD
(passives near U1), FLASH-D01 and GNDADC (ripped under R9/R38 and R23 for
the microvias, not yet rerouted).

The four GND pads: two got a 0.20/0.30 via beside them with a 0.15 mm wire,
one a 0.15 mm wire to the new via of its neighbour, one (C at 45.78, 22.26,
a 0.3 mm pad between two L4 traces) a **via in the pad** at (45.778, 22.268),
the only spot where the land clears both traces by 3 mil, and one (C at
51.35, 3.73, boxed on L1 by CHAN17, VCC1V8 and a VCC3V3 via, with CHAN12,
CHAN14 and TDI under it on L2 and L4) a 4 mm, 3 mil L1 wire to the GND via
at (54.18, 4.80), the only lane the maze found. `tools/fab_notes.py` now
writes the FAB NOTE lines on layer 48 from the file itself: the via
inventory, and every via that sits in an SMD pad listed as filled-and-capped
via-in-pad -- the 30 microvias, the GND one, and the older 0.20 mm through
vias in U3's pads.


**Fusion reads the file's NEW-STYLE rules, not the legacy `<param>` list.**
With `msWidth` set to 10 mil and `mdWireWire` to 6 mil in the file, DRC
reported nothing new, and with `msDrill`/`msMicroVia` at 0.09 mm it still
flagged all 30 microvias as "Drill Size". The rules Fusion applies are the
`<rule type="...">` elements inside `<designrules>` -- and there
`Minimum Drill Size` still said **0.2 mm**. Loading the legacy parameters as a
`.dru` (`board/zulu_a7_pcbway_hdi.dru`, via `/`, `DRC LOAD <path>;`, `DRC;`)
replaced that rule set and proved the point: **Air Wire (31) and Matched
Signal Lengths (1)** were the only errors left. The file itself is now fixed:
`hdi_swap.py` sets that rule to 0.1 mm along with `msMicroVia`, so a fresh
open of `zulu_a7.brd` reports no Drill Size errors without loading anything.
Other new-style rules worth knowing: `Drill Distance` 0.2 mm, `Dimension
Clearance` 0.3 mm, `Matched Lengths` tolerance 10 mm / gap factor 2.5. The
one Matched Signal Lengths error is NOT the USB pair (D+ 21.8 mm, D- 20.9 mm,
inside the tolerance): raising the tolerance to 50 mm clears it, raising the
gap factor does not, so it is a `_P`/`_N` pair more than 10 mm apart in
length: **AIN16_P 10.3 mm against AIN16_N 33.0 mm** (AIN15 is 12.9 against
19.3, inside the rule). AIN16_N takes a 23 mm detour; a forced reroute of
that one net (`CLOSE_FORCE`) or a meander on AIN16_P clears the error. For
an XADC input pair it has no electrical weight.

### The other end of the open nets -- 2026-09-05

With the balls escaping through L2, the pieces that stay bare are the OTHER
ends: six 0201 resistor pads on the bottom directly under U1 (PUDC_B,
CFG-M0, DONE, NODE_P0, PROG#, AIN15_P's C36), boxed in on L16 by the
dogbone via field, and 0201/0603 pads on the top between x = 24 and 34 mm
(UART_FT_RTS#/TXD on L5, FT-PWREN# on C13, LED0_G on LD0, DONE on R100),
boxed on L1 by the buses that pass them. `tools/pad_microvias.py` gives each
the same answer the balls got: a 0.10/0.20 mm microvia in the pad, 1-2 on
top and 7-16 on the bottom, at the first spot inside the pad where the
inner layer is clear; with `--rip` it takes out the foreign inner-layer
segments under a pad that has no such spot (FLASH-D01 under R38 and R9,
CHAN7 and FLASH-D02 under R23, FT-RESETN under LD0 -- 22 segments) for the
router to reroute. `zulu_a7.hdi-46r.brd` carries 14 such microvias. The
wall the floods then meet is no longer a pad row: for CHAN8 the ball's flood
covers the right half of every routing layer and the header pin's flood the
left half, and what separates them is the routed traffic itself -- SD-DAT2
and D9 along U1's west edge on L2, the dogbone via column at x = 43.35, the
horizontal buses on L7, A1's and SD-DAT2's staircases above U1 -- about
fifty nets on the frontier, which is what the pocket router rips one at a
time.

Wire Stub warnings are the other thing Fusion counts by its own rule: a wire
end that meets no other wire END on its layer, no via centre, and no pad. The
old check_board rule accepted a wire ending on another wire's body and passed
a board on which Fusion reported 39; `check_board.py` now uses Fusion's rule
and `fusion_connect.py` clears every stub it can (snap, split, hop, bridge,
delete a stump). The 15 that remained were wires ending inside a pad but off
its centre with nothing else at that point; a hop to the pad centre ends
each of those where Fusion wants it.

What would finish it, in order of cost: route the SDRAM bus fresh on L2/L7
with the whole U3 neighbourhood (GND and VCC3V3 stubs included) re-tied by the
plane pass afterwards -- a bus re-plan, not a pocket at a time; or move U3
0.5 mm away from the BGA ring so its top pad row is not inside the ring's
shadow. Both are placement-and-plan work for a fresh session.

The six-layer/JLCPCB material below is retained as design history and no longer
describes the active board.

> **The active outline is 2.750 x 1.000 in (69.85 x 25.40 mm).** The original
> 2.400-inch prototyping-header area is unchanged. The added 8.89 mm right-side
> strip carries J1, JP3, and JP4, centred at x = 65.39 mm. Historical analyses
> below identify the outline on which their measurements were made.

> ## The BGA escape is finished
>
> All three stages verify clean and all three are on the board.
>
> | | | |
> |---|---|---|
> | stage 1 | gang the plane balls | **73 traces** at 0.225 mm |
> | stage 2 | out of the enclosed rings into the moat | **54 traces** at 0.0762, **54 vias** |
> | stage 3 | fan out of the package to a ring at half-width **7.260 mm** | **1170 traces** at 0.09, **103 vias** |
>
> **1297 wires and 157 vias**, all on L1, every one clearing foreign copper by
> at least 0.090 mm. **230 of the 238 ball lands carry copper**; the 8 that do
> not are the package's no-connects.
>
> `check_board.py` 0 findings on both fabs, `validate.py` 0, `check_planes.py` 0
> with its two controls still failing as they must, junction audit clean, and the
> netlist byte-identical to the schematic it came from.
>
> What remains is ordinary routing: 52 of 175 signals still carry no copper, and
> the ground pour on L1/L6 stitched to L2/L4 has not been drawn.

> **Two fabs, two boards, one schematic.**
>
> | | root `zulu_a7.sch` / `.brd` | `board/pcbway/` |
> |---|---|---|
> | fab | **JLCPCB — active, route this** | PCBWay, **Plan A** (conventional) |
> | ball land | **0.225 mm** (0.82:1) | **0.225 mm** — same footprint |
> | line / space | 3 mil trace, 3.5 mil clearance | same, **pending confirmation** |
> | escape | between two lands, **+0.0188 mm** | identical geometry |
> | status | ready to route | line/space unconfirmed — see below |
>
> **PCBWay answered on 2026-08-27** (`board/PCBWAY-DFM-ENQUIRY.md`). They build
> BGA pads down to **8 mil (0.2032 mm)** at pitches to 0.4 mm, so our 0.225 land
> is fine; **0.5 oz and 1 oz outer both work**; and **HDI is out** — "would add
> the manufacturing a lot, so planA would be recommended". That collapsed the two
> variants onto one footprint: they now differ only in the rules file.
>
> What they did **not** answer is line and space inside the BGA, which is the
> number that decides everything. A follow-up is drafted.
>
> ```bash
> python tools/make_board.py --fab jlcpcb    # writes the root pair
> python tools/make_board.py --fab pcbway    # writes board/pcbway/
> ```
>
> Both are generated from the root `zulu_a7.sch`, which is **the only schematic to
> edit**. The nets are identical; the land diameter and the rules are all that
> differ. `check_board.py` reads the fab out of the board and checks the land
> against it, so a board carrying the wrong land for its fab fails.

## Start the board from the schematic, not from zulu_a7.brd

The existing `.brd` is the Spartan-6 layout and is not worth annotating onto:

    elements               65   against 216 parts  ->  189 missing, 38 stale
    package mismatches     16   C3/C4/C5... 0603 where the schematic says 0402
    routing               421 connections, 176 vias, all for the old FPGA
    design rules          the old board's

It does declare a four-layer stackup — `layerSetup (1*2*3*16)`, Route2 and
Route3 active — but no copper has ever been placed on the inner pair.

**Fusion 360 Electronics:** open the schematic, then *Switch to PCB Document*,
or add a new PCB to the design from the browser tree. Create a fresh PCB rather
than opening the stale one. All 216 components land outside the outline.

**Eagle:** move `zulu_a7.brd` aside, open `zulu_a7.sch`, *File → Switch to Board*.
With no `.brd` present it offers to create one from the schematic.

Then load `zulu_a7-6layer-jlcpcb.dru` (DRC dialog → Load) *before* routing
anything, so the rules are in force from the first trace.

## Board outline

**69.85 × 25.40 mm = 2.750 × 1.000 in.** Widened from 0.800 in and extended only
at the right edge. See "The board was 0.800 in and the parts did not fit" below
for the widening.

**X2's two pin rows widened with it, 0.700 in → 0.900 in**, keeping the 0.050 in
of board outboard of each row that the 0.800 in outline had. In ZULU-DIP37 they
sit at y 1.27 and 24.13.

### Which breadboard columns it lands in

Column positions step 0.1 in outward from 0.15 in either side of the centre
channel — the channel is **0.300 in**, three pitches, not one.

| breadboard | pins in | board covers | free to patch |
|---|---|---|---|
| standard 5+5, a-e \| f-j | **b and i** | b c d e f g h i | a \| j |
| wide 6+6, a-f \| g-l | **c and j** | c d e f g h i j | **a b \| k l** |

The edges land exactly halfway between two columns, so an edge never falls on a
hole. Both power rails stay clear either way.

#### Leaving the rows at 0.700 in was wrong, and wrong twice

It was the first attempt. It put the rows 0.150 in inside the edges instead of
0.050, so the pins landed in **d and i** rather than c and j; and it split the
interior into a 16.256 mm channel plus two 3.05 mm strips outside the rows,
rather than one continuous channel:

| pin span | channel | strips outside | usable / side | parts parked |
|---|---|---|---|---|
| 0.700 in | 16.256 mm | 2 × 3.05 mm | 1590 mm² | 4 |
| **0.900 in** | **21.336 mm** | none | 1529 mm² | **2** |

Slightly less raw area, and better in every way that matters: one band instead
of three, and the two left over are the Creative Commons silk logos rather than
SDRAM bypass capacitors.

A related defect went with it. The layer 39/40 keepout bands over the pin rows
are 2.54 mm tall, centred on each row. Widening the outline moved only their
outer edge, so the top band became **17.78 → 25.40, three times too tall**,
sterilising 355 mm² across both sides. That is what "24 decoupling caps did not
fit the window" was reporting.

### The board was 0.800 in and the parts did not fit

Two problems, and they turned out to be the same problem.

**Placement.** 2411 mm² of parts and permanent reservations against 2347 mm² of
usable interior: 63 mm² short on paper, and 44 parts actually parked, because
bulk area is a floor and the leftovers came out as strips too narrow to take an
0402 on end.

**The escape.** Stage 3's fan-out ring was pinned at half-width 6.20 mm, which
left 103 escapes a 1.20 mm band to fan through, and the fan angle was the whole
of what was still wrong with it — 28 trace conflicts, all of them neighbours
converging because perpendicular separation is tangential separation times
cos(lean).

The link is that **6.20 was never a board limit**. The edge allowed 9.46 and
X2's pad rows 7.43. It was the decoupling capacitors, sitting in the annulus the
fan wanted, and they were there because there was nowhere else for them to be.

| what | 0.800 in | 1.000 in |
|---|---|---|
| usable, both sides | 2347 mm² | **3180 mm²** |
| slack over what the parts need | −63 mm² | **+769 mm²** |
| parts parked | 44 | **4** |
| fan-out ring half-width | 6.20 mm | **6.38 mm** |
| stage-3 conflicts | 29 | **18**, all trace |

The widening grew the board 2.54 mm at each edge and moved the whole assembly
with the pin rows; the new area is the two strips outboard of the rows, which at
0.800 in were 0.51 mm and worth nothing. `make_board.py` applies the offset in
one place rather than restating forty coordinates — see `YOFF` and `yb()` there,
and the matching pair in `board_plan.py`.

#### Reserving the annulus is what converts the space into fan-out room

Widening alone does nothing for the escape. `tile()` fills whatever is free, so
without an explicit reservation the parts go straight back into the 6.20–7.64
band and `fanout_h` finds 6.20 again. `RING` reserves it, on **both** sides,
because a via is a through hole. On the 0.800 in board that reservation cost 18
more parked parts on top of the 44; at 1.000 in it is affordable.

`fanout_h`'s search cap was also 6.20 — not a limit, just where the search
stopped, and it had matched the real obstruction closely enough that nothing
ever noticed. Raised to 7.40.

#### The ring stops at 6.38, not 7.40, and that is honest

`fanout_h` used a box test for clearance while `verify3` measures copper as a
circle of its diagonal half-extent. The box test cleared 6.94 against Q1 and
R24; the verifier then reported five conflicts against exactly those two parts.
A search that returns a radius the verifier rejects is worse than no search,
because the failure resurfaces a stage later wearing a different name. Both use
the strict measure now, and it also checks the whole band the traces occupy —
`STUB` inboard of the ring to a via land outboard — not just the via itself.

**Q1 and R24 are what cap it at 6.38.** Moving them further out is the next
thing worth trying on the escape: the measured curve was 6.20 → 28 conflicts,
7.00 → 11, 7.40 → 6, plateauing at 6.

The pin grid is 24 columns and stops at x = 59.69. The original prototyping area
ends at x = 60.96, 1.27 mm past the last pin. An 8.89 mm connector-only strip
runs from x = 60.96 to 69.85; J1, JP3, and JP4 share x = 65.39 mm so they remain
outside the prototyping-header area.

### How the 44 pins are laid out

Both rows number **right to left**, and the numbering runs straight through from
one row to the other — pad 1 at the top row's right end, along to pad 20, then
pad 21 at the bottom row's right end and along to pad 44. Reading down either
column of the schematic symbol on sheet 3 walks the pads in order, which is the
only place the pinout is legible: the symbol shows gate names, not pad numbers,
so if the drawn order ever stops matching the pads the schematic silently lies.
Anything that moves a pin has to move its symbol instance too.

| | Top row (y = 19.05) — schematic **left** column | Bottom row (y = 1.27) — schematic **right** column |
|---|---|---|
| Pads | 1–20, x 59.69 → 1.27 | 21–44, x 59.69 → 1.27 |
| Count | 20 | 24 |
| Starts with | GND (1), +3.3V (2), GND (3), CHAN-CLK (4)… | GND (21), **VU** (22), GND (23), RST# (24)… |
| Ends with | …+3.3V (17), +1.8V (18), +1.0V (19), GND (20) | …ANALOG-IO1 (43), **+5V-INPUT** (44) |

Both rows start and end on the same x, so the board has a pin at all four
corners, and **the pin field now fills all 24 grid columns** — the same span the
board was specified to occupy, breadboard rows 1 to 24.

**Four** interior top-row positions — x 29.21, 31.75, 34.29, 36.83 — are
deliberately vacant and belong to the USB connector, giving **11.176 mm clear**
between pad 9 at x = 39.37 and pad 10 at x = 26.67. X1 needs 7.80 mm of copper
and is centred in that with 1.69 mm each side.

The gap sits between pins **9 and 10**, not 8 and 9. Moving CHAN4 across it from
x = 29.21 to 39.37 shifted the whole vacant run one place towards the microSD end
without changing its width or the numbering — CHAN4 is the ninth occupied
position from the right either way, so it stays pad 9.

#### The six pins at the far end are power and ground

They are the last three columns, which carried nothing until now. There were no
FPGA channels left to put there — 130 of U1's 138 user-I/O gates are wired and
the only 8 spare are `MGTPTX*`/`MGTREFCLK*`, which are not bonded as user I/O in
CPG236 — so they went to the thing the header was short of instead. **The header
had exactly one ground pin serving 32 signals.** It now has five, arranged with
the rail flanked by grounds on each row so every return has one adjacent:

| | x 59.69 | x 57.15 | x 54.61 |
|---|---|---|---|
| Top row | GND (1) | +3.3V (2) | GND (3) |
| Bottom row | GND (21) | **VU** (22) | GND (23) |

Pin 22 is **VU**, not VEXT — it is downstream of the OR-ing diodes, so it can
source 5 V rather than only accept it. Current drawn there comes through D1 from
USB or D2 from VEXT, both PMEG2020EJ at 2 A, so the real limit is whatever the
USB port supplies. Pin 44 remains VEXT, the input, and is labelled **+5V-INPUT**
on the symbol so the two 5 V pins cannot be mistaken for each other.

Adding six pads renumbered everything: what was pad 1–17 is now 4–20 and what
was 18–38 is now 24–44. Anything written against the old numbers is stale.

**Pin 44 is +5V-INPUT, on net VEXT, which is not VU.** VEXT is the external
input: it reaches VU through D2 and is clamped by D3, while USB 5 V arrives
through D1, so VU is the diode-OR of the two. Feed 5 V into pin 44 to run the
board without USB; take 5 V **out** of pin 22, which is VU itself.

Recreate on layer 20, width 0. In X2's own package frame the board is the
rectangle (0, 0) to (60.96, 25.40); place the outline to match wherever X2
lands:

    (0, 0)         ->  (60.96, 0)
    (60.96, 0)     ->  (60.96, 25.40)
    (60.96, 25.40) ->  (0, 25.40)
    (0, 25.40)     ->  (0, 0)

X2 occupies all 24 grid columns and 44 of the 48 slots; the four empty ones are
the USB landing. There is no strip past the grid any more, so no part of the
board is free of through-holes: the Pmod and the two JTAG rows stand among them,
in the channel between X2's rows.

The microSD can no longer live there. Its layer-39 keepout is the card plus
21.55 mm of eject stroke, so it has to throw the card off a board END rather
than a long edge, and the +x end is now Pmod. X3 is turned to eject over the
**-x end**, where the card overhangs by about 5.6 mm.

## Stackup — PCBWay 6-layer, 1.6 mm, 1 oz, 70 % residual

Taken from PCBWay's own standard-stackup list (`multi-layer-laminated-structure`,
6-layer section, entry 1), not from a blog article. An earlier revision of this
file carried 0.110 / 0.530 numbers that are not in that list at all.

> **IT IS A PLANNING ASSUMPTION, NOT A COMMITMENT.** Asked directly for the
> 6-layer stackup on 2026-08-27, PCBWay answered: *"the stack-up can be
> customized based on the impedance value, we don't have standard stack-up info
> for that."* Their published list is real and this table is read from it
> correctly, but their DFM contact will not stand behind a standard build — they
> work from an impedance target and design the stack to hit it.
>
> Two consequences. **Nothing here is confirmed by the fab**, so any impedance
> width computed from these Dk and thickness figures is provisional. And if
> controlled impedance is wanted, the order of operations is the other way round
> from what this section assumes: state a target Z0 first, let them return the
> stack, then compute widths. Nobody has specified a target for this board, and
> the SDRAM bus is the only thing on it fast enough to raise the question —
> 166 MHz over runs under 25 mm.

Which of their several 6-layer 1.6 mm builds applies is chosen by **inner-layer
residual copper ratio**. Ours is L2 solid, L3 signal, L4 solid and L5 **solid**
— the three-way split was measured and abandoned, see the box further down, so
the ratio is higher than when this was written, not lower. Comfortably above
60 % either way, so it is the 70 % structure:

| | material | nominal | after lamination | Dk |
|---|---|---|---|---|
| **L1 Top** | base copper 0.5 oz, **plated to 1 oz** | 0.0175 | 0.035 finished | |
| | prepreg 2116 RC58 % | 0.1300 | **0.1195** | 4.45 |
| **L2** | copper 1 oz | 0.0350 | | |
| | core | | **0.4300** | 4.60 |
| **L3** | copper 1 oz | 0.0350 | | |
| | prepreg 7628 RC46 % | 0.1960 | **0.1750** | 4.74 |
| **L4** | copper 1 oz | 0.0350 | | |
| | core | | **0.4300** | 4.60 |
| **L5** | copper 1 oz | 0.0350 | | |
| | prepreg 2116 RC58 % | 0.1300 | **0.1195** | 4.45 |
| **L6 Bottom** | base copper 0.5 oz, **plated to 1 oz** | 0.0175 | 0.035 finished | |

PCBWay quotes 1.45 mm after lamination and **1.55 mm +/- 10 % finished** — it is a
"1.6 mm" board by class, not by measurement. The `.dru` carries finished copper
(0.035 on all six) against the after-lamination dielectrics, so Eagle totals
1.494 mm.

Note the outer layers: **0.5 oz base plated up to 1 oz finished**. That is not a
detail, it is what the whole DFM question below turns on.

### Layer roles — L4 is a SIGNAL layer (changed 2026-08-27)

The thin dielectrics are L1–L2, L5–L6 and the middle L3–L4; the two 0.430 cores
sit at L2–L3 and L4–L5. Same shape as the stack this replaced, so the roles carry
over unchanged. Every signal layer is paired with a plane across a thin gap:

| layer | role | references | across |
|---|---|---|---|
| L1 | signal — escape, components | L2 | 0.1195 |
| L2 | **GND plane, solid** — poured 2026-08-27 | — | |
| L3 | signal — SDRAM bus, X2 header | L2 | 0.5495 |
| L4 | **signal** — SDRAM bus, X2 header | L5 | 0.5495 |
| L5 | **VCC3V3 plane, solid** — poured 2026-08-27 | — | |
| L6 | signal — components, remaining nets | L5 | 0.1195 |

**Four signal layers and two planes**, `sig / GND / sig / sig / PWR / sig`, which
is a standard six-layer arrangement. It replaced `sig / GND / sig / GND / PWR /
sig` on 2026-08-27 and the reason is measured, not stylistic.

> ### Why L4 stopped being a plane
>
> On paper the old stack had three signal layers. In practice it had **two**: L1
> is consumed entirely by the escape — 1314 wires, all short stubs from ball to
> fan-out ring — so the SDRAM bus and the X2 header were competing for L3 and L6
> alone. Freeing L4 was the only change tried all day that ADDS routing resource
> rather than rearranging it, and it is the only one that moved the number:
>
> | | before | after |
> |---|---|---|
> | SDRAM bus | 21 of 39 | **29 of 39** |
> | X2 header | 25 of 39 | **28 of 39** |
> | both, on one board | 36 of 78 | **57 of 78** |
>
> **That table is the L4 experiment, not the board's present state.** It was
> measured with only two groups on the board. The USB/FT2232 group has since
> been routed as well, and it takes its share: see "Where the routing stands"
> below.
>
> Four other things were tried first and every one of them failed: flipping U3 to
> the front, pouring and stitching last, thinning the escape ring, and PCBWay's
> 3 mil line/space. All four kept the two-layer budget and rearranged inside it.
>
> **The cost.** L3 loses the ground plane below it and now references L2 across
> 0.5495 mm instead of L4 across 0.1750; L4 references L5. Each still has a plane
> on one side. Route the two middle layers orthogonally — one predominantly X,
> one predominantly Y — which is the usual discipline for this stack. For a
> 166 MHz SDR bus over runs under 25 mm that is ordinary practice.
>
> **L2 AND L4 HAD NEVER BEEN POURED.** Nothing in the toolchain had ever written
> copper to either — no wires, no polygons — while this section asserted "solid
> GND" and check_planes tested them ANALYTICALLY, modelling the geometry rather
> than reading the file. Gerbers would have gone out with two bare inner layers.
> `ground.py` pours L2 now. It surfaced only because Christian asked whether L3
> and L4 were actually being used.

**L5 is solid, not split.** It was carried as a three-way split between VCC3V3,
VCC1V0 and VCC1V8 from the beginning; that was measured on 2026-08-27 and does
not work — see the box below. VCC3V3 has it to itself and the two low rails are
wide traces.

That makes the layer plan simpler than it was. **No signal layer references a
split plane** — L1 and L3 reference solid ground, L6 references solid VCC3V3 —
so the old caveat about keeping fast edges off the bottom layer is gone. A trace
on L6 now has a continuous reference for its whole length, and its return current
gets from the VCC3V3 plane to the ground planes through the decoupling and the
108 stitching vias.

> ## The three-way L5 split does not work, measured 2026-08-27
>
> It was carried from the start as "L5 split 3V3 / 1V0 / 1V8" and never tested
> against where the loads actually are. Tested now, it fails.
>
> | rail | loads | | |
> |---|---|---|---|
> | VCC3V3 | **129 pads** | x 1.55 .. 67.67 | the whole board |
> | VCC1V0 | 23 pads | x 3.81 .. 57.39 | regulator to FPGA |
> | VCC1V8 | 14 pads | x 6.35 .. 57.39 | regulator to FPGA |
>
> Both low rails run the **full length** of the board — U8 and its inductors at
> the left end, the FPGA and its decoupling at the right — and they interleave
> with each other and with VCC3V3 the whole way. Partition L5 by nearest load,
> which is the most favourable split that exists, and:
>
> | rail | pieces | area | the pieces, mm² |
> |---|---|---|---|
> | VCC3V3 | **1** | 1461 mm² | 1461 |
> | VCC1V0 | **10** | 180 mm² | 84, 19, 16, 14, 13, 13, 7, 6 … |
> | VCC1V8 | **10** | 113 mm² | 21, 20, 15, 14, 10, 10, 9, 8 … |
>
> **A planelet arriving in ten disconnected pieces is not a plane.** Each piece
> needs its own feed, the fingers joining them are narrow and therefore high
> impedance, and every finger is a slot in the reference under whatever L6 routes
> across it — which is the one thing the layer plan above was arranged to avoid.
>
> ### What to do instead
>
> **L5 solid VCC3V3**, and VCC1V0 and VCC1V8 as wide traces.
>
> VCC3V3 is the rail that earns a plane: 129 loads, spread over the whole board,
> and it comes out as a single 1461 mm² piece with no split at all. The other two
> are effectively point-to-point — one regulator output to one FPGA power group,
> with decoupling along the way — and a 1 mm trace in 1 oz copper carries about
> 2 A, comfortably over what VCCINT and VCCAUX draw on an XC7A35T.
>
> That also **removes the caveat above**: with L5 unsplit, L6 no longer
> references a split plane and "keep fast edges off the bottom layer" stops being
> a constraint. The layer plan gets simpler, not more complicated.
>
> ### APPLIED 2026-08-27
>
> L5 is poured solid VCC3V3 by `tools/ground.py`, alongside the GND pours on L1
> and L16. It is the one pour with **thermals off** — a plane exists to be low
> impedance and a thermal spoke is four narrow necks in series with it, whereas
> L1 and L16 keep thermals because those pads are hand-reworkable.
>
> And `check_planes.py` checks L5 now, having declined to for exactly as long as
> the split was the plan. The board carries **265 vias of which only 16 are
> VCC3V3**, so 249 of them punch an antipad through it — worth measuring rather
> than assuming:
>
> | isolate | antipad | pieces | largest | share of the copper |
> |---|---|---|---|---|
> | 0.20 | 0.70 | 4 | 1681 mm² | **99.8 %** |
> | 0.25 | 0.80 | 4 | 1681 mm² | **99.8 %** |
> | 0.30 | 0.90 | 6 | 1652 mm² | **99.8 %** |
>
> Intact at every isolation tried. The strays are 3.8 mm² and below, in via
> shadows, and `orphans="no"` means Eagle drops them itself — so the test is
> whether the main body holds, not whether stray copper exists.

### Trace widths

IPC-2141 closed form, +/-10 % typical — confirm against PCBWay's impedance
calculator before ordering. **Two columns**, because the outer-copper decision in
the DFM section below moves every microstrip:

| target | layer | geometry | 1 oz outer | 0.5 oz outer |
|---|---|---|---|---|
| 50 ohm single-ended | L1 / L6 | microstrip, h 0.1195, Dk 4.45 | **0.178 mm** (7.0 mil) | **0.200 mm** (7.9 mil) |
| 90 ohm differential, gap 0.127 | L1 / L6 | microstrip | 0.153 mm each | 0.174 mm each |
| 90 ohm differential, gap 0.152 | L1 / L6 | microstrip | **0.164 mm** each | 0.185 mm each |
| 50 ohm single-ended | L3 | stripline, 0.175 to L4 / 0.430 to L2 | **0.168–0.195 mm** | same (inner copper unchanged) |

The L3 figure is a bracket between two models — offset stripline referenced mainly
to the near plane (0.168) and symmetric stripline across the full 0.605 mm between
L2 and L4 (0.195). The truth is between them. Inner copper is 1 oz either way, so
only the outer layers move with the copper decision.

**These widths are for controlled-impedance nets only** — the USB pair, and the
SDRAM bus if you choose to control it. They are not the escape width.

### The DFM question, answered: PCBWay does not publish 2/2 mil

The question was whether 2/2 mil is tied to 1/3 oz base copper. Checked against
their published capability tables, the premise is wrong and the instinct behind it
is right.

**There is no 2/2 mil.** The Standard PCB page says "Min manufacturable trace is
4mil(0.1mm)" and the same for spacing. The Advanced PCB table, item 15, *the min
width/spacing of outer layer (before compensation)*:

| outer copper | normal | medium difficulty | non-standard review |
|---|---|---|---|
| **18 um** | >= 4/5 mil | >= 4/4 mil, **or parts 3.5/3.5 mil** | < 3.5/3.5 mil |
| **35 um** | >= 5/6 mil | >= 5/5 mil | < 4/4 mil |

with the remark on the 18 um row: *local 3.5/3.5 mil, only the distance from the
BGA chip area line to the PAD*. 2 mil appears only on their HDI page, for
laser-imaged HDI builds, alongside a 1.2/1.2 mil figure — not for a through-hole
board.

**But the copper relationship is real**, just at 3.5 mil rather than 2, and it is
*finished* copper, not base. What matters at the etch step is the copper thickness
on the layer at that moment, which for an outer layer is base plus plating:

- 35 um finished outer = 1 oz = 0.5 oz base plated up. **This is what every one of
  PCBWay's standard 6-layer 1.6 mm stackups uses**, including ours above.
- 18 um finished outer = 0.5 oz = 1/3 oz base plated up. Only this row unlocks the
  4/4 and the local 3.5/3.5.

So reaching the finest geometry means ordering **0.5 oz finished outer copper**,
which is a custom stackup, and it moves the L1/L6 widths in the table above by
about 12 %. That is the second column.

## X1 — rebuilt from the Molex drawing

**Done 2026-08-26** against `SD-105017-001` rev F sheet 1, material 105017-0001,
the RECOMMENDED P.C.B. PATTERN LAYOUT. The drawing is at
`XuLA3/Datasheet/1050170001_sd.pdf`, outside the repo with the others.

Measurements came off the PDF's **vector geometry**, not a render. Sheet 1 is a
`/Rotate 90` page, which is why the first attempts found nothing — `get_drawings()`
reports unrotated coordinates. Scale was set by the 5.00 mm between the plated-hole
centres and then checked twice against the drawing's own callouts:

    1.45 mm plated-hole land   measured 1.4467
    0.85 mm plated-hole drill  measured 0.8426

### The pattern, origin at the rear-row centreline, +y toward the PCB edge

| pads | x | y | geometry |
|---|---|---|---|
| **1–5** signal | −1.30, −0.65, 0, +0.65, +1.30 | 0 | SMD 0.40 × 1.35, 0.65 pitch |
| **MH1, MH2** rear shell nails | ∓2.50 | 0 | **plated, ø0.85 drill in a ø1.45 land** |
| **MP1, MP4** outer front tabs | ∓3.20 | +2.70 | SMD 1.80 × 1.90, R0.50 corners |
| **MP2, MP3** inner front tabs | ∓1.00 | +2.70 | SMD 1.50 × 1.90 |
| **MS1, MS2** slots in the outer tabs | ∓3.50 | +2.70 | **plated slot 0.60 × 1.30** |
| PCB EDGE | | **+4.141** | on layer 48 |
| mating face | | +4.841 | **0.70 mm past the board edge** |
| courtyard | ±4.893 | −1.486 … +4.141 | layer 39 |

Chain checks that all closed: 0.50 between the inner tabs, 3.50 across them,
4.60 between the outer tabs' inner edges, 7.00 between the slot centres, 8.20
overall, 1.30 slot length, 1.90 tab height, 1.35 pad height.

### The rotation was never the problem

R0 was right all along. The mouth does face +y, the top edge. What was wrong was
the footprint's insides: the silk bracket was open on the **rear**, which is what
made it read as mis-rotated, and the four SMD tabs were invented.

### Two things this cost, one of them a real decision

**1. U3 dropped 1.20 mm — and it is no longer centred on the Pmod.** The rear
shell nails are plated holes, so they are copper on *every* layer, and at
y 15.454–16.904 the drills went straight through U3's upper pad row. The old
footprint had four SMD tabs and no holes at all, so nothing on the back could
ever have collided; **the rebuild is what exposed it**.

1.20 rather than the 1.10 that merely clears the rule. These are *drilled*
holes: 1.10 left 0.114 mm land-to-pad against a 0.09 rule, and JLCPCB's hole
position tolerance is ±0.08, which would have eaten it. At 1.20 the clearance is
**0.214 mm**, still 0.134 after the worst-case drill wander.

U3 and J1 were both y-centred on 10.160, the board axis — that is what "centre the
SDRAM with the Pmod" meant. U3 is now at 8.960 and J1 is not. Moving J1 down to
match would leave it 1.67 mm off the bottom edge. **Left as a decision.**

**2. U2 dropped 0.12 mm.** Molex's courtyard reached 0.020 mm into U2's copper.
Physically nothing; 0.12 mm buys 0.10 of margin, and U2 stays x-centred on X1.

### Clearance around X1, measured

| | |
|---|---|
| X1 ↔ U2, both on top, copper to copper | **0.861 mm** |
| X1's plated holes ↔ U3 on the back | **0.214 mm** (0.134 after ±0.08 drill tolerance) |
| X1's courtyard ↔ U2 copper | 0.100 mm |
| X1's silk ↔ U2 copper | 0.586 mm |

The **0.861 mm channel** between X1 and U2 takes about **four** traces at 3 mil
with 3.5 mil clearance, and nothing else on the top layer crosses it — U3 sits
under that band but is on the back. Only four nets leave X1 at all (VBUS, D−, D+,
GND) and all four are headed for U2 directly below, so they run straight down the
channel rather than along it. There is room.

### Layer 46: JLCPCB does read it — with two conditions

Checked against JLCPCB's own Eagle article, *How to Generate Gerber and Drill
Files in Autodesk Eagle*. It says to **"Draw the slotted holes in the Milling
layer (46)"** using **"zero width lines and arcs"**, and their CAM job merges
layer 46 into the **GKO outline** output, which is where they require every
cutout, v-cut and slot to live or it is missed.

Two conditions, and both are on us:

1. **The CAM job must merge layer 46 into the outline.** Their published Eagle
   CAM does; a hand-rolled one might not. Check the GKO before uploading.
2. **A slot in the outline layer does not say whether it is plated.** JLCPCB's
   article explicitly recommends *adding a note to the order* naming any plated
   slotted holes. Do that — MS1 and MS2.

**This file had it wrong and it is fixed.** The slots were drawn as a 0.60-wide
stroke along the centreline, which is the other Eagle idiom. They are now
zero-width obround outlines — two straight sides and two `curve="-180"` arcs —
as JLCPCB asks. The 0.60 pad drill inside each slot stays on purpose: drill
first, then rout.

Size checks: 0.60 mm wide against JLCPCB's 0.35 mm minimum plated slot on a
multilayer board, so comfortable. The length-to-width ratio is 1.30 / 0.60 =
**2.17**, which clears PCBWay's hard floor of 2.0 but sits under the 2.5 that
JLCPCB's slot guide *prefers*. It is Molex's geometry, not a choice.

### Still unconfirmed: a plated slot INSIDE an SMD land

Nothing JLCPCB publishes covers it. Their slot guidance assumes a slot in open
board with its own land, and asks for ≥0.5 mm from a hole edge to nearby pads —
a rule our geometry cannot satisfy by construction, because the slot's own land
*is* the SMD pad it sits in. **Ask them directly.** It is the same message as the
3 mil question, so send both together.

### The overhang is deliberate and enforced

The shell hangs 0.70 mm past the outline by design. `check_board.py` knows and
reports it as a note rather than a finding, and the footprint carries the PCB
EDGE line on **layer 48** where the checker asserts it lands on the board
outline — so the placement and the drawing cannot drift apart.

## BGA escape — settled for JLCPCB at a 0.225 mm land

**Nothing drawn yet, but the geometry is settled and in the files.** Everything
below has been checked against the footprint rather than assumed.

### What is in the field

238 pads, matching `Datasheet/xc7a35tcpg236pkg_pinout.txt` exactly. Classified by
the net each carries — not by symbol type, which counts config straps as I/O:

| ring | grid index | signal | power/gnd | no-connect | total |
|---|---|---|---|---|---|
| 0 | 0 and 18 | 42 | 26 | 4 | 72 |
| 1 | 1 and 17 | 40 | 20 | 4 | 64 |
| 2 | 2 and 16 | 35 | 21 | 0 | 56 |
| 3–5 | | — | — | — | **empty** |
| 6–8 | core | 0 | 46 | 0 | 46 |
| | | **117** | **113** | 8 | 238 |

An earlier version of this section said 38/38/30 "user I/O" totalling 106. That
is the datasheet's user-I/O count, not the number of balls needing a route:
**117 carry a signal**, and there are **67 power/ground balls in rings 0–2** that
also need a plane, on top of the 46 in the core.

Rings 0, 1 and 2 hold 72, 64 and 56 balls — 4n−4 for n = 19, 17, 15. All three
are complete, so ring 1 is fully enclosed and every route out of it crosses a
populated row.

### The number, recomputed against what PCBWay actually publishes

Pads are round, **0.275 mm** — UG475 Table A-1, and the same table's text asks for
"a 1:1 ratio to the package solder mask defined (SMD) pad for improved board level
reliability", so 0.275 is both the maximum and the recommendation. On 0.500 mm
pitch the gap between two adjacent pad edges is **0.225 mm**, and a trace centred
in it needs w + 2s <= 0.225:

| rule | where it comes from | w + 2s | vs 0.225 gap |
|---|---|---|---|
| 5/6 mil | outer 35 um, normal | 0.4318 | no, by 0.207 |
| 5/5 mil | outer 35 um, medium | 0.3810 | no, by 0.156 |
| 4/4 mil | outer 18 um, medium | 0.3048 | no, by 0.080 |
| **3.5/3.5 mil** | **outer 18 um, local to BGA — PCBWay's finest** | **0.2667** | **no, by 0.042** |
| 3/3 mil | JLCPCB's finest, for comparison | 0.2286 | no, by 0.0036 |
| 2.5/2.5 mil | what this file used to assume | 0.1905 | would fit — but is not offered |

**PCBWay's finest published rigid geometry misses by 0.042 mm** — more than ten
times JLCPCB's 0.0036 mm miss. The fab change did not solve the escape. It was
made on a 2/2 mil figure that is not in their capability tables.

A through via in the diagonal void between four balls does not rescue it either.
The void gives 0.2543 mm of room at a 0.275 land with 3.5 mil clearance, and the
smallest via PCBWay will build — 0.15 mm drill, 3 mil ring at high difficulty —
needs a 0.3024 mm land. Short by 0.048 mm.

### Three ways out — superseded

The three options first written here (shrink the land at PCBWay, PCBWay HDI, or
change package) were derived from PCBWay's tables alone. Researching the other
fabs' published rules on 2026-08-26, while waiting for PCBWay to reply, found a
fourth that is better than any of them, and it is **back at JLCPCB**. Read the
next section instead.

## What the research found — the escape closes at JLCPCB, not at PCBWay

**Almost nothing here is a fab's confirmation.** It is their published capability
tables plus the geometry of this package, computed in
`tools/escape/options.py`. Treat every row as "publicly claimed", not "quoted to
us" — except the three things below, which PCBWay confirmed by email on
**2026-08-27**.

> **What PCBWay has now actually confirmed**, and what changed as a result:
>
> | they said | effect |
> |---|---|
> | BGA pad down to **8 mil (0.2032 mm)**, pitch to 0.4 mm | our 0.225 land is fine at PCBWay too — **the two fab variants collapsed onto one footprint** |
> | **0.5 oz and 1 oz** outer both work | no need to chase the 18 µm row for its own sake |
> | **HDI "would add the manufacturing a lot… planA would be recommended"** | Option B is dead; the 1+4+1-lands-every-ball-on-L2 problem dies with it |
>
> The one thing they did **not** answer is line and space inside the BGA — the
> only number that decides whether the escape closes. And their reply sits awkwardly
> with their own table: 3.5/3.5 mil appears there only on the 18 µm outer row,
> yet they say 0.5 oz and 1 oz both work. A follow-up is drafted in
> `board/PCBWAY-DFM-ENQUIRY.md`.
>
> Worth being precise about why the land alone cannot rescue it. `w + 2s` against
> `0.5 − land`:
>
> | land | gap | 3.5/3.5 mil (0.2667) | 4/4 mil (0.3048) |
> |---|---|---|---|
> | 0.275 | 0.225 | short 0.042 | short 0.080 |
> | **0.225** | 0.275 | **fits 0.008** | short 0.030 |
> | 0.2032, their floor | 0.297 | fits 0.030 | **still short 0.008** |
>
> **3.5/3.5 mil or finer is required whatever the land is.** Even at the smallest
> pad PCBWay will build, 4/4 mil does not escape this package.

### The thing that was never tried: a smaller land

Every earlier version of this file held the land at 0.275 mm because UG475 gives
that as the maximum and asks for a 1:1 ratio to the package pad. It is a
*maximum*, and the gap between two lands is `0.5 − land`, so the land is the one
term in the escape arithmetic that is ours to choose. Nobody had varied it.

| land | vs package pad | gap | what fits between two lands |
|---|---|---|---|
| 0.275 | 1:1, UG475's recommendation | 0.225 | nothing either fab publishes |
| 0.250 | 0.91:1 | 0.250 | 3/3 mil by 0.021 — but not 3/3.5 |
| **0.225** | **0.82:1** | **0.275** | **3 mil trace with 3.5 mil clearance, by 0.019** |
| 0.200 | 0.73:1 | 0.300 | 3.5/3.5 mil by 0.033 |

### What each fab actually publishes

| | JLCPCB | PCBWay |
|---|---|---|
| multilayer line/space | **0.09/0.09 mm (3.5/3.5 mil)** | 5/6 mil at 35 µm outer, 4/5 at 18 µm |
| in a BGA fan-out | **"3 mil is acceptable in BGA fan-outs"** | 3.5/3.5 mil local, and only at 18 µm outer |
| min BGA pad | **0.2 mm** (0.2–0.25 mm requires ENIG) | not published |
| min via hole / diameter | **0.15 / 0.25 mm**, preferred hole 0.2 | 0.15 mm drill, 3 mil ring → 0.3024 mm land |
| via-in-pad | epoxy filled & capped, **default on 6-layer and up** | resin filled + capped, "generally" for BGA |
| HDI / laser microvia | **none — through holes only** | 1+N+1 *normal process*, 4 mil laser, **0.065/0.065 mm** |
| surface finish | 6-layer is **ENIG** anyway | ENIG available |
| price of the fine line | **+20 % of the order** for 3.0–3.5 mil on 4–8 layers | in their medium/high-difficulty columns, unpriced |

Two rows decide it. JLCPCB explicitly allows **3 mil in a BGA fan-out**, which
PCBWay does not, and JLCPCB's minimum via is a **0.25 mm land on a 0.15 mm
drill** where PCBWay needs 0.3024 mm for the same drill. The board left JLCPCB
because 3/3 mil missed the 0.225 mm gap by 0.0036 mm — but that was measured
against a land nobody had questioned.

### The route that closes

**JLCPCB, 6-layer, land 0.225 mm, 3 mil trace at 3.5 mil clearance in the
fan-out.** No HDI, no via-in-pad, no custom stackup, and the original escape plan
below works unchanged. **This is what the root pair is now built to** — the land
went from 0.275 to 0.225 across all 238 pads, and the 0.325 mm mask opening
follows from the `.dru`'s 0.05 mm stop frame rather than being drawn:

    trace 0.0762 + 2 x 0.09 clearance = 0.2562   vs 0.275 gap   +0.0188 spare

The conservative reading is deliberate. JLCPCB's wording — *"3 mil is acceptable
in BGA fan-outs"*, singular, after a `0.09 / 0.09` width/space pair — most likely
concedes the 3 mil on **trace width only**, leaving clearance at 3.5 mil. If they
confirm 3/3 mil for both, the land can go back up to 0.250 (0.91:1) with 0.021
spare. **Ask before drawing.** Do not assume the generous reading.

Second choice, if 0.225 mm is judged too small a land: **PCBWay 1+4+1 HDI**, kept
alive as a generated variant in `board/pcbway/`, and the only route that keeps the
full 0.275 mm land. Their HDI line/space is
0.065/0.065 mm, which clears the 0.225 mm gap by 0.030, and a 4 mil laser via
sits inside a 0.275 mm land with 0.021 to spare. It costs the HDI premium and
lands every ball on L2, which is currently a solid ground plane.

### What this costs, and what still has to be confirmed

Changing the land meant rebuilding all 238 pads in the `ctambe` footprint. That
is **done** — `make_board.py --fab` now owns the land, rewrites it in the CPG236
package only (the old Spartan-6 FT256 footprint is still in the library at 0.4 mm
and must not move), and asserts the count at 238 so a silent miss cannot ship.

Open, in the order they matter:

1. ~~Does JLCPCB's 3 mil apply to spacing as well as width?~~ **RESOLVED
   2026-08-27 — the board needs nothing agreed.** Asked; they came back asking
   *which* 3.5 mil, which was a fair question (there are two, and this board uses
   one of each), and then pointed at their capability table row **Min. track
   width and spacing (1 oz)**:

   > Multilayer: **0.09 / 0.09 mm (3.5 / 3.5 mil). 3 mil is acceptable in BGA
   > fan-outs.**

   Two things follow, and together they close it:

   | our rule | vs their 1 oz multilayer standard | concession needed |
   |---|---|---|
   | spacing **0.0900 mm** | 0.09 — **meets it exactly** | **none** |
   | width **0.0762 mm** | 0.09 — below | the 3 mil BGA fan-out allowance, granted in the same sentence |

   So the spacing was never a concession, and **even on the narrowest reading of
   "3 mil" — width only — this board is inside their table as printed.** The ask
   was always smaller than it sounded; framing it as "3.5 mil" is what obscured
   that.

   And the row is the **1 oz** row, so the allowance holds at standard copper
   weight with no lighter foil. The 2 oz row drops to 0.15/0.15 multilayer, so
   weight does matter — and PCBWay by contrast puts its 3.5/3.5 only on the 18 µm
   row. That is a real advantage to JLCPCB here, not just a paper one.

   **Quote millimetres, not mils.** 0.09 mm is 3.54 mil and 0.0762 mm is
   3.00 mil; every mil figure in this file is a rounding of a metric number both
   fabs publish in mm, and the rounding is what caused the confusion.

   Still unstated: whether "3 mil" *also* covers spacing. It is now only an
   optional upgrade and **not a free one** — at 3/3 the land could rise to 0.250
   (0.91:1 rather than 0.82:1), but a 0.250 land leaves a 0.250 mm gap, which the
   present 0.0762/0.0900 does **not** fit (0.2562). It would force 3 mil spacing
   through the whole fan-out and re-cut the escape geometry, for a marginal
   reliability gain. **Recommendation: stay at 0.225.**
2. **Is 0.15 mm drill usable at all?** On a 1.6 mm board that is **10.7:1**,
   over the 10:1 ceiling both fabs work to. **Use 0.2 mm drill (8.0:1).** With a
   0.30 mm land it still clears the diagonal void at a 0.225 mm land by 0.030,
   and the centre annulus is not crowded either way. A 1.2 mm board would put
   0.15 mm back in range at 8:1, if the mechanicals ever allow it.
3. **Solder mask.** At a 0.325 mm opening the bridge between adjacent openings is
   0.175 mm (6.9 mil), comfortably over PCBWay's 4 mil dam; the escape trace runs
   under that bridge with 0.049 mm of mask each side. Confirm JLCPCB will hold it.
4. **Drill count.** JLCPCB surcharges above 150,000 holes/m². This board is
   0.001419 m², so the threshold is about **213 holes** — the BGA alone will pass
   it. A small fixed cost, but budget for it.
5. **0.225 mm is 0.82:1 against the package pad**, where UG475 asks for 1:1 "for
   improved board level reliability". This is the real price of the cheap route
   and it is a judgement call, not a calculation.

### Why the ball field allows any of this

Verified against the pinout file rather than assumed (`tools/escape/rings.py`,
`tools/escape/escape.py`). The grid is **19 × 19**: three complete rings, a
**three-cell empty moat**, then a 7 × 7 core with three balls missing.

    A-C / U-W rows, 1-3 / 17-19 cols   rings 0,1,2   72 + 64 + 56 = 192 balls
    D-F / P-T rows, 4-6 / 14-16 cols   rings 3,4,5   EMPTY
    G-N rows, 7-13 cols                core          46 balls, all power/ground

Ring 0 escapes outward with nothing in its way. Ring 2 escapes inward into the
moat, crossing nothing. **Only ring 1 is enclosed**, and of its 60 connected
balls, 12 are power or ground with a same-net neighbour in ring 0 or 2 and can be
ganged on L1 without a lane at all. That leaves **48 escapes for 56 lanes, 86 %**
— tight, but it is a real number and it fits.

The core is not a second instance of the problem: all 46 balls are power or
ground, and **only one, L11, cannot reach the moat through same-net orthogonal
neighbours** (diagonal ganging, which the check did not try, very likely covers
even that one).

### What does not need the fine line

Only the row crossings do. Ring 0 never crosses anything, ring 2 crosses nothing
on its way inward, and everything outside the ball field is drawn at 0.09 mm or
wider. 3 mil is a DRC floor used in one place, not a working width.

### Stage 1 is drawn: the power and ground gang

`tools/escape.py` owns this. Run it **after** `make_board.py`, which regenerates
the board with empty signals — placement is the source of truth and the escape is
derived from it, so re-running make_board throws the escape away on purpose.

    python tools/make_board.py --fab jlcpcb
    python tools/escape.py --apply

113 of the 238 balls carry a plane net. Same-net neighbours do not each need
their own escape — joined on L1 they need one between them. **73 wires at
0.225 mm take 113 balls down to 40 components.** Three kinds of edge:

| edge | span | nearest foreign land | count |
|---|---|---|---|
| orthogonal | 0.500 | 0.2750 | 68 |
| diagonal | 0.707 | **0.1286** | 3 |
| jump, over an empty grid cell | 1.000 | 0.2750 | 2 |

Only one diagonal per cell, or the two would cross.

**The jump is not a nicety.** L11 is a GND ball at the dead centre of the core
with VCC1V0 left, VCC1V0 below and VCC3V3 right, and nothing above because K11 is
one of three missing balls. Orthogonal and diagonal ganging both strand it, and a
ball at ring 8 with two populated rows around it has no other way out — no room
for a via beside it and none inside its land. Jumping the empty K11 to J11, which
is GND, is the only thing that connects it. The same jump through K10 makes
VCC1V0 a single component instead of two.

### Stage 2 is drawn: 54 escapes into the moat, and ring 1 goes outward

Ring 0 escapes outward and ring 2 inward; neither crosses anything. **Ring 1 is
the only enclosed row**, and after ganging 47 of its balls still need a lane —
40 signals and 7 power balls ganging could not reach a plane with.

**All 47 now go outward through ring 0, and none inward.** That is not what the
plan said, and the reason is a number that only appeared once the annulus was
drawn to scale.

#### The annulus has no lateral channel

| between | gap |
|---|---|
| ring-2 lands and the first via ring | **0.090 mm** |
| first and second via rings | **0.090 mm** |
| second and third via rings | **0.090 mm** |
| third via ring and the ring-6 lands | 0.605 mm |

A 3 mil trace needs 0.256 mm to run between two things. So **nothing moves
sideways in there**: a trace leaves its ball, goes straight in, and its via has
to be where the trace already is. That kills the tidy grid of via rings the plan
assumed, and with it the idea of threading deeper traces between shallower vias.

Two escapes on the ring-2 line are 0.25 mm apart at worst — a ball and the gap
beside it — and slipping a trace past a via needs **0.278 mm**. So an escape can
never pass its immediate neighbour's via. Everything lands on the outermost
depth it can, and the moat's capacity is **one escape per ball position, about
56**. 46 are spoken for by ring 2 itself (35 signals, 11 power groups) before
ring 1 gets a look in, and 8 more by the core.

Measured rather than assumed — `escape.py` was run with the inward allowance set
to 0, 4, 8, 12 and 16:

    MAX_IN=0    54 escapes   54 placed   0 unplaced    0 violations
    MAX_IN=4    58           57          1             2
    MAX_IN=8    62           61          1             4
    MAX_IN=12   66           64          2            14
    MAX_IN=16   70           64          6            14

**Zero is the only value that closes.** Ring 1 has 63 free outward gaps for its
47, and outside the package the perimeter is 36 mm, where nothing is tight.

#### What got drawn

**54 escapes, 54 vias, 127 wires on L1 in total, and the verifier is clean.**

| | |
|---|---|
| ring-2 signals | 35 |
| ring-2 power groups | 11 |
| core groups, outward from ring 6 | 8 |
| via depth from the ball it serves | 0.3525 – 0.8125 mm |

Two things the geometry forced, both of which the first three attempts got
wrong:

- **A trace crosses its side perpendicularly, not along a ray to the package
  centre.** The field is a Cartesian grid, so a homothety about the centre slides
  the crossing sideways — it put ring-1 traces 0.0326 mm from a ring-2 land where
  they needed 0.2406.
- **The four corners need to lean.** The two balls flanking a corner put their
  vias 0.209 mm apart, and going *deeper* makes it worse, because deeper at a
  corner means closer together. So an escape may leave its ball up to 50° off
  perpendicular: a ray at angle t still clears its neighbours by 0.5·cos t, which
  holds out to 61°. Nine escapes lean; the other 45 go straight in.

#### The planes still hold, checked against the real vias

`check_planes.py` now reads the via positions back out of the board rather than
guessing at a candidate grid. 54 vias, 6 GND and 48 foreign, and the copper under
the core stays connected at 0.09, 0.15 and 0.20 isolation — and still connected
with all 54 treated as foreign. The controls still island as they must.

### The decoupling is laid out in bands now, and the board no longer blocks

The blanket tile put capacitors under the ball field, through the moat, and hard
against all four edges of the package. Under the field they are useless — there
is no room for a via there, so they cannot be connected — and against the edges
they took the only space the escape had. It is five bands now, and the package
keeps a 0.99 mm belt on three sides and 2.45 mm on the left:

| band | side | what goes there |
|---|---|---|
| right, x 51.99–58.79 | back | the big one, out to JP3's hole lands |
| above, x 40.05–51.99, y 15.19–18.29 | back | between the package and X2's top holes |
| below, x 40.05–51.99, y 2.12–4.21 | back | and its bottom holes |
| left, x 39.55–41.01 | back | one column stood on end, **MR90** |
| above U1, y 15.30–18.29 | **front** | the overflow |
| above U3, x 14.60–38.36 | back | the 47 µF bulk, next to the regulator |

Two things had to change beyond the geometry. **Each size gets its own `tile()`
call**, because `tile()` sorts tallest-first inside a band to stop a 1206 setting
the height of a row of 0402s — which also means a mixed list puts the big parts
nearest the package and pushes the small ones out. Twelve 0.47 µF ended up parked
below the board that way. And the **overflow goes on the front**, above U1, which
is not a consolation prize: those are the 0.47 µF parts, the back directly under
that strip is now clear, so they via straight down beside the package instead of
running halfway across the board first.

**37 of 39 placed; C121 and C122 (0.47 µF) still have nowhere to go.**

#### What it bought

Clear board outside each edge of the package, against the 0.240 mm a via land
needs:

| edge | before | after |
|---|---|---|
| left | +0.530 | **+1.380** |
| right | **−0.629** | **+0.586** |
| below | +0.426 | **+1.660** |
| above | +0.860 | **+0.920** |

The right side used to have back-side copper reaching 0.629 mm *past* the package
edge. Every edge now clears comfortably.

### The fan-out router, and the number that stops it

`stage3()` is a real router now, not a ray search. Three things it does that the
ray search could not:

1. **One ring, not a grid.** Escapes arrive at the package edge at 0.25 mm
   spacing and a via needs 0.39. No arrangement interleaves out of that — a trace
   can never slip past the via of its immediate neighbour. The only thing that
   works is to go *out* until the perimeter is long enough: 103 vias at 0.39 need
   8h ≥ 40.2, so **h ≥ 5.03**.
2. **Isotonic via placement.** Each via wants to sit directly outboard of its own
   escape and they cannot all have that. Pushing each one forward off the last is
   the obvious fix and a bad one — the shift only accumulates, so by the far side
   the vias are a corner away from their balls. Pooling adjacent violators gives
   the least total movement and shares it out.
3. **A rectangular obstacle model.** `board_copper()` returns axis half-extents,
   not a circumscribed circle. A 1206 pad is 1.60 × 1.80, and calling that a
   radius of 1.204 throws away 0.40 mm on the axis that matters — worth two vias
   on the right-hand side.

**It still does not close, and the reason is per-side, not total.** The ball field
is lopsided: row A is nearly all ground and no-connects, row W is nearly all
signal.

| side | escapes | the placement allows | |
|---|---|---|---|
| bottom | **36** | h ≤ 5.290 → 27 vias | **short 9** |
| right | **33** | h ≤ 5.208 → 26 vias | **short 7** |
| top | 12 | h ≤ 5.400 → 27 vias | 15 spare |
| left | 22 | h ≤ 4.986 → 25 vias | 3 spare |

103 escapes against 105 places — but **the spare is on the top, and there is no
way round**. The channel between the ball lands and the via ring is 0.66 mm and
holds three traces; sixteen cannot walk round a corner in it.

#### Not every escape needs a via — 54 of 103 do

The router assumed all 103 drop to an inner layer. `tools/needvia.py` asks
instead whether each one *has* to: a ball only needs a via if it cannot reach its
destination on the top layer, and many go to X2's header, whose pins are **plated
holes** reachable from any layer, or to parts on the front.

| side | must | depends | no | of | holds | |
|---|---|---|---|---|---|---|
| bottom | **15** | 8 | 9 | 32 | 27 | fits |
| **right** | **30** | 2 | 3 | 35 | 26 | **short 4** |
| top | **3** | 6 | 2 | 11 | 27 | fits |
| left | **6** | 8 | 11 | 25 | 25 | fits |
| total | **54** | 24 | 25 | 103 | 105 | |

Ring-0 signals alone: **18 of 42 must, 10 definitely need no via at all**, and 14
depend on where the loose resistors land.

"must" is a floor, not an answer — the "depends" resolve once those resistors are
placed, and two traces that cross on L1 need a via whether or not their endpoints
did. But it settles the lower bound, and the lower bound is what decides whether
the fan-out has a chance. **Three sides of four now fit comfortably.** The bottom
was short 9 on the pessimistic count and needs 15 of its 27 places on the real
one.

#### The right-hand side, and why

30 of the right's 35 escapes must leave L1, and **17 of those 30 go to U3**.

U1 sits at x 42.00 on the front. **U3 sits at x 38.77 on the back** — to the
*left* of the FPGA. The SDRAM address bus comes out of the FPGA's right-hand
column and has to cross the whole package to reach it, so every one of those
signals changes layer immediately.

Closing the last 4 needs the right-hand half-width to go from 5.208 to **5.85**,
which means the right-hand capacitor column moving out from x 51.95 to 52.59 —
0.64 mm. To cover the "depends" as well it is 6.24, or x 52.98. That is a far
smaller change than the wholesale move that was tried and reverted, and it is
the next thing to do.

Worth asking separately whether the SDRAM bus should be on the FPGA's left-hand
balls instead. It is a schematic change and a bank-constrained one, but it would
move 17 vias from the crowded side to the empty one.

### The rest of the board is placed too, group by group

108 parts used to fall straight through to the park grid below the outline: 64
resistors, 36 capacitors, the inductors, the diodes, the transistors and the
Creative Commons artwork. Only 5 of them were ever "overflow" — the other 103
had never been given a home at all, and `make_board.py`'s summary line made that
easy to miss.

They are not interchangeable and they are not a tiling job. A series resistor
belongs at its source pin, a decoupling capacitor beside the pin it decouples,
the LTC3569's feedback divider tight to the regulator where trace length is part
of the circuit. So each one is **anchored to the device it serves**:

- the nets say it, once the power nets are set aside — those touch everything
- a part with only power nets has no signal to go on, so it falls back to the
  **schematic sheet** it was drawn on, which is how the designer grouped it

Then each group is placed as near its anchor as there is room, own side first,
in a box that grows 3 → 5 → 7.5 → 11 → 16 → 24 mm until it fits. The package
and its escape corridors are out of bounds for all of them.

**109 on the board, 59 parked** — up from 55 on the board and 113 parked.

### Three things that had to be fixed to make that safe

**`tile()` was placing parts by their silk and testing them against keepouts.**
An 0402 resistor's layer-39 box is 0.473 mm wider than its copper on every side,
so parts cleared each other's outlines and sat inside each other's keep-out
areas — 28 keepout collisions and 31 body collisions. `obst_box()` now returns
the keepout-inflated box and `tile()` uses it to size, position and avoid.
`bbox()` still ignores keepouts, deliberately: it measures how big a part *is*,
and X3's keepout is the microSD card plus 21.55 mm of eject stroke.

**The overlap assertion only checked the parts named in a table.** It was a
hand-written list — `SINGLE` plus the regulator plus `C7` plus the LEDs — so the
sixty-odd newly placed parts were not being checked at all. It is now every part
on the board.

**X1 needs the same exemption in `make_board.py` that it has in
`check_board.py`.** Its mating face sits 0.70 mm past the outline by design, and
widening the assertion caught it as the first thing off the board.

### What is still parked

59: 34 resistors, 20 capacitors, 2 diodes, 1 inductor, and the two remaining
pieces of Creative Commons artwork.

| sheet | parked |
|---|---|
| FT2232 JTAG CLK | 23 |
| Power Supplies | 15 |
| General IO | 12 |
| Memory | 9 |

The keepout-aware placement is what costs the density — a 0402 that used to
occupy 2.00 × 0.90 now claims 2.95 × 0.97, half again as much. That is the
correct number and the board is clean at it, where before it was dense and
wrong.

### Then a second pass, and the board turned out to be full

**59 parked → 44.** The FT2232 group went from 23 to 4. The Power Supplies
group did not move, and the reason is worth writing down.

#### The courtyard was being counted twice

`tile()` took the layer-39 keepout box and added 0.35 mm around it. That is
stricter than `check_board.py`, whose `shape()` unions layers 21/39/51 and asks
only that no two same-side bodies **overlap** — gap zero. The keepout already
*is* a clearance envelope.

It matters more than the 0.35 suggests, because the stock Eagle `rcl` keepout
is deliberately **anisotropic**. An 0402 carries 0.473 mm at the ends, where
the terminations and solder fillets are, and 0.033 mm at the sides, because
chip parts are meant to be packed shoulder to shoulder in rows. A uniform
0.35 mm turned that 0.033 into 0.416 mm of dead lane between every row.

The replacement is two rules, taking the wider on **each axis**:

| rule | why | 0402 half-extent |
|---|---|---|
| courtyard, `CY_GAP` 0.05 | pick-and-place and fillet envelope; abuts | 1.473 + 0.025 |
| copper, `CU_GAP` 0.30 | land to foreign land, so reflow cannot bridge | 1.000 + 0.150 |

An 0402 now claims 2.996 × 1.200 = 3.60 mm² where it claimed 6.07 — and the
result is near enough IPC-7351 density level N, which is a good sign the number
is right rather than merely smaller.

#### Reach has to grow for every group at once

Groups were placed one at a time, each run out to its full 24 mm before the
next started. So the FPGA's 31 parts reached 24 mm and took the whole board
with them, and the ten SDRAM bypass capacitors whose turn came ninth got
**zero** — nowhere within 24 mm of U3 to sit. Radius is the outer loop now:
every group gets its shot at 3 mm before any group is allowed 5. Nothing about
a capacitor 24 mm from its own device is worth the one it displaced 3 mm from
another.

A *finer* ladder is worse, not better — 11 rungs parked 38 and 15 rungs parked
37, against 35 for the original 6. Bigger steps place parts in bigger batches.

#### Two more, both small and both real

- **First fit was not first fit.** On a collision `tile()` stepped to whichever
  blocker `next()` happened to return, so a wide obstacle overlapping a narrow
  one threw the scan past the free lane between them and it never came back.
  It steps to the nearest right edge among all blockers now.
- **The generator was not reproducible.** `netparts` holds sets, Python
  randomises string hashing per process, and `Counter` ties break on insertion
  order — so the same inputs picked different anchors on different runs and the
  whole layout moved. Two runs gave 33 parked and then 35. Sorted now, ties to
  the lowest refdes; four consecutive runs produce byte-identical boards.

#### The back of the BGA, and the ring it collides with

Reserving the full `NOFPGA` box on **both** sides was costing 117 mm² of the
best decoupling real estate on the board — directly opposite the power balls,
where a bypass capacitor is supposed to go. U1's pads are layer-1 SMD; the only
copper the escape leaves on L6 is via lands.

Freeing it outright is wrong, though, and the way it failed is instructive:
`escape.py`'s `fanout_h()` looks for the largest half-width in 4.90..6.20 where
a whole ring of **through** vias still clears the board. With parts under the
package every candidate was blocked, `fanout_h` returned `None`, and stage 3
died with a `TypeError` that took the write of stages 1 and 2 with it. The
board came out unrouted.

So reserve the two things that are actually through-holes and nothing else:

| zone | half-width | what it is |
|---|---|---|
| `NOVIA` | ≤ 3.60 | the stage-2 moat |
| `RING` | 5.70 .. 6.44 | the h = 6.20 fan-out ring, plus a via land, a clearance and three search steps of margin |

That leaves a 2.10 mm band between them free. The stage-3 **traces** cross it,
but they are on L1 and these parts are on L6, so they never meet. Eleven parts
live there now — C36, C37, C123, C124, L6 and six pull-ups.

The trade, measured: full reservation 53 parked; band freed 44; whole back
freed 36 but no stage 3 at all. Stage 3 wins — without the fan-out there is no
routed board. Worth revisiting once stage 3 closes and the ring radius is
settled rather than rediscovered on every run.

### What is still parked after that

**44.** Stage 3 is unaffected: still 103 escapes onto a ring at half-width
6.200, and its 191 violations are all trace-against-trace, none of them against
a placed part.

| anchor | sheet | parked | of |
|---|---|---|---|
| U8 | Power Supplies | 17 | 23 |
| U1 | FPGA | 8 | 33 |
| X2 | General IO | 8 | 10 |
| U3 | Memory | 6 | 10 |
| U2 | FT2232 JTAG CLK | 4 | 17 |
| U10 | — | 1 | 4 |

**U8's 17 are not a packing failure — that end of the board is full.** Within
24 mm of U8 there are 151 mm² free on the back and 131 on the front, against
71 mm² of parts, and a grid search fits **zero** more 0402 in either. The free
area is entirely in strips narrower than 1.20 mm. The front-left is X3's
microSD footprint plus its card-eject keepout, 14.30 × 22.15 mm on a 20.32 mm
board; the back-left is U4, U10, U8, L1–L3, C85/C86, D1, Q2 and Q3 packed edge
to edge.

Every remaining lever trades a real margin, so they are decisions rather than
work:

1. **Low-profile parts under X3's card-eject path** (~60 mm², front left). A
   microSD sits ≈1.0–1.4 mm above the PCB and an 0402 is 0.5 mm tall, so it
   probably clears — but "probably" is not a clearance, and the card sweeps
   over it on every insertion.
2. **`CU_GAP` 0.30 → 0.20.** Still twice the 0.09 mm electrical minimum, but it
   is assembly margin being spent.
3. **Accept parts more than 24 mm from their anchor.** Cheap in area, expensive
   in review: a part placed far from its device *looks* placed, where a parked
   one is an obvious TODO.
4. **A larger outline**, if the Zulu form factor is not fixed.

### The moat is a keep-out now, and the caps moved

Eight decoupling capacitors — C90, C91, C94, C99, C103, C104, C107, C108 — had
copper inside the annulus where every stage-2 via has to land. They came from
`make_board.py`'s decoupling tile, a window that overlaps the ball field, and
nothing was wrong with that while the board had no vias.

`tile()` takes an `avoid` list now, and the moat is on it:

    MOAT = (43.11, 6.31, 49.89, 13.09)

That is the via zone — between the ring-2 and ring-6 ball centres, inset by
0.1125 land + 0.09 clearance + 0.15 via radius — grown by another 0.24 so a
capacitor clears a via land. Caps may still sit **over rings 0–2**, which carry
no vias and are a short hop from the ones just outside the package.

**Carving it out cost 46 mm², and the five capacitors that fell out were 0.47 µF
0402s** — the highest-frequency parts, the ones that must be closest. So three
other things moved:

1. **The window went to its real limits**, 40.05–58.70 × 2.12–18.20 instead of
   40.00–58.00 × 2.30–18.10. X2's header holes at y 1.27 and 19.05 with 1.52 mm
   lands bracket it, JP3's holes at x 59.55 close the right, U3 ends at 39.55.
2. **The six 47 µF 1206 bulk caps are placed first, and not under the FPGA.**
   They are 70 mm² of the 263 and gain nothing from sitting under the ball
   field. Three now sit in the belt above U3 (x 15.00–38.36, y 15.55–18.29),
   which also puts bulk next to the regulator where it belongs; three fall back
   into the bottom row of the FPGA window, clear of the field.
3. **`tile()` avoids every plated hole already placed.** It had no idea they
   existed — widening the bulk belt dropped a capacitor straight onto X1's shell
   nail. `check_board` caught it; `tile()` never would have.

All 39 capacitors are placed, nothing is in the moat, and the board checks clean.

### The plane perforation, checked before drawing stage 2

Stage 2 drops **97 vias into a 1.295 mm annulus**. Every one that is not GND
needs an antipad in the ground planes, and at 0.39 mm pitch those antipads
overlap. If they overlap the whole way round, the copper under the 7 × 7 core is
severed from the rest of L2 and L4 — a floating patch under the middle of the
FPGA, and no reference for anything on L3 that routes there. Nothing else in the
toolchain looks at a plane layer, and the failure is invisible in the copper.

`tools/check_planes.py` rasterises the plane, punches the antipads and floods
from outside the package. **It clears:**

| | |
|---|---|
| via places in the annulus | 162 at 0.39 pitch, 3 concentric rings |
| stage 2 needs | **97** — 9 GND (no antipad on L2/L4), 88 foreign |
| occupancy | **60 %**, 65 places spare |
| core copper at isolation 0.09 / 0.15 / 0.20 | connected, connected, connected |
| …treating all 97 as foreign | connected |

**And here is the cliff.** Filling the ring evenly, the core islands above
**142 of 162 places, 88 %**, at both 0.15 and 0.20 isolation. Stage 2 sits at
60 % with a 45-via margin.

The check runs two controls that **must fail** — a completely filled annulus at
0.15 and at 0.20 — and reports a finding if either comes back connected. A pass
with no failing control is not evidence.

One modelling detail worth keeping: at 0.09 isolation even a *full* annulus stays
connected, through a 0.55 mm diagonal gap between the corner vias of the outer
and second rings that a 0.48 mm antipad cannot close. That is a real channel, not
an artefact, but it is the only one at that isolation — do not rely on it.

**L5 is not checked.** It is split three ways and the split is not designed yet.
It is the harder case, because a planelet sees every via of the other two rails as
foreign as well — but it is also a different question, since a planelet only has
to reach its own vias, not stay continuous. Check it when the split exists.

**What this does not license.** 60 % is the count, not the placement. A
pathological cluster could still island a region while the total stays low, so
stage 2 must run this check against its *real* via positions, not against the
budget.

### What the checks cover now

`check_board.py` section 8 measures the drawn copper itself, and shares no code
with the generator:

- every wire against every pad and wire of a **different net**, at the board's own
  `mdWireWire`/`mdWirePad` — respecting which **side** an SMD is on, which the
  first version did not, and reported 38 shorts against back-side capacitors that
  are not there
- every wire end must land on its own net's copper, because copper that clears
  everything can still connect nothing

Mutation-tested both ways: widening one gang wire to 0.8 mm fires the clearance
check, sliding one 0.25 mm off its row fires the dangling-end check.

### What was checked and found sound

- The 238 pads match the Xilinx pinout file: none missing, none extra. "CPG236"
  names the package, not the ball count.
- The pads are `roundness="100"`, genuinely round, so the 0.2161 mm free radius
  at a 4-ball cell centre is real.
- Diagonal cell centres are **isolated points, not lanes**: two that are diagonal
  neighbours have a ball exactly halfway between them, so a 45° line through cell
  centres runs through ball centres. A trace crosses one row and must then stop
  or turn. This is why the crossing width, not the diagonal, is the constraint.

## Back-side height budget — the standoff is set by a part nobody has chosen yet

Every back-side component hangs into the gap between the board and the breadboard.
That gap is **not** a property of this design: X2 is 38 plated holes on 0.100 in
(1.016 mm drill, rows at y = 1.27 and 19.05), so the standoff is whatever pin
header gets soldered into them. Mounted the usable way — insulator on the bottom,
long pins down, short tails soldered on top — the insulator bottoms out on the
breadboard and **the standoff equals the insulator height, 2.54 mm** for a standard
0.100 in header. Mounted the other way up the standoff is zero and nothing fits.

Height above laminate = package A(max) + 0.10 mm for 1 oz copper and the reflowed
joint under the lead.

| Ref | Package | A max | +mount | Clearance | Source |
|---|---|---|---|---|---|
| **U4** | W25Q128JVSIQ SOIC-8 208 mil | **2.16** | **2.26** | **+0.28** | datasheet p69 |
| U10 | 93LC46BT SOIC-8 150 mil | 1.75 | 1.85 | +0.69 | JEDEC MS-012AA |
| C85/C140/86/93/97/98 | 47 µF 1206 | 1.60 | 1.70 | +0.84 | catalog typical, not specified |
| U3 | AS4C32M16SB TSOP-II 54 | 1.20 | 1.30 | +1.24 | datasheet p56 |
| L1–L3 | 1.5/3.3/2.2 µH 0603 | 1.00 | 1.10 | +1.44 | catalog typical, not specified |
| U8 | LTC3569 UDC QFN-20 | 0.80 | 0.90 | +1.64 | datasheet p23 |
| C0603 / C0402 | bulk / decoupling | 0.90 / 0.55 | 1.00 / 0.65 | +1.54 / +1.89 | catalog typical |

**U4 is the tallest part on the back and it clears by 0.28 mm.** No 1210 remains
anywhere in the design.

C85 used to be a 100 µF 1210 at 2.50 mm, which did not fit — it stood 0.06 mm into
the breadboard. It is now 47 µF 1206, paired with a second 47 µF 1206 at C140 in the
adjacent slot, so VCC1V0 bulk went 147 µF → 141 µF (a 4 % drop, on a rail that also
carries 2 × 4.7 µF and 4 × 0.47 µF) and the tallest thing on that rail dropped 0.90 mm.

Note which rows still say *not specified*: the six 47 µF 1206s and L1–L3 carry a value
but no MANF#, so their heights remain a purchasing decision. Everything with a
datasheet height (U4, U3, U8) clears comfortably. **The remaining height risk lives
entirely in the parts that have not been sourced yet** — fix those part numbers before
the fab order, not after. A 1206 that arrives at 1.9 mm instead of 1.6 still fits; the
point is that nothing currently forces it to.

If more back-side margin is ever needed, U4 has a WSON-8 6×5 mm option at A max
**0.80 mm** (package code P, datasheet p71) against the SOIC's 2.16 — 1.36 mm back, and
a smaller footprint, at the cost of leads you cannot see or hand-solder.

## The LTC3569 supply was repackaged — seven parts

Seven parts in the switching supply had a package that could not hold its value.
The values were all fine: the LTC3569 gives formulas rather than fixed numbers
and every one landed in range. It was the packages that were wrong, so the
packages moved and the values did not.

| Ref | Value | Was | Now | Why it had to change |
|---|---|---|---|---|
| C78 | 22 µF | 0402 | **0805** | 22 µF is not a manufacturable 0402; 0402 tops out near 10 µF. C<sub>IN</sub> on VU. |
| C80 | 22 µF | 0402 | **0805** | Same. C<sub>OUT</sub> buck 1 (VCC1V0, 1.2 A). |
| C82 | 10 µF | 0402 | **0603** | 10 µF 0402 exists only as a 4 V/6.3 V specialty part. C<sub>OUT</sub> buck 2. |
| C84 | 10 µF | 0402 | **0603** | Same, and on VCC3V3 where bias derating is worst. C<sub>OUT</sub> buck 3. |
| L1 | 1.5 µH | 0603 | **IND2520** | SW1 is the 1.2 A buck; datasheet p15 wants ≥ 1.5 × load = **1.8 A**. No 0603 reaches that. |
| L2 | 3.3 µH | 0603 | **IND2520** | SW2, 600 mA → 0.9 A needed. |
| L3 | 2.2 µH | 0603 | **IND2520** | SW3, 600 mA → 0.9 A needed. |

`IND2520` is a new footprint in `ctambe` for a 2.5 × 2.0 × 1.0 mm moulded power
inductor (Murata DFE252010P and equivalents), drawn to IPC-7351B density level B
from L 2.50 ±0.20, W 2.00 ±0.20, terminal 0.60 ±0.15 with toe 0.35 / heel 0.00 /
side 0.05 → **Z 3.40, G 1.30, X 2.30**. Silk sits in the 1.30 mm gap between the
pads so it never prints over copper. `C-GENERIC` also gained a `C0805` device
pointing at the `C0805` package `rcl` already carried.

The chosen inductors clear the requirement with margin — 1.5 µH at ~2.2 A, 2.2 µH
at ~1.8 A, 3.3 µH at ~1.5 A — and at 1.00 mm they are nowhere near the standoff.
The 0805s at 1.45 mm max are also well clear, so **U4 remains the tallest
back-side part**.

Cost: **+32 mm²** of footprint, or +43 mm² once the plan's packing factors are
applied. Back-side slack goes from +426 mm² (+21 %) to **+384 mm² (+19 %)**, and to +322 mm² (+16 %) once the header grew to 44 pins. The
power block in `tools/make_board.py` had to grow from 6.00 × 10.50 to 6.00 × 15.60
— at 3.40 mm wide only one IND2520 fits per row across a 6 mm block, so it now
runs up to the decoupling field's top edge at y = 18.10.

## Before routing

### Ground fill on L1 and L6, stitched — DONE, `tools/ground.py`

> **Poured and stitched.** Two GND polygons, one on L1 and one on L16, and **66
> stitching vias**. `python tools/ground.py --apply`, run **last of everything**
> — after both escapes, after `power.py` and after every `signals.py` group, and
> it refuses to run twice on the same board. It used to run straight after
> `escape.py`; that cost VCC1V0 its route, because stitching is a grid of
> through holes and a through hole blocks every layer. See the header of
> `tools/ground.py`.
>
> | | |
> |---|---|
> | pour outline | inset **0.40 mm** from the board edge — `mdCopperDimension` 0.30 plus half the 0.1524 outline width |
> | isolate | **0.25 mm**, deliberately wider than the 0.090 rule floor so the fill does not thread slivers between escape traces |
> | thermals / orphans / rank | yes / no / 1 |
> | stitching | **66 vias**, 0.2 mm drill on a 0.30 land, nearest neighbour **2.61–4.81 mm**, spread 25 left / 14 middle / 18 right |
> | worst clearance | **0.0920 mm** against a 0.090 rule, measured against every foreign pad |
>
> A pour in an Eagle file is **not copper** — a `<polygon>` in a `<signal>` is an
> outline plus rules, and Eagle computes the fill at ratsnest time against
> whatever else is on the board. So this does not have to be redone when the
> remaining unrouted signals are finished; the fill follows the routing.
>
> **The board is over a price step, and the stitching is no longer what does
> it.** JLCPCB surcharges above 150,000 holes/m², which on this 0.001548 m²
> board is 232 holes. The escape rings, the QFN fan-out and the routing vias
> come to 444 on their own; the 66 stitching vias take it to 510. Dropping the
> stitching would not bring it back under, so this is a consequence of the
> escape strategy rather than of the pour. Worth knowing, not worth avoiding.
>
> The via spacing is set by λ/20 in FR-4: 7.2 mm at 1 GHz, 3.6 at 2. At 2.60 mm
> minimum it is already 1.4× tighter than the fastest edge needs, and going below
> that buys nothing electrical while costing real routing room — a GND via ties
> L1/L2/L4/L6 together but it is a **hole through L3**, the signal layer, and
> **L5**, the split power layer. It does not perforate L2 or L4 at all: those are
> GND, so a GND via reinforces them rather than needing an antipad.
>
> **L5 is not poured.** It is split three ways between VCC1V0, VCC1V8 and
> VCC3V3 and that split is not designed yet — a planelet only has to reach its
> own vias, not stay continuous, which is why `check_planes.py` declines to check
> it as well.

The reasoning it was built to, kept because it is what the numbers were checked
against:

Flood the leftover space on both outer layers with GND copper and tie it down
with vias to L2 and L4. This is deliberate, not decoration, and it is easy to
forget until the board is already routed and awkward to add.

- **Pour on L1 and L6 only.** They are signal layers, not planes — the fill goes
  in the gaps between traces. L2, L4 and L5 are the actual planes and are poured
  solid regardless.
- **Stitch on roughly a 5 mm grid**, tighter to 2–3 mm around the BGA and along
  the board edge. The number that sets this is the fastest edge on the board:
  USB 2.0 Hi-Speed has a knee near 1 GHz, where λ in FR-4 is about 148 mm, so
  λ/20 is 7.4 mm. A 5 mm grid is comfortably inside that and costs about 50 vias
  on a board this size.
- **Same via geometry as the signal vias** — 0.20 mm drill, 0.40 mm pad — so the
  rules already in the `.dru` cover them.
- **Every island gets a via, or it gets deleted.** An unstitched scrap of fill is
  a floating conductor, which is worse than no fill at all. Check for orphans
  after the pour, not before.
- **Keep the fill out of the ball field.** The diagonal escape channels have
  0.159 mm of clearance each side of a 0.09 mm trace; there is no room for copper
  in there as well. Start the pour outside the 9.00 mm package outline.
- Fill also helps the back thermally, where the board faces a breadboard a
  couple of millimetres away with no airflow.

### Everything else

- `../vivado/zulu_a7_io.csv` carries per-pin **package trace delay**. The SDRAM
  bus spans 44.4 ps inside the package alone — CKE at N17 is 33.7 ps, A3 at K17
  is 78.1 — roughly 6.3 mm of FR-4. Length matching should start from those
  numbers, not from PCB copper alone.
- 64 of the 71 capacitors want to sit behind the FPGA's ball field, on the
  bottom side. See `../Zulu A7 Board Plan.html`.
- Usable area has two zones and it is worth counting them separately: where the header
  pads are, only the 16.256 mm channel between the rows is free; past the last pad there
  are no through-holes, so the full 20.32 is. That comes to 1205 mm² a side, 2409 across
  both, against 2026 mm² of placed parts — **+322 mm², about 16 % slack**, the drop
  coming from the header reaching three columns further into the board. Earlier
  revisions applied the channel to the whole length, which undercounted the board and is
  why the 2.400 in version read as break-even when it was really about +65.

## The autorouter's layer list is not the same as `<layers>`

Fusion greets the board with *Layer 2 (Route2), 3 (Route3), 4 (Route4),
5 (Route5) used but not enabled*. `check_board` has always passed "all 6 are
active in `<layers>` and can be routed on", and both were true at once: the
`<autorouter>` section was still configured for a **two-layer** board --
`PrefDir.1` and `PrefDir.16` enabled, every other layer `0` -- and `make_board`
carried it forward untouched from the original Zulu A7 via `keep("autorouter")`.

Now set explicitly, and enforced on every regeneration:

| layer | PrefDir | why |
|---|---|---|
| 1 | `*` | signal, top |
| 2 | `0` | **GND plane -- stays off** |
| 3 | `-` | signal, horizontal |
| 4 | `\|` | signal, vertical |
| 5 | `0` | **VCC3V3 plane -- stays off** |
| 16 | `*` | signal, bottom |

L3 and L4 are orthogonal because the stackup section above asks for it, and it
matters more than usual here: freeing L4 left L3 referencing L2 across 0.5495 mm
rather than a plane immediately beneath it.

**L2 and L5 stay off deliberately** and Fusion will keep naming them in that
warning, because they do carry copper. That is the message working as intended --
it reports objects on layers the router is not using. A router laying signals on
a plane layer is not what anyone wants; Eagle recomputes polygon isolation around
any new via, so a via through a pour is handled.

## Where the routing stands - 2026-08-29, after Fusion's autorouter

The board was autorouted in Fusion (variant 1, Optimize12 with TopRouter, 91.5 %
claimed). It **added** rather than replaced: +440 vias, +3158 wires, and the
existing routing including the differential pair was left alone.

| | before | after |
|---|---|---|
| vias | 428 | **868** |
| L1 | 1393 | 2018 |
| L3 | 361 | 1287 |
| L4 | 837 | 1724 |
| L16 | 667 | 1387 |

**The USB pair survived intact**: `USB_D_P` 25.86 mm on L1 and L3, `USB_D_N`
24.93 mm on L1, 0.15 mm wide, **skew 0.924 mm** -- unchanged to the micron.

107 connections remain, carried as layer-19 airwires across 50 nets, of which 57
are GND and are the pour's job rather than the router's.

`check_board` 1 finding, `validate` 0, junction audit clean. The one finding is
cosmetic: Fusion rewrote `msWidth` as `3mil`, which is 0.0762 mm exactly, and the
check compares the string.

### L1 at 94.6 % and L16 at 83.8 % are ACCEPTED -- decided 2026-08-29

> **The numbers below were restated later the same day, and the board did not
> change.** `check_planes` was counting every pad of the net as grounding the
> pour piece it sat on. That is circular: an SMD pad is copper on one layer, so
> a piece whose only anchor is such a pad ties the pad to the piece and the
> piece to the pad while nothing reaches L2/L4 -- the pair floats together and
> the check scored it as grounded. Only a via, a plated hole, or copper that
> traces to one actually reaches the planes.
>
> Correcting the rule took L16 from 89.7 % to 81.0 % and L1 from 96.2 % to
> 91.9 %. Stitching 18 vias and routing 13 stranded pads to vias brought them to
> **83.8 %** and **94.6 %**. So the 89.6 % accepted below was never a real 89 %:
> it was about 83 % measured with a rule that flattered it -- **and L1 had been
> failing the floor quietly the whole time**, which is the part worth
> remembering. The rule also hid the fault it was covering: every one of the 57
> GND pads Eagle's ratsnest called unconnected sat on a piece this check scored
> as tied.
>
> **Every figure in the table immediately below was measured under the old
> rule** and is overstated by roughly the same 6-9 points. The *argument* it
> supports survives -- the fragmentation is spread rather than concentrated, so
> there is no small fix -- but do not quote the numbers. Re-measuring the two
> hypotheticals would mean stripping copper off L16 again and has not been done.

The 95 % floor is not met on L16 and will not be. This was measured before it
was decided:

| L16 GND fill (old anchor rule -- overstated) | tied |
|---|---|
| as built | **89.6 %** |
| without all six power rails (298 of 1387 segments, 21 % of L16 copper) | 91.5 % |
| **without every non-GND trace on L16** | **98.2 %** |

Removing a fifth of the copper buys 1.9 of the 8.6 points on offer, and the ten
worst nets are worth 2.73 points between them -- the fragmentation is spread, not
concentrated, so there is no small fix. Even a bottom layer with NO signals on it
reaches only 98.2 %, because pads, vias and the outline fragment it anyway.

**So 95 % means L16 carries no routing at all**, and this board needs four
routing layers: Fusion took 2 h 47 m and 3914 rip-ups to reach 91.8 % completion
WITH L16 available, and U3 is bottom-mounted, so all 39 of its nets would need a
via at the pad just to escape upward.

What is being given up is smaller than the number suggests. **L2 and L5 are the
reference planes and both are solid** -- they are what L1/L3 and L4/L6 return
against. L16's fill is shielding and secondary return, and the strays are dropped
at CAM time rather than shipped as floating copper. The 11 stitching vias took it
from 76.6 % to 89.6 %, which is most of what was available.

`check_planes` carries both layers as entries in `ACCEPTED` -- `{"1": 0.94,
"16": 0.83}`, one point below each honest figure so a genuine regression trips
the check and ordinary noise does not. It prints the number, marks it accepted
and exits clean. That is deliberate: a check that reports a failure nobody
intends to fix is a check people stop reading. Lower the entries the moment the
board improves.

The check now credits copper that *reaches* a via, not just the via itself: it
seeds on vias and plated holes, then repeatedly grounds any of the net's own
wires **on the same layer** that touches something already grounded, to a fixed
point. Wires on different layers that merely cross are not connected -- only a
via bridges layers, and vias are already seeds. Without that, the 13 pads routed
to vias by `tools/stitch_traces.py` would score as floating, which is wrong in
the safe direction but still wrong.

**Revisit this if** the board goes somewhere EMC-sensitive, or if the bottom
layer's own traces turn out to need tighter return paths than a 90 %-connected
fill provides.

### The bottom pour, stitched as far as it goes

`tools/stitch_pour.py` finds the pieces of a pour that no via or pad reaches and
puts one via in each, as deep inside it as the geometry allows. It shares
check_planes' raster, isolation and anchor rule on purpose: a fix measured by a
different model than the check is not a fix.

| | before | after |
|---|---|---|
| L16 | 76.6 % | **89.6 %** |
| L1 | 95.9 % | **96.2 %** |

11 vias. **L16 is still under the 95 % floor and cannot be brought over it by
stitching.** Of the 59.8 mm2 still orphaned, 44.2 mm2 sits in 24 islands, and
every one of those 24 has **no via-legal cell anywhere in it** -- a via is copper
on all six layers, so an island that is wide open on L16 is still blocked by
whatever crosses above it on L1, L3 or L4. The other 15.6 mm2 is 127 slivers
under 0.60 mm2, too narrow to take a via with clearance.

Getting past 95 % means taking routing OFF L16, not adding more vias.

Two lessons in the tool itself. Its first version tried one candidate per island,
the deepest cell, and placed **nothing**: all 33 candidates were blocked,
including the middle of a 43 mm2 island with 1.65 mm of clearance to its own rim.
Offering the whole island, deepest first, found 4. Then dropping a redundant
depth filter -- `vmz` already holds a via clr + VIA_L/2 from every foreign object
on every layer, which is the real rule -- found 11.

**Fusion dropped `orphans="no"` and `rank="1"` from all four polygons** when it
re-saved the board. `orphans` defaults to no, so the behaviour is unchanged and
the strays are still discarded at CAM time rather than shipped as floating
copper -- which is why this metric is about lost ground COVERAGE, not antennas.
Re-running ground.py would put both attributes back.

### Four defects in the checkers, all exposed by a file a real CAD tool wrote

Nothing here had ever read a board that Fusion had saved. Every one of these was
silent, and every one of them flattered the board.

1. **868 vias were invisible.** These tools write
   `<via ... drill="0.2" diameter="0.3"/>`; Fusion writes
   `<via ... drill="0.2">` -- an open tag with no diameter. Every reader matched
   on `/>` or required `diameter=`, so `check_board` reported *all wires clear
   foreign copper* having tested **zero** vias, on a board whose autorouter had
   just added 440. One tolerant parser, `geom.vias()`, now serves the toolchain.
2. **Layer 19 was counted as copper.** Fusion stores unrouted connections as
   layer-19 wires inside `<signals>`. Airwires cross everything, so they read as
   **404 clearance violations at exactly 0.0000 mm** -- and made every signal
   look like it carried copper. Only layers 1-16 are copper.
3. **Through-hole pads were full size on the inner layers.** Eagle draws the
   whole pad on top and bottom and a restring annulus between; applying the drawn
   diameter to all six invented **233 clearances** against X2's DIP pads. Now
   computed from `rvPadInner` and the `rlMinPadInner`/`rlMaxPadInner` clamps.
4. **Two `TextIOWrapper`s over one stdout buffer.** A dozen tools rebind
   `sys.stdout`; importing one into another drops the first wrapper, which closes
   the shared buffer when collected and kills every later `print`. The previous
   wrapper is now kept referenced. `ground.py` already carried a note about this
   -- it had been found once and not generalised.

## Where the routing stands - 2026-08-28

| group | routed |
|---|---|
| microSD | **6 of 6** |
| USB / FT2232 | 8 of 13 |
| JTAG | 9 of 12 |
| SDRAM bus | 20 of 39 |
| X2 header | 19 of 39 |
| **total** | **62 of 109** |

```
make_board -> escape -> ground -> power -> signals microsd
           -> signals usb -> escape_qfn -> jtag -> sdram -> x2
```

`check_board` 0, `validate` 0, junction audit clean, netlist unchanged at 175
nets. 39 of 175 signals carry no copper.

### Order was chosen on what it LEAVES, not on the count

Three orders were measured on the same base:

| order | microSD | USB | JTAG | SDRAM | X2 | total |
|---|---|---|---|---|---|---|
| bus first | 0 | 13 | 6 | 22 | 23 | 64 |
| small groups mid | 0 | 13 | 8 | 27 | 17 | 65 |
| **microSD first** | **6** | 8 | **9** | 20 | 19 | 62 |

The board carries the third even though it routes two fewer nets, because the
count is not what matters when 47 nets still have to be finished by hand. The
microSD nets average **38.2 mm each** and cross the whole SDRAM footprint --
X3 is at x 4.05-15.95, U3 spans x 17.97-38.77, and the SD balls are on U1's east
side at x 43-49.5, with BTN at 18.9-21.7 in between. They are the hardest six
nets on the board. What the third order leaves behind is SDRAM and X2 nets, which
are short and sit next to their own pins.

**microSD and the FT2232 group compete directly**, which was not obvious. Routed
after USB it gets 0 of 6 even when nothing else is on the board; routed before
USB it gets 6 of 6 and USB drops to 8. It is not the SDRAM bus that blocks it.

The five USB nets given up are `USB_D_P`, `USB_D_N` -- the pair, which has to be
drawn by hand regardless -- and `FT-VCORE`, `FT-VPLL`, `FT-REF`, which are short
local connections between U2 and its own passives, not signal paths. Every UART
net, the clock and the EEPROM still route.

### Why microSD cannot simply be re-pinned

`repin.py` was re-run to check. It buys 3 %: the six nets go 229.2 mm to 222.5.
Per-side ball counts are invariant under the permutation and most of the length
is irreducible -- X3 is on the far side of U3 whichever ball is chosen. Repinning
is not the lever here; placement is.

### Why JTAG stops at 9 of 12

`FPGA-INIT#`, `FPGA-TMS` and `PROG#` remain. The FPGA-side JTAG nets sit on U1
balls at y 7.7-8.7, U1's SOUTH edge, and R4 -- the pack that joins them to the
header side -- is at y 20.5-22.1, NORTH of U1, which spans y 7.74-16.74. So each
has to travel from the bottom of the BGA around to the top. These are DEDICATED
config balls; `repin.py` deliberately cannot move them, because Vivado fixes
their site type. The ball cannot move, so R4 is what would have to. The space
directly south of U1 is U1's own decoupling field (C98, C101-C104, R12, R13),
which belongs tight to the BGA's power balls, so this is a placement decision
rather than a quick move.

## X1's footprint had its pins mirrored

**Found 2026-08-28 and fixed.** `MOLEX-105017-0001` placed pad 1 at x = -1.3 and
pad 5 at +1.3. It is now the other way round.

The drawing settles it. SD-105017-001 sheet 1, material 105017-0001, RECOMMENDED
P.C.B. PATTERN LAYOUT is a **top view** - third-angle projection, and the top
view sits above the front view sharing its left-right axis - with PIN 1 leftmost
and both PCB EDGE and CONNECTOR FRONT INTERFACE at the bottom. This footprint
puts the mouth at **+y**; its own layer-48 datum at y +4.141 lands exactly on the
board's north edge at 25.40. Mouth at +y instead of -y is a 180 degree rotation
of the drawing's view, and that rotation moves PIN 1 to +x as well. The
footprint's own note records what happened -- *Origin is the rear row centreline;
+y is the PCB EDGE and the mouth* -- the y sense was flipped and the x sense was
not, which is a mirror rather than a rotation.

What that cost, with X1 at x = 33.02:

| board x | the layout believed | physically was |
|---|---|---|
| 31.72 | pin 1 VBUS | **pin 5 GND** |
| 32.37 | pin 2 D- | **pin 4 ID** |
| 33.02 | pin 3 D+ | pin 3 D+ (centre pad, survives a mirror) |
| 33.67 | pin 4 ID, unconnected | **pin 2 D-** |
| 34.32 | pin 5 GND | **pin 1 VBUS** |

Plugging in a cable would have shorted VBUS to board GND, and the connector's
real D- contact would have sat on X1.4, which the schematic leaves unconnected.
Everything else measures correct against the drawing: 0.40 x 1.35 lands, 0.65
pitch, 2.60 span, 0.85/1.45 holes 5.00 apart, 8.20/3.50/0.50 shell geometry,
2.70 shell offset.

**X3 was checked the same way and is correct.** Hirose DM3AT-SF-PEJM5, page 3:
#1(DAT2) rightmost through #8(DAT1) leftmost with the card entering from the
bottom; the footprint has pin 1 at +3.85, pin 8 at -3.85 and its body toward -y.
The contact row verifies exactly (7.70 span, P = 1.1, 0.7 x 1.2 lands). Its
shield lands G1-G4 are still the author's dimension-chain derivation - the
footprint's own note asks for them to be verified against the Hirose pattern, and
that is still open.

## The USB pair's design rule -- net class 2, `usb-diff`

```
<class number="2" name="usb-diff" width="0.15" drill="0">
  <clearance class="2" value="0.125"/>
</class>
```

`USB_D_P` and `USB_D_N` are both in class 2, in the schematic and on the board.

**Where the numbers come from.** The pair routes on L1, which references the L2
GND plane across 0.1195 mm of prepreg 2116 RC58 at er 4.45, with 0.035 mm copper
-- the stackup table above. IPC-2141 edge-coupled microstrip over that geometry:

| w | s | Zdiff |
|---|---|---|
| 0.150 | 0.125 | **90.5** |
| 0.180 | 0.200 | 89.9 |
| 0.140 | 0.100 | 89.2 |
| 0.200 | 0.200 | 84.4 (what the router had been using) |

0.150 / 0.125 was chosen: closest to the 90 ohm USB 2.0 target while leaving
0.035 mm of margin over JLCPCB's 0.09 floor on the gap, and narrower than the
0.200 / 0.200 the router had been assuming, which computes to 84.4.

**This is a closed-form estimate, not a field solve.** er is quoted at 1 MHz and
falls to roughly 4.2-4.3 by 1 GHz, which raises Z slightly. Confirm against the
fab before ordering: JLCPCB publish an impedance calculator against their
stackups, and PCBWay said on 2026-08-27 that they build the stackup to the
impedance value and hold no standard one.

**Eagle's limitation, worth knowing.** A net class has one clearance number and
it means two things: the gap *within* the class -- which is what makes it the
differential pair gap -- and the clearance from that class to others. Here only
the class-2-to-class-2 value is set, so the pair's gap is 0.125 and its clearance
to everything else still comes from the board rule at 0.09. Raising the isolation
from other copper means adding a class-2-to-class-0 entry, which would
immediately flag the single-ended copper described below, so it is left for after
the pair is routed properly.

**Known mismatch, expected.** The two nets currently carry 0.10 mm single-ended
copper from the fallback router, which is under the class's 0.15 minimum, so
Eagle's DRC will flag a width violation on them. That copper is the thing that
gets ripped up when the pair is drawn by hand; it is not worth chasing before
then. `check_board` does not read net classes, which is why it still passes.
## The USB pair is named USB_D_P / USB_D_N -- do not change it back

Renamed from `USB_D+` / `USB_D-` on 2026-08-28. **Eagle recognises a
differential pair only from an `_P` / `_N` suffix on two otherwise identical
names.** With `+` and `-` it sees two ordinary nets: the diff-pair router will
not engage, and `MEANDER` will not length-tune them together. So the one pair on
this board that actually needs matched geometry was the one Fusion could not
help with, while it warns about the XADC analog inputs, which are sampled at
1 MSPS and do not care.

`USB_D+` is the friendlier name and it is the one the FT2232H datasheet uses for
the pin. It is also the reason this pair had no tool support for the whole of
this board's history. The naming IS the metadata in Eagle; there is nowhere else
to record that two nets are a pair.

The rename is nominal and was verified as such: 175 nets before and after, two
renamed, both pin sets identical (`USB_D_P` = U2.DP + X1.3-D+, `USB_D_N` = U2.DM
+ X1.2-D-), nothing else changed, and the routing result is unchanged at 64 of
109. `geom.find_pairs` still accepts `+`/`-`, `_p`/`_n` and `_H`/`_L` for boards
that do not follow the convention.

Before routing it in the GUI, set a differential-pair design rule for it so
Fusion's DRC checks gap and impedance as you draw.
## The USB pair is routed, with a crossover

| | |
|---|---|
| `USB_D_P` | 25.86 mm, L1 **and L3**, 2 vias |
| `USB_D_N` | 24.93 mm, L1 |
| width / gap | 0.15 / 0.125 -- net class 2 |
| **skew** | **0.924 mm** against a 1.27 budget |

```
side swap on L3, 1.40 mm at (37.61,19.39), flared to 0.40 mm
vias clear the other conductor by 0.385 mm
```

One conductor dives to L3, crosses UNDER the other and comes back up; the other
runs straight through. Two vias, on one conductor, so the pair is **not**
symmetric across the swap -- that is the cost of the reversed pinout, and why the
skew is measured rather than assumed.

**The pair flares before it swaps.** A via needs `VIA_L/2 + PAIR_W/2 + clr` =
0.315 mm from the other conductor, and the furthest a via at +h can be from a
diagonal running -h to +h is 2h -- 0.275 at the 0.125 gap. Impossible at any
crossover length, not merely tight. So the conductors taper to 0.40 mm apart for
the swap and taper back; the gap is not held across it, as in any hand-drawn one.

### Two fixes that made it land clean

**The MST legs were routed independently and the shared copper written twice.**
Routing edge (A,B) and edge (A,C) separately sends both down whatever corridor
leaves A. `UART_FT_RXD` came out **240.81 mm** on a 69.85 x 25.4 mm board -- 46 L3
segments of which the first 20 were the route and the rest the same copper again.
Each terminal now joins the NEAREST POINT ALREADY IN THE TREE, which is what a
hand router does. That net is now 33.9 mm.

**Fan-out vias were invented per (net, layer).** `place_via` works off the pad's
own side, so the position never depended on the routing layer; caching it per
layer reserved a separate via for every layer a net might use. Keyed by PAD
instead, each net has one, and a shared pool makes them mutually visible -- which
is what stopped `TDO` laying its stub 0.0744 mm from `TMS`'s via. The pool has to
stay LAZY: `fixed_for` reads the vias already decided rather than forcing a
decision for every net and layer, because the eager version reserved space for
nets that go on to fail and took microSD from 2 to 0.

### The board routes the pair OR microSD, not both

| order | pair | microSD | USB | JTAG | SDRAM | X2 | total |
|---|---|---|---|---|---|---|---|
| **USB first** (in the board) | **yes** | 1 | 13 | 9 | 23 | 11 | **57** |
| microSD first | no | 6 | 11 | 8 | 24 | 19 | 68 |

The board carries the pair. It is the only host interface, the crossover is the
hardest thing on this board to reproduce by hand, and the eleven nets given up
are ordinary routing. The microSD-first board also fails BOTH pour checks where
this one fails only L16.

## Where the routing stands - 2026-08-28

| group | routed |
|---|---|
| microSD | **6 of 6** |
| USB / FT2232 | 8 of 13 |
| JTAG | 9 of 12 |
| SDRAM bus | 20 of 39 |
| X2 header | 19 of 39 |
| **total** | **62 of 109** |

```
make_board -> escape -> ground -> power -> signals microsd
           -> signals usb -> escape_qfn -> jtag -> sdram -> x2
```

`check_board` 0, `validate` 0, junction audit clean, netlist unchanged at 175
nets. 39 of 175 signals carry no copper.

### Order was chosen on what it LEAVES, not on the count

Three orders were measured on the same base:

| order | microSD | USB | JTAG | SDRAM | X2 | total |
|---|---|---|---|---|---|---|
| bus first | 0 | 13 | 6 | 22 | 23 | 64 |
| small groups mid | 0 | 13 | 8 | 27 | 17 | 65 |
| **microSD first** | **6** | 8 | **9** | 20 | 19 | 62 |

The board carries the third even though it routes two fewer nets, because the
count is not what matters when 47 nets still have to be finished by hand. The
microSD nets average **38.2 mm each** and cross the whole SDRAM footprint --
X3 is at x 4.05-15.95, U3 spans x 17.97-38.77, and the SD balls are on U1's east
side at x 43-49.5, with BTN at 18.9-21.7 in between. They are the hardest six
nets on the board. What the third order leaves behind is SDRAM and X2 nets, which
are short and sit next to their own pins.

**microSD and the FT2232 group compete directly**, which was not obvious. Routed
after USB it gets 0 of 6 even when nothing else is on the board; routed before
USB it gets 6 of 6 and USB drops to 8. It is not the SDRAM bus that blocks it.

The five USB nets given up are `USB_D_P`, `USB_D_N` -- the pair, which has to be
drawn by hand regardless -- and `FT-VCORE`, `FT-VPLL`, `FT-REF`, which are short
local connections between U2 and its own passives, not signal paths. Every UART
net, the clock and the EEPROM still route.

### Why microSD cannot simply be re-pinned

`repin.py` was re-run to check. It buys 3 %: the six nets go 229.2 mm to 222.5.
Per-side ball counts are invariant under the permutation and most of the length
is irreducible -- X3 is on the far side of U3 whichever ball is chosen. Repinning
is not the lever here; placement is.

### Why JTAG stops at 9 of 12

`FPGA-INIT#`, `FPGA-TMS` and `PROG#` remain. The FPGA-side JTAG nets sit on U1
balls at y 7.7-8.7, U1's SOUTH edge, and R4 -- the pack that joins them to the
header side -- is at y 20.5-22.1, NORTH of U1, which spans y 7.74-16.74. So each
has to travel from the bottom of the BGA around to the top. These are DEDICATED
config balls; `repin.py` deliberately cannot move them, because Vivado fixes
their site type. The ball cannot move, so R4 is what would have to. The space
directly south of U1 is U1's own decoupling field (C98, C101-C104, R12, R13),
which belongs tight to the BGA's power balls, so this is a placement decision
rather than a quick move.

## X1's footprint had its pins mirrored

**Found 2026-08-28 and fixed.** `MOLEX-105017-0001` placed pad 1 at x = -1.3 and
pad 5 at +1.3. It is now the other way round.

The drawing settles it. SD-105017-001 sheet 1, material 105017-0001, RECOMMENDED
P.C.B. PATTERN LAYOUT is a **top view** - third-angle projection, and the top
view sits above the front view sharing its left-right axis - with PIN 1 leftmost
and both PCB EDGE and CONNECTOR FRONT INTERFACE at the bottom. This footprint
puts the mouth at **+y**; its own layer-48 datum at y +4.141 lands exactly on the
board's north edge at 25.40. Mouth at +y instead of -y is a 180 degree rotation
of the drawing's view, and that rotation moves PIN 1 to +x as well. The
footprint's own note records what happened -- *Origin is the rear row centreline;
+y is the PCB EDGE and the mouth* -- the y sense was flipped and the x sense was
not, which is a mirror rather than a rotation.

What that cost, with X1 at x = 33.02:

| board x | the layout believed | physically was |
|---|---|---|
| 31.72 | pin 1 VBUS | **pin 5 GND** |
| 32.37 | pin 2 D- | **pin 4 ID** |
| 33.02 | pin 3 D+ | pin 3 D+ (centre pad, survives a mirror) |
| 33.67 | pin 4 ID, unconnected | **pin 2 D-** |
| 34.32 | pin 5 GND | **pin 1 VBUS** |

Plugging in a cable would have shorted VBUS to board GND, and the connector's
real D- contact would have sat on X1.4, which the schematic leaves unconnected.
Everything else measures correct against the drawing: 0.40 x 1.35 lands, 0.65
pitch, 2.60 span, 0.85/1.45 holes 5.00 apart, 8.20/3.50/0.50 shell geometry,
2.70 shell offset.

**X3 was checked the same way and is correct.** Hirose DM3AT-SF-PEJM5, page 3:
#1(DAT2) rightmost through #8(DAT1) leftmost with the card entering from the
bottom; the footprint has pin 1 at +3.85, pin 8 at -3.85 and its body toward -y.
The contact row verifies exactly (7.70 span, P = 1.1, 0.7 x 1.2 lands). Its
shield lands G1-G4 are still the author's dimension-chain derivation - the
footprint's own note asks for them to be verified against the Hirose pattern, and
that is still open.

## The USB pair's design rule -- net class 2, `usb-diff`

```
<class number="2" name="usb-diff" width="0.15" drill="0">
  <clearance class="2" value="0.125"/>
</class>
```

`USB_D_P` and `USB_D_N` are both in class 2, in the schematic and on the board.

**Where the numbers come from.** The pair routes on L1, which references the L2
GND plane across 0.1195 mm of prepreg 2116 RC58 at er 4.45, with 0.035 mm copper
-- the stackup table above. IPC-2141 edge-coupled microstrip over that geometry:

| w | s | Zdiff |
|---|---|---|
| 0.150 | 0.125 | **90.5** |
| 0.180 | 0.200 | 89.9 |
| 0.140 | 0.100 | 89.2 |
| 0.200 | 0.200 | 84.4 (what the router had been using) |

0.150 / 0.125 was chosen: closest to the 90 ohm USB 2.0 target while leaving
0.035 mm of margin over JLCPCB's 0.09 floor on the gap, and narrower than the
0.200 / 0.200 the router had been assuming, which computes to 84.4.

**This is a closed-form estimate, not a field solve.** er is quoted at 1 MHz and
falls to roughly 4.2-4.3 by 1 GHz, which raises Z slightly. Confirm against the
fab before ordering: JLCPCB publish an impedance calculator against their
stackups, and PCBWay said on 2026-08-27 that they build the stackup to the
impedance value and hold no standard one.

**Eagle's limitation, worth knowing.** A net class has one clearance number and
it means two things: the gap *within* the class -- which is what makes it the
differential pair gap -- and the clearance from that class to others. Here only
the class-2-to-class-2 value is set, so the pair's gap is 0.125 and its clearance
to everything else still comes from the board rule at 0.09. Raising the isolation
from other copper means adding a class-2-to-class-0 entry, which would
immediately flag the single-ended copper described below, so it is left for after
the pair is routed properly.

**Known mismatch, expected.** The two nets currently carry 0.10 mm single-ended
copper from the fallback router, which is under the class's 0.15 minimum, so
Eagle's DRC will flag a width violation on them. That copper is the thing that
gets ripped up when the pair is drawn by hand; it is not worth chasing before
then. `check_board` does not read net classes, which is why it still passes.
## The USB pair is named USB_D_P / USB_D_N -- do not change it back

Renamed from `USB_D+` / `USB_D-` on 2026-08-28. **Eagle recognises a
differential pair only from an `_P` / `_N` suffix on two otherwise identical
names.** With `+` and `-` it sees two ordinary nets: the diff-pair router will
not engage, and `MEANDER` will not length-tune them together. So the one pair on
this board that actually needs matched geometry was the one Fusion could not
help with, while it warns about the XADC analog inputs, which are sampled at
1 MSPS and do not care.

`USB_D+` is the friendlier name and it is the one the FT2232H datasheet uses for
the pin. It is also the reason this pair had no tool support for the whole of
this board's history. The naming IS the metadata in Eagle; there is nowhere else
to record that two nets are a pair.

The rename is nominal and was verified as such: 175 nets before and after, two
renamed, both pin sets identical (`USB_D_P` = U2.DP + X1.3-D+, `USB_D_N` = U2.DM
+ X1.2-D-), nothing else changed, and the routing result is unchanged at 64 of
109. `geom.find_pairs` still accepts `+`/`-`, `_p`/`_n` and `_H`/`_L` for boards
that do not follow the convention.

Before routing it in the GUI, set a differential-pair design rule for it so
Fusion's DRC checks gap and impedance as you draw.
## The USB pair routes -- with a crossover -- but not yet on a clean board

`route_pair` can now build the side swap the reversed pinout needs, and the
result is measured, not asserted:

```
USB_D_P/USB_D_N: side swap on L3, 1.40 mm at (37.61,19.39), flared to 0.40 mm
                 vias clear the other conductor by 0.385 mm
                 chose L1, 25.4 / 25.4 mm, skew 0.924 (budget 1.27) OK
```

On the board that produces: `USB_D_P` 25.86 mm across layers 1 **and 3** with two
vias, `USB_D_N` 24.93 mm on L1, both 0.15 mm wide, gap 0.125 -- the net class 2
geometry -- and **0.924 mm of skew inside the 1.27 budget**.

### What the crossover is

One conductor dives to another layer, crosses UNDER the other, and comes back up;
the other runs straight through. Two vias, on one conductor only, so the pair is
NOT symmetric across the swap -- that asymmetry is the cost of the reversal and
is why the skew is measured afterwards rather than assumed.

**The pair flares first.** A via needs `VIA_L/2 + PAIR_W/2 + clr` = 0.315 mm from
the other conductor, and the furthest a via at +h can ever be from a diagonal
running -h to +h is 2h, which at the 0.125 mm gap is 0.275. Not marginal:
impossible at any crossover length. So the conductors taper apart to 0.40 mm for
the swap and taper back. The gap is not held across it, which is true of every
hand-drawn crossover as well.

### Why it is not in the board yet

A full run with the crossover reaches USB 13 of 13, microSD 2, JTAG 9, SDRAM 25,
X2 15 = 64, `validate` clean, junction audit clean, and **both pours passing for
the first time** (L1 96.6 %, L16 95.6 % against the 95 % floor). Two things stop
it being committed:

1. **One clearance violation**: `TDO` wire vs `TMS` via, 0.0744 mm against 0.0900.
   Same family as the others -- `terms_for` places each net's fan-out vias
   without seeing the ones other nets place in the same run. Deciding them all up
   front fixes it and costs more than it saves: it reserves a via for every
   (net, layer) pair including layers the net never uses, and USB fell 13 to 11
   and microSD 2 to 1. The fix wants to be lazy, not eager.
2. **`UART_FT_RXD` comes out 240.81 mm** on a 69.85 x 25.4 mm board. Not a DRC
   violation and not acceptable either; it eats routing resource that the SDRAM
   and X2 numbers then swing on.

The board in the repository is the previous one -- microSD 6 of 6, no pair. The
pair work is in the toolchain and reproducible; it is the surrounding FT2232
routing that is not ready.

## The USB pair still does not route as a pair

Fixing the footprint did **not** free the pair, and the reason I expected it to
was wrong. Measured against a clean base, layer by layer:

| layer | outcome |
|---|---|
| L1 | routes 27.60 / 29.27 mm, gap 0.20, **skew 1.670** (budget 1.27), then fails clearance |
| L3, L16 | no 0.60 mm corridor exists |
| L4 | no room for a fan-out via at (32.31, 8.62), inside U2's pad field |

On L1 the failure is `USB_D_N` running **0.054 mm from the `USB_D_P` pad edge**
where 0.090 is required. With the footprint corrected the pad order genuinely
reverses - D- is west of D+ at U2 and east of it at X1 - so the D- conductor has
to get past the D+ pad, and at 0.5 mm pitch with 0.20 mm conductors it cannot.
Narrowing to 0.10 mm would clear it geometrically, would not be a 90 ohm pair on
this stack, and would still leave 1.670 mm of skew.

So both nets route single-ended: `USB_D_P` 62.0 mm, `USB_D_N` 25.8 mm, 36.2 mm of
skew. Connected, DRC-clean, and not a working USB 2.0 high-speed link. It needs a
deliberate crossover, or X1 and U2 placed so the pair never has to reverse.

### Still open

1. **The USB pair**, above - the board's most important unfinished item.
2. **microSD is 0 of 6**, and 6 of 6 against a clear board. Measured before X2 as
   well as after and it is 0 either way: USB and SDRAM own the corridors running
   west from U1's escape towards X3.
3. **The L16 pour is 90.2 % connected against a 95 % floor.**
4. X3's shield lands G1-G4, unverified against the Hirose pattern.
5. The anchor tie-break still resolves alphabetically; R2, R4, R93 and R94 lose
   to U1 the way R34 and R35 did.
6. The SPI flash path (`FLASH-*`, `FPGA-CCLK`) is not grouped or routed.
