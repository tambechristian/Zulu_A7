"""Sheet 4 (zulu_a7_4.SchDoc), 2026-11-25: DONE LED LD5 + series resistor R135 (user request, Cmod A7 style).

WHY.  The FPGA holds DONE (ball U12, net FPGA-DONE) low until configuration completes, then releases it; the
existing pull-up is R4 elements G+H in series (2 x 100 R = 200 R to VCC3V3, net DONE-PU), exactly Digilent's
Cmod A7 R30. A LED + series R from FPGA-DONE to GND lights once the FPGA is configured, whatever the bitstream.
LD5 = Lite-On LTST-C191KFKT (orange 605 nm AlInGaP, VF ~1.9-2.0 V at 4 mA; user's colour choice; same LTST-C191
family and 0603 land as LD1-LD4); R135 = 140 R 0201
(RC0201FR-07140RL, same BOM line as R12/R16).  I = (3.3 - 1.9) / (200 + 140) = 4.1 mA; DONE then sits at
3.3 - 200 x 4.1 mA = 2.48 V, above VIH 2.0 V of bank 0 (DONE's own startup) and of the FT2232H that reads DONE
through R4-B. While unconfigured, DONE sinks 3.3/200 = 16.5 mA as it already does today.

WHAT.  Clones: R24 (this sheet, R-US_SMALLR0201, pins 1 left / 2 right at +-10) -> R135, LD3 (sheet 1, LED, rotated
so A is up at +20 and K down at -20) -> LD5. Block in the empty window x 680..900, y 600..745:
  label FPGA-DONE (730,690) -- wire -- R135 pin 1 (750,690) R135 (760,690) pin 2 (770,690) -- wire -- LD5 A (820,690)
  LD5 (820,670) K (820,650) -- wire -- label GND (820,630); a 2-line caption at (690,740)/(690,728).
The R135-LD5 node is unlabelled (Altium names it from a pin); the PCB side takes the net name from the ECO.
Append-only; header Weight rewritten; refuses to run twice; read back and verified.

    python tools/done_led_sch.py          (then reopen sheet 4 in Altium from the Projects tree)
"""
import os
import random
import re
import string
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Imported zulu_a7.PrjPcb')
TARGET = os.path.join(ROOT, 'zulu_a7_4.SchDoc')
SHEET1 = os.path.join(ROOT, 'zulu_a7_1.SchDoc')
WINDOW = (680, 900, 600, 745)
WIRE_STYLE = 'LineWidth=1|Color=32768'
COORD = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+|Corner\.X|Corner\.Y)=(-?\d+)')
UIDRE = re.compile(rb'\|UniqueID=[A-Z]{8}')
# three short lines: the sheet frame ends at x ~900 (the first 2-line draft ran past it and was rewrapped in place)
CAPTION = [(690, 744, 'DONE LED LD5 (orange): on once FPGA configured'),
           (690, 732, '(DONE released; R4 G+H = 200R pull-up). R135'),
           (690, 720, '140R: ~4 mA, DONE high ~2.5 V; as Cmod A7.')]
R_NOTE = 'DONE LED series resistor: FPGA-DONE (pin 1) to LD5 anode (pin 2). With R4 G+H (200R) to VCC3V3: ~4.1 mA.'
LD_NOTE = ('DONE LED: lights when DONE (U1 ball U12) is released after configuration; R135 140R from FPGA-DONE, '
           'cathode to GND. Off while unconfigured or while PROG_B holds the FPGA in reset.')
LD_SPEC = 'orange 605 nm AlInGaP, VF ~2.0 V -- FPGA configured (DONE high)'   # user 2026-11-25: orange

rng = random.Random(1125)


def uid():
    return ''.join(rng.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    return UIDRE.sub(lambda m: b'|UniqueID=' + uid().encode(), b)


def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        v += dx if (k in (b'Location.X', b'Corner.X') or k.startswith(b'X')) else dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD.sub(rep, b)


def num(b, k):
    v = field(b, k)
    return int(v) if v not in (None, '') else None


def template(sheet, ref):
    src = split(read_stream(sheet))
    root = [owner(b) for h, b in src if field(b, 'RECORD') == '34' and field(b, 'Text') == ref]
    assert len(root) == 1, (ref, root)
    return src, sorted(subtree(src, root))


def fonts(R):
    return [b for h, b in R if field(b, 'RECORD') == '31'][0]


def main():
    raw = read_stream(TARGET)
    recs = split(raw)
    N = len(recs)
    assert join(recs) == raw
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header Weight is already wrong'
    for s in os.listdir(ROOT):
        if s.endswith('.SchDoc'):
            t = {field(b, 'Text') for h, b in split(read_stream(os.path.join(ROOT, s))) if field(b, 'RECORD') == '34'}
            if {'R135', 'LD5'} & t:
                raise SystemExit('already applied or designator clash on %s' % s)
    x0, x1, y0, y1 = WINDOW
    for i, (h, b) in enumerate(recs):
        for kx, ky in (('Location.X', 'Location.Y'), ('X1', 'Y1'), ('X2', 'Y2')):
            x, y = num(b, kx), num(b, ky)
            if x is not None and y is not None and x0 <= x <= x1 and y0 <= y <= y1 and not field(b, 'IsHidden'):
                raise SystemExit('the window is not clear: record %d (%s) at (%d, %d)' % (i, field(b, 'RECORD'), x, y))
    out = [[h, b] for h, b in recs]
    idx = 1 + max(num(b, 'IndexInSheet') or 0 for h, b in recs if field(b, 'RECORD') == '1')

    def add(body):
        out.append([bytes(4), (body if isinstance(body, bytes) else body.encode('latin-1')) + b'\x00'])
        return len(out) - 1

    def clone(sheet, ref, new_ref, cx, cy, params, expect_pins, note, idx_in_sheet, fontmap=None):
        # fontmap {template FontID: target FontID} for fonts numbered differently on the two sheets (LD3's designator
        # font 8 on sheet 1 = Courier 7 pt rotated 90; sheet 4 has no such font: use 3, Courier 8 pt, as R24's
        # designator does). Every other font used must be identical on both sheets.
        fontmap = fontmap or {}
        src, tree = template(sheet, ref)
        for k in sorted({int(v) for i in tree for v in re.findall(rb'\|FontID=(\d+)', src[i][1])}):
            if k in fontmap:
                continue
            for p in ('Size', 'FontName', 'Rotation', 'Bold', 'Italic'):
                assert field(fonts(src), '%s%d' % (p, k)) == field(fonts(recs), '%s%d' % (p, k)), (ref, 'font', k, p)
        base = src[tree[0]][1]
        bx, by = num(base, 'Location.X'), num(base, 'Location.Y')
        pins = {field(src[i][1], 'Designator'): (num(src[i][1], 'Location.X') - bx, num(src[i][1], 'Location.Y') - by)
                for i in tree if field(src[i][1], 'RECORD') == '2'}
        assert pins == expect_pins, (ref, pins)
        dx, dy = cx - bx, cy - by
        pos, pin_uid, seen = {}, {}, set()
        for i in tree:
            b = src[i][1]
            if field(b, 'RECORD') == '41' and field(b, 'Name') in ('HiddenNetName', 'NOTE'):
                continue
            b2 = shift(new_uid(b[:-1] if b.endswith(b'\x00') else b), dx, dy)
            b2 = re.sub(rb'\|FontID=(\d+)', lambda m: b'|FontID=%d' % fontmap.get(int(m.group(1)), int(m.group(1))), b2)
            o = owner(b)
            if o is not None:
                b2 = set_field(b2, 'OwnerIndex', str(pos[o] - 1))
            rec = field(b2, 'RECORD')
            if rec == '1':
                b2 = set_field(b2, 'IndexInSheet', str(idx_in_sheet))
            if rec == '2':
                pin_uid[i] = field(b2, 'UniqueID')
            if rec == '34':
                b2 = set_field(b2, 'Text', new_ref)
            if rec == '41':
                nm = field(b2, 'Name')
                if nm in params:
                    b2 = set_field(b2, 'Text', params[nm])
                    seen.add(nm)
                elif nm == 'PinUniqueId':
                    b2 = set_field(b2, 'Text', pin_uid[o])
            pos[i] = add(b2)
        assert seen == set(params), (ref, sorted(set(params) - seen))
        add('|RECORD=41|OwnerIndex=%d|IndexInSheet=-1|OwnerPartId=1|Color=8421504|FontID=1|IsHidden=T|Text=%s|'
            'Name=NOTE|UniqueID=%s' % (pos[tree[0]] - 1, note, uid()))

    # R135 was 140R first; 1K chosen 2026-11-25 for VIH margin at the FT2232H (docs/done_led.md)
    clone(TARGET, 'R24', 'R135', 760, 690, {'Comment': '1K', 'MANF#': 'RC0201FR-071KL'},
          {'1': (-10, 0), '2': (10, 0)}, R_NOTE, idx)
    clone(SHEET1, 'LD3', 'LD5', 820, 670, {'SPEC': LD_SPEC, 'MANF#': 'LTST-C191KFKT', 'Comment': 'orange'}, {'A': (0, 20), 'K': (0, -20)}, LD_NOTE, idx + 1,
          fontmap={8: 3})
    for xa, ya, xb, yb in ((730, 690, 750, 690), (770, 690, 820, 690), (820, 650, 820, 630)):
        add('|RECORD=27|OwnerPartId=-1|%s|UniqueID=%s|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d'
            % (WIRE_STYLE, uid(), xa, ya, xb, yb))
    add('|RECORD=25|OwnerPartId=-1|Location.X=730|Location.Y=690|Justification=2|Color=128|FontID=3|Text=FPGA-DONE|'
        'UniqueID=%s' % uid())
    add('|RECORD=25|OwnerPartId=-1|Location.X=820|Location.Y=630|Color=128|FontID=3|Text=GND|UniqueID=%s' % uid())
    for x, y, t in CAPTION:
        add('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=8421504|FontID=3|Text=%s|UniqueID=%s'
            % (x, y, t, uid()))
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(TARGET, blob)
    assert read_stream(TARGET) == blob
    print('zulu_a7_4.SchDoc: %d -> %d records (+%d)' % (N, len(out), len(out) - N))


if __name__ == '__main__':
    main()
