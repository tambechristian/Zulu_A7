"""No-PMOD Rev 4 (2026-11-25): BTN centred between the X3 shell and the LED column.

    python tools/route/btn_centre/prep.py    (base = tools/route/illustration/base.json, board md5 904c5244)

After the JTAG move X3's body ends at x 16.00 and BTN's body (PTS810, 3.20 x 4.20 at rotation 90) spans x 16.40..19.60:
0.40 mm to the X3 shell but 1.35 mm to the LED pads (west edge x 20.95). BTN moves +0.475 mm east (origin 18.00 ->
18.475, y 12.92, rotation 90 unchanged), leaving 0.875 mm each side.
Copper ripped (left to router.py): copper that fed an old BTN pad; other-net copper within 0.09 mm of a new BTN pad on
Top; a same-net through via under a new BTN pad. X3 keepouts (already at the shifted X3) stay as router keepouts.
Writes model.json, base_moved.json and rip.json.
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
DX = 0.475
OLD = (18.00, 12.92)
KEEP = [(3.40, 19.35, 16.30, 19.95), (0.30, 6.80, 2.60, 7.30), (2.40, 5.00, 2.90, 7.30), (0.30, 4.90, 2.90, 5.40)]


def on_pad(p, x, y):
    return abs(x - p['x']) <= p['w'] / 2 + 1e-4 and abs(y - p['y']) <= p['h'] / 2 + 1e-4


def main():
    M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
    old = [dict(p) for p in M['pads'] if p['ref'] == 'BTN']
    assert len(old) == 4 and abs(sum(p['x'] for p in old) / 4 - OLD[0]) < 1e-3, old
    new = []
    for p in M['pads']:
        if p['ref'] == 'BTN':
            p['x'] = round(p['x'] + DX, 4)
            new.append(p)
    json.dump(M, open(os.path.join(HERE, 'base_moved.json'), 'w'))
    rm_t, rm_v = [], []
    for p in old:
        for t in M['tracks']:
            if t['layer'] in p['layers'] and t['net'] == p['net'] and t not in rm_t and (
                    on_pad(p, t['x1'], t['y1']) or on_pad(p, t['x2'], t['y2'])):
                rm_t.append(t)
        for v in M['vias']:
            if set(v['span']) & set(p['layers']) and v['net'] == p['net'] and on_pad(p, v['x'], v['y']) and v not in rm_v:
                rm_v.append(v)
    for p in new:
        for t in M['tracks']:
            if t['layer'] in p['layers'] and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if v in rm_v or not (set(v['span']) & set(p['layers'])):
                continue
            if v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR:
                rm_v.append(v)
            elif v['net'] == p['net'] and v['span'][0] == 'Top Layer' and v['span'][-1] == 'Bottom Layer' \
                    and pad_pt(p, v['x'], v['y']) < v['size'] / 2:
                rm_v.append(v)
                rm_t.extend(t for t in M['tracks'] if t not in rm_t and t['net'] == v['net'] and any(
                    abs(t[a] - v['x']) < 1e-3 and abs(t[c] - v['y']) < 1e-3 for a, c in (('x1', 'y1'), ('x2', 'y2'))))
    for v in list(rm_v):                              # a ripped via takes its stack partners
        for w in M['vias']:
            if w is not v and w not in rm_v and abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rm_v.append(w)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    pads = {p['pad']: [p['x'], p['y']] for p in new}
    moves = [{'ref': 'BTN', 'x': round(OLD[0] + DX, 4), 'y': OLD[1], 'dx': DX, 'dy': 0.0, 'pad_xy': pads, 'pad1': pads['1'],
              'rotation': 90}]
    model = dict(M)
    model['pads'] = M['pads'] + [{'ref': 'KO', 'pad': 'K%d' % i, 'net': '', 'x': (b[0] + b[2]) / 2, 'y': (b[1] + b[3]) / 2,
                                  'shape': 'rect', 'w': b[2] - b[0], 'h': b[3] - b[1], 'layers': ['Top Layer'],
                                  'drill': 0.0, 'plated': False} for i, b in enumerate(KEEP)]
    json.dump(model, open(os.path.join(HERE, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves, 'jogs': []}, open(os.path.join(HERE, 'rip.json'), 'w'), indent=1)
    print('removed %d tracks, %d vias on nets %s' % (len(rm_t), len(rm_v), sorted({o['net'] for o in rm_t + rm_v})))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d: %s' % (sum(oc.values()), dict(oc)))


if __name__ == '__main__':
    main()
