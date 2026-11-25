"""Zulu_a7_no_pmod Rev 2: JTAG holes onto the resized board.

    python tools/no_pmod_jtag2_prep.py

Rev 1's sites (north strip / west edge) are blocked on Rev 2 (VCC1V0 and VU Bottom copper, R108). A clean-site scan
(route/resize/jtag_sites.py: through-hole lands 0.762 + 0.09 mm to everything, 0.3 mm to the edge) leaves only:
  JP3 (TCK, TMS, GND)      vertical on the west edge, pad 1 (1.40, 14.75), rotation 90 (pins run +y)
  JP4 (TDI, TDO, VCC3V3)   horizontal in the south-west corner, pad 1 (1.50, 3.00), rotation 0 (pins run +x)
The east-end pieces of Rev 1's stage 2 (CLK-12M-SHARED to R24-1 and the LED0_R detour around it) are reused: the east
copper is identical. Writes route/jtag/: model.json (router input), base_compose.json (JP3 rotated, not moved),
base_moved.json, rip.json and east.json.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'route', 'jtag')
REV1 = os.path.join(HERE, '..', '..', 'Rev_1', 'tools', 'route', 'no_pmod2', 'final.json')
STK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
# ref, old origin (pad 2), new origin (pad 2), rotation
MOVES = [('JP3', 64.30, 21.68, 1.40, 17.29, 90), ('JP4', 64.30, 3.72, 4.04, 3.00, 0)]


def rot90(p, ox, oy):
    dx, dy = p['x'] - ox, p['y'] - oy
    p['x'], p['y'] = round(ox - dy, 4), round(oy + dx, 4)
    p['w'], p['h'] = p['h'], p['w']


def main():
    os.makedirs(OUT, exist_ok=True)
    M = json.load(open(os.path.join(HERE, 'route', 'resize', 'stage1.json')))
    F = json.load(open(REV1))
    east = {'tracks': [t for t in F['tracks'] if t['net'] in ('CLK-12M-SHARED', 'LED0_R')],
            'vias': [v for v in F['vias'] if v['net'] in ('CLK-12M-SHARED', 'LED0_R')]}
    rip = {'remove': [t for t in F['remove'] if t['net'] == 'LED0_R'],
           'remove_vias': [v for v in F['remove_vias'] if v['net'] == 'LED0_R'],
           'moves': [{'ref': r, 'x': nx, 'y': ny, 'dx': round(nx - ox, 4), 'dy': round(ny - oy, 4)} for r, ox, oy, nx, ny, a in MOVES]}
    for p in M['pads']:
        for r, ox, oy, nx, ny, a in MOVES:
            if p['ref'] == r and a == 90:
                rot90(p, ox, oy)
    json.dump(M, open(os.path.join(OUT, 'base_compose.json'), 'w'))
    for p in M['pads']:
        for r, ox, oy, nx, ny, a in MOVES:
            if p['ref'] == r:
                p['x'] = round(p['x'] + nx - ox, 4)
                p['y'] = round(p['y'] + ny - oy, 4)
    json.dump(M, open(os.path.join(OUT, 'base_moved.json'), 'w'))
    tk = lambda t: (t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))  # noqa: E731
    have = {tk(t) for t in M['tracks']}
    assert all(tk(t) in have for t in rip['remove']), 'LED0_R removals not on this board'
    rk = {tk(t) for t in rip['remove']}
    vk = {(v['net'], round(v['x'], 3), round(v['y'], 3)) for v in rip['remove_vias']}
    M['tracks'] = [t for t in M['tracks'] if tk(t) not in rk] + east['tracks']
    M['vias'] = [v for v in M['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) not in vk] + \
        [dict(v, span=STK[STK.index(v['from']):STK.index(v['to']) + 1]) for v in east['vias']]
    json.dump(M, open(os.path.join(OUT, 'model.json'), 'w'))
    json.dump(rip, open(os.path.join(OUT, 'rip.json'), 'w'), indent=1)
    json.dump(east, open(os.path.join(OUT, 'east.json'), 'w'))
    print([(p['ref'], p['pad'], p['net'], p['x'], p['y']) for p in M['pads'] if p['ref'] in ('JP3', 'JP4')])


if __name__ == '__main__':
    main()
