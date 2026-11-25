"""No-PMOD Rev 4 (2026-11-24), second pass after the independent review of the 3M X3 swap.

    python tools/route/x3_3m/prep2.py     (base: tools/route/illustration/base.json, read from the saved board)

1. 3M's 'pattern prohibition area' (TS-2197-02 sheet 3) was mislocated in prep.py / NoPmodX3_3M.pas. Re-derived
   from the PDF vector hatch: footprint X 6.65..7.25 (0.35 inside to 0.25 outside the body's +X edge, under the
   shell's 0.60 flat flange), Y -7.40..5.50 -> board x 5.10..18.00, y 19.35..19.95 (X3 origin 10.60, 12.70, rot 90).
   USB5V0 ran there on Top (a 0.2 mm track and a through via at 14.625, 19.65) under the GND shell flange: ripped,
   and the strip goes into the router model as a no-net keepout.
2. The GND through via at (3.125, 7.05) sat 0.075 mm from the G1 lock pad (mask web ~0.1 mm; solder wicking off the
   load-bearing lock joint): ripped, with a keepout band y 6.80..7.30 north of G1.
Writes model.json (router input), base_moved.json and rip.json into tools/route/x3_3m/pass2/.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402

OUT = os.path.join(HERE, 'pass2')
STRIP = (5.10, 19.35, 18.00, 19.95)
G1BAND = (2.00, 6.80, 4.30, 7.30)
RIP_VIAS = [('USB5V0', 14.625, 19.65), ('GND', 3.125, 7.05)]


def near(a, b):
    return abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3


def in_box(x, y, b, m=0.0):
    return b[0] - m < x < b[2] + m and b[1] - m < y < b[3] + m


def main():
    os.makedirs(OUT, exist_ok=True)
    M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
    rm_t, rm_v = [], []
    for t in M['tracks']:
        if t['layer'] == 'Top Layer' and any(in_box(t['x1'] + (t['x2'] - t['x1']) * i / 20, t['y1'] + (t['y2'] - t['y1']) * i / 20,
                                                    STRIP, t['w'] / 2) for i in range(21)):
            rm_t.append(t)
    for net, x, y in RIP_VIAS:
        hit = [v for v in M['vias'] if v['net'] == net and near((v['x'], v['y']), (x, y))]
        assert len(hit) == 1, (net, x, y, len(hit))
        rm_v += hit
        rm_t += [t for t in M['tracks'] if t not in rm_t and t['net'] == net and
                 (near((t['x1'], t['y1']), (x, y)) or near((t['x2'], t['y2']), (x, y)))]
    nets = sorted({o['net'] for o in rm_t + rm_v})
    assert set(nets) <= {'USB5V0', 'GND'}, nets
    ids_t, ids_v = {id(t) for t in rm_t}, {id(v) for v in rm_v}
    json.dump(M, open(os.path.join(OUT, 'base_moved.json'), 'w'))
    M['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    M['vias'] = [v for v in M['vias'] if id(v) not in ids_v]
    model = dict(M)
    model['pads'] = M['pads'] + [
        {'ref': 'KO', 'pad': n, 'net': '', 'x': (b[0] + b[2]) / 2, 'y': (b[1] + b[3]) / 2, 'shape': 'rect',
         'w': b[2] - b[0], 'h': b[3] - b[1], 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False}
        for n, b in (('X3STRIP', STRIP), ('G1BAND', G1BAND))]
    json.dump(model, open(os.path.join(OUT, 'model.json'), 'w'))
    json.dump({'remove': rm_t, 'remove_vias': rm_v, 'moves': [], 'jogs': []}, open(os.path.join(OUT, 'rip.json'), 'w'), indent=1)
    print('removed %d tracks, %d vias on %s' % (len(rm_t), len(rm_v), nets))
    oc = C.open_count(C.islands(M))
    print('open connections now: %d %s' % (sum(oc.values()), dict(oc)))


if __name__ == '__main__':
    main()
