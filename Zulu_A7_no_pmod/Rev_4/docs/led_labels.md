# Zulu_a7_no_pmod Rev 4: LED function labels (2026-11-26)

The user asked for small Top silkscreen labels: LD0 by LD0, LD1 by LD1, LD2 by LD2, PWR by LD3, CHRG by LD4, DONE
by LD5 and RXTX by LD6.

## Size

The labels use 0.8 mm height and 0.15 mm stroke, the board's X2 pin-label size. That is the smallest silk already on
the board, and PCBWay has accepted it. Smaller stroke text prints as blobs.

## What fits

`tools/route/led_labels/find_spots.py` searched for legal spots. Each label has to:
- keep 0.26 mm from every pad and every printing silk object (board rules: Silk To Solder Mask 0.254 mm and Silk To
  Silk 0.254 mm);
- stay off part bodies;
- sit nearer its own LED than any other LED.

Silk may cross vias, because every via is tented or plugged (FAB_NOTES "VIA TENTING").

| Label | LED | Result |
|---|---|---|
| LD0 | LD0 | Placed below LD0: (19.500, 6.835), rotation 0 |
| CHRG | LD4 | Placed above LD4: (20.525, 18.385), rotation 0 |
| RXTX | LD6 | Placed east of LD6: (37.900, 17.100), rotation 90 |
| LD1, LD2, PWR (LD3), DONE (LD5) | Middle of the LED column | No legal spot, not placed (user choice) |

The middle LEDs sit at a 1.6 mm pitch with 0.7 mm gaps between their pads. West of the column, BTN's body is
0.875 mm from the LED pads. East of the column, the strip between the cathode dots and U2's pads is 1.03 mm wide.
None of the four labels has a spot at 0.8, 0.6 or 0.5 mm. The user turned down one-letter tags and a layout rework.

RXTX first went above LD6 at (35.725, 20.800). There it ran into X2's pin-name row beside "C7" and read as a pin
name, so `tools/NoPmodRxtxLabelMove.pas` moved it to the spot east of LD6.

## Applied

- Scripts: `tools/NoPmodLedLabels.pas` added the free Top Overlay texts, then `tools/NoPmodRxtxLabelMove.pas` moved
  RXTX.
- Board: md5 5349dc06, saved 08:54.
- DRC: 0 violations (`docs/drc_led_labels.drc`).
- The labels were read back from the saved file.
- `board_illustration.py` RELEASED_MD5 was updated and the illustrations re-rendered. The illustration's bold font
  draws the labels larger than they print.
- Backup: `backups/Zulu_a7_no_pmod.PcbDoc.led-labels`.
