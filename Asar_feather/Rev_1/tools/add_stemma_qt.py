"""Add the STEMMA QT connector X5 to the Feather schematic (2026-11-06, user request).

X5 is JST SM04B-SRSS-TB, a 4-pin 1.0 mm side-entry header, on asar_a7_2.SchDoc (the sheet with X2 and its CHAN21 /
CHAN22 labels), in empty sheet space. Pin order is Adafruit's STEMMA QT order: 1 GND, 2 V+ (VCC3V3), 3 SDA (CHAN22,
Feather pin 28), 4 SCL (CHAN21, Feather pin 27). The two fixing tabs MP1 and MP2 go to GND.
The symbol is built from X4's records on asar_a7_1.SchDoc (same body and hidden-parameter layout), with new UniqueIDs,
pins and footprint link. Each pin gets a 20-unit wire to a net label. Refuses if X5 exists.
Check with check_feather_schematic.py (feather_map.ADDED_PINS) afterwards.
    python tools/add_stemma_qt.py      (close the project in Altium first)
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sch_netlist import sheet_objects  # noqa: E402
from schdoc import del_field, field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb')
SRC = os.path.join(ROOT, 'asar_a7_1.SchDoc')
PATH = os.path.join(ROOT, 'asar_a7_2.SchDoc')
X0, Y0, W, H = 700, 640, 50, 140              # the body rectangle, in sheet units
FP = 'JST-SM04B-SRSS-TB'
PINS = [('1', 'GND', 'GND'), ('2', 'V+', 'VCC3V3'), ('3', 'SDA', 'CHAN22'), ('4', 'SCL', 'CHAN21'),
        ('MP1', 'MP1', 'GND'), ('MP2', 'MP2', 'GND')]
PARAMS = {
    'SymbolName_1': 'CONN-4', 'DeviceName': 'SM04B-SRSS-TB', 'DeviceSetName': 'JST-SH-4', 'MANF': 'JST',
    'MANF#': 'SM04B-SRSS-TB(LF)(SN)',
    'SPEC': 'JST SH 1.0 mm, 4 circuits, side-entry SMT header with fixing tabs, 1 A, 50 V, -25..85 C, mates with '
            'SHR-04V-S housing; STEMMA QT / Qwiic order: pin 1 GND, 2 V+, 3 SDA, 4 SCL',
    'NOTE': 'STEMMA QT port on the Feather I2C pins (X2-27 SCL, X2-28 SDA). V+ is VCC3V3, so the devices pull SDA and '
            'SCL up to 3.3 V; devices carry the pull-ups, the board has none. The FPGA pins are not 5 V tolerant. '
            '2.95 mm tall, fits under a stacked FeatherWing; the plug leaves past the board end opposite the USB.',
    'Comment': 'STEMMA QT, I2C',
}
rng = random.Random(5252)


def main():
    src = split(read_stream(SRC))
    recs = split(read_stream(PATH))
    for f in (src, recs):
        if 'X5' in [field(b, 'Text') for h, b in f if field(b, 'RECORD') == '34']:
            sys.exit('REFUSED: X5 already exists')
    root = [owner(b) for h, b in src if field(b, 'RECORD') == '34' and field(b, 'Text') == 'X4']
    if len(root) != 1:
        sys.exit('REFUSED: %d X4 parts' % len(root))
    root = root[0]
    taken = {field(b, 'UniqueID') for f in (src, recs) for h, b in f} | {field(b, 'Text') for f in (src, recs) for h, b in f}

    def uid():
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in taken:
                taken.add(u)
                return u

    tree = sorted(subtree(src, [root]))
    kinds = [field(src[i][1], 'RECORD') for i in tree]
    if kinds.count('2') != 2 or kinds.count('6') != 4:
        sys.exit('REFUSED: X4 no longer has 2 pins and 4 lines: %s' % kinds)
    top = max(int(field(b, 'IndexInSheet') or 0) for h, b in recs)
    pin_i = [i for i in tree if field(src[i][1], 'RECORD') == '2']
    pin_t, uid_t = src[pin_i[0]], src[pin_i[0] + 1]
    if field(uid_t[1], 'Name') != 'PinUniqueId':
        sys.exit('REFUSED: the record after a pin is not its PinUniqueId')

    base = len(recs)
    new_index, out = {}, []

    def add(old, h, b):
        if old is not None:
            new_index[old] = base + len(out)
        out.append([h, b, old])

    lines = iter([(X0, Y0, X0 + W, Y0), (X0 + W, Y0, X0 + W, Y0 + H), (X0 + W, Y0 + H, X0, Y0 + H), (X0, Y0 + H, X0, Y0)])
    for i in tree:
        h, b = src[i]
        rec = field(b, 'RECORD')
        if i == pin_i[0]:                                  # all six pins go where X4's first pin was
            for k, (des, name, net) in enumerate(PINS):
                y = Y0 + H - 20 - 20 * k
                pb = set_field(set_field(pin_t[1], 'Name', name), 'Designator', des)
                pb = set_field(set_field(pb, 'Location.X', str(X0)), 'Location.Y', str(y))
                pin_at = base + len(out)
                add(None, pin_t[0], ('PIN', pb))
                ub = set_field(set_field(uid_t[1], 'Location.X', str(X0)), 'Location.Y', str(y))
                ub = set_field(set_field(ub, 'Text', uid()), 'UniqueID', uid())
                add(None, uid_t[0], ('PINUID', ub, pin_at))
            continue
        if i in (pin_i[0] + 1, pin_i[1], pin_i[1] + 1):
            continue
        if field(b, 'UniqueID'):
            b = set_field(b, 'UniqueID', uid())
        if i == root:
            top += 1
            for k, v in (('LibReference', FP), ('DesignItemId', FP), ('AllPinCount', str(len(PINS))),
                         ('ComponentDescription', 'JST SH 1.0 mm 4-pin side-entry SMT header, STEMMA QT / Qwiic port'),
                         ('Location.X', str(X0)), ('Location.Y', str(Y0)), ('IndexInSheet', str(top))):
                b = set_field(b, k, v)
        elif rec == '6':
            x1, y1, x2, y2 = next(lines)
            for k, v in (('X1', x1), ('Y1', y1), ('X2', x2), ('Y2', y2)):
                b = set_field(del_field(b, k + '_Frac'), k, str(v))
        elif rec == '34':
            b = set_field(set_field(b, 'Text', 'X5'), 'Location.X', str(X0))
            b = set_field(b, 'Location.Y', str(Y0 + H + 5))
        elif rec == '41' and field(b, 'Name') in PARAMS:
            b = set_field(b, 'Text', PARAMS[field(b, 'Name')])
            if field(b, 'Name') == 'Comment':
                b = set_field(set_field(b, 'Location.X', str(X0)), 'Location.Y', str(Y0 - 20))
        elif rec == '45':
            b = set_field(set_field(b, 'ModelName', FP), 'ModelDatafileEntity0', FP)
        add(i, h, b)

    new = []
    for h, b, old in out:
        if isinstance(b, tuple):
            if b[0] == 'PIN':
                b = set_field(b[1], 'OwnerIndex', str(new_index[root] - 1))
            else:
                b = set_field(b[1], 'OwnerIndex', str(b[2] - 1))
        else:
            o = owner(b)
            if o in new_index:
                b = set_field(b, 'OwnerIndex', str(new_index[o] - 1))
        new.append([h, b])
    recs.extend(new)
    if {field(b, 'Name') for h, b in new if field(b, 'RECORD') == '41'} < set(PARAMS):
        sys.exit('REFUSED: a parameter of the template is missing')

    pins, wires, juncs, labels = sheet_objects(PATH, recs)
    hot = {d: p for r, d, p in pins if r == 'X5'}
    if sorted(hot) != sorted(d for d, n, net in PINS):
        sys.exit('REFUSED: X5 pins %s' % sorted(hot))
    wire_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '27' and field(b, 'LocationCount') == '2')
    left_t = next((h, b) for h, b in recs if field(b, 'RECORD') == '25' and field(b, 'Justification') == '2')
    for des, name, net in PINS:
        x, y = hot[des]
        end = (x - 20, y)
        h, b = wire_t
        for k, v in (('X1', x), ('Y1', y), ('X2', end[0]), ('Y2', end[1])):
            b = del_field(b, k + '_Frac')
            b = set_field(b, k, '%g' % v)
        top += 1
        recs.append([h, set_field(set_field(b, 'UniqueID', uid()), 'IndexInSheet', str(top))])
        h, b = left_t
        b = del_field(del_field(b, 'Location.X_Frac'), 'Location.Y_Frac')
        b = set_field(set_field(b, 'Location.X', '%g' % end[0]), 'Location.Y', '%g' % end[1])
        top += 1
        recs.append([h, set_field(set_field(set_field(b, 'Text', net), 'UniqueID', uid()), 'IndexInSheet', str(top))])
    recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
    write_stream(PATH, join(recs))
    print('X5 added to asar_a7_2.SchDoc at %d,%d: %s (%d records, 6 wires, 6 labels)' % (
        X0, Y0, ', '.join('%s %s' % (d, net) for d, n, net in PINS), len(new)))


if __name__ == '__main__':
    main()
