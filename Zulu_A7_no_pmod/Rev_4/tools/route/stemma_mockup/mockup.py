"""Mock-up (2026-11-21, not on the board): STEMMA QT X5 (JST SM04B-SRSS-TB, Asar's footprint) on the TOP at the east
short edge, mating face at the edge, with C141, C142, C144, C145 (22 uF 0805 FPGA bulk caps) moved to the same XY on the
Bottom. Checks every body with tools/body_check.py, then draws top and bottom pictures with tools/board_illustration.py.

    python tools/route/stemma_mockup/mockup.py   -> docs/stemma_qt_mockup_top.png, docs/stemma_qt_mockup_bottom.png
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402
import board_illustration as BI  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

MOVED = ('C141', 'C142', 'C144', 'C145')
VU_LABEL_TOP = 4.65                                  # 'VU' pin-label ink box top + margin; X5's body must stay above it
PADS = [('1', 'GND', -3.875, -1.5), ('2', 'VCC3V3', -3.875, -0.5), ('3', 'SDA', -3.875, 0.5), ('4', 'SCL', -3.875, 1.5),
        ('MP1', 'GND', 0.0, -2.8), ('MP2', 'GND', 0.0, 2.8)]


def build(M, D, cy):
    M2, D2 = copy.deepcopy(M), copy.deepcopy(D)
    W = M2['board']['w']
    for p in M2['pads']:
        if p['ref'] in MOVED:
            p['layers'] = ['Bottom Layer']
    for c in D2['comps']:
        if c['ref'] in MOVED:
            c['layer'] = 'BOTTOM'
    mx = W - 1.2
    for n, net, dx, dy in PADS:
        w, h = (1.8, 1.2) if n.startswith('MP') else (1.55, 0.6)
        M2['pads'].append({'ref': 'X5', 'pad': n, 'net': net, 'x': round(mx + dx, 4), 'y': round(cy + dy, 4),
                           'shape': 'rect', 'w': w, 'h': h, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False})
    D2['comps'].append({'ref': 'X5', 'layer': 'TOP', 'rot': 0.0, 'pattern': 'JST-SM04B-SRSS-TB', 'height': 0})
    ps = [p for p in M2['pads'] if p['ref'] == 'X5']
    e = (min(p['x'] - p['w'] / 2 for p in ps), min(p['y'] - p['h'] / 2 for p in ps),
         max(p['x'] + p['w'] / 2 for p in ps), max(p['y'] + p['h'] / 2 for p in ps))
    body = (W - 4.3, cy - 3.0, W - 0.05, cy + 3.0)        # 6.0 wide, 4.25 deep, mating face at the edge
    D2['mech']['X5'] = {'side': 'Top', 'off': [body[0] - e[0], body[1] - e[1], body[2] - e[2], body[3] - e[3]]}
    return M2, D2, body


def main():
    M = json.load(open(os.path.join(TOOLS, 'route', 'release_gate', 'model.json')))
    D = json.load(open(os.path.join(TOOLS, 'route', 'release_gate', 'comps.json')))
    clean = []
    for k in range(0, 120):
        cy = round(3.5 + k * 0.05, 2)
        M2, D2, _ = build(M, D, cy)
        if not body_check.check(body_check.build(M2, D2), ['X5'] + list(MOVED), 0.10):
            clean.append(cy)
    clean = [c for c in clean if c - 3.0 >= VU_LABEL_TOP]
    print('clean X5 centre y range (bodies and the VU label): %.2f .. %.2f' % (clean[0], clean[-1]))
    cy = round((clean[0] + clean[-1]) / 2, 2)
    M2, D2, body = build(M, D, cy)
    print('X5 centre y %.2f, body %s, pads %s' % (cy, [round(v, 2) for v in body],
          [(p['pad'], p['x'], p['y']) for p in M2['pads'] if p['ref'] == 'X5']))
    # the vertical '21 GND' pin label lies under X5's mating face: in this mock-up it moves to the Bottom silk
    silk = [t for t in BI.read_silk(BI.PCB) if t['text'] != '21 GND']
    W, H = M2['board']['w'], M2['board']['h']
    xr, yr = (-1.0, W + 1.0), (-2.4, H + 1.9)
    fig_w = 20.0
    fig_h = fig_w * (yr[1] - yr[0]) / (xr[1] - xr[0])
    ppm = fig_w * 72.0 / (xr[1] - xr[0])
    for side in ('top', 'bottom'):
        fig = plt.figure(figsize=(fig_w, fig_h), dpi=100, facecolor='white')
        ax = fig.add_axes([0, 0, 1, 1])
        if side == 'top':
            BI.draw(ax, M2, D2, silk, ppm)
            b = body
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc='#efe9d4', ec='#333333', lw=0.6, zorder=4))
            ax.add_patch(Rectangle((b[2] - 0.9, b[1] + 0.9), 0.9, b[3] - b[1] - 1.8, fc='#2b2b2b', ec='#333333', lw=0.4, zorder=4.5))
            for p in M2['pads']:
                if p['ref'] == 'X5':
                    ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'],
                                           fc=BI.METAL if p['pad'].startswith('MP') else BI.PAD, ec=BI.METAL_EDGE, lw=0.4, zorder=4.6))
            ax.annotate('STEMMA QT (X5): JST SH 4-pin, cable plugs in from the east edge', xy=(b[2] - 0.6, b[1] + 0.4),
                        xytext=(W - 25.0, -1.35), fontsize=12, color='#b8860b', fontweight='bold', zorder=9,
                        arrowprops=dict(arrowstyle='->', color='#b8860b', lw=1.6))
            note = ('Mock-up, not on the board: STEMMA QT X5 (JST SM04B-SRSS-TB) at the top east edge, opening east; '
                    'C141, C142, C144, C145 moved underneath; pin label "21 GND" moves to the bottom silk.')
        else:
            BI.draw_bottom(ax, M2, D2, BI.read_silk(BI.PCB, 34), ppm)
            for r in MOVED:
                ps = [p for p in M2['pads'] if p['ref'] == r]
                x = W - sum(p['x'] for p in ps) / len(ps)
                y = max(p['y'] for p in ps) + 1.2
                ax.text(x, y, r, ha='center', va='bottom', fontsize=11, color='#ffd24d', zorder=9, fontweight='bold')
            note = 'Mock-up, bottom seen from below: C141, C142, C144, C145 (22 uF) moved here from the top, under X5.'
        ax.text(xr[0] + 0.3, yr[0] + 0.35, note, ha='left', va='center', fontsize=10, color='#555555')
        ax.set_xlim(*xr)
        ax.set_ylim(*yr)
        ax.set_aspect('equal')
        ax.axis('off')
        out = os.path.join(ROOT, 'docs', 'stemma_qt_mockup_%s.png' % side)
        fig.savefig(out, facecolor='white')
        print(out)


if __name__ == '__main__':
    main()
