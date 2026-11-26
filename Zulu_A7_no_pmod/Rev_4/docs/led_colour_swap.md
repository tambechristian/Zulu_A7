# Zulu_a7_no_pmod Rev 4: LED colours swapped (2026-11-26)

The user asked for LD1/LD2 green and LD3/LD4 red (previously the reverse).

| LED | Function | Was | Now | Series R | Current |
|---|---|---|---|---|---|
| LD1 | User LED (FPGA pin) | red LTST-C191KRKT | green LTST-C191KGKT | R83 330R | 3.9 mA (was 4.2) |
| LD2 | User LED (FPGA pin) | red LTST-C191KRKT | green LTST-C191KGKT | R84 330R | 3.9 mA (was 4.2) |
| LD3 | LTC3556 PGOODALL, all rails good | green LTST-C191KGKT | red LTST-C191KRKT | R107 680R | ~1.9 mA, unchanged |
| LD4 | LTC3556 CHRG, charging | green LTST-C191KGKT | red LTST-C191KRKT | R108 1.0k from VU | ~1.6 mA typ, unchanged |

Both parts are Lite-On LTST-C191 AlInGaP 0603s on the same LED0603 land with the same ~2.0 V typical Vf, so no
resistor, net, footprint or copper changes.

## What changed

- **Schematic.** `tools/led_colour_swap_sch.py` changed Comment, MANF# and SPEC on LD1/LD2 (sheet 2) and LD3/LD4
  (sheet 1), and rewrote the LD1/LD2 NOTE, which explained the old colour choice. No records were added. The netlist is
  identical before and after.
- **PCB.** ECO with Disable All, then only the 4 comment rows and the 4 parameter rows for LD1-LD4 enabled. The
  Design Item ID swaps, the Q1 comment, the JP descriptions, the other parameter rows, and the net-class, rule and
  room rows stayed off.
  - Board md5 ec5c0379, saved 2026-11-26 08:15.
  - The hidden PCB comments now read LD1/LD2 green and LD3/LD4 red.
  - Track geometry and nets are identical to 658cf76c. Altium re-ordered the records on save.
- **Tooling.**
  - `board_illustration.py` draws LD1/LD2 green and LD3/LD4 red (RELEASED_MD5 ec5c0379), and the illustrations
    were re-rendered.
  - The `bom_audit.py` LED row is updated.
  - `generate_jlcpcb_assembly.py` takes MPNs from the schematic, so the BOM lines become "LD1,LD2 LTST-C191KGKT"
    and "LD3,LD4 LTST-C191KRKT" with no code change. Both parts were already in its LCSC and description maps.

DRC was not re-run, because a hidden comment and parameters cannot change any rule result. The last DRC (0
violations) is on 658cf76c, and the Rev 4 release run will DRC this board.

Backups:
- `backups/zulu_a7_1.SchDoc.pre-led-swap`
- `backups/zulu_a7_2.SchDoc.pre-led-swap`
- `backups/Zulu_a7_no_pmod.PcbDoc.led-swap` (after the swap)

The pre-swap board is git 658cf76c.
