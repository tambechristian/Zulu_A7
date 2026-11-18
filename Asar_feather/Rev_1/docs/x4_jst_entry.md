# X4 (LiPo JST) against the Adafruit Feather reference (2026-11-16)

Question: is X4 laid down (side entry, cable parallel to the board) like on Adafruit Feathers? **No.**

## What X4 is today
- Part: JST **B2B-PH-SM4-TB**, the TOP-entry (vertical) PH header.
  - JST's model key reads 'B' = top entry and 'S' = side entry (ePH.pdf p.5).
  - Body height 6.6 mm; mated height (8.6) mm with the plug inserted from above (ePH.pdf p.2, p.4).
- Footprint: exactly JST's top-entry recommended land, turned 180 degrees.
  - Pads 1 and 2: 1.0 x 5.5 at (9.8, 17.75) and (11.8, 17.75).
  - Fixing tabs: 1.6 x 3.0 at (7.4, 20.0) and (14.2, 20.0).
- Position: centre x 10.80 mm, which is the Feather spec's 0.425 in from the left edge. The orientation is what differs.

## Adafruit Feather reference
Checked in Adafruit's own Eagle files: M0 Basic rev C, 32u4 Basic rev B, M4 Express, RP2040, ESP32-S2 rev C, ESP32-S3 and nRF52840 Sense rev C.
- Part: a side-entry SMT JST-PH clone, package "2-Pin JST PH Series Right-Angle Connector".
  - The RP2040 BOM carries LCSC C47647 (BOOMELE PH-2P, right angle).
  - The genuine JST equivalent is **S2B-PH-SM4-TB**: 5.5 mm tall, lying flat.
- Placement: Top side, rotation 0, origin about (10.8-10.9, 19.3).
  - The mouth faces +y, out of the long top edge. The front face is about 0.56 mm inside y = 22.86.
  - The fixing tabs are on the mouth side and the signal pads at the back.
- Polarity:
  - VBAT is the EAST pad, about x 11.8-11.9. The RP2040 and nRF52840 have a '+' in silk beside it.
  - GND is the WEST pad, nearer the USB.
  - Looking into the mouth with the board top side up, + is on your LEFT.
- Adafruit's Eagle pad names are the reverse of JST's numbering (their pad 1 = GND, pad 2 = VBAT).
  - By JST's own 'No. 1 circuit' marks (ePH.pdf p.2, p.4), Adafruit's VBAT pad is **JST circuit 1**.

## Polarity on Asar
- Asar wires JST circuit 1 = VBATT and circuit 2 = GND. The PH plug is keyed, so polarity follows the circuit number.
  - An Adafruit LiPo should therefore put + on VBATT on the present top-entry X4, and on a side-entry one with circuit
    1 = VBATT.
  - This is **deduced**: no Adafruit document states it in JST numbers. Meter one real Adafruit cell before first
    power-up.
- On a side-entry footprint with the mouth facing +y, circuit 1 (VBATT) is the **EAST** pad. That is the opposite
  side to today's X4. Do not copy Adafruit's "pin 1 = GND" netlist onto a JST-numbered footprint.

## What a side-entry X4 at the Feather spot needs
Measured with `tools/fab_facts.py read_board` on board f8dba4ec. Scripts and output are in the session scratchpad:
`jst/site/sites.py`, `detail.py`, `sites.txt`.

S2B land (JST minimum):
- Signal pads 1.0 x 3.5, from 5.5 to 9 mm behind the mating face.
- Tabs 1.5 x 3.4 at +-3.35, reaching 0.2 mm past the face.
- Body 7.9 x 6.

At the Adafruit position (face at y 22.304, centre x 10.795):
- **U10** (93LC46B, TDFN-8, Top, (11.0, 13.75)) sits under both new signal pads, with overlaps of 0.25-0.355 mm.
  - It must move. It cannot slide south, because U2's north pin row reaches y 12.2.
  - Its EE-DATA / EE-CLK fan-out moves with it.
- **VU** 0.4 mm Top track along y 21.825 crosses both tab lands. Its two Top-Bottom vias at (6.575, 21.825) and
  (14.775, 21.825) sit in the tabs.
- **VBATT** Top feed crosses the new GND (west) pad. It has to reach the east pad instead.
- **GND** Top-L2 via at (11.425, 16.925) sits under the new VBATT pad.
- Same-net vias under the new pads become via-in-pad unless they move: VBATT at (11.6, 14.725) and (11.15, 14.725);
  GND at (9.85, 14.425) and (9.225, 14.4).
- Margins:
  - X1 shell slot MP1 copper is 0.004 mm from the S2B body's rear edge; X1's moulded body is 0.404 mm away.
  - Q1 is 0.204 mm away.
  - X2-17 is 0.665 mm from the east tab.
  - The mounting hole is 2.8 mm away.
  - Tab copper is 0.36 mm from the board edge. That needs PCBWay's copper-to-edge minimum, which is not checked.
- Rejected sites:
  - Bottom side: U8 (LTC3556), L1, L9 and others are under it.
  - West short edge: the 2.5 mm mounting hole is inside the body, and the tab runs off the board.

Verdict: it fits after U10 is moved and the copper listed above is re-routed. After that the board needs DRC, the
fab outputs and both PCBWay packages again.

Sources:
- JST PH catalogue: https://www.jst-mfg.com/product/pdf/eng/ePH.pdf (p.2 land patterns, p.4 header tables, p.5 model key).
- Adafruit Feather spec: https://learn.adafruit.com/adafruit-feather/feather-specification
- Adafruit PCB repositories on GitHub (adafruit/Adafruit-Feather-*-PCB): the .brd/.sch files and lines are recorded
  in the workflow journal wf_8942fbaa-e52.

## Conversion done (2026-11-16, user: "Yes, convert")
Board `asar_feather.PcbDoc` saved 15:31:03, MD5 5a39625c, SHA-256 2029B59E...54A6BA. DRC 0 violations, 0 warnings
(`docs/drc_x4_side_entry.drc`). Not committed (Rev_1 is untracked).

What changed:
- **X4 = JST S2B-PH-SM4-TB(LF)(SN)**, footprint `JST-S2B-PH-SM4-TB` (asar_feather.PcbLib).
  - Origin at the housing centre, mouth toward +y.
  - Pads 1/2 are 1.0 x 3.5 at x +1.0/-1.0, y -4.25. Tabs MP1/MP2 are 1.5 x 3.4 at x -/+3.35, y +1.5.
  - Placed at (10.8, 19.3) rot 0: the face is at y 22.30, 0.56 mm inside the edge, as on Adafruit Feathers.
  - **Pin 1 = VBATT is the EAST pad (11.8, 15.05)**, pin 2 = GND is the west pad (9.8, 15.05).
  - Tab copper is 0.36 mm from the top edge. X5's tabs (0.30) and L1 (0.31) were already closer.
- **U10 (93LC46B TDFN) moved to (5.45, 19.0) rot 0**, in the pocket west of X4's west tab, pins 1-4 facing south.
  - **Trade-off:** its body is about 1.9 mm from the centre of the top-left mounting hole. An M2.5 screw head or a
    standoff wider than about 3.8 mm would sit on U10's corner. Use a small nylon screw or standoff there, or mount from
    below.
  - The only other free site, east of the east tab, would have cut off the VBATT path to X2-17 (BAT).
- **Schematic** (sheet 1, `tools/x4_side_entry_schematic.py`):
  - X4's library reference, description, MANF#, SPEC, NOTE and footprint model changed.
  - The netlist is proven identical to the backup `backups/asar_a7_1_before_x4_s2b.SchDoc`.
  - The ECO applied only the 4 X4 changes. Unticked:
    - 15 design-item-ID syncs (C78, C80, C160, C161, C163-C167, R113-R118), which were pending before this change;
    - the 10 net-class removals and the USB diff-pair removal;
    - "add U7 to the asar_a7_1 component class".
- **Copper**: `tools/route/x4conv/` holds the record.
  - Files: `plan.json` md5 d028c890, `fix_plan.json`, the models, and the scripts `build.py`, `geom.py`,
    `combine.py`, `router_x4.py`, `npth_gate.py`.
  - VU's top-edge bridge (6.575-14.775 at y 21.825) crossed both tabs.
    - It was the only link between VU's two halves: L8/U8-24 on one side; the U8 buck inputs, U7, C148 and C149 on the
      other.
    - It is replaced by a 4 mm, 0.4 mm Top track at y 17.5 under X4's body, between the existing through vias
      (8.8, 17.5) and (12.775, 17.5).
    - The dead Bottom feed to the old east via and the via at (17.25, 16.425) were removed.
  - VBATT: X4-1 already lands on the existing VBATT via stacks (11.6/11.15, 14.725) to U8-23/C151.
    - The X2-17 (BAT) branch now reaches X4-1 on L3 at 0.3 mm. Altium's Width_PWR_U8 allows 0.2; the router's internal
      width table says 1.1 inner, so `route_check` flags it.
    - It uses Top>L2>L3 lasers at (11.375, 17.0) and (13.05, 18.9).
  - GND: three Top>L2 lasers in X4-2. The C148 GND through via moved from (5.65, 20.35) to (5.95, 21.13).
  - EE-CS/CLK/DATA/DATA-DO, and U10's VCC3V3/GND ties, were routed by the board router (`router_x4.py` = router.py with
    VBATT allowed on L3/L4).
    - Settings: `--clear 0.077 --slack 0.005 --rip 0`.
    - X1's non-plated pegs were inflated so every new track keeps >= 0.137 mm (rule 0.127); actual min 0.392.
    - X1's body was a Top keepout.
  - Totals: 30 tracks and 16 vias removed, 97 tracks and 29 vias added, 1 track shortened, 1 via removed; 23 new
    lasers.
  - Microvias marked (`mark_microvias.py --expect 1187`, 23 new) and verified.
  - Board: 4877 tracks, 1597 vias. A recount from the saved file matches the plan exactly, and the other 838 pads are
    unchanged.
- **Silk**:
  - X1's designator is hidden. A free Top Overlay "X1" (0.8 mm, 0.15 stroke) sits at (2.25, 17.35); the designator
    would not move by script.
  - U10's lone overlay tick is now a pin-1 mark at (4.15, 17.35-17.55).
- **Fab outputs**:
  - Gerbers 15:33:36, drills 15:34:24. Through holes 160 -> 157, buried 249 -> 253, lasers 1176 -> 1187.
  - Every Gerber layer is identical to the 11:28 export outside x 1.5-19.5, y 8.5-23.5.
  - Both PCBWay packages were rebuilt (PASS). The 11:58 pair is in `backups/*_npth-fix_superseded.zip`.

Altium traps found on this build (26.11.1):
- In a PcbLib script, `PCBServer.SendMessageToRobots(..., PCBM_BoardRegisteration, ...)` crashes ScriptingSystem.DLL
  right after the first pad. Without it, the new pads are not saved. What worked:
  1. Copy and paste the B2B footprint in the PCB Library panel.
  2. Rename the copy in the Properties panel.
  3. Move its existing primitives by script (`tools/AsarX4Morph.pas`).
- A board designator's XLocation write did not hold, even after ChangeNameAutoposition := eAutoPos_Manual.
- The computer-use `type` action pastes via the clipboard, and here it pasted the user's clipboard text instead. Type
  in chunks of 4 characters or fewer.

Not done (optional): no "+" silk mark next to X4 pin 1 (there is no room for PCBWay's 0.8 mm legend between X4-1 and
Q1); meter one real Adafruit pack before first power-up.

## STOP: the side-entry housing collides with X1 and Q1 (found by review, 2026-11-16 ~16:00)
An independent review (workflow wf_0ddcf5d7-2d3, three lenses) found that the conversion above is mechanically invalid.
- The S2B-PH-SM4-TB housing is not 7.9 x 6.0. Two side legs at |x| 3.15-3.95 reach **7.6 mm** behind the face. Sources:
  - JST ePH p.2 "connector outline" in the land drawing and the p.4 side view;
  - KiCad `JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal` F.Fab;
  - Adafruit's JSTPH2_BATT tDocu (legs to 7.5 mm).
  - The "6" in the p.4 side view is only the main block. The site study and the library outline (Mech3/Mech7 to y -3.0)
    used 6.0, so every margin quoted above against "the S2B body" is wrong.
- At (10.8, 19.3) the legs cover y 14.70-16.30, x 6.85-7.65 and 13.95-14.75:
  - **west leg:** X1's rear shell leg MP1 (USB-C, slot at 6.78, 15.75), X1 pin 5 and X1's body;
  - **east leg:** Q1 (12 MHz oscillator) pad 1 and body.
  - DRC cannot see this: the footprints have no 3D bodies.
- Why Adafruit fits: their USB-C (CUI CUSB31-CFM2AX-01-X) overhangs the left edge and ends near x 6.4. Asar's HRO
  TYPE-C-31-M-12 reaches x 7.9.
- Measured escape routes (legs vs other parts' pads and bodies, 0.1 mm margin):
  - Moving X4 east clears X1 only from x about 12.5, but tab MP2 then hits X2-17 (BAT) from x 11.46.
  - Moving it north clears everything only with the face at y 24.1, which is 1.24 mm past the edge. That leaves about
    1.7 of the 3.4 mm tab land on the board.
- Status: the board, outputs and packages built at 15:31-15:35 carry this collision. **Do not upload them.**
  - The verified top-entry state is still recoverable: board md5 f8dba4ec (Altium History `asar_feather.~(52).PcbDoc`),
    sheet `backups/asar_a7_1_before_x4_s2b.SchDoc`, and the release ZIPs `backups/*_npth-fix_superseded.zip`.
- The same review also found:
  - a 10.34 mm dead VU stub on Bottom: the west half of the old bridge, from C149-2 around the mounting hole to
    (2.889, 21.963), which DRC's antenna check missed;
  - a stale "U10 has no silkscreen polarity mark" sentence in the assembly notes.

## FT2232H-56Q swap studied (user suggestion, 2026-11-16 evening) - it does not help X4
Workflow wf_ff5f271e-d7a ran four agents: datasheet facts, U2 usage, placement chain, and an adversarial check of the
chain. Scratch outputs are in the session scratchpad `u2_56q/`.
- **FT2232H-56Q**: the same die in an 8 x 8 VQFN-56 (DS_FT2232H v2.10, sections 3.2 and 8.3).
  - All 44 signals are kept in the same order. Dropped: 1 VCORE, 1 VCCIO, AGND and 5 GND pins.
  - The 5.9 mm exposed pad is the main ground and must go to GND.
  - FTDI land (TN_166, section 25): 0.25 x 0.80 pads on a 0.5 pitch, pad-centre span 8.00, EP 6.10. The copper
    extent is 8.8 mm against today's 9.6.
  - Stock: DigiKey 0, 260 due 2027-03-16, 50-week lead time.
- **It does not help X4.** U2's land ends at y 12.2 and X4's legs start at y 14.7. A 56Q at the same centre leaves
  both collisions exactly as they are.
- **What does make X4 fit at the Feather spot** (two agents agree, checked at >= 0.20 mm against real pad shapes; U2
  untouched):
  - X1 moves 1.80-1.86 mm south. The USB-C ends up off-centre on the short edge.
  - LD4 moves 0.25-0.31 south and LD3 0.05-0.11 south.
  - Q1 moves 1.40-1.46 east.
  - C149 goes to (2.60, 15.50).
  - The 1V0 buck is re-laid out:
    - U7 to (3.30, 7.55) r270;
    - L3 to (2.40, 10.95) r90;
    - C78 to (4.55, 10.80) r270;
    - C84 0.10 south for the 0.26 mm variant.
  - Optional: U10 to (3.40, 15.75) r90, which removes the mounting-hole caveat.
  - About 20 nets are touched (roughly 120 foreign segments and 27 vias in the way).
  - Main risk: the 1V0 buck loop gets worse, with its output cap about 4.9 mm from the inductor.
  - The legs clear by only 0.20 mm (0.26 in the variant), against the ComponentClearance rule of 0.254.
- **Alternative:** a shorter or overhanging USB-C. Its rear copper and body must end at x <= 6.70; Adafruit's CUI
  CUSB31-CFM2AX-01-X ends near 6.4. That leaves only the Q1 move.
- **Pre-existing finding:** U2's exposed pad has NO net and no via, but FTDI requires it on GND (64-pin note 2). The
  56Q would make this worse. It is worth fixing on its own.
