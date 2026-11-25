"""No-PMOD Rev 4 (2026-11-24): the 3M 2908-05WB-MG microSD socket X3 in place of the Hirose DM3D-SF.

    python tools/route/x3_3m/prep.py     (after route_model.py -> tools/route/x3_3m/base.json, board saved after
                                          the ECO footprint swap)

The ECO swapped the footprint about the Hirose origin (8.80, 12.475), rotation 90 (card mouth west). Moves (user
choice 'A', 2026-11-24, docs/x3_3m_placement_options.png):
* X3  -> origin (10.60, 12.70), rotation 90: its lock pads G1/G2 clear the JTAG column, the body ends at x 17.70.
* BTN -> origin (20.35, 5.20), rotation 0 (was 90 at 18.00, 12.92): the free strip below the LED column. y 5.20 keeps
         the pad mask 0.46 mm from the X2 silk row and leaves VBATT a 0.62 mm Top corridor above the VU track.
* C158 -> +0.60 mm east (its pad 1 sat on X3's G4 tab).
Copper ripped (left to router.py): every Top track/via that fed an old pad of X3 (the Hirose pads, read from Rev_3's
board model), BTN or C158; other-net copper within 0.09 mm of a new pad on the Top; and all Top copper inside what was
taken as 3M's 'pattern prohibition area' (footprint X 6.16..6.64 -> board y 18.86..19.34). WRONG: the review re-derived
it as X 6.65..7.25, Y -7.40..5.50 (board x 5.10..18.00, y 19.35..19.95); prep2.py (pass 2) fixes the copper. The
prohibition strip goes into the router model as a no-net keepout pad. A ripped via takes its stack partners.
A same-net through via under a new pad is ripped too (no through via in an SMD pad). Moves carry pad_xy (exact
pads; compose_plan must not shift base_moved.json twice); BTN's w/h are already swapped in base_moved.json.
Writes model.json (router input), base_moved.json (pads as after the change) and rip.json.
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
REV3 = os.path.join(os.path.dirname(os.path.dirname(TOOLS)), 'Rev_3', 'tools', 'route', 'illustration', 'base.json')
X3_OLD, X3_NEW = (8.80, 12.475), (10.60, 12.70)
BTN_OLD, BTN_NEW = (18.00, 12.92), (20.35, 5.20)
C158_D = (0.60, 0.0)
STRIP = (5.10, 18.86, 17.70, 19.34)
EXPECT_X3 = {'1': (7.00, 10.76), 'G1': (3.15, 6.10), 'G4': (17.30, 17.65)}   # moved pad centres, from the datasheet


def on_pad(p, x, y):
    return abs(x - p['x']) <= p['w'] / 2 + 1e-4 and abs(y - p['y']) <= p['h'] / 2 + 1e-4


def seg_in_box(t, b):
    import math
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.05) + 1)
    hw = t['w'] / 2
    for i in range(n + 1):
        x = t['x1'] + (t['x2'] - t['x1']) * i / n
        y = t['y1'] + (t['y2'] - t['y1']) * i / n
        if b[0] - hw < x < b[2] + hw and b[1] - hw < y < b[3] + hw:
            return True
    return False


def main():
    M = json.load(open(os.path.join(HERE, 'base.json')))
    R3 = json.load(open(REV3))
    old = [dict(p) for p in R3['pads'] if p['ref'] == 'X3']
    assert len(old) == 14, len(old)                      # Hirose: 8 + G1-G4 + A/B
    old += [dict(p) for p in M['pads'] if p['ref'] in ('BTN', 'C158')]
    new = []
    for p in M['pads']:
        if p['ref'] == 'X3':
            p['x'] = round(p['x'] + X3_NEW[0] - X3_OLD[0], 4)
            p['y'] = round(p['y'] + X3_NEW[1] - X3_OLD[1], 4)
            new.append(p)
        elif p['ref'] == 'BTN':                          # rotation 90 -> 0 about the origin: (dx, dy) -> (dy, -dx)
            dx, dy = p['x'] - BTN_OLD[0], p['y'] - BTN_OLD[1]
            p['x'], p['y'] = round(BTN_NEW[0] + dy, 4), round(BTN_NEW[1] - dx, 4)
            p['w'], p['h'] = p['h'], p['w']
            new.append(p)
        elif p['ref'] == 'C158':
            p['x'] = round(p['x'] + C158_D[0], 4)
            new.append(p)
    x3 = {p['pad']: p for p in new if p['ref'] == 'X3'}
    assert len(x3) == 12, sorted(x3)
    for k, (ex, ey) in EXPECT_X3.items():
        assert abs(x3[k]['x'] - ex) < 0.02 and abs(x3[k]['y'] - ey) < 0.02, (k, x3[k]['x'], x3[k]['y'], ex, ey)
    json.dump(M, open(os.path.join(HERE, 'base_moved.json'), 'w'))
    rm_t, rm_v = [], []
    # (1) Top copper that fed an old pad
    for p in old:
        for t in M['tracks']:
            if t['layer'] == 'Top Layer' and t['net'] == p['net'] and p['net'] and t not in rm_t and (
                    on_pad(p, t['x1'], t['y1']) or on_pad(p, t['x2'], t['y2'])):
                rm_t.append(t)
        for v in M['vias']:
            if 'Top Layer' in v['span'] and v['net'] == p['net'] and p['net'] and on_pad(p, v['x'], v['y']) and v not in rm_v:
                rm_v.append(v)
    # (2) other-net copper too close to a new pad (all on the Top)
    for p in new:
        for t in M['tracks']:
            if t['layer'] == 'Top Layer' and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR and t not in rm_t:
                rm_t.append(t)
        for v in M['vias']:
            if 'Top Layer' in v['span'] and v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR and v not in rm_v:
                rm_v.append(v)
    # (2b) a same-net THROUGH via whose land overlaps a new SMD pad (release rule: no through via in an SMD pad)
    for p in new:
        for v in M['vias']:
            if v['span'][0] == 'Top Layer' and v['span'][-1] == 'Bottom Layer' and v['net'] == p['net']                     and pad_pt(p, v['x'], v['y']) < v['size'] / 2 and v not in rm_v:
                rm_v.append(v)
                for t in M['tracks']:                    # and the stubs that only served it
                    if t not in rm_t and t['net'] == v['net'] and any(abs(t[a] - v['x']) < 1e-3 and abs(t[b] - v['y']) < 1e-3
                                                                      for a, b in (('x1', 'y1'), ('x2', 'y2'))):
                        rm_t.append(t)
    # (3) the 3M pattern-prohibition strip
    for t in M['tracks']:
        if t['layer'] == 'Top Layer' and t not in rm_t and seg_in_box(t, STRIP):
            rm_t.append(t)
    for v in M['vias']:
        if 'Top Layer' in v['span'] and v not in rm_v and STRIP[0] - v['size'] / 2 < v['x'] < STRIP[2] + v['size'] / 2 \
                and STRIP[1] - v['size'] / 2 < v['y'] < STRIP[3] + v['size'] / 2:
            rm_v.append(v)
    for v in list(rm_v):
        for w in M['vias']:
            if w is not v and w not in rm_v and abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rm_v.append(w)
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    moves = [{'ref': 'X3', 'x': X3_NEW[0], 'y': X3_NEW[1], 'dx': round(X3_NEW[0] - X3_OLD[0], 4),
              'dy': round(X3_NEW[1] - X3_OLD[1], 4), 'pad1': [x3['1']['x'], x3['1']['y']],
              'pad_xy': {k: [p['x'], p['y']] for k, p in x3.items()}},
             {'ref': 'BTN', 'x': BTN_NEW[0], 'y': BTN_NEW[1], 'dx': round(BTN_NEW[0] - BTN_OLD[0], 4),
              'dy': round(BTN_NEW[1] - BTN_OLD[1], 4), 'rotation': 0,
              'pad_xy': {p['pad']: [p['x'], p['y']] for p in new if p['ref'] == 'BTN'},
              'pad1': [[p['x'], p['y']] for p in new if p['ref'] == 'BTN' and p['pad'] == '1'][0]},
             {'ref': 'C158', 'x': round(18.10 + C158_D[0], 4), 'y': 16.6499, 'dx': C158_D[0], 'dy': 0.0,
              'pad_xy': {p['pad']: [p['x'], p['y']] for p in new if p['ref'] == 'C158'}}]
    # pad_xy everywhere: base_moved.json already holds the moved pads, and compose_plan.apply() would add dx/dy again
    model = dict(M)
    model['pads'] = M['pads'] + [{'ref': 'KO', 'pad': 'X3STRIP', 'net': '', 'x': (STRIP[0] + STRIP[2]) / 2,
                                  'y': (STRIP[1] + STRIP[3]) / 2, 'shape': 'rect', 'w': STRIP[2] - STRIP[0],
                                  'h': STRIP[3] - STRIP[1], 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False}]
    json.dump(model, open(os.path.join(HERE, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': moves, 'jogs': []}, open(os.path.join(HERE, 'rip.json'), 'w'), indent=1)
    nets = sorted({o['net'] for o in rm_t + rm_v})
    print('removed %d tracks, %d vias on %d nets: %s' % (len(rm_t), len(rm_v), len(nets), nets))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d on %d nets: %s' % (sum(oc.values()), len(oc), dict(oc)))


if __name__ == '__main__':
    main()
