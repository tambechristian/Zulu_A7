# Fab B: LEDs and BTN shifted west, away from U2 (2026-11-08)

The LED column sat 0.40 mm (pad to pad) from U2's west pad row. The user asked for more room there and chose to even
out all three Top-side gaps along the row X3 (microSD) - BTN - LEDs - U2:

| Gap (pad edge to pad edge) | Before | After |
|---|---:|---:|
| X3 -> BTN   | 2.125 | 1.575 |
| BTN -> LEDs | 2.150 | 1.550 |
| LEDs -> U2  | 0.400 | 1.550 |

Moves: BTN x 18.55 -> 18.00 (dx -0.55); LD0..LD5 x 23.35 -> 22.20 (dx -1.15). Y positions and the 1.6 mm LED pitch
are unchanged. The BTN designator moved with the part and still clears everything.

## How it was done
1. `tools/shift_prep.py <base> route/shift route/shift/moves.json` (generic group move + rip): 163 tracks and 67 vias
   on 25 nets ripped, 29 connections open.
2. `router.py` default order closed all 29 (76 vias, 164 tracks) in about 15 minutes; three other orderings were run
   in parallel and stopped once it finished.
3. `compose_plan.py` folded in 18 dead tracks (3 trimmed) and 11 dead vias; `route_check` vs `base_moved.json`:
   0 violations, 0 open. `FabBCopper_Shift` / `PlaceShift` applied it exactly (7 moves, -181 tracks, -78 vias,
   +76 vias, +167 tracks). `mark_microvias --expect 1027` marked 59 lasers.
4. First DRC found 2 problems the gate had missed: an orphan LED0_B fragment (7 L4 tracks + 1 buried via, reported as
   Un-Routed) and an SD-DAT0 Top stub (Net Antennae).
   **Gate bug, fixed in `prune_stubs.py`:** a track end counted as joined whenever it lay within half a width of a
   neighbour, so the router's 0.025 mm jog segments made every free end look connected. An end is now joined only to
   a coincident endpoint (within 0.01 mm) or a T-junction on another track's interior. Re-verified: the original
   board, the LED-spread board and the BTN-spread board all still report 0; the shifted board reported exactly the
   two DRC findings. `FabBCopper_ShiftCleanup` removed them (9 tracks, 1 buried via).
5. Final DRC 0 warnings / 0 violations; 1027 microvias verified; re-extracted model 0 open, 0 dead copper.

PcbDoc md5 16024cdb74af65ee10005a63d98d7b2e. Backup before this edit: `backups/zulu_a7_fab_b_before_shift.PcbDoc`
(dd2a32b0). Picture: `docs/led_btn_shift_after.png`.
