"""render.py <model.json> x0 y0 x1 y1 <out.png> [hl_net,hl_net,...] [plan.json]

Strategy-A working picture: the four routing layers (Top, L3, L4, Bottom) of a route model in a window; highlighted
nets in colour, JA*/PMOD nets in orange, every other net grey; vias drawn on every layer of their span (lasers thin
ring, buried dashed, through thick). A plan's new copper (tracks / vias) is drawn in black outline on top.
"""
import json
import math
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle, Polygon  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
ROUTE = ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
PAL = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#469990', '#9A6324',
       '#800000', '#808000', '#000075', '#e6beff']


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def main():
    M = json.load(open(sys.argv[1]))
    x0, y0, x1, y1 = [float(a) for a in sys.argv[2:6]]
    out = sys.argv[6]
    hl = sys.argv[7].split(',') if len(sys.argv) > 7 and sys.argv[7] else []
    plan = json.load(open(sys.argv[8])) if len(sys.argv) > 8 else None
    col = {n: PAL[i % len(PAL)] for i, n in enumerate(hl)}

    def c(net):
        if net in col:
            return col[net]
        if net.startswith('JA') or 'PMOD' in net:
            return '#ffb000'
        if net == 'GND':
            return '#9fd39f'
        if net == 'VCC3V3':
            return '#f2a0a0'
        return '#b8b8b8'
    sc = (x1 - x0) / 9.0
    fig, axs = plt.subplots(2, 2, figsize=(2 * 9.0 + 1, 2 * (y1 - y0) / sc + 1.5))
    for ax, L in zip(axs.flat, ROUTE):
        ax.set_title(L)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect('equal')
        ax.grid(True, lw=0.3, alpha=0.5)
        for p in M['pads']:
            ls = p['layers'] or (STACK if p['drill'] > 0 else [])
            if L not in ls or not (x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2):
                continue
            fc = c(p['net'] or '')
            if p['shape'] == 'circle' or p['ref'] == 'U1':
                ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, fc=fc, ec='k', lw=0.3, alpha=0.8))
            else:
                ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=fc, ec='k',
                                       lw=0.3, alpha=0.8))
            if p['net'] in col or (p['net'] or '').startswith('JA'):
                ax.text(p['x'], p['y'], '%s-%s' % (p['ref'], p['pad']), fontsize=4, ha='center', va='center')
        for t in M['tracks']:
            if t['layer'] != L:
                continue
            if max(t['x1'], t['x2']) < x0 - 1 or min(t['x1'], t['x2']) > x1 + 1 or max(t['y1'], t['y2']) < y0 - 1 or \
                    min(t['y1'], t['y2']) > y1 + 1:
                continue
            lw = t['w'] * 72 / sc * 0.85
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=c(t['net']), lw=lw, solid_capstyle='round',
                    alpha=0.9)
        for v in M['vias']:
            sp = span(v)
            if L not in sp or not (x0 - 1 < v['x'] < x1 + 1 and y0 - 1 < v['y'] < y1 + 1):
                continue
            ls = '--' if sp == ['L3-SIG', 'L4-SIG'] else '-'
            lw = 1.2 if sp == STACK else 0.4
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc=c(v['net']), ec='k', lw=lw, ls=ls, alpha=0.9))
        if plan:
            for t in plan.get('tracks', []):
                if t['layer'] == L:
                    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=0.6)
            for v in plan.get('vias', []):
                if L in span(v):
                    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='k', lw=0.8))
    handles = [plt.Line2D([], [], color=col[n], lw=4, label=n) for n in hl]
    if handles:
        fig.legend(handles=handles, loc='lower center', ncol=min(8, len(handles)), fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=110)


if __name__ == '__main__':
    main()
