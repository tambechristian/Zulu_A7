"""Stage 7 fan-out (2026-10-31, user: "go ahead with the via-in-pad laser microvias on U1"): every U1 ball with a
net gets a laser via-in-pad column at its centre -- GND balls Top>L2 (to the plane), VCC3V3 balls Top..L5 (the
stack_tie column: two laser vias, the buried L3>L4, one more laser via), every other net Top>L2>L3 (two stacked
laser vias) -- so the ball escapes on L3 at its own position; no dogbone, no Top neck, no interstitial site.
Laser via 0.10 mm hole / 0.25 mm land (PCBWay's published floor: 0.10 drill, 0.076 ring; the U1 land must grow
from 0.225 to 0.25 on the board). Rings 3-5 of the package are vacant and take the buried L3>L4 vias the router
needs to leave the field on L4.

    python tools/vip_fanout.py [tools/route/model.json] [outdir=tools/route/stage7] [--land 0.25]

--land sets every U1 pad to that size in the written models (the board's lands after the via-in-pad change; the
final plan must be route_checked against such a model before placement).

Writes model_bare.json (the board with every track and via removed), vip.json (the columns as a plan),
model_vip.json (bare + columns, the router's base), and prints the counts."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_check import span  # noqa: E402

LASER = (0.25, 0.10)                         # --laser S/H overrides (0.225/0.075: lands stay 0.225)
BURIED = (0.27, 0.15)
COLUMN = {'GND': [('Top Layer', 'L2-GND', LASER)],
          'VCC3V3': [('Top Layer', 'L2-GND', LASER), ('L2-GND', 'L3-SIG', LASER), ('L3-SIG', 'L4-SIG', BURIED),
                     ('L4-SIG', 'L5-VCC3V3', LASER)]}
SIGNAL = [('Top Layer', 'L2-GND', LASER), ('L2-GND', 'L3-SIG', LASER)]


def main():
    global LASER, COLUMN, SIGNAL
    argv = list(sys.argv[1:])
    if '--laser' in argv:
        i = argv.index('--laser')
        LASER = tuple(float(v) for v in argv[i + 1].split('/'))
        del argv[i:i + 2]
        COLUMN = {'GND': [('Top Layer', 'L2-GND', LASER)],
                  'VCC3V3': [('Top Layer', 'L2-GND', LASER), ('L2-GND', 'L3-SIG', LASER), ('L3-SIG', 'L4-SIG', BURIED),
                             ('L4-SIG', 'L5-VCC3V3', LASER)]}
        SIGNAL = [('Top Layer', 'L2-GND', LASER), ('L2-GND', 'L3-SIG', LASER)]
    scheme = 'all'
    if '--scheme' in argv:                      # rings: ring 0 bare (Top escape), ring 1 Top>L3, ring >= 2 Top>L4
        i = argv.index('--scheme')
        scheme = argv[i + 1]
        del argv[i:i + 2]
    sys.argv = [sys.argv[0]] + argv
    args = [a for a in sys.argv[1:] if not a.startswith('--') and a != sys.argv[sys.argv.index('--land') + 1]] if '--land' in sys.argv else sys.argv[1:]
    src = args[0] if args else os.path.join(HERE, 'route', 'model.json')
    out = args[1] if len(args) > 1 else os.path.join(HERE, 'route', 'stage7')
    os.makedirs(out, exist_ok=True)
    M = json.load(open(src))
    land = float(sys.argv[sys.argv.index('--land') + 1]) if '--land' in sys.argv else 0.0
    if land:                                       # the board's U1 lands after the change (0.25): every U1 pad
        M['pads'] = [dict(p, w=land, h=land) if p['ref'] == 'U1' else p for p in M['pads']]
    bare = dict(M, tracks=[], vias=[])
    json.dump(bare, open(os.path.join(out, 'model_bare.json'), 'w'))
    vias, kinds = [], {}
    u1 = [p for p in M['pads'] if p['ref'] == 'U1']
    xs, ys = sorted({round(p['x'], 3) for p in u1}), sorted({round(p['y'], 3) for p in u1})
    pitch = 0.5
    nmax = max(len(xs), len(ys)) - 1
    def ring(p):
        c = int(round((p['x'] - xs[0]) / pitch))
        r = int(round((p['y'] - ys[0]) / pitch))
        return min(c, nmax - c, r, nmax - r)
    rings = {}
    for p in M['pads']:
        if p['ref'] != 'U1' or not p['net']:
            continue
        col = COLUMN.get(p['net'], SIGNAL)
        if scheme == 'rings' and p['net'] not in COLUMN:
            rg = ring(p)
            rings[rg] = rings.get(rg, 0) + 1
            col = [] if rg == 0 else (SIGNAL if rg == 1 else SIGNAL + [('L3-SIG', 'L4-SIG', BURIED)])
        kinds[p['net']] = len(col)
        for lo, hi, (size, hole) in col:
            vias.append({'net': p['net'], 'x': p['x'], 'y': p['y'], 'size': size, 'hole': hole, 'from': lo, 'to': hi})
    n_gnd = sum(1 for p in M['pads'] if p['ref'] == 'U1' and p['net'] == 'GND')
    n_v33 = sum(1 for p in M['pads'] if p['ref'] == 'U1' and p['net'] == 'VCC3V3')
    n_sig = sum(1 for p in M['pads'] if p['ref'] == 'U1' and p['net'] and p['net'] not in COLUMN)
    plan = {'vias': vias, 'tracks': [], 'remove': [],
            'log': ['stage 7 via-in-pad fan-out: %d GND Top>L2, %d VCC3V3 Top..L5 columns, %d signal Top>L3 stacks; '
                    'laser %.2f/%.2f, buried %.2f/%.2f' % (n_gnd, n_v33, n_sig, LASER[0], LASER[1], BURIED[0], BURIED[1])]}
    json.dump(plan, open(os.path.join(out, 'vip.json'), 'w'), indent=0)
    mv = dict(bare, vias=[dict(v, span=span(v)) for v in vias])
    json.dump(mv, open(os.path.join(out, 'model_vip.json'), 'w'))
    if scheme == 'rings':
        plan['log'].append('rings scheme: signal balls per ring %s (ring 0 bare, 1 Top>L3, >=2 Top>L4)' % sorted(rings.items()))
        json.dump(plan, open(os.path.join(out, 'vip.json'), 'w'), indent=0)
        print(plan['log'][1])
    print(plan['log'][0])
    print('%d via objects on %d U1 balls (%d no-net balls untouched); model %d pads, bare of %d tracks and %d vias' % (
        len(vias), n_gnd + n_v33 + n_sig, sum(1 for p in M['pads'] if p['ref'] == 'U1' and not p['net']), len(M['pads']),
        len(M['tracks']), len(M['vias'])))


if __name__ == '__main__':
    main()
