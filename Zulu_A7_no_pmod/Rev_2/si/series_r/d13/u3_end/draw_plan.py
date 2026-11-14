import json, math, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
import engine as G, plot_layer
W = G.World()
d = json.load(open('joint/final_a_recs.json'))
recs = [d['d14'], d['d15']]
LC = {'Top Layer': 'tab:red', 'Bottom Layer': 'tab:blue', 'L3-SIG': 'tab:orange', 'L4-SIG': 'tab:purple', 'L2-GND': 'tab:green'}
panels = [('Top', (35.0, 41.3, 15.3, 19.2), 'Top: R133 (D14) + R134 (D15), SDRAM-D14 Top run through the U2 NE corridor, U2-47 GND re-tie'),
          ('L4-SIG', (35.0, 41.3, 15.3, 19.2), 'L4-SIG: D14 / D15 inner routes re-joined at the R133-2 / R134-2 columns'),
          ('Bottom', (35.0, 41.3, 15.3, 19.2), 'Bottom: unchanged copper; U3-51 / U3-53 stubs + first vias become SDRAM-D14 / SDRAM-D15')]
fig, axs = plt.subplots(3, 1, figsize=(15, 26))
for ax, (L, box, title) in zip(axs, panels):
    X0, X1, Y0, Y1 = box
    # faint context
    for t in W.tracks:
        if t is None or t['layer'] != L: continue
        ax.add_patch(Polygon(plot_layer.cap_poly(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), fc='0.75', alpha=.5, lw=0))
    for p in W.pads:
        lay = G.CU if p['layer'] == 'Multi' else [p['layer']]
        if L not in lay or not (X0 - 2 < p['x'] < X1 + 2 and Y0 - 2 < p['y'] < Y1 + 2): continue
        S = G.C.pad_shape(p, L)
        if S[0] == 'R':
            ax.add_patch(Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], fc='0.8', ec='0.5', lw=.4))
        else:
            ax.add_patch(Polygon(plot_layer.cap_poly(S[1], S[2], S[3], S[4], S[5]), fc='0.8', ec='0.5', lw=.4))
        if X0 < p['x'] < X1 and Y0 < p['y'] < Y1:
            ax.text(p['x'], p['y'], '%s-%s' % (p['ref'], p['pad']), fontsize=5, ha='center', va='center', color='0.3')
    for v in W.vias:
        if v is None or L not in v['span'] or not (X0 - 1 < v['x'] < X1 + 1 and Y0 - 1 < v['y'] < Y1 + 1): continue
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='0.5', lw=.5))
    for rec in recs:
        for t in rec['remove']:
            if G.LIN[t['layer']] != L or t.get('why') == 'rename': continue
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], 'k:', lw=1.2)
        for t in rec['tracks']:
            if G.LIN[t['layer']] != L: continue
            col = LC.get(t['layer'], 'k')
            if t['net'] == 'GND': col = 'tab:green'
            ax.add_patch(Polygon(plot_layer.cap_poly(t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2), fc=col, alpha=.85 if t.get('why') != 'rename' else .35, lw=0))
            if X0 < (t['x1'] + t['x2']) / 2 < X1 and t.get('why') != 'rename':
                ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2 + 0.05, t['net'], fontsize=6, color=col)
        for v in rec['vias']:
            sp = G.span(G.LIN[v['from']], G.LIN[v['to']])
            if L not in sp: continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='k' if v.get('why') == 'rename' else 'm', lw=1.4))
        for p in rec['parts']:
            if p['side'] != L: continue
            for k in ('1', '2'):
                pd = p['pad' + k]
                ax.add_patch(Rectangle((pd['x'] - .15, pd['y'] - .15), .3, .3, fc='gold', ec='k', lw=.6))
                ax.text(pd['x'], pd['y'], k, fontsize=6, ha='center', va='center')
            ax.text(p['x'], p['y'] + 0.22, '%s D%d' % (p['ref'], p['net_bit']), fontsize=8, ha='center', weight='bold')
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_title(title, fontsize=10)
fig.suptitle('d13/u3_end joint plan (13-R plan + R133 D14 + R134 D15); faint = copper after the 13-R plan; dotted = removed; magenta = new vias; black ring = renamed via', fontsize=10)
plt.tight_layout(rect=(0, 0, 1, 0.98)); plt.savefig('plan.png', dpi=110)
