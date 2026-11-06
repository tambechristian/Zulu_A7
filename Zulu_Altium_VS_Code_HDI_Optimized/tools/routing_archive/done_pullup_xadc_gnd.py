# -*- coding: utf-8 -*-
"""2026-09-10: two wires, found by the I/O-planner audit, that Vivado could never have found.

Both are connectivity changes, so both are checked the same way: the drawing's own connectivity
signature before and after, then the netlist exported from Altium, which must move exactly two pads
and nothing else.

1. THE DONE READBACK SITS ON A DIVIDER.

   As drawn:   VCC3V3 --R100 330-- [DONE] --R4 100-- [FPGA-DONE] -- U1-U12
                                     |
                                   U2-22 (FT2232H ADBUS5)

   The netlist says `DONE = {R4-2, R100-1, U2-22}` and `FPGA-DONE = {R4-15, U1-U12}`. R4-2 and R4-15
   are the two ends of one element of the 100 R array (isolated array, pad k joins pad 17-k), so the
   pull-up and the FT2232H input are on the SAME side of the series resistor and the FPGA's DONE
   ball is on the other. That makes a divider, and ADBUS5 reads its midpoint rather than DONE.

   Unconfigured, the FPGA holds DONE low, so the node sits at 3.3 * 100/430 = 0.767 V against the
   FT2232H's 0.80 V VIL max -- 33 mV of margin before any tolerance is spent. The CTS 742C163 is
   +-5 %: 105 R gives 0.797 V, and 330 R at -5 % as well gives 0.828 V, which is over. A host tool
   can then report DONE High with the part unconfigured.

   As UG470 figure 2-14 draws it, the pull-up belongs at the DONE ball and the series resistor
   between the ball and whatever is watching:

   Fixed:      VCC3V3 --R100 330-- [FPGA-DONE] -- U1-U12
                                        |
                                     R4 100
                                        |
                                     [DONE] -- U2-22

   With nothing else on the DONE side, no current flows in the 100 R and ADBUS5 reads the ball.

   THE EDIT. R100 keeps its place in the pull-up row; what changes is which net its wire is named
   for. The wire (607,932)-(812,932)-(812,1032) carried U2-22 all the way to R100 with a `DONE`
   label at 640. It becomes two stubs: (607,932)-(662,932) keeps the `DONE` label and U2-22, and
   (760,932)-(812,932)-(812,1032) takes R100 with a new `FPGA-DONE` label at its free end. Free ends
   carrying a label are this sheet's own idiom -- `DONE` at (572,422) and `FPGA-DONE` at (777,422)
   are drawn exactly that way -- and the U2 stub now matches the TCK row above it.

   Note the DONE row is deliberately no longer drawn like its PROG#/TMS/TDI/TDO neighbours, which do
   run one wire from the U2 pin to their pull-up. Those have no series element; DONE does, and the
   whole point is which side of it the pull-up sits on.

2. C124 RETURNS THE XADC SUPPLY TO DIGITAL GROUND.

   The XADC rail is VCC1V8 through L7 (600 R bead) to VCCADC, decoupled by C123 100nF and C124
   470nF. `C123-2` is on GNDADC, correctly. `C124-2` is on GND: its return runs to a ground symbol
   at (535,222) named GND rather than GNDADC.

   That does two things at once. It puts L6's 600 R inside C124's decoupling loop, so the larger of
   the two caps returns its ripple the long way round through the analog-to-digital ground tie; and
   C123 in series with C124 bridges GNDADC to GND at AC, which is the one thing the two beads exist
   to prevent. One port's name is wrong, not one wire's route: the symbol is already at the end of
   C124's own return wire, so its Text goes from GND to GNDADC and it draws as an analog ground.

Refuses to run twice.

    python tools/done_pullup_xadc_gnd.py tools "Imported zulu_a7.PrjPcb"
"""
import sys, os, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field
from sheet5_right_margin import num, rectype, points, fonts_of, drawn_boxes, signature

# --- 1. sheet 4, the DONE row ---------------------------------------------------------------
WIRE_OLD = ((607, 932), (812, 932), (812, 1032))
WIRE_NEW = ((760, 932), (812, 932), (812, 1032))
STUB_NEW = ((607, 932), (662, 932))
STUB_LIKE = ((607, 982), (662, 982))          # the TCK stub, copied for style
LABEL_LIKE = (777, 422, 'FPGA-DONE')          # the existing FPGA-DONE label, copied for style
LABEL_NEW = (760, 932)

# --- 2. sheet 5, the XADC return ---------------------------------------------------------------
PORT_AT = (535, 222)
PORT_OLD, PORT_NEW = 'GND', 'GNDADC'


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', lambda m: b'|UniqueID=' + uid().encode(), b)


def set_pts(b, pts):
    b = re.sub(rb'\|(X|Y)\d+(_Frac)?=[^|\x00]*', b'', b)
    tail = ''.join(f'|X{k}={x}|Y{k}={y}' for k, (x, y) in enumerate(pts, 1))
    b = set_field(b, 'LocationCount', str(len(pts)))
    return b[:-1] + tail.encode() + b'\x00'


def one(recs, pred, what):
    hit = [i for i, (h, b) in enumerate(recs) if pred(b)]
    assert len(hit) == 1, f'{what}: found {len(hit)}, expected 1'
    return hit[0]


def sheet4(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    if not any(rectype(b) == 27 and tuple(points(b)) == WIRE_OLD for h, b in recs):
        raise SystemExit('the DONE pull-up has already been moved; nothing done')
    sig = signature(recs)

    w = one(recs, lambda b: rectype(b) == 27 and tuple(points(b)) == WIRE_OLD, 'the DONE wire')
    stub = one(recs, lambda b: rectype(b) == 27 and tuple(points(b)) == STUB_LIKE, 'the TCK stub')
    lab = one(recs, lambda b: rectype(b) == 25 and field(b, 'Text') == LABEL_LIKE[2]
              and num(b, 'Location.X') == LABEL_LIKE[0]
              and num(b, 'Location.Y') == LABEL_LIKE[1], 'the FPGA-DONE label')
    keep = one(recs, lambda b: rectype(b) == 25 and field(b, 'Text') == 'DONE'
               and num(b, 'Location.Y') == 932, 'the DONE label on the U2 stub')

    recs[w][1] = set_pts(recs[w][1], WIRE_NEW)
    add_wire = set_pts(new_uid(recs[stub][1]), STUB_NEW)
    add_lab = new_uid(recs[lab][1])
    add_lab = set_field(set_field(add_lab, 'Location.X', str(LABEL_NEW[0])),
                        'Location.Y', str(LABEL_NEW[1]))
    recs.append([bytes(4), add_wire])
    recs.append([bytes(4), add_lab])
    recs[0][1] = set_field(recs[0][1], 'Weight', str(len(recs) - 1))
    print(f'  sheet 4: the DONE wire {WIRE_OLD[0]}..{WIRE_OLD[-1]} split -- U2-22 keeps '
          f'{STUB_NEW} with its DONE label at x{num(recs[keep][1], "Location.X")}, R100 takes '
          f'{WIRE_NEW} as FPGA-DONE')
    return recs, sig, N


def sheet5(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    i = [j for j, (h, b) in enumerate(recs)
         if rectype(b) == 17 and num(b, 'Location.X') == PORT_AT[0]
         and num(b, 'Location.Y') == PORT_AT[1]]
    assert len(i) == 1, f'the port at {PORT_AT}: found {len(i)}'
    i = i[0]
    if field(recs[i][1], 'Text') != PORT_OLD:
        raise SystemExit(f"C124's return is already named "
                         f"{field(recs[i][1], 'Text')}; nothing done")
    sig = signature(recs)
    recs[i][1] = set_field(recs[i][1], 'Text', PORT_NEW)
    print(f"  sheet 5: C124's return port at {PORT_AT} renamed {PORT_OLD} -> {PORT_NEW}")
    return recs, sig, N


def save(path, recs, sig, N0, expect):
    blob = join(recs)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    back = split(read_stream(path, 'FileHeader'))
    assert int(field(back[0][1], 'Weight')) == len(back) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in back), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in back if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    after = signature(back)
    moved = [n for n in set(map(tuple, sig)) ^ set(map(tuple, after))]
    fonts = fonts_of(back)
    print(f'    {N0} -> {len(back)} records, {len(drawn_boxes(back, fonts))} drawn objects, '
          f'{len(moved)} connectivity nodes changed')
    for n in sorted(moved):
        print(f'      {"was " if list(n) in sig else "now "}{n}')
    assert moved, 'nothing changed in the drawing connectivity'
    for e in expect:
        assert any(e in ' '.join(n) for n in moved), f'expected {e} among the changed nodes'


def main(prj):
    p4 = os.path.join(prj, 'zulu_a7_4.SchDoc')
    p5 = os.path.join(prj, 'zulu_a7_5.SchDoc')
    recs, sig, N = sheet4(p4)
    save(p4, recs, sig, N, ['R100-1', 'U2-22'])
    recs, sig, N = sheet5(p5)
    save(p5, recs, sig, N, ['C124-2'])
    print('\nnow export the netlist from Altium: FPGA-DONE must gain R100-1, DONE must lose it, '
          'GND must lose C124-2 and GNDADC gain it, and nothing else may move.')


if __name__ == '__main__':
    main(sys.argv[2])
