"""Sheet 3 (zulu_a7_3.SchDoc), 2026-11-13: the 16 SDRAM DQ series resistors R119-R134.

WHY.  docs/dq_series_resistors.md and docs/si_analysis.md: on reads, U3's full-drive DQ edges undershoot past DS181
Table 4 at U1's ball. A 22 ohm 0201 per data bit fixes it. The recipe is si/series_r/schematic_plan.md (16-resistor
version, pin orientation corrected 2026-11-13); the PCB side is si/series_r/dq_series_r_plan.json (md5 7c2b8ae6).

WHAT.
- 16 clones of R24 (sheet 4: R-US_SMALLR0201, footprint R0201), designators R119 + bit, Comment 22,
  MANF# RC0201FR-0722RL, a hidden NOTE. The template's two HiddenNetName pin parameters are dropped.
- Block in the empty window x 45..540, y 340..698: column A (D0-D7) cx 150, column B (D8-D15) cx 390, row y = 640 - 40k.
  Each row: label SDRAM-Dn -- wire -- pin 1 (left, cx-10) R pin 2 (right, cx+10) -- wire -- label Dn.
  PIN 1 = SDRAM-Dn (U3 side), PIN 2 = Dn (U1 side), matching pad 1 / pad 2 in the PCB plan.
- A 2-line caption at (60, 684) / (60, 672).
- The 16 net labels on U3's DQ stubs change text Dn -> SDRAM-Dn (found by text + location). Nothing else moves.
  Sheet 5 (U1), the XDC and the HDL keep Dn.

Append-only (no OwnerIndex moves); the header Weight is rewritten; refuses to run twice; read back and verified.

    python tools/dq_series_r_sch.py <target sheet 3> <sheet 4 (template)> [--all-sheets-dir DIR]
"""
import os
import random
import re
import string
import sys

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import field, join, owner, read_stream, set_field, split, subtree, write_stream  # noqa: E402

TEMPLATE = 'R24'
LIBREF = 'R-US_SMALLR0201'
COMMENT = '22'
MPN = 'RC0201FR-0722RL'
NOTE = 'series R on the SDRAM data net; position is SI-critical, see docs/dq_series_resistors.md'
WINDOW = (45, 540, 340, 698)
CAPTION = [(60, 684, 'U3 DQ SERIES RESISTORS R119-R134 (22 ohm): SDRAM-Dn = U3 side (pin 1), Dn = U1 side (pin 2, XDC names).'),
           (60, 672, 'Placement is SI-critical -- see NOTE and docs/dq_series_resistors.md.')]
# U3 DQ stub labels (si/series_r/schematic_plan.md section 1): bit -> (U3 pin, label location)
U3_LABELS = {0: ('2', (745, 1057)), 1: ('4', (745, 1037)), 2: ('5', (745, 1027)), 3: ('7', (745, 1007)),
             4: ('8', (745, 997)), 5: ('10', (745, 977)), 6: ('11', (745, 967)), 7: ('13', (745, 947)),
             8: ('42', (925, 947)), 9: ('44', (925, 967)), 10: ('45', (925, 977)), 11: ('47', (925, 997)),
             12: ('48', (925, 1007)), 13: ('50', (925, 1027)), 14: ('51', (925, 1037)), 15: ('53', (925, 1057))}
WIRE_STYLE = 'LineWidth=1|Color=32768'          # copied from the sheet's existing DQ stubs (record 17155)
COORD = re.compile(rb'\|(Location\.X|Location\.Y|X\d+|Y\d+)=(-?\d+)')


def parts():
    out = []
    for bit in range(16):
        cx = 150 if bit < 8 else 390
        y = 640 - 40 * (bit % 8)
        out.append(dict(bit=bit, ref='R%d' % (119 + bit), cx=cx, y=y))
    return out


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    return re.sub(rb'\|UniqueID=[A-Z]{8}', lambda m: b'|UniqueID=' + uid().encode(), b)


def shift(b, dx, dy):
    def rep(m):
        k, v = m.group(1), int(m.group(2))
        v += dx if (k == b'Location.X' or k.startswith(b'X')) else dy
        return b'|' + k + b'=' + str(v).encode()
    return COORD.sub(rep, b)


def num(b, k):
    v = field(b, k)
    return int(v) if v not in (None, '') else None


def main(target, template_sheet):
    src = split(read_stream(template_sheet))
    tpl_root = [owner(b) for h, b in src if field(b, 'RECORD') == '34' and field(b, 'Text') == TEMPLATE]
    assert len(tpl_root) == 1, tpl_root
    tree = sorted(subtree(src, tpl_root))
    base = src[tree[0]][1]
    assert field(base, 'LibReference') == LIBREF, field(base, 'LibReference')
    bx, by = num(base, 'Location.X'), num(base, 'Location.Y')
    pins = {field(src[i][1], 'Designator'): (num(src[i][1], 'Location.X') - bx, num(src[i][1], 'Location.Y') - by)
            for i in tree if field(src[i][1], 'RECORD') == '2'}
    assert pins == {'1': (-10, 0), '2': (10, 0)}, pins          # pin 1 left, pin 2 right, PinLength 0

    raw = read_stream(target)
    recs = split(raw)
    N = len(recs)
    assert join(recs) == raw
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header Weight is already wrong'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record without NUL'
    assert all(h[3] == 0 for h, b in recs), 'binary record present'
    texts = {field(b, 'Text') for h, b in recs if field(b, 'RECORD') in ('25', '17', '34')}
    clash = sorted(t for t in texts if t and (re.fullmatch(r'R(119|12\d|13[0-4])', t) or t.startswith('SDRAM-D')))
    if clash:
        raise SystemExit('already applied or name clash on the target: %s' % clash)
    x0, x1, y0, y1 = WINDOW
    for i, (h, b) in enumerate(recs):
        x, y = num(b, 'Location.X'), num(b, 'Location.Y')
        if x is not None and y is not None and x0 <= x <= x1 and y0 <= y <= y1 and field(b, 'RECORD') not in ('41',):
            raise SystemExit('the window is not clear: record %d at (%d, %d)' % (i, x, y))
    # fonts used by the template must be the same on the target
    ft = lambda R: [b for h, b in R if field(b, 'RECORD') == '31'][0]   # noqa: E731
    for k in sorted({int(v) for i in tree for v in re.findall(rb'FontID=(\d+)', src[i][1])}):
        for p in ('Size', 'FontName', 'Rotation', 'Bold', 'Italic'):
            assert field(ft(src), '%s%d' % (p, k)) == field(ft(recs), '%s%d' % (p, k)), ('font', k, p)
    # the 16 U3 labels: exactly one record each, by text and location
    lab_idx = {}
    for bit, (pin, (lx, ly)) in U3_LABELS.items():
        hits = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '25' and field(b, 'Text') == 'D%d' % bit
                and (num(b, 'Location.X'), num(b, 'Location.Y')) == (lx, ly)]
        assert len(hits) == 1, ('U3 label', bit, hits)
        lab_idx[bit] = hits[0]

    out = [[h, b] for h, b in recs]
    # each clone gets its own component IndexInSheet (the template's 68 is R34's on this sheet)
    idx0 = 1 + max(num(b, 'IndexInSheet') or 0 for h, b in recs if field(b, 'RECORD') == '1')

    def add(body):
        out.append([bytes(4), (body if isinstance(body, bytes) else body.encode('latin-1')) + b'\x00'])
        return len(out) - 1

    for p in parts():
        dx, dy = p['cx'] - bx, p['y'] - by
        pos = {}
        pin_uid = {}
        for i in tree:
            b = src[i][1]
            if field(b, 'RECORD') == '41' and field(b, 'Name') == 'HiddenNetName':
                continue
            b2 = shift(new_uid(b[:-1] if b.endswith(b'\x00') else b), dx, dy)
            o = owner(b)
            if o is not None:
                b2 = set_field(b2, 'OwnerIndex', str(pos[o] - 1))
            rec = field(b2, 'RECORD')
            if rec == '1':
                b2 = set_field(b2, 'IndexInSheet', str(idx0 + p['bit']))
                b2 = b2.replace(b' (sheet 2 only)', b'')
            if rec == '2':
                pin_uid[i] = field(b2, 'UniqueID')
            if rec == '34':
                b2 = set_field(b2, 'Text', p['ref'])
            if rec == '41':
                nm = field(b2, 'Name')
                if nm == 'Comment':
                    b2 = set_field(b2, 'Text', COMMENT)
                elif nm == 'MANF#':
                    b2 = set_field(b2, 'Text', MPN)
                elif nm == 'PinUniqueId':
                    b2 = set_field(b2, 'Text', pin_uid[o])      # invariant: PinUniqueId == its pin's UniqueID
            pos[i] = add(b2)
        add('|RECORD=41|OwnerIndex=%d|IndexInSheet=-1|OwnerPartId=1|Color=8421504|FontID=1|IsHidden=T|Text=%s|'
            'Name=NOTE|UniqueID=%s' % (pos[tree[0]] - 1, NOTE, uid()))
        cx, y, bit = p['cx'], p['y'], p['bit']
        for (xa, xb) in ((cx - 30, cx - 10), (cx + 10, cx + 30)):
            add('|RECORD=27|OwnerPartId=-1|%s|UniqueID=%s|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d'
                % (WIRE_STYLE, uid(), xa, y, xb, y))
        add('|RECORD=25|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Justification=2|Color=128|FontID=3|Text=SDRAM-D%d|'
            'UniqueID=%s' % (cx - 30, y, bit, uid()))
        add('|RECORD=25|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=128|FontID=3|Text=D%d|UniqueID=%s'
            % (cx + 30, y, bit, uid()))
    for x, y, t in CAPTION:
        add('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=8421504|FontID=3|Text=%s|UniqueID=%s'
            % (x, y, t, uid()))
    for bit, i in lab_idx.items():
        out[i][1] = set_field(out[i][1], 'Text', 'SDRAM-D%d' % bit)

    out[0][1] = set_field(out[0][1], 'Weight', str(len(out) - 1))
    blob = join(out)
    write_stream(target, blob)
    assert read_stream(target) == blob
    print('%s: %d -> %d records (+%d); 16 U3 labels renamed' % (os.path.basename(target), N, len(out), len(out) - N))
    verify(target)


def hot_end(b):
    L = num(b, 'PinLength') or 0
    rot = int(field(b, 'PinConglomerate') or 0) & 3
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][rot]
    return num(b, 'Location.X') + dx * L, num(b, 'Location.Y') + dy * L


def nets_on_sheet(R):
    """{label text: set((ref, pin))} -- labels joined to placed pins through wires on this sheet."""
    des = {owner(b): field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34'}
    hot = {}
    for h, b in R:
        if field(b, 'RECORD') != '2':
            continue
        o = owner(b)
        if num(b, 'OwnerPartId') == num(R[o][1], 'CurrentPartId'):
            hot.setdefault(hot_end(b), set()).add((des.get(o), field(b, 'Designator')))
    wires = [[(num(b, 'X%d' % j), num(b, 'Y%d' % j)) for j in range(1, num(b, 'LocationCount') + 1)]
             for h, b in R if field(b, 'RECORD') == '27']
    out = {}
    for h, b in R:
        if field(b, 'RECORD') != '25':
            continue
        pts, grew = {(num(b, 'Location.X'), num(b, 'Location.Y'))}, True
        while grew:
            grew = False
            for w in wires:
                if any(q in pts for q in w):
                    for q in w:
                        if q not in pts:
                            pts.add(q)
                            grew = True
        s = set()
        for q in pts:
            s |= hot.get(q, set())
        out.setdefault(field(b, 'Text'), set()).update(s)
    return out


def verify(path, other_sheets=None):
    R = split(read_stream(path))
    assert int(field(R[0][1], 'Weight')) == len(R) - 1, 'Weight'
    assert all(b.endswith(b'\x00') for h, b in R), 'NUL'
    uids = [field(b, 'UniqueID') for h, b in R if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueIDs'
    for i, (h, b) in enumerate(R):
        o = owner(b)
        if o is not None:
            assert 0 < o < len(R), (i, o)
        if field(b, 'RECORD') == '41' and field(b, 'Name') == 'PinUniqueId':
            assert field(R[o][1], 'UniqueID') == field(b, 'Text'), ('PinUniqueId', i)
    nets = nets_on_sheet(R)
    params = {}
    for h, b in R:
        if field(b, 'RECORD') == '41' and owner(b) is not None:
            params.setdefault(owner(b), {})[field(b, 'Name')] = field(b, 'Text')
    roots = {field(b, 'Text'): owner(b) for h, b in R if field(b, 'RECORD') == '34'}
    for p in parts():
        bit, ref = p['bit'], p['ref']
        u3pin = U3_LABELS[bit][0]
        assert nets.get('SDRAM-D%d' % bit) == {('U3', u3pin), (ref, '1')}, (bit, nets.get('SDRAM-D%d' % bit))
        assert nets.get('D%d' % bit) == {(ref, '2')}, (bit, nets.get('D%d' % bit))
        root = roots[ref]
        assert field(R[root][1], 'LibReference') == LIBREF
        assert '(sheet 2 only)' not in (field(R[root][1], 'ComponentDescription') or ''), ref
        assert (num(R[root][1], 'Location.X'), num(R[root][1], 'Location.Y')) == (p['cx'], p['y'])
        pr = params[root]
        assert pr.get('Comment') == COMMENT and pr.get('MANF#') == MPN and pr.get('NOTE') == NOTE, (ref, pr)
        assert pr.get('DeviceName') == 'R0201' and 'HiddenNetName' not in pr, ref
        model = [b for h, b in R if field(b, 'RECORD') == '45' and owner(b) is not None and owner(R[owner(b)][1]) == root]
        assert len(model) == 1 and field(model[0], 'ModelName') == 'R0201', ref
    ix = [num(b, 'IndexInSheet') for h, b in R if field(b, 'RECORD') == '1']
    assert len(ix) == len(set(ix)), 'duplicate component IndexInSheet'
    left = [t for t in nets if t and re.fullmatch(r'D\d+', t)]
    print('verify: %d records, %d UniqueIDs distinct, PinUniqueId invariant holds; on sheet 3 each SDRAM-Dn joins '
          'exactly U3 DQ pin + Rn pin 1, each Dn joins only Rn pin 2 (%d Dn labels left on the sheet)'
          % (len(R), len(uids), len(left)))
    return nets


if __name__ == '__main__':
    if sys.argv[1] == '--verify':
        verify(sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2])
