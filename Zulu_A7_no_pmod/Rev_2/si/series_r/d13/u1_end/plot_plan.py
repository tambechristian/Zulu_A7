"""plan.png: the u1_end joint plan (13-R plan + R133 D14 + R134 D15), Bottom-side view not mirrored.
Panel 1: overview of D13/D14/D15 routes; panel 2: zoom on R133/R134 (Bottom, L4, L5 shown); panel 3: why D13 has no site."""
import json, os, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import ulib
C = ulib.C
HERE = ulib.HERE
P = json.load(open(os.path.join(HERE, 'plan.json')))
objs, err = ulib.objs_for_plan(P)
assert not err
COL = {'Top': '#c0392b', 'L3-SIG': '#d68910', 'L4-SIG': '#7d3c98', 'Bottom': '#2471a3', 'L2-GND': '#1e8449', 'L5-VCC3V3': '#a04000'}
FAM = ('D13', 'D14', 'D15', 'SDRAM-D13', 'SDRAM-D14', 'SDRAM-D15')
rm = {(t['layer'].replace(' Layer', ''), round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3)) for t in P['remove'] if t['net'] in FAM and t.get('why') != 'rename'}


def draw(ax, win, layers, title, fam_only=False):
    x0, x1, y0, y1 = win
    for o in objs:
        if o.layer not in layers:
            continue
        bb = C.bbox(o.shape)
        if bb[2] < x0 or bb[0] > x1 or bb[3] < y0 or bb[1] > y1:
            continue
        f = o.net in FAM
        if fam_only and not f:
            continue
        c = COL[o.layer] if f else '#bbbbbb'
        a = 0.85 if f else 0.35
        S = o.shape
        if S[0] == 'R':
            ax.add_patch(Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], fc=c, ec='k' if f else 'none', lw=0.4, alpha=a, zorder=3 if f else 1))
        elif abs(S[1] - S[3]) < 1e-9 and abs(S[2] - S[4]) < 1e-9:
            ax.add_patch(Circle((S[1], S[2]), S[5], fc=c, ec='k' if f else 'none', lw=0.3, alpha=a, zorder=3 if f else 1))
        else:
            lw = max(0.5, 2 * S[5] * 72 * ax.get_window_extent().width / 72 / (x1 - x0) / 1.0)
            ax.plot([S[1], S[3]], [S[2], S[4]], color=c, lw=lw, alpha=a, solid_capstyle='round', zorder=3 if f else 1)
    for t in ulib.B['tracks']:
        k = (t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
        if k in rm and t['layer'] in layers:
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=0.8, ls=':', zorder=4)
    for pr in P['parts']:
        if not (x0 < pr['x'] < x1 and y0 < pr['y'] < y1) or pr['side'] not in layers:
            continue
        ax.annotate('%s %s\n%s' % (pr['ref'], 'D%d' % pr['net_bit'], pr['side']), (pr['x'], pr['y']), xytext=(0, 14), textcoords='offset points',
                    ha='center', fontsize=7, color='k', zorder=9, arrowprops=dict(arrowstyle='-', lw=0.5))
    for ref, box, c in (('U1 body', (41.4, 6.9, 51.4, 16.9), 'r'), ('U3 body (max)', (17.1749, 6.705, 39.525, 16.995), 'b')):
        ax.add_patch(Rectangle((box[0], box[1]), box[2] - box[0], box[3] - box[1], fc='none', ec=c, lw=0.8, ls='--', zorder=5))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=9)
    ax.grid(True, lw=0.2); ax.tick_params(labelsize=7)


fig = plt.figure(figsize=(15, 13))
ax1 = fig.add_subplot(3, 1, 1)
draw(ax1, (34.5, 50.5, 11.5, 18.6), C.CU, 'D13/D14/D15 copper after the plan (coloured by layer; grey = other nets; dotted = removed). '
     'R133 (D14) and R134 (D15) on Bottom at the U1 end; D13 unchanged', fam_only=False)
ax2 = fig.add_subplot(3, 2, 3)
draw(ax2, (44.6, 49.6, 15.9, 18.3), ('Bottom', 'L5-VCC3V3'), 'Zoom, Bottom + L5: R133 at (45.95,17.15), R134 at (47.20,16.80);\n'
     'pad 1 = SDRAM-Dn with L4>L5>Bottom VIPPO column, pad 2 = Dn to the kept through via V2')
ax3 = fig.add_subplot(3, 2, 4)
draw(ax3, (44.6, 49.6, 15.9, 18.3), ('L4-SIG',), 'Zoom, L4: the D14/D15 runs now end in the pad-1 columns\n(45.65,17.15) and (46.90,16.80); V2 keeps only its Top/Bottom role')
ax4 = fig.add_subplot(3, 2, 5)
draw(ax4, (39.6, 42.2, 11.9, 13.7), ('Top',), 'D13 U1 end, Top: no 0201 fits between D11 x40.145 and the\nAIN16_N via (41.30,12.665) (0.942 mm < 1.08) or between D11 y12.38 and AIN16_P y13.09 (0.634 < 1.08)')
ax5 = fig.add_subplot(3, 2, 6)
draw(ax5, (39.6, 42.2, 11.9, 13.7), ('Bottom',), 'D13 U1 end, Bottom: V2 (40.60,12.75) is boxed in by AIN16_P/AIN16_N tracks,\nthe GND via (40.9,13.4) and R128; the L3 run below x 39.84 is under U3')
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'plan.png'), dpi=120)
print('ok')
