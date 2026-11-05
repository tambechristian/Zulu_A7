"""Why are the open connections of a routing plan still open? (2026-10-26)

For every open connection of <plan> (on top of <model>) the router is asked to join the net's two nearest islands
on three boards, each with a generous search budget and a board-wide window:
    pads   only the pads (no copper at all)              fails -> the pads themselves wall it (placement)
    fixed  the model's copper (stage 1, the SDRAM bus)   fails -> fixed copper walls it (rip stage 1 / the bus)
    plan   the model's copper plus the plan's copper     fails -> congestion with the plan's own nets
Plane ties (GND, VCC3V3 islands with no plane connection) are tried with the plane via types.

    python tools/diagnose_open.py <plan.json> <model.json> [--pops N] [--out report.json]
"""
import argparse
import json
import math
import os
import sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

ST = R.STACK
G = {}


def with_plan(M, P):
    Mx = dict(M)
    Mx['tracks'] = M['tracks'] + P['tracks']
    Mx['vias'] = M['vias'] + [dict(v, span=ST[ST.index(v['from']):ST.index(v['to']) + 1]) for v in P['vias']]
    return Mx


def init(model, plan, pops, laser_small='', clear=0.09, sdram_rules=True):
    R.CLEAR = clear
    R.SDRAM_RULES = sdram_rules
    if laser_small:
        R.add_small_lasers(*[float(v) for v in laser_small.split('/')])
    M = json.load(open(model))
    P = json.load(open(plan))
    Mx = with_plan(M, P)
    G['Mx'] = Mx
    G['isl'] = C.islands(Mx)
    empty = dict(M, tracks=[], vias=[])
    G['boards'] = {'pads': R.Board(empty), 'fixed': R.Board(M), 'plan': R.Board(Mx)}
    G['pops'] = pops


def centre(M, g):
    b = R.bbox(M, g)
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def job(task):
    net, a, b = task                                  # b is None for a plane tie of island a
    Mx, isl = G['Mx'], G['isl']
    out = {'net': net, 'at': [round(v, 2) for v in centre(Mx, isl[net][a])]}
    for lvl in ('pads', 'fixed', 'plan'):
        B = G['boards'][lvl]
        Rt = R.Router(B, G['pops'])
        ok = False
        for mg in (2.5, 6.0, 60.0):
            boxes = [R.bbox(Mx, isl[net][a])] + ([R.bbox(Mx, isl[net][b])] if b is not None else [])
            win = R.window(B, boxes, mg if b is not None else min(mg, 3.0))
            src = R.island_mask(B, Mx, isl[net][a], win)
            if b is None:
                r = Rt.route(net, src, None, win, plane=R.PLANE_VIAS[net])
            else:
                r = Rt.route(net, src, R.island_mask(B, Mx, isl[net][b], win), win)
            if r:
                ok = True
                break
        out[lvl] = ok
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('model')
    ap.add_argument('--pops', type=int, default=1500000)
    ap.add_argument('--out', default='')
    ap.add_argument('--nets', default='', help='diagnose only these nets (comma list)')
    ap.add_argument('--laser-small', default='', help='second laser family SIZE/HOLE, as router.py --laser-small')
    ap.add_argument('--clear', type=float, default=0.09, help='Clearance rule, as router.py --clear')
    ap.add_argument('--sdram-plain', action='store_true', help='as router.py --sdram-plain')
    a = ap.parse_args()
    R.CLEAR = a.clear
    R.SDRAM_RULES = not a.sdram_plain
    M = json.load(open(a.model))
    Mx = with_plan(M, json.load(open(a.plan)))
    isl = C.islands(Mx)
    tasks = []
    for net, gs in sorted(isl.items()):
        if net in R.PLANE_VIAS:
            tasks += [(net, k, None) for k, g in enumerate(gs) if not g['plane']]
            continue
        if len(gs) < 2:
            continue
        # each island but the first joins its nearest earlier island (a spanning tree of the open connections)
        for k in range(1, len(gs)):
            ck = centre(Mx, gs[k])
            j = min(range(k), key=lambda j: math.dist(ck, centre(Mx, gs[j])))
            tasks.append((net, j, k))
    if a.nets:
        tasks = [t for t in tasks if t[0] in a.nets.split(',')]
    print('%d open connections to diagnose' % len(tasks), flush=True)
    with Pool(min(20, len(tasks)), initializer=init, initargs=(a.model, a.plan, a.pops, a.laser_small, a.clear, not a.sdram_plain)) as pool:
        res = pool.map(job, tasks, chunksize=1)
    cls = {}
    for r in res:
        c = 'placement' if not r['pads'] else 'fixed copper' if not r['fixed'] else \
            'congestion' if not r['plan'] else 'routable (budget/order)'
        r['class'] = c
        cls.setdefault(c, []).append(r)
    for c, rs in sorted(cls.items()):
        print('%-24s %2d  %s' % (c, len(rs), ' '.join('%s@%.1f,%.1f' % (r['net'], *r['at']) for r in rs)))
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
