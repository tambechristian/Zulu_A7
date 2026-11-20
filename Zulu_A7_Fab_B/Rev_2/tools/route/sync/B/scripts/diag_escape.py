"""diag_escape.py <model.json> <net,...> [router.json,...]  -- for each net, can each of its islands escape at all?
A* (router_b, same rules) from the island to every cell >= RAD mm away from the island's bbox, on any routing layer."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router_b as R  # noqa: E402
if os.environ.get('EXACT', '1') == '1':
    import exact_router  # noqa: E402,F401  (patches R.Router.dist / via_ok)
    R.MARGIN = exact_router.TRACK_SLACK

RAD = 1.2


def main():
    M = json.load(open(sys.argv[1]))
    nets = sys.argv[2].split(',')
    for f in (sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] else []):
        P = json.load(open(f))
        M['tracks'] += P['tracks']
        M['vias'] += [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]) for v in P['vias']]
    B = R.Board(M)
    Rt = R.Router(B, 200000)
    isl = R.C.islands(M)
    for net in nets:
        for gi, g in enumerate(isl.get(net, [])):
            bx = R.bbox(M, g)
            win = R.window(B, [bx], RAD + 1.0)
            i0, i1, j0, j1 = win
            yy, xx = np.mgrid[i0:i1, j0:j1]
            X, Y = xx * R.G, yy * R.G
            dx = np.maximum(np.maximum(bx[0] - X, X - bx[2]), 0)
            dy = np.maximum(np.maximum(bx[1] - Y, Y - bx[3]), 0)
            far = np.hypot(dx, dy) >= RAD
            dst = {l: far.copy() for l in R.ROUTE}
            r = Rt.route(net, R.island_mask(B, M, g, win), dst, win)
            pads = ['%s-%s' % (M['pads'][i]['ref'], M['pads'][i]['pad']) for i in g['pads']]
            if r:
                path, _ = r
                vias = [(p[3], round(p[1], 3), round(p[2], 3)) for p in path if p[3]]
                print('%-10s island %d %s bbox %s: ESCAPES (pops %d) first layer %s vias %s end %s' % (
                    net, gi, pads, [round(v, 2) for v in bx], Rt.pops, path[0][0], vias,
                    (path[-1][0], round(path[-1][1], 3), round(path[-1][2], 3))), flush=True)
            else:
                print('%-10s island %d %s bbox %s: SEALED (%s, pops %d)' % (net, gi, pads, [round(v, 2) for v in bx],
                                                                          Rt.why, getattr(Rt, 'pops', 0)), flush=True)


if __name__ == '__main__':
    main()
