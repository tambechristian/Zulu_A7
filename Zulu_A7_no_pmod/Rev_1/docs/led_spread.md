# Fab B LED spread (2026-11-08)

The LED column at x = 23.35 mm was crowded: six LEDs on a 1.2 mm pitch with 0.30 mm gaps. It is now spread evenly.

| Part | Old Y (mm) | New Y (mm) | Notes |
|------|-----------:|-----------:|-------|
| LD4  | 17.385 | 17.385 | does not move; the column starts here |
| LD3  | 16.185 | 15.785 | 1.6 mm pitch, 0.70 mm gaps |
| LD5  | 14.985 | 14.185 | 1.6 mm pitch, 0.70 mm gaps |
| LD2  | 13.785 | 12.585 | 1.6 mm pitch, 0.70 mm gaps |
| LD1  | 12.585 | 10.985 | 1.6 mm pitch, 0.70 mm gaps |
| LD0 (RGB 1.6 x 1.6) | 10.885 | 8.91 | 0.70 mm below LD1 |

## How it was done

1. **Prep and route.**
   - `tools/led_spread_prep.py` moves the pads in the router model and rips the pocket.
   - The router closes every connection; for LED0_R that needed a seeded re-run.
   - The plan is `tools/route/led/led_spread_plan.json`. It removes 62 tracks and 28 vias and adds 55 vias and 187 tracks.
   - `route_check` reports 0 violations and 0 open connections.
2. **Apply the plan.** `FabBCopper_LedSpread2.PrjScr`, procedure `PlaceLedSpread2`, applies the plan.
   - The first version refused because of a false positive. Its guard via sat where a ripped via had been. The emitter now picks a guard via that is not co-located with a ripped one.
3. **Mark microvias.** `mark_microvias.py --expect 1042` marked the 44 new laser vias.
4. **First DRC.** After Repour All, DRC reported 1 un-routed connection (GND) and 10 net antennae.
   - All 11 were tails that the rip window had clipped. The router had re-routed those nets in full, sometimes joining mid-body onto an old tail.
   - The route model's island count could not see them.
5. **Prune the tails.** New gate: `tools/prune_stubs.py`.
   - It applies Altium's antenna test: a track end must touch same-net copper, and each via-stack element must touch at least two objects.
   - It prunes to a fixpoint and trims tracks back to their last junction instead of deleting them when the router joined mid-body.
   - It reports 0 on the original board.
   - On the edited board it found 15 tracks (3 of them re-added shorter) and 12 vias (11 lasers and 1 buried), with 0 open afterwards.
   - The cleanup was applied with `FabBCopper_PruneFinish.PrjScr`.
6. **Final DRC:** 0 warnings, 0 violations.
   - The microvia check verifies 1031 records. That is 1042 minus the 11 lasers that were pruned.
   - The re-extracted model has 0 open connections, 0 dead copper, and the LEDs at the planned positions.

The final PcbDoc md5 is de7a8f00e897b31a521dee5f67535b40. A backup of the board before the edit is at `backups/zulu_a7_fab_b_before_led_spread.PcbDoc`.

## Emitter fixes (tools/emit_copper.py)

- **Via matching includes the layer span.** Removed vias are matched on LowLayer/HighLayer as well as position. A stack is several vias at one point, so matching on position alone over-matched.
- **Nothing is removed until everything is found.** Tracks and vias are both matched before anything is removed. An earlier version removed the tracks and only then refused on the vias.
- **The guard via is never a co-located one.** The guard via is chosen so that it does not sit where a ripped via was.

## Not yet checked

- Silk designators of the moved LEDs: the DRC silk rules pass, but placement has not been reviewed by eye.
- The BTN neighbourhood is unchanged.
