"""KiCad copy: X2 power pins re-ordered (2026-10-07), schematic side.

Same change as Zulu_Altium_VS_Code/tools/x2_power_pins.py on the Altium sheet:

    before  17 +3.3V (VCC3V3), 18 +1.8V (VCC1V8), 19 +1.0V (VCC1V0), 20 GND
    after   17 GND,            18 +3.3V,           19 +1.8V,           20 +1.0V

  * ZULU-CONN units 15/14/17/16 (gates +3.3V/+1.8V/+1.0V/GND) get pin numbers 18/19/20/17, in the
    schematic's embedded lib_symbols and in ctambe.kicad_sym;
  * each of those four placed units moves to the row of its new pin together with its global label
    (the four row wires are identical, so they stay);
  * the X2 NOTE (41 copies) and the sheet's text box are reworded as on the Altium sheet.
Guards make a second run stop. Text edits only; KiCad must not have the files open.

    python tools/apply_x2_pins_sch.py kicad_project
"""
import os
import re
import sys

PROJ = sys.argv[1]
SCH = os.path.join(PROJ, 'zulu_a7_2.kicad_sch')
LIB = os.path.join(PROJ, 'ctambe.kicad_sym')
ROWS = {17: 100.076, 18: 102.616, 19: 105.156, 20: 107.696}       # sheet y of each top-row pin, x 46.99
UNIT_OLD_NEW = {'15': (17, 18), '14': (18, 19), '17': (19, 20), '16': (20, 17)}   # unit: (old pin, new pin)
LABELS = {'VCC3V3': (17, 18), 'VCC1V8': (18, 19), 'VCC1V0': (19, 20), 'GND': (20, 17)}
TEXT_EDITS = [
    ('pins 10-20 (26.67..1.27) = CHAN7..CHAN13, +3.3V, +1.8V, +1.0V, GND, in channel order since 2026-09-09;',
     'pins 10-20 (26.67..1.27) = CHAN7..CHAN13, GND, +3.3V, +1.8V, +1.0V (channel order since 2026-09-09, '
     'power pins re-ordered 2026-10-07);', 41),
    ('Three grounds (1, 20, 21); 3.3 V for the header is pin 17 alone;',
     'Three grounds (1, 17, 21); 3.3 V for the header is pin 18 alone;', 41),
    ('then CHAN7..CHAN13 (10-16), +3.3V, +1.8V, +1.0V, GND (17-20).',
     'then CHAN7..CHAN13 (10-16), GND, +3.3V, +1.8V, +1.0V (17-20).', 1),
    ('THREE grounds: pins 1, 20, 21.  Pin 17 is the only +3.3V pin.',
     'THREE grounds: pins 1, 17, 21.  Pin 18 is the only +3.3V pin.', 1),
]


def fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return s


def renumber_units(t, where):
    """Pin number of each ZULU-CONN unit 14..17 in a lib symbol text."""
    for unit, (old, new) in UNIT_OLD_NEW.items():
        i = t.find(f'(symbol "ZULU-CONN_{unit}_0"')
        assert i >= 0, (where, unit)
        j = t.find('(symbol "ZULU-CONN_', i + 10)
        blk = t[i:j]
        nums = re.findall(r'\(number "(\d+)"', blk)
        assert nums == [str(old)], (where, unit, nums)
        t = t[:i] + blk.replace(f'(number "{old}"', f'(number "{new}"') + t[j:]
    return t


def shift_block(blk, dy):
    def rep(m):
        return f'(at {m.group(1)} {fmt(float(m.group(2)) + dy)}{m.group(3)}'
    return re.sub(r'\(at ([\d.\-]+) ([\d.\-]+)((?: [\d.\-]+)?\))', rep, blk)


def main():
    t = open(SCH, encoding='utf-8').read()
    lib = open(LIB, encoding='utf-8').read()
    # 1. pin numbers in the embedded lib symbol (the first block, before the placed symbols) and in the library
    ls = t.find('(lib_symbols'); le = t.find('\n\t)\n', ls)
    t = t[:ls] + renumber_units(t[ls:le], 'schematic lib_symbols') + t[le:]
    lib = renumber_units(lib, 'ctambe.kicad_sym')
    # 2. placed units 14..17 move to the row of their new pin
    moved = 0
    for unit, (old, new) in UNIT_OLD_NEW.items():
        head = f'(lib_id "ctambe:ZULU-CONN")\n\t\t(at 46.99 {fmt(ROWS[old])} 90)\n\t\t(unit {unit})'
        assert t.count(head) == 1, ('unit', unit)
        i = t.find(head); s = t.rfind('\n\t(symbol\n', 0, i); e = t.find('\n\t)\n', i) + 3
        t = t[:s] + shift_block(t[s:e], ROWS[new] - ROWS[old]) + t[e:]
        moved += 1
    # 3. the global label on each row moves with its unit
    spans = []
    for name, (old, new) in LABELS.items():
        pat = re.compile(r'\n\t\(global_label "' + re.escape(name) + r'"\n\t\t\(shape [^)]*\)\n\t\t\(at 39\.37 ' +
                         re.escape(fmt(ROWS[old])) + r' ')
        hits = list(pat.finditer(t))
        assert len(hits) == 1, ('label', name, len(hits))
        s = hits[0].start(); e = t.find('\n\t)\n', s) + 3
        spans.append((s, e, ROWS[new] - ROWS[old]))
    for s, e, dy in sorted(spans, reverse=True):
        t = t[:s] + shift_block(t[s:e], dy) + t[e:]
    # 4. NOTE and text box
    for old, new, n in TEXT_EDITS:
        assert t.count(old) == n, (old[:40], t.count(old))
        t = t.replace(old, new)
    open(SCH, 'w', encoding='utf-8', newline='\n').write(t)
    open(LIB, 'w', encoding='utf-8', newline='\n').write(lib)
    print(f'{moved} units and {len(spans)} labels moved; pins renumbered in the sheet and ctambe.kicad_sym')


if __name__ == '__main__':
    main()
