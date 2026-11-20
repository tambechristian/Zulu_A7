"""Component-body collision check for the Asar A7 (2026-11-19), ported from Zulu_A7_no_pmod/Rev_2/tools/body_check.py.

Altium's batch DRC never ran Component Clearance on this board, so 'DRC 0' said nothing about parts sitting on each
other (the 2026-11-18 pictures showed BTN against X5 and U8 against C151). This check models every body from
datasheet sizes and checks a router model (tools/route_model.py output):

    python tools/body_check.py <model.json> [--comps comps.json] [--refs BTN,X5,...] [--gap 0.10]

Body model
  * a box of the datasheet body size (BODY, nominal and maximum) centred on the part's pad extent on its own side,
    turned with the part (the rotation in comps.json decides, not the pad extent);
  * X1, X3, X4, X5: the outline in tools/body_mech.json, kept as offsets from the part's pad extent so a moved
    connector keeps its body (X4's housing is three boxes: the housing and its two legs either side of the pad notch;
    'offs_max' there, when given, is the maximum-tolerance outline);
  * X2: the two Feather header housings (1x16, 1x12, 2.54 mm wide) on the BOTTOM side around each pin row -- the
    headers ship loose and go in from the bottom, Feather style; X2's four mounting holes have no body. Sullins draws
    the insulator .100 in wide with only the drawing's general tolerance (+-0.20, so up to 2.74); like the no-PMOD
    gate, the housing is checked at its nominal 2.54 for both nominal and maximum, and parts near it are expected to
    keep the 0.10 warning gap (at the 2.74 extreme a part 0.10 away would touch it by up to 0.01 mm).
Checks, per side, for every pair of parts (or every pair involving --refs):
  body_body       nominal bodies overlap, or come closer than --gap
  body_body_max   maximum-tolerance bodies overlap
  body_pad        a body (nominal) lies over, or within --gap of, another part's pad on the same side
  body_pad_max    a maximum-tolerance body lies over another part's pad where the nominal body clears it (the
                  release gate lists these as warnings; nominal overlaps fail)
Pads of a through-hole part count on both sides. Exit status 1 if anything is reported.
mech_mismatch(D) lists the connectors whose side, rotation or footprint no longer match tools/body_mech.json (their
outlines are fixed offsets, valid only as placed); the release gate fails on any.
"""
import argparse
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMPS = os.path.join(HERE, 'route', 'body_gate', 'comps.json')   # regenerate: tools/comps_from_board.py
# pattern: nominal length along the footprint's x, width along its y, then the maximum-tolerance pair (mm)
BODY = {
    'R0201': (0.60, 0.30, 0.63, 0.33), 'C0201': (0.60, 0.30, 0.63, 0.33),
    # maxima from the fitted parts' datasheets (tools/body_heights.json 'parts', 2026-11-19 review): C0402 up to
    # 1.15 x 0.65 (Taiyo Yuden C139), C0603 1.85 x 1.05 (Samsung CL10A226 C82/C84), C0805 2.20 (Murata GRM21BR),
    # SC189 (U7) D 2.95 nominal / 3.10 max, CTS 742C +-0.20
    'R0402': (1.00, 0.50, 1.05, 0.55), 'C0402': (1.00, 0.50, 1.15, 0.65),
    'C0603': (1.60, 0.80, 1.85, 1.05), 'IND0603': (1.60, 0.80, 1.75, 0.95), 'LED0603': (1.60, 0.80, 1.70, 0.90),
    'C0805': (2.00, 1.25, 2.20, 1.45), 'IND2520': (2.50, 2.00, 2.70, 2.20),
    'SOT23-5': (2.95, 1.60, 3.10, 1.75), 'QFN28-UFD-4X5': (4.00, 5.00, 4.10, 5.10),
    'XC7A35T-CPG236': (10.0, 10.0, 10.1, 10.1), '742C043': (1.60, 1.60, 1.80, 1.80), '742C083': (3.20, 1.60, 3.40, 1.80),
    '742C163': (6.40, 1.60, 6.60, 1.80), '32X25': (2.50, 3.20, 2.60, 3.30), 'EVERLIGHT-19-337': (1.60, 1.60, 1.70, 1.70),
    'PTS810': (4.20, 3.20, 4.30, 3.30),
    # Asar-only footprints, from the manufacturer drawings (sources in tools/body_heights.json 'parts', 2026-11-19):
    # FT2232HQ 9.00 BSC (older drawing +-0.075), AS4C32M16SB 8.00 +-0.10, W25Q128JVPIQ D 6.00 x E 5.00 +-0.10 (pin rows
    # along E, i.e. along y at rot 0), 93LC46 MNY D 2.00 (pin rows) x E 3.00, profile 0.15
    'QFN-64-9X9-P0.5-EP4.35': (9.0, 9.0, 9.075, 9.075), 'FBGA-54-8X8-P0.8': (8.0, 8.0, 8.1, 8.1),
    'WSON-8-6X5-P1.27': (6.0, 5.0, 6.1, 5.1), 'TDFN-8-2X3-P0.5': (2.0, 3.0, 2.15, 3.15),
}
SPECIAL = {'FEATHER-28'}      # X2: build() makes its two bottom-side housings itself
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
                    offs = D['mech'][ref].get('offs') or [D['mech'][ref]['off']]
                    offt = D['mech'][ref].get('offs_max') or offs
                    body = [(e[0] + o[0], e[1] + o[1], e[2] + o[2], e[3] + o[3]) for o in offs]
                    bodyt = [(e[0] + o[0], e[1] + o[1], e[2] + o[2], e[3] + o[3]) for o in offt]
                elif pat in BODY:
                    L, W, Lt, Wt = BODY[pat]
                    if round(C[ref]['rot']) % 180 == 90:
                        L, W, Lt, Wt = W, L, Wt, Lt
                    cx, cy = (e[0] + e[2]) / 2, (e[1] + e[3]) / 2
                    body = [(cx - L / 2, cy - W / 2, cx + L / 2, cy + W / 2)]
                    bodyt = [(cx - Lt / 2, cy - Wt / 2, cx + Lt / 2, cy + Wt / 2)]
            if pb or body:
                parts[s][ref] = {'pads': pb, 'body': body, 'bodyt': bodyt}
    # X2: one bottom-side housing per pin row (the named pins; the mounting holes have none)
    if 'X2' in pads and C.get('X2', {}).get('pattern') in SPECIAL:
        rows = collections.defaultdict(list)
        for p in pads['X2']:
            if p['pad'].isdigit():
                rows[round(p['y'], 1)].append(p)
        for y, r in sorted(rows.items()):
            xs, ys = [p['x'] for p in r], [p['y'] for p in r]
            h = (min(xs) - 1.27, min(ys) - 1.27, max(xs) + 1.27, max(ys) + 1.27)
            ns = sorted(int(p['pad']) for p in r)
            parts['Bottom']['X2[%d-%d]' % (ns[0], ns[-1])] = {'pads': [], 'body': [h], 'bodyt': [h]}
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
                for x, xt in zip(X['body'], X['bodyt'] or X['body']):
                    for pb, p in Y['pads']:
                        g = gap(x, pb)
                        if g < min_gap:
                            out.append((s, 'body_pad', xn, yn, p['pad'], round(g, 3)))
                        gt = gap(xt, pb)
                        if gt < 0 and round(g, 3) >= 0:     # nominal clears or just touches (rounded like the rest)
                            out.append((s, 'body_pad_max', xn, yn, p['pad'], round(gt, 3)))
    return out


def mech_mismatch(D):
    """Connectors whose comps.json side / rotation / footprint differ from what tools/body_mech.json was derived on."""
    C = {c['ref']: c for c in D['comps']}
    bad = []
    for ref, m in D['mech'].items():
        c = C.get(ref)
        want = (m.get('layer'), m.get('rot'), m.get('pattern'))
        have = (c['layer'], round(c['rot']) % 360, c['pattern']) if c else None
        if None in want or have != want:
            bad.append('%s: body_mech.json was derived for %s, the board has %s' % (ref, want, have))
    return bad


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
