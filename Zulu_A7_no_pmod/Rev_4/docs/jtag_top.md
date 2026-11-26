# Zulu_a7_no_pmod Rev 4: JTAG row above X3, X3 to the west edge, BTN back home (2026-11-25)

This change starts from the Rev 4 3M-microSD board (md5 ab1a0f97, backup `backups/Zulu_a7_no_pmod.PcbDoc.pre-jtag-top`).
It ends at md5 904c5244 (saved 2026-11-25 17:54), with DRC 0 violations and 0 warnings (`docs/drc_jtag_top.drc`).
The follow-up BTN centring at the end of this note takes the board to md5 a2653692.

The user chose a through-hole JTAG header placed on top of X3, with X3 pushed to the left edge and BTN back in its
Rev 3 central position.

## Moves

| Part | Before | After |
|---|---|---|
| X3 | origin (10.60, 12.70) | (8.90, 12.70): 1.70 mm west. G1 copper sits 0.50 mm from the west edge; the lock housing face is 0.80 mm inside it. |
| JP4 (TDI, TDO, VCC3V3) | column on the west edge, rot 90 | rot 0. Holes at x 1.26 / 3.80 / 6.34, y 21.00. |
| JP3 (TCK, TMS, GND) | column on the west edge, rot 90 | rot 0. Holes at x 8.88 / 11.42 / 13.96, y 21.00. |
| BTN | (20.60, 5.20) rot 0 | (18.00, 12.92) rot 90 (Rev 3 position); then centred at (18.475, 12.92), see the end |
| C158 | x 18.70 | x 18.10 (Rev 3) |
| C11, C12, R35 (bottom) | y 21.39 | y 22.34 |
| C13 (bottom) | (2.60, 21.44) | (2.15, 19.59) |
| R34 (bottom, 4x array) | centre (12.22, 19.29) | centre (14.42, 18.39), turned +90 |

The two 1x3 headers form one 1x6 row on the X2 2.54 mm grid, directly under X2 pins 20-15 (1V0 ... C12). The pin
order is TDI TDO VCC3V3 TCK TMS GND, west to east.

The y = 21.00 row places the pad bottom 0.29 mm above X3's copper-prohibition strip (x 3.40..16.30, y 19.35..19.95)
and the pad top plus mask 0.30 mm below the X2 label silk.

## Why these sites for the bottom parts (`tools/route/jtag_top/sites.py`)

The row displaces five bottom parts, and two sites were searched. The west site (chosen) moves each part 2.4 mm or
less. The east site needed U10 moved 9.7 mm.

C11-C13 are 43-48 mm from the flash and socket supplies they decouple either way. They are plane-connected (L2 GND /
L5 3V3), so their position does not matter electrically.

## Routing

1. `tools/route/jtag_top/prep.py` ripped 99 tracks and 43 vias, leaving 49 opens on 18 nets. It rips:
   - copper feeding the old pads;
   - other-net copper too close to the new pads (through holes on every layer, plus the 0.24 mm hole-hole rule);
   - any same-net through via under a new SMD pad;
   - copper in the shifted X3 keepouts.
2. `router.py` routed 49/49.
3. The plan removes 153 tracks and 68 vias, adds 213 tracks and 69 vias, and makes 10 moves. route_check PASS; judge
   0 new DRC.
4. `tools/FabBCopper_JtagTop.pas` applied it, followed by microvia marking, repour and rebuild.

## DRC fixes after the move (`tools/NoPmodJtagFix.pas`, `tools/NoPmodBtnLabel8.pas`)

- **Bottom lands:** JP3/JP4 pads now use a local stack, with a 1.30 mm Bottom land (ring 0.142 mm) and 1.524 mm on Top
  and the inner layers. This cleared 7 bottom mask slivers against C11, C12, C13, C149 and R35.
- **Hidden designators:** X3 and R34 designators are hidden. They sat on the JTAG pads (top) and on JP3-3 (bottom).
- **BTN label:** at rotation 0 and (16.935, 9.065), clear of X3 G3 and the X3 silk.

## Verified on the saved file (route_model re-read)

| Check | Result |
|---|---|
| Opens | 0 |
| Microvias | 1316 (unchanged) |
| X3 keep-out strip | no copper |
| Nearest through via to X3 G1 | 0.905 mm |
| Through vias in SMD pads | only U2-EP and X4-2 (as before) |
| JTAG holes | at the positions and nets above |

**Body gate:** 0 fail and 18 warnings. The 3 new warnings are C11, C12 and R35 pad 2, each 0.07 mm from the X2
pins 11-20 bottom housing outline. They are the same kind as Rev 3's fifteen 0.06 mm warnings, and the headers ship
loose.

## Notes

- **Fitted JTAG header:** if a standard 2.54 mm 1x3/1x6 header is soldered on top, its plastic (2.54 mm wide,
  y 19.73..22.27) clears the X3 shell model (north edge y 19.70) by only 0.03 mm. It fits, but leave the header
  unfitted, or use a pogo/clip programming adapter, if a tighter fit matters.
- **Library mismatch:** the board-only 1.30 mm bottom lands on JP3/JP4 are not in the `1X03-NOSILK` library
  footprint. Re-applying it from the library would undo them; re-run `NoPmodJtagFix.pas` after any library update.
- **Unchanged:** the schematic, XDC and BOM (placement only).
- **Release:** the Rev 4 release (Gerbers, fabrication and assembly packages) is not built yet.
- **Illustrations:** `docs/board_illustration_top.png` and `_bottom.png` are redrawn from the final board
  (`tools/board_illustration.py`, RELEASED_MD5 a2653692).

## Follow-up: BTN centred between X3 and the LEDs (2026-11-25)

After the X3 move, BTN's body (16.40..19.60) sat 0.40 mm from the X3 shell (x 16.00) but 1.35 mm from the LED pads
(x 20.95). The user asked for it centred.

- **Move:** BTN +0.475 mm east to (18.475, 12.92), rotation 90. Its body now spans x 16.875..20.075, leaving 0.875 mm
  each side. The BTN designator follows to (17.410, 9.065) (`tools/NoPmodBtnLabel9.pas`).
- **Rip and route:** `tools/route/btn_centre/prep.py` ripped 6 tracks and the 4-via VCC3V3 microvia stack under
  pad 2, on N$BTN, PWR_PGOODALL and VCC3V3. The router laid 11 tracks and the same stack under the moved pad 2
  (Top-L2-L3-L4-L5, laser via-in-pad as before). route_check PASS; judge 0 new DRC.
- **Apply:** `tools/FabBCopper_BtnCentre.pas`, then mark_microvias (3 marked, 1316 verified), repour and rebuild.
- **Result:** board md5 a2653692 (saved 18:06), DRC 0/0 (`docs/drc_btn_centre.drc`), opens 0, microvias 1316.
  Tracks went from 6171 to 6176; vias stay at 2037. Body gate is unchanged at 18 warnings with no new ones.
- **Backups:** `backups/Zulu_a7_no_pmod.PcbDoc.pre-btn-centre` (904c5244) and `.btn-centre-final`.
