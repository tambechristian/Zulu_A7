"""No-PMOD Rev 4 (2026-11-25): route the UART activity LED LD6 + R136 (docs/rxtx_led.md). Copied from
tools/route/done_led/prep.py; only the new-pad set and the docstring differ.

    python tools/route/rxtx_led/prep.py    (input: tools/route/rxtx_led/base.json, a snapshot of the board re-read
                                            after NoPmodPlaceDoneLed.pas placed the parts; md5 in docs/done_led.md)

New pads: LD5 A (NetLD5_A) 21.40,14.185 / K (GND) 23.00,14.185 (LED0603, Top); R135 1 (FPGA-DONE) 20.45,13.885 /
2 (NetLD5_A) 20.45,14.485 (R0201 rot 90, Top). Opens: R135-1 to the FPGA-DONE net (U1 ball U12 / R4-7 / R4-15),
R135-2 to LD5-A, LD5-K to GND (a via to the L2 plane).
Ripped (left to router.py): other-net copper within 0.09 mm of a new pad on Top (tracks by segment distance, vias by
land), with a ripped via's stack partners and the tracks that end on a ripped via (all span layers -- the review's
note on btn_centre/prep.py). Any same-net through via under a new pad would be ripped too (release rule).
Keepouts: X3's prohibition strip and G1 bands (as btn_centre). Writes model.json, base_moved.json (= input) and rip.json.
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
NEW = {('LD6', 'A'), ('LD6', 'K'), ('R136', '1'), ('R136', '2')}
KEEP = [(3.40, 19.35, 16.30, 19.95), (0.30, 6.80, 2.60, 7.30), (2.40, 5.00, 2.90, 7.30), (0.30, 4.90, 2.90, 5.40)]


def main():
    M = json.load(open(os.path.join(HERE, 'base.json')))
    new = [p for p in M['pads'] if (p['ref'], p['pad']) in NEW]
    assert len(new) == 4, new
    json.dump(M, open(os.path.join(HERE, 'base_moved.json'), 'w'))
    rm_t, rm_v = [], []
    ids_t, ids_v = set(), set()

    def rip_t(t):
        if id(t) not in ids_t:
            ids_t.add(id(t))
            rm_t.append(t)

    def rip_v(v):
        if id(v) not in ids_v:
            ids_v.add(id(v))
            rm_v.append(v)
    for p in new:
        for t in M['tracks']:
            if t['layer'] in p['layers'] and t['net'] != p['net'] and pad_seg(p, t) < t['w'] / 2 + CLR:
                rip_t(t)
        for v in M['vias']:
            if not (set(v['span']) & set(p['layers'])):
                continue
            if v['net'] != p['net'] and pad_pt(p, v['x'], v['y']) < v['size'] / 2 + CLR:
                rip_v(v)
            elif v['net'] == p['net'] and v['span'][0] == 'Top Layer' and v['span'][-1] == 'Bottom Layer' \
                    and pad_pt(p, v['x'], v['y']) < v['size'] / 2:
                rip_v(v)
    for v in list(rm_v):                              # stack partners
        for w in M['vias']:
            if abs(w['x'] - v['x']) < 1e-4 and abs(w['y'] - v['y']) < 1e-4 and w['net'] == v['net']:
                rip_v(w)
    for v in rm_v:                                    # tracks ending on a ripped via, on its span layers
        for t in M['tracks']:
            if t['net'] == v['net'] and t['layer'] in v['span'] and any(
                    abs(t[a] - v['x']) < 1e-3 and abs(t[c] - v['y']) < 1e-3 for a, c in (('x1', 'y1'), ('x2', 'y2'))):
                rip_t(t)
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    model = dict(M)
    model['pads'] = M['pads'] + [{'ref': 'KO', 'pad': 'K%d' % i, 'net': '', 'x': (b[0] + b[2]) / 2, 'y': (b[1] + b[3]) / 2,
                                  'shape': 'rect', 'w': b[2] - b[0], 'h': b[3] - b[1], 'layers': ['Top Layer'],
                                  'drill': 0.0, 'plated': False} for i, b in enumerate(KEEP)]
    json.dump(model, open(os.path.join(HERE, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': [], 'jogs': []}, open(os.path.join(HERE, 'rip.json'), 'w'), indent=1)
    print('removed %d tracks, %d vias on nets %s' % (len(rm_t), len(rm_v), sorted({o['net'] for o in rm_t + rm_v})))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d: %s' % (sum(oc.values()), dict(oc)))


if __name__ == '__main__':
    main()
