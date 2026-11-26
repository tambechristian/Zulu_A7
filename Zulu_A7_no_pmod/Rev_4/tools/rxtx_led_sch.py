"""Sheet 4 (zulu_a7_4.SchDoc), 2026-11-25: UART activity LED LD6 (yellow) + R136 1K, the Cmod A7 way (user request).

WHY.  FT2232H channel B runs in UART mode; its BCBUS3 (pin 54) = RXLED# and BCBUS4 (pin 55) = TXLED# pulse low on
receive / transmit. The Cmod A7 (reconstructed sheet 5, reference/cmod_a7_usb_prog) ties both pins straight to one
LED cathode (its net RX_TX = IC6-54, IC6-55, LD4-K; LD4 anode via R60 from VCC3V3) -- FTDI's single-LED arrangement,
no diodes. Same here: VCC3V3 - R136 1K - LD6 (A -> K) - net FT-RXTX-LED = U2-54 + U2-55.
LD6 = Lite-On LTST-C191KSKT (yellow 591 nm AlInGaP 0603, the LD1-LD5 family and land); R136 = RC0201FR-071KL (1K,
the R11/R135 BOM line). I = (3.3 - ~1.9 - VOL) / 1k ~ 1.3 mA while a pin pulses low, LD3/LD4/LD5 level.

WHAT.
- The No-ERC crosses on U2-54 / U2-55 (607,682) / (607,672) are deleted; both pins get a 10-unit stub to x 617 and
  a vertical wire 617,682-617,672 carrying the net label FT-RXTX-LED at (617,677).
- Clones of R135 -> R136 and LD5 -> LD6 (same sheet, same fonts) in the empty window x 845..900, y 585..680:
  label VCC3V3 (855,675) -- wire -- R136 pin 1 (855,665) / pin 2 (875,665) -- wire -- LD6 A (875,645),
  LD6 (875,625), K (875,605) -- wire to (875,595) with label FT-RXTX-LED (right-justified).
Refuses to run twice; header Weight rewritten; read back and verified.

    python tools/rxtx_led_sch.py          (then reopen sheet 4 in Altium from the Projects tree)
"""
import os
import random
import re
import string
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import delete, field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Imported zulu_a7.PrjPcb')
TARGET = os.path.join(ROOT, 'zulu_a7_4.SchDoc')
NET = 'FT-RXTX-LED'
WINDOW = (845, 900, 585, 680)
WIRE_STYLE = 'LineWidth=1|Color=32768'
COORD = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+|Corner\.X|Corner\.Y)=(-?\d+)')
UIDRE = re.compile(rb'\|UniqueID=[A-Z]{8}')
R_NOTE = 'UART activity LED series resistor: VCC3V3 (pin 1) to LD6 anode (pin 2); ~1.3 mA while RXLED#/TXLED# pulse low.'
LD_NOTE = ('UART activity LED (yellow): cathode on U2 pins 54 BCBUS3 RXLED# and 55 BCBUS4 TXLED#, tied together as on '
           'the Cmod A7 (FTDI single-LED arrangement; the CBUS LED outputs only ever pull low). Channel B must stay in '
           'UART mode in the EEPROM for these pin functions.')
rng = random.Random(1126)


def uid():
    return ''.join(rng.choice(string.ascii_uppercase) for _ in range(8))


def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        v += dx if (k in (b'Location.X', b'Corner.X') or k.startswith(b'X')) else dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD.sub(rep, b)


def num(b, k):
    v = field(b, k)
    return int(v) if v not in (None, '') else None


def main():
    raw = read_stream(TARGET)
    recs = split(raw)
    assert join(recs) == raw
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header Weight is already wrong'
    for s in os.listdir(ROOT):
        if s.endswith('.SchDoc'):
            t = {field(b, 'Text') for h, b in split(read_stream(os.path.join(ROOT, s))) if field(b, 'RECORD') in ('34', '25')}
            if {'R136', 'LD6', NET} & t:
                raise SystemExit('already applied or designator clash on %s' % s)
    # the two No-ERC marks on U2-54 / U2-55
    noerc = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '22' and num(b, 'Location.X') == 607
             and num(b, 'Location.Y') in (682, 672)]
    assert len(noerc) == 2, noerc
    x0, x1, y0, y1 = WINDOW
    for i, (h, b) in enumerate(recs):
        for kx, ky in (('Location.X', 'Location.Y'), ('X1', 'Y1'), ('X2', 'Y2')):
            x, y = num(b, kx), num(b, ky)
            if x is not None and y is not None and x0 <= x <= x1 and y0 <= y <= y1 and not field(b, 'IsHidden'):
                raise SystemExit('the window is not clear: record %d (%s) at (%d, %d)' % (i, field(b, 'RECORD'), x, y))
    recs = delete(recs, noerc)
    N0 = len(recs)
    out = [[h, b] for h, b in recs]
    idx = 1 + max(num(b, 'IndexInSheet') or 0 for h, b in recs if field(b, 'RECORD') == '1')

    def add(body):
        out.append([bytes(4), (body if isinstance(body, bytes) else body.encode('latin-1')) + b'\x00'])
        return len(out) - 1

    def clone(ref, new_ref, cx, cy, params, note, idx_in_sheet):
        root = [owner(b) for h, b in recs if field(b, 'RECORD') == '34' and field(b, 'Text') == ref]
        assert len(root) == 1, ref
        tree = sorted(subtree(recs, root))
        base = recs[tree[0]][1]
        dx, dy = cx - num(base, 'Location.X'), cy - num(base, 'Location.Y')
        pos, pin_uid, seen = {}, {}, set()
        for i in tree:
            b = recs[i][1]
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'NOTE':
                continue
            b2 = shift(UIDRE.sub(lambda m: b'|UniqueID=' + uid().encode(), b[:-1] if b.endswith(b'\x00') else b), dx, dy)
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

    clone('R135', 'R136', 865, 665, {'Comment': '1K', 'MANF#': 'RC0201FR-071KL'}, R_NOTE, idx)
    clone('LD5', 'LD6', 875, 625, {'Comment': 'yellow', 'MANF#': 'LTST-C191KSKT',
                                   'SPEC': 'yellow 591 nm AlInGaP, VF ~2.0 V -- UART RX/TX activity (FT2232H RXLED#/TXLED#)'},
          LD_NOTE, idx + 1)
    for xa, ya, xb, yb in ((607, 682, 617, 682), (607, 672, 617, 672), (617, 682, 617, 672),
                           (855, 665, 855, 675), (875, 665, 875, 645), (875, 605, 875, 595)):
        add('|RECORD=27|OwnerPartId=-1|%s|UniqueID=%s|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d'
            % (WIRE_STYLE, uid(), xa, ya, xb, yb))
    add('|RECORD=25|OwnerPartId=-1|Location.X=617|Location.Y=677|Color=128|FontID=3|Text=%s|UniqueID=%s' % (NET, uid()))
    add('|RECORD=25|OwnerPartId=-1|Location.X=875|Location.Y=595|Justification=2|Color=128|FontID=3|Text=%s|UniqueID=%s' % (NET, uid()))
    add('|RECORD=25|OwnerPartId=-1|Location.X=855|Location.Y=675|Color=128|FontID=3|Text=VCC3V3|UniqueID=%s' % uid())
    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(TARGET, blob)
    assert read_stream(TARGET) == blob
    print('zulu_a7_4.SchDoc: -2 No-ERC, %d -> %d records' % (N0, len(out)))


if __name__ == '__main__':
    main()
