"""No-PMOD Rev 4 (2026-11-25): JTAG header to a 1x6 through-hole row above X3, X3 to the west edge, BTN back home.

    python tools/route/jtag_top/prep.py    (after sites.py west; base = tools/route/illustration/base.json)

User decisions 2026-11-25: through-hole JTAG header above X3; X3 pushed to the left edge; BTN back to its Rev 3
central position. Moves (origins, emit_copper checks every old origin and pad 1):
* X3  -1.70 mm x: the lock-housing face lands 0.80 mm inside the west edge, so a locked card stands ~0.8 mm proud
      (push-push) and an ejected one ~4.6 mm; G1 copper 0.50 mm from the edge.
* JP4 (TDI, TDO, VCC3V3) and JP3 (TCK, TMS, GND): rotation 90 -> 0, one row at y 21.00 on the X2 2.54 grid,
      holes at x 1.26 / 3.80 / 6.34 (JP4) and 8.88 / 11.42 / 13.96 (JP3), directly under X2 pins 20-15. y 21.00: pad
      bottom 0.29 mm above X3's copper-prohibition strip, pad top + mask 0.30 mm below the X2 label silk.
* BTN back to (18.00, 12.92) rotation 90 (Rev 3); C158 back to x 18.10 (Rev 3).
* Bottom parts the row displaces, sites from sites.py west: C11, C12, R35 +0.95 mm north; C13 to (2.15, 19.59);
  R34 turned +90 to centre (14.42, 18.39).
Copper ripped (left to router.py): copper that fed an old pad of a moved part (on that pad's layers), other-net copper
within 0.09 mm of a new pad on its layers (through-holes: every layer, and vias within the 0.24 mm hole rule).
A same-net through via under a new SMD pad is ripped too (release rule: no through via in an SMD pad).
Keepouts: X3's prohibition strip (board x 3.40..16.30, y 19.35..19.95, Top) and the G1 bands, all shifted with X3.
Writes model.json, base_moved.json and rip.json.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
from bodies_fix_prep import pad_pt, pad_seg  # noqa: E402

CLR = 0.09
HOLE_HOLE = 0.24
ALL = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
REV3 = os.path.join(os.path.dirname(os.path.dirname(TOOLS)), 'Rev_3', 'tools', 'route', 'illustration', 'base.json')
X3_DX = -1.70
ROW_Y = 21.00
JP = {'JP4': (3.80, ['TDI', 'TDO', 'VCC3V3']), 'JP3': (11.42, ['TCK', 'TMS', 'GND'])}
STRIP = (5.10 + X3_DX, 19.35, 18.00 + X3_DX, 19.95)
KEEP = [STRIP, (2.00 + X3_DX, 6.80, 4.30 + X3_DX, 7.30), (4.10 + X3_DX, 5.00, 4.60 + X3_DX, 7.30),
        (2.00 + X3_DX, 4.90, 4.60 + X3_DX, 5.40)]


def on_pad(p, x, y):
    return abs(x - p['x']) <= p['w'] / 2 + 1e-4 and abs(y - p['y']) <= p['h'] / 2 + 1e-4


def main():
    M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
    R3 = {(p['ref'], p['pad']): p for p in json.load(open(REV3))['pads']}
    S = {s['ref']: s for s in json.load(open(os.path.join(HERE, 'sites_west.json')))['parts']}
    moved = {'X3', 'JP3', 'JP4', 'BTN', 'C158', 'C11', 'C12', 'C13', 'R35', 'R34'}
    old = [dict(p) for p in M['pads'] if p['ref'] in moved]
    new = []
    for p in M['pads']:
        r = p['ref']
        if r == 'X3':
            p['x'] = round(p['x'] + X3_DX, 4)
        elif r in JP:
            cx, nets = JP[r]
            k = int(p['pad']) - 1
            assert p['net'] == nets[k], (r, p['pad'], p['net'])
            p['x'], p['y'] = round(cx + 2.54 * (k - 1), 4), ROW_Y
        elif r in ('BTN', 'C158'):
            q = R3[(r, p['pad'])]
            p['x'], p['y'], p['w'], p['h'] = q['x'], q['y'], q['w'], q['h']
        elif r in S:
            q = {a: (x, y) for a, x, y in S[r]['pads']}[p['pad']]
            p['x'], p['y'] = q
            if S[r]['turn'] % 180:
                p['w'], p['h'] = p['h'], p['w']
        else:
            continue
        new.append(p)
    json.dump(M, open(os.path.join(HERE, 'base_moved.json'), 'w'))
    rm_t, rm_v = [], []

    def lay(p):
        return ALL if p['drill'] else p['layers']
    for p in old:                                     # copper that fed an old pad
        for t in M['tracks']:
            if t['layer'] in lay(p) and t['net'] == p['net'] and p['net'] and t not in rm_t and (
                    on_pad(p, t['x1'], t['y1']) or on_pad(p, t['x2'], t['y2'])):
                rm_t.append(t)
        for v in M['vias']:
            if set(v['span']) & set(lay(p)) and v['net'] == p['net'] and p['net'] and on_pad(p, v['x'], v['y']) and v not in rm_v:
                rm_v.append(v)
    for p in new:                                     # other-net copper too close to a new pad
        for t in M['tracks']:
            if t['layer'] in lay(p) and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if v in rm_v:
                continue
            if set(v['span']) & set(lay(p)) and v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR:
                rm_v.append(v)
            elif p['drill'] and math.hypot(v['x'] - p['x'], v['y'] - p['y']) < HOLE_HOLE + p['drill'] / 2 + v['hole'] / 2:
                rm_v.append(v)
    for p in new:                                     # same-net THROUGH via whose land overlaps a new SMD pad
        if p['drill']:
            continue
        for v in M['vias']:
            if v['span'][0] == 'Top Layer' and v['span'][-1] == 'Bottom Layer' and v['net'] == p['net']                     and pad_pt(p, v['x'], v['y']) < v['size'] / 2 and v not in rm_v:
                rm_v.append(v)
                rm_t.extend(t for t in M['tracks'] if t not in rm_t and t['net'] == v['net'] and any(
                    abs(t[a] - v['x']) < 1e-3 and abs(t[c] - v['y']) < 1e-3 for a, c in (('x1', 'y1'), ('x2', 'y2'))))
    for b in KEEP:                                    # X3 keepouts, Top
        for t in M['tracks']:
            if t['layer'] == 'Top Layer' and t not in rm_t and any(
                    b[0] - t['w'] / 2 < t['x1'] + (t['x2'] - t['x1']) * i / 20 < b[2] + t['w'] / 2 and
                    b[1] - t['w'] / 2 < t['y1'] + (t['y2'] - t['y1']) * i / 20 < b[3] + t['w'] / 2 for i in range(21)):
                rm_t.append(t)
        for v in M['vias']:
            if 'Top Layer' in v['span'] and v not in rm_v and b[0] - v['size'] / 2 < v['x'] < b[2] + v['size'] / 2 \
                    and b[1] - v['size'] / 2 < v['y'] < b[3] + v['size'] / 2:
                rm_v.append(v)
    for v in list(rm_v):                              # a ripped via takes its stack partners
        for w in M['vias']:
            if w is not v and w not in rm_v and abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rm_v.append(w)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]

    def mv(ref, ox, oy, nx, ny, **kw):
        pads = {p['pad']: [p['x'], p['y']] for p in new if p['ref'] == ref}
        m = {'ref': ref, 'x': round(nx, 4), 'y': round(ny, 4), 'dx': round(nx - ox, 4), 'dy': round(ny - oy, 4),
             'pad_xy': pads, 'pad1': pads['1']}
        m.update(kw)
        return m
    moves = [mv('X3', 10.60, 12.70, 10.60 + X3_DX, 12.70),
             mv('JP4', 1.10, 8.89, 3.80, ROW_Y, rotation=0),
             mv('JP3', 1.10, 16.51, 11.42, ROW_Y, rotation=0),
             mv('BTN', 20.60, 5.20, 18.00, 12.92, rotation=90),
             mv('C158', 18.70, 16.6499, 18.10, 16.6499),
             mv('C11', 5.2999, 21.39, 5.2999, 22.34), mv('C12', 7.5998, 21.39, 7.5998, 22.34),
             mv('R35', 9.8998, 21.39, 9.8998, 22.34), mv('C13', 2.5999, 21.44, 2.15, 19.59),
             # R34 origin sits 0.80 mm west of its pad centroid; turning +90 about the origin puts it 0.80 south
             mv('R34', 11.42, 19.29, 14.42, 18.39 - 0.80, rotation=90)]
    model = dict(M)
    model['pads'] = M['pads'] + [{'ref': 'KO', 'pad': 'K%d' % i, 'net': '', 'x': (b[0] + b[2]) / 2, 'y': (b[1] + b[3]) / 2,
                                  'shape': 'rect', 'w': b[2] - b[0], 'h': b[3] - b[1], 'layers': ['Top Layer'],
                                  'drill': 0.0, 'plated': False} for i, b in enumerate(KEEP)]
    json.dump(model, open(os.path.join(HERE, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves, 'jogs': []}, open(os.path.join(HERE, 'rip.json'), 'w'), indent=1)
    nets = sorted({o['net'] for o in rm_t + rm_v})
    print('removed %d tracks, %d vias on %d nets' % (len(rm_t), len(rm_v), len(nets)))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
