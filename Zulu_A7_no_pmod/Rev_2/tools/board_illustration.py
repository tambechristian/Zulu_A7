# -*- coding: utf-8 -*-
"""Stylized top-view illustration of the Zulu_a7_no_pmod Rev 2 board (2026-11-14).  READ-ONLY on every input.

    python tools/board_illustration.py [--pcb PCBDOC] [--out PNG]

Same visual language as the Asar A7 Feather picture (docs/pin_labels_proposal.png in Asar_feather/Rev_1, drawn by
the pic_labels2.py scratch script): dark-green board, gold pads and plated holes with black drills, black IC bodies,
grey switch, coloured LED bodies, a faint green trace pattern, white bold silk text fitted into the silk's own boxes.

Inputs
  tools/route/bodies/base.json   pads (board mm, origin lower-left) and Top Layer tracks of the released board
                                 (PcbDoc md5 24de4472)
  tools/route/bodies/comps.json  side / pattern / rotation per part, fed to body_check.build() for the body boxes
  backups/Zulu_a7_no_pmod.PcbDoc.pre-bodies
                                 the released PcbDoc (md5 24de4472); its Texts6 stream gives the Top Overlay
                                 free texts (pin labels, pin numbers, board title) and the visible designators.
                                 Without olefile or the PcbDoc the labels fall back to short names derived from
                                 the X2 nets and the title 'ZULU A7 2.3'.
Output
  docs/board_illustration_top.png  (about 2000 px wide, white background)

What is drawn: Top-side parts and the through-hole parts only (U3, U8, U10, the inductors and most passives are on
the Bottom).  Stroke-font silk is drawn in DejaVu Sans Bold stretched into the stroke text's box (Altium's stroke
font: advance = height, last glyph about 2/3 of the height wide).  X2 pins that carry no silk label get a red ring
and a small red note outside the board (a note, not silk).  The board outline is a plain rectangle; the corners are
rounded for the picture only.
"""
import argparse
import hashlib
import json
import os
import struct
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyBboxPatch, PathPatch, Rectangle
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import body_check  # noqa: E402  (same folder: BODY table and build())

BASE = os.path.join(HERE, 'route', 'bodies', 'base.json')
COMPS = os.path.join(HERE, 'route', 'bodies', 'comps.json')
PCB = os.path.join(ROOT, 'backups', 'Zulu_a7_no_pmod.PcbDoc.pre-bodies')
OUT = os.path.join(ROOT, 'docs', 'board_illustration_top.png')
RELEASED_MD5 = '24de4472b67b2cb5a592e9dee2bd7e1a'

# colours as the Asar picture
BOARD, COPPER, PAD, SILK, DRILL = '#14361f', '#2c6b3e', '#c9a94a', '#ffffff', '#0a0a0a'
IC, IC_EDGE, METAL, METAL_EDGE, CREAM = '#1c1c1c', '#555555', '#c3c7cb', '#6d7378', '#efe9d4'
RED_LED, GREEN_LED, NOTE = '#ff4040', '#37e05a', '#c02020'
FP = FontProperties(family='DejaVu Sans', weight='bold')
U = 2.54e-6                       # Altium internal unit (1/10000 mil) in mm
CORNER = 1.5                      # cosmetic corner radius (the real outline is square)
TIGHT = 0.84                      # bold text run length as a fraction of the stroke text's length


# ----------------------------------------------------------------------------------------------- silk text
def read_silk(path):
    """Top Overlay texts that print: free texts plus the designators whose component shows its name."""
    import olefile
    f = olefile.OleFileIO(path)
    comps = []
    for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
        if 'PATTERN=' in r:
            kv = dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x)
            comps.append(kv)
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
        if b[0] != 33:                                    # 33 = Top Overlay
            continue
        txt = s[1:1 + s[0]].decode('latin-1', 'replace') if s else ''
        comp = struct.unpack('<H', b[7:9])[0]
        if comp != 0xFFFF:
            if not (b[41] == 1 and comp < len(comps) and comps[comp].get('NAMEON') == 'TRUE'):
                continue                                   # hidden designator / comment
            kind = 'designator'
        else:
            kind = 'free'
        out.append(dict(text=txt, kind=kind, x=struct.unpack('<i', b[13:17])[0] * U,
                        y=struct.unpack('<i', b[17:21])[0] * U, h=struct.unpack('<i', b[21:25])[0] * U,
                        rot=round(struct.unpack('<d', b[27:35])[0]) % 360, stroke=struct.unpack('<i', b[36:40])[0] * U))
    return out


SHORT = {'CHAN-CLK': 'CLK', 'VCC3V3': '3V3', 'VCC1V8': '1V8', 'VCC1V0': '1V0', 'ANALOG-IO0': 'AI0',
         'ANALOG-IO1': 'AI1', 'RST#': 'RST', 'GND': 'GND', 'VU': 'VU'}


def short(net):
    if net in SHORT:
        return SHORT[net]
    if net.startswith('CHAN'):
        return 'C' + net[4:]
    return net


def fallback_silk(pads):
    """No PcbDoc: one label per X2 pin from its net, just inside the board, plus the title."""
    out = []
    for p in pads:
        if p['ref'] != 'X2':
            continue
        top = p['y'] > 12.7
        s = short(p['net'])
        h = 0.8
        w = (len(s) - 1) * h + 0.667 * h
        out.append(dict(text=s, kind='free', x=p['x'] - w / 2, y=p['y'] - 3.19 if top else p['y'] + 2.39, h=h, rot=0,
                        stroke=0.15))
    out.append(dict(text='ZULU A7 2.3', kind='free', x=37.7, y=5.0, h=1.3, rot=0, stroke=0.18))
    return out


def silk_box(t):
    """Box (x0, x1, y0, y1) of an Altium stroke-font text, stroke half-width included."""
    n = len(t['text'])
    h = t['h']
    w = (n - 1) * h + 0.667 * h
    e = t['stroke'] / 2
    x, y = t['x'], t['y']
    if t['rot'] == 0:
        return (x - e, x + w + e, y - e, y + h + e)
    if t['rot'] == 90:                                    # baseline runs up, glyph tops point to -x
        return (x - h - e, x + e, y - e, y + w + e)
    if t['rot'] == 180:
        return (x - w - e, x + e, y - h - e, y + e)
    return (x - e, x + h + e, y - w - e, y + e)           # 270


def text_in_box(ax, s, box, rot=0, color=SILK, z=8):
    """DejaVu Sans Bold stretched to fill box (x0, x1, y0, y1); rot 90 reads bottom-to-top (as the Asar script)."""
    tp = TextPath((0, 0), s, size=1, prop=FP)
    e = tp.get_extents()
    x0, x1, y0, y1 = box
    w, h = x1 - x0, y1 - y0
    tr = Affine2D().translate(-e.x0, -e.y0)
    if rot in (0, 180):
        tr = tr.scale(w / e.width, h / e.height).translate(x0, y0)
    else:
        tr = tr.scale(h / e.width, w / e.height).rotate_deg(90).translate(x1, y0)
    ax.add_patch(PathPatch(tp.transformed(tr), fc=color, lw=0, zorder=z))


# ----------------------------------------------------------------------------------------------- drawing
def on_top(p):
    return p['layers'] is None or 'Top Layer' in p['layers']


def draw(ax, M, D, silk, pts_per_mm):
    W, H = M['board']['w'], M['board']['h']
    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle='round,pad=0,rounding_size=%g' % CORNER, fc=BOARD, ec='k',
                                lw=1.5, zorder=0))

    # faint trace pattern: Top Layer tracks
    for t in M['tracks']:
        if t['layer'] == 'Top Layer':
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=COPPER, lw=max(0.5, t['w'] * pts_per_mm * 0.6),
                    solid_capstyle='round', zorder=1)

    bodies = body_check.build(M, D)['Top']
    side = {c['ref']: c['layer'] for c in D['comps']}
    refs = {}
    for p in M['pads']:
        refs.setdefault(p['ref'], []).append(p)

    # SMD pads on Top (under the bodies)
    for p in M['pads']:
        if p['drill'] or not on_top(p) or side.get(p['ref']) != 'TOP':
            continue
        z = 5 if p['ref'] in ('BTN',) else 2
        ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=PAD, lw=0, zorder=z))

    def box(ref):
        b = bodies.get(ref, {}).get('body') or []
        return b[0] if b else None

    def rect(b, z=4, **kw):
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], zorder=z, **kw))

    # ICs with a pin-1 dot
    for ref, pin1 in (('U1', 'A1'), ('U2', '1'), ('U4', '1')):
        b = box(ref)
        if not b:
            continue
        rect(b, fc=IC, ec=IC_EDGE, lw=0.6)
        p1 = [p for p in refs[ref] if p['pad'] == pin1]
        if p1:
            m = 0.9
            px = min(max(p1[0]['x'], b[0] + m), b[2] - m)
            py = min(max(p1[0]['y'], b[1] + m), b[3] - m)
            ax.add_patch(Circle((px, py), 0.3, fc='#3a3a3a', ec='none', zorder=5))
    # crystal: metal lid
    if box('Q1'):
        b = box('Q1')
        rect(b, fc=METAL, ec=METAL_EDGE, lw=0.6)
        rect((b[0] + 0.3, b[1] + 0.3, b[2] - 0.3, b[3] - 0.3), z=4.5, fc='#d3d6d9', ec='none')
    # resistors and the resistor array
    for ref in refs:
        if ref.startswith('R') and side.get(ref) == 'TOP' and box(ref):
            rect(box(ref), fc='#111111', ec='#555555', lw=0.3)
    # LEDs (colours from the silk comments: LD1/LD2 red, LD3/LD4 green, LD0 RGB)
    for ref, c in (('LD1', RED_LED), ('LD2', RED_LED), ('LD3', GREEN_LED), ('LD4', GREEN_LED)):
        if box(ref):
            rect(box(ref), fc=c, ec='k', lw=0.4)
    if box('LD0'):
        b = box('LD0')
        rect(b, fc='#f4f4ff', ec='k', lw=0.4)
        ax.add_patch(Circle(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), 0.5, fc='#c0c8ff', ec='#6070ff', lw=0.6, zorder=5))
    # push button
    if box('BTN'):
        b = box('BTN')
        rect(b, fc='#b9b9b9', ec='#333333', lw=0.5)
        ax.add_patch(Circle(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), 0.9, fc='#2a2a2a', zorder=5))
    # micro-USB shell (overhangs the north edge as the real receptacle does)
    if box('X1'):
        b = box('X1')
        rect(b, fc=METAL, ec=METAL_EDGE, lw=0.6)
        rect((b[0] + 0.35, b[1] + 0.35, b[2] - 0.35, b[3] - 0.35), z=4.5, fc='none', ec='#9aa0a5', lw=0.6)
        for k in range(1, 4):
            xx = b[0] + (b[2] - b[0]) * k / 4
            ax.plot([xx, xx], [b[1] + 0.9, b[3] - 0.9], color='#a9aeb3', lw=0.8, zorder=4.6)
    # microSD socket shell
    if box('X3'):
        b = box('X3')
        rect(b, fc=METAL, ec=METAL_EDGE, lw=0.6)
        rect((b[0] + 0.5, b[1] + 0.5, b[2] - 0.5, b[3] - 0.5), z=4.5, fc='none', ec='#9aa0a5', lw=0.6)
        for k in range(1, 6):
            yy = b[1] + (b[3] - b[1]) * k / 6
            ax.plot([b[0] + 1.2, b[2] - 1.2], [yy, yy], color='#b0b5ba', lw=0.6, zorder=4.6)
        # the signal pins exit at the back of the shell: keep them visible
        for p in refs['X3']:
            if p['pad'].isdigit():
                ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=PAD, lw=0,
                                       zorder=5))
    # battery JST PH (cream housing, as the Asar STEMMA QT)
    if box('X4'):
        rect(box('X4'), fc=CREAM, ec='#333333', lw=0.5)
        b = box('X4')
        rect((b[0] + 0.8, b[1] + 0.6, b[2] - 0.8, b[3] - 1.4), z=4.5, fc='#e2dbc1', ec='#8a8470', lw=0.4)

    # through-hole pads and plated holes on top of everything
    for p in M['pads']:
        if not p['drill']:
            continue
        under = p['ref'] == 'X1'                          # shell legs: hidden under the shell
        z = 3 if under else 6
        r = max(p['w'], p['h']) / 2
        if p['shape'] == 'rect' and p['drill'] > min(p['w'], p['h']):      # slot (X1 MS1/MS2)
            ax.add_patch(FancyBboxPatch((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'],
                                        boxstyle='round,pad=0,rounding_size=0.3', fc=PAD, lw=0, zorder=z))
            ax.add_patch(FancyBboxPatch((p['x'] - 0.3, p['y'] - p['drill'] / 2), 0.6, p['drill'],
                                        boxstyle='round,pad=0,rounding_size=0.29', fc=DRILL, lw=0, zorder=z + 0.1))
            continue
        if p['shape'] == 'rect':
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=PAD, lw=0, zorder=z))
        else:
            ax.add_patch(Circle((p['x'], p['y']), r, fc=PAD, lw=0, zorder=z))
        ax.add_patch(Circle((p['x'], p['y']), p['drill'] / 2, fc=DRILL, lw=0, zorder=z + 0.1))

    # silk
    labelled = set()
    for t in silk:
        if not t['text'].strip():
            continue
        x0, x1, y0, y1 = silk_box(t)
        # bold glyphs are heavier than the stroke font: narrow the run to TIGHT of its length, about its centre,
        # so neighbouring labels (1V0 1V8 3V3 ...) keep a visible gap
        if t['rot'] in (0, 180):
            c, half = (x0 + x1) / 2, (x1 - x0) * TIGHT / 2
            x0, x1 = c - half, c + half
        else:
            c, half = (y0 + y1) / 2, (y1 - y0) * TIGHT / 2
            y0, y1 = c - half, c + half
        text_in_box(ax, t['text'], (x0, x1, y0, y1), t['rot'])
    # an X2 pin counts as labelled when a silk text box sits within 1.3 mm of its column and row edge
    for p in refs.get('X2', []):
        for t in silk:
            x0, x1, y0, y1 = silk_box(t)
            if t['kind'] == 'free' and any(c.isalpha() for c in t['text']) and x0 - 0.6 <= p['x'] <= x1 + 0.6 and \
                    min(abs(y0 - p['y']), abs(y1 - p['y'])) < 4.5:
                labelled.add(p['pad'])
    notes = []
    for p in sorted(refs.get('X2', []), key=lambda q: q['x']):
        if p['pad'] in labelled:
            continue
        ax.add_patch(Circle((p['x'], p['y']), 1.0, fc='none', ec='#ff5050', lw=1.6, zorder=7))
        ny = H + 0.75 if p['y'] > H / 2 else -0.75
        ax.text(p['x'], ny, short(p['net']), ha='center', va='center', fontsize=10, color=NOTE, zorder=9)
        notes.append(p['pad'])
    return notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pcb', default=PCB)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    M = json.load(open(BASE))
    D = json.load(open(COMPS))
    try:
        md5 = hashlib.md5(open(a.pcb, 'rb').read()).hexdigest()
        if md5 != RELEASED_MD5:
            print('note: %s md5 %s is not the released board %s' % (a.pcb, md5[:8], RELEASED_MD5[:8]))
        silk = read_silk(a.pcb)
        src = 'PcbDoc Texts6 (%d Top Overlay texts)' % len(silk)
    except Exception as e:                                # noqa: BLE001  (no olefile / no PcbDoc)
        silk = fallback_silk(M['pads'])
        src = 'net-derived fallback (%s)' % e

    W, H = M['board']['w'], M['board']['h']
    xr, yr = (-1.0, W + 1.0), (-1.9, H + 1.9)
    fig_w = 20.0
    fig_h = fig_w * (yr[1] - yr[0]) / (xr[1] - xr[0])
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=100, facecolor='white')
    ax = fig.add_axes([0, 0, 1, 1])
    pts_per_mm = fig_w * 72.0 / (xr[1] - xr[0])
    notes = draw(ax, M, D, silk, pts_per_mm)
    if notes:
        ax.text(xr[0] + 0.3, yr[0] + 0.45, 'Red rings: X2 pins with no silk label (red names are notes, not silk).',
                ha='left', va='center', fontsize=10, color='#555555')
    ax.set_xlim(*xr)
    ax.set_ylim(*yr)
    ax.set_aspect('equal')
    ax.axis('off')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    fig.savefig(a.out, facecolor='white')
    print('silk from', src)
    print('unlabelled X2 pins:', ', '.join(notes) or 'none')
    print(a.out)


if __name__ == '__main__':
    main()
