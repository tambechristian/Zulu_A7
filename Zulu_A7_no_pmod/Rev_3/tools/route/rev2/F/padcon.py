"""padcon.py <model.json> <out_step.json> -- prune-safe joints for the MOVED pads.

A kept track that reaches a moved pad of its own net only with its body (no endpoint on the pad) counts as
connected for route_conn / Altium, but prune_stubs only knows endpoint-on-pad joints and would trim the track off
the pad. For each such (pad, track) pair a connector (same net / layer / width) is added from the track's
centreline point P nearest the pad centre (inside the pad when the centreline crosses it) to the pad centre, or --
when the centreline misses the pad -- to the pad point nearest P (|PQ| <= w/2, so it stays inside the track)."""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import route_conn as C  # noqa: E402

EPS = 1e-4
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def main():
    M = json.load(open(sys.argv[1]))
    O = json.load(open(os.path.join(HERE, '..', 'model_base.json')))
    moved = [n for o, n in zip(O['pads'], M['pads']) if (o['x'], o['y']) != (n['x'], n['y']) and n['net']]
    add = []
    for p in moved:
        layers = p['layers'] or (STACK if p['drill'] else [])
        for t in M['tracks']:
            if t['net'] != p['net'] or t['layer'] not in layers or t['net'] in ('USB_D_P', 'USB_D_N'):
                continue
            s = (t['x1'], t['y1'], t['x2'], t['y2'])
            if C.pad_seg(p, s) > t['w'] / 2 + EPS:
                continue
            if C.pad_point(p, t['x1'], t['y1']) <= EPS or C.pad_point(p, t['x2'], t['y2']) <= EPS:
                continue
            L = math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])
            n = max(1, int(L / 0.002))
            best = None
            for k in range(n + 1):
                x, y = t['x1'] + (t['x2'] - t['x1']) * k / n, t['y1'] + (t['y2'] - t['y1']) * k / n
                d = C.pad_point(p, x, y)
                c = math.hypot(x - p['x'], y - p['y'])
                key = (d > EPS, d, c)
                if best is None or key < best[0]:
                    best = (key, x, y)
            (_, d, _), px, py = best
            if d <= EPS:
                qx, qy = p['x'], p['y']
            elif C.pad_round(p):
                r = min(p['w'], p['h']) / 2 - 0.001
                a = math.atan2(py - p['y'], px - p['x'])
                qx, qy = p['x'] + r * math.cos(a), p['y'] + r * math.sin(a)
            else:
                qx = min(max(px, p['x'] - p['w'] / 2 + 0.001), p['x'] + p['w'] / 2 - 0.001)
                qy = min(max(py, p['y'] - p['h'] / 2 + 0.001), p['y'] + p['h'] / 2 - 0.001)
            c = {'net': t['net'], 'layer': t['layer'], 'w': t['w'], 'x1': round(px, 4), 'y1': round(py, 4),
                 'x2': round(qx, 4), 'y2': round(qy, 4)}
            add.append(c)
            print('padcon %s.%s %-10s %-12s (%.4f,%.4f)-(%.4f,%.4f) w%.4f  [track (%.3f,%.3f)-(%.3f,%.3f)]' % (
                p['ref'], p['pad'], t['net'], t['layer'], c['x1'], c['y1'], c['x2'], c['y2'], c['w'],
                t['x1'], t['y1'], t['x2'], t['y2']))
    json.dump({'tracks': add, 'vias': [], 'remove': [], 'remove_vias': []}, open(sys.argv[2], 'w'), indent=0)
    print('%d pad connectors' % len(add))


if __name__ == '__main__':
    main()
