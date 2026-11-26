"""Rev_4, 2026-11-26 (user request): swap the LED colours. LD1/LD2 (user LEDs, sheet 2) red -> green and
LD3/LD4 (LTC3556 power good / charge, sheet 1) green -> red.

Both parts are Lite-On LTST-C191 AlInGaP 0603s on the same LED0603 land, with the same ~2.0 V typical Vf
(KRKT red 631 nm, KGKT green 571 nm). The swap changes no resistor and no net:
- LD1/LD2 through R83/R84 330R: (3.3 - 2.0)/330 = 3.9 mA (4.2 mA as red);
- LD3 through R107 680R: ~1.9 mA, unchanged;
- LD4 through R108 1.0k from VU: ~1.6 mA typical, unchanged.

Only parameter text changes: Comment, MANF#, SPEC and, on LD1/LD2, the NOTE, which explained the old choice.
No record is added or removed, so the header Weight stays. Refuses to run twice; read back and verified.

    python tools/led_colour_swap_sch.py      (then reload sheets 1 and 2 in Altium and run the ECO)
"""
import os
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Imported zulu_a7.PrjPcb')

USER_NOTE = ('User status LED, driven straight off an FPGA pin through {r} at 330R: (3.3 - Vf)/330 is 3.9 mA green, '
             '4.2 red, 3.6 yellow, and 1.2 mA blue or white. Any of the first three is comfortable and well inside an '
             'LVCMOS33 pin\'s 12 mA. Green since 2026-11-26 (user choice; red before). The colour is a preference, not '
             'a constraint. LD3 (power good) and LD4 (charging) are red, so the user LEDs and the status LEDs read '
             'differently at a glance. Same LTST-C191 family and 0603 land as LD3-LD6.')

EDITS = {
    'zulu_a7_2.SchDoc': {
        'LD1': {'Comment': ('red', 'green'), 'MANF#': ('LTST-C191KRKT', 'LTST-C191KGKT'),
                'SPEC': ('red indicator, 0603, Vf 2.1V max at 4mA', 'green 571 nm indicator, 0603, Vf ~2.0V at 4mA'),
                'NOTE': (None, USER_NOTE.format(r='R83'))},
        'LD2': {'Comment': ('red', 'green'), 'MANF#': ('LTST-C191KRKT', 'LTST-C191KGKT'),
                'SPEC': ('red indicator, 0603, Vf 2.1V max at 4mA', 'green 571 nm indicator, 0603, Vf ~2.0V at 4mA'),
                'NOTE': (None, USER_NOTE.format(r='R84'))},
    },
    'zulu_a7_1.SchDoc': {
        'LD3': {'Comment': ('green', 'red'), 'MANF#': ('LTST-C191KGKT', 'LTST-C191KRKT'),
                'SPEC': ('green -- LTC3556 PGOODALL: all three rails good (lights 230 ms after VCC3V3 is up)',
                         'red -- LTC3556 PGOODALL: all three rails good (lights 230 ms after VCC3V3 is up)')},
        'LD4': {'Comment': ('green', 'red'), 'MANF#': ('LTST-C191KGKT', 'LTST-C191KRKT'),
                'SPEC': ('green -- LTC3556 CHRG: on = charging, off = done / no USB, fast blink = bad battery',
                         'red -- LTC3556 CHRG: on = charging, off = done / no USB, fast blink = bad battery')},
    },
}


def main():
    for sheet, parts in EDITS.items():
        path = os.path.join(ROOT, sheet)
        raw = read_stream(path)
        recs = split(raw)
        assert join(recs) == raw
        refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
        done = set()
        for i, (h, b) in enumerate(recs):
            if field(b, 'RECORD') != '41':
                continue
            ref = refs.get(owner(b))
            name = field(b, 'Name')
            if ref in parts and name in parts[ref]:
                old, new = parts[ref][name]
                cur = field(b, 'Text')
                if old is not None and cur != old:
                    raise SystemExit('%s %s %s is %r, expected %r -- already applied?' % (sheet, ref, name, cur, old))
                recs[i][1] = set_field(b, 'Text', new)
                done.add((ref, name))
        want = {(r, n) for r, ps in parts.items() for n in ps}
        assert done == want, (sheet, sorted(want - done))
        blob = join(recs)
        write_stream(path, blob)
        assert read_stream(path) == blob
        print('%s: %d parameters changed' % (sheet, len(done)))


if __name__ == '__main__':
    main()
