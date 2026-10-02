# -*- coding: utf-8 -*-
"""How much routing room does a plan free, and how many lanes cross the corridors that matter?

    python tools/stage5/capacity.py [--inputs F] [plan.json ...]

Built on route_reach's own raster so the answer uses the same clearance model as the gates: a cell is
free for a 0.0762 mm track centreline on a layer when no foreign object on that layer comes within
its clearance + half the track width (0.09 everywhere, 0.10 from SDRAM copper on L3/L4, 0.20 from
SDRAM-CLK), and the board-edge band is excluded.  Two new tracks need 0.0762 + 0.09 = 0.1662 mm
between centres, so a free run of length L holds floor(L / 0.1662) + 1 lanes.

Reports, for the board alone and for the board plus the plans:
  * free routing area per layer, in mm2 and as a percentage of the board;
  * lanes across the cut-lines that stage 4b needs -- the north band (horizontal, y 19.6, x 5-39,
    stage 3's L4 spine) and the U1 east corridor (vertical, x 52.9, y 2-24, stage 3's Bottom column).
Add --cut 'name,h|v,pos,lo,hi' to measure another cut-line.
"""
import io, json, os, sys
import numpy as np

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_reach as RR
import merge as M

PITCH_LANE = 0.0762 + 0.09      # centre-to-centre for two adjacent 3 mil tracks at 0.09

CUTS = [('north band  y 19.6, x 5-39', 'h', 19.6, 5.0, 39.0),
        ('U1 east     x 52.9, y 2-24', 'v', 52.9, 2.0, 24.0)]


def rasters(inp, plans):
    objs = RR.world(inp, plans)
    R = RR.Raster(inp['outline'])      # route_reach's own raster, same cell and same clearances
    track_cov, via_cov, edge_t, edge_v = RR.base_rasters(R, inp, objs)
    free = [(tc == 0) & (~edge_t) for tc in track_cov]
    return R, free


def lanes(free_row):
    """lanes in one 1-D boolean run of free cells"""
    n = 0
    run = 0
    for c in list(free_row) + [False]:
        if c:
            run += 1
        else:
            if run:
                n += int(((run - 1) * RR.CELL) / PITCH_LANE) + 1
            run = 0
    return n


def measure(inp, plans, label):
    R, free = rasters(inp, plans)
    cell2 = RR.CELL * RR.CELL
    out = dict(label=label, area={}, cuts={})
    print('--- %s ---' % label)
    tot = 0.0
    for li, L in enumerate(RR.LAYERS):
        a = float(free[li].sum()) * cell2
        out['area'][L] = a
        tot += a
        print('   free for a 3 mil track: %-7s %8.1f mm2' % (L, a))
    out['area']['TOTAL'] = tot
    print('   %-31s %8.1f mm2' % ('total over the four layers', tot))
    for name, kind, pos, lo, hi in CUTS:
        per = {}
        for li, L in enumerate(RR.LAYERS):
            if kind == 'h':
                j = int(round((pos - R.y0) / RR.CELL))
                i0 = int(round((lo - R.x0) / RR.CELL)); i1 = int(round((hi - R.x0) / RR.CELL))
                row = free[li][j, i0:i1 + 1]
            else:
                i = int(round((pos - R.x0) / RR.CELL))
                j0 = int(round((lo - R.y0) / RR.CELL)); j1 = int(round((hi - R.y0) / RR.CELL))
                row = free[li][j0:j1 + 1, i]
            per[L] = lanes(row)
        out['cuts'][name] = per
        print('   lanes across %-28s %s  = %d' % (name, '  '.join('%s %2d' % (k.replace('-SIG', ''), v) for k, v in per.items()), sum(per.values())))
    return out


def main():
    a = sys.argv[1:]
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))
    skip = set()
    for k in ('--inputs',):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    paths = [p for i, p in enumerate(a) if i not in skip and p.endswith('.json')]
    before = measure(inp, [], 'board as saved')
    if not paths:
        return 0
    plan = M.merge(paths)[0]
    after = measure(inp, [plan], 'board + %d plan file(s)' % len(paths))
    print('\n=== GAIN ===')
    for L in list(RR.LAYERS) + ['TOTAL']:
        d = after['area'][L] - before['area'][L]
        print('   %-7s %+8.1f mm2   (%8.1f -> %8.1f)' % (L, d, before['area'][L], after['area'][L]))
    for name in before['cuts']:
        b, f = before['cuts'][name], after['cuts'][name]
        print('   lanes %-28s %s   total %d -> %d  (%+d)'
              % (name, '  '.join('%s %d->%d' % (k.replace('-SIG', ''), b[k], f[k]) for k in b),
                 sum(b.values()), sum(f.values()), sum(f.values()) - sum(b.values())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
