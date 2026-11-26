"""Floorplan sketch renderer (2026-11-26). READ-ONLY on the board.

    python tools/floorplan_sketch.py PLAN.json OUT.png [--title TEXT] [--current]

PLAN.json holds {"placements": [{ref, side, cx, cy, w, h, rot, note}], "blocks": [{name, side, x0, y0, x1, y1, contents}]}.
The script draws two panels, TOP and BOTTOM. Both are seen from above (x-ray, not mirrored), so a part keeps its board
coordinates in both. It also prints a geometry check:
- parts outside the board;
- same-side overlaps closer than 0.4 mm;
- parts inside the header keep-out (y < 2.4 or y > 23.0, outside the gaps x 24.13-36.83);
- parts over the through-hole JTAG pins.

--compare draws today (left) beside PLAN (right). --current draws today's Rev 4 layout from tools/route/illustration (pad extents) instead of PLAN.json.
"""
import argparse
import collections
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 60.96, 25.4
GAP = (24.13, 36.83)
CLASS = [  # (prefixes, face colour, label)
    (('U1',), '#2b2b2b', 'FPGA'),
    (('U3',), '#4a3b8f', 'SDRAM'),
    (('U4',), '#6a5acd', 'Flash'),
    (('U2', 'U10', 'Q1'), '#1f5f8b', 'USB-JTAG/UART + clock'),
    (('BTN', 'LD', 'R4'), '#2e8b57', 'User I/O, LEDs, misc'),
    (('U8', 'U7', 'L'), '#b03a2e', 'Power'),
    (('X1', 'X3', 'X4', 'X5'), '#9e9e9e', 'Connectors'),
    (('JP',), '#c9a227', 'JTAG header'),
    (('C',), '#8d6e63', 'Bulk caps'),
]


def colour(ref):
    for pre, c, _ in CLASS:
        if ref.startswith(pre):
            return c
    return '#777777'


def current_plan():
    M = json.load(open(os.path.join(HERE, 'route', 'illustration', 'base.json')))
    D = json.load(open(os.path.join(HERE, 'route', 'illustration', 'comps.json')))
    side = {c['ref']: c['layer'] for c in D['comps']}
    bb = collections.defaultdict(lambda: [1e9, 1e9, -1e9, -1e9])
    for p in M['pads']:
        b = bb[p['ref']]
        b[0] = min(b[0], p['x'] - p['w'] / 2); b[1] = min(b[1], p['y'] - p['h'] / 2)
        b[2] = max(b[2], p['x'] + p['w'] / 2); b[3] = max(b[3], p['y'] + p['h'] / 2)
    keep = ('U1', 'U2', 'U3', 'U4', 'U7', 'U8', 'U10', 'Q1', 'X1', 'X3', 'X4', 'X5', 'R4', 'BTN', 'JP3', 'JP4',
            'L1', 'L2', 'L3', 'LD0', 'LD1', 'LD2', 'LD3', 'LD4', 'LD5', 'LD6')
    pl = []
    for r in keep:
        b = bb[r]
        pl.append(dict(ref=r, side=side[r], cx=(b[0] + b[2]) / 2, cy=(b[1] + b[3]) / 2, w=b[2] - b[0], h=b[3] - b[1], rot=0))
    blocks = [dict(name='U1 0805 bulk caps', side='TOP', x0=52.25, y0=5.2, x1=57.35, y1=18.1, contents='C93-C146'),
              dict(name='PMIC block', side='BOTTOM', x0=2.0, y0=3.0, x1=16.0, y1=20.0, contents='U8, L1-L3, caps')]
    return dict(placements=pl, blocks=blocks)


def check(plan):
    out = []
    pl = plan['placements']
    for p in pl:
        x0, y0, x1, y1 = p['cx'] - p['w'] / 2, p['cy'] - p['h'] / 2, p['cx'] + p['w'] / 2, p['cy'] + p['h'] / 2
        p['box'] = (x0, y0, x1, y1)
        if x0 < -0.6 or y0 < -0.6 or x1 > W + 0.6 or y1 > H + 0.6:
            out.append('%s outside the board %s' % (p['ref'], tuple(round(v, 2) for v in p['box'])))
        inside_gap = x0 >= GAP[0] - 0.3 and x1 <= GAP[1] + 0.3
        if (y0 < 2.4 or y1 > 23.0) and not inside_gap:
            out.append('%s in the header keep-out %s' % (p['ref'], tuple(round(v, 2) for v in p['box'])))
    for i, a in enumerate(pl):
        for b in pl[i + 1:]:
            th = a['ref'].startswith('JP') or b['ref'].startswith('JP')
            if a['side'] != b['side'] and not th:
                continue
            A, B = a['box'], b['box']
            dx = max(A[0] - B[2], B[0] - A[2]); dy = max(A[1] - B[3], B[1] - A[3])
            g = max(dx, dy) if (dx < 0 and dy < 0) else ((max(dx, 0) ** 2 + max(dy, 0) ** 2) ** 0.5)
            if g < 0.4 and not (a['ref'][:2] == 'JP' and b['ref'][:2] == 'JP'):
                out.append('%s / %s (%s) gap %.2f mm' % (a['ref'], b['ref'], a['side'] if not th else 'through-hole', g))
    return out


def panel(ax, plan, side, title):
    ax.add_patch(FancyBboxPatch((0, 0), W, H, boxstyle='round,pad=0,rounding_size=1.0', fc='#173d22', ec='black', lw=1.2))
    for y in (1.27, 24.13):
        for k in range(20):
            x = 1.27 + 2.54 * k
            if GAP[0] + 0.1 < x < GAP[1] - 0.1:
                continue
            ax.add_patch(plt.Circle((x, y), 0.85, fc='#c9a227', ec='none', alpha=0.85))
            ax.add_patch(plt.Circle((x, y), 0.45, fc='black', ec='none'))
    ax.text(2.5, 3.2, 'XADC pins 39/40', color='#ffd54f', fontsize=6.5, ha='left', va='bottom')
    for b in plan.get('blocks', []):
        if b['side'] != side:
            continue
        ax.add_patch(Rectangle((b['x0'], b['y0']), b['x1'] - b['x0'], b['y1'] - b['y0'], fc='none', ec='#ffcc80', lw=1.0,
                               ls='--', hatch='///', alpha=0.55))
        if b['x1'] - b['x0'] >= 5 and b['y1'] - b['y0'] >= 3:
            ax.text(b['x0'] + 0.3, b['y1'] - 0.3, b.get('short', b['name'].split(' (')[0]), color='#ffcc80', fontsize=5.5,
                    ha='left', va='top', wrap=True)
    for p in plan['placements']:
        on = p['side'] == side or p['ref'].startswith('JP')
        x0, y0, x1, y1 = p['box']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=colour(p['ref']) if on else 'none',
                               ec='white' if on else '#9e9e9e', lw=0.8 if on else 0.5, ls='-' if on else ':',
                               alpha=0.95 if on else 0.6))
        if on:
            fs = 8 if (x1 - x0) * (y1 - y0) > 40 else 6.5 if (x1 - x0) * (y1 - y0) > 6 else 5
            rot = 90 if (y1 - y0) > (x1 - x0) * 1.6 and (x1 - x0) < 4 else 0
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, p['ref'], color='white', fontsize=fs, ha='center', va='center',
                    rotation=rot, fontweight='bold')
    ax.set_xlim(-1.5, W + 1.5)
    ax.set_ylim(-1.5, H + 1.5)
    ax.set_aspect('equal')
    ax.set_xticks(range(0, 61, 10))
    ax.set_yticks(range(0, 26, 5))
    ax.tick_params(labelsize=6)
    ax.set_title(title, fontsize=9, loc='left')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', nargs='?')
    ap.add_argument('out')
    ap.add_argument('--title', default='Floorplan sketch')
    ap.add_argument('--current', action='store_true')
    ap.add_argument('--compare', action='store_true', help='today (left) next to PLAN (right)')
    a = ap.parse_args()
    plan = current_plan() if a.current else json.load(open(a.plan))
    plan.setdefault('placements', [])
    problems = check(plan)
    if a.compare:
        cur = current_plan()
        check(cur)
        fig, axs = plt.subplots(2, 2, figsize=(19, 9.2))
        panel(axs[0][0], cur, 'TOP', 'TODAY (Rev 4) - TOP')
        panel(axs[1][0], cur, 'BOTTOM', 'TODAY (Rev 4) - BOTTOM (x-ray from the top)')
        panel(axs[0][1], plan, 'TOP', a.title + ' - TOP')
        panel(axs[1][1], plan, 'BOTTOM', a.title + ' - BOTTOM (x-ray from the top)')
    else:
        fig, axs = plt.subplots(2, 1, figsize=(11, 9.6))
        panel(axs[0], plan, 'TOP', a.title + ' - TOP side')
        panel(axs[1], plan, 'BOTTOM', a.title + ' - BOTTOM side (seen from the top, x-ray; dotted = parts on the other side)')
    handles = [Rectangle((0, 0), 1, 1, fc=c, ec='white') for _, c, _ in CLASS]
    fig.legend(handles, [l for _, _, l in CLASS], loc='lower center', ncol=5, fontsize=7, frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(a.out, dpi=170)
    print(a.out)
    print('geometry check: %d issue(s)' % len(problems))
    for s in problems:
        print('  ' + s)


if __name__ == '__main__':
    main()
