"""Zulu_a7_no_pmod: delete the Pmod (J1, R26-R33 and the JA*/PMOD-* copper), cut the board to 2.4 x 1.0 in and pull
the six surviving resistors inside the new east edge.

    python tools/no_pmod_prep.py <base_model.json> <out_dir>

JP3/JP4 (JTAG) are parked, not routed: they leave the model so the router only rejoins what stays on the board.
Writes model.json (router input), base_moved.json (route_check / compose base: parts gone or moved, copper untouched)
and rip.json (emit_copper removals + component moves).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_conn as C  # noqa: E402

W_NEW = 60.96
EDGE_LIM = W_NEW - 0.30           # router/route_check edge clearance
WINDOW_X = 57.5                   # signal nets that cross the edge are ripped east of this
# TDI is left out of SIG on purpose: its old route hugs the south edge (y 0.3, inside the router's 0.30 keep-out), so it
# stays down to (60.1, 3.0), which is inside the new edge, and the router continues from that interior end.
GONE = {'J1', 'R26', 'R27', 'R28', 'R29', 'R30', 'R31', 'R32', 'R33', 'JP3', 'JP4'}
PMOD = {'JA%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)} | {'PMOD-%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)}
SIG = {'TCK', 'TDO', 'TMS', 'UART_FT_CTS#', 'PROG#', 'CLK-12M-FPGA', 'CLK-12M-FT', 'CLK-12M-SHARED', 'FPGA-TCK', 'CHAN22'}
PLANE = {'GND', 'VCC3V3'}
# R24, R25 and R5 sit next to the ends of their nets' surviving copper, so the clock and FPGA-TCK no longer run the length
# of the east strip (the old routes used the strip past the new edge).
MOVES = [('R25', 61.10, 5.65, 56.30, 14.05), ('R24', 59.05, 5.65, 59.35, 21.20), ('R90', 63.15, 14.17, 58.95, 13.15), ('R5', 61.10, 14.17, 56.70, 20.10),
         ('R92', 61.10, 17.01, 60.20, 17.01), ('R93', 63.15, 17.01, 60.20, 17.80), ('R99', 61.10, 19.85, 60.20, 19.85)]


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    mv = {r: (nx - ox, ny - oy) for r, ox, oy, nx, ny in MOVES}
    old = [dict(p) for p in M['pads'] if p['ref'] in mv]
    C0 = dict(M, pads=[dict(p, x=round(2 * 61.10 - p['x'], 4)) if p['ref'] == 'R5' else p for p in M['pads'] if p['ref'] not in GONE],
              board={'w': W_NEW, 'h': M['board']['h']})
    json.dump(C0, open(os.path.join(out, 'base_compose.json'), 'w'))  # compose_plan applies 'moves' itself
    gone_pads = [dict(p) for p in M['pads'] if p['ref'] in GONE]
    M['pads'] = [p for p in M['pads'] if p['ref'] not in GONE]
    for p in M['pads']:
        if p['ref'] in mv:
            p['x'] = round(p['x'] + mv[p['ref']][0], 4)
            p['y'] = round(p['y'] + mv[p['ref']][1], 4)
            if p['ref'] == 'R5':          # R5 is also turned 180 degrees about its centre, so pad 2 faces the FPGA-TCK via
                p['x'] = round(2 * 56.70 - p['x'], 4)
    M['board']['w'] = W_NEW
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    dead_land = old + gone_pads
    on_old = lambda x, y, net: any(p['net'] == net and C.pad_point(p, x, y) < 1e-3 for p in dead_land)  # noqa: E731
    rm_t = []
    for t in M['tracks']:
        east = max(t['x1'], t['x2']) + t['w'] / 2
        if t['net'] in PMOD or east > EDGE_LIM or (t['net'] in SIG and max(t['x1'], t['x2']) > WINDOW_X)                 or (t['net'] == 'TDI' and min(t['y1'], t['y2']) > 5 and max(t['x1'], t['x2']) > WINDOW_X):
            rm_t.append(t)
        elif t['net'] in PLANE and (on_old(t['x1'], t['y1'], t['net']) or on_old(t['x2'], t['y2'], t['net'])):
            rm_t.append(t)
    cols = set()
    for v in M['vias']:
        key = (v['net'], round(v['x'], 3), round(v['y'], 3))
        if v['net'] in PMOD or v['x'] + v['size'] / 2 > EDGE_LIM or (v['net'] in SIG and v['x'] > WINDOW_X):
            cols.add(key)
        elif v['net'] in PLANE and any(p['net'] == v['net'] and C.pad_point(p, v['x'], v['y']) - v['size'] / 2 < 1e-3 for p in dead_land):
            cols.add(key)
    rm_v = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) in cols]
    it, iv = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in it]
    M['vias'] = [v for v in M['vias'] if id(v) not in iv]
    # X2's pad is modelled by its bounding box, so the end of TDI at (60.1, 3.0) sits on the box and the raster router
    # cannot leave it: extend it by hand onto open board. The router continues from (60.25, 3.40).
    # R4-3's east side has no room left inside the new edge: fan it out west, between the array's two pad columns.
    manual = {'tracks': [{'net': 'TDI', 'layer': 'Top Layer', 'w': 0.0762, 'x1': 60.1, 'y1': 3.0, 'x2': 60.25, 'y2': 3.4},
                         {'net': 'TDI', 'layer': 'Top Layer', 'w': 0.0762, 'x1': 60.1499, 'y1': 16.9781, 'x2': 59.45, 'y2': 17.02},
                         {'net': 'TDO', 'layer': 'Top Layer', 'w': 0.0762, 'x1': 60.1499, 'y1': 17.778, 'x2': 59.52, 'y2': 17.48},
                         {'net': 'TDO', 'layer': 'Bottom Layer', 'w': 0.0762, 'x1': 59.52, 'y1': 17.48, 'x2': 58.75, 'y2': 17.48},
                         {'net': 'TDO', 'layer': 'Bottom Layer', 'w': 0.0762, 'x1': 58.75, 'y1': 17.48, 'x2': 58.75, 'y2': 17.01},
                         {'net': 'FPGA-TCK', 'layer': 'Bottom Layer', 'w': 0.0762, 'x1': 55.4, 'y1': 20.1, 'x2': 56.4, 'y2': 20.1},
                         {'net': 'GND', 'layer': 'Bottom Layer', 'w': 0.0762, 'x1': 57.55, 'y1': 20.3, 'x2': 57.0, 'y2': 20.1}],
              'vias': [{'net': 'TDI', 'x': 59.45, 'y': 17.02, 'size': 0.3, 'hole': 0.15, 'from': 'Top Layer', 'to': 'L2-GND'},
                       {'net': 'TDI', 'x': 59.45, 'y': 17.02, 'size': 0.3, 'hole': 0.15, 'from': 'L2-GND', 'to': 'L3-SIG'},
                       {'net': 'TDO', 'x': 59.52, 'y': 17.48, 'size': 0.35, 'hole': 0.2, 'from': 'Top Layer', 'to': 'Bottom Layer'},
                       {'net': 'GND', 'x': 57.55, 'y': 20.3, 'size': 0.35, 'hole': 0.2, 'from': 'Top Layer', 'to': 'Bottom Layer'}]}
    M['tracks'] += manual['tracks']
    STK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
    M['vias'] += [dict(v, span=STK[STK.index(v['from']):STK.index(v['to']) + 1]) for v in manual['vias']]
    json.dump(manual, open(os.path.join(out, 'manual.json'), 'w'))
    moves = [{'ref': r, 'x': nx, 'y': ny, 'dx': round(nx - ox, 4), 'dy': round(ny - oy, 4)} for r, ox, oy, nx, ny in MOVES]  # x, y = NEW place (emit_copper guards on x - dx)
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves}, open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    print('ripped %d tracks, %d vias (%d columns)' % (len(rm_t), len(rm_v), len(cols)))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), oc))


if __name__ == '__main__':
    main()
