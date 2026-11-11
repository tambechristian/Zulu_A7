"""Fix-up after replace_u5_tps63802.py (2026-11-09): its one-line note ran past the sheet frame. The two 2026-09-06
regulator notes move up 20 units (602 -> 622, 592 -> 612) and the 2026-11-09 note becomes two lines at 602 and 592.
    python tools/wrap_u5_note.py <sheet-1 SchDoc>        (close the project in Altium first)"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

LINES = ['2026-11-09: U5 SC189Z -> TI TPS63802 buck-boost, holds 3.3 V as the LiPo falls below it; L1 0.47 uH;',
         'R109/R110 511k/91k = 3.31 V; MODE = GND (power save); PG unused. Footprint VSON10-DLA0010A.']
path = sys.argv[1]
recs = split(read_stream(path))
taken = {field(b, 'UniqueID') for h, b in recs}
rng = random.Random(6380202)


def find(prefix):
    hit = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '4' and (field(b, 'Text') or '').startswith(prefix)]
    if len(hit) != 1:
        sys.exit('REFUSED: %d notes start with %r' % (len(hit), prefix))
    return hit[0]


a, b, n = find('2026-09-06: LTC3569'), find('dividers, no sequencer'), find('2026-11-09: U5 SC189Z')
for i, y in ((a, 622), (b, 612)):
    recs[i][1] = set_field(recs[i][1], 'Location.Y', str(y))
recs[n][1] = set_field(set_field(recs[n][1], 'Text', LINES[0]), 'Location.Y', '602')
u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
assert u not in taken
top = max(int(field(x, 'IndexInSheet') or 0) for h, x in recs) + 1
second = set_field(set_field(set_field(set_field(recs[n][1], 'Text', LINES[1]), 'Location.Y', '592'), 'UniqueID', u),
                   'IndexInSheet', str(top))
recs.append([recs[n][0], second])
recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
write_stream(path, join(recs))
print('notes rewrapped on', os.path.basename(path))
