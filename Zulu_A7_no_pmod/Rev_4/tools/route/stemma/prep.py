"""No-PMOD Rev 3 (2026-11-21): STEMMA QT X5 on the Top at the east short edge, plus the four 22 uF caps under it.

    python tools/route/stemma/prep.py        (after route_model.py -> tools/route/stemma/base.json)

* X5 (JST-SM04B-SRSS-TB, rotation 90, mouth east): origin (58.28, 8.15). Its tab lands MP1/MP2 end 0.30 mm from
  the east edge (as Asar's X5); pads 1-4 (GND, VCC3V3, I2C-SDA, I2C-SCL) at x 55.885, y 6.65..9.65. The y range
  7.65..8.65 clears every body (tools/body_check.py) and the 'VU 22' pin label; 8.15 is its middle.
* C141, C142, C144, C145 (0805, 22 uF) flip to the Bottom at the same XY (0805 is symmetric about its origin).
* U1 balls U19 -> I2C-SDA, R19 -> I2C-SCL (sheet 5, tools/stemma_sheet5.py).
Copper ripped (left to router.py): every Top track/via that touches an old cap pad (now gone from the Top), and
other-net copper within 0.09 mm of a new pad on its layer (X5 on the Top, the caps on the Bottom). A ripped via takes
its stack partners. Writes model.json (router input), base_moved.json (pads as after the change) and rip.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
from bodies_fix_prep import pad_pt, pad_seg  # noqa: E402

CLR = 0.09
OX, OY = 58.28, 8.15
CAPS = ('C141', 'C142', 'C144', 'C145')
X5 = [('1', 'GND', -1.5), ('2', 'VCC3V3', -0.5), ('3', 'I2C-SDA', 0.5), ('4', 'I2C-SCL', 1.5)]
BALLS = {'U19': 'I2C-SDA', 'R19': 'I2C-SCL'}


def on_pad(p, x, y):
    return abs(x - p['x']) <= p['w'] / 2 + 1e-4 and abs(y - p['y']) <= p['h'] / 2 + 1e-4


def main():
    M = json.load(open(os.path.join(HERE, 'base.json')))
    old_caps = [dict(p) for p in M['pads'] if p['ref'] in CAPS]
    assert len(old_caps) == 8 and all(p['layers'] == ['Top Layer'] for p in old_caps)
    for p in M['pads']:
        if p['ref'] in CAPS:
            p['layers'] = ['Bottom Layer']
        if p['ref'] == 'U1' and p['pad'] in BALLS:
            assert not p['net'], p
            p['net'] = BALLS[p['pad']]
    new = [{'ref': 'X5', 'pad': n, 'net': net, 'x': round(OX - 2.395, 4), 'y': round(OY + lx, 4), 'shape': 'rect',
            'w': 1.55, 'h': 0.6, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False} for n, net, lx in X5]
    new += [{'ref': 'X5', 'pad': n, 'net': 'GND', 'x': round(OX + 1.48, 4), 'y': round(OY + lx, 4), 'shape': 'rect',
             'w': 1.8, 'h': 1.2, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False} for n, lx in (('MP1', -2.8), ('MP2', 2.8))]
    M['pads'] += new
    json.dump(M, open(os.path.join(HERE, 'base_moved.json'), 'w'))
    rm_t, rm_v = [], []
    # (1) Top copper that fed the old cap pads
    for p in old_caps:
        for t in M['tracks']:
            if t['layer'] == 'Top Layer' and t['net'] == p['net'] and t not in rm_t and (
                    on_pad(p, t['x1'], t['y1']) or on_pad(p, t['x2'], t['y2'])):
                rm_t.append(t)
        for v in M['vias']:
            if 'Top Layer' in v['span'] and v['net'] == p['net'] and on_pad(p, v['x'], v['y']) and v not in rm_v:
                rm_v.append(v)
    # (2) other-net copper too close to a new pad on its layer
    for p in new + [p for p in M['pads'] if p['ref'] in CAPS]:
        L = p['layers'][0]
        for t in M['tracks']:
            if t['layer'] == L and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if L in v['span'] and v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR and v not in rm_v:
                rm_v.append(v)
    for v in list(rm_v):
        for w in M['vias']:
            if w is not v and w not in rm_v and abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rm_v.append(w)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    moves = [{'ref': r, 'x': round(sum(p['x'] for p in old_caps if p['ref'] == r) / 2, 4),
              'y': round(sum(p['y'] for p in old_caps if p['ref'] == r) / 2, 4), 'dx': 0.0, 'dy': 0.0,
              'layer': 'Bottom Layer'} for r in CAPS]
    json.dump(M, open(os.path.join(HERE, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves, 'jogs': []}, open(os.path.join(HERE, 'rip.json'), 'w'), indent=1)
    nets = sorted({o['net'] for o in rm_t + rm_v})
    print('removed %d tracks, %d vias on %d nets: %s' % (len(rm_t), len(rm_v), len(nets), nets))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
