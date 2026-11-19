# Fab B BTN spread (2026-11-08)

After the LED spread, BTN (PTS810 tactile switch, body 3.2 x 4.2 mm) still sat 0.90 mm (pad to pad) from the LED
column on its east, with 3.2 mm of empty Top side to its west (out to the microSD socket X3). It moved 1.25 mm west,
from x 19.80 to 18.55 (y unchanged at 12.92), so the two gaps are now equal:

| Gap (pad edge to pad edge) | Before | After |
|---|---:|---:|
| X3 (microSD) -> BTN | 3.375 | 2.125 |
| BTN -> LED column    | 0.900 | 2.150 |

The BTN designator moved with the part onto C158's pads (silk-to-mask, 2 DRC hits); it now sits centred under the
button (box x 17.31..19.79, y 8.97..10.02, 0.30 mm below the pads), placed by `tools/FabB_BtnLabel.pas`.

## How it was done
1. `tools/btn_spread_prep.py` moves BTN in the router model and rips the pocket: 13 tracks and 28 vias on CHAN21,
   CHAN22, FT-RESETN, N$BTN, SD-CLK and VCC3V3 (8 open connections).
2. `router.py` closed all 8 in 68 s (28 vias, 47 tracks); `plan_prune` / `plan_dedupe` changed nothing.
3. New `tools/compose_plan.py` folds the stub prune into the plan before anything reaches the board: it applies
   rip + route to the board model, runs `prune_stubs.analyse`, and turns dead copper into removals (here 3 clipped L3
   tails, 2 of them trimmed, and 1 orphaned VCC3V3 through via). The composed plan leaves 0 dead copper and 0 open.
   `route_check` against the board with BTN moved: 0 violations, 0 open.
4. `emit_copper.py` now supports X moves (`dx`). `FabBCopper_BtnSpread.PrjScr` / `PlaceBtnSpread` applied it
   exactly: moved 1 part, removed 16 tracks and 29 vias, placed 28 vias and 49 tracks.
5. `mark_microvias.py --expect 1030` marked the 22 new laser vias (1031 - 23 removed + 22 added).
6. Repour All, DRC: 0 copper violations; the 2 silk hits were the designator, fixed in step above. Final DRC 0/0.

Via-in-pad: two filled Top>L2 microvias sit in BTN pads (N$BTN in pad 4, VCC3V3 in pad 2), replacing the three the
earlier BTN move had put in pads 1, 3 and 4; the VIPPO note in the fab files still applies.

## Result
- PcbDoc md5 dd2a32b02f1b4b6b16b2c7da9bccbe20; backup before the edit `backups/zulu_a7_fab_b_before_btn_spread.PcbDoc`
  (= de7a8f00, the LED-spread board).
- Re-extracted model `tools/route/btn/final.json`: 4349 tracks, 1785 vias (as planned), 0 open, 0 dead copper.
- 1030 microvia records verified. Picture: `docs/btn_spread_after.png`.
