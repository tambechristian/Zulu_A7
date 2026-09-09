# -*- coding: utf-8 -*-
"""Sheet 4, 2026-09-09: four cosmetic moves, no change to connectivity.

R3 GOES ON TOP OF RST#. R3 is the PROGRAM_B pull-up (tools/r3_pullup_c39_out.py moved its lower end
to VCC3V3 earlier today). It was still drawn hanging BELOW the RST# wire on a 110-unit stub, with
the rail label at the bottom, which reads like a pull-DOWN. It now stands on the RST# wire itself,
body above it, rail label above that: the shape every pull-up on this sheet has. The symbol is
mirrored about its own origin -- orientation 3 becomes 1 and the two pin conglomerates swap, so pin
1 still lands on RST# and pin 2 still ends at VCC3V3 -- and the long stub wire is deleted. The rail
label stops being the rotated font-4 one the earlier script cloned and becomes a horizontal font-3
one, matching R1's.

R1 MOVES UP 60. R3 now occupies x 747 from y 442 to 492, and R1's FPGA-INIT# wire ran straight
through that at y 462. R1, its two wires and both its labels move up together; nothing else lives
above them until y 760.

C41 TURNS OVER AND COMES DOWN BESIDE C40. C40 and C41 are the FT2232H's VPHY and VPLL bypasses.
C40 hung below its node with ground at the bottom; C41 hung above its node with ground at the TOP,
so the pair read as opposites. C41 is now drawn exactly like C40 -- orientation 1, pin 1 pointing
down -- and sits at the same height, so the two ground symbols stand side by side at y 1067 and the
two capacitors hang from their nodes in the same direction. The capacitor symbol is symmetric about
its origin, so turning it over moves no line.

C40 SLIDES RIGHT 40 to make that room (the two were 12 units apart), and its FT-VPHY net label goes
with it to keep the same gap from the drop. Everything around C40 carries sub-unit _Frac offsets
from the EAGLE import -- three junctions and a 0.04-unit wire hold that node together at three
different fractional positions -- so the whole cluster is translated by a whole number of units with
every _Frac left alone. Do not try to tidy it: the fractions are what connect it.

One wire is deleted, so every later OwnerIndex is renumbered and the header count rewritten.
The netlist must come out identical to the one before this ran. Refuses to run twice.

    python tools/sheet4_layout.py tools "Imported zulu_a7.PrjPcb/zulu_a7_4.SchDoc"
"""
import sys, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

R3_MIRROR = 774                          # y_new = 774 - y_old: mirror about the origin, 332 -> 442
R3_OLD_STUB = ((747, 282), (747, 292))   # rail stub under the old position
R3_NEW_STUB = ((747, 482), (747, 492))
R3_OLD_LABEL = (747, 282)
R3_NEW_LABEL = (747, 492)
R3_DEAD_WIRE = ((747, 332), (747, 442))  # the long stub down from RST# to the old R3
R1_DY = 60
R1_WIRES = {((712, 472), (712, 462), (777, 462)), ((712, 512), (712, 522))}
R1_LABELS = {(712, 522): 'VCC3V3', (777, 462): 'FPGA-INIT#'}
C41_DY = -50
C41_PORT = (252, 1157)                   # ground, above the capacitor, orientation 1
C41_NEW_PORT = (252, 1067)
C41_WIRES = {((252, 1147), (252, 1157)): ((252, 1067), (252, 1077)),      # ground stub, now below
             ((252, 1122), (252, 1127)): ((252, 1097), (252, 1122))}      # node stub, now longer
C41_COMMENT = (262, 1068)                # its old spot now falls on the wire L4 feeds
C40_DX = 40
C40_X = 264                              # every object of that cluster sits at integer x 264
C40_LABEL = (312, 1107)                  # FT-VPHY, travels with it


def num(b, k):
    v = field(b, k)
    return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def wire_pts(b):
    if not b.startswith(b'|RECORD=27|'):
        return None
    n = num(b, 'LocationCount') or 0
    return tuple((num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1))


def subtree(recs, root):
    members, changed = {root}, True
    while changed:
        changed = False
        for i, (h, b) in enumerate(recs):
            if owner_list_index(b) in members and i not in members:
                members.add(i); changed = True
    return members


def shift_y(b, dy):
    """Add dy to every y in the record. Leaves _Frac fields alone (they are sub-unit offsets)."""
    b = re.sub(rb'\|Location\.Y=(-?\d+)', lambda m: b'|Location.Y=' + str(int(m.group(1)) + dy).encode(), b)
    return re.sub(rb'\|(Y\d+)=(-?\d+)', lambda m: b'|' + m.group(1) + b'=' + str(int(m.group(2)) + dy).encode(), b)


def shift_x(b, dx):
    b = re.sub(rb'\|Location\.X=(-?\d+)', lambda m: b'|Location.X=' + str(int(m.group(1)) + dx).encode(), b)
    return re.sub(rb'\|(X\d+)=(-?\d+)', lambda m: b'|' + m.group(1) + b'=' + str(int(m.group(2)) + dx).encode(), b)


def mirror_y(b, about):
    b = re.sub(rb'\|Location\.Y=(-?\d+)', lambda m: b'|Location.Y=' + str(about - int(m.group(1))).encode(), b)
    return re.sub(rb'\|(Y\d+)=(-?\d+)', lambda m: b'|' + m.group(1) + b'=' + str(about - int(m.group(2))).encode(), b)


def has_frac(b):
    return b'_Frac=' in b


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    where = {d: i for i, d in desig.items() if d in ('R1', 'R3', 'C40', 'C41')}
    assert set(where) == {'R1', 'R3', 'C40', 'C41'}, sorted(where)
    if num(recs[where['R3']][1], 'Location.Y') == 442:
        raise SystemExit('sheet 4 is already laid out this way; nothing done')
    assert num(recs[where['R3']][1], 'Location.Y') == 332, 'R3 is not where this script expects it'
    assert num(recs[where['R1']][1], 'Location.Y') == 472, 'R1 is not where this script expects it'
    assert num(recs[where['C40']][1], 'Location.X') == 264, 'C40 is not where this script expects it'
    assert num(recs[where['C41']][1], 'Location.Y') == 1137, 'C41 is not where this script expects it'
    r3, r1, c40, c41 = (subtree(recs, where[d]) for d in ('R3', 'R1', 'C40', 'C41'))
    for i in r3:                     # only the mirror needs whole numbers; translations keep _Frac
        assert not has_frac(recs[i][1]), f'record {i} carries a _Frac; the R3 mirror cannot handle that'

    out, kill, done = [], None, set()
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        p = wire_pts(b)
        xy = (num(b, 'Location.X'), num(b, 'Location.Y'))

        if i in r3:                                            # ---- R3, mirrored about its origin
            b = mirror_y(b, R3_MIRROR)
            if b.startswith(b'|RECORD=1|'):
                assert field(b, 'Orientation') == '3'
                b = set_field(b, 'Orientation', '1')
            elif b.startswith(b'|RECORD=2|'):
                c = {'49': '51', '51': '49'}[field(b, 'PinConglomerate')]
                b = set_field(b, 'PinConglomerate', c)
            elif b.startswith(b'|RECORD=34|'):                 # designator, placed like R1's
                b = set_field(set_field(b, 'Location.X', '756'), 'Location.Y', '472')
            elif b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'Comment':
                b = set_field(set_field(b, 'Location.X', '766'), 'Location.Y', '472')
            done.add('r3')
        elif i in r1:                                          # ---- R1, straight up
            b = shift_y(b, R1_DY)
            done.add('r1')
        elif i in c41:                                         # ---- C41, turned over and dropped
            b = shift_y(b, C41_DY)
            if b.startswith(b'|RECORD=1|'):
                assert field(b, 'Orientation') == '3'
                b = set_field(b, 'Orientation', '1')
            elif b.startswith(b'|RECORD=2|'):
                c = {'33': '35', '35': '33'}[field(b, 'PinConglomerate')]
                b = set_field(b, 'PinConglomerate', c)
            elif b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'Comment':
                b = set_field(set_field(b, 'Location.X', str(C41_COMMENT[0])),
                              'Location.Y', str(C41_COMMENT[1]))
            done.add('c41')
        elif i in c40:                                         # ---- C40, right; _Frac untouched
            if num(b, 'Location.X') is not None and num(b, 'Location.Y') is None:
                pass                                           # positionless import junk (x=7)
            else:
                b = shift_x(b, C40_DX)
            done.add('c40')
        elif oi is None:                                       # ------------- loose objects
            if p == R3_DEAD_WIRE:
                kill = i; done.add('dead wire'); continue
            elif p == R3_OLD_STUB:
                b = set_field(set_field(set_field(set_field(
                    b, 'X1', str(R3_NEW_STUB[0][0])), 'Y1', str(R3_NEW_STUB[0][1])),
                    'X2', str(R3_NEW_STUB[1][0])), 'Y2', str(R3_NEW_STUB[1][1]))
                done.add('r3 stub')
            elif b.startswith(b'|RECORD=25|') and xy == R3_OLD_LABEL and field(b, 'Text') == 'VCC3V3':
                b = set_field(set_field(set_field(set_field(
                    b, 'Location.X', str(R3_NEW_LABEL[0])), 'Location.Y', str(R3_NEW_LABEL[1])),
                    'Orientation', '0'), 'FontID', '3')        # horizontal, in R1's style
                done.add('r3 label')
            elif p in R1_WIRES:
                b = shift_y(b, R1_DY); done.add('r1 wires')
            elif b.startswith(b'|RECORD=25|') and R1_LABELS.get(xy) == field(b, 'Text'):
                b = shift_y(b, R1_DY); done.add('r1 labels')
            elif p in C41_WIRES:
                q = C41_WIRES[p]
                b = set_field(set_field(set_field(set_field(
                    b, 'X1', str(q[0][0])), 'Y1', str(q[0][1])), 'X2', str(q[1][0])), 'Y2', str(q[1][1]))
                done.add('c41 wires')
            elif b.startswith(b'|RECORD=17|') and xy == C41_PORT and field(b, 'Text') == 'GND':
                b = set_field(set_field(set_field(
                    b, 'Location.X', str(C41_NEW_PORT[0])), 'Location.Y', str(C41_NEW_PORT[1])),
                    'Orientation', '3')                        # symbol below the wire, like C40's
                done.add('c41 port')
            elif b.startswith(b'|RECORD=25|') and xy == C40_LABEL and field(b, 'Text') == 'FT-VPHY':
                b = shift_x(b, C40_DX); done.add('c40 label')
            elif p and any(x == C40_X for x, y in p):
                assert all(y > 1000 for x, y in p), f'wire {p} is at x {C40_X} but not in the C40 cluster'
                b = re.sub(rb'\|(X\d+)=264\b', lambda m: b'|' + m.group(1) + b'=' + str(C40_X + C40_DX).encode(), b)
                done.add('c40 wires')
            elif xy[0] == C40_X and xy[1] is not None:
                assert xy[1] > 1000, f'object at {xy} is at x {C40_X} but not in the C40 cluster'
                b = shift_x(b, C40_DX); done.add('c40 loose')
        out.append([h, b])

    want = {'r3', 'r1', 'c41', 'c40', 'dead wire', 'r3 stub', 'r3 label', 'r1 wires', 'r1 labels',
            'c41 wires', 'c41 port', 'c40 label', 'c40 wires', 'c40 loose'}
    assert done == want, sorted(want ^ done)
    assert kill is not None

    newpos = {old: new for new, old in enumerate(i for i in range(N) if i != kill)}
    fixed = []
    for old, (h, b) in zip((i for i in range(N) if i != kill), out):
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} is owned by the deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        fixed.append([h, b])
    fixed[0][1] = set_field(fixed[0][1], 'Weight', str(len(fixed) - 1))
    blob = join(fixed)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 4: {N} -> {len(fixed)} records (1 wire deleted)')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is not None:
            assert 0 <= oi < len(recs) and recs[oi][1].startswith(
                (b'|RECORD=1|', b'|RECORD=2|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi)
    desig = {owner_list_index(b): field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
    at = {d: recs[i][1] for i, d in desig.items() if d in ('R1', 'R3', 'C40', 'C41')}
    assert (num(at['R3'], 'Location.X'), num(at['R3'], 'Location.Y')) == (747, 442), 'R3 is not on RST#'
    assert field(at['R3'], 'Orientation') == '1', 'R3 still points down'
    assert (num(at['R1'], 'Location.X'), num(at['R1'], 'Location.Y')) == (712, 532), 'R1 did not move'
    assert (num(at['C40'], 'Location.X'), num(at['C40'], 'Location.Y')) == (304, 1087), 'C40 did not move'
    assert (num(at['C41'], 'Location.X'), num(at['C41'], 'Location.Y')) == (252, 1087), 'C41 did not move'
    assert field(at['C41'], 'Orientation') == '1', 'C41 did not turn over'

    def ends(d):                                   # the two electrical ends of a two-pin part
        i = [k for k, v in desig.items() if v == d][0]
        e = []
        for h, b in recs:
            if b.startswith(b'|RECORD=2|') and owner_list_index(b) == i:
                x, y = num(b, 'Location.X'), num(b, 'Location.Y')
                dx, dy = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}[int(field(b, 'PinConglomerate')) & 3]
                n = int(field(b, 'PinLength'))
                e.append((x + dx * n, y + dy * n))
        return sorted(e)
    assert ends('R3') == [(747, 442), (747, 482)], ends('R3')
    assert ends('R1') == [(712, 532), (712, 572)], ends('R1')
    assert ends('C40') == [(304, 1077), (304, 1097)], ends('C40')
    assert ends('C41') == [(252, 1077), (252, 1097)], ends('C41')

    wires = {wire_pts(b) for h, b in recs if b.startswith(b'|RECORD=27|')}
    ports = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text')
             for h, b in recs if b.startswith(b'|RECORD=17|')}
    labels = {(num(b, 'Location.X'), num(b, 'Location.Y')): field(b, 'Text')
              for h, b in recs if b.startswith(b'|RECORD=25|') and owner_list_index(b) is None}
    juncs = {(num(b, 'Location.X'), num(b, 'Location.Y')) for h, b in recs if b.startswith(b'|RECORD=29|')}
    assert R3_DEAD_WIRE not in wires, 'the long R3 stub survived'
    assert R3_NEW_STUB in wires and labels.get(R3_NEW_LABEL) == 'VCC3V3', 'R3 lost its rail'
    assert ((632, 442), (747, 442)) in wires and ((747, 442), (777, 442)) in wires and (747, 442) in juncs, \
        'the RST# wire under R3 is not intact'
    assert ((712, 532), (712, 522), (777, 522)) in wires and labels.get((777, 522)) == 'FPGA-INIT#', 'R1 lost INIT#'
    assert ((712, 572), (712, 582)) in wires and labels.get((712, 582)) == 'VCC3V3', 'R1 lost its rail'
    assert ports.get((252, 1067)) == 'GND' and ports.get((304, 1067)) == 'GND', 'the two grounds are not side by side'
    assert ((252, 1067), (252, 1077)) in wires and ((252, 1097), (252, 1122)) in wires, 'C41 is not wired'
    assert ((304, 1067), (304, 1077)) in wires, 'C40 is not wired'
    assert ((237, 1122), (252, 1122)) in wires and (252, 1122) in juncs, 'the VPLL node moved'
    assert labels.get((352, 1107)) == 'FT-VPHY', 'the FT-VPHY label did not follow C40'
    print(f'verify: {len(recs)} records, R3 stands on RST# under a VCC3V3 label, R1 is 60 higher, '
          'C40 and C41 hang side by side over two ground symbols at y 1067')


if __name__ == '__main__':
    main(sys.argv[2])
