"""Redraw si/series_r/dq_series_r_plan.png for the 15-resistor fallback plan (user decision 2026-11-13: D13 gets no
resistor, R132 unused).  Copy of d13/fold/draw_plan.py with: titles for 15 R, no U1 designator box (plan15 has no
designator move, so its legend entry is dropped), D13 marked "no R (user decision)" at U3-50, and the md5 check.
Reads ../../dq_series_r_plan.json (must be md5 187b8703, byte copy of d13/fallback15/plan15.json) and the board
extract through ../../dfm_check.py (read-only).

    PYTHONDONTWRITEBYTECODE=1 python draw_plan15.py
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
             ('North / U1 side: R127, R129-R131 (Top), R128, R133, R134 (Bottom); D13 has no R', (34.8, 48.6, 11.6, 18.6))]
    fig, axes = plt.subplots(2, 1, figsize=(13, 13.5))
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
                ax.text(pr['x'], pr['y'] - 0.32 if pr['side'] == 'Bottom' and (pr['y'] < 9 or pr['ref'] == 'R134') else pr['y'] + 0.22,
                        '%s D%d (%s)' % (pr['ref'], pr['net_bit'], pr['side'][0]), fontsize=7, ha='center', zorder=7,
                        fontweight='bold')
        for m in P.get('designator_moves', []):
            w, h = len(m['text']) * m['height'] * 0.8, m['height']
            for (tx, ty, ls, lab) in ((m['x_from'], m['y_from'], ':', 'old'), (m['x'], m['y'], '-', 'new')):
                if x0 < tx < x1 and y0 < ty < y1:
                    ax.add_patch(Rectangle((tx, ty), w, h, fc='none', ec='#117a65', lw=1.2, ls=ls, zorder=6))
                    ax.text(tx + w / 2, ty + h / 2, '%s %s' % (m['text'], lab), fontsize=6, ha='center', va='center', color='#117a65', zorder=7)
        for p in D.B['pads']:
            if p['ref'] == 'U3' and str(p['pad']) == '50' and x0 < p['x'] < x1 and y0 < p['y'] < y1:
                assert p['net'] == 'D13', p['net']
                ax.annotate('D13: no R (user decision)' + chr(10) + 'U3-50 stays on D13, copper unchanged',
                            xy=(p['x'], p['y']),
                            xytext=(p['x'] - 0.5, p['y'] - 2.7), fontsize=8, ha='left', color='black',
                            fontweight='bold', zorder=8, arrowprops=dict(arrowstyle='->', color='black', lw=1.0, ls='--'),
                            bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='black', lw=0.8))
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
    fig.suptitle('DQ series resistors, implementation plan: 15 R (13-R plan + R133 D14 / R134 D15 Bottom); D13 no R (user decision 2026-11-13), R132 unused; faint = existing copper; mm, y up',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)



if __name__ == '__main__':
    md5 = hashlib.md5(open(PLAN, 'rb').read()).hexdigest()
    assert md5 == '187b8703833e9d785fd62c91d044bdf8', md5
    P = json.load(open(PLAN))
    draw(P, D.board_records()[1], D.board_records()[2])
    print('wrote', OUT_PNG, 'from plan md5', md5)
