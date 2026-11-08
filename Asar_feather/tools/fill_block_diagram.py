"""Fill the boxes of the block diagram (asar_a7_0.SchDoc, sheet 1) with a solid colour.

Each block is drawn as four separate sheet-level lines, which cannot be filled. This finds every innermost closed
rectangle those lines form (collinear pieces merged first), and inserts one filled Rectangle record (RECORD=14) per box
right after the sheet record, so it draws underneath the lines, arrows and text that follow it. Every OwnerIndex that
points past the insertion point moves up by the number of inserted records and the header Weight follows the record
count, so nothing else in the file changes. Refuses if the sheet already has a filled rectangle (runs once).

    python tools/fill_block_diagram.py [--color 0xRRGGBB] [--out path] [--dry-run]

Close the sheet in Altium first; the default colour is sky blue (#87CEEB).
"""
import argparse
import os
import random
import re
import shutil
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schdoc import read_stream, split, join, field, set_field, owner, write_stream  # noqa: E402

SHEET = os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb', 'asar_a7_0.SchDoc')


def text(body):
    return body.decode('latin-1', 'replace').rstrip('\x00')


def boxes(recs):
    """Innermost axis-aligned rectangles formed by the sheet-level lines, with the texts inside each."""
    H, V, texts = {}, {}, []
    for _, b in recs:
        t = text(b)
        if field(b, 'OwnerIndex') is not None:
            continue
        if t.startswith('|RECORD=6|'):
            n = int(field(b, 'LocationCount') or 0)
            pts = [(int(field(b, 'X%d' % i)), int(field(b, 'Y%d' % i))) for i in range(1, n + 1)]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                if y1 == y2:
                    H.setdefault(y1, []).append((min(x1, x2), max(x1, x2)))
                elif x1 == x2:
                    V.setdefault(x1, []).append((min(y1, y2), max(y1, y2)))
        elif t.startswith('|RECORD=4|') and field(b, 'Text'):
            texts.append((int(field(b, 'Location.X')), int(field(b, 'Location.Y')), field(b, 'Text')))

    def merge(d):
        out = {}
        for k, iv in d.items():
            iv.sort()
            m = []
            for a, c in iv:
                if m and a <= m[-1][1]:
                    m[-1][1] = max(m[-1][1], c)
                else:
                    m.append([a, c])
            out[k] = m
        return out
    H, V = merge(H), merge(V)

    def cov(d, k, a, c):
        return any(s <= a and c <= e for s, e in d.get(k, []))
    xs, ys = sorted(V), sorted(H)
    found = []
    for i, x0 in enumerate(xs):
        for x1 in xs[i + 1:]:
            if x1 - x0 < 30 or x1 - x0 > 600:
                continue
            for j, y0 in enumerate(ys):
                for y1 in ys[j + 1:]:
                    if y1 - y0 < 30:
                        continue
                    if cov(H, y0, x0, x1) and cov(H, y1, x0, x1) and cov(V, x0, y0, y1) and cov(V, x1, y0, y1):
                        found.append((x0, y0, x1, y1))
    inner = [b for b in found if not any(o != b and b[0] <= o[0] and b[1] <= o[1] and o[2] <= b[2] and o[3] <= b[3]
                                         for o in found)]
    return [(b, [t for x, y, t in texts if b[0] < x < b[2] and b[1] < y < b[3]]) for b in inner]


def uid(taken):
    while True:
        u = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
        if u not in taken:
            taken.add(u)
            return u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--color', default='0x87CEEB', help='fill colour as 0xRRGGBB (default sky blue)')
    ap.add_argument('--src', default=SHEET)
    ap.add_argument('--out', default=None, help='write here instead of editing the sheet in place')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    rgb = int(a.color, 16)
    bgr = ((rgb & 0xFF) << 16) | (rgb & 0xFF00) | (rgb >> 16)        # Altium stores colours as 0xBBGGRR

    recs = split(read_stream(a.src))
    assert text(recs[0][1]).startswith('|HEADER='), 'record 0 is not the header'
    assert text(recs[1][1]).startswith('|RECORD=31|'), 'record 1 is not the sheet record'
    if any(text(b).startswith('|RECORD=14|') and field(b, 'IsSolid') == 'T' for _, b in recs):
        sys.exit('Refusing: the sheet already has a filled rectangle.')
    found = boxes(recs)
    named = [(b, t) for b, t in found if t]
    for b, t in named:
        print('  box %s %s' % (b, t))
    print('%d boxes with text (%d without, skipped)' % (len(named), len(found) - len(named)))
    if a.dry_run:
        return

    taken = {field(b, 'UniqueID') for _, b in recs if field(b, 'UniqueID')}
    random.seed(20261107)
    new = []
    for (x0, y0, x1, y1), _ in named:
        body = ('|RECORD=14|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Corner.X=%d|Corner.Y=%d|LineWidth=1|Color=128'
                '|AreaColor=%d|IsSolid=T|UniqueID=%s' % (x0, y0, x1, y1, bgr, uid(taken))).encode('latin-1') + b'\x00'
        new.append([b'\x00\x00\x00\x00', body])
    n, at = len(new), 2                                             # insert right after the sheet record
    out = recs[:at] + new
    for h, b in recs[at:]:
        o = owner(b)                                                 # list index of the owner, or None
        if o is not None and o >= at:
            b = set_field(b, 'OwnerIndex', str(int(field(b, 'OwnerIndex')) + n))
        out.append([h, b])
    for h, b in recs[:at]:
        o = owner(b)
        assert o is None or o < at, 'a record before the insertion point has an owner after it'
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    data = join(out)

    # Check: re-parse, every original record is unchanged apart from its shifted OwnerIndex.
    chk = split(data)
    assert len(chk) == len(recs) + n
    for (h0, b0), (h1, b1) in zip(recs[at:], chk[at + n:]):
        o0, o1 = field(b0, 'OwnerIndex'), field(b1, 'OwnerIndex')
        if o0 is not None and int(o0) + 1 >= at:
            assert int(o1) == int(o0) + n
            b1 = set_field(b1, 'OwnerIndex', o0)
        assert b0 == b1, 'record changed: %r' % b0[:80]
    for i, (h, b) in enumerate(chk):
        o = owner(b)
        if o is not None and o > 0:
            assert text(chk[o][1]).startswith('|RECORD='), 'record %d points at a non-record' % i

    dst = a.out or a.src
    if not a.out:
        shutil.copy2(a.src, a.src + '.pre-fill')
    else:
        shutil.copy2(a.src, dst)
    write_stream(dst, data)
    print('inserted %d filled rectangles (AreaColor %d = #%06X) into %s; Weight %s' % (n, bgr, rgb, dst, field(out[0][1], 'Weight')))


if __name__ == '__main__':
    main()
