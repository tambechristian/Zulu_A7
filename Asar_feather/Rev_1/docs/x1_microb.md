# X1: USB-C -> micro-USB B (2026-11-17)

## Why

X4 became a side-entry JST S2B-PH-SM4-TB at the Adafruit Feather position (docs/x4_jst_entry.md). Its rear
side legs (|x| 3.15..3.95 mm from the housing centre, reaching 7.6 mm behind the face: board y 14.7..16.3) sat on
the HRO USB-C X1 (west leg) and on oscillator Q1 (east leg). The user chose to replace USB-C with micro-B
("Yes, micro-B") and to keep U2 as it is (FT2232HQ QFN-64).

## Part

Amphenol ICC **10118193-0001LF** micro-USB 2.0 B receptacle, flanged, right angle, SMT: 5 contacts, 4 SMT shell
pads, 2 shell legs in plated slots. LCSC C132562 (12,765 in stock, about $0.28 when chosen). Customer drawing
10118193 Rev D. Runner-up: Molex 47346-0001 (all SMT, no slots) if PCBWay will not plate 0.50 x 1.20 mm slots.

## Footprint `AMPHENOL-10118193-0001LF` (asar_feather.PcbLib)

Made by copying MOLEX-105017-0001 in the PCB Library panel and moving its primitives with
`tools/AsarX1Morph2.pas` (scripted new primitives crash the library script engine on Altium 26.11.1). The first
morph (`AsarX1Morph.pas`) refused: the Molex copy's edge-line track (file layer 72) does not report as
eMechanical16, so Morph2 takes "the track on any other layer". The two parked Molex MS pads were deleted by hand.

Footprint origin = **pin 3 pad centre** (not the board edge); mouth toward -x.

| pads | centre (local mm) | size |
|---|---|---|
| 1..5 (VBUS, D-, D+, ID, GND) | (0, +1.30 .. -1.30), pitch 0.65 | 1.35 x 0.40 rect |
| MP1 / MP2 (rear shell) | (-0.225, +-3.20) | 1.40 x 1.60 |
| MP3 / MP4 (front shell) | (-2.675, +-1.20) | 1.90 x 1.90 |
| MH1 / MH2 (shell legs) | (-2.675, +-3.30) | plated slot 0.50 x 1.20 along x, 1.71 x 1.01 obround land |

Mech3 body x -4.825..0.225, y +-3.45; Mech7 flange; Mech2 courtyard; maker's PCB END line 4.125 mm behind pin 3.
Height 2.7 mm. Verified from the saved library file (slot hole type, 1.20 mm length, rotation 0).

## Schematic (sheet 1, `tools/x1_microb_schematic.py`)

X1 description / DeviceName / MANF (Amphenol ICC) / MANF# / Comment / footprint model; pin 4 renamed **4-ID** and
left open with a No-ERC marker; shell pin MH1 (was CC2) now **GND**; **R27/R28** (USB-C 5.1k CC pull-downs) deleted
with their label stubs. The script rebuilds the netlist before and after and refuses unless the only change is:
nets USB-CC1/USB-CC2 gone, GND loses R27-1/R28-1 and gains X1-MH1, X1-4 open. Backup:
`backups/asar_a7_1_before_x1_microb.SchDoc`. `tools/sch_vs_board.py` on the saved board: MATCH.

## Board

1. ECO from sheet 1 (net-class / diff-pair removals and 15 unrelated Design Item ID syncs unticked). The footprint
   swap itself failed ("Cannot match pads"), so `tools/AsarX1Remove.pas` deleted the old X1 and a second ECO
   added it back with the new footprint and nets.
2. X4 refreshed from the library inside this board only (Tools > Update From PCB Libraries, X4 ticked alone: the
   library-side "Update PCB With" would also have hit the open no-PMOD board, which uses the same footprint name).
3. `tools/AsarX1Place.pas`: X1 pin 3 at **(4.125, 11.43)**, rot 0, mouth west, designator/comment hidden (the
   free "X1" text stays); maker's PCB-end line on the board edge x = 0; body overhangs 0.70 mm, flange 1.30 mm.
   **Q1 moved 1.46 mm east** (pad 1 (14.15, 15.4) -> (15.61, 15.4)): pad edge 0.26 mm from X4's east leg.
4. Copper plan `tools/route/x1microb/` (build.py hand plan + router r1.json -> plan.json, emitted as
   `FeatherCopper_X1MicroB.pas`): 99 tracks + 20 vias removed, 32 tracks + 11 vias added.
   - D+ / D-: Top, 0.15 mm, X1 pins 3/2 -> U2-8/U2-7, 7.53 / 7.63 mm, coupled at 0.15 mm for 2.25 mm, no vias.
     Old USB copper (L3 D+ route, Top D- route, dangling USB5V0 stack) removed.
   - VBUS: X1-1 -> USB5V0 Top>L4 stack at (7.90, 13.88), 0.35 mm.
   - Shell ties on Top: MP2 -> MH2, MP1 -> MH1 (0.4 mm), pin 5 -> MP4 (0.3 mm); MH1/MH2 reach the L2 plane.
   - VU hop under X1 (fed only R26's pull-up): blind L4>L5>Bottom stacks at the old via spots joined by a
     0.2 mm L4 track (Bottom is blocked by C78-1 / L3-2, 0.3 mm apart).
   - Dead VU Bottom stub through MH1's slot (23 segments) removed; orphan GND laser (7.6, 7.95) removed.
   - Q1 area: VU feed rerouted straight down from V33, (14.475, 17.5) -> (14.475, 14.55) -> V37, 0.4 mm (under X4's
     east leg); FLASH-D02 (L3 -> buried -> L4 -> through via (17.45, 16.625) -> R2-1), CLK-12M-SHARED (Top>L3
     stack in Q1-3), FT-PWREN# (around Q1-3), GND ties for Q1-2 (laser in pad), C93-2 and C144-2 by the router.
   Gates on the plan: route_check (only the router's own VU inner-width preference; the DRC minimum is 0.2 mm),
   hole_gate PASS, pad_gate PASS, NPTH >= 0.127 PASS, dangling-end check 0, 0 open connections.
5. `tools/AsarX1Clean.pas`: the first DRC found what route_model.py (which skips net-less copper) could not see:
   26 net-less tracks + 2 vias (the old CC routes, net-less once the ECO deleted their nets) and three antennae
   (old Q1 GND/VCC3V3 ties, old USB-C shell tie): removed. U2's designator moved onto Q1-3; a designator move does
   not hold, so `tools/AsarU2Label.pas` hid it and added a free "U2" (box 12.70..14.34 x 12.60..13.71).
6. Microvias marked in the saved file (`tools/mark_microvias.py`, 1172 verified).

First saved state: MD5 f279d785 (12:46:07), DRC 0 / 0; superseded by the review fixes below. DRC does not run Component Clearance: by body boxes, X1 is 2.5 mm from
X4's west leg; Q1's pads are 0.26 mm and its Mech7 outline 0.16 mm from X4's east leg.

## Independent review (workflow wf_3b983b44-cc8, 4 finders + 4 skeptics) and fixes

No blockers. Fixed (13:50-13:54):
- **F2/C4** MH1/MH2 were full-stack pads left from the Molex copy: L3/L4/L5 kept 1.45 mm rounds (0.125 mm ring at
  the slot ends, VCC3V3 plane 0.20 mm from the slot wall). `tools/AsarX1Lib2.pas` made them simple 1.71 x 1.01
  obrounds on every layer; X1 updated on the board from the library (X1 ticked alone).
- **M1/F3** the courtyard sat on Mechanical 2, which this board names "Route Tool Path" (router kind): moved to
  Mechanical 7 (the other parts' courtyard layer); the slot-end arcs went to Mechanical 3 and now cap the slots.
- **C1/C5** D+/D- re-routed as a coupled pair (`tools/route/x1microb/build2.py`, `FeatherCopper_X1MicroB2.pas`):
  0.2 mm straight exit from each pad (no 45-degree notch), 0.30 mm pitch down x 5.35/5.65 and along y 7.75/8.05,
  split in the last 0.83 mm; coupled 5.23 mm, lengths 7.71 / 7.99 mm, uncoupled about 1.6 / 2.0 mm (the board's
  DiffPairsRouting MaxUncoupledLength is 3.0 mm; DRC does not run that rule).
- **C2** leftover USB-CC2 copper that the ECO renamed to GND (two Top>L2>L3 laser stacks, 6.1 mm of L3): removed.
  New gate `tools/route/x1microb/padless.py` (pad-less components, planes not joining): 0.
- **C3** FLASH-D02 through via moved (17.45, 16.625) -> (17.35, 16.55), hole clear of R2-1's mask opening.
- **M3** assembly notes: hand-solder X1's legs with an iron, no selective mini-wave (bottom C149, GND/VU 0805,
  sits 0.23 mm from MH1's land). **E1** README and **E3** the sheet-1 X1 note corrected
  (`tools/x1_note_schematic.py`, netlist identical).

Accepted as is: M2 (X4's east leg to Q1-1's pad 0.26 mm, to Q1's ceramic body 0.46 mm; the 0.254 ComponentClearance
intent is met with 0.006 mm to spare); F1 (slot lands 1.71 x 1.01 vs the drawing's 1.60 x 0.90, for a 0.255 ring;
noted in the footprint description); C8 (VU current still passes the pre-existing single through via
(15.55, 14.225); add a second via if VU load on battery approaches 1 A); E4 (the schematic PDF in the project folder
is stale since 2026-11-11 and ships nowhere: re-export before sharing it); E5/F5 (X1 keeps the old symbol name
MINI-USB-105017-0001 as LibReference).

Fix re-check (workflow wf_58d35417-4fd, measured from the saved board, Gerbers and drills): all fixed, no
regressions; full stream diff against f279d785 shows only the intended changes. L5 plane now 0.331 mm from the slot
wall (was 0.201); D+/D- coupled 5.9 / 5.7 mm, uncoupled 1.8 / 2.3 mm; pad-less copper 0; R2-1 hole 0.070 mm outside
its mask opening (VIA_IN_PAD list 107). Note: rule Clearance_Plane_NPTH (scope Name = 'X1-') matched the old USB-C
pegs and now matches nothing; the X1 slot lands are held off the planes by the 3 mil rule like every plated pad.

Final board: MD5 **295cdfc5ca320eb5b5b22b1378366655**, SHA-256 2B762CD8...12E9576FB, saved 13:53:43.
**DRC 0 / 0** (`docs/drc_x1_microb.drc`, 13:54:05), 0 open connections, sch_vs_board MATCH, 1168 lasers marked.

## Outputs

Gerbers 13:55 + NC drill 13:56 regenerated (split plated / non-plated, G85 slots, as the previous release: those
two options had reset after the Altium restart and were re-ticked, now saved with the board). Drills: 156 through,
2 X1 slots (0.50 tool), 4 NPTH (mounting), 252 buried, 1168 lasers.
`tools/package_fabrication_release.py` and `tools/generate_pcbway_assembly.py` retargeted (counts, hash, X1 notes,
panel note: X1 overhangs the left edge, keep it free of tabs). Both PASS:
`fabrication/Asar_Feather_PCBWay_Fabrication_2026-11-17_PROVISIONAL.zip`,
`assembly/Asar_Feather_PCBWay_Assembly_2026-11-17_PROVISIONAL.zip`. Do not upload them before the order questions
below are settled.

## Open

- PCBWay: plated 0.50 x 1.20 mm slots with 1.71 x 1.01 lands; the routed gap along X1's overhang in the panel.
