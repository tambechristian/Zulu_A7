"""Sheet 5 (zulu_a7_5.SchDoc, "FPGA Connections"), 2026-11-13: reorganize U1's 138 ball rows into labelled blocks.

WHY.  U1 (XC7A35T, CPG236) is drawn as one-pin EAGLE parts, one row per ball: ball/bank text, net label, wire,
arrow pin with a name. The rows had drifted: blocks scattered, big rotated headings far from their rows, rows filed
by where they used to be rather than by their net (K18 = CHAN11 under FT2232H, P17 = LED0_R under CONFIG, P19 =
FT-PWREN# and R19 under LED/BUTTON, ...), ten pin names left from earlier re-pins (N17 'BTN' carrying LED0_B, ...),
long labels running into the ball text, and two notes that described old pin-outs.

WHAT (no connection changes; the script proves the sheet's nets are identical before and after).
- Every row is filed by its NET into one of the user's ten categories and laid out on one grid: two columns, a
  horizontal heading with a rule per category, sub-headings where a category has parts, pin ends aligned, ball/bank
  text right-aligned clear of the longest label. Rows (with the parts wired to them: R23 on PUDC_B, the XADC supply
  filter L6/L7/C123/C124) move rigidly; the configuration straps R20-R22 move as one group beside CONFIG.
- Stale pin names (the visible GATE text) are set to the ball's present function; rows with no net become IO_<ball>.
- P17 gets its missing ball text (IO_L13N_T2_MRCC_14, from AMD's xc7a35t_cpg236.pkg); every ball text is checked
  against that file.
- The two notes are rewritten from the rows themselves; the old rotated headings and sub-headings are replaced.

    python tools/sheet5_reorganize.py <sheet 5 in> <sheet 5 out>
"""
import hashlib
import math
import os
import re
import shutil
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools')
from schdoc import delete, field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402
from sheet3_u3_layout import fval, net_map, report, set_f, uid  # noqa: E402

SRC_MD5 = '3f76a73674bbc2d9bb32bacb66a78de8'
PKG = 'C:/AMDDesignTools/2026.1/data/parts/xilinx/artix7/public/ibis/pkg/xc7a35t_cpg236.pkg'
H = {'A': 290, 'B': 780}                 # pin hot-end x of each column
TOP = 1270
PITCH = 10
TEXT_DX = -95                            # ball/bank text right end, from the pin end
HEAD_FONT, SUB_FONT = 2, 4               # Courier New 11 / 8
GREY = 8421504

GATE_FIX = {'K17': 'UART_RXD', 'K18': 'CHAN11', 'H19': 'CHAN13', 'G17': 'CHAN7', 'E19': 'CHAN12', 'T17': 'CHAN28',
            'N19': 'BTN', 'N17': 'LED0_B', 'P17': 'LED0_R', 'P19': 'FT_PWREN#'}


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
        return 'ANALOG (XADC)', 'XADC inputs', ['AIN15_P', 'AIN15_N', 'AIN16_P', 'AIN16_N'].index(n)
    if n in ('VCCADC', 'GNDADC') and ball in ('C13', 'C12'):
        return 'ANALOG (XADC)', 'XADC supply (ferrite + decoupling)', 10 + ['C13', 'C12'].index(ball)
    if n == 'GNDADC':
        return 'ANALOG (XADC)', 'XADC dedicated pins, unused: tied to GNDADC', 20 + ['A12', 'B13', 'B12', 'A13'].index(ball)
    if n == 'CHAN-CLK' or n.startswith('CHAN'):
        return 'PROTOTYPING HEADER', None, -1 if n == 'CHAN-CLK' else int(n[4:])
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


COLUMNS = {'A': ['CONFIG', 'CLOCK', 'JTAG', 'FLASH / microSD', 'FT2232H', 'LED / BUTTON', 'ANALOG (XADC)'],
           'B': ['PROTOTYPING HEADER', 'SDRAM', 'UNCONNECTED BALLS']}
SUB_ORDER = {'FLASH / microSD': ['SPI flash U4 (master SPI x4 configuration)', 'microSD X3 (native 4-bit SD bus)'],
             'ANALOG (XADC)': ['XADC inputs', 'XADC supply (ferrite + decoupling)', 'XADC dedicated pins, unused: tied to GNDADC'],
             'UNCONNECTED BALLS': ['Spare user I/O: no net', 'GTP TX / REFCLK: left floating (UG482 table 5-4)',
                                   'GTP RX: tied to GND (UG482 table 5-4)', 'Thermal diode DXP/DXN, unused: tied to GND']}


def main(src, dst):
    if hashlib.md5(open(src, 'rb').read()).hexdigest() != SRC_MD5:
        raise SystemExit('%s is not the expected sheet 5 (md5 %s)' % (src, SRC_MD5))
    raw = read_stream(src)
    R = split(raw)
    assert join(R) == raw and int(field(R[0][1], 'Weight')) == len(R) - 1
    before = net_map(R)
    pkg = {}
    for line in open(PKG):
        m = re.match(r'^([A-W]\d+)\s+\|\s+\d+\s+(\S+)\s+\1\s*$', line)
        if m:
            pkg[m.group(1)] = m.group(2)

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
            for i, w in wires.items():
                if i in ws:
                    continue
                if any(q in pts for q in w) or any(onseg(q, a, c) for q in list(pts) for a, c in zip(w, w[1:])):
                    ws.add(i)
                    pts |= set(w)
                    grew = True
        segs = [s for i in ws for s in zip(wires[i], wires[i][1:])]
        objs = {i for i, (r, p, t) in free.items() if p in pts or any(onseg(p, a, c) for a, c in segs)}
        comps = {c for q in pts for c in pinpts.get((round(q[0], 3), round(q[1], 3)), ())}
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
            ys.append(free[o][1][1])
        return min(ys), max(ys)

    notes = []
    for col, cats in COLUMNS.items():
        x0, y = H[col], TOP
        for cat in cats:
            its = sorted(items[cat], key=lambda cl: (SUB_ORDER.get(cat, [None]).index(cl['sub']) if cl['sub'] else 0,
                                                     (0, cl['key'], '') if isinstance(cl['key'], int) else (1, 0, cl['key'])))
            headings.append((x0 + TEXT_DX - 150, y, cat))
            rules.append(((x0 + TEXT_DX - 150, y - 4), (x0 + 110, y - 4)))
            y -= 18
            last_sub = None
            for cl in its:
                if cl['sub'] != last_sub:
                    if last_sub is not None:
                        y -= 4
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
                    y -= 46
            if cat == 'CONFIG':
                cfg_top = TOP - 18
            y -= 14
        print('column %s ends at y %.0f' % (col, y))
        assert y > (175 if col == 'A' else 175), 'column %s overflows' % col

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
                assert pkg.get(ball) in (txt, txt[:-2] if txt.endswith('_0') else None) or ball in ('C12', 'C13'), (ball, txt, pkg.get(ball))
                b = set_f(set_f(R[t][1], 'Location.X', hx + TEXT_DX), 'Location.Y', hy + 1)
                b = set_field(b, 'Justification', '8')
                R[t][1] = b
                done.add(t)
            else:
                assert ball == 'P17', ball
                R.append([bytes(4), ('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Justification=8|Color=%d|FontID=7|'
                                     'Text=%s  %s|UniqueID=%s' % (hx + TEXT_DX, hy + 1, GREY, ball, pkg[ball], uid())).encode() + b'\x00'])
            g = rows[c]['gate']
            want = GATE_FIX.get(ball) or (('IO_' + ball) if cl['names'][c] is None and cl['cat'] == 'UNCONNECTED BALLS'
                                          and cl['sub'].startswith('Spare') else None)
            if want and field(R[g][1], 'Text') != want:
                R[g][1] = set_field(R[g][1], 'Text', want)

    # ---- old headings, sub-headings and notes go; new ones come -----------------------------------------------
    drop = set()
    old_heads = {'SDRAM', 'PROTOTYPING HEADER', 'JTAG', 'FLASH', 'CONFIG', 'FT2232H', 'ANALOG', 'CLCK', 'LED / BUTTON',
                 'UNCONNECTED BALLS', 'XADC analog (unused)', 'Thermal diode (unused)', 'Battery backup (unused)',
                 'GTP - float (UG482 T5-4)', 'FT2232H handshake'}
    for i, (h, b) in enumerate(R):
        if field(b, 'RECORD') == '4' and owner(b) is None and (field(b, 'Text') or '') in old_heads:
            drop.add(i)
        if field(b, 'RECORD') == '28' and owner(b) is None and (field(b, 'Text') or '').startswith(('The six pins above', 'The six microSD')):
            drop.add(i)
    assert len(drop) == 17, len(drop)
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
    note_text = {5: 'The six balls above (CCLK, FCS_B, D00-D03) are the only ones master-SPI configuration can use '
                    '(UG470); they are ordinary user I/O once DONE goes high.',
                 15: 'microSD runs the native 4-bit SD bus on its own pins (%s), so a card cannot fight the '
                     'configuration bus.' % sd}
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
    print('%s: %d -> %d records; %d clusters moved, %d gate names fixed' % (
        os.path.basename(dst), len(split(raw)), len(R), len(clusters), len(GATE_FIX)))
    report(before, net_map(split(read_stream(dst))))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
