"""Bottom-side picture of a board model region (read-only helper for build.py / the README picture).

    python draw.py model.json out.png x0 x1 y0 y1 [title] [--layer 'Bottom Layer']
As a module: panel(ax, M, comps, box, title, layer, hilite)
"""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools'
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402

JT = {'TCK': '#d62728', 'TMS': '#1f77b4', 'TDI': '#2ca02c', 'TDO': '#ff7f0e', 'GND': '#555555', 'VCC3V3': '#9467bd'}


def panel(ax, M, comps, box, title, layer='Bottom Layer', hilite=('JP3', 'JP4'), inner=False):
    x0, x1, y0, y1 = box
    side = 'Bottom' if layer == 'Bottom Layer' else 'Top'
    parts = body_check.build(M, comps)[side]
    for name, P in parts.items():
        for b in P['body']:
            if b[2] < x0 - 1 or b[0] > x1 + 1 or b[3] < y0 - 1 or b[1] > y1 + 1:
                continue
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=True, fc='#f3e6c4', ec='#a08040',
                                   lw=0.8, ls='--', zorder=1, alpha=0.6))
            cx, cy = (max(b[0], x0) + min(b[2], x1)) / 2, (max(b[1], y0) + min(b[3], y1)) / 2
            ax.text(cx, cy, name, fontsize=5, color='#806020', ha='center', va='center', zorder=6, alpha=0.8, clip_on=True)
    for t in M['tracks']:
        if t['layer'] != layer:
            continue
        if max(t['x1'], t['x2']) < x0 - 1 or min(t['x1'], t['x2']) > x1 + 1:
            continue
        c = JT.get(t['net'], '#3a7d44' if False else '#4a9a5a')
        if t['net'] not in JT:
            c = '#9fc9a6'
        ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=c, lw=max(t['w'] * 28, 0.8), solid_capstyle='round',
                zorder=3 if t['net'] in JT else 2)
    for p in M['pads']:
        L = p['layers'] or body_check.STACK
        if layer not in L:
            continue
        if p['x'] < x0 - 1 or p['x'] > x1 + 1 or p['y'] < y0 - 1 or p['y'] > y1 + 1:
            continue
        hot = p['ref'] in hilite
        c = JT.get(p['net'], '#c0392b') if hot else '#c8a050'
        if p['shape'] == 'circle' or p['ref'] in ('U1', 'U3'):
            ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, fc=c, ec='k' if hot else 'none', lw=0.8,
                                zorder=4, alpha=0.9))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=c, ec='none',
                                   zorder=4, alpha=0.85))
        if hot:
            ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=4.5, ha='center',
                    va='center', zorder=8, color='white', weight='bold')
    for v in M['vias']:
        if layer not in v['span']:
            continue
        if v['x'] < x0 - 1 or v['x'] > x1 + 1 or v['y'] < y0 - 1 or v['y'] > y1 + 1:
            continue
        c = JT.get(v['net'], '#777777')
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc=c, ec='k', lw=0.4, zorder=5, alpha=0.9))
        ax.add_patch(Circle((v['x'], v['y']), v['hole'] / 2, fc='white', ec='none', zorder=5))
    if inner:      # the JTAG nets on the inner layers, dashed, for context
        for t in M['tracks']:
            if t['layer'] in ('L3-SIG', 'L4-SIG') and t['net'] in ('TCK', 'TMS', 'TDI', 'TDO'):
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=JT[t['net']], lw=1.0, ls=(0, (2, 1.5)),
                        alpha=0.75, zorder=2.5)
        for v in M['vias']:
            if 'Bottom Layer' not in v['span'] and v['net'] in ('TCK', 'TMS', 'TDI', 'TDO') and x0 <= v['x'] <= x1 and y0 <= v['y'] <= y1:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec=JT[v['net']], lw=0.8, ls='--', zorder=5))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_title(title, fontsize=8)
    ax.tick_params(labelsize=6)
    ax.grid(True, lw=0.2, alpha=0.4)


def main():
    a = sys.argv[1:]
    layer = 'Bottom Layer'
    if '--layer' in a:
        i = a.index('--layer')
        layer = a[i + 1]
        del a[i:i + 2]
    M = json.load(open(a[0]))
    comps = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'comps.json')))
    box = tuple(float(v) for v in a[2:6])
    fig, ax = plt.subplots(figsize=(14, 14 * (box[3] - box[2]) / (box[1] - box[0]) + 0.6))
    panel(ax, M, comps, box, a[6] if len(a) > 6 else layer, layer)
    fig.tight_layout()
    fig.savefig(a[1], dpi=170)


if __name__ == '__main__':
    main()
