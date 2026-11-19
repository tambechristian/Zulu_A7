# Zulu_a7_no_pmod Rev 2: PCBWay fabrication and assembly release (2026-11-13)

## 1. Through vias taken out of SMD pads

The first fab-output check found 5 through vias (0.35/0.20) with their lands in SMD pads, against the rule of 2026-11-11
(`docs/ltc3556.md`: no through via in an SMD pad; microvias in pads are VIPPO). None came from the series resistors:
R108-1, R108-2 and C78-1 came from the JTAG-column move, R24-1 and R4-6 from the resize. User decision 2026-11-13:
move them out.

Plan `tools/route/vip2/plan.json`, from `tools/route/vip/move_thru_vias.py` (the Fab B planner, unchanged) and
`tools/route/vip2/make_plan.py`:

| Pad | Net | Action |
|---|---|---|
| R108-1 (Bottom) | VU | via 0.250 mm east to (5.875, 13.150); jumpers Top 0.40, Bottom 0.20 |
| R108-2 (Bottom) | LD4_A | via 0.372 mm to (6.125, 13.700); jumpers Top 0.0762, Bottom 0.15 |
| C78-1 (Bottom) | GND | via 0.300 mm south to (2.200, 13.975); jumper Bottom 0.15 |
| R24-1 (Bottom) | CLK-12M-SHARED | via 0.175 mm north to (59.200, 21.525); jumpers L3 0.0762, Bottom 0.15 |
| R4-6 (Top) | TCK | no legal spot within 1.5 mm: replaced in place by a Top>L2 + L2>L3 microvia + L3>L4 buried stack (TCK has copper only on Top and L4), as Fab B's stacks |

The planner also flagged C161-1's GND via at (4.8, 16.6). That is a bounding-box artefact: the land only meets the
corner of C161's rounded pad box. Fab B accepted the same via, so the plan leaves it. On the saved board the R24-1 and
C161-1 lands are tangent to their same-net pads (gap 0.000 mm, hole 0.075 mm from the pad edge); neither overlaps.

Gates before Altium: route_check 0 violations / 0 open; width check 0; the Rev 2 judge (`tools/route/rev2/judge/
judge.py`): 0 emit problems, 0 new DRC findings, 0 through vias in SMD pads, 1 new microvia in a pad (TCK, R4-6);
prune_stubs 0 dead; route_conn 0 open; planeweb: both pours one island, unchanged.

Applied with `tools/FabBCopper_NoPmodViaOutOfPad.pas` (`emit_copper.py`): "removed 0 tracks and 5 vias, placed 7 vias
and 7 tracks". `mark_microvias.py --laser 0.30/0.15 --expect 1204` marked the 2 new laser vias. Re-poured
(`NoPmod_Repour`), ratsnest rebuilt (0 connections). **Batch DRC 2026-11-13 19:49:56: 0 violations, 0 warnings**
(`docs/drc_via_out_of_pad.drc`). Board saved 19:49:42, **md5 36f559b4**, SHA-256 FC2DCDB7.... A fresh extract equals the
plan's result exactly (0 track and 0 via differences). Backups: `backups/Zulu_a7_no_pmod.PcbDoc.pre-via-out-of-pad`
(c88d7ac6) and `.via-out-of-pad-pre-microvia`.

Via counts: through 342 -> 341, Top-L2 318 -> 319, L2-L3 303 -> 304, L3-L4 buried 402 -> 403; microvias 1204.

## 1b. Second pass: 0.025 mm clearance for the moved lands (same day)

An independent review of the first release (own PcbDoc parser with real pad shapes) found the four moved vias
exactly tangent to their pads, and R108-1 / R108-2 overlapping by 0.01-0.04 um: the Fab B planner accepts a land-to-pad
gap of 0.0. `move_thru_vias.py` now reads `VIP_PAD_GAP` (default 0.0, Fab B behaviour unchanged); re-planned from the
same pre-move board with `VIP_PAD_GAP=0.025` (`tools/route/vip2/plan1b.json`), and `tools/route/vip2/make_delta.py`
turned it into a delta against the placed board (`delta.json`: remove the 4 vias and 7 jumpers, place 4 + 7):

| Pad | First pass | Second pass (moved from the in-pad point) |
|---|---|---|
| R108-1 VU | (5.875, 13.150) | (5.900, 13.150), 0.275 mm |
| R108-2 LD4_A | (6.125, 13.700) | (6.100, 13.700), 0.395 mm |
| C78-1 GND | (2.200, 13.975) | (2.200, 13.950), 0.325 mm |
| R24-1 CLK-12M-SHARED | (59.200, 21.525) | (59.200, 21.550), 0.200 mm |

Gates: route_check 0/0, width 0, judge 0 emit problems / 0 new DRC / 0 through vias in pads, prune 0, route_conn 0,
planeweb unchanged. `FabBCopper_NoPmodViaClear.pas`: "removed 7 tracks and 4 vias, placed 4 vias and 7 tracks" (no
laser vias, no marking). Repour, ratsnest 0, **DRC 2026-11-13 20:10:17: 0/0** (`docs/drc_via_clear.drc`). Board saved
20:10:09, **md5 00989c86**, SHA-256 1B58837C...; extract equals the plan result exactly. Backup of the first pass:
`backups/Zulu_a7_no_pmod.PcbDoc.pre-via-clear` (36f559b4). Gerbers 20:11:08, NC drill 20:11:44 (G85).

The 10 through-via lands still tangent to a same-net pad (C147-1, C149-1, C151-1, C160-1, C161-1, R102-2, R103-2,
R114-2, U7-2, X3-G2) are Fab B Rev 2's vias at Fab B's positions (Fab B's note listed them as "land abuts the pad");
their holes are 0.075 mm outside the pads. They stay; the note now lists them.

The review's note findings were all taken: `fab_facts.py` gained `through_via_lands_abutting_smd_pads`,
`mask_over_microvias` (18 microvia lands partly inside a same-net opening, hole margins down to 0.015 mm),
`unstacked_outer_microvias` (55), `different_net_projected_hole_overlaps` (7, two coaxial; the resistor doc's "one
fully coaxial" was wrong), `usb_coupled_overlap_by_gap` (11.44 mm true overlap, not 11.79) and `copper_to_edge`
(from the copper Gerbers: planes 0.25 mm from every edge, signal copper 0.262 mm from the long edges, 0.338 west,
0.310 east). `fab_notes.py` uses them: tangent-land list, microvia mask list, "fill and cap all 1,204 microvias",
measured panel edge distances, courtyard overlaps in EQ 1, all 7 projected overlaps in EQ 3. Left as is: the LDP's
first line carries Altium's absolute output path (Fab B's LDP has the same).

## 1c. R108 moved out from under L9 (same day, user request after the release review)

The 4-lens release review (workflow wf_bafc3504-ec1) found R108 (0402, Bottom, VU -> LD4_A) at (6.0, 13.475), between
L9's pads and under its 2.5 x 2.0 x 1.2 mm molded body, since the JTAG-column move (Fab B has it at x 1.9-3.2, now the
JTAG column). Site search (every Bottom/Top site within 8 mm; pad boxes + 0.10 mm courtyard clear of every other part's
pad extent, 0.09 mm to other-net copper): nearest legal Bottom site (3.40, 17.80), rotation 180, pad 1 (VU) east on the
VU 0.40 mm Bottom track, pad 2 (LD4_A) west. The Top sites were rejected (north of the microSD socket). A first choice,
(3.0, 18.35) vertical, would have put pad 2 on that VU track: the judge caught the short (the site search checked the
flipped orientation against the wrong net; fixed).

`tools/r108_move_prep.py` (move + dead copper: the old jumper vias, their stubs, and the VU triangle at (5.9, 13.15) that
prune_stubs cannot see) -> `router.py` (LD4_A: L5-Bottom + L4-L5 microvia stack in R108-2's pad, L4 0.0762 mm to the
existing LD4_A through via at (3.70, 13.83)) -> `compose_plan.py` (now takes explicit pad positions for a turned part)
-> route_check 0/0, width 0, judge 0 new DRC / 0 through vias in pads, prune 0, route_conn 0, planes one piece.
`tools/FabBCopper_NoPmodR108.pas` (`emit_copper.py` gained `rotation` and a pad-1 position check): "Moved 1 parts,
removed 7 tracks and 2 vias, placed 2 vias and 2 tracks". Saved board = plan exactly; mark_microvias --expect 1206;
repour; ratsnest 0; **DRC 2026-11-13 21:12:52: 0/0** (`docs/drc_r108_move.drc`). **Board md5 24de4472**, SHA-256
CD502C40...; backups `backups/Zulu_a7_no_pmod.PcbDoc.pre-r108-move` (00989c86), `.r108-pre-microvia`.
Gerbers 21:13:50, NC drill 21:14:32 (G85).

Via counts: through 341 -> 339, L4-L5 281 -> 282, L5-Bottom 300 -> 301 (microvias 1206); via-in-pad 84 sites
(R108-2 added, VIPPO).

Release review fixes folded in at the same time (fab_facts.py, fab_notes.py, generate_jlcpcb_assembly.py, packager):
every mask opening per via listed (24 contacts on 21 through vias, 20 on microvias) with the copper gap to that
opening's own pad; 9 vias / 10 contacts for the tangent lands; 56 unstacked microvias (incl. one dead L4-L5 at
(26.7, 11.8), N$LD1A, left as is); EQ 2 now gives the board-wide mask cover (min 0.020 mm, 69 track/opening pairs
under 0.044 mm, after a second review caught a reach filter that skipped opening corners; U2-48 is 0.025, not 0.044 as decision 15 said); EQ 3 lists drill pairs without the lamination claim;
CHANGES lists every part placed differently from Fab B Rev 2 and the TCK stack; "hole sizes are finished sizes";
USB coupled length explained against Fab B's 11.79; assembly notes list all 84 via-in-pad sites on 40 parts and point
the U1 vias at the fab note's plug-all request; the packager scans every archived byte for the order number.
Not added (user's call): IPC-6012 class, electrical test, VIPPO dimple limit.

## 2. Fabrication release

- (first pass) Gerbers exported 19:51:38, NC drill re-exported 19:57:18 with **"Use drilled slot command (G85)" ticked**: this
  project's NC Drill setup had it off, so the first export wrote X1's slots as routed G00/G01 paths. The G85 file is
  byte-identical to the committed one.
- `tools/fab_facts.py` on the saved board: drill_vs_board 0 missing / 0 extra in every file, 0 through vias in SMD
  pads, 83 via-in-pad sites (all microvias; Fab B's 68 + the 7 series-resistor pads + R4-3, R4-5, R4-6, R24-2,
  R90-2, R92-1, R99-1, R99-2).
- `tools/fab_notes.py` (new) writes `fabrication/Zulu_A7_no_pmod_Rev_2_PCBWay_FAB_NOTES.txt` from fab_facts.json, so
  every board number in the note is measured. It adds the EQ questions of decisions 9, 12, 14, 15 and the CHAN7 /
  SDRAM-D14 advisory (`docs/dq_series_resistors.md`), and words the panel as a proposal.
- `tools/package_fabrication_release.py` retargeted (hashes, outline 60.96, drill counts, release name/date):
  **NO_PMOD_REV_2_PCBWAY_FABRICATION_RELEASE PASS** (last rebuilt on board 24de4472, after the R108 move), `fabrication/Zulu_A7_no_pmod_Rev_2_PCBWay_Fabrication_2026-11-13.zip`
  (23 entries).

## 3. Assembly release

`python tools/generate_jlcpcb_assembly.py` (retargeted to this board): **ASSEMBLY_RELEASE PASS**, 67 BOM lines,
`assembly/Zulu_A7_no_pmod_Rev_2_PCBWay_*`. Regenerated after the via moves: BOM, CPL and both drawings are
byte-identical to the first run; only the notes' PCB hash line changed.

The Fab B Rev 2 files in `fabrication/` and `assembly/` are left as they were.

## 4. Second review (workflow wf_2d86126f-fca, after the R108 move)

R108: every check passed (board diff = exactly the plan; VU / LD4_A one island each; drills, Gerbers, CPL and the bottom
drawing agree; L9's body clear). Tightest new margin: R108-1 (VU) to the GND through via at (4.600, 18.425), 0.0908 mm
against 0.09; R108's courtyard touches C78's (pad to pad 0.20 mm). Fixed from that review: the mask-cover reach filter
(EQ 2: min 0.020, 69 pairs, not 0.022 / 30), the via-in-pad new-site list (now computed against Fab B: 16 pads incl.
R108-2), CHANGES (two surviving moved vias, C78-1 and R24-1; the R108 vias went with R108), the assembly notes (84 sites
on 83 pads), a copper-gap column for the microvia tenting rows, and the packager now holds the order number only as a
SHA-256 (the literal was in the public repo's history since 31df8a8; that history is not rewritten).
