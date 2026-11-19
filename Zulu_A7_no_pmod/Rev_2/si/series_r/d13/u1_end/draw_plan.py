"""Redraw si/series_r/dq_series_r_plan.png for the folded 13-resistor plan.  draw() is plan_export.py's own
function, copied with asserted string replacements (two titles and the output path); nothing else changes.
Reads ../../dq_series_r_plan.json (must be md5 f2949630, the d10 relocate plan) and the board extract through
../../dfm_check.py (imported read-only).

    PYTHONDONTWRITEBYTECODE=1 python draw_plan.py
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, SR)
sys.argv = [sys.argv[0]]
import dfm_check as D  # noqa: E402

EMIT_LAYER = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG',
              'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}
PLAN = os.path.join(SR, 'dq_series_r_plan.json')
OUT_PNG = os.path.join(SR, 'dq_series_r_plan.png')


def draw(P, base_t, base_v):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    col = {'Top Layer': '#c0392b', 'Bottom Layer': '#2471a3', 'L3-SIG': '#d68910', 'L4-SIG': '#7d3c98',
           'L2-GND': '#1e8449', 'L5-VCC3V3': '#a04000'}
    views = [('South row (Bottom-side view, not mirrored): R119-R126', (27.6, 39.6, 3.2, 9.6)),
             ('North / U1 side: R127, R129, R130, R131 (Top), R128 (Bottom)', (37.6, 44.0, 11.6, 17.2))]
    fig, axes = plt.subplots(2, 1, figsize=(12, 13))
    rmkey = {(r['layer'], round(r['x1'], 3), round(r['y1'], 3), round(r['x2'], 3), round(r['y2'], 3)) for r in P['remove']}
    for ax, (title, (x0, x1, y0, y1)) in zip(axes, views):
        for p in D.B['pads']:
            if not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1) or p['layer'] not in ('Top', 'Bottom', 'Multi'):
                continue
            ax.add_patch(Rectangle((p['x'] - p['size_x'] / 2 if p['rot'] in (0, 180) else p['x'] - p['size_y'] / 2,
                                    p['y'] - p['size_y'] / 2 if p['rot'] in (0, 180) else p['y'] - p['size_x'] / 2),
                                   p['size_x'] if p['rot'] in (0, 180) else p['size_y'],
                                   p['size_y'] if p['rot'] in (0, 180) else p['size_x'],
                                   fc='#bbbbbb' if p['layer'] == 'Bottom' else '#e8c0c0', ec='none', alpha=0.6, zorder=1))
            if p['ref'] == 'U3' and p['net']:
                ax.text(p['x'], p['y'], '%s\n%s' % (p['pad'], p['net'][:7]), fontsize=5, ha='center', va='center', zorder=6, clip_on=True)
        for t in base_t:
            if t['layer'] not in D.CU or not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0):
                continue
            k = (EMIT_LAYER[t['layer']], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
            if k in rmkey:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=0.8, ls=':', zorder=3)
            else:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[EMIT_LAYER[t['layer']]], lw=max(0.6, t['w'] * 12), alpha=0.18, zorder=2)
        for v in base_v:
            if x0 < v['x'] < x1 and y0 < v['y'] < y1:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#888888', lw=0.5, zorder=2))
        for t in P['tracks']:
            if t.get('why') == 'rename':
                continue
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[t['layer']], lw=max(1.0, t['w'] * 14), zorder=4,
                    solid_capstyle='round')
        for v in P['vias']:
            if v.get('why') == 'rename':
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#000000', lw=1.2, zorder=5))
        for pr in P['parts']:
            for pd in (pr['pad1'], pr['pad2']):
                ax.add_patch(Rectangle((pd['x'] - 0.15, pd['y'] - 0.15), 0.3, 0.3, fc='#f1c40f', ec='k', lw=0.6, zorder=5))
            if x0 < pr['x'] < x1 and y0 < pr['y'] < y1:
                ax.text(pr['x'], pr['y'] - 0.32 if pr['side'] == 'Bottom' and pr['y'] < 9 else pr['y'] + 0.22,
                        '%s D%d (%s)' % (pr['ref'], pr['net_bit'], pr['side'][0]), fontsize=7, ha='center', zorder=7,
                        fontweight='bold')
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect('equal')
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.2)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=c, lw=2, label='new ' + k) for k, c in col.items()]
    h += [Line2D([], [], color='k', ls=':', label='removed'), Line2D([], [], marker='s', color='#f1c40f', ls='', label='new R pad'),
          Line2D([], [], marker='o', mfc='none', color='k', ls='', label='new via / microvia')]
    axes[0].legend(handles=h, fontsize=7, loc='upper left', ncol=3)
    fig.suptitle('DQ series resistors, implementation plan: 13 R (12-R plan + DFM fixes F1/F2 + D10 relocate: R129 new, R130 moved); faint = existing copper; mm, y up',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)



if __name__ == '__main__':
    md5 = hashlib.md5(open(PLAN, 'rb').read()).hexdigest()
    assert md5.startswith('f2949630'), md5
    P = json.load(open(PLAN))
    draw(P, D.board_records()[1], D.board_records()[2])
    print('wrote', OUT_PNG, 'from plan md5', md5)
