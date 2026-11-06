# -*- coding: utf-8 -*-
"""SDRAM bus route plan: U3 (TSOP-II 54, Bottom) to U1 (XC7A35T CPG236) for all 39 nets.

    python tools/sdram_route_plan.py                  writes tools/sdram_route_plan.json (about 15 s)
    python tools/sdram_route_plan.py --lenient-clk    the clock vias keep only 0.10 on L3/L4 (see below)
    python tools/sdram_route_plan.py --out <plan.json> --spec-out <spec.json>
then
    python tools/route_emit.py tools/sdram_route_plan.json SdramRoute --require-complete [--write]

Reads tools/route_inputs.json only (the saved PcbDoc as tools/route_inputs.py extracted it) and
checks its own result with tools/route_emit.py before it exits (exit 1 unless clean and 39/39).

Origin: the 'perrow2' plan of the 2026-09-15 routing retry, chosen by the judge over a
negotiated-congestion A* plan (77 vias, SDRAM copper on Bottom under U1 and in the west strip,
FPGA-TDO's south via slot taken) and a lane plan (18 U3 vias outside the pocket, among the
U2 decoupling caps and U10).

Decisions (all of them live in build_spec):
  * Bottom carries ONLY the U3 pad stubs (<= 2.8 mm) into pocket vias between the pad rows;
    Bottom outside U3 stays free for the power feeds.
  * One inner layer per net, chosen so no two nets on a layer cross; the swapped U1 exit
    orders (A9/A11, CKE/CLK, UDQM/D8, A2/A3, A0/A10/BS1, D1/D2) go on different layers.
  * U1-side vias are placed before any track: south face = a flat row at y 4.40
    (x 38.50..45.25, 0.675 pitch) fed by 3 mil Top fans; west face lower arm (south-row nets)
    = A2 A3 BS1 A0 BS0 staircase at x 38.6..40.25; west face upper arm (north-row nets) = one
    column at x 38.50, y 10.60..15.40, Top heads as non-crossing L shapes turning north at
    x 38.81 + 0.175 k; north face D14 (47.9,17.15) / D15 (48.9,16.8); the 10 moat-via nets
    need no new U1-side via.
  * Per-net corridor rectangles on L3/L4, a keep-out band in front of each U3 row that a
    lane may enter only at its own pad, pocket-via boxes where U2 / LD3..LD5 Top pads leave
    one legal spot, and a routing order per stack so every lane hugs the right neighbour.
  * 25 um grid A* over Top / L3 / L4 / Bottom, then exact segment checks and shortcuts.
  * SDRAM-CLK: M1 -> Top 3 mil head (y 10.90, north at x 39.51) -> via (38.85, 12.70), stepped
    east out of the x 38.50 column -> L4 -> pocket via (27.125, 16.10) -> Bottom to U3 pad 38.
    Besides its own 0.20 on L3/L4 (Clearance_SDRAM_CLK), both clock vias keep 0.20 to every
    foreign object on every layer (via pitch 0.55; CKE's and UDQM's pocket via boxes moved to
    make room), so the plan stays DRC-clean even if Altium's OnLayer('L3-SIG') scope also
    matches through vias.  --lenient-clk drops that and reproduces the perrow2 plan exactly.
"""
import io, json, math, os, sys, time, heapq
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_emit as RE

INPUTS = os.path.join(HERE, 'route_inputs.json')
OUT = os.path.join(HERE, 'sdram_route_plan.json')
inp = json.load(io.open(INPUTS, encoding='utf-8'))
STRICT_CLK = [True]
CLK = 'SDRAM-CLK'
CLK_GAP = 0.20

# south face: (net, U1-side via x, y, inner layer, Top pre-drop points after the stub end)
SOUTH = [
    ('SDRAM-CS#', 38.5, 4.4, 'L4-SIG', [(42.4, 6.55)]),
    ('RAS#', 39.175, 4.4, 'L3-SIG', [(42.65, 6.55)]),
    ('CAS#', 39.85, 4.4, 'L4-SIG', [(42.9, 6.55)]),
    ('WE#', 40.525, 4.4, 'L3-SIG', [(43.15, 6.55)]),
    ('LDQM', 41.2, 4.4, 'L4-SIG', [(43.4, 6.55)]),
    ('D6', 41.875, 4.4, 'L3-SIG', [(43.65, 6.55)]),
    ('D5', 42.55, 4.4, 'L4-SIG', [(43.825, 7.15), (43.825, 6.55)]),
    ('D3', 43.225, 4.4, 'L3-SIG', [(44.475, 7.15), (44.475, 6.55)]),
    ('D1', 43.9, 4.4, 'L4-SIG', [(44.65, 6.55)]),
    ('D2', 44.575, 4.4, 'L3-SIG', [(44.9, 6.55)]),
    ('D0', 45.25, 4.4, 'L4-SIG', [(45.15, 6.55)]),
]
SOUTH_ORDER = [s[0] for s in SOUTH]


def build_spec(strict_clk):
    """every design decision of the plan: U1-side vias, layers, corridors, via boxes, order"""
    nets = {}
    for (n, vx, vy, L, pre) in SOUTH:
        nets[n] = dict(via=[vx, vy], layers=[L], top_pre=[list(p) for p in pre])
    L3, L4 = 'L3-SIG', 'L4-SIG'
    UNDER = [[17.3, 3.6, 46.5, 9.6]]
    for n in SOUTH_ORDER:
        px = inp['nets'][n]['u3'][0]['x']
        nets[n]['allow'] = [[17.3, 3.6, 46.5, 6.45], [px - 0.75, 3.6, px + 0.75, 9.6]]
        nets[n]['why'] = 'south face: Top fan to a flat via row at y 4.40, lane under the U3 south row, rises at its pad'

    def net(n, via=None, layers=(L3,), pre=None, top=None, **kw):
        d = dict(layers=list(layers))
        if via: d['via'] = list(via)
        if pre: d['top_pre'] = [list(p) for p in pre]
        if top is not None: d['top'] = [list(p) for p in top]
        d.update(kw)
        nets[n] = d

    # ---- west face, lower arm: south-row nets, lanes WSW into the pocket side, northern vias further west
    LOW = [[17.3, 6.8, 40.6, 11.0]]
    lower = [('A2', L4, (38.6, 8.95)), ('A3', L3, (39.15, 8.7)), ('BS1', L4, (39.75, 8.25)), ('A0', L3, (40.25, 8.1)), ('BS0', L3, (40.2, 7.55))]
    for n, L, v in lower:
        net(n, via=v, layers=(L,), allow=LOW, why='west face lower arm (south row, pocket side)')
    nets['BS0']['top'] = [[40.9, 7.56], [40.5, 7.56]]
    nets['A0']['top'] = [[41.35, 8.15], [40.9, 8.21], [40.5, 8.21]]
    nets['BS1']['top'] = [[41.7, 8.33], [41.4, 8.33], [40.9, 8.38], [40.5, 8.38], [40.0, 8.45]]
    nets['A3']['top'] = [[41.7, 8.92], [41.4, 8.96], [40.9, 8.93], [40.5, 8.9]]
    nets['A2']['top'] = [[41.4, 9.14], [40.9, 9.12], [40.5, 9.08], [40.1, 9.08], [39.8, 9.2]]
    # ---- west face, upper arm: north-row nets in one via column at x 38.50 (lanes WNW), each Top head an L:
    # west along its exit line, north at t_k = 38.81 + 0.175 k (northern heads turn further east), west into the via
    UP = [[17.3, 9.7, 41.0, 19.2]]
    upper = [('A5', L3), ('A7', L3), ('A11', L4), ('A9', L3), ('SDRAM-CLK', L4), ('CKE', L3), ('D8', L4), ('UDQM', L3),
             ('D10', L3), ('D11', L3), ('D13', L3)]
    COLX = 38.5
    Y = {'A5': 10.6, 'A7': 11.05, 'A11': 11.5, 'A9': 11.95, 'SDRAM-CLK': 12.65, 'CKE': 13.15, 'D8': 13.6, 'UDQM': 14.05,
         'D10': 14.5, 'D11': 14.95, 'D13': 15.4}
    EXIT = {'A5': [[40.9, 9.65], [40.4, 9.71]], 'A7': [[41.4, 9.87], [40.9, 9.83], [40.4, 9.88]]}
    for nn, yy in {'A11': 10.46, 'A9': 10.68, 'SDRAM-CLK': 10.9, 'CKE': 11.13, 'D8': 11.36, 'UDQM': 11.59,
                   'D10': 12.21, 'D11': 12.43, 'D13': 12.9}.items():
        EXIT[nn] = [[41.5, yy], [40.9, yy]]
    for k, (n, L) in enumerate(upper):
        t = round(38.81 + 0.175 * k, 4)
        s_ = EXIT[n][-1][1]
        net(n, via=(COLX, Y[n]), layers=(L,), allow=UP, why='west face upper arm (north row, via column x 38.50)')
        nets[n]['top'] = EXIT[n] + [[t, s_], [t, Y[n]]]
    # north pocket via windows forced by LD3/LD4/LD5 (x 22.1..24.6) and U2's west column (x 25.0..26.55)
    nets['A7']['bottom_x'] = [20.5, 21.3]
    nets['A9']['bottom_x'] = [21.3, 22.8]
    nets['A11']['bottom_x'] = [23.2, 23.6]
    nets['SDRAM-CLK']['bottom_x'] = [25.9, 27.4]
    nets['CKE']['bottom_x'] = [25.1, 27.4]
    nets['UDQM']['bottom_x'] = [26.7, 27.6]
    # ---- moat via nets
    def win(n, lo=None, hi=None):
        """the pocket-via window column of net n (inner layers)"""
        u = inp['nets'][n]['u3'][0]
        bx = nets[n].get('bottom_x', [u['x'] - 0.6, u['x'] + 0.6])
        x0, x1 = min(bx[0], u['x']) - 0.5, max(bx[1], u['x']) + 0.5
        if u['y'] < 10:
            return [x0, 6.8 if lo is None else lo, x1, 11.0 if hi is None else hi]
        return [x0, 13.0 if lo is None else lo, x1, 17.6 if hi is None else hi]

    net('A4', layers=(L4,), allow=[[41.4, 8.9, 43.6, 10.05], [40.7, 8.55, 41.6, 9.35], [40.0, 8.55, 40.75, 8.76], [38.3, 8.6, 40.1, 9.7], [36.1, 10.715, 36.22, 16.9], [36.2, 10.67, 36.32, 16.9], [36.3, 10.611, 36.42, 16.9], [36.4, 10.551, 36.52, 16.9], [36.5, 10.492, 36.62, 16.9], [36.6, 10.432, 36.72, 16.9], [36.7, 10.372, 36.82, 16.9], [36.8, 10.313, 36.92, 16.9], [36.9, 10.253, 37.02, 16.9], [37.0, 10.194, 37.12, 16.9], [37.1, 10.134, 37.22, 16.9], [37.2, 10.074, 37.32, 16.9], [37.3, 10.015, 37.42, 16.9], [37.4, 9.955, 37.52, 16.9], [37.5, 9.896, 37.62, 16.9], [37.6, 9.836, 37.72, 16.9], [37.7, 9.776, 37.82, 16.9], [37.8, 9.717, 37.92, 16.9], [37.9, 9.657, 38.02, 16.9], [38.0, 9.598, 38.12, 16.9], [38.1, 9.538, 38.22, 16.9], [38.2, 9.478, 38.32, 16.9], [38.3, 9.419, 38.42, 16.9], [38.4, 9.359, 38.52, 16.9], [38.5, 9.3, 38.62, 16.9], [38.6, 9.24, 38.72, 16.9], [17.3, 10.715, 36.15, 16.9]],
        why='moat via: west through the A10/40.40 gap (south lane), the apex between the arms')
    net('A6', layers=(L4,), allow=[[41.4, 9.2, 43.6, 10.6], [40.7, 8.95, 41.6, 9.5], [40.05, 8.9, 40.75, 9.95], [38.3, 9.25, 40.15, 9.95], [36.1, 11.025, 36.22, 16.9], [36.2, 10.98, 36.32, 16.9], [36.3, 10.921, 36.42, 16.9], [36.4, 10.861, 36.52, 16.9], [36.5, 10.802, 36.62, 16.9], [36.6, 10.742, 36.72, 16.9], [36.7, 10.682, 36.82, 16.9], [36.8, 10.623, 36.92, 16.9], [36.9, 10.563, 37.02, 16.9], [37.0, 10.504, 37.12, 16.9], [37.1, 10.444, 37.22, 16.9], [37.2, 10.384, 37.32, 16.9], [37.3, 10.325, 37.42, 16.9], [37.4, 10.265, 37.52, 16.9], [37.5, 10.206, 37.62, 16.9], [37.6, 10.146, 37.72, 16.9], [37.7, 10.086, 37.82, 16.9], [37.8, 10.027, 37.92, 16.9], [37.9, 9.967, 38.02, 16.9], [38.0, 9.908, 38.12, 16.9], [38.1, 9.848, 38.22, 16.9], [38.2, 9.788, 38.32, 16.9], [38.3, 9.729, 38.42, 16.9], [38.4, 9.669, 38.52, 16.9], [38.5, 9.61, 38.62, 16.9], [38.6, 9.55, 38.72, 16.9], [17.3, 11.025, 36.15, 16.9]],
        why='moat via: west through the A10/40.40 gap (north lane), the apex between the arms')
    net('A8', layers=(L4,), allow=[[41.4, 9.8, 43.6, 11.1], [40.3, 9.75, 41.5, 10.2], [38.3, 9.8, 40.6, 10.3], [36.1, 11.335, 36.22, 16.9], [36.2, 11.29, 36.32, 16.9], [36.3, 11.231, 36.42, 16.9], [36.4, 11.171, 36.52, 16.9], [36.5, 11.112, 36.62, 16.9], [36.6, 11.052, 36.72, 16.9], [36.7, 10.992, 36.82, 16.9], [36.8, 10.933, 36.92, 16.9], [36.9, 10.873, 37.02, 16.9], [37.0, 10.814, 37.12, 16.9], [37.1, 10.754, 37.22, 16.9], [37.2, 10.694, 37.32, 16.9], [37.3, 10.635, 37.42, 16.9], [37.4, 10.575, 37.52, 16.9], [37.5, 10.516, 37.62, 16.9], [37.6, 10.456, 37.72, 16.9], [37.7, 10.396, 37.82, 16.9], [37.8, 10.337, 37.92, 16.9], [37.9, 10.277, 38.02, 16.9], [38.0, 10.218, 38.12, 16.9], [38.1, 10.158, 38.22, 16.9], [38.2, 10.098, 38.32, 16.9], [38.3, 10.039, 38.42, 16.9], [38.4, 9.979, 38.52, 16.9], [38.5, 9.92, 38.62, 16.9], [38.6, 9.86, 38.72, 16.9], [17.3, 11.335, 36.15, 16.9]],
        why='moat via: west through the 40.40/40.90 gap, the apex between the arms')
    nets['A8']['bottom_x'] = [21.3, 22.0]
    net('A1', layers=(L3,), allow=[[41.5, 8.5, 43.6, 9.5], [40.3, 8.7, 41.6, 9.3], [39.3, 8.1, 40.6, 8.95], [38.6, 6.8, 39.5, 8.6], [17.3, 6.8, 38.7, 11.5]],
        why='moat via: L3, west through the A10/40.40 gap and the A3|BS1 slot (A10 takes the same slot on L4)')
    net('A10', layers=(L4,), allow=[[40.95, 8.3, 41.6, 8.95], [39.9, 8.35, 41.0, 8.47], [39.6, 8.35, 40.0, 9.0], [39.1, 8.0, 39.9, 9.0], [38.6, 6.8, 39.5, 8.5], [17.3, 6.8, 38.7, 11.5]], why='outside via: slot A3|BS1 in the lower arm')
    for n, ytop in (('A2', 9.45), ('A3', 9.1), ('BS1', 8.7), ('A0', 8.45), ('BS0', 7.95)):
        nets[n]['allow'] = [[38.3, 6.8, 40.6, ytop], [17.3, 6.8, 38.5, 11.5]]
    nets['BS0']['allow'] = [[39.9, 6.8, 40.6, 7.9], [38.3, 6.8, 40.0, 7.4], [17.3, 6.8, 38.5, 11.5]]
    nets['A0']['allow'] = [[40.0, 6.8, 40.6, 8.45], [38.3, 6.8, 40.1, 7.9], [17.3, 6.8, 38.5, 11.5]]
    nets['BS1']['allow'] = [[39.55, 6.8, 40.6, 8.4], [38.9, 6.8, 39.65, 7.95], [17.3, 6.8, 39.0, 11.5]]
    nets['A2']['allow'] = [[38.3, 8.7, 40.6, 9.3], [17.3, 6.8, 38.7, 11.5]]
    GAP = [[41.5, 12.2, 43.6, 15.3], [38.0, 14.5, 41.0, 16.1], [17.3, 14.5, 41.0, 16.9]]
    net('D9', layers=(L4,), allow=[[42.0, 12.2, 43.6, 12.65], [41.6, 12.2, 42.35, 14.84], [40.9, 14.5, 42.35, 14.84], [38.0, 14.5, 41.0, 15.8], [17.3, 14.5, 41.0, 15.78]], why='moat via: north in the channel, west through the 14.4/15.4 gap of the 41.40 column')
    net('D12', layers=(L4,), allow=[[42.6, 12.7, 43.6, 13.1], [42.6, 12.7, 43.1, 15.3], [40.9, 14.95, 43.1, 15.3]] + GAP[1:], why='moat via: north in the channel, west through the 14.4/15.4 gap of the 41.40 column')
    net('A12', layers=(L3,), allow=[[40.3, 10.2, 43.6, 11.9], [17.3, 9.7, 41.0, 16.9]], bottom_x=[23.2, 24.4],
        why='moat via: west through the fence, slot between A9 and CLK')
    CORNER = [[41.5, 7.2, 44.2, 9.2], [36.3, 6.8, 41.6, 7.9], [17.3, 7.1, 38.8, 11.5]]
    net('D7', layers=(L4,), allow=[[41.1, 7.45, 43.6, 9.2], [40.5, 7.2, 41.6, 7.9], [39.6, 6.8, 40.6, 7.2], [36.3, 6.8, 39.7, 7.9], CORNER[2]], band_x1=36.5, why='moat via: south-west corner under BS0, pocket side')
    net('D4', layers=(L4,), allow=[[43.7, 7.2, 44.2, 9.2], [41.1, 7.2, 44.2, 7.3], [40.6, 6.8, 41.6, 7.3], [39.3, 6.7, 40.75, 6.9], [40.6, 6.7, 41.1, 7.3], [36.3, 6.7, 39.4, 7.6], CORNER[2]], band_x1=36.5, why='moat via: south-west corner under BS0, pocket side')
    for n, _ in upper:
        nets[n]['allow'] = [[17.3, 9.7, 41.0, 16.9]]
    for n in ('A2', 'A3', 'BS1', 'A0', 'BS0', 'A1', 'A10', 'D7', 'D4'):
        nets[n]['band_x1'] = 35.85
    # every pocket-side net may use its own window column
    for n in list(nets):
        if n in SOUTH_ORDER or 'allow' not in nets[n]:
            continue
        nets[n]['allow'] = nets[n]['allow'] + [win(n)]
    nets['UDQM']['via_box'] = [[26.85, 16.45, 27.05, 16.67]]
    nets['SDRAM-CLK']['via_box'] = [[26.85, 16.0, 27.05, 16.25]]
    nets['CKE']['via_box'] = [[26.85, 15.5, 27.05, 15.8]]
    nets['A11']['via_box'] = [[23.25, 16.45, 23.35, 16.67]]
    nets['A12']['via_box'] = [[23.25, 15.9, 23.35, 16.25]]
    nets['A8']['via_box'] = [[21.4, 16.45, 21.84, 16.67]]
    nets['A9']['via_box'] = [[21.4, 15.9, 21.84, 16.25]]
    nets['A7']['via_box'] = [[20.6, 16.3, 21.1, 16.67]]
    for n_ in ('UDQM', 'SDRAM-CLK', 'CKE'):
        nets[n_]['bottom_x'] = [25.0, 27.1]
    nets['D0']['via_box'] = [[37.35, 7.0, 38.05, 7.35]]
    nets['A9']['allow'] = [[17.3, 9.7, 41.0, 13.62], [20.8, 13.0, 23.3, 17.6]]
    nets['A11']['block'] = [['L4-SIG', 22.7, 13.0, 23.7, 16.3]]
    if strict_clk:
        # the clock's two vias keep 0.20 to everything: its U1-side via steps east out of the
        # x 38.50 column (0.57 from CKE's via, 0.83 from A9's, so A12's L3 slot keeps 0.20 / 0.10)
        # and its pocket via sits >= 0.55 from CKE's and UDQM's and 0.20 clear of U2's west pads
        nets['SDRAM-CLK']['via'] = [38.85, 12.7]
        nets['SDRAM-CLK']['top'] = EXIT['SDRAM-CLK'] + [[39.51, 10.9], [39.51, 12.7]]
        nets['SDRAM-CLK']['via_box'] = [[27.05, 15.95, 27.3, 16.2]]
        nets['SDRAM-CLK']['bottom_x'] = [25.0, 27.35]
        nets['CKE']['via_box'] = [[26.85, 15.45, 26.95, 15.6]]
        nets['UDQM']['via_box'] = [[26.85, 16.6, 27.05, 16.665]]
    # ---- north face
    NORTH = [[35.0, 15.8, 49.5, 19.2]]
    net('D14', via=(47.9, 17.15), layers=(L4,), top=[(48.325, 16.725)], bottom_x=(35.6, 36.2), allow=NORTH, why='north face')
    net('D15', via=(48.9, 16.8), layers=(L4,), top=[], bottom_x=(37.9, 39.0), allow=NORTH, why='north face')

    head_order = SOUTH_ORDER + ['A2', 'A3', 'BS1', 'A0', 'BS0'] + [n for n, _ in upper]
    order = SOUTH_ORDER + ['D14', 'D15', 'D4', 'D7', 'BS0', 'BS1', 'A0', 'A10', 'A1', 'A3', 'A2',
                          'D9', 'D12'] + [n for n, _ in reversed(upper)] + ['A12', 'A8', 'A6', 'A4']
    assert sorted(order) == sorted(inp['nets']), set(inp['nets']) ^ set(order)
    return dict(order=order, head_order=head_order, nets=nets)


G = 0.025
X0, Y0, X1, Y1 = 17.0, 3.45, 52.5, 19.4
LF = inp['land_field']
NX = int(round((X1 - X0) / G)) + 1
NY = int(round((Y1 - Y0) / G)) + 1
M = float(os.environ.get('GRID_M', '0.003'))   # grid safety margin; corner cuts are repaired exactly afterwards
LAYERS = ['Top', 'L3-SIG', 'L4-SIG', 'Bottom']
W = {'Top': 0.0762, 'L3-SIG': 0.125, 'L4-SIG': 0.125, 'Bottom': 0.125}
FACTOR = {'Top': 2.2, 'Bottom': 1.5}
VIA_COST = 0.5
# phase 2: Bottom is a short stub straight out of the U3 pad into the pocket
BOTTOM_HALF = float(os.environ.get('BOTTOM_HALF', '0.6'))
BOTTOM_S_YMAX = 9.45   # U2's south Top pads (y 7.125..8.675, x 27.6..35.4) push those pocket vias to y >= 8.94
BAND_HALF = 0.7
BOTTOM_N_YMIN = 13.8   # LD3/LD5/BTN Top pads push some north-row pocket vias down
VIA_LAND = 0.35

# ---------------------------------------------------------------- obstacles
vias = [dict(v) for v in inp['vias']]                     # x y net
tracks = [dict(t) for t in inp['tracks']]                 # layer net x1 y1 x2 y2 width
pads = {'Top': inp['top_pads'], 'Bottom': inp['bottom_pads']}
NETS = inp['nets']
SD = set(NETS)


def clr(net, layer):
    return RE.clearance_for(net, layer, inp)


def strict_pair(net, other):
    """True when a via of one of the two (different) nets is the clock's and the strict reading
    of Clearance_SDRAM_CLK is on: that via keeps 0.20 to the other's copper on every layer"""
    return STRICT_CLK[0] and net != other and CLK in (net, other)


def to_ix(x):
    return int(round((x - X0) / G))


def to_iy(y):
    return int(round((y - Y0) / G))


def xy(ix, iy):
    return (round(X0 + ix * G, 4), round(Y0 + iy * G, 4))


def mark_circle(arr, x, y, r):
    ix0, ix1 = max(0, to_ix(x - r) - 1), min(NX - 1, to_ix(x + r) + 1)
    iy0, iy1 = max(0, to_iy(y - r) - 1), min(NY - 1, to_iy(y + r) + 1)
    if ix0 > ix1 or iy0 > iy1:
        return
    ys = (Y0 + np.arange(iy0, iy1 + 1) * G)[:, None]
    xs = (X0 + np.arange(ix0, ix1 + 1) * G)[None, :]
    arr[iy0:iy1 + 1, ix0:ix1 + 1] |= (xs - x) ** 2 + (ys - y) ** 2 <= r * r


def mark_seg(arr, x1, y1, x2, y2, r):
    ix0, ix1 = max(0, to_ix(min(x1, x2) - r) - 1), min(NX - 1, to_ix(max(x1, x2) + r) + 1)
    iy0, iy1 = max(0, to_iy(min(y1, y2) - r) - 1), min(NY - 1, to_iy(max(y1, y2) + r) + 1)
    if ix0 > ix1 or iy0 > iy1:
        return
    ys = (Y0 + np.arange(iy0, iy1 + 1) * G)[:, None]
    xs = (X0 + np.arange(ix0, ix1 + 1) * G)[None, :]
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        d2 = (xs - x1) ** 2 + (ys - y1) ** 2
    else:
        t = np.clip(((xs - x1) * dx + (ys - y1) * dy) / L2, 0.0, 1.0)
        d2 = (xs - (x1 + t * dx)) ** 2 + (ys - (y1 + t * dy)) ** 2
    arr[iy0:iy1 + 1, ix0:ix1 + 1] |= d2 <= r * r


def mark_rect(arr, cx, cy, sx, sy, r):
    ix0, ix1 = max(0, to_ix(cx - sx / 2 - r) - 1), min(NX - 1, to_ix(cx + sx / 2 + r) + 1)
    iy0, iy1 = max(0, to_iy(cy - sy / 2 - r) - 1), min(NY - 1, to_iy(cy + sy / 2 + r) + 1)
    if ix0 > ix1 or iy0 > iy1:
        return
    ys = (Y0 + np.arange(iy0, iy1 + 1) * G)[:, None]
    xs = (X0 + np.arange(ix0, ix1 + 1) * G)[None, :]
    ddx = np.maximum(np.abs(xs - cx) - sx / 2, 0.0)
    ddy = np.maximum(np.abs(ys - cy) - sy / 2, 0.0)
    arr[iy0:iy1 + 1, ix0:ix1 + 1] |= ddx ** 2 + ddy ** 2 <= r * r


RESERVED = []   # fictional Top lanes of not-yet-routed nets: dicts like tracks (layer Top)


def track_block(net, layer):
    """cells where a track centre of `net` on `layer` would violate clearance"""
    b = np.zeros((NY, NX), dtype=bool)
    w = W[layer]
    c = clr(net, layer)
    for v in vias:
        if v['net'] != net:
            cv = max(c, CLK_GAP) if (v['net'] == CLK and strict_pair(net, CLK)) else c
            mark_circle(b, v['x'], v['y'], cv + VIA_LAND / 2 + w / 2 + M)
    for t in tracks + RESERVED + BLOCKERS:
        if t['layer'] == layer and t['net'] != net:
            mark_seg(b, t['x1'], t['y1'], t['x2'], t['y2'], max(c, clr(t['net'], layer)) + w / 2 + t['width'] / 2 + M)
    if layer in pads:
        for p in pads[layer]:
            if p['net'] != net:
                mark_rect(b, p['x'], p['y'], p['sx'], p['sy'], c + w / 2 + M)
    for (L, x0, y0, x1, y1) in PER_NET_BLOCK.get(net, []):
        if L == layer:
            mark_rect(b, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, 0.0)
    if layer in ('L3-SIG', 'L4-SIG') and PER_NET_ALLOW.get(net):
        ok = np.zeros((NY, NX), dtype=bool)
        for (x0, y0, x1, y1) in PER_NET_ALLOW[net]:
            ok[max(0, to_iy(y0)):to_iy(y1) + 1, max(0, to_ix(x0)):to_ix(x1) + 1] = True
        b |= ~ok
    return b


def via_block(net):
    b = np.zeros((NY, NX), dtype=bool)
    for v in vias:
        pitch = VIA_LAND + CLK_GAP if strict_pair(net, v['net']) else RE.VIA_PITCH
        mark_circle(b, v['x'], v['y'], max(pitch, RE.VIA_PITCH) + M)
    for L in pads:
        for p in pads[L]:
            # own-net pads too: a via never sits on or beside an SMD pad (pads cannot take vias)
            gap = CLK_GAP if (net == CLK and strict_pair(net, p['net'])) else 0.09
            mark_rect(b, p['x'], p['y'], p['sx'], p['sy'], gap + VIA_LAND / 2 + M)
    for t in tracks + RESERVED:
        if t['net'] != net:
            cl = clr(t['net'], t['layer'])
            if strict_pair(net, t['net']) and net == CLK:
                cl = max(cl, CLK_GAP)
            mark_seg(b, t['x1'], t['y1'], t['x2'], t['y2'], cl + t['width'] / 2 + VIA_LAND / 2 + M)
    # no new via inside U1's land field
    mark_rect(b, (LF['x0'] + LF['x1']) / 2, (LF['y0'] + LF['y1']) / 2, LF['x1'] - LF['x0'], LF['y1'] - LF['y0'], 0.0)
    if net in VIA_XRANGE:
        lo, hi = VIA_XRANGE[net]
        b[:, :to_ix(lo)] = True
        b[:, to_ix(hi) + 1:] = True
    if VIA_BOX.get(net):
        ok = np.zeros((NY, NX), dtype=bool)
        for (x0, y0, x1, y1) in VIA_BOX[net]:
            ok[max(0, to_iy(y0)):to_iy(y1) + 1, max(0, to_ix(x0)):to_ix(x1) + 1] = True
        b |= ~ok
    return b



# ------------------------------------------------------------ exact checks
def seg_ok(net, layer, seg, eps=0.0005, why=None):
    w = W[layer]
    c = clr(net, layer)
    for v in vias:
        if v['net'] == net:
            continue
        d = RE.seg_dist(seg, (v['x'], v['y'], v['x'], v['y'])) - w / 2 - VIA_LAND / 2
        cv = max(c, CLK_GAP) if (v['net'] == CLK and strict_pair(net, CLK)) else c
        if d < cv + eps:
            if why is not None:
                why.append('via %s (%.3f,%.3f) d=%.4f' % (v['net'], v['x'], v['y'], d))
            return False
    if layer in ('L3-SIG', 'L4-SIG') and PER_NET_ALLOW.get(net):
        n_ = max(16, int(math.hypot(seg[2] - seg[0], seg[3] - seg[1]) / 0.02))
        for k_ in range(n_ + 1):
            px_ = seg[0] + (seg[2] - seg[0]) * k_ / n_
            py_ = seg[1] + (seg[3] - seg[1]) * k_ / n_
            if not any(x0 - 0.013 <= px_ <= x1 + 0.013 and y0 - 0.013 <= py_ <= y1 + 0.013 for (x0, y0, x1, y1) in PER_NET_ALLOW[net]):
                if why is not None:
                    why.append('outside corridor')
                return False
    for (L, x0, y0, x1, y1) in PER_NET_BLOCK.get(net, []):
        if L == layer and RE.seg_rect(seg, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 0.002, y1 - y0 - 0.002) < 1e-9:
            if why is not None:
                why.append('per-net block %s' % ((L, x0, y0, x1, y1),))
            return False
    if layer in pads:
        for p in pads[layer]:
            if p['net'] == net:
                continue
            d = RE.seg_rect(seg, p['x'], p['y'], p['sx'], p['sy']) - w / 2
            if d < c + eps:
                if why is not None:
                    why.append('pad %s-%s (%s) d=%.4f' % (p['ref'], p['pad'], p['net'], d))
                return False
    for t in tracks + RESERVED:
        if t['layer'] != layer or t['net'] == net:
            continue
        d = RE.seg_dist(seg, (t['x1'], t['y1'], t['x2'], t['y2'])) - w / 2 - t['width'] / 2
        if d < max(c, clr(t['net'], layer)) + eps:
            if why is not None:
                why.append('track %s (%.3f,%.3f)-(%.3f,%.3f) d=%.4f' % (t['net'], t['x1'], t['y1'], t['x2'], t['y2'], d))
            return False
    return True


# ------------------------------------------------------------------ regions
def make_region(row):
    def top(x, y):
        return x >= 38.3

    def inner(x, y):
        return x >= 17.3 and 3.6 <= y <= 19.2

    def bottom(x, y):
        # Bottom only for the stub: from the pad centre into the pocket (or east of the rows)
        if x > 40.6:
            return False
        if row == 'S':
            return 6.16 <= y <= BOTTOM_S_YMAX
        return BOTTOM_N_YMIN <= y <= 17.54
    return {'Top': top, 'L3-SIG': inner, 'L4-SIG': inner, 'Bottom': bottom}


def region_mask(fn):
    ys = (Y0 + np.arange(NY) * G)[:, None]
    xs = (X0 + np.arange(NX) * G)[None, :]
    return np.vectorize(fn)(np.broadcast_to(xs, (NY, NX)), np.broadcast_to(ys, (NY, NX)))


REGION_CACHE = {}


def region_masks(row):
    if row not in REGION_CACHE:
        r = make_region(row)
        REGION_CACHE[row] = {L: region_mask(r[L]) for L in LAYERS}
    return REGION_CACHE[row]


# --------------------------------------------------------------------- A*
DEBUG = {}
ALLOW_TOP_HOP = [False]



DIRS = [(1, 0, G), (-1, 0, G), (0, 1, G), (0, -1, G),
        (1, 1, G * math.sqrt(2)), (1, -1, G * math.sqrt(2)), (-1, 1, G * math.sqrt(2)), (-1, -1, G * math.sqrt(2))]


def astar(net, sources, target, layers_allowed, factors, row, bbox, no_via=False):
    """sources: list of (layer, x, y); target: (layer, x, y). returns list of (layer, ix, iy)"""
    masks = region_masks(row)
    x_lo, x_hi = bbox
    free = {}
    px = NETS[net]['u3'][0]['x']
    blo, bhi = BOTTOM_X.get(net, (px - BOTTOM_HALF, px + BOTTOM_HALF))
    blo, bhi = min(blo, px - 0.2), max(bhi, px + 0.2)
    for L in layers_allowed:
        f = ~track_block(net, L) & masks[L]
        ixs = np.arange(NX)
        f[:, (ixs < to_ix(x_lo)) | (ixs > to_ix(x_hi))] = False
        if L == 'Bottom':
            f[:, (ixs < to_ix(blo)) | (ixs > to_ix(bhi))] = False
        free[L] = f
    vb = ~via_block(net)
    if no_via:
        vb[:] = False
    DEBUG['free'] = free
    DEBUG['via'] = vb
    lay_idx = {L: i for i, L in enumerate(layers_allowed)}
    nl = len(layers_allowed)
    N = NX * NY
    free_b = [free[L].reshape(-1).tobytes() for L in layers_allowed]
    via_b = vb.reshape(-1).tobytes()
    fac = [factors.get(L, 1.0) for L in layers_allowed]
    g = [None] * (nl * N)
    parent = {}
    tx, ty = to_ix(target[1]), to_iy(target[2])
    tstate = lay_idx[target[0]] * N + ty * NX + tx
    # the end cells themselves may sit inside the grid safety margin of a neighbour that the exact
    # check accepts (pre-runs at exactly 0.09): open them, the exact post-check still applies
    for (L, x, y) in list(sources) + [target]:
        if L in lay_idx and region_masks(row)[L][to_iy(y), to_ix(x)]:
            fb_ = bytearray(free_b[lay_idx[L]])
            fb_[to_iy(y) * NX + to_ix(x)] = 1
            free_b[lay_idx[L]] = bytes(fb_)
    if not free_b[lay_idx[target[0]]][ty * NX + tx]:
        print('   target cell blocked for', net, target)
        return None, 0
    heap = []
    for (L, x, y) in sources:
        if L not in lay_idx:
            continue
        ix, iy = to_ix(x), to_iy(y)
        s = lay_idx[L] * N + iy * NX + ix
        if not free_b[lay_idx[L]][iy * NX + ix]:
            print('   source cell blocked for', net, L, x, y)
            continue
        g[s] = 0.0
        parent[s] = -1
        h = math.hypot((ix - tx) * G, (iy - ty) * G)
        heapq.heappush(heap, (h, 0.0, s))
    closed = bytearray(nl * N)
    pops = 0
    while heap:
        f, gc, s = heapq.heappop(heap)
        if closed[s]:
            continue
        closed[s] = 1
        pops += 1
        if s == tstate:
            path = []
            while s != -1:
                l, r = divmod(s, N)
                iy, ix = divmod(r, NX)
                path.append((layers_allowed[l], ix, iy))
                s = parent[s]
            path.reverse()
            return path, pops
        l, r = divmod(s, N)
        iy, ix = divmod(r, NX)
        fb = free_b[l]
        fl = fac[l]
        for dx, dy, dl in DIRS:
            nx_, ny_ = ix + dx, iy + dy
            if nx_ < 0 or ny_ < 0 or nx_ >= NX or ny_ >= NY:
                continue
            ci = ny_ * NX + nx_
            if not fb[ci]:
                continue
            ns = l * N + ci
            if closed[ns]:
                continue
            ng = gc + dl * fl
            og = g[ns]
            if og is None or ng < og:
                g[ns] = ng
                parent[ns] = s
                h = math.hypot((nx_ - tx) * G, (ny_ - ty) * G)
                heapq.heappush(heap, (ng + h, ng, ns))
        if via_b[r] and layers_allowed[l] != 'Bottom':
            for l2 in range(nl):
                if l2 == l or not free_b[l2][r]:
                    continue
                # Top only at the U1 end, Bottom only as the final stub: Top->inner, inner->inner, inner->Bottom
                if (layers_allowed[l2] == 'Top' and not ALLOW_TOP_HOP[0]) or (layers_allowed[l] == 'Top' and layers_allowed[l2] == 'Bottom'):
                    continue
                ns = l2 * N + r
                if closed[ns]:
                    continue
                ng = gc + VIA_COST
                og = g[ns]
                if og is None or ng < og:
                    g[ns] = ng
                    parent[ns] = s
                    h = math.hypot((ix - tx) * G, (iy - ty) * G)
                    heapq.heappush(heap, (ng + h, ng, ns))
    return None, pops


# ------------------------------------------------------- path -> primitives
def path_to_runs(path):
    """split grid path into per-layer polylines and via points"""
    runs, vs = [], []
    cur_layer, pts = path[0][0], [xy(path[0][1], path[0][2])]
    for (L, ix, iy) in path[1:]:
        p = xy(ix, iy)
        if L != cur_layer:
            vs.append(p)
            runs.append((cur_layer, pts))
            cur_layer, pts = L, [p]
        else:
            pts.append(p)
    runs.append((cur_layer, pts))
    return runs, vs


def merge_collinear(pts):
    out = [pts[0]]
    for i in range(1, len(pts)):
        if len(out) >= 2:
            ax, ay = out[-2]
            bx, by = out[-1]
            cx, cy = pts[i]
            if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) < 1e-9 and (bx - ax) * (cx - bx) + (by - ay) * (cy - by) > 0:
                out[-1] = pts[i]
                continue
        out.append(pts[i])
    return out


BAD = []


def shortcut(net, layer, pts):
    pts = merge_collinear(pts)
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1:
            if seg_ok(net, layer, (pts[i][0], pts[i][1], pts[j][0], pts[j][1])):
                break
            j -= 1
        if j == i + 1 and not seg_ok(net, layer, (pts[i][0], pts[i][1], pts[j][0], pts[j][1])):
            # a grid step that cuts a corner: try the two axis-aligned doglegs
            a, b = pts[i], pts[j]
            fixed = False
            for m in ((a[0], b[1]), (b[0], a[1])):
                if m != a and m != b and seg_ok(net, layer, (a[0], a[1], m[0], m[1])) and seg_ok(net, layer, (m[0], m[1], b[0], b[1])):
                    out.append(m)
                    fixed = True
                    break
            if not fixed:
                BAD.append((net, layer, a, b))
        out.append(pts[j])
        i = j
    return out



# ============================================================================ spec routing
# Every net is driven from the SPEC built by build_spec: the U1-side via (for Top-exit nets), the
# inner layer, per-net corridor / keep-out rectangles, and the routing order.  All U1-side vias
# are placed as obstacles before any track is routed, so no head can take another's spot.
VIA_XRANGE = {}
BOTTOM_X = {}
BLOCKERS = []
PER_NET_BLOCK = {}
PER_NET_ALLOW = {}
VIA_BOX = {}
SPEC = {}
HEADS = {}


def snap(v):
    return round(round(v / G) * G, 4)


def finalize(net, path, att, plan, why):
    n = NETS[net]
    u1, u3 = n['u1'][0], n['u3'][0]
    fixed_head = None
    if path and path[0][0] == 'TOP_ROUTE':
        fixed_head = path[0][1]
        path = path[1:]
    runs, vs = path_to_runs(path)
    if fixed_head:
        vs.insert(0, xy(path[0][1], path[0][2]))
        runs.insert(0, ('Top', [tuple(p) for p in fixed_head]))
    else:
        runs[0][1][0] = (u1['x'], u1['y'])
    runs[-1][1][-1] = (u3['x'], u3['y'])
    new_vias = [dict(net=net, x=x, y=y, why=why) for (x, y) in vs]
    for v in new_vias:
        vias.append(dict(x=v['x'], y=v['y'], size=VIA_LAND, hole=0.2, net=net))
    new_tracks = []
    total = 0.0
    layers_used = []
    for k, (L, pts) in enumerate(runs):
        if len(pts) < 2:
            continue
        if not (fixed_head and k == 0):
            pts = shortcut(net, L, pts)
        layers_used.append(L)
        for a, b in zip(pts, pts[1:]):
            if a == b:
                continue
            t = dict(net=net, x1=a[0], y1=a[1], x2=b[0], y2=b[1], layer=L, width=W[L], why=why)
            new_tracks.append(t)
            total += math.hypot(b[0] - a[0], b[1] - a[1])
    for t in new_tracks:
        tracks.append(dict(layer=t['layer'], net=net, x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], width=t['width']))
    plan['vias'] += new_vias
    plan['tracks'] += new_tracks
    inner = [L for L in layers_used if L in ('L3-SIG', 'L4-SIG')]
    plan['nets'][net] = dict(layer='+'.join(dict.fromkeys(inner)) if inner else 'Top/Bottom', length_mm=round(total, 3),
                             vias=len(new_vias) + (1 if u1['kind'] == 'via' else 0), attempt=att)





def band_rects(row, mode, px, hb, x1=None):
    """keep-out rectangles (x0, y0, x1, y1) in front of a U3 row, outside [px-hb, px+hb]"""
    if row == 'S':
        x1 = x1 or (39.3 if mode == 'under' else 38.0)
        cuts = [(17.0, 27.2, 8.45), (27.2, 35.8, 9.5), (35.8, x1, 8.45)]   # U2 south pads raise the middle
        y0w = 5.6 if mode == 'under' else 6.45
        out = []
        for (a, b, top) in cuts:
            wa, wb = a, min(b, px - hb)
            if wb > wa:
                out.append((wa, y0w, wb, top))
            ea, eb = max(a, px + hb), b
            if eb > ea:
                out.append((ea, 6.45, eb, top))
        return out
    x1 = x1 or 38.0
    cuts = [(17.0, 21.9, 15.3), (21.9, 27.0, 13.9), (27.0, x1, 16.05)]   # LD3/LD4/LD5 and U2's west column push vias down
    out = []
    for (a, b, bot) in cuts:
        wa, wb = a, min(b, px - hb)
        if wb > wa:
            out.append((wa, bot, wb, 17.25))
        ea, eb = max(a, px + hb), b
        if eb > ea:
            out.append((ea, bot, eb, 17.25))
    return out


def route_head(net, plan):
    s = SPEC[net]
    u1 = NETS[net]['u1'][0]
    vx, vy = s['via']
    if s.get('top'):
        pts = [(u1['x'], u1['y'])] + [tuple(p) for p in s['top']] + [(vx, vy)]
        for a_, b_ in zip(pts, pts[1:]):
            why = []
            if not seg_ok(net, 'Top', (a_[0], a_[1], b_[0], b_[1]), eps=0.0, why=why):
                print('  %-9s head segment %s-%s: %s' % (net, a_, b_, why[:2]))
                return None
        return [('TOP_ROUTE', pts)]
    pre = [(u1['x'], u1['y'])] + [tuple(p) for p in s.get('top_pre', [])]
    for a_, b_ in zip(pre, pre[1:]):
        why = []
        if not seg_ok(net, 'Top', (a_[0], a_[1], b_[0], b_[1]), eps=0.0, why=why):
            print('  %-9s head pre-segment %s-%s: %s' % (net, a_, b_, why[:2]))
            return None
    sx, sy = pre[-1]
    bbox = (min(u1['x'], vx) - 3.0, max(u1['x'], vx) + 3.0)
    p, pops = astar(net, [('Top', sx, sy)], ('Top', vx, vy), ['Top'], dict(FACTOR), 'S', bbox, no_via=True)
    if not p:
        print('  %-9s head FAIL' % net)
        return None
    pts = [xy(ix, iy) for (_, ix, iy) in p]
    pts[0] = (sx, sy)
    pts = pre[:-1] + shortcut(net, 'Top', pts)
    return [('TOP_ROUTE', pts)]


def route_spec_net(net, plan):
    s = SPEC[net]
    n = NETS[net]
    u1, u3 = n['u1'][0], n['u3'][0]
    row = 'S' if abs(u3['y'] - 6.1701) < 0.01 else 'N'
    layers = [L for L in s['layers']] + ['Bottom']
    PER_NET_BLOCK[net] = [tuple(r) for r in s.get('block', [])]
    PER_NET_ALLOW[net] = [tuple(r) for r in s.get('allow', [])]
    VIA_BOX[net] = [tuple(r) for r in s.get('via_box', [])]
    # the pocket-via band in front of each U3 row is for vias: a lane may cross it only
    # within BAND_HALF of its own pad, so no lane runs diagonally in front of other pads
    if not s.get('noband'):
        px = u3['x']
        hb = s.get('band_half', BAND_HALF)
        if 'bottom_x' in s:          # the lane window must cover the pocket-via window
            hb = max(hb, px - s['bottom_x'][0] + 0.35, s['bottom_x'][1] - px + 0.35)
        mode = s.get('band', 'under' if (row == 'S' and u1['kind'] != 'via' and u1['y'] < 7.3) else 'pocket')
        for r in band_rects(row, mode, px, hb, s.get('band_x1')):
            for L in ('L3-SIG', 'L4-SIG'):
                PER_NET_BLOCK[net].append((L,) + r)
    head = []
    if u1['kind'] != 'via':
        head = HEADS.get(net)
        if head is None:
            head = route_head(net, plan)
        if head is None:
            return False
        vx, vy = s['via']
        srcs = [(L, vx, vy) for L in s['layers']]
    else:
        srcs = [(L, u1['x'], u1['y']) for L in s['layers']]
    bbox = tuple(s.get('bbox', (17.3, 52.0)))
    if 'bottom_x' in s:
        BOTTOM_X[net] = tuple(s['bottom_x'])
    t0 = time.time()
    path, pops = astar(net, srcs, ('Bottom', u3['x'], u3['y']), layers, dict(FACTOR, **s.get('factor', {})), row, bbox)
    print('  %-9s %-14s pops=%7d %.1fs %s' % (net, '+'.join(s['layers']), pops, time.time() - t0, 'OK' if path else 'FAIL'), flush=True)
    if not path:
        return False
    if head and head[0][0] == 'TOP_ROUTE':
        full = head + path
    elif head:
        full = head + path
    else:
        full = path
    finalize(net, full, 'spec', plan, s.get('why', 'phase 2 spec'))
    return True


def route_all(d):
    """route every net of spec d; returns the plan"""
    SPEC.clear(); HEADS.clear(); BOTTOM_X.clear(); PER_NET_BLOCK.clear(); PER_NET_ALLOW.clear(); VIA_BOX.clear()
    for n, s in d['nets'].items():
        SPEC[n] = s
    order = d['order']
    plan = dict(vias=[], tracks=[], nets={})
    vias[:] = [dict(v) for v in inp['vias']]
    tracks[:] = [dict(t) for t in inp['tracks']]
    # every U1-side via of every spec net is an obstacle from the start
    for n in order:
        s = SPEC[n]
        if s.get('via'):
            s['via'] = (snap(s['via'][0]), snap(s['via'][1]))
            vias.append(dict(x=s['via'][0], y=s['via'][1], size=VIA_LAND, hole=0.2, net=n, fixed=True))
    unrouted = []
    # heads first, in their own order (east first), so the long western heads fan around the
    # short eastern ones; each head's Top copper is an obstacle for later heads
    PRE = []
    for n in d.get('head_order', []):
        s_ = SPEC[n]
        if s_.get('top_pre'):
            u = NETS[n]['u1'][0]
            pts = [(u['x'], u['y'])] + [tuple(p) for p in s_['top_pre']]
            for a_, b_ in zip(pts, pts[1:]):
                PRE.append(dict(layer='Top', net=n, x1=a_[0], y1=a_[1], x2=b_[0], y2=b_[1], width=W['Top']))
    tracks.extend(PRE)
    for n in d.get('head_order', []):
        if NETS[n]['u1'][0]['kind'] == 'via' or n in HEADS:
            continue
        h = route_head(n, plan)
        if h is None:
            continue
        HEADS[n] = h
        if h[0][0] == 'TOP_ROUTE':
            pts = h[0][1]
        else:
            pts = [xy(ix, iy) for (_, ix, iy) in h]
            pts[0] = (NETS[n]['u1'][0]['x'], NETS[n]['u1'][0]['y'])
            pts = shortcut(n, 'Top', pts)
            HEADS[n] = [('TOP_ROUTE', pts)]
        for a_, b_ in zip(pts, pts[1:]):
            tracks.append(dict(layer='Top', net=n, x1=a_[0], y1=a_[1], x2=b_[0], y2=b_[1], width=W['Top']))
    for n in order:
        if not route_spec_net(n, plan):
            unrouted.append(n)
    plan['unrouted'] = unrouted
    return plan


def main(argv):
    STRICT_CLK[0] = '--lenient-clk' not in argv
    out = argv[argv.index('--out') + 1] if '--out' in argv else OUT
    d = build_spec(STRICT_CLK[0])
    if '--spec-out' in argv:
        json.dump(d, io.open(argv[argv.index('--spec-out') + 1], 'w', encoding='utf-8'), indent=1)
    t0 = time.time()
    plan = route_all(d)
    plan['generator'] = 'tools/sdram_route_plan.py' + (' --lenient-clk' if not STRICT_CLK[0] else '')
    json.dump(plan, io.open(out, 'w', encoding='utf-8'), indent=1)
    probs = RE.check(inp, plan)
    comp = RE.completeness(inp, plan)
    bad = sorted(k for k, (ok, _) in comp.items() if not ok)
    for b_ in BAD:
        print('  UNREPAIRED corner cut:', b_)
    print('%d vias, %d tracks, unrouted=%s, problems=%d, joined %d/%d%s  (%.0f s) -> %s' % (
        len(plan['vias']), len(plan['tracks']), plan['unrouted'], len(probs), len(comp) - len(bad), len(comp),
        (' missing ' + ' '.join(bad)) if bad else '', time.time() - t0, os.path.normpath(out)))
    for p_ in probs[:30]:
        print('  ', p_)
    return 0 if not probs and not bad else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
