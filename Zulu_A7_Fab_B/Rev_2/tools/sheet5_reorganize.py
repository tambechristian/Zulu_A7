"""zulu_a7_5.SchDoc (title block "Sheet 6", FPGA Connections), 2026-11-18: reorganize U1's 138 ball rows into blocks.

Port of Zulu_A7_no_pmod/Rev_2/tools/sheet5_reorganize.py (third pass, 1166f8c) to Fab B, with the generalisations and
review fixes of the Asar Feather port (Asar_feather/Rev_1/tools/sheet6_reorganize.py, docs/sheet6_reorganize.md). All
three sheets come from the same EAGLE import with the same geometry. Fab B differs from the no-PMOD input only in the
eight balls that carry the Pmod JA nets (no net on no-PMOD), so it gets one more category, PMOD JA, and no spare user
I/O. Fab B Rev_1 and Rev_2 hold the same sheet, so the input is checked by the md5 of its FileHeader stream.

WHY.  U1 (XC7A35T, CPG236) is drawn as one-pin EAGLE parts, one row per ball: ball/bank text, net label, wire,
arrow pin with a name. The rows had drifted: blocks scattered, big rotated headings far from their rows, rows filed
by where they used to be rather than by their net (K18 = CHAN11 under FT2232H, P17 = LED0_R under CONFIG, P19 =
FT-PWREN# and R19 = JA7 under LED/BUTTON, W19/W18 = JA8/JA3 in the prototyping header, ...), pin names left from
earlier re-pins (N17 'BTN' carrying LED0_B, U18 'IO_A14' carrying JA1, ...), and two notes that described old
pin-outs.

WHAT (no connection changes; the script proves the sheet's nets are identical before and after).
- Every row is filed by its NET into one of eleven categories and laid out on one grid: two columns, a horizontal
  heading with a rule per category, sub-headings where a category has parts, pin ends aligned, ball/bank text
  right-aligned clear of the longest label. Rows (with the parts wired to them: R23 on PUDC_B, the XADC supply
  filter L6/L7/C123/C124) move rigidly; the configuration straps R20-R22 move as one group beside CONFIG.
  Column A: CONFIG, CLOCK, JTAG, FLASH / microSD, FT2232H, LED / BUTTON, ANALOG (XADC);
  column B: PROTOTYPING HEADER, PMOD JA (JA1-JA4, JA7-JA10), SDRAM, UNCONNECTED BALLS.
- Pin names (the visible GATE text): a user-I/O ball shows its port in vivado/zulu_a7_pins.xdc (the name the FPGA
  design uses); each XDC line's comment net must equal the sheet net, else that ball keeps its name and is reported;
  every XDC port must have a row. Dedicated pins keep their function name; G3/G2/H2/J2 show AMD's AD4P/AD4N/AD12P/
  AD12N; a spare user-I/O ball with no net would show IO_<ball> (Fab B has none: the eight no-PMOD spares carry
  Pmod JA here). The hidden GateName_<part> follows.
- Every ball text is checked against AMD's xc7a35t_cpg236.pkg; a missing one (P17) is added from it; C13 reads
  AMD's VCCADC_0.
- The two notes are rewritten from the rows themselves (the master-SPI note names what E19/EMCCLK and V19/DOUT_CSO_B
  carry on this board); the old rotated headings, sub-headings and the stale 'Pmod JA (bank 16 x5)' are replaced.

    python tools/sheet5_reorganize.py <sheet 6 in> <sheet 6 out>
"""
import hashlib
import os
import re
import shutil
import sys
from collections import defaultdict

sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402
from sheet3_u3_layout import fval, net_map, report, set_f, uid  # noqa: E402

SRC_STREAM_MD5 = 'e5cdcb91fb8627f5cbde01ed9580d7f2'   # FileHeader stream of Fab B Rev_1 = Rev_2 zulu_a7_5.SchDoc
PKG = 'C:/AMDDesignTools/2026.1/data/parts/xilinx/artix7/public/ibis/pkg/xc7a35t_cpg236.pkg'
XDC = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/vivado/zulu_a7_pins.xdc'   # the Zulu A7 pin file, Pmod JA included
XDC_PORTS = 101
H = {'A': 290, 'B': 780}                 # pin hot-end x of each column
TOP = 1270
PITCH = 10
TEXT_DX = -95                            # ball/bank text right end, from the pin end
HEAD_FONT, SUB_FONT = 2, 4               # Courier New 11 / 8 (same font table entries as the no-PMOD sheet)
GREY = 8421504
NOTE_CHARS, NOTE_LINES = 80, 4           # a 38-unit note frame 355 wide holds 4 lines of ~81 chars (Altium PDF metrics)

# Pin names (the visible GATE text), one rule (no-PMOD review 2026-11-14): a user-I/O ball shows its XDC port, the name
# the FPGA design uses; dedicated pins keep their function name; the XADC auxiliary inputs show AMD's channel names;
# balls with no net show IO_<ball>.
GATE_DEDICATED = {'C11': 'CCLK', 'G3': 'AD4P', 'G2': 'AD4N', 'H2': 'AD12P', 'J2': 'AD12N'}
BALL_TEXT_FIX = {'C13': 'VCCADC_0'}      # AMD's name; the old text dropped the _0
# The XADC input nets keep inherited names that do not match their channels (Asar review 2026-11-17): say it here
XADC_INPUTS = 'XADC inputs: net AIN15 = VAUX4 (G3/G2), AIN16 = VAUX12 (H2/J2)'
PMOD = ['JA1', 'JA2', 'JA3', 'JA4', 'JA7', 'JA8', 'JA9', 'JA10']


def num(b, k):
    v = field(b, k)
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def hot(b):
    L = num(b, 'PinLength') or 0
    r = (num(b, 'PinConglomerate') or 0) & 3
    dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][r]
    return fval(b, 'Location.X') + dx * L, fval(b, 'Location.Y') + dy * L


def onseg(p, a, c):
    (x, y), (x1, y1), (x2, y2) = p, a, c
    return abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < 1e-6 and \
        min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6 and min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6


def category(ball, net, gate):
    """(category, sub-heading, sort key) from the row's net."""
    n = net or ''
    if n in ('CFG-M0', 'CFG-M1', 'CFG-M2', 'PUDC_B', 'RST#', 'FPGA-INIT#', 'FPGA-DONE') or (n == 'VCC3V3' and ball == 'V11'):
        order = ['CFG-M0', 'CFG-M1', 'CFG-M2', 'VCC3V3', 'PUDC_B', 'RST#', 'FPGA-INIT#', 'FPGA-DONE']
        return 'CONFIG', None, order.index(n)
    if n == 'CLK-12M-FPGA':
        return 'CLOCK', None, 0
    if n.startswith('FPGA-T'):
        return 'JTAG', None, ['FPGA-TCK', 'FPGA-TMS', 'FPGA-TDI', 'FPGA-TDO'].index(n)
    if n == 'FPGA-CCLK' or n.startswith('FLASH-'):
        return 'FLASH / microSD', 'SPI flash U4 (master SPI x4 configuration)', \
            ['FPGA-CCLK', 'FLASH-CS#', 'FLASH-D00', 'FLASH-D01', 'FLASH-D02', 'FLASH-D03'].index(n)
    if n.startswith('SD-'):
        return 'FLASH / microSD', 'microSD X3 (native 4-bit SD bus)', \
            10 + ['SD-CLK', 'SD-CMD', 'SD-DAT0', 'SD-DAT1', 'SD-DAT2', 'SD-DAT3'].index(n)
    if n.startswith('UART_FT_') or n == 'FT-PWREN#':
        return 'FT2232H', None, ['UART_FT_RXD', 'UART_FT_TXD', 'UART_FT_RTS#', 'UART_FT_DTR#', 'UART_FT_CTS#',
                                 'FT-PWREN#'].index(n)
    if n in ('BTN', 'LED0_R', 'LED0_G', 'LED0_B', 'LED1', 'LED2'):
        return 'LED / BUTTON', None, ['BTN', 'LED0_R', 'LED0_G', 'LED0_B', 'LED1', 'LED2'].index(n)
    if n.startswith('AIN'):
        return 'ANALOG (XADC)', XADC_INPUTS, ['AIN15_P', 'AIN15_N', 'AIN16_P', 'AIN16_N'].index(n)
    if n in ('VCCADC', 'GNDADC') and ball in ('C13', 'C12'):
        return 'ANALOG (XADC)', 'XADC supply (ferrite + decoupling)', 10 + ['C13', 'C12'].index(ball)
    if n == 'GNDADC':
        return 'ANALOG (XADC)', 'XADC VP/VN unused, VREFP/VREFN = on-chip reference: all tied to GNDADC', 20 + ['A12', 'B13', 'B12', 'A13'].index(ball)
    if n == 'CHAN-CLK' or n.startswith('CHAN'):
        return 'PROTOTYPING HEADER', None, -1 if n == 'CHAN-CLK' else int(n[4:])
    if n in PMOD:
        return 'PMOD JA', None, PMOD.index(n)
    if n in ('A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12', 'BS0', 'BS1', 'CAS#', 'RAS#',
             'WE#', 'SDRAM-CS#', 'CKE', 'SDRAM-CLK', 'LDQM', 'UDQM') or re.fullmatch(r'D\d+', n):
        order = ['A%d' % i for i in range(13)] + ['BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'SDRAM-CS#', 'CKE', 'SDRAM-CLK',
                                                  'LDQM', 'UDQM'] + ['D%d' % i for i in range(16)]
        return 'SDRAM', None, order.index(n)
    if not n:
        if ball in ('D2', 'D1', 'B2', 'A2', 'B8', 'A8', 'B10', 'A10'):
            return 'UNCONNECTED BALLS', 'GTP TX / REFCLK: left floating (UG482 table 5-4)', \
                10 + ['D2', 'D1', 'B2', 'A2', 'B8', 'A8', 'B10', 'A10'].index(ball)
        return 'UNCONNECTED BALLS', 'Spare user I/O: no net', ball
    if n == 'GND' and ball in ('B4', 'A4', 'B6', 'A6'):
        return 'UNCONNECTED BALLS', 'GTP RX: tied to GND (UG482 table 5-4)', 20 + ['B4', 'A4', 'B6', 'A6'].index(ball)
    if n == 'GND' and ball in ('A11', 'B11'):
        return 'UNCONNECTED BALLS', 'Thermal diode DXP/DXN, unused: tied to GND', 30 + ['A11', 'B11'].index(ball)
    raise ValueError('no category for %s %s %s' % (ball, net, gate))


# PMOD JA sits under the other user-I/O header; column B has the room (column A already runs past the title block's
# top with its short ANALOG names), and without spare user I/O UNCONNECTED BALLS is shorter than on no-PMOD.
COLUMNS = {'A': ['CONFIG', 'CLOCK', 'JTAG', 'FLASH / microSD', 'FT2232H', 'LED / BUTTON', 'ANALOG (XADC)'],
           'B': ['PROTOTYPING HEADER', 'PMOD JA', 'SDRAM', 'UNCONNECTED BALLS']}
SUB_ORDER = {'FLASH / microSD': ['SPI flash U4 (master SPI x4 configuration)', 'microSD X3 (native 4-bit SD bus)'],
             'ANALOG (XADC)': [XADC_INPUTS, 'XADC supply (ferrite + decoupling)',
                               'XADC VP/VN unused, VREFP/VREFN = on-chip reference: all tied to GNDADC'],
             'UNCONNECTED BALLS': ['Spare user I/O: no net', 'GTP TX / REFCLK: left floating (UG482 table 5-4)',
                                   'GTP RX: tied to GND (UG482 table 5-4)', 'Thermal diode DXP/DXN, unused: tied to GND']}


def wrap(text, width):
    lines, cur = [], ''
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w) if cur else w
    return lines + [cur] if cur else lines


def pretouch(R):
    """Second no-PMOD review (2026-11-14), drawing quirks the old sheet already had, fixed in the original coordinates:
    - E18 PUDC_B: the R23 branch ran back along the pin through its name -> R23 sits under the label side and drops
      from a junction on the label wire;
    - C13 VCCADC: the C123/C124 branch ran along the pin through its name -> the caps drop 16 lower and take a tap
      from a junction on the label wire;
    - A12/B13/B12/A13 (GNDADC) and A11/B11 (GND): the tie wire lay over the pin and the label sat on the pin-name side
      -> a stub and label left of the pin end, like every other row;
    - GTP RX B4/B6/A6: GND ports (one drawing its bars through A4's label) -> GND net labels, as A4 already had.
    Returns (records to delete, new record bodies); nets are unchanged (checked by the caller)."""
    def find_wire(a, c):
        hits = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '27' and num(b, 'LocationCount') == 2 and
                {(num(b, 'X1'), num(b, 'Y1')), (num(b, 'X2'), num(b, 'Y2'))} == {a, c}]
        assert len(hits) == 1, (a, c, hits)
        return hits[0]

    def find_obj(rec, xy, text=None):
        hits = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == rec and owner(b) is None and
                (num(b, 'Location.X'), num(b, 'Location.Y')) == xy and (text is None or field(b, 'Text') == text)]
        assert len(hits) == 1, (rec, xy, text, hits)
        return hits[0]

    def shift(i, dx, dy):
        b = R[i][1]
        for kx, ky in (('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')):
            if fval(b, kx) is not None and fval(b, ky) is not None:
                b = set_f(set_f(b, kx, fval(b, kx) + dx), ky, fval(b, ky) + dy)
        n = num(b, 'LocationCount')
        if n:
            for j in range(1, n + 1):
                b = set_f(set_f(b, 'X%d' % j, fval(b, 'X%d' % j) + dx), 'Y%d' % j, fval(b, 'Y%d' % j) + dy)
        R[i][1] = b
    des = {owner(b): field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34'}
    kids = defaultdict(list)
    for i, (h, b) in enumerate(R):
        if owner(b) is not None:
            kids[owner(b)].append(i)

    def part(ref):
        root = [i for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '1' and des.get(i) == ref]
        assert len(root) == 1, ref
        out, todo = [], list(root)
        while todo:
            k = todo.pop()
            out.append(k)
            todo += kids.get(k, [])
        return out
    drop, new = set(), []

    def wire(a, c):
        new.append('|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID=%s|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d'
                   % (uid(), a[0], a[1], c[0], c[1]))

    def junction(xy):
        new.append('|RECORD=29|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=128|Locked=T|UniqueID=%s' % (xy[0], xy[1], uid()))

    def label(xy, text):
        new.append('|RECORD=25|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Justification=2|Color=128|FontID=4|Text=%s|'
                   'UniqueID=%s' % (xy[0], xy[1], text, uid()))
    # E18 / R23
    drop |= {find_wire((285, 1222), (315, 1222)), find_wire((315, 1212), (315, 1222)), find_obj('29', (285, 1222))}
    for i in part('R23') + [find_wire((315, 1182), (315, 1192)), find_obj('25', (315, 1185), 'VCC3V3')]:
        shift(i, -35, 0)
    wire((280, 1222), (280, 1212))
    junction((280, 1222))
    # C13 / C123, C124
    drop |= {find_wire((485, 267), (510, 267)), find_wire((510, 267), (535, 267)), find_obj('29', (485, 267)),
             find_obj('29', (510, 267))}
    for i in part('C123') + part('C124') + [find_wire((510, 227), (510, 237)), find_wire((535, 222), (535, 237)),
                                            find_obj('25', (510, 227), 'GNDADC'), find_obj('17', (535, 222), 'GNDADC')]:
        shift(i, 0, -16)
    wire((480, 267), (480, 251))
    wire((480, 251), (535, 251))
    junction((480, 267))
    junction((510, 251))
    # XADC / thermal tie rows: stub + label left of the pin end
    for y, net in ((597, 'GNDADC'), (587, 'GNDADC'), (577, 'GNDADC'), (567, 'GNDADC'), (547, 'GND'), (537, 'GND')):
        drop |= {find_wire((935, y), (960, y)), find_obj('25', (960, y), net)}
        wire((925, y), (935, y))
        label((925, y), net)
    # GTP RX: GND labels instead of ports
    for y in (442, 422, 412):
        drop.add(find_obj('17', (225, y), 'GND'))
        label((225, y), 'GND')
    return drop, new


def main(src, dst):
    raw = read_stream(src)
    if hashlib.md5(raw).hexdigest() != SRC_STREAM_MD5:
        raise SystemExit('%s is not the expected Fab B FPGA sheet (FileHeader stream md5 %s)' % (src, SRC_STREAM_MD5))
    R = split(raw)
    assert join(R) == raw and int(field(R[0][1], 'Weight')) == len(R) - 1
    before = net_map(R)
    pre_drop, pre_new = pretouch(R)
    for body in pre_new:
        R.append([bytes(4), body.encode('latin-1') + b'\x00'])
    R = delete(R, pre_drop)
    R[0][1] = set_field(R[0][1], 'Weight', str(len(R) - 1))
    report(before, net_map(R))                    # the pre-touch changes no net
    xdc, xdc_net, xdc_fn = {}, {}, {}
    for line in open(XDC):
        m = re.search(r'PACKAGE_PIN\s+(\w+).*get_ports \{?([^}\]]+)\}?\]\s*;#\s*(\S+)\s+bank\s+\d+\s+(\S+)', line)
        if m:
            assert m.group(1) not in xdc, line
            xdc[m.group(1)] = m.group(2).strip()
            xdc_net[m.group(1)] = m.group(3)
            xdc_fn[m.group(1)] = m.group(4)
    assert len(xdc) == XDC_PORTS, len(xdc)
    pkg = {}
    for line in open(PKG):
        m = re.match(r'^([A-W]\d+)\s+\|\s+\d+\s+(\S+)\s+\1\s*$', line)
        if m:
            pkg[m.group(1)] = m.group(2)
    xdc_bad = []                                  # (ball, why): that ball keeps its pin name
    for ball in sorted(xdc):
        if pkg.get(ball) != xdc_fn[ball]:
            xdc_bad.append((ball, 'XDC comment says %s, AMD .pkg says %s' % (xdc_fn[ball], pkg.get(ball))))

    des = {owner(b): field(b, 'Text') for h, b in R if field(b, 'RECORD') == '34'}
    cur = {i: num(b, 'CurrentPartId') for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '1'}
    kids = defaultdict(list)
    for i, (h, b) in enumerate(R):
        if owner(b) is not None:
            kids[owner(b)].append(i)

    def subtree(i):
        out, todo = [], [i]
        while todo:
            k = todo.pop()
            out.append(k)
            todo += kids.get(k, [])
        return out
    wires = {i: [(fval(b, 'X%d' % j), fval(b, 'Y%d' % j)) for j in range(1, num(b, 'LocationCount') + 1)]
             for i, (h, b) in enumerate(R) if field(b, 'RECORD') == '27'}
    free = {i: (field(b, 'RECORD'), (fval(b, 'Location.X'), fval(b, 'Location.Y')), field(b, 'Text'))
            for i, (h, b) in enumerate(R) if field(b, 'RECORD') in ('25', '17', '29', '22') and owner(b) is None}
    pinpts = defaultdict(set)
    comp_pins = defaultdict(list)
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') == '2':
            o = owner(b)
            if o in cur and num(b, 'OwnerPartId') == cur[o]:
                p = hot(b)
                pinpts[(round(p[0], 3), round(p[1], 3))].add(o)
                comp_pins[o].append(p)

    def network(p0):
        pts, ws, grew = {p0}, set(), True
        while grew:
            grew = False
            segs = [sg for k in ws for sg in zip(wires[k], wires[k][1:])]
            for i, w in wires.items():
                if i in ws:
                    continue
                if any(q in pts for q in w) or any(onseg(q, a, c) for q in list(pts) for a, c in zip(w, w[1:])) or \
                        any(onseg(q, a, c) for q in w for a, c in segs):      # a T: this wire ends mid-segment
                    ws.add(i)
                    pts |= set(w)
                    grew = True
        segs = [s for i in ws for s in zip(wires[i], wires[i][1:])]
        objs = {i for i, (r, p, t) in free.items() if p in pts or any(onseg(p, a, c) for a, c in segs)}
        comps = {c for q in pts for c in pinpts.get((round(q[0], 3), round(q[1], 3)), ())}
        comps |= {c for q, cs in pinpts.items() if any(onseg(q, a, d) for a, d in segs) for c in cs}   # pin on a wire's middle
        return ws, objs, comps

    # ---- clusters: U1 rows plus the parts wired to them ------------------------------------------------------
    rows = {}
    for i in cur:
        if des.get(i) != 'U1':
            continue
        pid = cur[i]
        vis = [k for k in kids[i] if num(R[k][1], 'OwnerPartId') == pid]
        pins = [k for k in vis if field(R[k][1], 'RECORD') == '2']
        if not pins:
            rows[i] = None                       # part 1: the hidden-pin carrier, no row
            continue
        gate = [k for k in vis if field(R[k][1], 'RECORD') == '41' and field(R[k][1], 'Name') == 'GATE']
        assert len(gate) == 1, (i, gate)
        rows[i] = dict(ball=field(R[pins[0]][1], 'Designator'), hot=hot(R[pins[0]][1]), gate=gate[0])
    assert sum(1 for r in rows.values() if r) == 138
    seen, clusters = set(), []
    for i, r in rows.items():
        if r is None or i in seen:
            continue
        comps, ws, objs, todo = {i}, set(), set(), [i]
        while todo:
            c = todo.pop()
            for p in comp_pins[c]:
                w2, o2, c2 = network(p)
                ws |= w2
                objs |= o2
                for k in c2 - comps:
                    comps.add(k)
                    todo.append(k)
        seen |= comps
        clusters.append(dict(comps=comps, wires=ws, objs=objs))
    for i in cur:                                 # R20-R22: label-connected straps, one group
        if i not in seen and des.get(i) in ('R20', 'R21', 'R22'):
            ws, objs = set(), set()
            for p in comp_pins[i]:
                w2, o2, c2 = network(p)
                assert c2 <= {i}, (des.get(i), c2)
                ws |= w2
                objs |= o2
            clusters.append(dict(comps={i}, wires=ws, objs=objs, strap=True))
            seen.add(i)
    left = [des.get(i) for i in cur if i not in seen and des.get(i) not in ('U1', 'FRAME2')]
    assert not left, left

    # ball texts by ball
    btext = {}
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') == '4' and owner(b) is None:
            m = re.match(r'^([A-W]\d{1,2})\s+(\S+)$', field(b, 'Text') or '')
            if m:
                btext.setdefault(m.group(1), []).append(i)

    # ---- file every row ---------------------------------------------------------------------------------------
    items = defaultdict(list)                    # category -> [(sub, key, cluster)]
    for cl in clusters:
        if cl.get('strap'):
            continue
        us = [c for c in cl['comps'] if rows.get(c)]
        names = {}
        for c in us:
            ws, objs, _ = network(rows[c]['hot'])
            nm = sorted({free[o][2] for o in objs if free[o][0] in ('25', '17')})
            assert len(nm) <= 1, (rows[c]['ball'], nm)
            names[c] = nm[0] if nm else None
        keyed = sorted((category(rows[c]['ball'], names[c], None), c) for c in us)
        (cat, sub, key), anchor = keyed[0]
        cl.update(cat=cat, sub=sub, key=key, rows=[c for k, c in keyed], names=names, anchor=anchor)
        items[cat].append(cl)
    straps = [cl for cl in clusters if cl.get('strap')]
    assert set(items) == {c for cs in COLUMNS.values() for c in cs}, sorted(items)

    # ---- layout -----------------------------------------------------------------------------------------------
    moves = {}                                   # cluster index -> (dx, dy)
    headings, subheads, rules = [], [], []

    def bbox_y(cl):
        ys = []
        for c in cl['comps']:
            ys += [p[1] for p in comp_pins[c]]
            for k in subtree(c):
                for kk in ('Location.Y', 'Corner.Y'):
                    v = fval(R[k][1], kk)
                    if v is not None and field(R[k][1], 'IsHidden') != 'T' and (num(R[k][1], 'OwnerPartId') in (None, -1, cur[c])):
                        ys.append(v)
        for w in cl['wires']:
            ys += [p[1] for p in wires[w]]
        for o in cl['objs']:
            r, (x, y), t = free[o]
            ys.append(y)
            if len(cl['comps']) == 1 and r != '17':   # a plain row's pitch covers its label, not a port symbol
                continue
            if r == '17':                         # power port: stem + bars (19) + text, in its direction
                ori = num(R[o][1], 'Orientation') or 0
                ys.append(y - 32 if ori == 3 else y + 32 if ori == 1 else y)
                if ori in (0, 2):
                    ys += [y - 6, y + 6]
            elif r == '25':                       # net label text: above its anchor, or along it when vertical
                ori = num(R[o][1], 'Orientation') or 0
                ys += [y - 14, y + 8] if ori in (1, 3) else [y + 8]   # R23's VCC3V3 drop reached RST# (2026-11-14)
        return min(ys), max(ys)

    notes, col_end = [], {}
    for col, cats in COLUMNS.items():
        x0, y = H[col], TOP
        for cat in cats:
            its = sorted(items[cat], key=lambda cl: (SUB_ORDER.get(cat, [None]).index(cl['sub']) if cl['sub'] else 0,
                                                     (0, cl['key'], '') if isinstance(cl['key'], int) else (1, 0, cl['key'])))
            rules.append(((x0 + TEXT_DX - 150, y), (x0 + (85 if col == 'A' else 110), y)))
            headings.append((x0 + TEXT_DX - 150, y - 12, cat))
            y -= 24
            last_sub = None
            for cl in its:
                if cl['sub'] != last_sub:
                    if last_sub is not None:
                        y -= 8
                    subheads.append((x0 + TEXT_DX - 150, y, cl['sub']))
                    y -= 12
                    last_sub = cl['sub']
                a = rows[cl['anchor']]['hot']
                lo, hi = bbox_y(cl)
                top_off = hi - a[1]                   # cluster parts above the anchor row
                ya = y - max(0, top_off - 2)
                moves[id(cl)] = (x0 - a[0], ya - a[1])
                y = ya - (a[1] - lo) - PITCH if len(cl['rows']) > 1 or len(cl['comps']) > 1 else ya - PITCH
                if len(cl['comps']) > 1 and len(cl['rows']) > 0:
                    y -= 6
                if cat == 'FLASH / microSD' and cl['key'] in (5, 15):
                    notes.append((cl['key'], x0, y))
                    y -= 42
            if cat == 'CONFIG':
                cfg_top = TOP - 18
            y -= 8
        col_end[col] = y
        print('column %s ends at y %.0f' % (col, y))
        # column A's lowest blocks (ANALOG) have short pin names and may pass the title block's top (y 170) as long as
        # nothing reaches x 378; column B lies over the title block, so it stops above it
        assert y > (100 if col == 'A' else 175), 'column %s overflows' % col

    # straps beside CONFIG: one rigid group, top at the CONFIG heading
    ys = [p[1] for cl in straps for c in cl['comps'] for p in comp_pins[c]] + \
         [p[1] for cl in straps for w in cl['wires'] for p in wires[w]] + [free[o][1][1] for cl in straps for o in cl['objs']]
    xs = [p[0] for cl in straps for c in cl['comps'] for p in comp_pins[c]] + \
         [p[0] for cl in straps for w in cl['wires'] for p in wires[w]] + [free[o][1][0] for cl in straps for o in cl['objs']]
    sdx, sdy = (H['A'] + 175) - min(xs), (cfg_top - 6) - max(ys)
    for cl in straps:
        moves[id(cl)] = (sdx, sdy)

    # ---- apply moves ----------------------------------------------------------------------------------------
    def mv(i, dx, dy):
        b = R[i][1]
        for kx, ky in (('Location.X', 'Location.Y'), ('Corner.X', 'Corner.Y')):
            if fval(b, kx) is not None and fval(b, ky) is not None:
                b = set_f(set_f(b, kx, fval(b, kx) + dx), ky, fval(b, ky) + dy)
        n = num(b, 'LocationCount')
        if n:
            for j in range(1, n + 1):
                b = set_f(set_f(b, 'X%d' % j, fval(b, 'X%d' % j) + dx), 'Y%d' % j, fval(b, 'Y%d' % j) + dy)
        R[i][1] = b
    done = set()
    renamed = []
    added_text, xdc_seen = [], set()
    for cl in clusters:
        dx, dy = moves[id(cl)]
        recs = set(cl['wires']) | set(cl['objs'])
        for c in cl['comps']:
            recs |= set(subtree(c))
        for i in recs:
            assert i not in done, i
            done.add(i)
            mv(i, dx, dy)
        for c in cl.get('rows', []):              # the row's ball text: right end at TEXT_DX from the pin end
            ball = rows[c]['ball']
            hx, hy = rows[c]['hot'][0] + dx, rows[c]['hot'][1] + dy
            ts = btext.get(ball, [])
            if ts:
                assert len(ts) == 1, (ball, ts)
                t = ts[0]
                txt = field(R[t][1], 'Text').split()[1]
                if ball in BALL_TEXT_FIX:
                    txt = BALL_TEXT_FIX[ball]
                    R[t][1] = set_field(R[t][1], 'Text', '%s  %s' % (ball, txt))
                assert pkg.get(ball) in (txt, txt[:-2] if txt.endswith('_0') else None) or ball in ('C12', 'C13'), (ball, txt, pkg.get(ball))
                b = set_f(set_f(R[t][1], 'Location.X', hx + TEXT_DX), 'Location.Y', hy + 1)
                b = set_field(b, 'Justification', '8')
                R[t][1] = b
                done.add(t)
            else:
                added_text.append(ball)
                body = ('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=0|Justification=8|Color=%d|FontID=7|'
                        'Text=%s  %s|UniqueID=%s' % (hx + TEXT_DX, GREY, ball, pkg[ball], uid())).encode()
                R.append([bytes(4), set_f(body, 'Location.Y', hy + 1) + b'\x00'])   # same _Frac as its neighbours
            g = rows[c]['gate']
            want = None
            if ball in xdc:
                xdc_seen.add(ball)
                if xdc_net[ball] != cl['names'][c]:
                    xdc_bad.append((ball, 'XDC comment net %s, sheet net %s' % (xdc_net[ball], cl['names'][c])))
                if ball not in {b for b, why in xdc_bad}:
                    want = xdc[ball]
            elif ball in GATE_DEDICATED:
                want = GATE_DEDICATED[ball]
            elif cl['names'][c] is None and cl['cat'] == 'UNCONNECTED BALLS' and cl['sub'].startswith('Spare'):
                want = 'IO_' + ball
            if want:
                renamed.append((ball, field(R[g][1], 'Text'), want)) if field(R[g][1], 'Text') != want else None
            if want and field(R[g][1], 'Text') != want:
                R[g][1] = set_field(R[g][1], 'Text', want)
            if want:                              # the hidden GateName_<part id> carries the same name
                pid = cur[c]
                for k in kids[c]:
                    if field(R[k][1], 'RECORD') == '41' and field(R[k][1], 'Name') == 'GateName_%d' % pid:
                        R[k][1] = set_field(R[k][1], 'Text', want)
    for ball in sorted(set(xdc) - xdc_seen):      # every XDC port must have its row on this sheet
        xdc_bad.append((ball, 'XDC port %s has no row on this sheet' % xdc[ball]))

    # ---- Asar review fixes (workflow wf_1d1c79ad-e33, 2026-11-17), same geometry here ---------------------------
    # pretouch() drops C123/C124 16 units, which put C123's designator on L7's baseline ('L7 C123' read as one) and
    # left the VCCADC port's tap junction 4 units from the cap-branch junction: L7's designator goes left of its coil,
    # above its vertical 'FB 600R' value; the port and its junction slide 5 units west along the same wire.
    def one(pred, what):
        hits = [i for i, (h, b) in enumerate(R) if pred(b)]
        assert len(hits) == 1, (what, hits)
        return hits[0]
    k = one(lambda b: field(b, 'RECORD') == '34' and field(b, 'Text') == 'L7', 'L7 designator')
    assert (round(fval(R[k][1], 'Location.X'), 3), round(fval(R[k][1], 'Location.Y'), 3)) == (278.504, 367.441), 'L7 text?'
    R[k][1] = set_f(set_f(R[k][1], 'Location.X', 252), 'Location.Y', 399.504)
    for rec, txt in (('17', 'VCCADC'), ('29', None)):
        k = one(lambda b: field(b, 'RECORD') == rec and owner(b) is None and (txt is None or field(b, 'Text') == txt) and
                (round(fval(b, 'Location.X'), 3), round(fval(b, 'Location.Y'), 3)) == (281, 403.504), 'VCCADC tap ' + rec)
        R[k][1] = set_f(R[k][1], 'Location.X', 276)

    # ---- old headings, sub-headings and notes go; new ones come -----------------------------------------------
    drop = set()
    old_heads = {'SDRAM', 'PROTOTYPING HEADER', 'JTAG', 'FLASH', 'CONFIG', 'FT2232H', 'ANALOG', 'CLCK', 'LED / BUTTON',
                 'UNCONNECTED BALLS', 'XADC analog (unused)', 'Thermal diode (unused)', 'Battery backup (unused)',
                 'GTP - float (UG482 T5-4)', 'FT2232H handshake', 'Pmod JA (bank 16 x5)'}
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') == '4' and owner(b) is None and (field(b, 'Text') or '') in old_heads:
            drop.add(i)
        if field(b, 'RECORD') == '28' and owner(b) is None and (field(b, 'Text') or '').startswith(('The six pins above', 'The six microSD')):
            drop.add(i)
    assert len(drop) == 18, len(drop)
    new = []
    for x, y, t in headings:
        new.append('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=%d|FontID=%d|Text=%s|UniqueID=%s'
                   % (x, y, GREY, HEAD_FONT, t, uid()))
    for (a, c) in rules:
        new.append('|RECORD=6|OwnerPartId=1|LineWidth=1|Color=%d|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d|UniqueID=%s'
                   % (GREY, a[0], a[1], c[0], c[1], uid()))
    for x, y, t in subheads:
        new.append('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=%d|FontID=%d|Text=%s|UniqueID=%s'
                   % (x, y, GREY, SUB_FONT, t, uid()))
    ball_of = {rows[c]['ball']: cl['names'][c] for cl in clusters for c in cl.get('rows', [])}
    sd = ', '.join('%s %s' % (n[3:], b) for b, n in sorted(ball_of.items(), key=lambda kv: kv[1] or '') if n and n.startswith('SD-'))
    # The master-SPI note, true for Fab B (UG470 table 2-2, Master SPI x4 column): the flash interface is CCLK, FCS_B,
    # D00-D03; the mode's one optional ball is EMCCLK (only with ExtMasterCclk_en); DOUT_CSO_B is '-' in x4 (not used,
    # high-Z during configuration). Here EMCCLK's ball E19 is a header pin and V19 is a Pmod pin, so the note says so.
    flash = {b: n for b, n in ball_of.items() if n == 'FPGA-CCLK' or (n or '').startswith('FLASH-')}
    funcs = ('CCLK', 'FCS_B', 'D00_MOSI', 'D01_DIN', 'D02', 'D03')
    assert len(flash) == 6 and sorted(f for b in flash for f in funcs if re.search(r'(^|_)%s(_|$)' % f, pkg[b])) == \
        sorted(funcs), {b: pkg[b] for b in flash}
    assert 'EMCCLK' in pkg['E19'] and 'DOUT_CSO_B' in pkg['V19'] and ball_of['E19'] and ball_of['V19']
    note_text = {5: 'The six balls above are the master-SPI x4 flash interface (UG470 table 2-2). FCS_B and D00-D03 '
                    'become ordinary user I/O once DONE goes high; CCLK is a dedicated pin (user access only through '
                    'STARTUPE2). The optional EMCCLK (E19) carries %s instead; DOUT_CSO_B (V19, here %s) is unused '
                    'in x4 mode.' % (ball_of['E19'], ball_of['V19']),
                 15: 'microSD runs the native 4-bit SD bus on its own pins (%s), so a card cannot fight the '
                     'configuration bus.' % sd}
    for key, t in note_text.items():
        assert len(wrap(t, NOTE_CHARS)) <= NOTE_LINES, (key, wrap(t, NOTE_CHARS))
    for key, x0, y in notes:
        new.append('|RECORD=28|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Corner.X=%d|Corner.Y=%d|AreaColor=16777215|'
                   'TextColor=%d|FontID=%d|Alignment=1|WordWrap=T|ClipToRect=T|Text=%s|UniqueID=%s'
                   % (x0 + TEXT_DX - 150, y - 40, x0 + 110, y - 2, GREY, SUB_FONT, note_text[key], uid()))
    for body in new:
        R.append([bytes(4), body.encode('latin-1') + b'\x00'])
    R = delete(R, drop)
    R[0][1] = set_field(R[0][1], 'Weight', str(len(R) - 1))

    blob = join(R)
    if os.path.abspath(dst) != os.path.abspath(src):
        shutil.copyfile(src, dst)
    write_stream(dst, blob)
    assert read_stream(dst) == blob
    print('%s: %d -> %d records; %d clusters moved, %d pin names changed' % (
        os.path.basename(dst), len(split(raw)), len(R), len(clusters), len(renamed)))
    for b, old, new in sorted(renamed):
        print('   %-4s %-16s -> %s' % (b, old, new))
    print('ball texts added from the AMD package file: %s' % (', '.join(added_text) or 'none'))
    print('XDC %s: %d ports; %d have a row whose net equals the comment net and a .pkg name equal to the comment%s' % (
        os.path.basename(XDC), len(xdc), len(xdc) - len({b for b, w in xdc_bad}),
        '' if not xdc_bad else '; NOT USED for the balls below'))
    for b, why in xdc_bad:
        print('   XDC NOT USED for %s: %s' % (b, why))
    print('notes:')
    for key, t in sorted(note_text.items()):
        print('   ' + '\n   '.join(wrap(t, NOTE_CHARS)))
    report(before, net_map(split(read_stream(dst))))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
