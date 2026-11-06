# -*- coding: utf-8 -*-
"""Before/after picture of the C123 move (docs/c123_move.png), drawn from two board models.

    git show f2ddd8f:Zulu_Altrium/tools/route_inputs.json > before.json      the board before the ECO
    python tools/c123_plot.py before.json tools/route_inputs.json docs/c123_move.png
"""
import json, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
BEFORE, AFTER, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
COL = {'VCCADC': '#d62728', 'GNDADC': '#2ca02c', 'VCC1V0': '#ff7f0e', 'GND': '#7f7f7f'}
LAY = {'Top': '-', 'Bottom': '-', 'L3-SIG': '--', 'L4-SIG': ':'}
def draw(ax, path, win, title):
    d = json.load(open(path)); x0, x1, y0, y1 = win
    inwin = lambda x, y, m=0.6: x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m
    for t in d['tracks']:
        if not (inwin(t['x1'], t['y1']) or inwin(t['x2'], t['y2'])): continue
        c = COL.get(t['net'], '#c8c8c8'); hot = t['net'] in COL
        lw = max(t['width'] * 72 / ((x1 - x0) / 5.2) * 0.9, 0.6)
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], LAY.get(t['layer'], '-'), color=c,
                lw=lw, alpha=(0.2 if t['width'] > 0.6 else (0.95 if t['layer'] == 'Bottom' else 0.45)) if hot else 0.35, solid_capstyle='round', zorder=3 if hot else 1)
    for v in d['vias']:
        if inwin(v['x'], v['y']):
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec=COL.get(v['net'], '#9a9a9a'), lw=1.2, zorder=4))
            ax.add_patch(Circle((v['x'], v['y']), 0.10, fc='#444', ec='none', zorder=4))
    for p in d['bottom_pads']:
        if inwin(p['x'], p['y'], 0.3):
            ax.add_patch(Rectangle((p['x'] - p['sx'] / 2, p['y'] - p['sy'] / 2), p['sx'], p['sy'], fc=COL.get(p['net'], '#bbbbbb'),
                                   ec='k', lw=0.6, alpha=0.8, zorder=5))
            if p['ref'] in ('C123', 'C92', 'C124', 'L7'):
                ax.text(p['x'], p['y'] - p['sy'] / 2 - 0.08, '%s-%s' % (p['ref'], p['pad']), ha='center', va='top', fontsize=6.5, zorder=6)
    for p in d['top_pads']:
        if p['ref'] == 'U1' and inwin(p['x'], p['y'], 0.2) and p['net'] in COL:
            ax.add_patch(Circle((p['x'], p['y']), p['sx'] / 2, fc='none', ec=COL[p['net']], lw=0.9, ls='--', zorder=2))
            ax.text(p['x'] + 0.13, p['y'] + 0.13, p['pad'], fontsize=6, color=COL[p['net']], zorder=6)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=9)
    ax.tick_params(labelsize=7); ax.grid(alpha=0.15)
fig, axs = plt.subplots(2, 2, figsize=(11, 8.6))
U1W = (44.9, 48.6, 13.3, 16.1); BEADW = (51.6, 57.0, 1.7, 5.6)
draw(axs[0][0], BEFORE, U1W, 'U1 analog corner, before')
draw(axs[0][1], AFTER, U1W, 'U1 analog corner, after: C123 under the VCCADC/GNDADC vias, C92 one slot west')
draw(axs[1][0], BEFORE, BEADW, 'L7 bead, before: C123 (0402) on L7-2, its GNDADC chain to (56.20, 4.80)')
draw(axs[1][1], AFTER, BEADW, 'L7 bead, after: L7-2 straight to the VCCADC via, GNDADC tail gone')
fig.text(0.5, 0.01, 'Bottom solid, L3 dashed, L4 dotted; red VCCADC, green GNDADC, orange VCC1V0, grey GND; U1 balls dashed circles (Top); the 1.2 mm VCC1V0 trunk faded. '
         'Drawn from tools/route_inputs.json before and after the saved board.', ha='center', fontsize=7.5)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(OUT, dpi=130)
print('wrote', OUT)
