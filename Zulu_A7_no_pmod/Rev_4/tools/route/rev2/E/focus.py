"""focus.py --model M --seed S --net NET --win x0,y0,x1,y1 [--pops N] [--out OUT] [--probe SOFT] [--hw W]
          [--islands a,b] [--slack 0.02]
Route one open connection of NET inside a hand-picked window (efast via policy: no via land on an SMD pad,
plane-tie columns, numpy via_ok). The two islands joined are the two largest-overlap islands with copper in the
window (or --islands i,j by index as printed). On success writes OUT = seed + the new copper (a router plan).
--probe SOFT: instead, find the cheapest path through router (seed) copper at SOFT mm per cell and print the nets it
crosses (nothing is ripped or written)."""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import efast  # noqa: E402,F401
R = efast.R
C = R.C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--seed', required=True)
    ap.add_argument('--net', required=True)
    ap.add_argument('--win', required=True)
    ap.add_argument('--pops', type=int, default=2000000)
    ap.add_argument('--out', default='')
    ap.add_argument('--probe', type=float, default=0.0)
    ap.add_argument('--hw', type=float, default=1.0)
    ap.add_argument('--islands', default='')
    ap.add_argument('--slack', type=float, default=0.02)
    a = ap.parse_args()
    R.MARGIN = a.slack
    M = json.load(open(a.model))
    P = json.load(open(a.seed))
    B = R.Board(M)
    Rt = R.Router(B, a.pops)
    Rt.out_t += P['tracks']
    Rt.out_v += P['vias']
    Rt.rip(set())
    Rt.hw = a.hw
    Mx = dict(M)
    Mx['tracks'] = M['tracks'] + Rt.out_t
    Mx['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in Rt.out_v]
    x0, y0, x1, y1 = map(float, a.win.split(','))
    win = (max(0, int(y0 / R.G)), min(B.H, int(y1 / R.G) + 1), max(0, int(x0 / R.G)), min(B.W, int(x1 / R.G) + 1))
    gs = C.islands(Mx).get(a.net, [])
    print('%s: %d islands' % (a.net, len(gs)))
    masks = []
    for k, g in enumerate(gs):
        m = R.island_mask(B, Mx, g, win)
        n = sum(int(v.sum()) for v in m.values())
        bb = R.bbox(Mx, g)
        print('  island %d: %d cells in window, pads %s, bbox %.2f,%.2f-%.2f,%.2f' % (
            k, n, ['%s.%s' % (Mx['pads'][i]['ref'], Mx['pads'][i]['pad']) for i in g['pads']][:4], *bb))
        masks.append((n, k, m))
    if a.islands:
        ia, ib = map(int, a.islands.split(','))
    else:
        top = sorted([t for t in masks if t[0] > 0], reverse=True)[:2]
        if len(top) < 2:
            print('fewer than two islands reach the window')
            return
        ia, ib = top[0][1], top[1][1]
    src, dst = masks[ia][2], masks[ib][2]
    if a.probe:
        Rt.soft = a.probe
        r = Rt.route(a.net, src, dst, win, base=True)
        if not r:
            print('probe: no path (%s, %d pops)' % (Rt.why, getattr(Rt, 'pops', 0)))
            return
        vic = Rt.blockers(a.net, r[0], tight=True)
        print('probe path %d cells, crosses router copper of: %s' % (len(r[0]), ' '.join(sorted(vic))))
        pts = [(l[:3], round(x, 3), round(y, 3), k) for l, x, y, k in r[0]]
        out, last = [], None
        for p in pts:
            if p[0] != last or p[3]:
                out.append(p)
                last = p[0]
        print('  layer changes:', out[:40])
        return
    r = Rt.route(a.net, src, dst, win)
    if not r:
        print('hard route failed (%s, %d pops)' % (Rt.why, getattr(Rt, 'pops', 0)))
        return
    n0t, n0v = len(Rt.out_t), len(Rt.out_v)
    Rt.commit(a.net, *r)
    nt, nv = Rt.out_t[n0t:], Rt.out_v[n0v:]
    print('routed: %d tracks, %d vias (%d pops)' % (len(nt), len(nv), Rt.pops))
    for t in nt:
        print('  T %s %.3f,%.3f-%.3f,%.3f w%.3f' % (t['layer'][:3], t['x1'], t['y1'], t['x2'], t['y2'], t['w']))
    for v in nv:
        print('  V %.3f,%.3f %s>%s %.2f' % (v['x'], v['y'], v['from'][:3], v['to'][:3], v['size']))
    if a.out:
        json.dump({'tracks': Rt.out_t, 'vias': Rt.out_v, 'remove': P.get('remove', [])}, open(a.out, 'w'), indent=0)
        print('->', a.out)


if __name__ == '__main__':
    main()
