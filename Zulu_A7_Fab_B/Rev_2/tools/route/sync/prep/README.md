# Fab B Rev 2 <- no_pmod Rev 2: board transplant prep (2026-11-20)

Prep for applying, to TARGET (`Zulu_A7_Fab_B/Rev_2`, `zulu_a7_fab_b.PcbDoc` md5 33023787), the board changes made on
SOURCE (`Zulu_A7_no_pmod/Rev_2`, `Zulu_a7_no_pmod.PcbDoc` at 427960e, md5 9b0341ba) since 22ee1dc, keeping TARGET's
Pmod (J1, R26-R33, the JA/PMOD nets) and its east-end JTAG (JP3/JP4). Nothing here touches a PcbDoc. The plan built
on this prep (`tools/route/sync/final_plan.json`) was applied and committed with the no-PMOD sync on 2026-11-20.

All models use TARGET's route-model format (`tools/route_model.py`: board-relative mm, y up, Altium layer names;
`board / planes / pads / tracks / vias`). TARGET and SOURCE share one coordinate frame: 705 pads of unmoved parts are
identical between the two models; the only differences are 0.1 um KiCad rounding (18.1499 against 18.15).

Rebuild everything: `sh scripts/run_all.sh` (about 9 minutes; KiCad 10 python only for the models, at most 2 python
processes at once).

## Result in one paragraph

Every applicable SOURCE copper change fits TARGET except in the Pmod zone east of U1 (x 49.6-60.5), where
SOURCE re-routed nets through the space that its Pmod removal freed. The clean transplant removes 897 tracks and 362 vias, then adds
1489 tracks and 354 vias. It is emit-ready: every removal hits exactly one base_cur object by emit_copper's rule and by
emit_delta's exact 0.1 um key on TARGET's native Altium coordinates. route_check passes with 0 violations, the
full-board exact DRC finds 0 new violations against base_cur, no through via lands in any SMD pad, there is 0 dead
copper and 0 width violations. It leaves **10 open connections on 10 nets**: CHAN2, CHAN5, CHAN9, CLK-12M-FPGA,
FLASH-D02, FPGA-INIT#, FPGA-TMS, GND (U1-L19), PROG# and UART_FT_TXD. Every SDRAM-Dn / Dn net and the whole DQ
series-resistor change came over complete. The drops did not cut any of them. The USB pair is SOURCE's exactly: Top only, 0.15 mm, no
vias, P = N = 12.1863 mm. If the JA copper is ripped (`rip_ja.json`), only FLASH-D02 and PROG# stay open among the
transplanted nets, and the 8 JA nets become the routing job instead.

## Files

| file | what |
|---|---|
| `models/tgt_33023787.json` | TARGET now, from `tools/route_model.py` (863 pads, 4917 tracks, 1961 vias) |
| `models/src_<commit>.json` | SOURCE at 22ee1dc, 51ffba0, 06d9f27, 04819de, 3b1817d, 3e4ee8c, 427960e (SOURCE's route_model.py, frame 30.48; the PcbDocs are the inventory copies in scratchpad `sync/board/pcb`) |
| `base_cur.json` | **(a)** TARGET now (= `models/tgt_33023787.json`): 863 pads, 4917 tracks, 1961 vias |
| `base_new.json` | **(b)** TARGET after the ECO + placement, before any copper change: 896 pads (-106 +139), copper = base_cur |
| `base_new_check.json` | the per-part proof for base_new (moves, swaps, U3 nets, netlist comparison) |
| `placement.json` | the 27 parts as SOURCE HEAD places them (x, y, rot, side, footprint) next to TARGET now; this is the placement the Altium step must reproduce |
| `delta.json` | SOURCE 22ee1dc -> HEAD in route-model terms: 1236 removed and 2095 added objects, each with its commit and feature and with `target_hits` (emit-rule matches on TARGET) |
| `transplant.json` | **(c)** the emit-ready plan (clean mode): remove 897 tracks + 362 vias, add 1489 tracks + 354 vias, `moves: []`, `_meta` |
| `dropped.json` | everything left out of `transplant.json`, with its reason (and, for conflicts, the TARGET object it hits) |
| `transplant_log.json` | in-pad via replacement, prune passes, TARGET objects pruned, trimmed tracks, duplicate placed once, removals by reason |
| `after_transplant.json` | **(d)** base_new - removals + additions (5509 tracks, 1953 vias, 896 pads) |
| `model.json` | **router input** = `after_transplant.json` (the 10 opens) |
| `check.json` | every check of the clean variant (see Checks below), with `open_islands` (pads, track/via counts, bbox and planar gap per island) |
| `opens.json` | `open_islands` of all four variants |
| `summary.json` | the numbers of all four variants |
| `rip_ja.json` | **rip option**: every JA1..JA10 track (99) and via (58) on TARGET (U1 east balls -> R26..R33), in `{remove, remove_vias}` form; it is disjoint from the transplant removals, so it can be appended to them |
| `transplant_ripja.json`, `after_transplant_ripja.json`, `dropped_ripja.json`, `check_ripja.json`, ... | the same transplant built with the JA rip first, so the SOURCE copper that only clashed with JA copper comes in too |
| `transplant_stubs.json`, `after_transplant_stubs.json`, ... (`_stubs`, `_stubs_ripja`) | **stubs** mode: only floating fragments are pruned; dead-ended copper that hangs off a pad island is kept as a partial route for the router (compose_plan prunes what stays unused) |
| `route_check_official*.txt`, `prune_after*.txt`, `route_conn_after*.txt`, `widthcheck*.txt`, `native_keys*.txt` | TARGET's own CLIs run on each variant |
| `extra_classes.json` | `{SDRAM_DATA: [SDRAM-D0..15]}` for `widthcheck.py` (needed while TARGET's PcbDoc had no SDRAM-Dn nets; since the 2026-11-20 sync they are in SDRAM_DATA) |
| `log_*.txt`, `run_all.log` | the build logs |
| `scripts/` | `common.py` (keys, multiset diff), `geo.py` (exact checks: TARGET's router/route_conn/judge with SDRAM-D0..15 added to the SDRAM rule set), `build_base.py`, `delta.py`, `build_transplant.py`, `apply_check.py`, `native_keys.py`, `summarize.py`, `run_all.sh` |

## (b) base_new

- Swapped to SOURCE HEAD footprints at SOURCE positions, with every pad checked equal to SOURCE HEAD:
  - U2: FT2232HL-LQFP64 at (31.475, 13.6) becomes FT2232HQ-QFN64 at (30.5, 14.55), Top. 64 pads become 65, and the new
    EP pad is 4.2 x 4.2 on GND.
  - X4: JST-B2B at (29.86, 5.3) becomes JST-S2B-PH-SM4-TB at (31.39, 4.9), Top, with pads 1, 2, MP1 and MP2.
  - U10: SPI-8_SOIC_150 at (20.985, 18.645) becomes MSOP-8_3X3_P0.65 at (23.485, 20.245), Bottom.
  - The pin/net map is unchanged apart from U2-EP = GND.
- Moved rigidly, with the same footprint and nets (TARGET pads == SOURCE 22ee1dc pads, proven per pad):
  - U4: +0.40 N
  - R34: +0.40 E
  - C87, C88, C94, C99, C106: -0.20 S
  - R1: +0.30 N
- Added: R119-R134 (R0201) at SOURCE positions. R127 and R129-R132 are on Top; the others are on Bottom. Each pad 1 is SDRAM-Dn and each pad 2 is Dn.
- U3 DQ pads 2, 4, 5, 7, 8, 10, 11, 13, 42, 44, 45, 47, 48, 50, 51 and 53 change from Dn to SDRAM-Dn. TARGET's geometry is
  kept (it equals SOURCE's).
- Every other pad is TARGET's, including the U1 JA balls, J1, R26-R33, JP3/JP4, R5/R24/R25/R90/R92/R93/R99 and
  C78/R108 (SOURCE moved those in its Pmod work, so the moves do not come over).
- Every pad net equals the simulated Fab B netlist after the schematic change (scratchpad
  `sync/schematics/net_sim_r.txt`): **0 mismatches** and 0 netlist pins without a pad. The only exceptions are
  single-pin `N$` nets (no net on the board) and NetL3_1, which is Altium's name for N$L3-1.
- base_new on its own has 78 open connections (the new and moved pads are not wired yet).

## (c) transplant: rules and counts

1. All of 04819de is skipped: 8 removals and 12 additions (R108 move, C78/R24/R4-TCK vias-out-of-pad).
2. Removals are SOURCE's removals that exist on TARGET: 1162 objects (3b1817d 978, 3e4ee8c 107, 06d9f27 74,
   427960e 3). Each carries TARGET's own coordinates. The 66 SOURCE removals with no TARGET counterpart are listed in
   `dropped.json` as "SOURCE-only object". They are SOURCE's 22ee1dc-era PROG#/TMS/TDI pieces.
3. **No through via in any SMD pad.** TARGET's two GND through vias that the new footprints put inside pads are removed
   (`remove_vias`) and replaced at the same point:
   - (32.35, 16.575) sits inside U2-EP and also ties U3-46 on Bottom through a 0.45 mm Bottom track. It becomes a full
     microvia column: Top>L2, L2>L3, L3-L4 buried 0.27, L4>L5 and L5>Bottom.
   - (32.475, 9.025) sits inside X4-2. It becomes Top>L2.
   - All lasers are 0.30/0.15. Each replacement sits exactly where the through via was, so every land and hole only
     shrinks.
   - SOURCE HEAD still has both of these as through vias; nothing else on SOURCE HEAD is a through via in a pad.
4. An addition is left out when it clashes with TARGET copper or a TARGET pad that stays (clearance with the SDRAM
   rules, hole-to-hole 0.24 mm, board edge, width). All 69 such additions are in the Pmod zone. The nets they clash
   with:
   - JA4: CHAN2, CHAN5, CHAN9, GND (U1-L19)
   - JA8/JA10: CLK-12M-FPGA
   - JA1/2/4/8/9/10, CLK-12M-FPGA and CLK-12M-SHARED: FLASH-D02
   - JA8/JA9: FPGA-INIT#
   - JA2/JA9/JA10: FPGA-TMS
   - JA2/3/8/9, CLK-12M-FT, FPGA-TCK, LED0_R and TDO (TARGET's east-end R24/R5/JP3 area): PROG#
   - JA1/2/3/8/9/10: UART_FT_TXD
5. An addition that touches SOURCE-only copper (SOURCE HEAD copper that is neither on TARGET nor transplanted) is left
   out: 3 TMS/TDI JTAG-trunk pieces of 06d9f27/3b1817d and 2 in the Pmod zone (CLK-12M-FPGA, PROG#).
6. Clean mode: dead copper is pruned to a fixpoint with `prune_stubs.analyse`, the compose_plan way.
   - 173 additions become dead and are left out: 158 in the zone, 14 at x 47.9-49.6 and 1 TMS piece.
   - 95 TARGET objects become dead and are added to the removals: CHAN9 41, FLASH-D02 21, CHAN5 10, FPGA-TMS 10,
     PROG# 8, FPGA-INIT# 3, CLK-12M-FPGA 1 and CHAN2 1.
   - 2 tracks are trimmed and become remove + a shorter track.
7. One exact duplicate in SOURCE HEAD (TDI L3 jog (27.625, 6.8)-(27.625, 6.825), present twice) is placed once.
8. Additions by feature:
   - hq_s2b_msop (U2/X4/U10 + re-routes): 1584
   - dq_series_r: 128
   - body_u4: 79
   - body_r34: 18
   - body_c_row: 10
   - body_r1: 9
   - u4_via: 7
   - in-pad replacement: 6
   - trimmed: 2
9. Vias:
   - Added: Top-L2 92, L2-L3 70, L3-L4 buried 60, L4-L5 51, L5-Bottom 57, through 24 (none in an SMD pad).
   - Removed: Top-L2 84, L2-L3 80, buried 73, L4-L5 36, L5-Bottom 40, through 49.

| variant | remove t/v | add t/v | opens | dead copper left | dropped additions |
|---|---|---|---|---|---|
| clean (`transplant.json`) | 897 / 362 | 1489 / 354 | 10 | 0 | 69 conflict + 173 dead + 5 SOURCE-only + 12 (04819de) |
| stubs | 829 / 335 | 1583 / 377 | 10 | 174 t + 53 v (partial routes) | 69 conflict + 54 floating + 5 + 12 |
| ripja (with `rip_ja.json`) | 948 / 400 | 1613 / 383 | 10 | 0 | 7 conflict + 78 dead + 8 + 12 |
| stubs_ripja | 928 / 393 | 1673 / 396 | 10 | 81 t + 20 v | 7 conflict + 5 floating + 7 + 12 |

A third mode, `restore`, was also tried: it put back TARGET objects that SOURCE removed on the open nets wherever
they clash with nothing. It closed 0 of the 10 opens and brought back TARGET's GND through via in the moved U4-4 pad, so
it was dropped.

## (d) checks (identical result for all four variants unless noted)

- **Emit-readiness.** `judge.emit_match` finds 0 problems on both base_cur and base_new: every remove line hits
  exactly one object and the Kill counts equal the list lengths. `native_keys.py` gives 0 misses and 0 duplicate keys
  for every removal against TARGET's native Altium coordinates with SOURCE's `emit_delta.py` exact 0.1 um keys. This
  holds for `rip_ja.json` too.
- **route_check.py** with the plan against base_new passes with 0 violations. It was run both in-process with
  SDRAM-D0..15 in the SDRAM rules and with TARGET's unpatched CLI (`route_check_official*.txt`). One caveat:
  route_check's via removal ignores the span, so its model also drops 4 stack members that stay (N$LD1A at
  (33.3, 16.1) and (27.9, 13.5), CHAN5 at (49.1, 18.95), CHAN2 at (53.4, 22.15)) and does not check new copper against
  them. The full DRC below covers them.
- **Full-board exact DRC** (judge.drc: pads, tracks, vias, holes, edge) of after_transplant against base_cur: 0 new
  violations. base_cur shows 37 and the result 34; these are model artefacts that already exist on the DRC-clean
  board. This also covers moved and new pads against copper that stays, which route_check never checks.
- **Through via in an SMD pad**: 0. Microvias in SMD pads that are new: 66 in clean mode (allowed).
- **prune_stubs**: 0 dead in clean and ripja. Stubs gives 174 tracks + 53 vias and stubs_ripja 81 + 20, kept on
  purpose.
- **widthcheck.py** with TARGET's PcbDoc rules + `extra_classes.json` gives 0 violations in every variant, and 0
  against SOURCE HEAD's rules too.
- after_transplant equals SOURCE HEAD copper for x 3.8-47.5 except:
  - the 6 replacement microvias;
  - SOURCE-only copper: the west-column JTAG trunks (TMS 103, TDI 56, TCK 33, TDO 21), the 04819de VU/GND pieces, and
    CHAN9's west part, which clean mode prunes and stubs mode keeps.

### Open connections (route_conn)

Clean / `model.json` has 10 opens. The gap is the planar distance between the two islands (stubs gap in brackets).

| net | islands | gap mm (stubs) | where |
|---|---|---|---|
| CHAN2 | X2-5 (49.5-53.4, 22.2-24.1) / U1-B17 | 6.45 (0.82) | zone south-east of U1 to the X2 east row |
| CHAN5 | X2-8 (41.9-50.0, 19-24) / U1-D17 bare | 3.87 (1.16) | U1 east edge to X2 |
| CHAN9 | X2-12 bare / U1-J17 bare | 29.8 (stubs: TARGET's route back to (49.93, 12.48) L2-L3, only the U1-J17 Top escape is missing) | U1-J17 escape (JA4 Top track at 0.037 mm) |
| CLK-12M-FPGA | U1-L17 (49.5-50.7, 10.2-11.6) / R25-2 (56.7-61.4, 5.7-12.9) | 5.97 (3.34) | Pmod zone, through the JA8/JA10 fan-out |
| FLASH-D02 | U1-G18 bare / R2-1 + U4-3 (43.9-55.5, 18.7-22.5) | 6.19 (5.98) | U1 G18 to the U4 flash, north-east of U1 |
| FPGA-INIT# | U1-U11 (46.9-47.9, 8.4-9.6) / R1-1 (57.8, 4.6-4.9) | 10.4 (2.23) | Pmod zone south, through JA8/JA9 |
| FPGA-TMS | U1-W9 (45.9-50.0, 4.3-8.2) / R4-12 (56.4-58.5, 14.5-18.6) | 10.0 (1.80) | Pmod zone, across JA2/JA9/JA10 |
| GND | plane / U1-L19 (50.9, 11.4) bare | 0.21 | one plane tie at U1-L19 (Top>L2 microvia); SOURCE's two Top>L2 vias hit JA4 Top tracks |
| PROG# | R4-1 + R99-1 (60.2-61.1, 15.4-19.9) / U2-21 (23.0-49.5, 2.0-10.1) | 16.3 (11.1) | "PROG# split": closest U2-side point (49.5, 2.28) L3-L4; the R4/R99 side is at the east end |
| UART_FT_TXD | U1-K17 (48.9-49.9, 11.0-12.1) / U2-38 (34.9-50.3, 1.6-13.3) | 6.52 (4.48) | east end: U2 side reaches (50.25, 4.28), U1-K17 escape at (48.85, 10.95) |

With `rip_ja.json` (ripja), 10 opens:
- FLASH-D02, gap 5.98 (2.23 with stubs)
- PROG#, gap 16.3 (8.06 with stubs)
- JA1, JA2, JA3, JA4, JA7, JA8, JA9, JA10: bare U1 east ball to R26..R33, gaps 7.6-14.4 mm. U1 balls are at
  x 49.9-50.9, y 7.4-9.4 and C17 at (49.9, 15.4); R26-R33 are at x 58.75-63.45, y 5.65-14.17.

The ripja transplant brings in SOURCE's complete routes for CHAN2, CHAN5, CHAN9, CLK-12M-FPGA, FPGA-INIT#, FPGA-TMS,
GND U1-L19 and UART_FT_TXD. Only 7 additions still clash with TARGET's east-end parts:
- PROG# against CLK-12M-FT, FPGA-TCK, LED0_R and TDO
- FLASH-D02 against CLK-12M-FPGA and CLK-12M-SHARED

## (e) USB pair (USB_D_P / USB_D_N) in after_transplant

| check | result |
|---|---|
| match with SOURCE HEAD | all 34 tracks identical |
| layer | Top only |
| width | 0.15 mm |
| vias | 0 |
| path | U2-8/U2-7 (26.075, 14.8 / 15.3) to X1-3/X1-2 (30.48 / 31.13, 21.26) |
| length | P = N = 12.1863 mm, mismatch 0.0000 mm (N carries a 3-bump serpentine at x 25.1-25.3, y 15.65-18.15) |
| coupling at 0.30 mm pitch | 9.15 mm at +-0.005, 9.55 mm at +-0.01, 10.39 mm at +-0.03 (75-85 %); the uncoupled parts are the serpentine and the pad fan-outs |
| minimum edge gap | 0.15 mm |
| clearance to other nets | 0 new DRC violations |
| for comparison: TARGET now | 15.92 mm, mismatch 0.0002 mm |

## What the routing strategies need

- **Start model**: `model.json` (clean, 10 opens). The alternative is `after_transplant_stubs.json`: the same 10 opens
  but much shorter gaps (CHAN9's whole route stays). If the JA fan-out is to be re-routed, use
  `after_transplant_ripja.json` or `_stubs_ripja`.
- **route_check base**: `base_new.json`. The plan to compose is the transplant's `remove` / `remove_vias` plus its
  `tracks` / `vias`, plus the router's plan (or `rip_ja.json` appended to the removals for the JA option). Judge against
  base_cur with `scripts/apply_check.py <plan> <tag>`, which runs emit-match, route_check, prune, route_conn, the
  full DRC, the via-in-pad audit and USB.
- **TARGET's router.py lacks SDRAM-D0..15 in its SDRAM set.** Without it, SDRAM-Dn copper gets 0.09 mm clearance and
  0.0762 mm width on L3/L4/Bottom instead of 0.10 / 0.10. Port SOURCE's lines 49-52. Also port SOURCE's
  through-via-in-SMD-pad mask (`_through_in_pad_mask`, the user rule) and its router-via hole-to-hole block. SOURCE's
  `prune_stubs.py` trim snap is a further useful fix. `geo.py` patches the SDRAM set for every check here.
- **widthcheck** needed `extra_classes.json` until SyncRules put the SDRAM-Dn nets in SDRAM_DATA (done 2026-11-20).
- **Emitting**: about 900 removals is too many for `emit_copper.py`'s per-line matching. Port SOURCE's table-driven
  `tools/emit_delta.py` with TARGET's path guard (zulu_a7_fab_b.PcbDoc). Its exact keys already match TARGET's native
  coordinates. Then run `mark_microvias.py` after the save.
- **Order on the board**: first the ECO (schematic sync: U2 FT2232HQ-QFN64 + EP, X4 S2B, U10 MSOP-8, R119-R134, U3
  DQ nets), then the placement in `placement.json`, then the transplant + routing plan. The removals are TARGET copper
  that the ECO does not delete.
- **SOURCE-only nets that do not come over**: the west JTAG column trunks (TMS/TDI/TCK/TDO), the 04819de C78/R108/R24
  vias-out-of-pad and the R108 move. TARGET keeps its own east JTAG routing.
- **Model caveats**:
  - rotated or rounded pads are bounding boxes (conservative);
  - U1 lands are round (route_conn ROUND);
  - planes are taken as full pours, so the plane web is not checked here (`route/rev2/judge/planeweb.py` does that);
  - 3D-body clearance is not checked here; the release body gate does that.
