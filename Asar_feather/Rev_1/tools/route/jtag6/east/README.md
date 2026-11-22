# JTAG test points in one 2x3 block at JP3's site (Asar A7 Feather, board 9be75ad9, strategy "east")

## Problem
The owner wants the six JTAG test points next to each other. They are two TP-1X03-SMD parts on the Bottom, with 1.0 mm round pads at a 1.27 mm pitch:
* JP3 (TCK, TMS, GND) sits at x 17.75, y 5.05..7.59, beside U2.
* JP4 (TDI, TDO, VCC3V3) sits at x 4.85..7.39, y 3.15, against X2's south housing. That is 11 mm away from JP3.

This strategy keeps the cluster at JP3's site. JP4 joins JP3 there.

**A line of six does not fit here. This is why:**
* **Vertical line at x 17.75.** Six pads need 5 x 1.27 + 1.0 = 7.35 mm. L5's pads end at y 4.08 and C85-1/C86-1 start at y 9.10, which leaves 5.02 mm (4.62 mm with the 0.10 mask web on each side).
* **Horizontal line at y 6.3, x 17.1..24.2.** The best grid position for this line (`work/search2.py`, `search3.py`) still overlaps four other-net Bottom items. These are two pieces of the VCC1V0 C86->C87 feed, the VCC1V8 run (20.35, 5.475)-(21.875, 8.775) and the GNDADC via at (21.4, 6.95).

**A 2x3 block with JP3 left where it is does not fit either:**
* JP4 east at x 19.02 overlaps C94-1 by 0.14 mm and the VCC1V0 feed.
* JP4 west at x 16.48 overlaps C100's pads by 0.40 mm.

**The 2x3 block fits in only one window.** Four neighbours bound it:
* C100 on the west (pads up to x 16.38)
* R97 on the south-west (pad top at y 4.72)
* C94-1 on the south-east (from x 19.38, y <= 5.58)
* C85-1/C86-1 on the north (from y 9.10)

With pad_gate's 0.10 mask web and 0.30 to every body, these limits give:
* JP3 column x: 17.08..17.41
* bottom row y: 5.40..5.86 (the lower bound is 5.52 for x <= 17.2, from R97's body)

Two pieces of existing copper are inside that window:
* **FT-VCORE through via at (17.5, 8.425).** Its Bottom land is 0.31 mm from the GND pad centre. Anywhere in the window it is at most 0.56 mm from the top-left pad centre, and 0.77 mm is needed. The via carries only Top and L4 copper.
* **VCC1V0 0.5 mm feed at x 19.05..19.15.** Its left edge is at x 18.8..18.9. The east column reaches x >= 18.85.

## Change
**Block.** The block is on the Bottom at a 1.27 mm pitch. Both parts are at rotation 90, with pad 1 to the south. Each column reads like the sibling board's line: GND TMS TCK | VCC3V3 TDO TDI.

| y \ x | 17.20 (JP3) | 18.47 (JP4) |
|---|---|---|
| 8.36 | GND (JP3-3) | VCC3V3 (JP4-3) |
| 7.09 | TMS (JP3-2) | TDO (JP4-2) |
| 5.82 | TCK (JP3-1) | TDI (JP4-1) |

**Moves:**
* JP3: dx -0.55, dy +0.77. Rotation stays at 90. New origin (pad 2) is (17.20, 7.09).
* JP4: dx +12.35, dy +3.94. Rotation changes from 0 to 90. New origin is (18.47, 7.09).
* No other part moves.

**Removed (32 tracks, 4 vias):**
* JP4's whole TDI branch: the U2-17 Top run (8.3 -> 9.85 at y 2.825), the through via at (8.3, 2.825), and 21 Bottom pieces west to the old JP4-1.
* JP4's TDO branch: 5 Bottom pieces from R91-1 west to the old JP4-2. R91-1 keeps its stack at (8.975, 4.475).
* The old JP4-3 VCC3V3 laser at (7.275, 2.775).
* The old JP3-3 GND through via at (17.475, 7.275) and its 0.025 stub. It would sit on the new TMS pad.
* The TMS tail into the old JP3-2.
* Three VCC1V0 feed pieces.

**FT-VCORE.** The through via at (17.5, 8.425) becomes a Top>L2>L3>L4 stack (0.30/0.15, 0.30/0.15, 0.27/0.15) at the same point. The stack has the same Top and L4 joints as the through via but no Bottom land. The board already has 43 Top>L2>L3>L4 stacks (13 with these exact sizes, 14 now).

**VCC1V0 (C86-1 -> C87-1 Bottom feed).** The 0.2 neck now runs straight up x 19.19 to y 6.37, 0.12 mm from the new TDI pad and 0.09 from C94-1 as before. It then goes:
* 0.3 out to x 19.45
* 0.5 up to y 8.85
* 0.5 back into C86-1 at (19.05, 9.25)

The piece widths go from {0.15, 0.15, 0.2, 0.3, 0.5} to {0.15, 0.15, 0.2, 0.3, 0.5, 0.5}. No net or layer got narrower.

**TCK.** The L4>L5>Bottom stack at (17.375, 5.175) and its L4 run stay. A 0.67 mm Bottom link joins the stack to the moved JP3-1. The via land is 0.018 mm outside the pad copper. It still reaches 0.032 mm into the pad's 0.05 mask opening. That crescent of same-net land is exposed, but the hole is not (hole edge 0.59 from the pad centre). Before the move, this via sat in JP3-1 itself.

**TMS.** The kept Bottom run ends at (17.125, 6.575). A 0.52 mm piece joins it to JP3-2.

**Plane ties.** Both vias sit beside the pad. Neither is in the pad.
* GND: a dedicated through via 0.35/0.20 at (16.60, 7.885), with a 0.25 track to JP3-3. The land is 0.09 outside JP3-3's copper, so it is clear of that pad's mask opening. Its nearest other-net copper is at least 0.32 away on every layer; on the Bottom it sits 0.045 from C100-2 (also GND) and its land reaches 0.005 into C100-2's mask opening (same net, hole not exposed; listed in the fab notes). On L5 its anti-pad leaves about 0.18 to the VCC3V3 pour (rule 0.175).
* VCC3V3: an L5>Bottom laser 0.30/0.15 at (17.835, 7.62), between the four upper pads, with a 0.2 track to JP4-3. It is 0.43 from the VCC3V3 Top>L5 stack at (17.85, 8.05), so route_check's hole rule of 0.24 holds.

**TDI and TDO** (`route_tdi_tdo.json`, tools/router.py on stage A's model, no rip-up):
* TDI: from its L4>L5>Bottom stack at (12.35, 4.1), on the R90 / R4-3 path, along L4 to a new L4>L5>Bottom stack at (17.1, 4.575), then on Bottom into JP4-1. The branch is 6.28 mm long.
* TDO: from its L3 run at (13.95, 5.275), along L3 to a buried L3-L4 via at (17.1, 6.35), along L4 to a new L4>L5>Bottom stack at (17.85, 6.625), then on Bottom into JP4-2. The branch is 6.22 mm long.

**Via count: 1575 -> 1581.**
* Through vias: -2 (three removed, one GND added).
* Single-level lasers 0.30/0.15: +6.
* Buried L3-L4 0.27/0.15: +2.
* Stacked sites: +3 (FT-VCORE, TDI, TDO).
* Vias in a JP pad: 3 -> 0. These were the old VIP-list rows JP3-1, JP3-3 and JP4-3.

## Proof (gates.txt, all from this directory's files)
| Gate | Result |
|---|---|
| route_check plan.json model_moved.json | 34 tracks, 10 vias, 32 removed. Violations: **0**. Open connections after the plan: **0**. PASS |
| hole_gate, whole final board (vias given from/to) | 0 pairs under 0.240 in the same dielectric. PASS (base: 0) |
| pad_gate model_final.json JP3 JP4 | 22 pairs within 1 mm, 0 under clearance 0.0762 or web 0.10. PASS. The nearest other part's pad is C85-1 / C86-1 at a 0.240 gap (web 0.140) |
| Moved pads vs other-net tracks and vias | Min **0.103** (JP3-1 to the FPGA-TCK laser). 0 under 0.09 |
| route_conn, final model | 0 open |
| Dangling ends / weak vias (TCK TMS TDI TDO GND VCC3V3 FT-VCORE VCC1V0) | Base 2, final 2, **new 0**. The two are pre-existing GND Top-L2 lasers far from this change |
| Widths | 0 net/layer pairs narrower |
| body_check, full board | Base 8 findings, final 8, **new or worse 0**. The one overlap is the baseline's. mech_mismatch: none |
| Probe access | Nearest other part body **0.420** (C100, to JP3-1 / JP3-2; target 0.30). Nearest other pad 0.240 (C85-1 / C86-1). X2 housing 2.78 away |
| Branch lengths | TDI 4.96 -> 6.28 mm<br>TDO 2.84 -> 6.22 mm<br>TCK 4.52 -> 5.19 mm<br>TMS 5.11 -> 5.35 mm |

A smoke test ran tools/emit_copper.py's main() with its output redirected into `emit/`; nothing was written under Rev_1. It accepts the plan and emits the move guards, `Cm.Rotation := 90.0` and the pad-1 checks (17.200, 5.820) and (18.470, 5.820).

## Rebuild
1. `python build.py --stage-a` writes `model_a.json`, the router input.
2. In Rev_1/tools, run:
   * `python router.py --model <here>/model_a.json --nets TDI --rip 0 --pops 1500000 --margin 4 --out <here>/work/r2_tdi.json`
   * then `python router.py --model <here>/model_a.json --seed <here>/work/r2_tdi.json --nets TDO --rip 0 --pops 1500000 --margin 4 --out <here>/work/r2_tdi_tdo.json`

   The output is byte-for-byte equal to `route_tdi_tdo.json` (checked).
3. `python build.py` writes plan.json, model_moved.json, model_final.json and comps_final.json.
4. `python gates.py > gates.txt`
5. `python picture.py` writes jtag_east_bottom.png.

## Applied 2026-11-21 (docs/jtag_block.md)
1. tools/FeatherCopper_JtagBlock.pas (emit_copper on plan.json): removals, then the moves (a plain component move plus rotation, not a drag), then the new copper. Both pad-1 checks passed.
2. Repour All (L2 / L5 polygons), save.
3. tools/mark_microvias.py --expect 1174 on the closed PcbDoc marked the 7 new lasers. The 2 new buried L3-L4 vias are not microvias and stay unmarked.
4. DRC with Component Clearance: JP3 vs JP4 flagged (test pads have no 3D body), so tools/AsarCCRuleJTAG.pas added ComponentClearance_JP3JP4 (0.10). Saved again after the clean DRC; DRC 0, 36 rules.
5. Fabrication and assembly releases rebuilt and PASS. The VIP CSV lost three JP rows; laser, buried, through and stacked counts changed as listed in docs/jtag_block.md.

## Files
* `build.py`: stage A by hand, plus the frozen router output. Writes plan.json (emit_copper format with `moves`, including JP4's `rotation`), model_moved.json, model_final.json and comps_final.json.
* `route_tdi_tdo.json`: the router's TDI and TDO copper.
* `gates.py` and `gates.txt`: the gates above.
* `picture.py`, `draw.py` and `jtag_east_bottom.png`: the Bottom side before and after.
* `work/`: the exploration scripts (window search, via-site scan, stage-A checks) and the router outputs r2_tdi.json / r2_tdi_tdo.json. Their large data files (grid.npz, candidate lists, intermediate models) were not kept; build.py regenerates model_a.json / model_moved.json. build.py reads ../model.json, ../comps.json (board 9be75ad9, kept) and ../board.PcbDoc, which is backups/asar_feather_before_jtag_block.PcbDoc (copy it there to rebuild).
* `empty_plan.json`: the empty plan hole_gate runs on for the whole-board check.
