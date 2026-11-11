"""Wrap a one-line schematic note (Label, RECORD=4) into several stacked labels inside the sheet frame.

    python tools/wrap_sheet_note.py <SchDoc> <text prefix> <x> <y top line> <chars per line> [line pitch=10, as the sheets' other stacked notes]

Altium labels are single-line, so a long note runs straight across the frame. The record whose Text starts with
<text prefix> keeps its UniqueID and gets the first line, moved to (x, y); every further line is a new label with
the same colour and font, appended at the end of the record list (nothing points at it, so no OwnerIndex shifts)
and placed <pitch> (10 mil units) below the previous one. Units are the file's 10 mil units.
"""
import os
import random
import re
import string
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schdoc as S  # noqa: E402


def main():
    path, prefix, x, y, width = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    pitch = int(sys.argv[6]) if len(sys.argv) > 6 else 10
    recs = S.split(S.read_stream(path))
    hits = [i for i, (h, b) in enumerate(recs) if S.field(b, 'RECORD') == '4' and (S.field(b, 'Text') or '').startswith(prefix)]
    if len(hits) != 1:
        sys.exit('REFUSED: %d labels start with %r' % (len(hits), prefix))
    i = hits[0]
    hdr, body = recs[i]
    text = S.field(body, 'Text')
    lines = textwrap.wrap(text, width)
    used = set(re.findall(rb'\|UniqueID=([A-Z]{8})', b''.join(b for h, b in recs)))
    rnd = random.Random(text)
    body = S.set_field(S.set_field(S.set_field(body, 'Location.X', str(x)), 'Location.Y', str(y)), 'Text', lines[0])
    recs[i] = [hdr, body]
    color, font = S.field(body, 'Color'), S.field(body, 'FontID')
    for k, line in enumerate(lines[1:], 1):
        while True:
            uid = ''.join(rnd.choice(string.ascii_uppercase) for _ in range(8)).encode()
            if uid not in used:
                used.add(uid)
                break
        nb = ('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=%s|FontID=%s|Text=%s|UniqueID=%s'
              % (x, y - k * pitch, color, font, line, uid.decode())).encode('latin-1') + b'\x00'
        recs.append([hdr, nb])
    # the header's Weight is the record count Altium reads; records past it are silently ignored
    w = S.field(recs[0][1], 'Weight')
    if w is None or int(w) != len(recs) - 1 - (len(lines) - 1):
        sys.exit('REFUSED: header Weight=%s does not match the %d records read' % (w, len(recs) - 1 - (len(lines) - 1)))
    recs[0] = [recs[0][0], S.set_field(recs[0][1], 'Weight', str(len(recs) - 1))]
    S.write_stream(path, S.join(recs))
    print('%s: %d lines at x %d, y %d..%d (max %d chars)' % (os.path.basename(path), len(lines), x, y, y - (len(lines) - 1) * pitch,
                                                            max(len(l) for l in lines)))
    for l in lines:
        print('   ', l)


if __name__ == '__main__':
    main()
