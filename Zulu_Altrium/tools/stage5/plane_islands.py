# -*- coding: utf-8 -*-
"""Does an internal plane survive its anti-pads as ONE island, and does every pad of the
plane net sit over it?

    python tools/stage5/plane_islands.py [--inputs F] [--net VCC3V3] [--plane L5] [plan.json ...]

Altium pours an internal plane over the board inside PLANE<n>PULLBACK (20 mil here) and punches an
anti-pad around every hole that is NOT on the plane's net: diameter = hole + 2 x PlaneClearance,
and PlaneClearance is 9.8425 mil = 0.25 mm, so a 0.20 mm via hole punches 0.70 mm.  Holes ON the
plane net connect Direct (rule PlaneConnect_Vias) and punch nothing.

The plane is rasterised at 0.02 mm and labelled **4-connected**.  4 and not 8: two plane regions that
meet at a single diagonal pixel corner touch at a point of zero width and conduct nothing, and an
8-connected labelling calls them one island.  This gate existed to find exactly that failure, and it
could not see it until 2026-09-23 (the stage-5 reviewers caught it); re-labelled 4-connected, L5
carrying VCC3V3 turns out to have a 0.48 mm2 patch at x 48.648-49.148, y 12.208-13.588 that the
8-connected run reported as part of the main island.  The gate is: ONE island holding essentially all
the copper, every pad of the plane net over it, and no stray worth worrying about.  Exit 1 otherwise.

Measured on the stage-4a board (2026-09-23), before any stage-5 copper, 4-connected:
    L5 as GND today    255 anti-pads, 1514.4 mm2 main, 0.009 mm2 stray, all 211 GND pads over the main
    L5 as VCC3V3       338 anti-pads, 1477.4 mm2 main, 0.502 mm2 stray (0.480 of it one patch inside
                       U1's land field at 48.648-49.148 x 12.208-13.588, walled in by the VCC1V8,
                       CHAN and GND vias that punch L5 only once it stops being GND), all 128 VCC3V3
                       pads over the main island.  That patch carries nothing -- no VCC3V3 via inside
                       it, no VCC3V3 pad over it -- and no routing plan creates or can remove it: it is
                       a consequence of the plane net change itself.  It is floating copper, i.e. an
                       isolated plane region, not a connectivity fault.
"""
import io, json, os, sys
import numpy as np
from scipy import ndimage

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import merge as M

PULLBACK = 0.508
PLANE_CLR = 0.25
STEP = 0.02


def analyse(inp, plane_net, extra_vias=()):
    o = inp['outline']
    x0, y0 = o['x0'] + PULLBACK, o['y0'] + PULLBACK
    x1, y1 = o['x1'] - PULLBACK, o['y1'] - PULLBACK
    nx = int(round((x1 - x0) / STEP)) + 1
    ny = int(round((y1 - y0) / STEP)) + 1
    X, Y = np.meshgrid(x0 + np.arange(nx) * STEP, y0 + np.arange(ny) * STEP, indexing='ij')
    copper = np.ones((nx, ny), bool)
    holes = [(v['x'], v['y'], v.get('hole', 0.2) / 2.0 + PLANE_CLR)
             for v in list(inp['vias']) + list(extra_vias) if v.get('net') != plane_net]
    holes += [(p['x'], p['y'], p['hole'] / 2.0 + PLANE_CLR)
              for p in inp['th_pads'] if p.get('net') != plane_net]
    for hx, hy, r in holes:
        i0 = max(0, int((hx - r - x0) / STEP) - 1); i1 = min(nx, int((hx + r - x0) / STEP) + 2)
        j0 = max(0, int((hy - r - y0) / STEP) - 1); j1 = min(ny, int((hy + r - y0) / STEP) + 2)
        if i1 > i0 and j1 > j0:
            copper[i0:i1, j0:j1] &= ~((X[i0:i1, j0:j1] - hx) ** 2 + (Y[i0:i1, j0:j1] - hy) ** 2 <= r * r)
    lab, n = ndimage.label(copper)          # 4-connected: a diagonal pixel touch is not a conductor
    sizes = ndimage.sum(copper, lab, range(1, n + 1)) * STEP * STEP
    order = list(np.argsort(sizes)[::-1])
    return dict(lab=lab, sizes=sizes, order=order, n=n, x0=x0, y0=y0, nx=nx, ny=ny,
                holes=len(holes), total=float(sizes.sum()), gross=(x1 - x0) * (y1 - y0))


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    net = opt('--net', 'VCC3V3')
    plane = opt('--plane', 'L5')
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))
    skip = set()
    for k in ('--inputs', '--net', '--plane'):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    paths = [p for i, p in enumerate(a) if i not in skip and p.endswith('.json')]
    plan = M.merge(paths)[0] if paths else {'vias': [], 'tracks': []}
    if plan.get('remove'):
        import route_emit as RE
        inp, missing = RE.apply_removals(inp, plan)
        if missing:
            print('REMOVALS DO NOT MATCH THE BOARD: %s' % '; '.join(missing))
            return 2
    extra = [dict(x=v['x'], y=v['y'], hole=v.get('hole', 0.2), net=v.get('net')) for v in plan['vias']]
    r = analyse(inp, net, extra)
    allp = inp['top_pads'] + inp['bottom_pads'] + inp['th_pads']
    pads = [p for p in allp if p.get('net') == net]
    main_isl = int(r['order'][0]) + 1

    print('plane %s carrying %s: %d anti-pads, %d island(s), %.1f mm2 of %.1f mm2 gross '
          '(board + %d plan file(s): %d plan vias)'
          % (plane, net, r['holes'], r['n'], r['total'], r['gross'], len(paths), len(extra)))
    for k in r['order'][:5]:
        if r['sizes'][k] > 0.0005:
            print('   island %2d  %8.3f mm2  (%5.1f %%)' % (k + 1, r['sizes'][k], 100.0 * r['sizes'][k] / r['total']))
    stray = [k for k in r['order'][1:] if r['sizes'][k] > 0.0005]
    stray_area = float(sum(r['sizes'][k] for k in r['order'][1:]))

    bad = []
    for p in pads:
        i = int(round((p['x'] - r['x0']) / STEP)); j = int(round((p['y'] - r['y0']) / STEP))
        if not (0 <= i < r['nx'] and 0 <= j < r['ny']):
            bad.append((p, 'outside the %.3f mm pullback' % PULLBACK)); continue
        isl = r['lab'][i, j]
        if isl == 0:
            bad.append((p, 'over an anti-pad void'))
        elif isl != main_isl:
            bad.append((p, 'over island %d (%.3f mm2)' % (isl, r['sizes'][isl - 1])))
    print('   %d of %d %s pads sit over the main island (sampled at the pad centre)'
          % (len(pads) - len(bad), len(pads), net))

    # a pad reaches the plane through a BARREL, not by lying over copper: check every via of the net
    conn = [v for v in list(inp['vias']) + extra if v.get('net') == net]
    offv = []
    for v in conn:
        i = int(round((v['x'] - r['x0']) / STEP)); j = int(round((v['y'] - r['y0']) / STEP))
        if not (0 <= i < r['nx'] and 0 <= j < r['ny']) or r['lab'][i, j] != main_isl:
            offv.append(v)
    print('   %d of %d %s vias land on the main island' % (len(conn) - len(offv), len(conn), net))
    for v in offv:
        print('   OFF-PLANE VIA (%7.3f,%7.3f)' % (v['x'], v['y']))
    bad += [(dict(ref='via', pad='@%.3f,%.3f' % (v['x'], v['y']), x=v['x'], y=v['y']), 'via off the main island') for v in offv]
    for p, why in bad:
        print('   OFF-PLANE %-9s (%7.3f,%7.3f)  %s' % (p['ref'] + '-' + str(p['pad']), p['x'], p['y'], why))
    if stray:
        print('   %d stray island(s) over 0.0005 mm2, %.4f mm2 of floating plane copper in all:' % (len(stray), stray_area))
        for k in stray[:6]:
            xs, ys = np.nonzero(r['lab'] == k + 1)     # lab is [i(x), j(y)]
            print('      %8.4f mm2  x %.3f..%.3f  y %.3f..%.3f'
                  % (r['sizes'][k], r['x0'] + xs.min() * STEP, r['x0'] + xs.max() * STEP,
                     r['y0'] + ys.min() * STEP, r['y0'] + ys.max() * STEP))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
