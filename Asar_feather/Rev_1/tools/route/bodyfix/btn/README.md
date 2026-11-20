# Fix "btn": BTN 0.50 mm west, clear of X5 (Asar A7 Feather, board c4bf0b71)

## Problem
BTN (PTS810, Top) pad 2 sat 0.100 mm south of X5's housing (JST SM04B-SRSS-TB, body x 46.05..50.30,
y 6.70..12.70), and BTN's body sat 0.35 mm west of it. The target was pad 2 at least 0.30 mm away and the body
at least 0.50 mm away. The gap is diagonal: pad 2 overlaps X5's body in x, and the clearance in y is only 0.10.
So BTN has to move at least 0.433 mm west (hypot(d - 0.1499, 0.1001) >= 0.30). The suggested 0.3-0.4 mm
does not reach the target.

## Change
* **Move**: BTN moves rigidly by dx = -0.50, dy = 0, with no rotation. It does not move in y, so the TX / D4
  labels below it (ink up to y 3.394; BTN body bottom stays at 3.60) stay clear. The pad centres are now
  x 41.0251 / 45.1749.
* **Via-in-pads**: none move. The pad 1 and pad 2 VCC3V3 stacks at (41.125 / 45.275, 6.025) and the pad 3 N$BTN
  Top>L2>L3 via at (41.125, 3.975) stay where they are. Their centres are inside the moved pads. Before the move,
  each land overhung its pad's west edge by 0.025 mm; now each land is fully inside in x. Pads 1 and 2 keep the
  existing 0.075 mm overhang on their south edge, which the move does not change.
* **Copper**: 4 tracks are removed and 6 are added, all on Top at 0.0762 mm, on signal nets only. No vias change.
  * **N$BTN**: the north branch at x 40.85 ran through the moved pad 1 (VCC3V3), so both of its pieces are removed.
    The new branch leaves the pad 3-4 link at x 41.70 and runs north 0.112 mm east of pad 1 to y 6.65. It then
    rejoins the old track end at (40.85, 9.15) in one segment. The pad 3-4 link (41.925 -> 45.275 at y 3.875) ended
    in the old pad 3 only, so a 0.625 mm stub (41.3001 -> 41.925) joins it to the moved pad 3.
  * **N$LD0B**: the diagonal from LD0-1 crossed the moved pad 3, so the diagonal and the run under the pads are both
    removed. The new route keeps the same 45-degree line (x + y = 44.625) to (40.35, 4.275) and drops at x 40.35,
    0.112 mm west of pad 3. It then runs east at y 3.669 instead of 3.675 and ends at (46.244, 3.669), exactly on
    the line of the kept (46.25, 3.675)-(46.325, 3.75) piece. The new run is 0.093 mm from pads 3 and 4 and from
    N$LD0G at y 3.5. The old run was 0.0857 mm from them, below the router's 0.09 mm clearance.

## Proof (all from this directory's files)
| Gate | Result |
|---|---|
| body_check `--refs BTN --gap 1.0` | X5 body to BTN pad 2: **0.364** (target 0.30). BTN body to X5 body: **0.850** (target 0.50). No other part comes within 1 mm. |
| body_check, full board | The same 41 findings as the baseline, line for line (diff is empty). Nothing new and nothing involving BTN. The remaining overlaps are the baseline's U8/C151 and X2 south-row findings, which belong to the other fixes. |
| route_check plan.json model1.json | 0 violations, 0 open connections, PASS |
| hole_gate (model vias given from/to) | 0 pairs, PASS (no holes added) |
| pad_gate model_final.json BTN | 0 under 0.0762 or web 0.10, PASS (nearest pad: R80/R81 at 0.70) |
| verify.py: moved pads vs foreign Top copper | Minimum 0.093. Baseline: 0.0857 at pads 3 and 4. |
| verify.py: islands / dangling | 0 open before and after. No net gained an island. 0 dangling items before and after. |
| verify.py: power widths | 0 power-net items touched. No net or layer got narrower. |

## Files
* `build.py`: rebuilds `model1.json` (BTN moved), `plan.json` (emit_copper format plus `moves`) and
  `model_final.json`.
* `verify.py`: runs the extra gates above and writes `model_final_hg.json` for hole_gate.

`emit_copper.py` has no `moves` support. The BTN move must be a plain component move in Altium
(MoveByXY -0.50, 0), not a drag that pulls tracks with it. Free vias stay where they are. The free silk text
'BTN' above the switch (x 42.10..44.53) stays put and is now 0.22 mm east of the switch's centre line.
