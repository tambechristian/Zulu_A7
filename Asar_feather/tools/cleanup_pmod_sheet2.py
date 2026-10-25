"""Remove what the deleted Pmod J1 left behind on asar_a7_2.SchDoc (2026-10-23, user request).

apply_feather_schematic.py's cleanup kept these because the wires touch each other, so none looked dangling:
  - the VCC3V3 power port at (230, 414), its seven wires to J1's old pins 6/12 hot spots (270/340, 424) and the
    junction at (260, 404);
  - the text frame "Digilent 12-pin Pmod (JA) ..." describing J1.
It also rewrites the HiddenNetName tags on R26-R28's pins (PMOD-n / JAn, left from the import) to the nets the
pins now carry. Those tags do not change connectivity; the pins are not hidden.
Each target is matched by content, and the script refuses unless it finds exactly what it expects.
Check afterwards with check_feather_schematic.py (the netlist must not change).
    python tools/cleanup_pmod_sheet2.py      (close asar_a7_2.SchDoc in Altium first)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sch_netlist import num  # noqa: E402
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Asar_feather.PrjPcb', 'asar_a7_2.SchDoc')
WIRES = {((230, 404), (260, 404)), ((230, 404), (230, 414)), ((340, 424), (360, 424)), ((260, 424), (270, 424)),
         ((260, 404), (260, 424)), ((260, 404), (360, 404)), ((360, 404), (360, 424))}
TAGS = {('R26', '1'): 'VU', ('R26', '2'): 'EN', ('R27', '1'): 'GND', ('R27', '2'): 'USB-CC1',
        ('R28', '1'): 'GND', ('R28', '2'): 'USB-CC2'}


def pt(b, k):
    return (num(b, 'X%d' % k), num(b, 'Y%d' % k))


def main():
    recs = split(read_stream(PATH))
    drop = set()
    for i, (h, b) in enumerate(recs):
        r = field(b, 'RECORD')
        if r == '17' and field(b, 'Text') == 'VCC3V3' and (num(b, 'Location.X'), num(b, 'Location.Y')) == (230, 414):
            drop.add(i)
        elif r == '27' and field(b, 'LocationCount') == '2' and tuple(sorted((pt(b, 1), pt(b, 2)))) in {tuple(sorted(w)) for w in WIRES}:
            drop.add(i)
        elif r == '29' and (num(b, 'Location.X'), num(b, 'Location.Y')) == (260, 404):
            drop.add(i)
        elif r == '28' and (field(b, 'Text') or '').startswith('Digilent 12-pin Pmod (JA)'):
            drop.add(i)
    kinds = sorted(field(recs[i][1], 'RECORD') for i in drop)
    if kinds != ['17', '27', '27', '27', '27', '27', '27', '27', '28', '29']:
        sys.exit('REFUSED: expected port + 7 wires + junction + note, found RECORD %s' % kinds)

    refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
    tagged = 0
    for i, (h, b) in enumerate(recs):
        if field(b, 'RECORD') != '41' or field(b, 'Name') != 'HiddenNetName':
            continue
        pin = owner(b)
        if field(recs[pin][1], 'RECORD') != '2':
            continue
        key = (refs.get(owner(recs[pin][1])), field(recs[pin][1], 'Designator'))
        if key in TAGS:
            recs[i][1] = set_field(b, 'Text', TAGS[key])
            tagged += 1
    if tagged != len(TAGS):
        sys.exit('REFUSED: retagged %d of %d pins' % (tagged, len(TAGS)))

    out = delete(recs, drop)
    write_stream(PATH, join(out))
    print('asar_a7_2.SchDoc: removed %d records (VCC3V3 port, 7 wires, junction, Pmod note); %d pin tags renamed; '
          '%d -> %d records' % (len(drop), tagged, len(recs), len(out)))


if __name__ == '__main__':
    main()
