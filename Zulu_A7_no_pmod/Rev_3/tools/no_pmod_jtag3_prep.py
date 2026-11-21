"""Zulu_a7_no_pmod Rev 2 (user request 2026-11-12): all six JTAG holes in one column on the west edge, centred on the
board: from the bottom TDI 6.35, TDO 8.89, VCC3V3 11.43 (JP4) and TCK 13.97, TMS 16.51, GND 19.05 (JP3), x 1.10, both
headers at rotation 90 (pins run +y).

The lower half of that column held part of the LTC3556 input on Bottom, so (user approved) C78 moves to (2.80, 15.65) and
R108 to (6.00, 13.45) (route/jtag2/sites.py: nearest legal spots), and the Bottom VU trunk west of x 3.7, C78's GND tie and
the JTAG routes from stage 2 are ripped for re-routing.

    python tools/no_pmod_jtag3_prep.py
Writes route/jtag2/: base_compose.json (JP4 rotated about its old origin, nothing moved), base_moved.json, model.json
(router input) and rip.json.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'route', 'jtag2')
# ref, old origin, new origin, rotate 90 about the old origin first
MOVES = [('JP3', 1.10, 17.43, 1.10, 16.51, False), ('JP4', 4.04, 3.00, 1.10, 8.89, True),
         ('C78', 1.14, 7.8999, 2.80, 15.65, False), ('R108', 2.525, 13.475, 6.00, 13.45, False)]
JTAG = {'TCK', 'TMS', 'TDI', 'TDO'}


def main():
    M = json.load(open(os.path.join(HERE, 'route', 'jtag', 'after_title.json')))
    S2 = json.load(open(os.path.join(HERE, 'route', 'jtag', 'final.json')))
    for p in M['pads']:
        for r, ox, oy, nx, ny, rot in MOVES:
            if p['ref'] == r and rot:
                dx, dy = p['x'] - ox, p['y'] - oy
                p['x'], p['y'] = round(ox - dy, 4), round(oy + dx, 4)
                p['w'], p['h'] = p['h'], p['w']
    json.dump(M, open(os.path.join(OUT, 'base_compose.json'), 'w'))
    for p in M['pads']:
        for r, ox, oy, nx, ny, rot in MOVES:
            if p['ref'] == r:
                p['x'] = round(p['x'] + nx - ox, 4)
                p['y'] = round(p['y'] + ny - oy, 4)
    json.dump(M, open(os.path.join(OUT, 'base_moved.json'), 'w'))
    tk = lambda t: (t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))  # noqa: E731
    vk = lambda v: (v['net'], round(v['x'], 3), round(v['y'], 3))  # noqa: E731
    # match the stage-2 copper within 3 um, either direction (the extracted coordinates are not bit-identical)
    s2 = [t for t in S2['tracks'] if t['net'] in JTAG]

    def is_s2(t):
        e = 0.003
        for a in s2:
            if a['net'] == t['net'] and a['layer'] == t['layer'] and (
                    all(abs(a[k] - t[k]) < e for k in ('x1', 'y1', 'x2', 'y2')) or
                    (abs(a['x1'] - t['x2']) < e and abs(a['y1'] - t['y2']) < e and abs(a['x2'] - t['x1']) < e and abs(a['y2'] - t['y1']) < e)):
                return True
        return False
    s2v = [v for v in S2['vias'] if v['net'] in JTAG]
    is_s2v = lambda v: any(a['net'] == v['net'] and abs(a['x'] - v['x']) < 0.003 and abs(a['y'] - v['y']) < 0.003 for a in s2v)  # noqa: E731
    rm, rmv = [], []
    for t in M['tracks']:
        if is_s2(t):
            rm.append(t)
        elif t['net'] == 'TMS' and abs(t['x1'] - 1.625) < 1e-3 and abs(t['y1'] - 16.725) < 1e-3:     # NoPmod_Silk4 stub
            rm.append(t)
        elif t['net'] == 'VU' and t['layer'] == 'Bottom Layer' and max(t['x1'], t['x2']) < 3.7:
            rm.append(t)
        elif t['net'] == 'GND' and t['layer'] == 'Bottom Layer' and max(t['x1'], t['x2']) < 0.7 and 6.0 < t['y1'] < 6.7:
            rm.append(t)
    for v in M['vias']:
        if is_s2v(v) or (v['net'] == 'GND' and abs(v['x'] - 0.575) < 1e-3 and abs(v['y'] - 6.2) < 1e-3):
            rmv.append(v)
    ids, idv = {id(t) for t in rm}, {id(v) for v in rmv}
    R = dict(M, tracks=[t for t in M['tracks'] if id(t) not in ids], vias=[v for v in M['vias'] if id(v) not in idv])
    json.dump(R, open(os.path.join(OUT, 'model.json'), 'w'))
    json.dump({'remove': rm, 'remove_vias': rmv,
               'moves': [{'ref': r, 'x': nx, 'y': ny, 'dx': round(nx - ox, 4), 'dy': round(ny - oy, 4)} for r, ox, oy, nx, ny, rot in MOVES]},
              open(os.path.join(OUT, 'rip.json'), 'w'), indent=1)
    import collections
    print('rip tracks', collections.Counter(t['net'] for t in rm), 'vias', collections.Counter(v['net'] for v in rmv))
    print([(p['ref'], p['pad'], p['net'], p['x'], p['y']) for p in R['pads'] if p['ref'] in ('JP3', 'JP4', 'C78', 'R108')])


if __name__ == '__main__':
    main()
