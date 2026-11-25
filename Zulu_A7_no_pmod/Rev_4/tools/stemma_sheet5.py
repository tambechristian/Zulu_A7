"""No-PMOD Rev 3 (2026-11-21): tie FPGA balls U19 and R19 to the STEMMA QT nets on zulu_a7_5.SchDoc.

    python tools/stemma_sheet5.py      (close the project in Altium first; run after tools/add_stemma_qt.py)

Sheet 5 draws U1 one ball per part, pin hot end at x 780. Used balls carry a wire 770..780 and a net label at 770
(the CHAN rows); the eight balls the Pmod left free carry a No-ERC mark at 780 instead. For U19 (y 440, -> I2C-SDA)
and R19 (y 470, -> I2C-SCL) the No-ERC record is replaced in place by the wire (so no record index moves) and the
net label is appended, both cloned from CHAN28's pair. Refuses unless both marks are where expected and unowned.
"""
import random
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

PATH = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/Imported zulu_a7.PrjPcb/zulu_a7_5.SchDoc'
BALLS = [('U19', 440, 'I2C-SDA'), ('R19', 470, 'I2C-SCL')]
rng = random.Random(7122)


def main():
    R = split(read_stream(PATH))
    if any(field(b, 'RECORD') == '25' and field(b, 'Text') in ('I2C-SDA', 'I2C-SCL') for h, b in R):
        sys.exit('REFUSED: the I2C labels already exist')
    wire = [(h, b) for h, b in R if field(b, 'RECORD') == '27' and field(b, 'X1') == '770' and field(b, 'Y1') == '956']
    lab = [(h, b) for h, b in R if field(b, 'RECORD') == '25' and field(b, 'Text') == 'CHAN28']
    if len(wire) != 1 or len(lab) != 1:
        sys.exit('REFUSED: CHAN28 template wire/label not found once (%d, %d)' % (len(wire), len(lab)))
    taken = {field(b, 'UniqueID') for h, b in R}
    top = max(int(field(b, 'IndexInSheet') or 0) for h, b in R)

    def uid():
        while True:
            u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
            if u not in taken:
                taken.add(u)
                return u
    for ball, y, net in BALLS:
        hits = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '22' and field(b, 'Location.X') == '780'
                and field(b, 'Location.Y') == str(y)]
        if len(hits) != 1 or field(R[hits[0]][1], 'OwnerIndex'):
            sys.exit('REFUSED: No-ERC at (780, %d) for %s: %d found' % (y, ball, len(hits)))
        h, b = wire[0]
        for k, v in (('X1', '770'), ('Y1', str(y)), ('X2', '780'), ('Y2', str(y))):
            b = set_field(b, k, v)
        top += 1
        R[hits[0]] = [h, set_field(set_field(b, 'UniqueID', uid()), 'IndexInSheet', str(top))]
        h, b = lab[0]
        b = set_field(set_field(set_field(b, 'Location.Y', str(y)), 'Text', net), 'UniqueID', uid())
        top += 1
        R.append([h, set_field(b, 'IndexInSheet', str(top))])
        print('%s (y %d): No-ERC -> wire 770..780 + label %s' % (ball, y, net))
    R[0][1] = set_field(R[0][1], 'Weight', str(len(R) - 1))
    blob = join(R)
    write_stream(PATH, blob)
    assert read_stream(PATH) == blob
    print('written, %d records' % len(R))


if __name__ == '__main__':
    main()
