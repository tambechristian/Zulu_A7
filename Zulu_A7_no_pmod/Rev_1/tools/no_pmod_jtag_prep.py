"""Zulu_a7_no_pmod: put the JTAG holes on the board. JP3 goes to the north strip (rotation 0), JP4 to the west edge
(rotation 90, pins running +y).

    python tools/no_pmod_jtag_prep.py <placed_model.json> <out_dir>

Writes model.json (router input), base_moved.json (route_check) and base_compose.json (compose_plan: rotated, not moved).
"""
import json
import os
import sys

MOVES = [('JP3', 64.30, 21.68, 14.29, 22.045, 0), ('JP4', 64.30, 3.72, 1.60, 14.64, 90)]


def rot(p, ox, oy, a):
    if a == 90:
        dx, dy = p['x'] - ox, p['y'] - oy
        p['x'], p['y'] = round(ox - dy, 4), round(oy + dx, 4)
        p['w'], p['h'] = p['h'], p['w']


def main():
    M = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for r, ox, oy, nx, ny, a in MOVES:
        for p in M['pads']:
            if p['ref'] == r:
                rot(p, ox, oy, a)
    json.dump(M, open(os.path.join(out, 'base_compose.json'), 'w'))
    for r, ox, oy, nx, ny, a in MOVES:
        for p in M['pads']:
            if p['ref'] == r:
                p['x'] = round(p['x'] + nx - ox, 4)
                p['y'] = round(p['y'] + ny - oy, 4)
    json.dump(M, open(os.path.join(out, 'model.json'), 'w'))
    json.dump(M, open(os.path.join(out, 'base_moved.json'), 'w'))
    json.dump({'remove': [], 'remove_vias': [],
               'moves': [{'ref': r, 'x': nx, 'y': ny, 'dx': round(nx - ox, 4), 'dy': round(ny - oy, 4)} for r, ox, oy, nx, ny, a in MOVES]},
              open(os.path.join(out, 'rip.json'), 'w'), indent=1)
    print([(p['ref'], p['pad'], p['net'], p['x'], p['y'], p['w'], p['layers'][:1], len(p['layers'])) for p in M['pads'] if p['ref'] in ('JP3', 'JP4')])


if __name__ == '__main__':
    main()
