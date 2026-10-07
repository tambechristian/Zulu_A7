# -*- coding: utf-8 -*-
"""SDRAM (39 nets) + XADC AIN15/AIN16 (4 nets) co-route plan, XADC copper placed first.

    python tools/coroute_plan.py            writes tools/coroute_plan.json, then runs both gates (about 30 s)

Reads tools/route_inputs.json only. Imports tools/sdram_route_plan.py's router UNEDITED and re-runs it with the
XADC copper (and the one removal) as fixed obstacles. Exit 0 only when all of these pass on the written plan:
    python tools/route_emit.py tools/coroute_plan.json CoRoute --require-complete   clean, 43/43
    python tools/route_foreclosure.py tools/coroute_plan.json                        foreclosed: none
    an exact track-to-pad clearance check (route_emit samples segment-to-pad distance at 25 points)

Why this plan (judge, 2026-09-15, over a 3-net local repair and a regenerated 'pair quality' plan):
  * the local repair had a real clearance fault on Bottom (AIN16_N 0.0893 from R11-1, rule 0.09) and boxed
    R12-2 (NODE_P0) in with no via slot; the 'quality' plan boxed R12-2, R10-1, R10-2 and R16-2 in with no via
    slot (NODE_P0, NODE_P1 and ANALOG-IO0 unroutable, which disconnects the AIN15/AIN16 inputs from their
    sources) and ran AIN16 19 mm on Bottom under U1. This plan leaves every filter-block net routable.
  * XADC: both pairs on Bottom (over L5, off the SDRAM layers), 0.1663 mm pitch (0.09 gap) down the U1 west
    -- NOTE 2026-09-24: L5 carried GND when this was planned and now carries VCC3V3 (stage 5).  Eight of the
    52 reference-plane crossings are XADC; docs/stage5_l5_plane.md prices the move to L3-SIG if it matters.
    strip; loops U1 -> C36 / C37 5.5 / 4.4 mm2; about 3.4 mm of Bottom copper under the U1 land field.

Decisions:
  * Removal (the proven-safe one): GND via (41.40,13.8999) + its Top stub from F1. F1 keeps GND through the F1-E1
    chain and E1's via (41.40,14.40); route_emit refuses the plan if any U1 power/GND ball loses its via.
  * U1 escapes on Top: AIN15_N via (40.60,14.05); AIN16_P via (40.45,13.40) west past the G1 GND via;
    AIN16_N via (41.30,12.665); AIN15_P leaves from its existing G3 moat via (43.40,13.90) on Bottom.
  * Bottom bundle: rubber-band tracks wrapped around the fan-out vias (pegs below), west-to-east
    AIN15_N, AIN15_P, AIN16_P, AIN16_N; AIN15 turns south-west to C36/R12/R13, AIN16 runs south-east under
    C113 and above the SDRAM south via row to R16/R17/C37.
  * The filter crosses P and N (R12-1 P / R13-1 N sit opposite C36-1 N / C36-2 P; the same for C37 against
    R16/R17): AIN15_P takes one Top hop (41.50,4.66)->(39.65,3.85), AIN16_N one Top hop (46.15,3.35)->(43.30,3.20).
  * SDRAM around it: south via row 38.50/39.15/39.80 + eight vias 41.90..45.25 at y 4.40 (x 40.0-41.8 left to
    AIN15); upper-arm Top risers re-pitched to 38.6465 + 0.1665 k; D10/D11 heads bend around the AIN16_N via;
    D13 drops to its own via (40.60,12.75) instead of the x 38.50 column. Everything else is the committed router.
"""
import io
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_emit as RE
import sdram_route_plan as SRP          # the committed SDRAM router, not a copy

INPUTS = os.path.join(HERE, 'route_inputs.json')
OUT = os.path.join(HERE, 'coroute_plan.json')
W3 = 0.0762

# ============================================================================ XADC copper (placed first)
REMOVE = {'vias': [{'net': 'GND', 'x': 41.4, 'y': 13.8999}],
          'tracks': [{'net': 'GND', 'layer': 'Top', 'x1': 41.9, 'y1': 13.8999, 'x2': 41.4, 'y2': 13.8999}]}

ESCAPE_VIAS = [('AIN15_N', 40.6, 14.05), ('AIN16_P', 40.45, 13.4), ('AIN16_N', 41.3, 12.665)]
ESCAPE_TOP = [('AIN15_N', 'Top', [(41.6875, 13.65), (41.35, 13.72), (40.6, 14.05)]),
              ('AIN16_P', 'Top', [(41.6875, 13.15), (41.2, 13.15), (40.9, 13.09), (40.6, 13.09), (40.45, 13.4)]),
              ('AIN16_N', 'Top', [(41.6875, 12.65), (41.3, 12.665)])]

HOP15P = (41.5, 4.66)       # AIN15_P hop via; at (41.35,4.75) or (41.35,4.62) it closes D2's L3 lane
FILTER_VIAS = [('AIN15_P',) + HOP15P, ('AIN15_P', 39.65, 3.85), ('AIN16_N', 46.15, 3.35), ('AIN16_N', 43.3, 3.2)]
FILTER_POLYS = [
    ('AIN15_N', 'Bottom', [(40.45, 4.6), (40.45, 4.3), (40.45, 3.6), (40.35, 3.05)]),          # -> C36-1
    ('AIN15_N', 'Bottom', [(40.45, 4.3), (41.35, 4.3), (41.35, 3.95)]),                        # -> R13-1
    ('AIN15_P', 'Bottom', [HOP15P, (41.62, 4.26), (41.65, 4.05), (41.65, 3.05)]),              # -> C36-2
    ('AIN15_P', 'Top', [HOP15P, (39.65, 3.85)]),                                               # hop over the filter
    ('AIN15_P', 'Bottom', [(39.65, 3.85), (40.15, 3.95)]),                                     # -> R12-1
    ('AIN16_P', 'Bottom', [(45.85, 4.9), (45.85, 3.65), (45.15, 3.65), (44.95, 3.95), (43.95, 3.05)]),  # R16-1, C37-2
    ('AIN16_N', 'Bottom', [(46.016, 5.0), (46.02, 4.6), (46.15, 3.95), (46.15, 3.35)]),        # R17-1
    ('AIN16_N', 'Top', [(46.15, 3.35), (43.3, 3.2)]),                                          # hop over the filter
    ('AIN16_N', 'Bottom', [(43.3, 3.2), (42.65, 3.05)]),                                       # -> C37-1
]

# rubber band: start, pegs (cx, cy, r, side) with side +1 = peg on the left (ccw), -1 = on the right (cw), end
STEP = math.radians(10)


def _tangent(c1, rho1, c2, rho2):
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    dist = math.hypot(dx, dy)
    delta = rho2 - rho1
    if dist <= abs(delta):
        raise ValueError('no tangent %s %s' % (c1, c2))
    L = math.sqrt(dist * dist - delta * delta)
    phi = math.atan2(dy, dx) - math.atan2(delta, L)
    n = (-math.sin(phi), math.cos(phi))
    return (c1[0] - rho1 * n[0], c1[1] - rho1 * n[1]), (c2[0] - rho2 * n[0], c2[1] - rho2 * n[1])


def _elements(start, pegs, end):
    return [(tuple(start), 0.0, 0)] + [((p[0], p[1]), p[2], p[3]) for p in pegs] + [(tuple(end), 0.0, 0)]


def _nonbinding(start, pegs, end):
    els = _elements(start, pegs, end)
    tps = [_tangent(c1, r1 * s1, c2, r2 * s2) for (c1, r1, s1), (c2, r2, s2) in zip(els, els[1:])]
    worst, wi = 0, None
    for k in range(1, len(els) - 1):
        c, r, s_ = els[k]
        tin, tout = tps[k - 1][1], tps[k][0]
        a0 = math.atan2(tin[1] - c[1], tin[0] - c[0])
        a1 = math.atan2(tout[1] - c[1], tout[0] - c[0])
        sw = (a1 - a0) % (2 * math.pi) if s_ > 0 else (a0 - a1) % (2 * math.pi)
        if sw > math.pi and sw > worst:
            worst, wi = sw, k - 1
    return wi


def band(start, pegs, end):
    """shortest polyline from start to end wrapped around the pegs (a peg the band does not touch is dropped)"""
    pegs = list(pegs)
    while True:
        bad = _nonbinding(start, pegs, end)
        if bad is None:
            break
        del pegs[bad]
    els = _elements(start, pegs, end)
    tps = [_tangent(c1, r1 * s1, c2, r2 * s2) for (c1, r1, s1), (c2, r2, s2) in zip(els, els[1:])]
    pts = [tuple(start)]
    for k in range(1, len(els) - 1):
        c, r, s = els[k]
        tin, tout = tps[k - 1][1], tps[k][0]
        a0 = math.atan2(tin[1] - c[1], tin[0] - c[0])
        a1 = math.atan2(tout[1] - c[1], tout[0] - c[0])
        sweep = (a1 - a0) % (2 * math.pi) if s > 0 else -((a0 - a1) % (2 * math.pi))
        if abs(sweep) > 1.9 * math.pi:
            sweep = 0.0
        nseg = max(1, int(math.ceil(abs(sweep) / STEP - 1e-9)))
        d = sweep / nseg
        if abs(sweep) < 1e-6:
            pts.append(tin)
            continue
        rv = r / math.cos(abs(d) / 2)          # chords stay outside the peg radius
        pts.append(tin)
        for i in range(nseg):
            a = a0 + d * (i + 0.5)
            pts.append((c[0] + rv * math.cos(a), c[1] + rv * math.sin(a)))
        pts.append(tout)
    pts.append(tuple(end))
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.004:
            out.append(p)
        else:
            out[-1] = p if p == pts[-1] else out[-1]
    return [(round(x, 4), round(y, 4)) for x, y in out]


def bundle_runs():
    """the four Bottom runs down the U1 west strip, wrapped around the fan-out and SDRAM vias"""
    S = 0.1663                        # bundle pitch: 0.0762 + 0.09 + 0.0001
    CV = math.cos(math.radians(5))
    R1 = 0.3033                       # via land 0.175 + 0.09 + half track + 0.0002
    R2 = R1 / CV + S
    R3 = R2 / CV + S
    PC1 = 0.1283                      # around a pad corner
    PC2 = PC1 / CV + S
    V15N, VP16, VN16, MOAT = (40.6, 14.05), (40.45, 13.4), (41.3, 12.665), (43.4001, 13.8999)
    GNDn, D13v, VCCn, GND10 = (40.9, 13.4), (40.6, 12.75), (40.9, 11.8999), (40.9, 10.15)
    VCC94, A10, VCC79, GND69 = (40.4, 9.4), (41.4, 8.65), (40.9, 7.8999), (41.4, 6.9)
    C113a, C113b, C113c = (42.0, 7.8), (42.0, 7.5), (42.9, 7.5)
    L, R = 1, -1
    P = lambda c, r, s: (c[0], c[1], r, s)
    E15N, E15P, E16P, E16N = (40.45, 4.6), HOP15P, (45.85, 4.9), (46.016, 5.0)
    return [
        ('AIN15_P', band(MOAT, [P(GNDn, R1, L), P(V15N, R1, R), P(VP16, R1, L), P(D13v, R2, L), P(VCC94, R1, L), P(A10, R1, L),
                               P(VCC79, R2, R), P(GND69, R1, L)], E15P)),
        ('AIN15_N', [V15N] + band((40.2, 14.1), [P(VP16, R2, L), P(D13v, R3, L), P(VCC94, R2, L), P(A10, R2, L), P(VCC79, R1, R),
                                                P((40.8, 6.8), 0.0, L)], E15N)),
        ('AIN16_P', band(VP16, [P(D13v, R1, L), P(VCCn, R2, L), P(GND10, R2, L), P(VCC94, R1, R), P(A10, R1, R), P(C113a, PC2, L),
                               P(C113b, PC2, L), P(C113c, PC2, L)], E16P)),
        ('AIN16_N', band(VN16, [P(D13v, R1, R), P(VCCn, R1, L), P(GND10, R1, L), P(VCC94, R2, R), P(A10, R2, R), P(C113a, PC1, L),
                               P(C113b, PC1, L), P(C113c, PC1, L)], E16N)),
    ]


def build_xadc():
    vias = [dict(net=n, x=x, y=y) for (n, x, y) in ESCAPE_VIAS + FILTER_VIAS]
    polys = ESCAPE_TOP + FILTER_POLYS + [(n, 'Bottom', pts) for n, pts in bundle_runs()]
    tracks = []
    for net, layer, pts in polys:
        for a, b in zip(pts, pts[1:]):
            tracks.append(dict(net=net, layer=layer, x1=a[0], y1=a[1], x2=b[0], y2=b[1], width=W3))
    return dict(remove=REMOVE, vias=vias, tracks=tracks)


# ============================================================================ SDRAM around the XADC copper
SOUTH_X = [38.5, 39.15, 39.8, 41.9, 42.3786, 42.8571, 43.3357, 43.8143, 44.2929, 44.7714, 45.25]   # all at y 4.40
RISER = {'A5': 38.6465, 'A7': 38.813, 'A11': 38.9795, 'A9': 39.146, 'SDRAM-CLK': 39.3125, 'CKE': 39.479,
         'D8': 39.6455, 'UDQM': 39.812, 'D10': 39.9785, 'D11': 40.145}
HEAD_OVERRIDE = {
    'D10': {'top': [[41.2, 12.14], [40.95, 12.205], [40.9, 12.21], [39.9785, 12.21], [39.9785, 14.5]]},
    'D11': {'top': [[41.6, 12.33], [41.2, 12.33], [40.95, 12.38], [40.145, 12.38], [40.145, 14.95]]},
    'D13': {'via': [40.6, 12.75], 'top': [[41.35, 12.97], [41.15, 12.97], [40.9, 12.92]]},
}


def route_sdram(base, fixed):
    inp, missing = RE.apply_removals(base, fixed)
    assert not missing, missing
    inp = dict(inp)
    inp['vias'] = inp['vias'] + [dict(x=v['x'], y=v['y'], size=0.35, hole=0.2, net=v['net']) for v in fixed['vias']]
    inp['tracks'] = inp['tracks'] + [dict(t) for t in fixed['tracks']]
    inp['nets'] = {n: v for n, v in base['nets'].items() if v.get('cls', 'SDRAM').startswith('SDRAM')}
    SRP.inp = inp                      # the router reads its module-level inputs at call time
    SRP.STRICT_CLK[0] = True
    SRP.BAD[:] = []
    SRP.SOUTH = [(n, SOUTH_X[k], 4.4, L, pre) for k, (n, vx, vy, L, pre) in enumerate(SRP.SOUTH)]
    d = SRP.build_spec(True)
    for n, x in RISER.items():         # the Top L-head's northward riser
        top = d['nets'][n]['top']
        top[-2] = [x, top[-2][1]]
        top[-1] = [x, top[-1][1]]
    for n, o in HEAD_OVERRIDE.items():
        d['nets'][n].update(o)
    plan = SRP.route_all(d)
    if plan['unrouted'] or SRP.BAD:
        raise SystemExit('SDRAM router: unrouted %s, unrepaired corner cuts %s' % (plan['unrouted'], SRP.BAD))
    return plan


# ============================================================================ exact pad clearance
def _seg_rect_exact(seg, cx, cy, sx, sy):
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    for (px, py) in ((seg[0], seg[1]), (seg[2], seg[3])):
        if x0 <= px <= x1 and y0 <= py <= y1:
            return 0.0
    edges = [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]
    return min(RE.seg_dist(seg, e) for e in edges)


def exact_pad_check(base, plan):
    bad = []
    for t in plan['tracks']:
        seg = (t['x1'], t['y1'], t['x2'], t['y2'])
        c = RE.clearance_for(t['net'], t['layer'], base)
        pads = list(base['th_pads']) + (base['top_pads'] if t['layer'] == 'Top' else base['bottom_pads'] if t['layer'] == 'Bottom' else [])
        for p in pads:
            if p['net'] == t['net'] or abs(p['x'] - (seg[0] + seg[2]) / 2) > abs(seg[2] - seg[0]) / 2 + p['sx'] / 2 + 0.5 \
                    or abs(p['y'] - (seg[1] + seg[3]) / 2) > abs(seg[3] - seg[1]) / 2 + p['sy'] / 2 + 0.5:
                continue
            d = _seg_rect_exact(seg, p['x'], p['y'], p['sx'], p['sy']) - t['width'] / 2
            if d < c - RE.EPS:
                bad.append('track %s %s %.4f from pad %s-%s (%s)' % (t['net'], t['layer'], d, p['ref'], p['pad'], p['net']))
    return bad


def main():
    t0 = time.time()
    base = json.load(io.open(INPUTS, encoding='utf-8'))
    fixed = build_xadc()
    sd = route_sdram(base, fixed)
    strip = lambda o: {k: v for k, v in o.items() if k != 'why'}
    plan = dict(vias=[strip(v) for v in fixed['vias']] + [strip(v) for v in sd['vias']],
                tracks=[strip(t) for t in fixed['tracks']] + [strip(t) for t in sd['tracks']],
                remove=fixed['remove'],
                notes=['generator: tools/coroute_plan.py (XADC-first co-route; SDRAM by tools/sdram_route_plan.py around it)',
                       'removal: GND via (41.40,13.8999) + its Top stub from F1; F1 keeps GND via the E1 chain and (41.40,14.40)',
                       'XADC on Bottom as two 0.1663-pitch pairs down the U1 west strip; Top hops at the filter for AIN15_P and AIN16_N',
                       'SDRAM changes: south row 38.50/39.15/39.80 + 41.90..45.25 at y 4.40; risers 38.6465+0.1665k; D10/D11 heads; D13 via (40.60,12.75)'])
    json.dump(plan, io.open(OUT, 'w', encoding='utf-8'), indent=1)
    print('wrote %s: %d vias, %d tracks (XADC %d/%d, SDRAM %d/%d) in %.0f s' % (
        os.path.normpath(OUT), len(plan['vias']), len(plan['tracks']), len(fixed['vias']), len(fixed['tracks']),
        len(sd['vias']), len(sd['tracks']), time.time() - t0))
    ok = True
    exact = exact_pad_check(base, plan)
    print('exact track-to-pad clearance: %s' % ('clean' if not exact else '%d PROBLEM(S)' % len(exact)))
    for b in exact[:20]:
        print('  ', b)
    ok &= not exact
    g1 = subprocess.run([sys.executable, os.path.join(HERE, 'route_emit.py'), OUT, 'CoRoute', '--require-complete'],
                        capture_output=True, text=True)
    print('--- route_emit.py coroute_plan.json CoRoute --require-complete (exit %d)' % g1.returncode)
    print(g1.stdout.rstrip())
    ok &= g1.returncode == 0 and 'geometry and connectivity check: clean' in g1.stdout and 'nets joined end to end: 43/43' in g1.stdout
    g2 = subprocess.run([sys.executable, os.path.join(HERE, 'route_foreclosure.py'), OUT], capture_output=True, text=True)
    print('--- route_foreclosure.py coroute_plan.json (exit %d)' % g2.returncode)
    print('\n'.join(g2.stdout.rstrip().splitlines()[-1:]))
    ok &= g2.returncode == 0 and 'foreclosed by the plan(s): none' in g2.stdout
    print('BOTH GATES PASS' if ok else 'GATES FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
