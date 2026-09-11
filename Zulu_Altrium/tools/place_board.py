# -*- coding: utf-8 -*-
"""Compute a placement for every component on zulu_a7.PcbDoc and prove it is legal.

SOURCES, all primary
    docs/placement.html          the block plan -- front/back split and the four re-pin moves
    Imported .../zulu_a7.PcbLib  the real land patterns; every extent below is measured, not drawn
    .../zulu_a7.NET              which parts exist and what they connect to
    zulu_a7.PcbDoc               SOURCEHIERARCHICALPATH, i.e. which schematic sheet each part is on
    Claude_Fable/zulu_a7.c0.brd  the previous routed layout on the SAME 69.85 x 25.40 outline,
                                 read in pad space by old_placement.py

WHAT THE OLD BOARD IS AND IS NOT USED FOR
It is NOT the authority on where a part goes. It is a different revision: the flash sat on the
BACK at (25.55, 9.60), the EEPROM at the far left of the back, the XADC dividers 45 mm from
their balls, and the SDRAM directly BEHIND the FPGA -- which only works with the 1+6+1 HDI stack
the fab rejected in writing. docs/placement.html moves all four, and the plan wins every time.

What the old board IS used for: the orientations a routed layout proved (the USB opening at +y,
the microSD opening facing the left edge, J1 at 90 degrees, the LED column pitch), and the two
anchor positions the plan and the old board independently agree on to the micron -- X2 at
(30.480, 12.700) and X1 at (33.020, 22.721). Every anchor below carries the source it came from.

WHY THE PLAN IS NOT SIMPLY OBEYED EITHER
The plan's rectangles are BODY outlines. Several land patterns are larger and three collide:

    X4  JST B2B-PH-SM4-TB   land is 6.50 mm deep, the plan drew 3.30, and the connector cannot
                            move sideways -- it has to sit in the 11.18 mm window where X2's pins
                            are omitted. So U2 moves UP instead, from y 11.80 to 13.60.
    U2  FT2232HL-LQFP64     land is 12.95 mm, not the 10 mm body the plan drew; Q1 and U4 shift
                            right to clear it.
    JP4 1X03 at y 0.70      a 1.524 mm pad would hang 0.06 mm over the board edge. JP3/JP4 keep
                            the old board's y (21.68 / 3.72) and take the plan's x.

Run:  python tools/place_board.py            report only
      python tools/place_board.py --emit     also write tools/ZuluPlacement.pas
"""
import collections
import math
import os
import re
import sys

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_pcblib import pads as lib_pads
from board_preflight import read_netlist, NET, LIB, PCB
from old_placement import load as load_old

BOARD = (69.85, 25.40)
EDGE = 0.30          # minimum copper to board edge
CLEAR = 0.30         # minimum land to land between different components

# ---------------------------------------------------------------- anchors
# (designator, layer, rotation, centre of the PAD BOUNDING BOX in board mm, source)
PLAN, OLDB, BOTH, FIX = 'plan', 'old board', 'plan+old agree', 'geometry'
ANCHORS = [
    # ---- front
    ('X2',  'top',    0, 30.480, 12.700, BOTH),
    ('X1',  'top',    0, 33.020, 22.721, BOTH),    # shield tabs 0.49 mm off the top edge
    ('X3',  'top',   90,  8.800, 12.500, PLAN),    # opening faces -x: the card enters over the edge
    ('X4',  'top',    0, 32.400,  3.550, PLAN),    # centred in X2's 11.18 mm pin-free window
    ('U2',  'top',    0, 32.950, 13.600, FIX),     # plan y 11.80 + 1.80 to clear X4's real land
    ('U1',  'top',    0, 46.400, 11.900, PLAN),    # rotation 0, measured best of four (change 5)
    ('Q1',  'top',    0, 41.300, 19.750, FIX),     # plan 39.75, right to clear U2's LQFP land
    ('U4',  'top',    0, 47.500, 19.400, FIX),     # flash to the FRONT (change 1); plan x 45.0
    ('BTN', 'top',   90, 20.300, 12.920, OLDB),
    ('LD0', 'top',    0, 24.600, 10.885, OLDB),    # the old LED column, x re-centred 0.25 left
    ('LD1', 'top',    0, 24.600, 12.585, OLDB),
    ('LD2', 'top',    0, 24.600, 13.785, OLDB),
    ('LD5', 'top',    0, 24.600, 14.985, OLDB),
    ('LD3', 'top',    0, 24.600, 16.185, FIX),     # new part: bq24232 CHG, same column and pitch
    ('LD4', 'top',    0, 24.600, 17.385, FIX),     # new part: bq24232 DONE
    ('J1',  'top',   90, 66.400, 12.700, PLAN),    # plan x, board-centred y
    ('JP3', 'top',    0, 64.300, 21.680, FIX),     # plan x, old y: the plan's y is off the edge
    ('JP4', 'top',    0, 64.300,  3.720, FIX),
    ('R4',  'top',   90, 59.300, 18.178, FIX),     # old x 59.79 clipped JP3 pad 1 by 0.09
    # ---- back
    ('U3',  'bottom', 90, 28.350, 11.850, PLAN),   # BESIDE the FPGA: through-vias, not HDI
    ('U10', 'bottom',  0, 24.750, 20.600, FIX),    # EEPROM behind the bridge (change 3);
                                                   # plan y 20.15 overlapped the SDRAM by 0.14
    ('R1',  'bottom',  0, 58.200,  3.700, FIX),    # 742C043; old y 3.00 sat on X2 pin 5
    ('R34', 'bottom',  0, 11.820, 19.290, OLDB),   # 742C083 SD pull-ups, above the power block
    # ---- off the board entirely
    # The four Creative Commons marks are NOT PART OF THE BOARD. They are licence art -- 3.56 mm
    # circles for BY and SA, 6.12 mm for CC and the copyright ring -- that EAGLE carried as real
    # pinless components so they would print with the drawing. The previous layout parked all four
    # BELOW the outline on a shared baseline at y = -9.502, and that is where they go: on the
    # board there is nowhere to put 21 mm of silkscreen circles without covering something, and
    # the user confirmed on 2026-09-11 that they are not meant to be on the PCB at all.
    # Positions are the previous layout's own, read out of zulu_a7.c0.brd. Each package is drawn
    # centred on its origin, so the element position IS the centre of the mark. They carry no
    # copper, so nothing here can fail a clearance rule.
    ('U$2', 'top',    0,  5.059, -6.441, OLDB),    # CC_CC,        6.12 mm
    ('U$3', 'top',    0, 10.895, -7.722, OLDB),    # CC_BY,        3.56 mm
    ('U$4', 'top',    0, 15.451, -7.722, OLDB),    # CC_SA,        3.56 mm
    ('U$5', 'top',    0, 21.288, -6.441, OLDB),    # CC_COPYRIGHT, 6.12 mm
]

# ---------------------------------------------------------------- regions
# name: (layer, x0, y0, x1, y1, note)
REGIONS = collections.OrderedDict([
    # name      layer      x0     y0     x1     y1   rot  note
    ('PWR',   ('bottom',  1.20,  4.00, 15.30, 18.20,  0, 'bucks, charger, inductors (plan 1.0-15.5/4.0-21.0)')),
    ('NW',    ('bottom',  1.20, 20.94, 16.60, 22.90,  0, 'above R34, beside the microSD')),
    ('SDL',   ('bottom', 17.40, 18.60, 20.95, 22.90,  0, 'left of the EEPROM')),
    ('SDR',   ('bottom', 28.55, 18.60, 39.40, 22.90,  0, 'right of the EEPROM, above the SDRAM')),
    ('UNDER', ('bottom', 17.40,  2.60, 39.40,  5.20,  0, 'below the SDRAM, behind the bridge')),
    ('XADC',  ('bottom', 40.00,  2.60, 47.00,  5.20,  0, 'XADC dividers beside the FPGA (change 2)')),
    ('CFG',   ('bottom', 47.60,  2.60, 57.20,  5.20,  0, 'config straps and the XADC supply filter')),
    ('DEC',   ('bottom', 42.00,  7.50, 54.00, 18.00,  0, 'FPGA decoupling, under the ball field')),
    ('BULKN', ('bottom', 39.80, 20.60, 59.20, 23.00,  0, '0603 bulk, north of the field')),
    ('EAST',  ('bottom', 58.60,  5.50, 63.60, 20.00,  0, 'series and pull-up resistors, left of the Pmod')),
    ('TE',    ('top',    52.25,  5.20, 57.60, 21.20, 90, '0805 bulk on the FRONT, east of the FPGA')),
])

ASSIGN = {}


def assign(region, names):
    for n in names.split():
        ASSIGN[n] = region


# sheet 1 -- power
assign('PWR',   'U5 U6 U7 U8 L1 L2 L3 Q2 C78 C80 C82 C84 C147 C148 C149 C150 C151 '
                'R77 R78 R102 R103 R104 R105 R106 R107 R108')
# sheet 3 -- microSD, SDRAM, flash.  C3-C9 sit directly behind the SDRAM they decouple.
assign('NW',    'R35 C11 C12 C13')
assign('UNDER', 'C3 C4 C5 C6 C7 C8 C9')
assign('BULKN', 'R2 R6 R7')
# sheet 4 -- FT2232, EEPROM, JTAG.  The SDRAM occupies the whole back behind the bridge, so the
# bridge decoupling goes to the strips immediately above and below it.
assign('UNDER', 'C38 C40 C41 C133 C134 C135 C136 C137 C138 C139 C152 C153 C154 L4 L5 R18')
assign('SDL',   'R19 R96 R97 R98 R101')
assign('EAST',  'R5 R24 R25 R90 R91 R92 R93 R94 R99')
# sheet 5 -- config straps and XADC supply
assign('CFG',   'R20 R21 R22 R23 C123 C124 L6 L7')
# sheet 2 -- header, Pmod, XADC dividers, indicators
assign('XADC',  'R10 R11 R12 R13 R14 R15 R16 R17 C36 C37')
assign('EAST',  'R26 R27 R28 R29 R30 R31 R32 R33')
assign('SDR',   'R80 R81 R82 R83 R84 R85 R86')
# sheet 6 -- decoupling: 0201s under the ball field, 0603 bulk north of it, 0805 bulk on the front
assign('DEC',   'C89 C90 C91 C92 C95 C96 C107 C108 C109 C110 C111 C112 C113 C114 C115 C116 '
                'C117 C118 C119 C120 C121 C122')
assign('BULKN', 'C87 C88 C94 C99 C100 C101 C102 C103 C104 C105 C106')
assign('TE',    'C85 C86 C93 C97 C98 C140 C141 C142 C143 C144 C145 C146')

GRIDDED = {'DEC', 'EAST'}    # spread out, not shelf-packed

THRU = {'ZULU-DIP37', '2X06', '1X03-NOSILK'}     # pads present on every layer


def lib_geometry(path=LIB):
    """footprint -> ((w, h), [(dx, dy, pw, ph), ...]) -- extent, and every pad relative to centre.

    The per-pad list is what makes a collision test mean anything for the pin fields: X2's bounding
    box is 59.9 x 24.4 mm and covers almost the whole board, so box-against-box says every part on
    the board hits the header. Its FORTY PADS occupy 92 mm2 of that 1462, and it is the pads that
    have to be cleared.
    """
    f = olefile.OleFileIO(path)
    skip = {'FileHeader', 'Library', 'Textures', 'Models', 'ComponentParamsTOC',
            'LayerKindMapping', 'FileVersionInfo'}
    out = {}
    for name in sorted({e[0] for e in f.listdir() if len(e) > 1} - skip):
        p = lib_pads(f, name)
        if not p:
            out[name] = ((0.0, 0.0), [])
            continue
        x0 = min(q[1] - q[3] / 2 for q in p); x1 = max(q[1] + q[3] / 2 for q in p)
        y0 = min(q[2] - q[4] / 2 for q in p); y1 = max(q[2] + q[4] / 2 for q in p)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        out[name] = ((x1 - x0, y1 - y0), [(q[1] - cx, q[2] - cy, q[3], q[4]) for q in p])
    f.close()
    return out


def lib_extents(path=LIB):
    """footprint -> (w, h) of the pad bounding box in mm, at rotation 0."""
    return {k: v[0] for k, v in lib_geometry(path).items()}


def sheets(path=PCB):
    f = olefile.OleFileIO(path)
    d = f.openstream(['Components6', 'Data']).read().decode('latin-1')
    f.close()
    out = {}
    for b in re.split(r'(?=\|SELECTION=)', d):
        if 'PATTERN=' not in b:
            continue
        g = dict(re.findall(r'\|([A-Z0-9_]+)=([^|\x00]*)', b))
        out[g['SOURCEDESIGNATOR']] = g.get('SOURCEHIERARCHICALPATH', '?')
    return out


def size(fp, rot, ext):
    w, h = ext[fp]
    return (h, w) if rot % 180 == 90 else (w, h)


def pack(rect, items, ext, rrot=0):
    """Shelf-pack items into rect. items = [(designator, footprint)]. -> placed, overflow."""
    x0, y0, x1, y1 = rect
    order = sorted(items, key=lambda it: (-size(it[1], rrot, ext)[1],
                                          -size(it[1], rrot, ext)[0], it[0]))
    placed, over = [], []
    cx, cy, shelf = x0, y0, 0.0
    for d, fp in order:
        w, h = size(fp, rrot, ext)
        if w <= 0 or h <= 0:                       # the four pinless CC logos
            placed.append((d, 0, x0 + (x1 - x0) / 2, y0 + (y1 - y0) / 2))
            continue
        if cx + w > x1 + 1e-9:
            cx = x0
            cy += shelf + CLEAR
            shelf = 0.0
        if cy + h > y1 + 1e-9:
            over.append((d, fp))
            continue
        placed.append((d, rrot, cx + w / 2, cy + h / 2))
        cx += w + CLEAR
        shelf = max(shelf, h)
    return placed, over


def grid(rect, items, ext, rrot=0):
    """Spread items evenly over rect on a near-square grid.

    Shelf packing is right where space is scarce, but wrong for decoupling: it would stack all
    twenty-two 0201s in one 12 x 0.9 mm strip in a corner of a 12 x 10.5 mm region, which is the
    opposite of what a decoupling cap is for. The via dog-bones are not drawn yet, so an even
    lattice across the ball field is the honest first pass -- it puts each cap near a different
    part of the array and leaves the fan-out room to be cut in between.
    """
    x0, y0, x1, y1 = rect
    real = [(d, fp) for d, fp in sorted(items) if ext[fp][0] > 0]
    placed = [(d, rrot, (x0 + x1) / 2, (y0 + y1) / 2)
              for d, fp in sorted(items) if ext[fp][0] <= 0]
    if not real:
        return placed, []
    maxw = max(size(fp, rrot, ext)[0] for _, fp in real)
    maxh = max(size(fp, rrot, ext)[1] for _, fp in real)
    n = len(real)
    cols = max(1, int(math.ceil(math.sqrt(n * (x1 - x0) / max(y1 - y0, 1e-9)))))
    cols = max(1, min(cols, int((x1 - x0 + CLEAR) / (maxw + CLEAR))))
    rows = max(1, min(int(math.ceil(n / float(cols))),
                      int((y1 - y0 + CLEAR) / (maxh + CLEAR))))
    over = real[cols * rows:]
    for i, (d, fp) in enumerate(real[:cols * rows]):
        w, h = size(fp, rrot, ext)
        c, r = i % cols, i // cols
        px = x0 + w / 2 + (x1 - x0 - w) * (c / float(cols - 1) if cols > 1 else 0.5)
        py = y0 + h / 2 + (y1 - y0 - h) * (r / float(rows - 1) if rows > 1 else 0.5)
        placed.append((d, rrot, px, py))
    return placed, over


def rail_centroids(u1_centre):
    """Where each supply rail's balls actually are, in board mm.

    The 0201s under the ball field are not interchangeable. VCC1V0 is the core supply and its
    eight balls sit in a 0.5 x 3.0 mm cluster at the centre of the die; VCC1V8 is three balls
    just north-east of it; the 28 VCC3V3 balls are spread over the whole 9 x 9 mm array. Placing
    the caps alphabetically would put every core cap in one row along the top edge of the region,
    3 mm from the balls that need them. This reads the ball positions out of the PcbLib and the
    netlist and hands each rail a target.
    """
    comp, nets = read_netlist(NET)
    ball = {}
    for n, refs in nets.items():
        for r in refs:
            if r.startswith('U1-'):
                ball[r[3:]] = n
    f = olefile.OleFileIO(LIB)
    pos = {q[0]: (q[1], q[2]) for q in lib_pads(f, 'XC7A35T-CPG236')}
    f.close()
    xs = [v[0] for v in pos.values()]; ys = [v[1] for v in pos.values()]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    out = {}
    for b, n in ball.items():
        if b in pos and n.startswith('VCC'):
            out.setdefault(n, []).append((pos[b][0] - cx + u1_centre[0],
                                          pos[b][1] - cy + u1_centre[1]))
    return {n: (sum(q[0] for q in v) / len(v), sum(q[1] for q in v) / len(v), len(v),
                max(max(q[0] for q in v) - min(q[0] for q in v),
                    max(q[1] for q in v) - min(q[1] for q in v)))
            for n, v in out.items()}


def rail_grid(rect, items, ext, rrot=0, rails=None, capnet=None):
    """The DEC lattice, but each cap goes to the free point nearest its own rail's balls."""
    placed, over = grid(rect, items, ext, rrot)
    if not rails or not capnet:
        return placed, over
    pts = [(d, r, x, y) for d, r, x, y in placed]
    slots = [(x, y) for _, _, x, y in pts]
    names = [d for d, _, _, _ in pts]
    # tightest rail first: it has the least freedom and the most to lose
    order = sorted(names, key=lambda d: (rails.get(capnet.get(d), (0, 0, 0, 99))[3], d))
    free = list(range(len(slots)))
    out = []
    for d in order:
        t = rails.get(capnet.get(d))
        if t is None:
            i = free[0]
        else:
            i = min(free, key=lambda j: (slots[j][0] - t[0]) ** 2 + (slots[j][1] - t[1]) ** 2)
        free.remove(i)
        out.append((d, rrot, slots[i][0], slots[i][1]))
    return out, over


def build(verbose=True):
    comp, nets = read_netlist(NET)
    ext = lib_extents()
    u1 = [a for a in ANCHORS if a[0] == 'U1'][0]
    rails = rail_centroids((u1[3], u1[4]))
    capnet = {}
    for n, refs in nets.items():
        if not n.startswith('VCC'):
            continue
        for r in refs:
            capnet[r.split('-')[0]] = n
    out, src = {}, {}
    for d, layer, rot, cx, cy, s in ANCHORS:
        out[d] = (layer, rot, cx, cy)
        src[d] = s

    rest = [d for d in sorted(comp) if d not in out]
    missing = [d for d in rest if d not in ASSIGN]
    byreg = collections.defaultdict(list)
    for d in rest:
        if d in ASSIGN:
            byreg[ASSIGN[d]].append((d, comp[d]))

    overflow = []
    if verbose:
        print('REGIONS')
    for name, (layer, x0, y0, x1, y1, rrot, note) in REGIONS.items():
        items = byreg.get(name, [])
        if name == 'DEC':
            placed, over = rail_grid((x0, y0, x1, y1), items, ext, rrot, rails, capnet)
        elif name in GRIDDED:
            placed, over = grid((x0, y0, x1, y1), items, ext, rrot)
        else:
            placed, over = pack((x0, y0, x1, y1), items, ext, rrot)
        area = sum(ext[fp][0] * ext[fp][1] for _, fp in items)
        box = (x1 - x0) * (y1 - y0)
        for d, rot, px, py in placed:
            out[d] = (layer, rot, px, py)
            src[d] = 'region ' + name
        overflow += [(name, d, fp) for d, fp in over]
        if verbose:
            print('  %-6s %-6s %5.1f x %5.1f  %3d parts  %5.1f of %5.1f mm2 land (%2.0f%%)%s'
                  % (name, layer, x1 - x0, y1 - y0, len(items), area, box, 100 * area / max(box, 1e-9),
                     '   OVERFLOW %d' % len(over) if over else ''))
    if missing and verbose:
        print('\nUNASSIGNED (%d): %s' % (len(missing), ' '.join(missing)))
    if overflow and verbose:
        print('\nOVERFLOW (%d):' % len(overflow))
        for r, d, fp in overflow:
            print('   %-6s %-6s %s' % (r, d, fp))
    return comp, ext, out, src, missing, overflow


def boxes(comp, ext, place):
    out = {}
    for d, (layer, rot, cx, cy) in place.items():
        w, h = size(comp[d], rot, ext)
        out[d] = (layer, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return out


def rects(comp, geom, place):
    """designator -> (layer, [(x0, y0, x1, y1), ...]) in board mm.

    One rectangle per part, except the pin fields, which get one per pad.
    """
    out = {}
    for d, (layer, rot, cx, cy) in place.items():
        fp = comp[d]
        (w, h), pl = geom[fp]
        if w <= 0:
            out[d] = (layer, [])
            continue
        if fp in THRU:
            rs = []
            for dx, dy, pw, ph in pl:
                if rot % 360 == 90:
                    dx, dy, pw, ph = -dy, dx, ph, pw
                elif rot % 360 == 180:
                    dx, dy = -dx, -dy
                elif rot % 360 == 270:
                    dx, dy, pw, ph = dy, -dx, ph, pw
                rs.append((cx + dx - pw / 2, cy + dy - ph / 2, cx + dx + pw / 2, cy + dy + ph / 2))
            out[d] = (layer, rs)
        else:
            if rot % 180 == 90:
                w, h = h, w
            out[d] = (layer, [(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)])
    return out


def check(comp, geom, place):
    rc = rects(comp, geom, place)
    off, hits = [], []
    for d in sorted(rc):
        layer, rs = rc[d]
        for x0, y0, x1, y1 in rs:
            if x0 < EDGE or y0 < EDGE or x1 > BOARD[0] - EDGE or y1 > BOARD[1] - EDGE:
                off.append('%-6s %-6s  x %6.2f..%6.2f  y %6.2f..%6.2f' % (d, layer, x0, x1, y0, y1))
                break
    names = [d for d in sorted(rc) if rc[d][1]]
    for i, a in enumerate(names):
        la, ra = rc[a]
        for b in names[i + 1:]:
            lb, rb = rc[b]
            if la != lb and comp[a] not in THRU and comp[b] not in THRU:
                continue
            worst = None
            for ax0, ay0, ax1, ay1 in ra:
                for bx0, by0, bx1, by1 in rb:
                    ox = min(ax1, bx1) - max(ax0, bx0)
                    oy = min(ay1, by1) - max(ay0, by0)
                    gap = min(ox, oy)
                    if gap > -CLEAR + 2e-3 and (worst is None or gap > worst[0]):
                        worst = (gap, ox, oy)
            if worst:
                hits.append((round(worst[0], 3), a, b, round(worst[1], 3), round(worst[2], 3)))
    return off, sorted(hits, reverse=True)


def main():
    comp, ext, place, src, missing, overflow = build()
    geom = lib_geometry()
    off, hits = check(comp, geom, place)
    print('\nplaced %d of %d components' % (len(place), len(comp)))
    print('\nOFF-BOARD or within %.2f mm of the edge: %d' % (EDGE, len(off)))
    for s in off:
        print('   ' + s)
    print('\nPAIRS CLOSER THAN %.2f mm: %d' % (CLEAR, len(hits)))
    for g, a, b, ox, oy in hits[:40]:
        print('   %-6s %-6s  overlap x %6.2f  y %6.2f   (%s / %s)' % (a, b, ox, oy, comp[a], comp[b]))
    ok = not off and not hits and not missing and not overflow
    print('\n%s' % ('PLACEMENT CLEAN' if ok else 'NOT CLEAN -- fix the above'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
