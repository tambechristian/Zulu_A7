# -*- coding: utf-8 -*-
"""How much room is left for GND stitching vias?  Legal 0.35 mm via sites, board vs plan.

    python tools/route_stitch.py                                  the whole board and the standard windows
    python tools/route_stitch.py <plan.json> [<plan2.json> ...]    the same, with those plans placed
    python tools/route_stitch.py --window x0 x1 y0 y1 [plans...]   one window of your own
        --inputs F     another route_inputs.json
        --step S       grid (default 0.10 mm; 0.05 for a fine count)
        --span A,B,..  count sites for this via span (layer names, outer to inner; default through)

A position counts when a 0.35 mm land keeps 0.09 mm from every pad, track and keep-out on every
layer, 0.44 mm centre to centre from every via, stays outside U1's land field, and sits 0.80 mm
inside the board edge (the 20 mil plane pullback, so the via actually reaches L2/L5).

Routing spends this resource silently: no rule, and none of the other gates, notices that a trunk
has taken the last stitching sites out of a band.  Grown from the script the manufacturing reviewer
wrote against the stage-1 candidates (2026-09-16), where it was what separated three plans that had
all passed every gate: 86.3 %, 77.5 % and 77.5 % of the board's sites kept.

SPANS (2026-09-29, HDI): --span counts sites for a microvia instead (e.g. Top,L2-GND for a GND
stitch that never leaves the top dielectric): land and pitch from tools/hdi.json, only the pads,
tracks and keep-outs on layers of the span, the land-field ban only where hdi bans it, the pitch to
a via only if the spans share a layer.  The default is the through count above.
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hdi

RI = os.path.join(HERE, 'route_inputs.json')
LAND, PITCH, C, EDGE = 0.35, 0.44, 0.09, 0.80        # the through via; per-span values from tools/hdi.json

WINDOWS = [('whole board', 0.0, 69.85, 0.0, 25.40),
           ('regulator block     x  0..17, y  2..17', 0.0, 17.0, 2.0, 17.0),
           ('south band          x 11..31, y  2.0..4.6', 11.0, 31.0, 2.0, 4.6),
           ('south band          x 31..58, y  2.0..4.6', 31.0, 58.0, 2.0, 4.6),
           ('Bottom channel      x 12..28, y  2.1..2.6', 12.0, 28.0, 2.1, 2.6),
           ('north Top band      x 12..28, y  4.0..7.0', 12.0, 28.0, 4.0, 7.0),
           ('LED / X3 channel    x  9..25, y  3.0..20.0', 9.0, 25.0, 3.0, 20.0),
           ('north band          x 18..40, y 18.2..23.2', 18.0, 40.0, 18.2, 23.2),
           ('U1 surround         x 39..56, y  5.0..23.0', 39.0, 56.0, 5.0, 23.0)]


def without_removals(inp, plans):
    """the board as the plans leave it: their 'remove' lists taken out first (2026-09-16 -- this used to
    count the copper a plan deletes as still blocking stitching sites)"""
    sys.path.insert(0, HERE)
    from route_emit import apply_removals
    for p in plans:
        if p.get('remove'):
            inp = apply_removals(inp, p)[0]
    return inp


def sites(inp, plans, x0, x1, y0, y1, step, span=hdi.THROUGH):
    H = hdi.load(inp)
    land = H.land(span)
    xs = np.arange(x0, x1 + 1e-9, step)
    ys = np.arange(y0, y1 + 1e-9, step)
    X, Y = np.meshgrid(xs, ys)
    ok = np.ones(X.shape, bool)
    ol, lf = inp['outline'], inp['land_field']
    if H.field_ban(span):
        ok &= ~((X >= lf['x0']) & (X <= lf['x1']) & (Y >= lf['y0']) & (Y <= lf['y1']))
    ok &= (X - ol['x0'] >= EDGE) & (ol['x1'] - X >= EDGE) & (Y - ol['y0'] >= EDGE) & (ol['y1'] - Y >= EDGE)
    for v in inp['vias'] + [w for p in plans for w in p.get('vias', [])]:
        need = H.pitch_between(span, hdi.span_of(v))
        if need is not None:
            ok &= (X - v['x']) ** 2 + (Y - v['y']) ** 2 >= need ** 2
    for k, L in (('top_pads', 'Top'), ('bottom_pads', 'Bottom'), ('th_pads', None)):
        if L is not None and L not in span:
            continue
        for p in inp[k]:
            dx = np.maximum(np.abs(X - p['x']) - p['sx'] / 2, 0)
            dy = np.maximum(np.abs(Y - p['y']) - p['sy'] / 2, 0)
            ok &= (dx * dx + dy * dy) >= (C + land / 2) ** 2
    for t in inp['tracks'] + [t for p in plans for t in p.get('tracks', [])]:
        if t['layer'] not in span:
            continue
        ax, ay, bx, by = t['x1'], t['y1'], t['x2'], t['y2']
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 == 0:
            d2 = (X - ax) ** 2 + (Y - ay) ** 2
        else:
            u = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
            d2 = (X - (ax + u * dx)) ** 2 + (Y - (ay + u * dy)) ** 2
        ok &= d2 >= (C + land / 2 + t['width'] / 2) ** 2
    for k in inp.get('keepouts', []):
        if k['layer'] not in span:
            continue
        cx, cy = (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2
        dx = np.maximum(np.abs(X - cx) - (k['x1'] - k['x0']) / 2, 0)
        dy = np.maximum(np.abs(Y - cy) - (k['y1'] - k['y0']) / 2, 0)
        ok &= (dx * dx + dy * dy) >= (C + land / 2) ** 2
    return int(ok.sum())


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    inp = json.load(io.open(opt('--inputs', RI), encoding='utf-8'))
    step = float(opt('--step', '0.10'))
    span = tuple(opt('--span', ','.join(hdi.THROUGH)).split(','))
    plans = [json.load(io.open(p, encoding='utf-8')) for p in a if p.endswith('.json') and p != opt('--inputs')]
    if '--window' in a:
        i = a.index('--window')
        wins = [('window %s %s %s %s' % tuple(a[i + 1:i + 5]),) + tuple(float(v) for v in a[i + 1:i + 5])]
    else:
        wins = WINDOWS
    if span != hdi.THROUGH:
        print('via span %s' % '/'.join(span))
    print('%-44s %9s %9s %7s' % ('window', 'board', 'with plan' if plans else '', 'kept'))
    after = without_removals(inp, plans)
    for name, x0, x1, y0, y1 in wins:
        n0 = sites(inp, [], x0, x1, y0, y1, step, span)
        if plans:
            n1 = sites(after, plans, x0, x1, y0, y1, step, span)
            print('%-44s %9d %9d %6.1f %%' % (name, n0, n1, 100.0 * n1 / n0 if n0 else 100.0))
        else:
            print('%-44s %9d' % (name, n0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
