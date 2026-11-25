"""render.py <model.json> <out.png> x0,y0,x1,y1 LAYER[,LAYER] [plan.json] [NET,NET to highlight]
Draws pads / tracks / vias of the given layers in a window (debug aid; plan copper drawn on top in red)."""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import route_conn as C  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
COL = {'Top Layer': '#d04040', 'L3-SIG': '#40a040', 'L4-SIG': '#4060d0', 'Bottom Layer': '#c0a000',
       'L2-GND': '#808080', 'L5-VCC3V3': '#a060a0'}


def main():
    M = json.load(open(sys.argv[1]))
    x0, y0, x1, y1 = map(float, sys.argv[3].split(','))
    layers = sys.argv[4].split(',')
    plan = json.load(open(sys.argv[5])) if len(sys.argv) > 5 and sys.argv[5] != '-' else None
    hl = set(sys.argv[6].split(',')) if len(sys.argv) > 6 else set()
    fig, ax = plt.subplots(figsize=(max(6, (x1 - x0) * 1.6), max(4, (y1 - y0) * 1.6)))
    inside = lambda x, y, m=1.0: x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m  # noqa: E731
    for p in M['pads']:
        ls = p['layers'] or (STACK if p['drill'] else [])
        if not set(ls) & set(layers) or not inside(p['x'], p['y'], 2):
            continue
        a = 0.35 if p['net'] not in hl else 0.8
        c = 'k' if p['drill'] else COL.get([l for l in ls if l in layers][0], 'k')
        if C.pad_round(p):
            ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, color=c, alpha=a))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=c, alpha=a))
        if p['drill']:
            ax.add_patch(Circle((p['x'], p['y']), p['drill'] / 2, fill=False, color='w', lw=0.8))
        ax.text(p['x'], p['y'], '%s.%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=5, ha='center', va='center')

    def draw(ts, vs, extra):
        for t in ts:
            if t['layer'] not in layers or not (inside(t['x1'], t['y1'], 3) or inside(t['x2'], t['y2'], 3)):
                continue
            lw = t['w'] * 72 / ((x1 - x0) / (max(6, (x1 - x0) * 1.6)))
            a = 0.9 if (extra or t['net'] in hl) else 0.45
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='r' if extra else COL[t['layer']], lw=lw * 0.98,
                    alpha=a, solid_capstyle='round')
            if (extra or t['net'] in hl):
                ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2, t['net'], fontsize=4)
        for v in vs:
            sp = v.get('span') or STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
            if not set(sp) & set(layers) or not inside(v['x'], v['y']):
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color='m' if extra else 'k', alpha=0.5))
            ax.text(v['x'], v['y'] + 0.12, '%s %s' % (v['net'], sp[0][:2] + sp[-1][:2]), fontsize=3.5)
    draw(M['tracks'], M['vias'], False)
    if plan:
        draw(plan['tracks'], plan['vias'], True)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.grid(True, lw=0.2)
    ax.set_title('%s %s' % (os.path.basename(sys.argv[1]), ','.join(layers)))
    fig.savefig(sys.argv[2], dpi=110, bbox_inches='tight')


if __name__ == '__main__':
    main()
