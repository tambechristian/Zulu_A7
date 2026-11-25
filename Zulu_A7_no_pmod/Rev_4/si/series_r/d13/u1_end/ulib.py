"""u1_end designer library: the 13-R plan applied to the board extract, through this folder's COPY of
d10/fold/check.py (imported read-only; check.py only writes when main() runs).  Gives the post-plan object list,
a fast local rule probe used ONLY as a pre-filter (final legality always comes from running check.py), and plots.
"""
import json, math, os, sys, collections, copy
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.normpath(os.path.join(HERE, '..', '..'))
BASE_PLAN = os.path.join(SR, 'dq_series_r_plan.json')
_saved = sys.argv
sys.argv = [sys.argv[0], '--plan', BASE_PLAN, '--tag', '_ulib']
sys.path.insert(0, HERE)
import check as C  # noqa: E402
sys.argv = _saved

B = C.B
CU = C.CU
P13 = json.load(open(BASE_PLAN))


def base_objs():
    E = C.load_plan()
    pads, tracks, vias, newflags, errors = C.apply(E)
    assert not errors, errors
    objs = C.build_objs(pads, tracks, vias, set())
    return objs, pads, tracks, vias


def plot_window(objs, win, fname, title='', extra=None, layers=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, Polygon
    x0, x1, y0, y1 = win
    layers = layers or CU
    n = len(layers)
    cols = 3 if n > 2 else n
    rows = int(math.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(7 * cols, 7 * rows * (y1 - y0) / (x1 - x0) + 0.6))
    axes = list(getattr(axes, 'flat', [axes]))
    import matplotlib.colors as mc
    nets = sorted({o.net for o in objs if o.net})
    cmap = plt.get_cmap('tab20')
    ncol = {nm: cmap(i % 20) for i, nm in enumerate(nets)}
    for ax, L in zip(axes, layers):
        for o in objs:
            if o.layer != L:
                continue
            bb = C.bbox(o.shape)
            if bb[2] < x0 or bb[0] > x1 or bb[3] < y0 or bb[1] > y1:
                continue
            c = '#dddddd' if o.net in ('GND', 'VCC3V3') else ncol.get(o.net, 'k')
            if o.net and o.net.replace('SDRAM-', '') in ('D13', 'D14', 'D15'):
                c = 'red'
            S = o.shape
            if S[0] == 'R':
                ax.add_patch(Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], fc=c, ec='k', lw=0.3, alpha=0.7))
            else:
                if abs(S[1] - S[3]) < 1e-9 and abs(S[2] - S[4]) < 1e-9:
                    ax.add_patch(Circle((S[1], S[2]), S[5], fc=c, ec='k', lw=0.3, alpha=0.7))
                    if o.kind == 'via':
                        ax.add_patch(Circle((S[1], S[2]), o.hole / 2, fc='w', ec='none'))
                else:
                    ax.plot([S[1], S[3]], [S[2], S[4]], color=c, lw=S[5] * 2 * 72 * 7 / (x1 - x0) / 1.0, alpha=0.7,
                            solid_capstyle='round')
            if o.kind in ('pad', 'via') and o.net and x0 < o.xy[0] < x1 and y0 < o.xy[1] < y1:
                lbl = o.net[:10] if o.kind == 'via' else '%s\n%s' % (o.pad, o.net[:8])
                ax.text(o.xy[0], o.xy[1], lbl, fontsize=4.5, ha='center', va='center', zorder=9)
            elif o.kind == 'track' and o.net and (o.shape[1] + o.shape[3]) / 2 > x0 and (o.shape[1] + o.shape[3]) / 2 < x1:
                mx, my = (o.shape[1] + o.shape[3]) / 2, (o.shape[2] + o.shape[4]) / 2
                if y0 < my < y1:
                    ax.text(mx, my, o.net[:10], fontsize=4, ha='center', va='center', color='k', alpha=0.8, zorder=9)
        if extra:
            for e in extra:
                if e.get('layer') not in (None, L):
                    continue
                if e['type'] == 'rect':
                    ax.add_patch(Rectangle((e['x0'], e['y0']), e['x1'] - e['x0'], e['y1'] - e['y0'], fc='none', ec=e.get('c', 'b'), lw=1))
                if e['type'] == 'pt':
                    ax.plot([e['x']], [e['y']], marker=e.get('m', 'x'), color=e.get('c', 'b'), ms=4)
        if L in ('Top', 'Bottom'):
            side = 'TopOverlay' if L == 'Top' else 'BottomOverlay'
            for t in B['texts']:
                if t['layer'] == side and not t['hidden']:
                    S = C.text_box(t)
                    ax.add_patch(Rectangle((S[1] - S[3], S[2] - S[4]), 2 * S[3], 2 * S[4], fc='none', ec='m', lw=0.8, ls='--'))
                    ax.text(S[1], S[2], t['text'], color='m', fontsize=7)
            for t in B['tracks']:
                if t['layer'] == side:
                    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='m', lw=0.6)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title('%s %s' % (title, L), fontsize=9)
        ax.grid(True, lw=0.2); ax.tick_params(labelsize=6)
        import numpy as np
        ax.set_xticks(np.arange(math.floor(x0 * 2) / 2, x1, 0.5)); ax.set_yticks(np.arange(math.floor(y0 * 2) / 2, y1, 0.5))
    fig.tight_layout()
    fig.savefig(fname, dpi=130)
    plt.close(fig)


def objs_for_plan(P, tmpname='_tmp_plan.json'):
    pth = os.path.join(HERE, tmpname)
    json.dump(P, open(pth, 'w'))
    old = C.PLAN
    C.PLAN = pth
    try:
        E = C.load_plan()
        pads, tracks, vias, newflags, errors = C.apply(E)
    finally:
        C.PLAN = old
        os.remove(pth)
    return C.build_objs(pads, tracks, vias, newflags), errors
