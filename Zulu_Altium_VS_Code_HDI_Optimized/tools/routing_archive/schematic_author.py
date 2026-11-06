"""Put the author's name in every sheet's title block (2026-10-08, user request).

The EAGLE title block (DOCFIELD) reads "AUTHOR: >AUTHOR", and >AUTHOR resolves to the global attribute
"Christian Tambe". The Altium EAGLE importer kept only a DOCFIELD parameter named AUTHOR whose text is the literal
word "AUTHOR", and dropped the "AUTHOR:" label (its name collided with that parameter). This script, per SchDoc:
  1. sets the DOCFIELD's AUTHOR parameter text to "Christian Tambe" (at the >AUTHOR position, as in EAGLE);
  2. appends a sheet label "AUTHOR:" at the PROJECT: label's x and the AUTHOR row's y, in PROJECT:'s font and
     colour, so the row reads "AUTHOR: Christian Tambe" like the EAGLE original;
  3. updates the header Weight (record count - 1).
Every other record stays byte-identical, which the script checks after writing. It refuses to run twice.
    python tools/schematic_author.py "<project folder>"        (edits every *.SchDoc in it; close it in Altium first)
"""
import glob
import os
import random
import re
import sys

from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

NAME = 'Christian Tambe'
LABEL = 'AUTHOR:'


def uid(taken):
    rng = random.Random(len(taken))
    while True:
        u = ''.join(rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
        if u not in taken:
            taken.add(u)
            return u


def one(recs, pred, what, path):
    hits = [i for i, (h, b) in enumerate(recs) if pred(b)]
    if len(hits) != 1:
        raise SystemExit('REFUSED %s: %d %s records' % (os.path.basename(path), len(hits), what))
    return hits[0]


def edit(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    if any(field(b, 'RECORD') == '4' and field(b, 'Text') == LABEL for h, b in recs):
        raise SystemExit('REFUSED %s: an AUTHOR: label already exists' % os.path.basename(path))
    a = one(recs, lambda b: field(b, 'Name') == 'AUTHOR' and field(b, 'RECORD') == '41', 'AUTHOR parameter', path)
    if field(recs[a][1], 'Text') != 'AUTHOR':
        raise SystemExit('REFUSED %s: AUTHOR parameter text is %r' % (os.path.basename(path), field(recs[a][1], 'Text')))
    p = one(recs, lambda b: field(b, 'Name') == 'PROJECT' and field(b, 'Text') == 'PROJECT:', 'PROJECT: label', path)
    if field(recs[a][1], 'OwnerIndex') != field(recs[p][1], 'OwnerIndex'):
        raise SystemExit('REFUSED %s: AUTHOR and PROJECT: belong to different owners' % os.path.basename(path))
    if int(field(recs[0][1], 'Weight')) != len(recs) - 1:
        raise SystemExit('REFUSED %s: header Weight does not match the record count' % os.path.basename(path))

    taken = set(re.findall(rb'\|UniqueID=([A-Z]{8})', data))
    taken = {t.decode() for t in taken}
    x, y = field(recs[p][1], 'Location.X'), field(recs[a][1], 'Location.Y')
    font, color = field(recs[p][1], 'FontID'), field(recs[p][1], 'Color')
    before = [b for h, b in recs]

    recs[a][1] = set_field(recs[a][1], 'Text', NAME)
    body = ('|RECORD=4|OwnerPartId=-1|Location.X=%s|Location.Y=%s|Color=%s|FontID=%s|Text=%s|UniqueID=%s\x00'
            % (x, y, color, font, LABEL, uid(taken))).encode('latin-1')
    recs.append([recs[a][0][:2] + b'\x00\x00', body])
    recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
    write_stream(path, 'FileHeader', join(recs))

    after = split(read_stream(path, 'FileHeader'))
    assert len(after) == len(before) + 1
    for i, (h, b) in enumerate(after[:-1]):
        if i in (0, a):
            continue
        assert b == before[i], (path, i)
    assert field(after[a][1], 'Text') == NAME
    assert field(after[-1][1], 'Text') == LABEL and field(after[0][1], 'Weight') == str(len(after) - 1)
    print('%-18s AUTHOR -> %s at (%s, %s); label "%s" added at (%s, %s); records %d -> %d'
          % (os.path.basename(path), NAME, field(after[a][1], 'Location.X'), y, LABEL, x, y, len(before), len(after)))


def main(folder):
    docs = sorted(glob.glob(os.path.join(folder, '*.SchDoc')))
    if len(docs) != 7:
        raise SystemExit('REFUSED: expected 7 SchDocs in %s, found %d' % (folder, len(docs)))
    for d in docs:
        edit(d)


if __name__ == '__main__':
    main(sys.argv[1])
