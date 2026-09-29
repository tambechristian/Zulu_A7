# -*- coding: utf-8 -*-
"""Per-ball ESCAPE capability of U1, which is what the 2026-09-10 re-pin study did not measure.

    python tools/stage7/escape_audit.py [--inputs F] [--json OUT]

WHY.  docs/repin_study.md scored a permutation on total net LENGTH and found a full re-pin worth
411 mm (16 %).  Stage 6 did not fail on length: three routers on a board whose worst corridor is 16 %
loaded all stopped at 86-88 of 140, and every one of them reported the same cause -- U1's east face
has ball rows with no legal escape at all (docs/stage6_attempt.md).  Length is the wrong objective;
this measures the right one.

WHAT IT MEASURES, per signal ball, on the board as saved:
  * where the ball's fan-out already put it -- the dog-bone stub end and its via, if any.  A re-pin
    does NOT move that copper: the stub and via are geometry, and a permutation only changes which
    NET sits on them.  So a ball's escape capability is a property of the BOARD, not of its net, and
    it is the same for whatever net the re-pin puts there.
  * the widest legal straight run out of that stub end in each of the four directions, by
    segw.maxwidth (which since 2026-09-28 applies BOTH nets' clearances -- see commit 84b6812).
    Negative means no track of any legal width can leave that way.
  * whether a fresh 0.35 mm via land is legal within reach, by route_reach's own via raster.
A ball is DEAD when no direction admits a 0.0762 mm track and no via site is in reach: no net placed
there can be routed anywhere, so a permutation must not put an unrouted net on it.
"""
import io, json, math, os, sys
import numpy as np

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, 'stage6'))
import route_reach as RR
import segw

MINW = 0.0762
REACH = 1.20                      # how far from the stub end a via site may sit and still serve it
PROBE = 1.50                      # length of the straight probe run
DIRS = (('E', 1, 0), ('W', -1, 0), ('N', 0, 1), ('S', 0, -1))
POWER = {'VCC3V3', 'VCC1V0', 'VCC1V8', 'GND', 'GNDADC', 'VCCADC'}


def main():
    a = sys.argv[1:]
    def opt(n, d=None):
        return a[a.index(n) + 1] if n in a else d
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))

    allp = inp['top_pads'] + inp['bottom_pads'] + inp['th_pads']
    balls = [p for p in allp if p['ref'] == 'U1' and p.get('net') and p['net'] not in POWER]

    # the fan-out: each ball's own copper.  The stub end is the far end of the track that starts on
    # the ball; if the ball has none, the ball centre is the only place a route can start.
    ends = {}
    for b in balls:
        best = (b['x'], b['y'])
        for t in inp['tracks']:
            if t['net'] != b['net']:
                continue
            for p, q in (((t['x1'], t['y1']), (t['x2'], t['y2'])), ((t['x2'], t['y2']), (t['x1'], t['y1']))):
                if abs(p[0] - b['x']) < 1e-4 and abs(p[1] - b['y']) < 1e-4:
                    best = q
        ends[b['pad']] = best

    objs = RR.world(inp, [])
    R = RR.Raster(inp['outline'])
    tc, vc, edge_t, edge_v = RR.base_rasters(R, inp, objs)
    via_ok = (vc == 0) & (~edge_v)

    def via_within(x, y, r):
        i0 = max(0, int((x - r - R.x0) / RR.CELL)); i1 = min(R.nx, int((x + r - R.x0) / RR.CELL) + 1)
        j0 = max(0, int((y - r - R.y0) / RR.CELL)); j1 = min(R.ny, int((y + r - R.y0) / RR.CELL) + 1)
        if i1 <= i0 or j1 <= j0:
            return 0
        return int(via_ok[j0:j1, i0:i1].sum())

    # a stub that ENDS ON ITS OWN FAN-OUT VIA can leave on any of the four layers, not just the two
    # outer ones: the via is the layer change.  Probing Top and Bottom only -- which is what stage 6's
    # "negative on all 17 east rows" figure did -- understates the escape badly, so the layer set is
    # chosen per ball from whether the stub end carries a via of the ball's own net.
    ownvia = {}
    for b in balls:
        ex, ey = ends[b['pad']]
        ownvia[b['pad']] = any(v['net'] == b['net'] and abs(v['x'] - ex) < 1e-4 and abs(v['y'] - ey) < 1e-4
                               for v in inp['vias'])

    rows = []
    for b in balls:
        ex, ey = ends[b['pad']]
        layers = ('Top', 'Bottom', 'L3-SIG', 'L4-SIG') if ownvia[b['pad']] else ('Top', 'Bottom')
        w = {}
        wl = {}
        for name, dx, dy in DIRS:
            seg = (ex, ey, ex + dx * PROBE, ey + dy * PROBE)
            best, bl = -9.0, None
            for layer in layers:
                r = segw.maxwidth(inp, b['net'], layer, seg)
                v = r[0] if isinstance(r, tuple) else r
                if v > best:
                    best, bl = v, layer
            w[name] = round(best, 4)
            wl[name] = bl
        sites = via_within(ex, ey, REACH)
        live = [k for k, v in w.items() if v >= MINW]
        rows.append(dict(ball=b['pad'], net=b['net'], x=b['x'], y=b['y'],
                         stub_x=round(ex, 4), stub_y=round(ey, 4), has_via=ownvia[b['pad']],
                         w=w, best_layer=wl, via_sites=sites, open_dirs=live,
                         dead=(not live and sites == 0)))
    rows.sort(key=lambda r: (r['dead'], -max(r['w'].values())))
    dead = [r for r in rows if r['dead']]
    print('U1 signal balls audited: %d' % len(rows))
    print('  with NO legal track direction and NO via site in %.2f mm  -> DEAD: %d' % (REACH, len(dead)))
    print('  with no legal track direction but a via site in reach:      %d'
          % sum(1 for r in rows if not r['open_dirs'] and r['via_sites']))
    print('  with at least one legal direction:                          %d'
          % sum(1 for r in rows if r['open_dirs']))
    if dead:
        print('\nDEAD balls (a permutation must not put an unrouted net on these):')
        for r in dead:
            print('   %-4s %-12s stub (%7.3f,%7.3f) via=%-5s E%7.4f W%7.4f N%7.4f S%7.4f  sites %d'
                  % (r['ball'], r['net'], r['stub_x'], r['stub_y'], r['has_via'],
                     r['w']['E'], r['w']['W'], r['w']['N'], r['w']['S'], r['via_sites']))
    out = opt('--json')
    if out:
        json.dump(rows, io.open(out, 'w', encoding='utf-8'), indent=1)
        print('\nwrote %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
