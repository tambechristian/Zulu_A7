# -*- coding: utf-8 -*-
"""Sheet 0 block diagram, 2026-09-09: the charger and the battery connector get their blocks.

The diagram still showed USB VBUS feeding the regulators directly, which stopped being true when
the bq24232 replaced D1 (sheet 1, 2026-09-09). This inserts two blocks in the empty band above the
Voltage Regulators, in the same style as the rest of the sheet (110 x 70 outline, FontID 2 title,
FontID 4 net labels, the sheet's own 10 x 10 arrowheads):

    USB Port --+5V--> [ PMIC BQ24232 ] <--VBATT--> [ LiPo Connect ]
                            |
                           VU
                            v
                   [ Voltage Regulators ]

The +5V riser out of the USB port is extended from y 887 to y 1002 and turned into the charger's
left edge instead of the regulators'; the old stub and its arrowhead are deleted, and the +5V label
follows the corner. The charger's output drops into the top edge of the Voltage Regulators block as
VU, and the battery connector hangs off its right edge as VBATT, drawn with an arrowhead at each
end because the pack both takes charge and supplies the board.

Nothing on this sheet carries connectivity -- it is all drawing furniture, RECORD=4 text and
RECORD=6 lines with no pins or nets -- so the netlist cannot change. Deleting records renumbers
every surviving OwnerIndex (the frame component's 40 children point back at it) and the header
Weight is rewritten; verify() checks both, after a first version of this script broke sheet 0 by
skipping them and Altium refused to open it. Refuses to run twice.

    python tools/sheet0_pmic_block.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

Y = 1002                                                            # centre line of the new blocks
PMIC = (225, 967, 335, 1037)                                        # x0, y0, x1, y1
LIPO = (385, 967, 495, 1037)
VR_TOP = 922                                                        # top edge of the Voltage Regulators block
DEAD = {((215, 887), (185, 887)),                                   # the old +5V stub into the regulators
        ((215, 892), (225, 887)), ((215, 887), (215, 892)),         # and its arrowhead
        ((215, 882), (215, 887)), ((225, 887), (215, 882))}
RISER = ((185, 887), (185, 712))


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def num(b, k):
    v = field(b, k); return int(v) if v is not None else None


def seg(b):
    return ((num(b, 'X1'), num(b, 'Y1')), (num(b, 'X2'), num(b, 'Y2'))) if b.startswith(b'|RECORD=6|') else None


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    if any(field(b, 'Text') == 'BQ24232' for h, b in recs):
        raise SystemExit('the PMIC block is already on sheet 0; nothing done')
    line_tpl = next(b for h, b in recs if b.startswith(b'|RECORD=6|'))
    text_tpl = next(b for h, b in recs if b.startswith(b'|RECORD=4|') and field(b, 'FontID') == '2')
    idx = max(n for n in (num(b, 'IndexInSheet') for h, b in recs) if n is not None)
    kill, found = set(), set()
    for i, (h, b) in enumerate(recs):
        s = seg(b)
        if s in DEAD:
            kill.add(i); found.add(s)
        elif s == RISER:
            recs[i][1] = set_field(b, 'Y1', str(Y))                 # the riser now reaches the charger
            found.add('riser')
        elif b.startswith(b'|RECORD=4|') and field(b, 'Text') == '+5V':
            recs[i][1] = set_field(set_field(b, 'Location.X', '160'), 'Location.Y', str(Y - 5))
            found.add('+5V')
    assert found == DEAD | {'riser', '+5V'}, found

    # deleting records shifts every later list index, so each surviving OwnerIndex has to follow;
    # the frame component's 40 children live near the end of the file and all point back at it
    keep = [i for i in range(len(recs)) if i not in kill]
    newpos = {old: new for new, old in enumerate(keep)}
    out = []
    for old_i in keep:
        h, b = recs[old_i]
        o = field(b, 'OwnerIndex')
        if o is not None:
            oi = int(o) + 1
            assert oi in newpos, f'record {old_i} is owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        out.append([h, b])

    def line(x1, y1, x2, y2):
        nonlocal idx
        idx += 1
        b = line_tpl
        for k, v in (('IndexInSheet', idx), ('X1', x1), ('Y1', y1), ('X2', x2), ('Y2', y2)):
            b = set_field(b, k, str(v))
        out.append([bytes(4), set_field(b, 'UniqueID', uid())])

    def text(x, y, s, font='2'):
        nonlocal idx
        idx += 1
        b = text_tpl
        for k, v in (('IndexInSheet', idx), ('Location.X', x), ('Location.Y', y), ('FontID', font), ('Text', s)):
            b = set_field(b, k, str(v))
        out.append([bytes(4), set_field(b, 'UniqueID', uid())])

    def box(x0, y0, x1, y1):
        line(x0, y0, x0, y1); line(x0, y1, x1, y1); line(x1, y1, x1, y0); line(x1, y0, x0, y0)

    def arrow(x, y, d):
        """the sheet's own arrowhead: tip at (x, y), 10 back, 10 across; d = 'r', 'l' or 'd'"""
        if d == 'r':
            line(x - 10, y + 5, x, y); line(x - 10, y, x - 10, y + 5); line(x - 10, y - 5, x - 10, y); line(x, y, x - 10, y - 5)
        elif d == 'l':
            line(x + 10, y + 5, x, y); line(x + 10, y, x + 10, y + 5); line(x + 10, y - 5, x + 10, y); line(x, y, x + 10, y - 5)
        else:
            line(x - 5, y + 10, x, y); line(x, y + 10, x - 5, y + 10); line(x + 5, y + 10, x, y + 10); line(x, y, x + 5, y + 10)

    box(*PMIC); text(266, Y + 5, 'PMIC'); text(256, Y - 10, 'BQ24232')
    box(*LIPO); text(398, Y - 5, 'LiPo Connect')
    line(185, Y, PMIC[0] - 10, Y); arrow(PMIC[0], Y, 'r')                       # USB +5V into the charger
    cx = (PMIC[0] + PMIC[2]) // 2
    line(cx, PMIC[1], cx, VR_TOP + 10); arrow(cx, VR_TOP, 'd'); text(cx + 8, 947, 'VU', '4')
    arrow(PMIC[2], Y, 'l'); line(PMIC[2] + 10, Y, LIPO[0] - 10, Y); arrow(LIPO[0], Y, 'r')
    text(PMIC[2] + 13, Y + 10, 'VBATT', '4')

    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))   # the header carries the record count
    blob = join(out)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 0: {N} -> {len(out)} records ({len(kill)} deleted, {len(out) - N + len(kill)} added)')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header Weight does not match the record count'
    texts = {field(b, 'Text'): (num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=4|')}
    for t in ('PMIC', 'BQ24232', 'LiPo Connect', 'VU', 'VBATT', '+5V'):
        assert t in texts, t
    segs = {seg(b) for h, b in recs if b.startswith(b'|RECORD=6|')}
    for s in DEAD:
        assert s not in segs, s
    assert ((185, Y), (185, 712)) in segs, 'the +5V riser does not reach the charger'
    for x0, y0, x1, y1 in (PMIC, LIPO):                                          # both outlines closed
        for s in (((x0, y0), (x0, y1)), ((x0, y1), (x1, y1)), ((x1, y1), (x1, y0)), ((x1, y0), (x0, y0))):
            assert s in segs, s
    assert ((280, PMIC[1]), (280, VR_TOP + 10)) in segs, 'charger output does not reach the regulators'
    assert ((PMIC[2] + 10, Y), (LIPO[0] - 10, Y)) in segs, 'battery link missing'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    for i, (h, b) in enumerate(recs):                                            # every parent link resolves
        o = field(b, 'OwnerIndex')
        if o is None:
            continue
        oi = int(o) + 1
        assert 0 <= oi < len(recs), (i, oi)
        assert recs[oi][1].startswith((b'|RECORD=1|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi, recs[oi][1][:20])
    # the frame component's children reuse low IndexInSheet values, so only the loose drawing is checked
    ix = [num(b, 'IndexInSheet') for h, b in recs
          if field(b, 'OwnerIndex') is None and num(b, 'IndexInSheet') is not None and num(b, 'IndexInSheet') >= 0]
    assert len(ix) == len(set(ix)), 'duplicate IndexInSheet among the loose records'
    print(f'verify: blocks at {texts["PMIC"]} and {texts["LiPo Connect"]}, {len(segs)} line segments, ids unique')


if __name__ == '__main__':
    main(os.path.join(sys.argv[2], 'zulu_a7_0.SchDoc'))
