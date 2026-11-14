"""READ-ONLY probe behind si/series_r/schematic_plan.md (2026-11-13). Writes nothing outside stdout.

    python si/series_r/schematic_probe.py > si/series_r/schematic_probe.txt

Reads the seven SchDocs (FileHeader via olefile), the PcbDoc (Components6/Nets6/Classes6/Rules6 via olefile) and
the Rev 2 XDC, and prints every fact the plan quotes: U3's DQ pins and the net labels on them (sheet 3), the D0-D15
labels on U1 (sheet 5) against the XDC, every R designator on the schematic and the board, net-name collisions for
the proposed names, the free block on sheet 3, the template's font IDs, and file-integrity counters.
"""
import collections
import re
import sys

import olefile

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, owner, read_stream, split  # noqa: E402

REV2 = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/'
PRJ = REV2 + 'Imported zulu_a7.PrjPcb/'
PCB = PRJ + 'Zulu_a7_no_pmod.PcbDoc'
XDC = REV2 + 'si/vivado/zulu_a7_no_pmod.xdc'
PROPOSED = ['SDRAM-D%d' % k for k in range(16)]
BLOCK = (45, 540, 340, 698)          # sheet-3 window for the resistor block (x0, x1, y0, y1), 10 mil units


def n(b, k):
    v = field(b, k)
    return int(v) if v not in (None, '') else None


def sheet(s):
    return split(read_stream(PRJ + 'zulu_a7_%d.SchDoc' % s))


def hot_end(b):
    """electrical end of a pin: Location + PinLength along the PinConglomerate rotation (bits 0-1)"""
    L = n(b, 'PinLength') or 0
    rot = int(field(b, 'PinConglomerate') or 0) & 3
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][rot]
    return n(b, 'Location.X') + dx * L, n(b, 'Location.Y') + dy * L


def label_to_pins(R, ref):
    """{label text: [(pin designator, hot end)]} for labels joined to ref's placed pins by plain wires"""
    des = {owner(b): field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34'}
    hot = {}
    for h, b in R:
        if field(b, 'RECORD') != '2':
            continue
        o = owner(b)
        if des.get(o) == ref and n(b, 'OwnerPartId') == n(R[o][1], 'CurrentPartId'):
            hot[hot_end(b)] = field(b, 'Designator')
    wires = [[(n(b, 'X%d' % j), n(b, 'Y%d' % j)) for j in range(1, n(b, 'LocationCount') + 1)]
             for h, b in R if field(b, 'RECORD') == '27']
    out = {}
    for h, b in R:
        if field(b, 'RECORD') != '25':
            continue
        pts, grew = {(n(b, 'Location.X'), n(b, 'Location.Y'))}, True
        while grew:
            grew = False
            for w in wires:
                if any(q in pts for q in w):
                    for q in w:
                        if q not in pts:
                            pts.add(q)
                            grew = True
        pins = [(hot[q], q) for q in pts if q in hot]
        if pins:
            out.setdefault(field(b, 'Text'), []).extend(pins)
    return out


def main():
    S = {s: sheet(s) for s in range(7)}
    print('== integrity (all sheets)')
    for s, R in S.items():
        u = collections.Counter(field(b, 'UniqueID') for h, b in R if field(b, 'UniqueID'))
        print('sheet %d: %d records, Weight=%s, records without NUL %d, binary records %d, duplicate UniqueIDs %d' % (
            s, len(R), field(R[0][1], 'Weight'), sum(not b.endswith(b'\x00') for h, b in R),
            sum(h[3] != 0 for h, b in R), sum(v > 1 for v in u.values())))

    print('\n== sheet 3: U3 DQ pins and the labels on them')
    R3 = S[3]
    lab3 = label_to_pins(R3, 'U3')
    for k in range(16):
        print('D%d' % k, lab3.get('D%d' % k))
    for i, (h, b) in enumerate(R3):
        if field(b, 'RECORD') == '25' and re.fullmatch(r'D\d+', field(b, 'Text') or ''):
            print('  label record %d %s at (%s, %s) Justification=%s FontID=%s' % (
                i, field(b, 'Text'), field(b, 'Location.X'), field(b, 'Location.Y'), field(b, 'Justification'),
                field(b, 'FontID')))

    print('\n== sheet 5: U1 balls on D0-D15, against the XDC')
    lab5 = label_to_pins(S[5], 'U1')
    xdc = dict(re.findall(r'PACKAGE_PIN (\w+)\s.*get_ports \{(D\d+)\}', open(XDC).read()))
    xdc = {v: k for k, v in xdc.items()}
    for k in range(16):
        balls = [p for p, q in lab5.get('D%d' % k, [])]
        print('D%d ball %s  XDC %s  %s' % (k, balls, xdc.get('D%d' % k), 'OK' if balls == [xdc.get('D%d' % k)] else 'MISMATCH'))
    other = [s for s in range(7) if s not in (3, 5) and any(
        field(b, 'RECORD') == '25' and re.fullmatch(r'D\d+', field(b, 'Text') or '') for h, b in S[s])]
    print('D-labels on other sheets:', other or 'none')

    print('\n== net names: every net label / power port text, all sheets; collisions with the proposal')
    names = set()
    for R in S.values():
        names |= {field(b, 'Text') for h, b in R if field(b, 'RECORD') in ('25', '17')}
    o = olefile.OleFileIO(PCB)

    def recs(name):
        return [m.group(0).decode('latin-1') for m in re.finditer(rb'\|[^\x00]*', o.openstream(name).read())]

    def f(t, k):
        m = re.search(r'\|' + re.escape(k) + r'=([^|]*)', t, re.I)
        return m.group(1) if m else None
    pnets = {f(x, 'NAME') for x in recs('Nets6/Data')}
    print('schematic names %d, PCB nets %d; proposed names already used: %s' % (
        len(names), len(pnets), sorted((names | pnets) & set(PROPOSED)) or 'none'))
    print('SDRAM-prefixed names now:', sorted(x for x in names | pnets if x and x.startswith('SDRAM')))

    print('\n== R designators')
    sch = set()
    for R in S.values():
        sch |= {field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34' and re.fullmatch(r'R\d+', field(b, 'Text') or '')}
    pcb = {f(x, 'SOURCEDESIGNATOR') for x in recs('Components6/Data')}
    pcbr = {d for d in pcb if d and re.fullmatch(r'R\d+', d)}
    key = lambda d: int(d[1:])  # noqa: E731
    print('schematic R:', len(sch), sorted(sch, key=key))
    print('PCB R:', len(pcbr), 'same set' if pcbr == sch else 'DIFFER %s' % sorted(pcbr ^ sch))
    print('highest R: %d; R119-R134 used anywhere: %s' % (
        max(map(key, sch | pcbr)), sorted({'R%d' % k for k in range(119, 135)} & (sch | pcbr)) or 'none'))

    print('\n== PCB classes and rules that name the data bus')
    for c in recs('Classes6/Data'):
        mem = re.findall(r'\|M\d+=([^|]*)', c)
        if any(re.fullmatch(r'D\d+', m) for m in mem):
            print('class', f(c, 'NAME'), mem)
    for r in recs('Rules6/Data'):
        s = (f(r, 'SCOPE1EXPRESSION') or '') + ' | ' + (f(r, 'SCOPE2EXPRESSION') or '')
        if 'SDRAM' in s or re.search(r"InNet\('D\d", s):
            print('rule', f(r, 'RULEKIND'), f(r, 'NAME'), s)

    print('\n== sheet-3 block window %s: objects inside (frame excluded)' % (BLOCK,))
    x0, x1, y0, y1 = BLOCK
    des = {owner(b): field(b, 'Text') for h, b in R3 if field(b, 'RECORD') == '34'}
    C = re.compile(rb'\|(Location\.X|Location\.Y|Corner\.X|Corner\.Y|X\d+|Y\d+)=(-?\d+)')
    hits = 0
    for i, (h, b) in enumerate(R3):
        if field(b, 'RECORD') == '2' or (field(b, 'RECORD') == '41' and field(b, 'IsHidden')):
            continue
        xs, ys = [], []
        for k, v in C.findall(b):
            (xs if (k.endswith(b'X') or k.startswith(b'X')) else ys).append(int(v))
        if not xs:
            continue
        if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
            continue
        root = owner(b)
        while root is not None and owner(R3[root][1]) is not None:
            root = owner(R3[root][1])
        if root is not None and (des.get(root) or '').startswith('FRAME'):
            continue
        hits += 1
        print('  record %d RECORD=%s %s' % (i, field(b, 'RECORD'), (field(b, 'Text') or '')[:60]))
    print('objects in the window:', hits)

    print('\n== template R24 (sheet 4) and the font tables')
    R4 = S[4]
    ci = [owner(b) for h, b in R4 if field(b, 'RECORD') == '34' and field(b, 'Text') == 'R24'][0]
    tree = [i for i, (h, b) in enumerate(R4) if i == ci or owner(b) == ci or (owner(b) is not None and owner(R4[owner(b)][1]) == ci)]
    fonts = sorted({int(v) for i in tree for v in re.findall(rb'FontID=(\d+)', R4[i][1])})
    print('R24 subtree records', len(tree), 'FontIDs used', fonts,
          'HiddenNetName children', sum(field(R4[i][1], 'Name') == 'HiddenNetName' for i in tree))
    ft = {s: [x for x in S[s] if field(x[1], 'RECORD') == '31'][0][1] for s in (3, 4)}
    for k in fonts:
        a = [field(ft[s], '%s%d' % (p, k)) for s in (3, 4) for p in ('Size', 'FontName', 'Rotation')]
        print('  font %d sheet3 %s / sheet4 %s -> %s' % (k, a[:3], a[3:], 'same' if a[:3] == a[3:] else 'DIFFERENT'))
    print('R24 params:', {field(R4[i][1], 'Name'): field(R4[i][1], 'Text') for i in tree
                          if field(R4[i][1], 'RECORD') == '41' and field(R4[i][1], 'Name') in (
                              'MANF', 'MANF#', 'SPEC', 'Comment', 'DeviceName', 'LibraryName')})
    print('R24 pins (designator, hot end):', [(field(R4[i][1], 'Designator'), hot_end(R4[i][1])) for i in tree
                                                if field(R4[i][1], 'RECORD') == '2'],
          'body at', (field(R4[ci][1], 'Location.X'), field(R4[ci][1], 'Location.Y')))


if __name__ == '__main__':
    main()
