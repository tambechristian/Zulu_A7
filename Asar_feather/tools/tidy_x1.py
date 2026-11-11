"""Tidy the X1 USB connector symbol on sheet 1 (2026-11-10, user request; Zulu A7 Fab B and Asar Feather).

Since the 2026-09-10 pin-per-pad split, X1's shell pins (MH1/MH2/MP1-MP4/MS1/MS2) sit at x 230..240 with their name
"GND" drawn inside the body, on top of the names of pins 1-5. This script, with no change to the netlist:
  - moves the right edge of the shell outline (X1-owned lines/arcs at x >= 225) 20 units right,
  - moves the shell pins (Location.X 230) and the X1 designator 20 units right,
  - hides the name of every shell pin named GND (PinConglomerate bit 0x08); a shell pin with another name keeps it,
  - moves the sheet objects on the old shell-pin hot ends (x 240, y 1060..1150: the GND bus wire, its junctions, a net
    label) 20 units right.

Then (second step, --labels): the X1 designator goes to (232, 1149) above the shell, clear of the USB-CC2 label, and the
USB5V0 net label on pin 1's hot end becomes a 15-unit wire stub with the label at its left end, right-justified like
USB_D_N/USB_D_P, so its text no longer runs into the body.

    python tools/tidy_x1.py <sheet-1 SchDoc> [--labels]   (close the sheet in Altium first; writes a .pre-x1tidy backup)
"""
import shutil
import sys

sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else __file__.rsplit('/', 1)[0])
from schdoc import field, join, read_stream, set_field, split, write_stream  # noqa: E402

DX = 20
Y0, Y1 = 1060, 1150


def labels(path):
    recs = split(read_stream(path))
    hit = 0
    for i, (h, b) in enumerate(recs):
        if field(b, 'RECORD') == '34' and field(b, 'Text') == 'X1':
            b = set_field(set_field(b, 'Location.X', '232'), 'Location.Y', '1149')
            hit += 1
        elif (field(b, 'RECORD') == '25' and field(b, 'Text') == 'USB5V0' and field(b, 'Location.X') == '185'
              and field(b, 'Location.Y') == '1132'):
            b = set_field(set_field(b, 'Location.X', '170'), 'Justification', '2')
            hit += 1
        recs[i] = (h, b)
    assert hit == 2, 'expected the X1 designator and the USB5V0 label at (185, 1132); found %d' % hit
    tmpl = [r for r in recs if field(r[1], 'RECORD') == '27'][0]
    w = b'|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID=X1USBSTB|LocationCount=2|X1=170|Y1=1132|X2=185|Y2=1132' + bytes([0])
    recs.append((tmpl[0], w))
    recs[0] = (recs[0][0], set_field(recs[0][1], 'Weight', str(len(recs) - 1)))
    shutil.copyfile(path, path + '.pre-x1labels')
    write_stream(path, join(recs))
    print(path, 'designator moved, USB5V0 stub added')


def main():
    path = sys.argv[1]
    if '--labels' in sys.argv:
        return labels(path)
    data = read_stream(path)
    recs = split(data)
    comp = None
    for h, b in recs:
        if field(b, 'RECORD') == '34' and field(b, 'Text') == 'X1':
            comp = int(field(b, 'OwnerIndex'))
    assert comp is not None, 'X1 not found'
    cx = int(field(recs[comp + 1][1], 'Location.X'))
    assert cx == 205, 'X1 is not where this script expects it (Location.X %s)' % cx
    n = {'outline': 0, 'pins': 0, 'names': 0, 'sheet': 0}
    out = []
    for i, (h, b) in enumerate(recs):
        r = field(b, 'RECORD')
        o = field(b, 'OwnerIndex')
        mine = o is not None and int(o) == comp
        if mine and r == '6':
            for kx in ('X1', 'X2'):
                if int(field(b, kx)) >= 225:
                    b = set_field(b, kx, str(int(field(b, kx)) + DX))
                    n['outline'] += 1
        elif mine and r == '12':
            if int(field(b, 'Location.X')) >= 225:
                b = set_field(b, 'Location.X', str(int(field(b, 'Location.X')) + DX))
                n['outline'] += 1
        elif mine and r == '2' and int(field(b, 'Location.X')) == 230:
            b = set_field(b, 'Location.X', str(230 + DX))
            n['pins'] += 1
            if field(b, 'Name') == 'GND':
                c = int(field(b, 'PinConglomerate'))
                b = set_field(b, 'PinConglomerate', str(c & ~0x08))
                n['names'] += 1
        elif mine and r == '34':
            b = set_field(b, 'Location.X', str(int(field(b, 'Location.X')) + DX))
        elif not mine and r == '27':
            k = 1
            while field(b, 'X%d' % k) is not None:
                if int(field(b, 'X%d' % k)) == 240 and Y0 <= int(field(b, 'Y%d' % k)) <= Y1:
                    b = set_field(b, 'X%d' % k, str(240 + DX))
                    n['sheet'] += 1
                k += 1
        elif not mine and r in ('29', '25') and field(b, 'Location.X') == '240' and Y0 <= int(field(b, 'Location.Y')) <= Y1:
            b = set_field(b, 'Location.X', str(240 + DX))
            n['sheet'] += 1
        out.append((h, b))
    shutil.copyfile(path, path + '.pre-x1tidy')
    write_stream(path, join(out))
    print(path, n)


if __name__ == '__main__':
    main()
