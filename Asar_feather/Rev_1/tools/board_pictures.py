# -*- coding: utf-8 -*-
"""Asar A7 top and bottom pictures, to scale, from the saved board. 2026-11-18. READ-ONLY on every input.

    "C:/Program Files/KiCad/10.0/bin/python.exe" -u tools/picture_dump.py     (refresh after any board change)
    python tools/board_pictures.py
        -> docs/pin_labels_proposal.png   top side: the silk as placed, red rings on X2 pins without a label
        -> docs/pin_labels_bottom.png     bottom side seen from below (mirrored): which pin names fit on the bottom silk

Replaces the 2026-11-06/08 scratch scripts (pic_labels2.py and the bottom one), which drew a routing-stage model
from before the micro-B X1, the side-entry X4 and the LTC3556 block. Same visual language: dark-green board, gold
pads, black drills, black IC bodies, coloured LEDs, grey switches, a faint trace pattern, white bold silk fitted into
the stroke text's own ink box. Grey text is a note (part names, designators), never silk; red names are notes too.

Inputs
  tools/picture_dump.json   pads as copper polygons, tracks, vias with the outer layers they reach, overlay lines,
                            Mechanical 3 bodies, X1's Mechanical 7 flange
  the PcbDoc's Texts6       the silk texts (anchor, height, stroke, rotation), read here with olefile because KiCad
                            redraws Altium's stroke font in its own font (labels came out up to 0.41 mm east). The
                            PcbDoc's md5 must equal the dump's.
  vivado/asar_feather_pins.xdc  X2's CHAN nets -> Feather names; the other X2 names are checked against their nets

Altium stroke font ink (checked against fabrication/..._2026-11-17_PROVISIONAL.zip asar_feather.GTO): every glyph
advances one text height except '1' and 'I' (5/6); the last glyph's ink is 2/3 of the height wide (1/3 for '1' and
'I'); the ink box adds half the stroke on every side.

Bodies: Mechanical 3 where the footprint has a real one (this board's body layer); the ICs and Q1 from their package
size (PKG) centred on their pads (Q1's Mechanical 3 holds copies of its lands); the R34 array (742C083, no Mechanical
3) from its 3.2 x 1.6 mm package, drawn under its pads like the other passives; X5 from its silk lines (6.0 mm wide,
front at its silk front line, 4.25 mm deep per JST's SM04B-SRSS-TB drawing); two-pad passives without one from
their pads. X1 adds its Mechanical 7 flange; in the bottom view the part of X1 past the west edge shows too.

Bottom silk fit (the proposal, nothing is placed on the board): each Feather name at the top labels' size, in the
same row as the top labels, centred on its pin, may slide up to 0.6 mm sideways and 1.5 mm toward the board centre.
It must keep 0.15 mm from every copper pad on the bottom (through-hole rings and holes included), 0.10 mm from
bottom part bodies, 0.30 mm from the board edge and 0.15 mm from the names already placed (west to east), and no
other pad or body may sit between the name and its pin. Vias are not obstacles (tented). A pin whose name finds no
spot gets a red ring.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import struct
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, Polygon, Rectangle  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DUMP = os.path.join(HERE, 'picture_dump.json')
PCB = os.path.join(ROOT, 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc')
XDC = os.path.join(ROOT, 'vivado', 'asar_feather_pins.xdc')
OUT_TOP = os.path.join(ROOT, 'docs', 'pin_labels_proposal.png')
OUT_BOTTOM = os.path.join(ROOT, 'docs', 'pin_labels_bottom.png')

BOARD, COPPER, PAD, SILK, DRILL, VIA = '#14361f', '#2c6b3e', '#c9a94a', '#ffffff', '#0a0a0a', '#3a7f4f'
IC, IC_EDGE, METAL, METAL_EDGE, CREAM = '#1c1c1c', '#555555', '#c3c7cb', '#6d7378', '#efe9d4'
PART, PART_EDGE, BUTTON = '#161616', '#4a4a4a', '#b9b9b9'
RED_LED, GREEN_LED, NOTE, RING, GREY = '#ff4040', '#37e05a', '#c02020', '#ff5050', '#a9a9a9'
FB = FontProperties(family='DejaVu Sans', weight='bold')
FN = FontProperties(family='DejaVu Sans')
U = 2.54e-6                                   # Altium internal unit (1/10000 mil) in mm
LAYER = {33: 'top', 34: 'bottom'}             # Texts6 layer byte: Top / Bottom Overlay
ADV, INK = {'1': 5 / 6, 'I': 5 / 6}, {'1': 1 / 3, 'I': 1 / 3}

# X2 pads whose name comes from a fixed net; the CHAN nets are named by the XDC
FIXED = {1: ('RST', 'RST#'), 2: ('3V3', 'VCC3V3'), 3: ('AREF', 'AREF'), 4: ('GND', 'GND'), 5: ('A0', 'ANALOG-IO0'),
         6: ('A1', 'ANALOG-IO1'), 17: ('BAT', 'VBATT'), 18: ('EN', 'EN'), 19: ('USB', 'USB5V0')}
XDC_SHORT = {'MOSI': 'MO', 'MISO': 'MI'}
SILK_ALIAS = {'RS': 'RST'}                    # the reset pin's top label reads RS
# package body (long, short) from the datasheets (see footprints.py); the long side follows the longer pad spread
PKG = {'XC7A35T-CPG236': (10.0, 10.0), 'QFN-64-9X9-P0.5-EP4.35': (9.0, 9.0), 'FBGA-54-8X8-P0.8': (8.0, 8.0),
       'WSON-8-6X5-P1.27': (6.0, 5.0), 'QFN28-UFD-4X5': (5.0, 4.0), 'TDFN-8-2X3-P0.5': (3.0, 2.0),
       '32X25': (3.2, 2.5)}
ARRAY = {'742C083': (3.2, 1.6)}               # resistor arrays without a Mechanical 3 body (CTS 742C, 0603 x 4)
PIN1 = {'U1': 'A1', 'U2': '1', 'U3': 'A1', 'U4': '1', 'U8': '1', 'U10': '1'}
X5_DEPTH = 4.25
TOP_NOTES = {'U1': ('U1', 'XC7A35T'), 'U2': ('U2', 'FT2232HQ'), 'U3': ('U3', 'SDRAM'), 'U4': ('U4', 'FLASH'),
             'X1': ('X1', 'micro-B'), 'X4': ('X4', 'S2B-PH-SM4-TB'), 'X5': ('X5', 'STEMMA QT'), 'Q1': ('Q1',)}
CLR_PAD, CLR_BODY, CLR_EDGE, CLR_LABEL, SLIDE_X, SLIDE_Y = 0.15, 0.10, 0.30, 0.15, 0.6, 1.5


# ----------------------------------------------------------------------------------------------- data
def pin_names(D):
    chan = {}
    for line in open(XDC):
        m = re.search(r'get_ports \{F_(\w+)\}\]\s*;#\s*(\S+)', line)
        if m:
            chan[m.group(2)] = XDC_SHORT.get(m.group(1), m.group(1))
    names = {}
    for p in D['pads']:
        if p['ref'] != 'X2' or not p['pad']:
            continue
        n = int(p['pad'])
        if n in FIXED:
            assert p['net'] == FIXED[n][1], ('X2-%d' % n, p['net'], FIXED[n][1])
            names[n] = FIXED[n][0]
        else:
            names[n] = chan[p['net']]
    assert sorted(names) == list(range(1, 29)), sorted(names)
    return names


def ink_width(s, h):
    return (sum(ADV.get(c, 1.0) for c in s[:-1]) + INK.get(s[-1], 2 / 3)) * h


def ink_box(t):
    """Ink box (x0, x1, y0, y1) of an Altium stroke text, stroke included."""
    h, e, w, x, y = t['h'], t['stroke'] / 2, ink_width(t['text'], t['h']), t['x'], t['y']
    return {0: [x - e, x + w + e, y - e, y + h + e], 90: [x - h - e, x + e, y - e, y + w + e],
            180: [x - w - e, x + e, y - h - e, y + e], 270: [x - e, x + h + e, y - w - e, y + e]}[t['rot']]


def read_texts(path, md5):
    """Overlay texts that print: free texts, plus designators / comments whose component shows them."""
    import olefile
    if hashlib.md5(open(path, 'rb').read()).hexdigest() != md5:
        raise SystemExit('%s changed since picture_dump.json: re-run tools/picture_dump.py' % path)
    f = olefile.OleFileIO(path)
    comps = []
    for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
        if 'PATTERN=' in r:
            comps.append(dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x))
    d = f.openstream('Texts6/Data').read()
    out, i = [], 0
    while i + 5 <= len(d):
        i += 1                                            # object id (5 = text)
        subs = []
        for _ in range(2):
            n = struct.unpack('<I', d[i:i + 4])[0]
            subs.append(d[i + 4:i + 4 + n])
            i += 4 + n
        b, s = subs
        if b[0] not in LAYER:
            continue
        txt = s[1:1 + s[0]].decode('latin-1', 'replace') if s else ''
        comp = struct.unpack('<H', b[7:9])[0]
        owner = ''
        if comp != 0xFFFF:
            c = comps[comp]
            if c.get('NAMEON' if b[41] == 1 else 'COMMENTON') != 'TRUE':
                continue
            owner = c.get('SOURCEDESIGNATOR', '?')
        if not txt.strip():
            continue
        if LAYER[b[0]] == 'bottom':
            raise NotImplementedError('Bottom Overlay text %r: add mirrored-text support' % txt)
        out.append(dict(text=txt, side=LAYER[b[0]], owner=owner, x=struct.unpack('<i', b[13:17])[0] * U,
                        y=struct.unpack('<i', b[17:21])[0] * U, h=struct.unpack('<i', b[21:25])[0] * U,
                        rot=round(struct.unpack('<d', b[27:35])[0]) % 360, stroke=struct.unpack('<i', b[36:40])[0] * U))
    for t in out:
        t['box'] = ink_box(t)
    return out


def extent(polys):
    xs = [q[0] for poly in polys for q in poly]
    ys = [q[1] for poly in polys for q in poly]
    return [min(xs), max(xs), min(ys), max(ys)]


def parts_and_bodies(D):
    W, H = D['board']['w'], D['board']['h']
    pads = collections.defaultdict(list)
    for p in D['pads']:
        pads[p['ref']].append(p)
    silk = collections.defaultdict(list)
    for s in D['silk']:
        silk[s['owner']].append(s)
    parts = {}
    for c in D['parts']:
        ref = c['ref']
        if not pads[ref] or not (0 <= c['x'] <= W and 0 <= c['y'] <= H):
            continue                                    # the CC logos sit off the board and have no pads
        ps = pads[ref]
        body, poly = None, c['body_poly']
        if c['footprint'] in PKG:
            a, b = PKG[c['footprint']]
            cs = [q for q in ps if not (len(ps) > 8 and q['pad'] == str(len(ps)))] or ps   # exposed pad last
            xs, ys = [q['x'] for q in cs], [q['y'] for q in cs]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            if (max(xs) - min(xs) >= max(ys) - min(ys)) != (a >= b):
                a, b = b, a
            body, poly = [cx - a / 2, cx + a / 2, cy - b / 2, cy + b / 2], None
        elif ref == 'X5':
            ls = silk['X5']
            ys = [s['y1'] for s in ls if s['y1'] == s['y2'] and s['x1'] != s['x2']]
            front = max(max(s['x1'], s['x2']) for s in ls)
            body = [front - X5_DEPTH, front, min(ys), max(ys)]
        elif c['body']:
            body = c['body']
        elif len(ps) == 2 and c['footprint'][:1] in 'RCIL':
            x0, x1, y0, y1 = extent([pl for q in ps for pl in q['poly']])
            if x1 - x0 >= y1 - y0:
                m = (y1 - y0) * 0.1
                body = [x0 + 0.03, x1 - 0.03, y0 + m, y1 - m]
            else:
                m = (x1 - x0) * 0.1
                body = [x0 + m, x1 - m, y0 + 0.03, y1 - 0.03]
        elif c['footprint'] in ARRAY:
            a, b = ARRAY[c['footprint']]
            xs, ys = [q['x'] for q in ps], [q['y'] for q in ps]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            if (max(xs) - min(xs) >= max(ys) - min(ys)) != (a >= b):
                a, b = b, a
            body = [cx - a / 2, cx + a / 2, cy - b / 2, cy + b / 2]
        parts[ref] = dict(c, body=body, body_poly=poly, pads=ps, flange=c['flange'] if ref == 'X1' else None)
    return parts


# ----------------------------------------------------------------------------------------------- drawing helpers
def text_in_box(ax, s, box, rot=0, color=SILK, z=8, font=FB):
    """Text stretched to fill box (x0, x1, y0, y1); rot 90 reads bottom-to-top."""
    tp = TextPath((0, 0), s, size=1, prop=font)
    e = tp.get_extents()
    x0, x1, y0, y1 = box
    tr = Affine2D().translate(-e.x0, -e.y0)
    if rot in (0, 180):
        tr = tr.scale((x1 - x0) / e.width, (y1 - y0) / e.height).translate(x0, y0)
    else:
        tr = tr.scale((y1 - y0) / e.width, (x1 - x0) / e.height).rotate_deg(90).translate(x1, y0)
    ax.add_patch(PathPatch(tp.transformed(tr), fc=color, lw=0, zorder=z))


def note(ax, lines, box, hmax=0.9, hmin=0.32, color=GREY, z=9, rot=0):
    """Grey note lines centred in box (x0, x1, y0, y1), font size at most hmax, shrunk to fit 88 % of the box;
    skipped (False) when that is below hmin. rot 90 reads bottom-to-top."""
    x0, x1, y0, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = (x1 - x0, y1 - y0) if not rot else (y1 - y0, x1 - x0)
    paths = [TextPath((0, 0), s, size=1, prop=FN) for s in lines]
    wid = max(tp.get_extents().width for tp in paths)
    cap = TextPath((0, 0), 'H', size=1, prop=FN).get_extents().height
    gap, n = 0.45, len(lines)
    h = min(hmax, 0.88 * bw / wid, 0.85 * bh / (cap * (n + gap * (n - 1))))
    if h < hmin:
        return False
    total = h * cap * (n + gap * (n - 1))
    for k, tp in enumerate(paths):
        e = tp.get_extents()
        base = total / 2 - h * cap * (k + 1) - h * cap * gap * k
        tr = Affine2D().scale(h).translate(-h * (e.x0 + e.width / 2), base)
        if rot:
            tr = tr.rotate_deg(90)
        ax.add_patch(PathPatch(tp.transformed(tr.translate(cx, cy)), fc=color, lw=0, zorder=z))
    return True


# ----------------------------------------------------------------------------------------------- one side
def draw_side(ax, D, parts, names, side, labels, pts_per_mm):
    W, H = D['board']['w'], D['board']['h']
    vx = (lambda x: x) if side == 'top' else (lambda x: W - x)

    def vbox(b):
        x0, x1 = sorted((vx(b[0]), vx(b[1])))
        return [x0, x1, b[2], b[3]]

    def vpoly(poly):
        return [(vx(x), y) for x, y in poly]

    def rect(b, z=4, **kw):
        b = vbox(b)
        ax.add_patch(Rectangle((b[0], b[2]), b[1] - b[0], b[3] - b[2], zorder=z, **kw))

    def outline(c, z=4, **kw):                           # the Mechanical 3 outline when it closes, else the box
        if c.get('body_poly'):
            ax.add_patch(Polygon(vpoly(c['body_poly']), closed=True, zorder=z, **kw))
        else:
            rect(c['body'], z=z, **kw)

    def micro_b(c, z):
        b = c['body']
        outline(c, z=z, fc=METAL, ec=METAL_EDGE, lw=0.6)
        rect((b[0] + 0.35, b[1] - 0.35, b[2] + 0.35, b[3] - 0.35), z=z + 0.5, fc='none', ec='#9aa0a5', lw=0.6)
        for k in range(1, 4):
            yy = b[2] + (b[3] - b[2]) * k / 4
            ax.plot([vx(b[0] + 0.9), vx(b[1] - 0.9)], [yy, yy], color='#a9aeb3', lw=0.8, zorder=z + 0.6)
        if c['flange']:                                  # front flange, wider than the shell
            rect(c['flange'], z=z + 0.7, fc=METAL, ec=METAL_EDGE, lw=0.6)

    ax.add_patch(Polygon(vpoly(D['board']['outline']), closed=True, fc=BOARD, ec='k', lw=1.5, zorder=0))
    for t in D['tracks']:
        if t['layer'] == side:
            ax.plot([vx(t['x1']), vx(t['x2'])], [t['y1'], t['y2']], color=COPPER, lw=max(0.5, t['w'] * 7),
                    solid_capstyle='round', zorder=1)
    for v in D['vias']:                                  # only the vias that reach this face (tented dots)
        if v[side]:
            ax.add_patch(Circle((vx(v['x']), v['y']), v['size'] * 0.36, fc=VIA, lw=0, zorder=1.5))

    mine = {r: c for r, c in parts.items() if c['side'] == side}
    big = {r for r, c in mine.items() if c['footprint'] in PKG or r[0] in 'XQ' or r in ('BTN', 'RESET', 'U7')
           or r.startswith('LD')}

    if side == 'bottom' and parts['X1']['side'] == 'top':   # X1 overhangs the west edge: that part shows from below
        micro_b(parts['X1'], z=-1)                           # (drawn under the board, so only the overhang shows)

    # passive bodies under their pads (they show between the pads)
    for r, c in mine.items():
        if r not in big and c['body']:
            rect(c['body'], z=1.8, fc=PART, ec=PART_EDGE, lw=0.3)
    # SMD pads of this side
    for p in D['pads']:
        if p['drill'] or p['side'] != side or p['ref'] not in parts:
            continue
        z = 5.5 if p['ref'] == 'X3' else 2              # microSD contacts show through the cage
        for poly in p['poly']:
            ax.add_patch(Polygon(vpoly(poly), closed=True, fc=PAD, lw=0, zorder=z))

    for r, c in mine.items():
        b = c['body']
        if r not in big or not b:
            continue
        fp = c['footprint']
        if r == 'Q1':                                    # crystal: metal lid
            rect(b, fc=METAL, ec=METAL_EDGE, lw=0.6)
            rect((b[0] + 0.3, b[1] - 0.3, b[2] + 0.3, b[3] - 0.3), z=4.5, fc='#d3d6d9', ec='none')
        elif fp in PKG or fp == 'SOT23-5':
            outline(c, fc=IC, ec=IC_EDGE, lw=0.6)
            p1 = [p for p in c['pads'] if p['pad'] == PIN1.get(r)]
            if p1 and fp in PKG:
                m = min(0.9, (b[1] - b[0]) / 4, (b[3] - b[2]) / 4)
                px = min(max(p1[0]['x'], b[0] + m), b[1] - m)
                py = min(max(p1[0]['y'], b[2] + m), b[3] - m)
                ax.add_patch(Circle((vx(px), py), min(0.3, m * 0.6), fc='#3a3a3a', lw=0, zorder=5))
        elif r == 'X1':                                  # micro-B shell overhanging the west edge
            micro_b(c, z=4)
        elif r == 'X3':                                  # microSD socket
            outline(c, fc=IC, ec=IC_EDGE, lw=0.6)
        elif r == 'X4':                                  # JST PH side entry: housing, mouth toward the north edge
            outline(c, fc=CREAM, ec='#333333', lw=0.5)
            rect((b[0] + 0.9, b[1] - 0.9, b[3] - 3.2, b[3] - 0.25), z=4.5, fc='#ddd5ba', ec='#8a8470', lw=0.5)
        elif r == 'X5':
            rect(b, fc=CREAM, ec='#333333', lw=0.5)
        elif r in ('BTN', 'RESET'):
            outline(c, fc=BUTTON, ec='#333333', lw=0.5)
            ax.add_patch(Circle((vx((b[0] + b[1]) / 2), (b[2] + b[3]) / 2), 0.8, fc='#2a2a2a', zorder=5))
        elif r == 'LD0':
            outline(c, fc='#f4f4ff', ec='k', lw=0.4)
            ax.add_patch(Circle((vx((b[0] + b[1]) / 2), (b[2] + b[3]) / 2), 0.45, fc='#c0c8ff', ec='#6070ff',
                                lw=0.6, zorder=5))
        elif r.startswith('LD'):
            colour = RED_LED if 'red' in c['value'].lower() else GREEN_LED
            xs = [q['x'] for q in c['pads']]
            cx, cy = sum(xs) / len(xs), sum(q['y'] for q in c['pads']) / len(xs)
            w, h = (1.6, 0.8) if max(xs) - min(xs) > 0.5 else (0.8, 1.6)
            rect((cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2), fc=colour, ec='k', lw=0.4)

    # through-hole pads, mounting holes and slots on top of everything
    for p in D['pads']:
        if not p['drill']:
            continue
        x, y = vx(p['x']), p['y']
        if not p['plated'] or (p['ref'] == 'X2' and not p['pad']):
            ax.add_patch(Circle((x, y), p['drill'] / 2, fc=DRILL, ec=PAD, lw=0.5, zorder=6))
            continue
        for poly in p['poly']:
            ax.add_patch(Polygon(vpoly(poly), closed=True, fc=PAD, lw=0, zorder=6))
        if p['slot']:
            x0, x1, y0, y1 = extent(p['poly'])
            ln, wd = max(p['slot']), min(p['slot'])
            w, h = (ln, wd) if x1 - x0 >= y1 - y0 else (wd, ln)
            ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                        boxstyle='round,pad=0,rounding_size=%g' % (wd / 2 - 0.01), fc=DRILL, lw=0,
                                        zorder=6.1))
        else:
            ax.add_patch(Circle((x, y), p['drill'] / 2, fc=DRILL, lw=0, zorder=6.1))

    # silk: overlay lines as placed, then the texts
    for s in D['silk']:
        if s['side'] == side:
            ax.plot([vx(s['x1']), vx(s['x2'])], [s['y1'], s['y2']], color=SILK, lw=s['w'] * pts_per_mm,
                    solid_capstyle='round', zorder=8)
    for t in labels:
        text_in_box(ax, t['text'], vbox(t['box']), t['rot'])

    # notes
    if side == 'top':
        for r, lines in TOP_NOTES.items():
            if r in mine and mine[r]['body']:
                b = vbox(mine[r]['body'])
                if r == 'X4':                            # between the pad notch and the mouth
                    b = [b[0], b[1], b[2] + 1.75, b[3] - 3.3]
                if r == 'X5':
                    note(ax, lines, b, hmax=0.75, rot=90)
                else:
                    note(ax, lines, b, hmax=0.95 if r[0] == 'U' else 0.7)
    else:
        for r, c in mine.items():
            if c['body']:
                b = vbox(c['body'])
                if max(b[1] - b[0], b[3] - b[2]) < 1.4:
                    continue
                note(ax, (r,), b, hmax=0.62, hmin=0.4, rot=0 if b[1] - b[0] >= b[3] - b[2] else 90)

    # red rings on X2 pins without a label on this side
    done = {t['pin'] for t in labels if t.get('pin')}
    missing = []
    for p in sorted((q for q in parts['X2']['pads'] if q['pad']), key=lambda q: vx(q['x'])):
        n = int(p['pad'])
        if n in done:
            continue
        ax.add_patch(Circle((vx(p['x']), p['y']), 1.0, fc='none', ec=RING, lw=1.6, zorder=7))
        ny = H + 0.75 if p['y'] > H / 2 else -0.75
        ax.text(vx(p['x']), ny, names[n], ha='center', va='center', fontsize=9, color=NOTE, zorder=9)
        missing.append(names[n])
    return missing


# ----------------------------------------------------------------------------------------------- labels
def top_labels(texts, names):
    by_name = {v: k for k, v in names.items()}
    return [dict(t, pin=by_name.get(SILK_ALIAS.get(t['text'], t['text'])) if not t['owner'] else None)
            for t in texts if t['side'] == 'top']


def bottom_labels(D, parts, names, top):
    """The proposal: which Feather names fit on the bottom silk (rule in the module docstring)."""
    W, H = D['board']['w'], D['board']['h']
    obstacles = []                                       # (box, clearance, what)
    for p in D['pads']:
        if p['ref'] not in parts:
            continue
        r = p['drill'] / 2
        hole = [p['x'] - r, p['x'] + r, p['y'] - r, p['y'] + r]
        if p['side'] in ('bottom', 'both'):
            obstacles.append((extent(p['poly']) if p['poly'] else hole, CLR_PAD, p['ref'] + '-' + p['pad']))
        elif p['drill']:                                 # an unplated hole is open on the bottom too
            obstacles.append((hole, CLR_PAD, p['ref'] + '-' + p['pad']))
    for c in parts.values():
        if c['side'] == 'bottom' and c['body']:
            obstacles.append((c['body'], CLR_BODY, c['ref']))

    template = [t for t in top if t['text'] == 'BAT']
    assert len(template) == 1
    h, stroke = template[0]['h'], template[0]['stroke']
    rows = collections.defaultdict(list)                 # the top labels' rows: ink y0 per row
    for t in top:
        if t['pin'] and t['rot'] == 0:
            rows[t['pin'] >= 17].append(t['box'][2])
    row = {k: sorted(v)[len(v) // 2] for k, v in rows.items()}

    def clear(b, o, c):
        return b[1] + c <= o[0] or o[1] + c <= b[0] or b[3] + c <= o[2] or o[3] + c <= b[2]

    placed, out = [], []
    pins = sorted((q for q in parts['X2']['pads'] if q['pad']), key=lambda q: (int(q['pad']) >= 17, q['x']))
    steps = [k / 10 for k in range(0, int(SLIDE_X * 10) + 1)]
    cands = sorted(((dx, dy / 10) for dx in steps for dy in range(0, int(SLIDE_Y * 10) + 1) for dx in {dx, -dx}),
                   key=lambda q: (2 * abs(q[0]) + q[1], abs(q[0]), q[0]))
    for p in pins:
        n = int(p['pad'])
        own = 'X2-%d' % n
        north = n >= 17
        w = ink_width(names[n], h) + stroke
        ring = extent(p['poly'])
        for dx, dy in cands:
            y0 = row[north] + (-dy if north else dy)
            b = [p['x'] - w / 2 + dx, p['x'] + w / 2 + dx, y0, y0 + h + stroke]
            if b[0] < CLR_EDGE or b[1] > W - CLR_EDGE or b[2] < CLR_EDGE or b[3] > H - CLR_EDGE:
                continue
            if not (all(clear(b, o, c) for o, c, _ in obstacles) and all(clear(b, o, CLR_LABEL) for o in placed)):
                continue
            # nothing else between the name and its own pin
            gap = [b[0], b[1], b[3], ring[2]] if north else [b[0], b[1], ring[3], b[2]]
            if gap[3] > gap[2] and not all(clear(gap, o, 0) for o, _, what in obstacles if what != own):
                continue
            placed.append(b)
            out.append(dict(text=names[n], box=b, rot=0, pin=n, dx=round(dx, 2), dy=round(dy, 2)))
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', default=DUMP)
    ap.add_argument('--pcb', default=PCB)
    a = ap.parse_args()
    D = json.load(open(a.dump))
    texts = read_texts(a.pcb, D['board']['md5'])
    names = pin_names(D)
    parts = parts_and_bodies(D)
    md5 = D['board']['md5'][:8]
    W, H = D['board']['w'], D['board']['h']

    def figure(xr, yr):
        fig = plt.figure(figsize=(13, 6.6), dpi=115, facecolor='white')
        ax = fig.add_axes([0.01, 0.01, 0.98, 0.91])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xlim(*xr)
        ax.set_ylim(*yr)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        fig.canvas.draw()
        bb = ax.get_window_extent()                      # after the equal-aspect squeeze
        return fig, ax, bb.width / fig.dpi * 72 / (xr[1] - xr[0])

    top = top_labels(texts, names)
    fig, ax, ppm = figure((-1.6, W + 0.9), (-1.5, H + 0.9))
    miss_top = draw_side(ax, D, parts, names, 'top', top, ppm)
    saved = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(a.pcb)))   # was a fixed 2026-11-18 until 11-20
    ax.set_title('Asar A7 top side, to scale (board %s, saved %s). White: silk as placed. Red rings: pins with no '
                 'label (red names are notes). Grey: notes, not silk.' % (md5, saved), fontsize=9.5, loc='left')
    fig.savefig(OUT_TOP, facecolor='white')
    plt.close(fig)

    bot = bottom_labels(D, parts, names, top)
    fig, ax, ppm = figure((-0.9, W + 1.6), (-1.5, H + 1.5))
    miss_bot = draw_side(ax, D, parts, names, 'bottom', bot, ppm)
    ax.set_title('Asar A7 bottom, seen from below (mirrored), to scale (board %s). White names: pins that fit '
                 '(proposal, not on the board); ticks at U8, JP4: real silk. Red rings: no room. Grey: designators.'
                 % md5, fontsize=9, loc='left')
    fig.savefig(OUT_BOTTOM, facecolor='white')
    plt.close(fig)

    print('board', D['board']['md5'])
    print('top: %d silk texts; unlabelled X2 pins: %s' % (len(top), ' '.join(miss_top) or 'none'))
    print('bottom: names that fit:', ' '.join('%s(%+.1f,%.1f)' % (t['text'], t['dx'], t['dy']) for t in bot))
    print('bottom: no room:', ' '.join(miss_bot) or 'none')
    print(OUT_TOP)
    print(OUT_BOTTOM)


if __name__ == '__main__':
    main()
