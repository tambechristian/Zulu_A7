# -*- coding: utf-8 -*-
"""Move VCC3V3 onto the LTC3569's 1.2 A channel (SW1) and VCC1V0 onto SW3.

Applied to Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc (Power Supplies) on
2026-09-06, after docs/power_budget.md showed VCC3V3 to be the rail short of
headroom on a 600 mA channel while VCC1V0 needed a third of the 1.2 A one.

The inductors stay on their channels: L1 (1.5 uH, DFE252010P-1R5M, 1.8 A)
already sits on SW1 and now carries VCC3V3; L3 (2.2 uH, DFE252010P-2R2M,
0.9 A) stays on SW3 and now carries VCC1V0.  So on the board only the copper
downstream of L1/L3 changes rail, and the regulator area is untouched.
Ripple: 3.3 V through 1.5 uH ~0.29 A p-p (24 % of 1.2 A), 1.0 V through
2.2 uH ~0.16 A p-p (27 % of 600 mA).  The output capacitors follow the
nodes: C80 22 uF now on the 1.2 A channel, C84 10 uF on the 600 mA one, which
is the datasheet's own pairing.

Edits, all on sheet 1:
  * net labels at the inductor outputs: VCC1V0 (803,1072) -> VCC3V3,
    VCC3V3 (803,992) -> VCC1V0
  * feedback dividers (VFB = 0.8 V): R65/R66 30K/120K -> 180K/57.6K so FB1
    regulates 3.3 V; R71/R73 180K/57.6K -> 30K/120K so FB3 regulates 1.0 V
  * enables: EN1 was tied to VU (always on) and EN3 to EN_BIAS.  The rails
    keep their enables, so the pins swap: EN3 (buck 3 = VCC1V0) goes to the
    VU bus through the RT stub, EN1 (buck 1 = VCC3V3) goes to EN_BIAS.
    VCC1V0 therefore still rises first, as UG483 recommends.
  * a dated note above U8
"""
import sys, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))

def label_at(b, text, x, y):
    return b.startswith(b'|RECORD=25|') and field(b, 'Text') == text and field(b, 'Location.X') == str(x) and field(b, 'Location.Y') == str(y)

def wire_pts(b, pts):
    if not b.startswith(b'|RECORD=27|'):
        return False
    n = int(field(b, 'LocationCount') or 0)
    got = [(field(b, f'X{i}'), field(b, f'Y{i}')) for i in range(1, n + 1)]
    return got == [(str(x), str(y)) for x, y in pts]

def set_wire(b, pts):
    for i, (x, y) in enumerate(pts, 1):
        b = set_field(b, f'X{i}', str(x))
        b = set_field(b, f'Y{i}', str(y))
    return b

def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    comps = {i: b for i, (h, b) in enumerate(recs) if b.startswith(b'|RECORD=1|')}
    desig = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    done = []
    values = {'R65': ('30K 1%', '180K 1%'), 'R66': ('120K 1%', '57.6K 1%'),
              'R71': ('180K 1%', '30K 1%'), 'R73': ('57.6K 1%', '120K 1%')}
    for rec in recs:
        b = rec[1]
        # rail labels at the inductor outputs
        if label_at(b, 'VCC1V0', 803, 1072):
            rec[1] = set_field(b, 'Text', 'VCC3V3'); done.append('label VCC1V0->VCC3V3 at L1'); continue
        if label_at(b, 'VCC3V3', 803, 992):
            rec[1] = set_field(b, 'Text', 'VCC1V0'); done.append('label VCC3V3->VCC1V0 at L3'); continue
        # feedback resistor values (Comment parameter and any other parameter carrying the value)
        if b.startswith(b'|RECORD=41|') and field(b, 'OwnerIndex') is not None:
            d = desig.get(int(field(b, 'OwnerIndex')) + 1)
            if d in values and field(b, 'Text') == values[d][0]:
                rec[1] = set_field(b, 'Text', values[d][1]); done.append(f'{d} {values[d][0]} -> {values[d][1]}'); continue
        # EN1 stub: start at x=385 instead of 395
        if wire_pts(b, [(395, 977), (445, 977)]):
            rec[1] = set_wire(b, [(385, 977), (445, 977)]); done.append('EN1 stub'); continue
        # EN3 stub: start at x=405
        if wire_pts(b, [(395, 957), (445, 957)]):
            rec[1] = set_wire(b, [(405, 957), (445, 957)]); done.append('EN3 stub'); continue
        # the vertical that tied EN1 to the VU bus now ties EN3 to it (through the RT stub at y=997)
        if wire_pts(b, [(395, 977), (395, 997)]):
            rec[1] = set_wire(b, [(405, 957), (405, 997)]); done.append('EN3 -> VU bus'); continue
        # the vertical that tied EN3 to EN_BIAS now ties EN1 to it (onto the EN_BIAS wire at y=907)
        if wire_pts(b, [(395, 907), (395, 957)]):
            rec[1] = set_wire(b, [(385, 907), (385, 977)]); done.append('EN1 -> EN_BIAS'); continue
        # the EN_BIAS label rode on that vertical
        if label_at(b, 'EN_BIAS', 395, 920):
            rec[1] = set_field(b, 'Location.X', '385'); done.append('EN_BIAS label moved'); continue
    # junctions where the two new verticals end on other wires, and a dated note
    new = [
        f'|RECORD=29|OwnerPartId=-1|Location.X=385|Location.Y=907|Color=128|Locked=T|UniqueID={uid()}',
        f'|RECORD=29|OwnerPartId=-1|Location.X=405|Location.Y=997|Color=128|Locked=T|UniqueID={uid()}',
        '|RECORD=4|OwnerPartId=-1|Location.X=445|Location.Y=1092|Orientation=0|Color=8421504|FontID=3|Text=2026-09-06: VCC3V3 moved to SW1 (1.2A buck), VCC1V0 to SW3 (600mA). L1/L3, C80/C84 stay; R65/R66 and R71/R73 swapped; EN1/EN3 swapped so VCC1V0 still rises first. See docs/power_budget.md|UniqueID=' + uid(),
    ]
    for body in new:
        recs.append([b'\x00\x00\x00\x00', body.encode() + b'\x00'])
    hdr = recs[0][1]
    recs[0][1] = set_field(hdr, 'Weight', str(int(field(hdr, 'Weight')) + len(new)))
    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    expected = 11
    print(f'{len(done)} edits: {done}')
    if len(done) != expected:
        raise SystemExit(f'expected {expected} edits, check the sheet')

if __name__ == '__main__':
    main(sys.argv[2])
