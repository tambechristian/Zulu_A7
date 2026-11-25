"""Component-body collision gate (2026-11-14).

The board carries no 3D bodies and the batch DRC never ran its Component Clearance rule, so 'DRC 0' said nothing about
parts sitting on each other (the 2026-11-14 audit found U4 on U1, R34 on U7, X2's 11-20 housing on U10 and X4's housing
over U2's south pins).  This gate models every body from datasheet sizes and checks a router model (route_model.py
output, or a judge result.json after a plan):

    python tools/body_check.py <model.json> [--refs U4,R34,...] [--gap 0.10]

Body model
  * a box of the datasheet body size (BODY, nominal and maximum) centred on the part's pad extent on its own side,
    turned with the part (the pad extent's long axis decides nothing: the rotation in comps.json does);
  * X1, X3, X4: the footprint's own Mechanical 3/4 body outline, kept as an offset from the pad extent (comps.json
    'mech'), so a moved connector keeps its body;
  * X2: four 2.54 mm 1x10 housings on the BOTTOM side around each pin row (the assembly notes put them there).
Checks, per side, for every pair of parts (or every pair involving --refs):
  body_body       nominal bodies overlap, or come closer than --gap
  body_body_max   maximum-tolerance bodies overlap
  body_pad        a body (nominal) lies over, or within --gap of, another part's pad on the same side
Pads of a through-hole part count on both sides.  Exit status 1 if anything is reported.
"""
import argparse
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS = os.path.join(HERE, 'route', 'illustration', 'comps.json')   # regenerate: route/illustration/comps_from_board.py
# pattern: nominal length along the footprint's x, width along its y, then the maximum-tolerance pair (mm)
BODY = {
    'R0201': (0.60, 0.30, 0.63, 0.33), 'C0201': (0.60, 0.30, 0.63, 0.33),
    'R0402': (1.00, 0.50, 1.05, 0.55), 'C0402': (1.00, 0.50, 1.05, 0.55),
    'C0603': (1.60, 0.80, 1.70, 0.90), 'IND0603': (1.60, 0.80, 1.75, 0.95), 'LED0603': (1.60, 0.80, 1.70, 0.90),
    'C0805': (2.00, 1.25, 2.10, 1.45), 'IND2520': (2.50, 2.00, 2.70, 2.20),
    'SOT23-5': (2.90, 1.60, 3.05, 1.75), 'QFN28-UFD-4X5': (4.00, 5.00, 4.10, 5.10),
    'SPI-8_SOIC_150': (3.90, 4.90, 4.00, 5.00), 'MSOP-8_3X3_P0.65': (3.00, 3.00, 3.10, 3.10), 'SOIC-8_208MIL': (5.28, 5.28, 5.38, 5.38),
    'TSOPII-54': (10.16, 22.22, 10.26, 22.42), 'FT2232HL-LQFP64': (10.0, 10.0, 10.2, 10.2),
    'FT2232HQ-QFN64': (9.0, 9.0, 9.1, 9.1),
    'XC7A35T-CPG236': (10.0, 10.0, 10.1, 10.1), '742C043': (1.60, 1.60, 1.75, 1.75), '742C083': (3.20, 1.60, 3.40, 1.75),
    '742C163': (6.40, 1.60, 6.55, 1.75), '32X25': (2.50, 3.20, 2.60, 3.30), 'EVERLIGHT-19-337': (1.60, 1.60, 1.70, 1.70),
    'PTS810': (4.20, 3.20, 4.30, 3.30),
}
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def ext(bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def gap(a, b):
    """Edge gap between two boxes; negative = overlap depth (the smaller of the two axes)."""
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def load(model_path, comps_path=COMPS):
    return build(json.load(open(model_path)), json.load(open(comps_path)))


def build(M, D):
    """M: a router model (only 'pads' is used); D: comps.json contents (rotations may be edited by the caller)."""
    C = {c['ref']: c for c in D['comps']}
    pads = collections.defaultdict(list)
    for p in M['pads']:
        if p.get('ref'):
            pads[p['ref']].append(p)

    def side(ref):
        return 'Top' if C[ref]['layer'] == 'TOP' else 'Bottom'

    def on(p, s):
        L = p['layers'] or STACK
        return ('Top Layer' if s == 'Top' else 'Bottom Layer') in L

    def pbox(p):
        return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
    parts = {s: {} for s in ('Top', 'Bottom')}
    for ref, ps in pads.items():
        if ref not in C:
            continue
        own = side(ref)
        for s in ('Top', 'Bottom'):
            pb = [(pbox(p), p) for p in ps if on(p, s)]
            body, bodyt = [], []
            if s == own and pb:
                e = ext([b for b, _ in pb])
                pat = C[ref]['pattern']
                if ref in D['mech']:
                    o = D['mech'][ref]['off']
                    body = bodyt = [(e[0] + o[0], e[1] + o[1], e[2] + o[2], e[3] + o[3])]
                    # extra boxes (Rev 4, 3M X3 lock-pin housing): (x0, y0, x1, y1) from the pad extent's min corner
                    for x0, y0, x1, y1 in D['mech'][ref].get('extra', []):
                        body = bodyt = body + [(e[0] + x0, e[1] + y0, e[0] + x1, e[1] + y1)]
                elif pat in BODY:
                    L, W, Lt, Wt = BODY[pat]
                    if round(C[ref]['rot']) % 180 == 90:
                        L, W, Lt, Wt = W, L, Wt, Lt
                    cx, cy = (e[0] + e[2]) / 2, (e[1] + e[3]) / 2
                    body = [(cx - L / 2, cy - W / 2, cx + L / 2, cy + W / 2)]
                    bodyt = [(cx - Lt / 2, cy - Wt / 2, cx + Lt / 2, cy + Wt / 2)]
            if pb or body:
                parts[s][ref] = {'pads': pb, 'body': body, 'bodyt': bodyt}
    # X2: Bottom-side 1x10 housings, one per pin row
    if 'X2' in pads:
        rows = collections.defaultdict(list)
        for p in pads['X2']:
            rows[(int(p['pad']) - 1) // 10].append(p)
        for k, r in sorted(rows.items()):
            xs, ys = [p['x'] for p in r], [p['y'] for p in r]
            if max(xs) - min(xs) > max(ys) - min(ys):
                h = (min(xs) - 1.27, min(ys) - 1.27, max(xs) + 1.27, max(ys) + 1.27)
            else:
                h = (min(xs) - 1.27, min(ys) - 1.27, max(xs) + 1.27, max(ys) + 1.27)
            parts['Bottom']['X2[%d-%d]' % (k * 10 + 1, k * 10 + 10)] = {'pads': [], 'body': [h], 'bodyt': [h]}
    return parts


def check(parts, refs=None, min_gap=0.10):
    out = []
    for s, P in parts.items():
        names = sorted(P)
        if refs:
            pairs = [(a, b) for a in names if a.split('[')[0] in refs for b in names if b != a and
                     (b.split('[')[0] not in refs or b > a)]
        else:
            pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
        for a, b in pairs:
            if True:
                ba, bb = a.split('[')[0], b.split('[')[0]
                if ba == bb:
                    continue
                A, B = P[a], P[b]
                for x in A['body']:
                    for y in B['body']:
                        g = gap(x, y)
                        if g < min_gap:
                            out.append((s, 'body_body', a, b, '', round(g, 3)))
                for x in A['bodyt']:
                    for y in B['bodyt']:
                        g = gap(x, y)
                        if g < 0:
                            out.append((s, 'body_body_max', a, b, '', round(g, 3)))
                for X, Y, xn, yn in ((A, B, a, b), (B, A, b, a)):
                    for x in X['body']:
                        for pb, p in Y['pads']:
                            g = gap(x, pb)
                            if g < min_gap:
                                out.append((s, 'body_pad', xn, yn, p['pad'], round(g, 3)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('model')
    ap.add_argument('--refs', default='')
    ap.add_argument('--gap', type=float, default=0.10)
    ap.add_argument('--comps', default=COMPS)
    a = ap.parse_args()
    refs = set(r for r in a.refs.split(',') if r) or None
    res = check(load(a.model, a.comps), refs, a.gap)
    worst = {}
    for r in res:
        k = r[:4]
        if k not in worst or r[5] < worst[k][5]:
            worst[k] = r
    for r in sorted(worst.values(), key=lambda r: r[5]):
        print('%-6s %-13s %-10s %-10s %-5s %7.3f' % r)
    print('body_check: %d pair findings (gap < %.2f mm or max-tolerance overlap)' % (len(worst), a.gap))
    sys.exit(1 if worst else 0)


if __name__ == '__main__':
    main()
