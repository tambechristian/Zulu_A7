# JTAG test pads in one 2x3 block (2026-11-21)

The owner did not like the six JTAG test points being apart: JP3 (TCK, TMS, GND) sat under the FT2232H's east edge at
x 17.75, and JP4 (TDI, TDO, VCC3V3) 11 mm away in the south-west corner beside X2's mounting hole. Both are
TP-1X03-SMD parts on the Bottom (three 1.0 mm round pads at 1.27 mm), not fitted (DNS).

## What fits

Design workflow wf_5978d09f-caf: three independent designers (cluster at JP4's site, at JP3's site, best site anywhere),
each plan checked by an adversarial verifier, then a judge.

- **A straight line of six does not fit** anywhere near the JTAG nets without moving power copper: every line
  position cuts the 0.4 mm VU trunk or the 0.5 mm VCC1V0 feed, or overlaps C100 / C85 / C86 / C94 / L5. The only
  clear line sites are along X2's north housing at the far north-east, about 5x farther from the JTAG nets.
- **A 2x3 block fits in two places**, both passing every gate:
  - **East (chosen):** at JP3's site, one window bounded by C100, R97, C94-1 and C85-1/C86-1.
  - **West:** in the south-west pocket above X2's mounting hole. Rejected: TDO and TDI would sit 1.9-2.1 mm from the
    hole centre, so a screw head or standoff on the Bottom could cover them and short them to VCC3V3.

## The change (tools/route/jtag6/east/, README there has the full proof)

| y \ x | 17.20 (JP3, rotation 90) | 18.47 (JP4, rotation 0 -> 90) |
|---|---|---|
| 8.36 | GND | VCC3V3 |
| 7.09 | TMS | TDO |
| 5.82 | TCK | TDI |

- JP3 moves dx -0.55, dy +0.77; JP4 moves dx +12.35, dy +3.94 and turns 90. No other part moves.
- Removed 32 tracks and 4 vias: JP4's whole TDI and TDO branches and its VCC3V3 laser, JP3's GND through via and the
  TMS tail into the old JP3-2, three VCC1V0 feed pieces, and the FT-VCORE through via at (17.5, 8.425).
- Added 34 tracks and 10 vias:
  - TDI and TDO re-routed (tools/router.py) from their existing vias to the new JP4 pads on L3 / L4, landing with
    new L4>L5>Bottom stacks; branches 6.28 and 6.22 mm.
  - TCK and TMS keep their routes; short Bottom links join them to the moved JP3 pads.
  - GND: a through via beside JP3-3. VCC3V3: an L5>Bottom laser between the upper pads. No via in any JP pad now.
  - FT-VCORE: the through via becomes a Top>L2>L3>L4 stack at the same point (no Bottom land).
  - VCC1V0 (C86-1 -> C87-1 Bottom feed) re-routed east of the block; no piece narrower.
- Gates (model): route_check 0 violations / 0 open, hole_gate PASS, pad_gate PASS (0.27 mm pad gap, 0.17 mm mask web
  inside the block; C85-1/C86-1 0.24 mm, web 0.14), body_check no new finding, no dangling copper. Nearest other part
  body 0.42 mm (C100), X2 housing 2.78 mm. Verified independently (OK).

## Altium

1. `tools/FeatherCopper_JtagBlock.pas` (tools/emit_copper.py): "Moved 2 parts, removed 32 tracks and 4 vias, placed
   10 vias and 34 tracks", both pad-1 checks passed. Repour All, saved 15:52:33.
2. PcbDoc closed; `mark_microvias.py --expect 1174` marked the 7 new lasers (backup
   `asar_feather.PcbDoc.pre-microvia`; the 11-19 one renamed `.pre-microvia-2026-11-19-bodyfix`). Reopened.
3. First DRC: 1 violation, Component Clearance JP3 vs JP4 (no 3D bodies on test pads, so Altium compares their
   primitive boxes). `tools/AsarCCRuleJTAG.pas` added `ComponentClearance_JP3JP4` (0.10 mm), like the other
   deliberate tight pairs. Saved 15:54:49.
4. DRC at 15:54:58: 0 violations. The review found that the 15:54:49 save (MD5 7490c9ef) still stored the first
   DRC's JP3/JP4 marker (a TComponentClearanceViolation stream), because it was saved before the clean DRC; anyone
   opening the board would have seen it. Saved again at 16:21:41 after the clean DRC: the stream is gone.
5. **DRC 0 warnings / 0 violations, 36 rules including Component Clearance** (`docs/drc_jtag_block.drc`, 16:21:51,
   after the final save). 1174 microvias verified; Connections6 empty (no stale ratsnest line).

Board MD5 **682cd9d3980d61aafd53e95f735ce5bd**, SHA-256 7EEBABAA...67080EF1 (was 9be75ad9).

The re-save also carried Altium housekeeping the review found harmless: hidden designator/comment texts of 15 parts
nudged (all hidden, silkscreen unchanged), 20 extruded bodies' MODEL.2D.ROTATION normalised (outlines identical), the
five older Component Clearance rules shifted one priority down behind the new one (same order), and the Repour All
re-rounded two L2/L5 anti-pad necks away from the change (by up to 0.02 mm, more clearance, not less).
Backup before: `backups/asar_feather_before_jtag_block.PcbDoc` (9be75ad9).

## Schematic

`tools/set_jp_block_notes.py` rewrote JP3's and JP4's NOTE parameter (asar_a7_4.SchDoc; the old text said the other
three pads were "4.2 mm away under the FT2232H"). Only those two records changed; sch_vs_board MATCH.
Backup `backups/asar_a7_4_before_jtag_block.SchDoc`.

## Release files

Gerbers 16:22:25, NC drill 16:22:49 (split plated / non-plated and G85 as before). Drill changes:

| File | Before | After |
|---|---|---|
| Through 0.20 | 155 | 153 |
| Buried L3-L4 0.15 | 252 | 254 |
| Top-L2 0.15 | 209 | 210 |
| L2-L3 0.15 | 173 | 174 |
| L4-L5 0.15 | 197 | 199 |
| L5-Bottom 0.15 | 241 | 243 |
| Microvias total | 1168 | 1174 |

- `package_fabrication_release.py` retargeted (hash, drill table, microvia total):
  `fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-21_PROVISIONAL.zip` PASS (body gate 0 fail, 5 warn as before).
  The notes' via counts follow the board: blind/buried XY sites 765 -> 769, of which stacked (2 or more drills)
  458 -> 461; the via-in-pad CSV loses the three JP rows (541 -> 538). Two new lands touched by a same-net pad's mask
  opening (hole not exposed) are listed: the TCK stack at (17.375, 5.175) by JP3-1 (0.032 mm) and the new GND
  through via at (16.60, 7.885) by C100-2 (0.005 mm).
- `generate_pcbway_assembly.py`: `assembly/Asar_Feather_PCBWay_Assembly_2026-11-21_PROVISIONAL.zip` PASS. BOM and CPL
  unchanged (JP3/JP4 are DNS); notes change only in the board hash and via counts.
- Board pictures and `tools/board_dump.json` / `tools/picture_dump.json` refreshed from this board.
- Independent review (workflow wf_38be2a45-0e0): every Tracks6 / Vias6 / Pads6 / Components6 change equals the plan
  one for one; 0 open connections and 0 dangling ends on the whole board; GND / VCC3V3 pads reach their planes; the
  7 new lasers flagged as microvias and the 2 buried vias not; Gerber and drill differences are the plan's objects
  plus the plane anti-pads; BOM and CPL identical; only JP3/JP4's NOTE records changed in the schematic.

For PCBWay: the via mix changed (+6 lasers, +2 buried, -2 through, 3 more stacked sites), so the quote's via
counts need the new notes.
