# x2row: the bottom 0201 row clears X2's south header housing

Asar A7 Feather, board `asar_feather.PcbDoc` md5 c4bf0b71 (read only). The model is `Rev_1/tools/route/body_gate/model.json`.
`build.py` writes `model1.json` (parts moved, copper unchanged), `plan.json` (emit_copper format with `moves`) and
`model_final.json` (model1 with the plan applied).

## The problem
The twelve bottom 0201s C40 C41 C152 C153 C154 R19 C155 C156 C157 C158 C159 C38 have their pads at y 2.670. X2's
bottom header housing for pins 1-16 ends at y 2.540. The bodies overlap it by 0.020 mm nominal and 0.035 mm at
maximum tolerance (36 body_check findings).

## The change
**Moves (rotations unchanged):**
- The twelve parts move together by (0, +0.125), so the row stays straight with its pads at y 2.795. The extra
  0.005 above the 0.12 minimum keeps the nominal gap off the 0.10 float edge.
- R18 (0402, FT-REF) moves by (+0.02, +0.05). This widens the Bottom lane between C41 and R18-2 so TDI fits at
  0.09 mm clearance. Without the nudge the lane is 0.235 mm, which leaves 0.079 a side.

**Copper:** 13 tracks and 5 vias removed; 29 tracks and 5 vias added.
1. **21 jogs on Bottom.** Each runs from the via's centre to the moved pad's centre. They are 0.20 wide for GND,
   VCC3V3 and FT-VPLL, and 0.15 for FT-VPHY and FT-VCORE. The vias stay where they are.
   - Moving them with the parts fails. Of the 23 vias that serve the row, 10 would break 0.09, 8 of them by
     overlapping something: U2's south pads, the TDI and CHAN1 tracks on Top, R86, and the FT-VPHY/FT-VCORE L4 tracks.
   - After the move, the vias that stay only touch their pads by 0.055 mm, or not at all where a pad was fed by a
     stub. Every jog gives a full-width contact instead.
2. **FT-VCORE stack (45+5B).** It moves from (14.500, 2.900) to (14.470, 2.920), and its Bottom and L4 tracks get
   new end points. C153-1 had moved to 0.070 from it; the gap is now 0.100.
3. **FT-RESETN.** The Bottom run from (14.725, 3.425) to R19-1 is removed, with its 45+5B stack (7 tracks, 2 vias).
   That run sat in a lane north of C153/C154 that becomes 0.185 mm once the row moves. L4 now continues from the
   existing end at (14.725, 3.425) at y 3.60 to a stack_bot (L4>L5>Bottom, 0.30/0.15) in R19-1's pad (3 tracks,
   2 vias). This is a via in a pad, so the laser needs to be filled and capped, like the board's other lasers.
4. **TDI.** The through via under U2-17 moves north by the row's dy, from (9.825, 3.075) to (9.825, 3.200). The
   Bottom run over C41 is laid again at y 3.0875, centred in the C41 / R18-2 lane. It rejoins the old track at
   (11.05, 3.275) at 45 degrees. The Top stub inside U2-17 goes, because the via now sits on the pad.

## Gates (final model)
| Gate | Result |
|---|---|
| body_check (whole board) | The 36 X2/row findings are gone. The row is 0.105 mm from the housing (nominal), 0.090 at maximum tolerance, and the housing is 0.105 from the pads. What remains is the baseline list unchanged: U8/C151 -0.150 (a separate fix), U7/L3 0.025, and X2 to C101/C102/C139 0.040. No new finding. |
| route_check plan.json model1.json | 0 violations, 0 open connections |
| hole_gate | PASS. Plan against model1 minus the removed vias: 0 pairs. Final board, all pairs: 0 pairs. |
| pad_gate (12 row parts + R18) | PASS. 112 pairs within 1 mm, none under 0.0762 or the 0.10 web. The tightest is 0.235 / 0.135. |
| check_extra.py | PASS. Moved pads against all other-net copper: min 0.0971 (C41-1 to the TDI via). New copper to the X1/X2 pads: 0.181 (rule 0.127). |
| dangling.py | PASS. Every touched net is still 1 island with 0 padless groups. Antenna counts are unchanged (GND 84/84 are its plane-tie via ends). Board-wide open is 0/0. |
| widths | No touched net got narrower. FT-VCORE stays 0.15, TDI and FT-RESETN stay 0.0762, and the new GND/VCC3V3/FT-VPLL jogs are 0.20, wider than the 0.076 / 0.15 stubs they back up. |

**Repour needed:** L2 and L5 must be repoured. The changed vias leave slivers on the planes of 0.029 to 0.034 mm.
The baseline had slivers of 0.004 at the same spots. The pours' 3 mil Remove Necks clears them.

## Considered
- **Vias move with the parts.** Rejected: see the numbers in step 1 of the change.
- **The router for TDI, no R18 nudge.** `router.py --nets TDI --rip 0` closed it, but the result is a long detour:
  - an L3/L4 path from the via at (8.300, 2.825) out to R4-3, about 9 mm, with 3 vias and 14 tracks;
  - the 9-track tail to R90 would have to be removed as well;
  - in total about 31 copper items against 9, for one 80 um part nudge saved.
- **TDI kept in the old lane at 3 mil.** 0.079 a side passes the board's 0.0762 rule but fails the 0.09 routing
  check.
