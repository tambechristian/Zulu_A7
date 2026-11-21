"""d10_elsewhere: the 12-resistor plan (si/series_r/dq_series_r_plan.json, taken unchanged) + R129 on D10.

PLANNING ONLY.  Reads board_extract.json (PcbDoc md5 2a616c1c) and dq_series_r_plan.json; writes plan.json and
plan.png in this folder.  Prove with:  python dfm_check_d10.py --plan plan.json --tag d10

Where R129 goes and why (maze.py / wedge_route.py did the systematic search over D10's whole route, both sides of the
board, every via type on the board; see the summary at the end of this docstring):
  R129 sits on the BOTTOM side in the small free wedge between U3's east body end (TSOP-II, x <= 39.46 nominal,
  39.525 max) and the PROG# / VCC1V0 / VCC3V3 copper east of it, vertical (rot 270, like R121/R124/R125).
  U3 side (SDRAM-D10): unchanged from U3-45 through the L3 run to the through via (38.5,14.5), then a new 0.10 mm
    Bottom track from that via's Bottom land east to R129-1.  The via's Top land is left unconnected.
  U1 side (D10): R129-2 -> Bottom 0.10 mm diagonal -> L5>Bottom + L4>L5 stacked microvias (0.30/0.15) under U3's body
    -> L4 0.125 mm -> L3>L4 buried via (0.27/0.15) -> L3 0.125 mm down the free band SW of D13's diagonal ->
    Top>L2 + L2>L3 stacked microvias (0.30/0.15) in the free Top pocket under the D10 Top run -> Top 0.0762 mm stub
    -> the EXISTING Top run at (40.1,12.21) -> U1-K2.  The Top run upstream of (40.1,12.21) -- (38.5,14.5)-(39.9785,
    14.5)-(39.9785,12.21)-(40.1,12.21) -- is removed (it would otherwise short the two halves).
  Nothing of R127/R130/R131 or any other net changes.

THE CAVEAT (why d10_placed is reported false): R129's body (RC0201 max 0.63 x 0.33) ends at x = CX - 0.165, i.e.
  0.0575 mm from U3's NOMINAL body end and 0.0075 mm INSIDE U3's maximum-tolerance body outline.  ComponentClearance
  is 0.254 mm (Altium's batch DRC does not run it on this board, see docs/dq_series_resistors.md decision 9).  Every
  copper-legal R0201 site that D10 can reach from both sides overlaps a component body; with zero overlap allowed
  there are none (maze_result_comp0.json, maze_result_comp0254.json).
"""
import collections, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.abspath(os.path.join(HERE, '..', '..'))
B = json.load(open(os.path.join(SR, 'board_extract.json')))
BASE = json.load(open(os.path.join(SR, 'dq_series_r_plan.json')))
ORDER = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
EL = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'L5-VCC3V3': 'L5-VCC3V3'}

# ------------------------------------------------------------------ geometry (mm, board coords, y up)
CX, CY = float(os.environ.get('D10_CX', '39.6825')), float(os.environ.get('D10_CY', '14.625'))
P1 = (CX, round(CY + 0.3, 4))          # R129-1 = SDRAM-D10 (north)
P2 = (CX, round(CY - 0.3, 4))          # R129-2 = D10 (south)
V45 = (39.2825, 13.925)                # L4>L5 + L5>Bottom stacked microvias (U1 side)
V34 = (39.25, 13.52)                   # L3>L4 buried (>= 0.39 mm centre-centre from V45 and the SD-DAT2 buried via: HoleToHole 0.24)
V23 = (40.10, 12.075)                  # Top>L2 + L2>L3 stacked microvias
J = (40.10, 12.21)                     # junction on the existing Top run
SD_BOT = [(38.5, 14.5), (38.80, 14.5), (39.225, 14.925), P1]                      # Bottom 0.10, via -> R129-1
U1_BOT = [P2, (P2[0] - (P2[1] - V45[1]), V45[1]), V45]                            # Bottom 0.10, R129-2 -> V45
U1_L4 = [V45, V34]                                                                 # L4 0.125
U1_L3 = [V34, (39.25, 13.20), (39.975, 12.475), (39.975, 12.20), V23]              # L3 0.125 (45-degree band SW of D13 / SD-DAT2)
U1_TOP = [V23, J]                                                                  # Top 0.0762
TOP_KEEP = [J, (40.9, 12.21)]                                                      # replaces (39.9785,12.21)-(40.9,12.21)
W = {'Bottom Layer': 0.10, 'L4-SIG': 0.125, 'L3-SIG': 0.125, 'Top Layer': 0.0762}


def rnd(p):
    return (round(p[0], 4), round(p[1], 4))


def segs(pts, layer, net):
    pts = [rnd(p) for p in pts]
    out = []
    for a, b in zip(pts, pts[1:]):
        if a == b:
            continue
        out.append(dict(net=net, layer=layer, w=W[layer], x1=a[0], y1=a[1], x2=b[0], y2=b[1]))
    return out


def via(xy, frm, to, size, hole, net):
    return dict(net=net, x=round(xy[0], 4), y=round(xy[1], 4), size=size, hole=hole, **{'from': frm, 'to': to})


def d10_edit():
    """D10's edit in the plan file's own format"""
    rm, rmv, tr, vi, mv = [], [], [], [], []
    bt = [t for t in B['tracks'] if t['net'] == 'D10' and t['layer'] in ('Top', 'Bottom', 'L3-SIG')]
    bv = [v for v in B['vias'] if v['net'] == 'D10']
    # U3-side copper keeps its geometry and becomes SDRAM-D10 (remove + re-add, as plan_export.py writes renames)
    for t in bt:
        if t['layer'] in ('Bottom', 'L3-SIG'):
            rm.append(dict(net='D10', layer=EL[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
            tr.append(dict(net='SDRAM-D10', layer=EL[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], why='rename'))
    for v in bv:
        rmv.append(dict(net='D10', x=v['x'], y=v['y'], hole=v['hole'], span=[EL[v['span'][0]], EL[v['span'][-1]]], why='rename'))
        vi.append(dict(net='SDRAM-D10', x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': EL[v['span'][0]], 'to': EL[v['span'][-1]]}, why='rename'))
    # the Top run upstream of the junction goes
    gone = [((38.5, 14.5), (39.9785, 14.5)), ((39.9785, 14.5), (39.9785, 12.21)), ((39.9785, 12.21), (40.9, 12.21))]
    for a, b in gone:
        m = [t for t in bt if t['layer'] == 'Top' and {rnd((t['x1'], t['y1'])), rnd((t['x2'], t['y2']))} == {rnd(a), rnd(b)}]
        assert len(m) == 1, (a, b, m)
        t = m[0]
        rm.append(dict(net='D10', layer='Top Layer', w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    # new copper
    tr += segs(SD_BOT, 'Bottom Layer', 'SDRAM-D10')
    tr += segs(U1_BOT, 'Bottom Layer', 'D10') + segs(U1_L4, 'L4-SIG', 'D10') + segs(U1_L3, 'L3-SIG', 'D10')
    tr += segs(U1_TOP, 'Top Layer', 'D10') + segs(TOP_KEEP, 'Top Layer', 'D10')
    new_v = [via(V45, 'L4-SIG', 'L5-VCC3V3', 0.30, 0.15, 'D10'), via(V45, 'L5-VCC3V3', 'Bottom Layer', 0.30, 0.15, 'D10'),
             via(V34, 'L3-SIG', 'L4-SIG', 0.27, 0.15, 'D10'),
             via(V23, 'Top Layer', 'L2-GND', 0.30, 0.15, 'D10'), via(V23, 'L2-GND', 'L3-SIG', 0.30, 0.15, 'D10')]
    vi += new_v
    for v in new_v:
        mv.append(dict(v, type='buried 0.27/0.15' if v['size'] < 0.29 else 'microvia 0.30/0.15'))
    part = dict(ref='R129', net_bit=10, side='Bottom', footprint='R0201', comment='22', x=round(CX, 5), y=round(CY, 5), rot=270,
                pad1=dict(net='SDRAM-D10', x=P1[0], y=P1[1]), pad2=dict(net='D10', x=P2[0], y=P2[1]), designator_hidden=True)
    return rm, rmv, tr, vi, mv, part


def main():
    P = json.loads(json.dumps(BASE))
    rm, rmv, tr, vi, mv, part = d10_edit()
    P['source'] = dict(BASE['source'], plan=BASE['source']['plan'] + ' + d10_elsewhere R129 (D10) at the U3 body end',
                       generated_by='si/series_r/d10/d10_elsewhere/design.py', base_plan='si/series_r/dq_series_r_plan.json (unchanged)')
    P['remove'] += rm
    P['remove_vias'] += rmv
    P['tracks'] += tr
    P['vias'] += vi
    P['microvias'] += mv
    P['parts'].append(part)
    P['parts'].sort(key=lambda p: p['net_bit'])
    P['renet_pads'].append(dict(ref='U3', pad='45', net='SDRAM-D10'))
    P['net_class_add']['SDRAM_DATA'] = sorted(set(P['net_class_add']['SDRAM_DATA']) | {'SDRAM-D10'}, key=lambda s: int(s[7:]))
    P['renamed_existing'] = dict(tracks=sum(1 for t in P['tracks'] if t.get('why') == 'rename'),
                                 vias=sum(1 for v in P['vias'] if v.get('why') == 'rename'))
    P['d10'] = dict(ref='R129', site='Bottom, U3 east body end', centre=[CX, CY], rot=270,
                    u3_body_gap_nominal_mm=round(CX - 0.165 - 39.46, 4), u3_body_gap_max_mm=round(CX - 0.165 - 39.525, 4),
                    component_clearance_rule_mm=0.254, note='ComponentClearance exception needed (see design.py docstring)',
                    added_vias_u1_side=5, removed_top_run_mm=round(1.4785 + 2.29 + 0.1215, 3))
    json.dump(P, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)
    print('plan.json: remove %d tracks / %d vias, add %d tracks / %d vias (%d new), %d parts, renamed %s' % (
        len(P['remove']), len(P['remove_vias']), len(P['tracks']), len(P['vias']), len(P['microvias']), len(P['parts']), P['renamed_existing']))
    if '--no-png' not in sys.argv:
        draw(P)


def draw(P):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    from matplotlib.lines import Line2D
    col = {'Top Layer': '#c0392b', 'Bottom Layer': '#2471a3', 'L3-SIG': '#d68910', 'L4-SIG': '#7d3c98', 'L2-GND': '#1e8449', 'L5-VCC3V3': '#a04000'}
    LN = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}
    rmkey = {(r['layer'], round(r['x1'], 3), round(r['y1'], 3), round(r['x2'], 3), round(r['y2'], 3)) for r in P['remove'] if not r.get('why')}
    views = [('Whole plan: 13 resistors (R129 = D10, this design)', (27.0, 44.5, 3.0, 18.5), False),
             ('D10 detail: R129 on Bottom at U3\'s east body end; U1 side Bottom>L4>L3>Top', (37.9, 41.3, 11.6, 15.6), True)]
    fig, axes = plt.subplots(1, 2, figsize=(22, 11), gridspec_kw=dict(width_ratios=[1.35, 1]))
    for ax, (title, (x0, x1, y0, y1), det) in zip(axes, views):
        for p in B['pads']:
            if not (x0 - 1 < p['x'] < x1 + 1 and y0 - 1 < p['y'] < y1 + 1):
                continue
            w, h = p['w'], p['h']
            fc = '#bbbbbb' if p['layer'] == 'Bottom' else '#e8c0c0'
            ax.add_patch(Rectangle((p['x'] - w / 2, p['y'] - h / 2), w, h, fc=fc, ec='none', alpha=0.55, zorder=1))
            if det and p['ref'] in ('U3', 'U1') and p['net']:
                ax.text(p['x'], p['y'], '%s-%s' % (p['ref'], p['pad']), fontsize=5, ha='center', va='center', clip_on=True, zorder=6)
        for t in B['tracks']:
            if t['layer'] not in LN and t['layer'] not in col:
                continue
            L = LN.get(t['layer'], t['layer'])
            if not (min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0):
                continue
            k = (L, round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))
            if k in rmkey:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='k', lw=1.0, ls=':', zorder=3)
            else:
                ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[L], lw=max(0.5, t['w'] * (14 if det else 5)), alpha=0.16, zorder=2)
        for v in B['vias']:
            if x0 < v['x'] < x1 and y0 < v['y'] < y1:
                ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#999999', lw=0.4, zorder=2))
        # U3 body outline (nominal and max)
        for k, ls in (('nom', '-'), ('max', '--')):
            bd = B['u3']['body'][k]
            ax.add_patch(Rectangle((bd['x0'], bd['y0']), bd['x1'] - bd['x0'], bd['y1'] - bd['y0'], fc='none', ec='#555555', lw=0.8, ls=ls, zorder=2))
        for t in P['tracks']:
            if t.get('why'):
                continue
            ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color=col[t['layer']], lw=max(1.0, t['w'] * (16 if det else 6)), zorder=4, solid_capstyle='round',
                    alpha=1.0 if 'D10' in t['net'] else 0.55)
        for v in P['vias']:
            if v.get('why'):
                continue
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='none', ec='#000000', lw=1.2 if 'D10' in v['net'] else 0.6, zorder=5))
        for pr in P['parts']:
            for pd in (pr['pad1'], pr['pad2']):
                top = pr['side'] == 'Top'
                ax.add_patch(Rectangle((pd['x'] - 0.15, pd['y'] - 0.15), 0.3, 0.3, fc='none' if top else ('#f1c40f' if pr['ref'] != 'R129' else '#2ecc71'),
                                       ec='#b7950b' if top else 'k', lw=1.2 if top else 0.6, hatch='///' if top else None, zorder=5))
            if x0 < pr['x'] < x1 and y0 < pr['y'] < y1:
                ax.text(pr['x'] + (0.25 if det else 0), pr['y'] + (0 if det else 0.3), '%s D%d (%s)' % (pr['ref'], pr['net_bit'], pr['side'][0]),
                        fontsize=8 if det else 6, ha='left' if det else 'center', zorder=7, fontweight='bold')
        if det:
            for txt, xy in (('V45 L4>L5>Bot', (39.2825, 13.925)), ('V34 L3>L4 buried', (39.2825, 13.6)), ('V23 Top>L2>L3', (40.1, 12.075)),
                            ('through via (38.5,14.5)\nnow SDRAM-D10', (38.5, 14.5)), ('Top run kept from here\n(upstream removed, dotted)', (40.1, 12.21))):
                ax.annotate(txt, xy, xytext=(xy[0] - 0.9 if xy[0] > 39 else xy[0] - 0.55, xy[1] + 0.35), fontsize=7,
                            arrowprops=dict(arrowstyle='->', lw=0.6), zorder=8)
            ax.text(39.47, 15.45, 'U3 body end: nominal (solid) 39.46,\nmax (dashed) 39.525', fontsize=7, ha='right')
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=10); ax.grid(alpha=0.2)
    h = [Line2D([], [], color=c, lw=2, label='new ' + k) for k, c in col.items() if k not in ('L2-GND', 'L5-VCC3V3')]
    h += [Line2D([], [], color='k', ls=':', label='removed (D10 Top run upstream of the junction, and others)'),
          Line2D([], [], marker='s', color='#f1c40f', ls='', label='R119-R131 pads (12-R plan, Bottom)'),
          Line2D([], [], marker='s', mfc='none', mec='#b7950b', color='#b7950b', ls='', label='R127/R130/R131 pads (Top side, hatched)'),
          Line2D([], [], marker='s', color='#2ecc71', ls='', label='R129 pads (D10)'),
          Line2D([], [], marker='o', mfc='none', color='k', ls='', label='new via / microvia')]
    axes[0].legend(handles=h, fontsize=7, loc='lower left')
    fig.suptitle('d10_elsewhere plan (PcbDoc md5 2a616c1c): 12-R plan unchanged + R129 (D10). Faint = existing copper; board coords mm, y up. '
                 'R129 needs a U3 ComponentClearance waiver.', fontsize=10, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(os.path.join(HERE, 'plan.png'), dpi=140)


if __name__ == '__main__':
    main()
