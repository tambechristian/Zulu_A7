# -*- coding: utf-8 -*-
"""Sheet 1, 2026-09-10: the two revision notes are re-wrapped to fit inside the drawing frame.

THE DEFECT. Sheet 1's inner border is the RECORD=6 line at x=890. Three of its comment lines were
drawn straight through it and off the printed page. They are hand-wrapped paragraphs -- one
RECORD=4 per line, no word wrap of any kind in the format -- and each was wrapped correctly when it
was written and then had text appended to it without re-wrapping:

    rec483   the SC189 note, one line of 201 characters, runs to x 1197.7  -- 307.7 past the border
    rec1059  the bq24232 note's third line, 238 characters, runs to x 1191.3 -- 301.3 past
    rec1057  the bq24232 note's first line, 161 characters, runs to x  906.7 --  16.7 past

The middle line, rec1058 at 156 characters, ends at 884.2 and just fits, which is what the width
was originally chosen for: font 3 is Courier New size 7, so a character advances 0.535 * 7 = 3.745
schematic units, and from x=300 the border allows 155 characters. Both paragraphs simply grew.

Sheets 0 and 2 to 6 were checked the same way and none of their comments cross their own border.

THE FIX. Each paragraph is joined back into one string, re-wrapped to the widest line that fits, and
written back out one RECORD=4 per line on the same 10-unit pitch. The wrap is balanced, not greedy:
the narrowest width that still gives the minimum number of lines, so the last line is not a stub.
Words are never split, which keeps `VQFN16-3X3-RGT`, `JST-B2B-PH-SM4-TB` and `docs/power_budget.md`
intact.

NOT A WORD OF THE TEXT CHANGES. That is asserted, not hoped for: the paragraph is compared word for
word before and after, and the tool refuses to run if any source line contains a double space, since
re-flowing would silently normalise it away.

WHICH WAY EACH PARAGRAPH GROWS is chosen from what is beside it. The bq24232 note needs a fourth
line and grows DOWN from its top at y 710, because y 640 to 690 across x 250 to 900 is empty. The
SC189 note needs a second line and grows UP from its bottom at y 592, because U5's designator sits
at y 574..581.8 and a line at 582 would clear it by 0.2 of a unit; above it there is nothing until
the other note at 690.

New lines are appended, so no existing index moves and no OwnerIndex needs renumbering; only the
header count changes. Refuses to run twice.

    python tools/sheet1_notes.py tools "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"
"""
import sys, os, re, random, string, textwrap
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import num, rectype, fonts_of, drawn_boxes, signature, text_box

BORDER = 890.0
MARGIN = 6.0
ADV = 0.535                      # Courier advance per unit of FontSize, calibrated on the PDF
PITCH = 10

NOTES = [
    dict(name='bq24232 charger', x=300, lines=[710, 700, 690], grow='down',
         starts='2026-09-09: D1 (USB VBUS Schottky)'),
    dict(name='SC189 supplies', x=445, lines=[592], grow='up',
         starts='2026-09-06: LTC3569 section replaced'),
]


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', lambda m: b'|UniqueID=' + uid().encode(), b)


def balanced(text, maxw):
    """the narrowest wrap that still uses the fewest lines, so no line is left a stub."""
    opts = dict(break_long_words=False, break_on_hyphens=False)
    n = len(textwrap.wrap(text, maxw, **opts))
    lo, hi = 1, maxw
    while lo < hi:
        mid = (lo + hi) // 2
        if len(textwrap.wrap(text, mid, **opts)) <= n:
            hi = mid
        else:
            lo = mid + 1
    out = textwrap.wrap(text, lo, **opts)
    assert len(out) == n, (len(out), n)
    return out


def find(recs, N):
    """the records of one note, top line first."""
    got = []
    for y in N['lines']:
        hit = [i for i, (h, b) in enumerate(recs)
               if rectype(b) == 4 and num(b, 'Location.X') == N['x']
               and num(b, 'Location.Y') == y]
        assert len(hit) == 1, f"{N['name']}: {len(hit)} texts at ({N['x']},{y})"
        got.append(hit[0])
    got.sort(key=lambda i: -num(recs[i][1], 'Location.Y'))
    assert (field(recs[got[0]][1], 'Text') or '').startswith(N['starts']), \
        f"{N['name']}: the top line does not start as expected"
    return got


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N0 = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N0 - 1, 'header count is already wrong'
    fonts = fonts_of(recs)
    if not [e for e in drawn_boxes(recs, fonts) if e[1] in (4, 28) and e[2][2] > BORDER + 0.05]:
        raise SystemExit('no comment on sheet 1 crosses the frame; nothing done')
    sig = signature(recs)

    adds, wrote = [], []
    for N in NOTES:
        idx = find(recs, N)
        src = [field(recs[i][1], 'Text') for i in idx]
        for t in src:
            assert '  ' not in t, f"{N['name']}: a source line has a double space; re-flowing " \
                                  f"would change it: {t[:60]!r}"
        para = ' '.join(src)
        size = fonts[num(recs[idx[0]][1], 'FontID')][0]
        width = int((BORDER - MARGIN - N['x']) // (ADV * size))
        out = balanced(para, width)
        assert ' '.join(out) == para, 'the re-wrap changed the text'
        wrote.append((N['name'], para, [t for t in out]))
        top = N['lines'][0] if N['grow'] == 'down' else N['lines'][-1] + PITCH * (len(out) - 1)
        ys = [top - PITCH * k for k in range(len(out))]
        print(f"{N['name']}: {len(src)} lines of up to {max(len(t) for t in src)} chars -> "
              f"{len(out)} of up to {max(len(t) for t in out)} (fits {width}), "
              f"y {ys[0]} down to {ys[-1]}")
        for k, (t, y) in enumerate(zip(out, ys)):
            if k < len(idx):
                b = set_field(recs[idx[k]][1], 'Text', t)
                recs[idx[k]][1] = set_field(b, 'Location.Y', str(y))
            else:
                b = new_uid(recs[idx[0]][1])
                b = set_field(set_field(b, 'Text', t), 'Location.Y', str(y))
                adds.append([bytes(4), set_field(b, 'Location.X', str(N['x']))])
            print(f'    y {y:5}  {t}')

    recs += adds
    recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 1: {N0} -> {len(recs)} records ({len(adds)} lines added)')
    verify(path, sig, wrote)


def verify(path, sig_before, wrote):
    recs = split(read_stream(path, 'FileHeader'))
    live = {field(b, 'Text') for h, b in recs if rectype(b) == 4}
    for name, para, lines in wrote:
        assert all(t in live for t in lines), f'{name}: a re-wrapped line is not in the file'
        assert ' '.join(lines) == para, f'{name}: the paragraph changed'
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    fonts = fonts_of(recs)
    boxes = drawn_boxes(recs, fonts)
    over = [e for e in boxes if e[1] in (4, 28) and e[2][2] > BORDER + 0.05]
    assert not over, f'{len(over)} comments still cross the frame: ' \
                     f'{[(e[3][:40], round(e[2][2], 1)) for e in over]}'
    txt = [e for e in boxes if e[1] in (4, 25, 34, 41, 17) and e[3]]
    txt.sort(key=lambda e: e[2][0])
    clash = []
    for a in range(len(txt)):
        ax0, ay0, ax1, ay1 = txt[a][2]
        for b in range(a + 1, len(txt)):
            bx0, by0, bx1, by1 = txt[b][2]
            if bx0 >= ax1 - 0.3:
                break
            if by0 < ay1 - 0.3 and ay0 < by1 - 0.3:
                clash.append((txt[a][3][:30], txt[b][3][:30]))
    assert signature(recs) == sig_before, 'the drawing connectivity changed'
    widest = max(e[2][2] for e in boxes if e[1] in (4, 28))
    print(f'verify: {len(recs)} records, no comment past x={BORDER:.0f} (widest now {widest:.1f}), '
          f'{len(clash)} text-on-text overlaps, connectivity unchanged')
    for a, b in clash:
        print(f'    overlap: {a!r} x {b!r}')


if __name__ == '__main__':
    main(sys.argv[2])
