"""Zulu_a7_no_pmod Rev 2: cut the board to 2.4 x 1.0 in by reusing Rev 1's resize plan.

    python tools/no_pmod_resize_prep.py

East of x ~43 mm the Rev 2 copper is identical to Rev 1's, and Rev 1's stage-1 plan (Rev_1/tools/route/no_pmod/final.json)
only touches x >= 45.8, so it is reused as it stands, minus:
  - its removals on the Pmod nets (already deleted here by NoPmod_RemoveCopper), and
  - the R5-1 GND tie via at (57.55, 20.30), which already exists on the board (Rev 1 had to delete the duplicate).
Writes route/resize/: base_compose.json (pads gone, R5 rotated about its old origin, board 60.96 wide), rip.json,
plan.json (Rev 1's additions) and base_moved.json (route_check base: parts moved, R5 rotated).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'route', 'resize')
REV1 = os.path.join(HERE, '..', '..', 'Rev_1', 'tools', 'route', 'no_pmod', 'final.json')
PMOD = {'JA%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)} | {'PMOD-%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)}


def main():
    os.makedirs(OUT, exist_ok=True)
    M = json.load(open(os.path.join(HERE, 'route', 'no_pmod', 'after.json')))
    F = json.load(open(REV1))
    M['board'] = {'w': 60.96, 'h': 25.4}
    C0 = dict(M, pads=[dict(p, x=round(2 * 61.10 - p['x'], 4)) if p['ref'] == 'R5' else p for p in M['pads']])
    json.dump(C0, open(os.path.join(OUT, 'base_compose.json'), 'w'))
    mv = {m['ref']: m for m in F['moves']}
    B = dict(C0, pads=[dict(p) for p in C0['pads']])
    for p in B['pads']:
        if p['ref'] in mv:
            p['x'] = round(p['x'] + mv[p['ref']]['dx'], 4)
            p['y'] = round(p['y'] + mv[p['ref']]['dy'], 4)
    json.dump(B, open(os.path.join(OUT, 'base_moved.json'), 'w'))
    rip = {'remove': [t for t in F['remove'] if t['net'] not in PMOD],
           'remove_vias': [v for v in F['remove_vias'] if v['net'] not in PMOD], 'moves': F['moves']}
    dup = lambda v: v['net'] == 'GND' and abs(v['x'] - 57.55) < 1e-3 and abs(v['y'] - 20.3) < 1e-3  # noqa: E731
    plan = {'tracks': F['tracks'], 'vias': [v for v in F['vias'] if not dup(v)]}
    json.dump(rip, open(os.path.join(OUT, 'rip.json'), 'w'))
    json.dump(plan, open(os.path.join(OUT, 'plan.json'), 'w'))
    # every removal must exist on this board
    tk = lambda t: (t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3))  # noqa: E731
    have = {tk(t) for t in M['tracks']}
    miss = [t for t in rip['remove'] if tk(t) not in have]
    vh = {(v['net'], round(v['x'], 3), round(v['y'], 3)) for v in M['vias']}
    missv = [v for v in rip['remove_vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3)) not in vh]
    print('removals %d tracks (%d not on this board), %d vias (%d not on this board); adds %d tracks, %d vias; dropped duplicate vias %d'
          % (len(rip['remove']), len(miss), len(rip['remove_vias']), len(missv), len(plan['tracks']), len(plan['vias']),
             sum(1 for v in F['vias'] if dup(v))))


if __name__ == '__main__':
    main()
