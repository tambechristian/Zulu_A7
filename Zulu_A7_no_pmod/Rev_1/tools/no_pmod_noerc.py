"""Zulu_a7_no_pmod: No-ERC markers on the eight U1 balls the Pmod used to drive (open on purpose; five are input-typed
pins and would otherwise raise 'floating input pin' errors). Layout copied from Altium's RECORD=22, as add_noerc.py."""
import os
import random
import string
import sys

sys.path.insert(0, r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools')
from fix_text_orientation import field, join, read_stream, set_field, split, write_stream  # noqa: E402

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7_5.SchDoc')
SPOTS = [(945, 407), (945, 397), (265, 882), (945, 377), (750, 202), (265, 892), (945, 347), (945, 337)]
recs = split(read_stream(P, 'FileHeader'))
have = {(field(b, 'Location.X'), field(b, 'Location.Y')) for _, b in recs if b.startswith(b'|RECORD=22|')}
n = 0
for x, y in SPOTS:
    if (str(x), str(y)) in have:
        continue
    uid = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
    body = ('|RECORD=22|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=255|Symbol=Thin Cross|IsActive=T|SuppressAll=T|UniqueID=%s' % (x, y, uid)).encode()
    recs.append([b'\x00\x00\x00\x00', body + b'\x00'])
    n += 1
w = int(field(recs[0][1], 'Weight'))
recs[0][1] = set_field(recs[0][1], 'Weight', str(w + n))
d = join(recs)
write_stream(P, 'FileHeader', d)
assert read_stream(P, 'FileHeader') == d
print('added', n, 'Weight', w, '->', w + n)
