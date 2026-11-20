"""render.py <model.json> <out.png> [x0,y0,x1,y1] [net1,net2,...]  -- per-layer picture of a route model region.
Highlighted nets in colour (labelled), everything else grey; vias drawn on every layer of their span."""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

LAYERS = ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    box = [float(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 and sys.argv[3] else [44, 0, 69.85, 25.4]
    hl = sys.argv[4].split(',') if len(sys.argv) > 4 and sys.argv[4] else []
    cmap = plt.get_cmap('tab20')
    col = {n: cmap(i % 20) for i, n in enumerate(hl)}
    W = box[2] - box[0]
    Hh = box[3] - box[1]
    fig, axs = plt.subplots(2, 2, figsize=(2 * W * 0.9 + 2, 2 * Hh * 0.9 + 2))
    for ax, l in zip(axs.flat, LAYERS):
        ax.set_title(l)
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
        ax.set_aspect('equal')
        ax.grid(True, lw=0.2)
        for p in M['pads']:
            if not (box[0] - 2 < p['x'] < box[2] + 2 and box[1] - 2 < p['y'] < box[3] + 2):
                continue
            lay = p['layers'] or []
            if l not in lay and not p['drill']:
                continue
            c = col.get(p['net'], (0.7, 0.7, 0.7, 1))
            if p['shape'] == 'circle' or p['ref'] == 'U1':
                ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, fc=c, ec='k', lw=0.3, alpha=0.6))
            else:
                ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], fc=c, ec='k', lw=0.3,
                                       alpha=0.6))
            if p['net'] in col or p['ref'] != 'U1':
                ax.text(p['x'], p['y'], '%s-%s' % (p['ref'], p['pad']), fontsize=3, ha='center', va='center')
        for t in M['tracks']:
            if t['layer'] != l:
                continue
            if max(t['x1'], t['x2']) < box[0] - 1 or min(t['x1'], t['x2']) > box[2] + 1:
                continue
            c = col.get(t['net'], (0.55, 0.55, 0.55, 1))
            lw = t['w'] * 72 * 0.9 * 0.0393701 * (fig.dpi / 72) * 10
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=c, lw=max(0.4, t['w'] * 25), solid_capstyle='round',
                    alpha=0.9 if t['net'] in col else 0.6)
        for v in M['vias']:
            sp = v.get('span')
            if l not in sp:
                continue
            if not (box[0] - 1 < v['x'] < box[2] + 1):
                continue
            c = col.get(v['net'], (0.4, 0.4, 0.4, 1))
            thr = len(sp) == 6
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc=c, ec='r' if thr else 'k', lw=0.5 if thr else 0.2,
                                alpha=0.8))
        for n in hl:
            pass
    handles = [plt.Line2D([0], [0], color=col[n], lw=3) for n in hl]
    if hl:
        fig.legend(handles, hl, loc='upper center', ncol=min(10, len(hl)), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=110)


if __name__ == '__main__':
    main()
