"""Zoomed Bottom-layer plot (working aid for design_bottom.py): python zoom_plot.py x0 y0 x1 y1 out.png"""
import sys, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design_bottom as D


def draw(ax, objs, proxies, box, extra=None, labels=True):
    x0, y0, x1, y1 = box
    for r, b in proxies.items():
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ls='--', lw=0.6, ec='k'))
        ax.text((b[0] + b[2]) / 2, b[3], r, fontsize=5, ha='center', va='bottom', color='k')
    for o in objs:
        b = D.G.bbox(o)
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        net = o['net'] or ''
        isd = net.startswith('D') and net[1:].isdigit() or net.startswith('SDRAM-D')
        col = ('tab:orange' if isd else ('tab:green' if o.get('new') else 'tab:blue'))
        if o['kind'] == 'rect':
            g = o['g']
            ax.add_patch(Rectangle((g[0], g[1]), g[2] - g[0], g[3] - g[1], fc=col, ec='k', lw=0.3, alpha=0.8))
            if labels:
                ax.text((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, net[:9], fontsize=3.5, ha='center', va='center', rotation=90 if g[3] - g[1] > g[2] - g[0] else 0)
        elif o['kind'] == 'circ':
            g = o['g']
            ax.add_patch(Circle((g[0], g[1]), g[2], fc=col, ec='k', lw=0.3, alpha=0.8))
            if labels:
                ax.text(g[0], g[1], net[:7], fontsize=3, ha='center', va='center')
        else:
            g = o['g']
            ax.plot([g[0], g[2]], [g[1], g[3]], color=col, lw=max(g[4] * 2 * 72 / 25.4 * ax.figure.dpi / 72 * 0.0 + 0.1, 0.1),
                    solid_capstyle='round', alpha=0.85)
            # true width: draw as polygon-ish via linewidth in data units
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')


def draw_tracks_true_width(ax, objs, box):
    x0, y0, x1, y1 = box
    import numpy as np
    for o in objs:
        if o['kind'] != 'seg':
            continue
        b = D.G.bbox(o)
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        g = o['g']
        dx, dy = g[2] - g[0], g[3] - g[1]
        L = (dx * dx + dy * dy) ** 0.5 or 1e-9
        nx, ny = -dy / L * g[4], dx / L * g[4]
        net = o['net'] or ''
        isd = net.startswith('D') and net[1:].isdigit() or net.startswith('SDRAM-D')
        col = ('tab:orange' if isd else ('tab:green' if o.get('new') else 'tab:blue'))
        ax.add_patch(Polygon([(g[0] + nx, g[1] + ny), (g[2] + nx, g[3] + ny), (g[2] - nx, g[3] - ny), (g[0] - nx, g[1] - ny)],
                             fc=col, ec='none', alpha=0.75))
        for (cx, cy) in ((g[0], g[1]), (g[2], g[3])):
            ax.add_patch(Circle((cx, cy), g[4], fc=col, ec='none', alpha=0.75))
        ax.text((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, net[:8], fontsize=2.8, ha='center', va='center', color='k')


if __name__ == '__main__':
    x0, y0, x1, y1 = map(float, sys.argv[1:5])
    out = sys.argv[5]
    objs = D.load_bottom()
    prox = D.comp_proxies()
    fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / (x1 - x0) + 0.5), dpi=150)
    draw(ax, [o for o in objs if o['kind'] != 'seg'], prox, (x0, y0, x1, y1))
    draw_tracks_true_width(ax, objs, (x0, y0, x1, y1))
    ax.grid(True, lw=0.2)
    import numpy as np
    ax.set_xticks(np.arange(round(x0), x1, 0.5)); ax.set_yticks(np.arange(round(y0 * 2) / 2, y1, 0.25))
    ax.tick_params(labelsize=5)
    fig.savefig(out, bbox_inches='tight')
