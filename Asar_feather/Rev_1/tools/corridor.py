"""Lane capacity across a cut line (2026-10-31): for a vertical cut x=X (or horizontal y=Y) between y0..y1, per
routing layer, the copper intervals crossing the line (tracks, vias, pads with their clearance) and the free gaps
that still fit one SDRAM lane (0.1 width + 0.1 clearance on inner layers, 0.0762 + 0.09 on the outer ones), next to
the nets whose copper already crosses the line.

    python tools/corridor.py <model.json> [plan.json] x=30.3 y0=6 y1=17 [nets=A1,A2]   (or y=16.4 x0=.. x1=..)"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import router as R  # noqa: E402
from route_check import span  # noqa: E402


def main():
    files = [a for a in sys.argv[1:] if '=' not in a]
    kv = dict(a.split('=', 1) for a in sys.argv[1:] if '=' in a)
    if 'clear' in kv:                                    # clear=0.0762 sdram=plain: the rules of router.py --clear / --sdram-plain
        R.CLEAR = float(kv.pop('clear'))
    if kv.pop('sdram', '') == 'plain':
        R.SDRAM_RULES = False
    M = json.load(open(files[0]))
    tracks, vias = list(M['tracks']), list(M['vias'])
    if len(files) > 1:
        P = json.load(open(files[1]))
        rm = P.get('remove', [])

        def same(t, r):
            return t['net'] == r['net'] and t['layer'] == r['layer'] and \
                {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == \
                {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))}
        tracks = [t for t in tracks if not any(same(t, r) for r in rm)] + P['tracks']
        vias = vias + [dict(v, span=span(v)) for v in P['vias']]
    vertical = 'x' in kv
    X = float(kv['x']) if vertical else float(kv['y'])
    lo, hi = (float(kv['y0']), float(kv['y1'])) if vertical else (float(kv['x0']), float(kv['x1']))
    want = set(kv['nets'].split(',')) if 'nets' in kv else set()
    print('%s cut at %.2f, %s %.2f..%.2f' % ('vertical' if vertical else 'horizontal', X, 'y' if vertical else 'x', lo, hi))
    for layer in R.ROUTE:
        inner = layer in R.INNER
        lane = (0.1 + 0.1) if inner else (0.0762 + 0.09)
        iv = []                                     # (a, b, net) occupied intervals along the cut (copper + clearance)
        for t in tracks:
            if t['layer'] != layer:
                continue
            c = R.clearance(t['net'], layer)
            r = t['w'] / 2 + c
            p1, p2 = ((t['x1'], t['y1']), (t['x2'], t['y2']))
            a1, a2 = (p1[0], p2[0]) if vertical else (p1[1], p2[1])
            b1, b2 = (p1[1], p2[1]) if vertical else (p1[0], p2[0])
            if min(a1, a2) - r > X or max(a1, a2) + r < X:
                continue
            # the track's extent along the cut where it is within r of the line: project the thick segment
            if abs(a2 - a1) < 1e-9:
                lo_b, hi_b = min(b1, b2) - r, max(b1, b2) + r
            else:
                tt = [(X - r - a1) / (a2 - a1), (X + r - a1) / (a2 - a1)]
                tt = [max(0.0, min(1.0, v)) for v in tt]
                bb = [b1 + v * (b2 - b1) for v in tt]
                lo_b, hi_b = min(bb) - r, max(bb) + r
            iv.append((lo_b, hi_b, t['net']))
        for v in vias:
            if layer not in v['span']:
                continue
            a, b = (v['x'], v['y']) if vertical else (v['y'], v['x'])
            r = v['size'] / 2 + R.clearance(v['net'], layer)
            if abs(a - X) < r:
                h = math.sqrt(r * r - (a - X) ** 2)
                iv.append((b - h, b + h, v['net']))
        for p in M['pads']:
            ls = p['layers'] or (R.STACK if p['drill'] > 0 else [])
            if layer not in ls:
                continue
            a, b = (p['x'], p['y']) if vertical else (p['y'], p['x'])
            r = max(p['w'], p['h']) / 2 + R.clearance(p['net'], layer)
            if abs(a - X) < r:
                iv.append((b - r, b + r, p['net'] or '(nc)'))
        iv = [(max(lo, a), min(hi, b), n) for a, b, n in iv if b > lo and a < hi]
        iv.sort()
        merged, nets = [], {}
        for a, b, n in iv:
            nets[n] = nets.get(n, 0) + 1
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        free, cur, lanes = [], lo, 0
        for a, b in merged:
            if a - cur >= lane:
                free.append((cur, a)); lanes += int((a - cur + (0.1 if inner else 0.09)) // lane)
            cur = max(cur, b)
        if hi - cur >= lane:
            free.append((cur, hi)); lanes += int((hi - cur + (0.1 if inner else 0.09)) // lane)
        crossing = sorted(nets)
        print('%-13s crossing %2d nets, free lanes %2d  gaps: %s' % (
            layer, len(crossing), lanes, ' '.join('%.2f-%.2f' % g for g in free)))
        print('   nets: %s' % ' '.join(crossing))
        if want:
            print('   wanted nets crossing here: %s' % ' '.join(sorted(want & set(crossing))))


if __name__ == '__main__':
    main()
