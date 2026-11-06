# -*- coding: utf-8 -*-
"""Sheet 5, 2026-09-09: the grey ball captions are regenerated from the pins they annotate.

THE DEFECT. Beside every FPGA pin row on sheet 5 is a grey caption of the form "<ball>  <pin
function>", e.g. "C8  TCK_0". They were written when the pins were first assigned and never touched
again, so they survived the re-pin. Checked two ways before this ran:

  * against the live pin on each row: 42 captions right, 94 wrong;
  * against the exported netlist, asking whether the caption's ball is one of the U1 balls carrying
    that row's net: 34 right, 102 wrong.

The failures are coherent, which is what makes it certain rather than a measurement artefact.
SD-DAT2's row is captioned W2, a ball that really carries SDRAM-CS#. CHAN0's row says W3, which
carries CAS#. CHAN2's says W5, which carries D5. Worst is the Pmod block, whose captions claim balls
A14, A15 and W7: those three carry SDRAM D14, D15 and D2, so three balls read as double-booked on
one page, and the symbol's own pin NAMES still say IO_A14, IO_A15 and IO_W7.

The pin designators -- the authoritative half of each row -- are correct throughout. It is the
caption text that is stale, and sheet 5 is the page a layout engineer reads ball assignments from.

THE FIX. For each caption, find the live pin on its row (same y, first one to the right), take that
pin's designator as the ball, and look the ball up in Datasheet/xc7a35tcpg236pkg_pinout.txt for the
function name -- the same file tools/bom_audit.py already checks the power tree against, and the
source the original captions were copied from, in the same "<ball>  <name>" shape. A caption whose
row has no live pin, or whose ball is not in the pinout file, is left alone and reported.

"Live pin" matters here: U1 is placed 139 times on this sheet and every placement carries the whole
236-ball pin set as children, so a naive search finds thousands of pins at any coordinate. Only the
pins whose OwnerPartId equals their placement's CurrentPartId are drawn and connected.

Text only. No record is added or removed, no Location changes, so the netlist must come out
identical. Refuses to run twice.

    python tools/sheet5_ball_captions.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

CAPTION = re.compile(r'^([A-Z]{1,2}\d{1,2})\s\s+(\S+)\s*$')
ROW_TOL = 3          # a caption and its pin sit within this many units in y
MAX_DX = 260         # and the pin is this far to the right at most


def oi(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def num(b, k):
    v = field(b, k)
    return int(v) if v is not None else None


def load_pinout(path):
    xl = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        p = line.split()
        if len(p) >= 2 and re.fullmatch(r'[A-Z]{1,2}\d{1,2}', p[0]):
            xl[p[0]] = p[1]
    return xl


def live_pins(recs):
    cur = {i: field(b, 'CurrentPartId') for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|')}
    desig = {oi(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    out = []
    for h, b in recs:
        if not b.startswith(b'|RECORD=2|'):
            continue
        p = oi(b)
        if p not in cur or field(b, 'OwnerPartId') != cur[p]:
            continue
        d = field(b, 'Designator')
        if d and re.fullmatch(r'[A-Z]{1,2}\d{1,2}', d) and desig.get(p) == 'U1':
            out.append((num(b, 'Location.X'), num(b, 'Location.Y'), d))
    return out


def main(prj):
    path = os.path.join(prj, 'zulu_a7_5.SchDoc')
    pinout = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(prj))),
                          'Datasheet', 'xc7a35tcpg236pkg_pinout.txt')
    if not os.path.exists(pinout):
        pinout = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), '..', 'Datasheet',
                              'xc7a35tcpg236pkg_pinout.txt')
    xl = load_pinout(pinout)
    assert len(xl) > 200, f'the pinout file looks wrong: {len(xl)} balls'

    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    pins = live_pins(recs)
    assert 130 < len(pins) < 160, f'{len(pins)} live U1 pins on sheet 5, expected about 138'

    changed, already, orphan, unknown = 0, 0, [], []
    for i, (h, b) in enumerate(recs):
        if not b.startswith(b'|RECORD=4|'):
            continue
        t = field(b, 'Text') or ''
        m = CAPTION.match(t)
        if not m:
            continue
        cx, cy = num(b, 'Location.X'), num(b, 'Location.Y')
        row = [p for p in pins if abs(p[1] - cy) <= ROW_TOL and 0 < (p[0] - cx) <= MAX_DX]
        if not row:
            orphan.append((t, cx, cy)); continue
        row.sort(key=lambda p: p[0] - cx)
        ball = row[0][2]
        func = xl.get(ball)
        if not func:
            unknown.append((t, ball)); continue
        want = f'{ball}  {func}'
        if t.strip() == want:
            already += 1
            continue
        recs[i][1] = set_field(b, 'Text', want)
        changed += 1

    if not changed:
        raise SystemExit('every caption already names the pin on its row; nothing done')
    assert len(recs) == N
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 5: {changed} captions rewritten, {already} were already right')
    for t, cx, cy in orphan:
        print(f'   left alone, no live pin on its row: {t!r} at ({cx},{cy})')
    for t, ball in unknown:
        print(f'   left alone, ball {ball} is not in the package file: {t!r}')
    verify(path, xl)


def verify(path, xl):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    pins = live_pins(recs)
    agree = disagree = 0
    bad = []
    for h, b in recs:
        if not b.startswith(b'|RECORD=4|'):
            continue
        t = field(b, 'Text') or ''
        m = CAPTION.match(t)
        if not m:
            continue
        cx, cy = num(b, 'Location.X'), num(b, 'Location.Y')
        row = [p for p in pins if abs(p[1] - cy) <= ROW_TOL and 0 < (p[0] - cx) <= MAX_DX]
        if not row:
            continue
        row.sort(key=lambda p: p[0] - cx)
        if m.group(1) == row[0][2] and m.group(2) == xl.get(row[0][2]):
            agree += 1
        else:
            disagree += 1
            bad.append((t, row[0][2]))
    assert not disagree, f'{disagree} captions still disagree with their pin: {bad[:5]}'
    print(f'verify: all {agree} captions name the ball on their own row, with the function the '
          'package file gives it')


if __name__ == '__main__':
    main(sys.argv[2])
