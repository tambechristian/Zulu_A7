# -*- coding: utf-8 -*-
"""LD0: Victory VS NRD8 (maker-direct only) -> Everlight EAST1616RGBA8, 2026-09-08.

Sheet 2. EAST1616RGBA8 is Everlight's 19-337/R6GHBHW-A01/2T (datasheet DSE-0009126 Rev.3,
22-Dec-2016): 1.6 x 1.6 x 0.35 mm, three independent diodes, diffused lens. Its package page
is the VS NRD8 page line for line: same body, same recommended pads (0.55 x 0.4 outer at
+-0.725, 0.7 x 0.5 middle, 1.9 / 2.2 mm spans) and the same physical arrangement, cathodes in
the left column under the cathode mark (blue, red, green top to bottom) and anodes on the
right. Only the pad NUMBERS differ: Victory 1/2/3 cathodes and 4/5/6 anodes, Everlight 2/4/6
cathodes and 1/3/5 anodes. So the six pins are renumbered and nothing else moves: LED0_B/R/G
stay on the cathodes (now 2/4/6, to the FPGA), N$LD0B/R/G on the anodes (now 1/3/5, through
R80/R81/R82). Footprint model renamed EVERLIGHT-19-337 (the VS-NRD8 pattern with Everlight's
numbers). Refuses to run twice.

    python tools/ld0_east1616.py tools "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"
"""
import sys
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

PINMAP = {'1': '2', '2': '4', '3': '6', '4': '1', '5': '3', '6': '5'}   # Victory number -> Everlight number
NEW_MPN = 'EAST1616RGBA8'
SPEC = ('RGB LED, three independent diodes, 1.6 x 1.6 x 0.35 mm, diffused lens, 624 / 525 / 468 nm, VF typ 2.05 / 3.2 / 3.2 V '
        '(max 2.4 / 3.7 / 3.7), IF 25 mA max per colour; anodes 1 B, 3 R, 5 G, cathodes 2 B, 4 R, 6 G (19-337 sheet p8); '
        'replaced the distributor-less Victory VS NRD8 on 2026-09-08')
NOTE = ('Everlight EAST1616RGBA8 = 19-337/R6GHBHW-A01/2T (DSE-0009126 Rev.3, 22-Dec-2016); water-clear twin EAST1616RGBA4 = '
        '19-337/R6GHBHC-A01/2T. Same body, lens and recommended pads as the Victory VS NRD8 it replaces (0.55 x 0.4 outer pads at '
        '+-0.725 mm, 0.7 x 0.5 middle, 1.9 / 2.2 mm spans) and the same arrangement: cathodes in the left column under the cathode '
        'mark, blue / red / green top to bottom, anodes on the right. Only the numbering differs (Everlight anodes 1/3/5 on the '
        'right, cathodes 2/4/6 on the left), so on 2026-09-08 the pins were renumbered 1/2/3 -> 2/4/6 and 4/5/6 -> 1/3/5 with the '
        'nets unchanged: LED0_B/R/G on the cathodes to the FPGA, N$LD0B/R/G on the anodes through R80/R81/R82. Footprint '
        'EVERLIGHT-19-337 = the VS-NRD8 pattern with Everlight pad numbers. Digi-Key 15,840 in stock at $0.43 on 2026-09-08.')
DESC = 'RGB LED, three independent diodes, 6 pads: anodes 1/3/5 (B/R/G), cathodes 2/4/6 (B/R/G). Everlight 19-337 package.'


def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    des = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    comp = [i for i, d in des.items() if d == 'LD0']
    assert len(comp) == 1, comp
    ci = comp[0]; obj = ci - 1
    assert recs[ci][1].startswith(b'|RECORD=1|')
    prm, pins = {}, []
    for i, (h, b) in enumerate(recs):
        oi = field(b, 'OwnerIndex')
        if oi is None or int(oi) != obj: continue
        if b.startswith(b'|RECORD=41|'): prm[field(b, 'Name')] = i
        elif b.startswith(b'|RECORD=2|'): pins.append(i)
    assert field(recs[prm['MANF#']][1], 'Text') == 'VS NRD8', 'already applied'
    assert sorted(field(recs[i][1], 'Designator') for i in pins) == ['1', '2', '3', '4', '5', '6']
    for i in pins:
        b = recs[i][1]
        old = field(b, 'Designator'); new = PINMAP[old]
        b = set_field(b, 'Designator', new)
        if field(b, 'Name') == old: b = set_field(b, 'Name', new)
        recs[i][1] = b
    recs[prm['MANF']][1] = set_field(recs[prm['MANF']][1], 'Text', 'Everlight')
    recs[prm['MANF#']][1] = set_field(recs[prm['MANF#']][1], 'Text', NEW_MPN)
    recs[prm['SPEC']][1] = set_field(recs[prm['SPEC']][1], 'Text', SPEC)
    recs[prm['NOTE']][1] = set_field(recs[prm['NOTE']][1], 'Text', NOTE)
    recs[prm['Comment']][1] = set_field(recs[prm['Comment']][1], 'Text', NEW_MPN)
    recs[ci][1] = set_field(recs[ci][1], 'ComponentDescription', DESC)
    i44 = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=44|') and int(field(b, 'OwnerIndex')) == obj]
    i45 = [i for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=45|') and int(field(b, 'OwnerIndex')) == i44[0] - 1]
    assert len(i44) == 1 and len(i45) == 1
    assert field(recs[i45[0]][1], 'ModelName') == 'VS-NRD8'
    recs[i45[0]][1] = set_field(recs[i45[0]][1], 'ModelName', 'EVERLIGHT-19-337')
    out = join(recs)
    assert len(split(out)) == len(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print(f'LD0 -> {NEW_MPN}: pins renumbered {PINMAP}, footprint EVERLIGHT-19-337')


if __name__ == '__main__':
    main(sys.argv[2])
