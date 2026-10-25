"""Add a hardware reset button to the Feather schematic (2026-10-23, user request).

RESET is a copy of BTN (C&K PTS810, footprint PTS810, pads 1+2 one terminal, 3+4 the other) placed 120 units
below it on asar_a7_2.SchDoc, in empty sheet space. Pins 1/2 go to RST# (FPGA PROGRAM_B, pulled up by R1 and
reached by the FT2232H through R4's 100 ohm) and pins 3/4 to GND, each through a 20-unit wire to a net label.
Pressing it holds PROGRAM_B low; releasing it makes the FPGA reload from flash, whatever design is loaded.
The copy gets new UniqueIDs and pin IDs, designator RESET and its own NOTE/SPEC. Refuses if RESET exists.
Check with check_feather_schematic.py (feather_map.ADDED_PINS) afterwards.
    python tools/add_reset_button.py      (close asar_a7_2.SchDoc in Altium first)
"""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sch_netlist import num, sheet_objects  # noqa: E402
from schdoc import del_field, field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb', 'asar_a7_2.SchDoc')
DX, DY = 0, -120
NOTE = ('Hardware reset: pressing pulls RST# (FPGA PROGRAM_B) to GND; on release the FPGA reloads its configuration '
        'from the SPI flash, whatever design is running. Same part and footprint as BTN. RST# is also driven by the '
        'FT2232H through R4 (100 ohm), which limits the current if the bridge drives it high while the button is held.')
SPEC = 'tactile switch SPST-NO momentary, SMT J-lead, 4.2 x 3.2 x 2.5 mm, 1.6 N (same as BTN); RESET for PROGRAM_B'
XKEY = re.compile(rb'(\|(?:Location\.X|Corner\.X|X\d+)=)(-?\d+)')
YKEY = re.compile(rb'(\|(?:Location\.Y|Corner\.Y|Y\d+)=)(-?\d+)')
rng = random.Random(4242)


def main():
    recs = split(read_stream(PATH))
    refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
    if 'RESET' in refs.values():
        sys.exit('REFUSED: RESET already exists')
    src = [c for c, r in refs.items() if r == 'BTN']
    if len(src) != 1:
        sys.exit('REFUSED: %d BTN parts' % len(src))
    taken = {field(b, 'UniqueID') for h, b in recs} | {field(b, 'Text') for h, b in recs}

    def uid():
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in taken:
                taken.add(u)
                return u

    tree = sorted(subtree(recs, src))
    base = len(recs)
    new_index = {old: base + k for k, old in enumerate(tree)}
    for old in tree:
        h, b = recs[old]
        o = owner(b)
        if o in new_index:
            b = set_field(b, 'OwnerIndex', str(new_index[o] - 1))
        b = XKEY.sub(lambda m: m.group(1) + str(int(m.group(2)) + DX).encode(), b)
        b = YKEY.sub(lambda m: m.group(1) + str(int(m.group(2)) + DY).encode(), b)
        if field(b, 'UniqueID'):
            b = set_field(b, 'UniqueID', uid())
        if field(b, 'Name') == 'PinUniqueId':
            b = set_field(b, 'Text', uid())
        if field(b, 'RECORD') == '34' and field(b, 'Text') == 'BTN':
            b = set_field(b, 'Text', 'RESET')
        if field(b, 'Name') == 'NOTE':
            b = set_field(b, 'Text', NOTE)
        if field(b, 'Name') == 'SPEC':
            b = set_field(b, 'Text', SPEC)
        recs.append([h, b])

    pins, wires, juncs, labels = sheet_objects(PATH, recs)
    hot = {d: p for r, d, p in pins if r == 'RESET'}
    if sorted(hot) != ['1', '2', '3', '4']:
        sys.exit('REFUSED: RESET pins %s' % sorted(hot))
    wire_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '27' and field(b, 'LocationCount') == '2')
    left_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '25' and field(b, 'Justification') == '2')
    right_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '25' and field(b, 'Text') == 'GND'
                   and field(b, 'Justification') in (None, '0'))
    top = max(int(field(b, 'IndexInSheet') or 0) for h, b in recs)
    for d, net in (('1', 'RST#'), ('2', 'RST#'), ('3', 'GND'), ('4', 'GND')):
        x, y = hot[d]
        end = (x - 20, y) if d in ('1', '2') else (x + 20, y)
        h, b = wire_t
        for k, v in (('X1', x), ('Y1', y), ('X2', end[0]), ('Y2', end[1])):
            b = del_field(b, k + '_Frac')
            b = set_field(b, k, '%g' % v)
        top += 1
        recs.append([h, set_field(set_field(b, 'UniqueID', uid()), 'IndexInSheet', str(top))])
        h, b = left_t if d in ('1', '2') else right_t
        b = del_field(del_field(b, 'Location.X_Frac'), 'Location.Y_Frac')
        b = set_field(set_field(b, 'Location.X', '%g' % end[0]), 'Location.Y', '%g' % end[1])
        top += 1
        recs.append([h, set_field(set_field(set_field(b, 'Text', net), 'UniqueID', uid()), 'IndexInSheet', str(top))])
    recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
    write_stream(PATH, join(recs))
    print('RESET added at BTN %+d,%+d: pins 1/2 -> RST#, 3/4 -> GND (%d records copied, 4 wires, 4 labels)' % (
        DX, DY, len(tree)))


if __name__ == '__main__':
    main()
