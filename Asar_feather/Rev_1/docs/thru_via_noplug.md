# No through via in an SMD pad: PCBWay need not resin-plug (2026-11-23)

The owner asked to clear Asar's through vias out of the SMD pads, so that the order drops PCBWay's flat resin-plug /
plate-over step (IPC-4761 type VII, about $70 and 2-3 days). A partial fix saves nothing, so the goal was zero.

Phases 1-3 reached zero, but the result was electrically worse than the original. The owner said "Keep fixing", and
phases 4-5 plus a clean-up (5c) brought it back close to the original. The plan, its gates and its README are in
`tools/route/thru_vip_noplug/`; `vip_check.py` and `vip_tight.py` there are the acceptance checkers.

## Result

| | Before (682cd9d3) | After (2d0736f2) |
|---|---|---|
| Through vias in or touching an SMD pad (vip_check) | 102 | **0** |
| Through vias without a 3-mil etchable land gap / 0.10 hole-to-mask (vip_tight) | 105 | **0** |
| Through vias 0.20/0.35 | 153 | 109 |
| Laser microvias | 1174 | 1359 |
| Buried L3-L4 | 254 | 311 |
| Three-drill stacked sites (four/five-drill) | 65 (59/5) | 94 (59/5, none new) |
| Tracks / vias | 4807 / 1581 | 4893 / 1779 |

The change removes 197 tracks and 122 vias and adds 283 tracks and 320 vias. Six parts move, rotation kept:

| Part | Move |
|---|---|
| C78 | 0 / +0.05 |
| C121 | -0.05 / 0 |
| C124 | +0.13 / 0 |
| L1 | +0.13 / 0 |
| L2 | +0.17 / 0 |
| L9 | 0 / -0.02 |

Every through via that was in a pad is either dog-boned out or replaced by filled laser vias in the pad. A dog-boned
via's land is at least 0.0762 from pad copper, so the gap can be etched and CAM cannot merge it back into the pad, and
its hole is at least 0.10 from the mask opening. The tightest dog-bone has a 0.0775 land gap and 0.1016 hole-to-mask.
The board-wide minimum hole-to-mask, 0.1009, is an original via (CLK-12M-FT at R4-14).

L5-VCC3V3 now carries 8 short tracks (6 GND, 1 VU, 1 VCCADC; 0.20-0.25 mm) as well as its pour. The 5 um repour
simulation and Altium's repour keep L5 one live island.

The checkers read `pad_truth.json` beside them (md5 c550afde; U1 balls round, proven against the released Gerbers).
To re-run them, dump the board with `tools/route_model.py` (KiCad python, `ASAR_MODEL=<out.json>`), then run
`python tools/route/thru_vip_noplug/vip_tight.py <out.json>`. Both checkers give 0 on 2d0736f2.

## Electrical: original -> after

Regulator hot loops (input cap to IC pins), mm / vias in series. Two path metrics are given because they disagree. Both
use the shortest copper path with plane hops at straight distance:
- **s5** (`gates.txt` 18a) prefers the through-via ties.
- **s4** (`gates.txt` 20c) lets the path run through the filled-laser chains.

| Loop | Before (s5 / s4) | After s5 | After s4 |
|---|---|---|---|
| Buck-1 VIN, C148-2 -> U8-5 | 3.00 / 2 | 3.25 / 4 | 3.25 / 4 |
| Buck-1 GND, C148-1 -> U8-3 | 4.26 / 2; 5.22 / 2 | **5.16 / 2 (+0.90)** | 4.86 / 5 |
| Buck-2 GND, C160-1 -> U8-16 | 4.15 / 2; 4.23 / 2 | 4.31 / 2 | 4.29 / 2 |
| U7 input GND, C149-1 -> U7-2 | 2.09 / 2; 3.28 / 2 | 2.22 / 4 | 2.22 / 4 |
| USB input, C150-1 -> U8 exposed pad | 1.35 / 6 (s4) | - | 0.73 / 0 |

Buck-1 VIN is 0.25 mm longer, with two more filled microvias: about 0.1-0.2 nH, small next to the capacitor's own
mounted inductance.

Buck-1's GND return is the worst case. Through the through vias it is 0.9 mm longer. Through the laser chains it is
0.35 mm shorter, but with three more microvias in series. Each filled microvia spans one ~0.1 mm dielectric (roughly
0.05 nH), so the real return sits between the two numbers. Treat it as slightly worse than the original.

C149-1 -> U7-2 counts as met only because the metric credits a 0.30 mm L3 GND strap into U7-2's in-pad stack. U7-2's
only direct L2 tie is the dog-bone on the side away from the caps.

`gates.txt` ends "GATES FAIL" with 12 failing gates. The owner accepted all 12; the misses are not hidden:
- **Raw pad_gate:** fails only on the original 0.100 mm mask webs, which the moves do not change.
- **C124:** 0.04 mm farther from U1.
- **G-TIE:** C121-2.
- **U8 GND full-depth tie sites:** 1 within 0.6 mm (the rule asks for 4).
- **G-LOOP:**
  - s5: 6 pairs beyond +0.50 (C148-1>U8-3, C82-1>U8-16, C147-1>U8-27, C167-1>U8-27, C148-2>U8-1, C151-1>U8-27).
  - s4: 23 of 158 pairs, e.g. C82-1>U8-29 +0.93 mm; 17 of them only on via count.
- **G-POWER:** 24 of 442 pairs.
- **G-COUPLE:** 20 net pairs, all but PWR_SW2|VU against GND / VCC3V3.
- **G-SIG:** 21 slow-signal pairs.

U8 GND has GND through vias at 0.61-0.74 mm from pins 3, 13 and 16, against 0.31 mm in the original. The physical
minimum for a dog-boned via off a 0.5 mm-pitch QFN pin end is about 0.60 mm. Pins 3, 10 and 13 are strapped to U8's
exposed pad with 0.25 mm Bottom copper, so the group shares these vias. U8-27 has no through via (X4-2's Top pad
covers the site); it reaches GND through a filled-laser chain with a 0.45 mm tie.

Accepted remainders, all small and listed in full in `tools/route/thru_vip_noplug/gates.txt` sections 20c-20h:
- **VU paths:** from U8-1, up to +0.72 mm on a 0.40 mm track (under 1 mOhm); C160-2 -> U8-5 is +1.6 mm / +2 vias.
- **VCC1V8 -> L7-1:** +1.27 to +1.52 mm on a 0.15 mm track. This is mA-level XADC supply, upstream of the ferrite.
- **C121-2 tie:** 0.73 mm (limit 0.60). It is a 0201 decap among many in parallel.
- **Switch-node coupling:** PWR_SW2 runs 0.0925 mm from VU over 0.86 mm (was 0.125 over 0.44), from L2's move. VU is a
  stiff, decoupled rail.
- **DONE via antipad:** the DONE through via's L5 antipad lies under PROG#'s L4 track (0.743 mm, was 0.449). Every legal
  nudge brings it closer to a clock.
- **Slow signals:** TMS, TDI, EE-CLK, FPGA-TDO, GNDADC and PWR_FB2 gain up to 4-5 microvias.
- **Untouched:** XADC AIN15/16 and USB D+/D- copper.
- **Leftover via-to-pad stubs:** the original GND through vias at U8-3 (8.3, 16.475) and U8-13 (11.175, 19.4) were
  removed, but their 0.30 mm stubs to the pads stay. Each reaches 0.10 mm past its pad, inside the footprint of the
  removed 0.35 mm via land. That is no new copper exposure compared with the original, so they are accepted.

## Assembly

- **0201 tombstone balance** is back to the original level: parts over 0.2 of pad area 5 (original 5), over 0.1 28
  (original 32).
- **Uneven heating:** on 22 small capacitors the GND pad reaches its plane through a filled chain or dog-bone while the
  other pad has a direct laser into a plane. These are 0201 C38, C111, C117, C119-C122, C133-C138, C155, C157-C159 and
  0402 C3-C7. The assembly notes ask PCBWay for a ramp-soak-spike profile on the bottom side.
- **X4 tab mask strips:** X4-MP1 and X4-MP2 (no-net JST mounting tabs) have 0.047 / 0.029 mm mask strips to VU / VBATT.
  The copper gap holds, and a bridge would only tie a rail to a floating tab. Accepted.

## Altium (2026-11-23)

1. Backup `backups/asar_feather_before_vip_noplug.PcbDoc` (682cd9d3).
2. Ran `tools/FeatherCopper_VipFinal5c.pas` (Run Script > Browse > From file, `.PrjScr`). It reported "Moved 6 parts,
   removed 197 tracks and 122 vias, placed 320 vias and 283 tracks", with no missing net.
3. Repour All, save (21:28:57), close.
4. The 2026-11-21 `.pre-microvia` backup was renamed `.pre-microvia-2026-11-21`.
   `mark_microvias.py --expect 1359` marked the 198 new lasers.
5. Dumped the closed board (`route_model.py`): tracks 4893, vias 1779 and pads 840 equal the plan's model object for
   object. vip_check and vip_tight both report 0 on it.
6. Reopened, Repour All, then DRC: 36 rules, 0 warnings, 0 violations, including hole size (microvia rule),
   hole-to-hole, component clearance with 3D bodies, mask sliver and net antennae. Saved after the clean DRC at 21:32:21:
   **MD5 2d0736f200d2ee47d43653ea173fddb0**, SHA-256 CD3E56C7...BCD983.
7. `mark_microvias.py --expect 1359 --verify`: verified. The board stores no violation marker.
8. Gerbers 21:32:56. NC drill 21:33:53: split plated / non-plated and G85 had reset and were ticked again.
9. The DRC was re-run after the save for the packager's freshness check (21:35:07, 0/0): `docs/drc_thru_via_noplug.drc`.
   The board was not saved again (MD5 unchanged).

Drill table (`asar_feather.DRR`):

| File | Before | After |
|---|---|---|
| Through 0.20 | 153 | 109 |
| Buried L3-L4 0.15 | 254 | 311 |
| Top-L2 0.10 / 0.15 | 173 / 210 | 177 / 219 |
| L2-L3 | 105 / 174 | 125 / 201 |
| L4-L5 | 47 / 199 | 64 / 241 |
| L5-Bottom | 23 / 243 | 46 / 286 |

1.00 x 28, NPTH 2.50 x 4 and slots 0.50 x 2 are unchanged.

## Release (2026-11-23 PROVISIONAL)

- **`tools/package_fabrication_release.py`**, retargeted (hash, drills, 1359 microvias, date):
  - It gained no-plug branches. Q8 reads "Through vias in SMD pads: NONE - please tent, do not plug", the tenting
    section says all 109 through vias are tented (IPC-4761 type I/II), and Q10 asks the price without plugging.
  - It refuses to print that text if any through-via land reaches a mask opening.
  - Q7 and the layer table now say L5 carries 8 short tracks besides its pour (fab_facts gained
    `track_count_by_layer`).
  - The "replaces" paragraph now lists exactly what changes. That is copper, the bottom mask and paste, and the
    plated drill files. Top mask and paste, NPTH, slots, outline, stack-up and silkscreen do not change.
  - The new conditional clauses are parenthesised, so `%` and `+` apply to the whole sentence.
  - With through vias in pads, the plugged branch still prints the master text.
  - `fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-23_PROVISIONAL.zip`: PASS (body gate 0 fail, 5 warn as before).
- **`tools/generate_pcbway_assembly.py`**:
  - No-plug branches.
  - The zero-count lookups use `.get`.
  - The new item-D conditional is joined with `+`.
  - It adds the soak-reflow bullet, printed only when no through via is in a pad.
  - `assembly/Asar_Feather_PCBWay_Assembly_2026-11-23_PROVISIONAL.zip`: PASS. The BOM is identical. Six CPL rows
    change: C78, C121, C124, L1, L2, L9.
- The 2026-11-21 zips moved to `backups/*_plugged_superseded.zip`.
- Board pictures, `tools/board_dump.json` and `tools/picture_dump.json` were refreshed from 2d0736f2.

For PCBWay: the quote must drop the resin-plug step. The via mix changed: 44 fewer through vias, 185 more lasers, 57
more buried vias, and 29 more three-drill stacked sites. Every laser in or touching an SMD pad (502 in the CSV) and
every stacked site is copper-filled and capped flat, as before.
