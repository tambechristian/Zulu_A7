"""Strategy C: regional rip of the zone x 49.0-61.0 on a transplant variant.

    python scripts/zone.py <variant>          variant: '' (clean), _stubs, _ripja, _stubs_ripja

Rips, from prep/after_transplant<variant>.json, every track whose x-range meets [X0, X1] and every via whose centre
lies in it, for every net that is not power / plane / SDRAM / USB. Writes
    work/zone<variant>.json        the router input (pads of base_new, copper minus the rip)
    work/rip<variant>.json         {'ripped_base': [...base_cur objects], 'ripped_add_tracks': [...], 'ripped_add_vias': [...],
                                    'nets': [...]} - the rip split into TARGET copper (new removals) and transplant additions
                                    (dropped from the plan)
and prints the opens and the dead copper the rip leaves outside the zone.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.dirname(HERE)
PREP = os.path.join(os.path.dirname(CDIR), 'prep')
sys.path.insert(0, os.path.join(CDIR, 'tools'))
import router as R  # noqa: E402  (C/tools/router.py = SOURCE's router: SDRAM-Dn set, through-in-pad mask)
import route_conn as RC  # noqa: E402
import prune_stubs as PS  # noqa: E402

X0, X1 = 49.0, 61.0
STACK = R.STACK
POWER = {'GND', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VCCADC', 'GNDADC', 'VU', 'USB5V0', 'VBATT', 'FT-VCORE', 'FT-VPHY',
         'FT-VPLL', 'NetL1_1', 'NetL2_1', 'NetL3_1', 'VCC5V0', 'VBUS'}
USB = {'USB_D_P', 'USB_D_N'}


def span(v):
    return v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def r4(x):
    return round(x, 4)


def tkey(t):
    e = sorted([(r4(t['x1']), r4(t['y1'])), (r4(t['x2']), r4(t['y2']))])
    return (t['net'], t['layer'], r4(t['w'])) + e[0] + e[1]


def vkey(v):
    s = span(v)
    return (v['net'], r4(v['x']), r4(v['y']), r4(v['hole']), s[0], s[-1])


def is_power(net):
    if net in POWER or net in R.SDRAM or net in USB:
        return True
    w = [R.width(net, l) for l in R.ROUTE]
    return max(w) > 0.1001 and net not in R.SDRAM


def in_zone_t(t):
    return max(t['x1'], t['x2']) >= X0 and min(t['x1'], t['x2']) <= X1


def in_zone_v(v):
    return X0 <= v['x'] <= X1


def main():
    var = sys.argv[1] if len(sys.argv) > 1 else ''
    M = json.load(open(os.path.join(PREP, 'after_transplant%s.json' % var)))
    Bc = json.load(open(os.path.join(PREP, 'base_cur.json')))
    plan = json.load(open(os.path.join(PREP, 'transplant%s.json' % var)))
    nets = sorted({t['net'] for t in M['tracks'] if in_zone_t(t)} | {v['net'] for v in M['vias'] if in_zone_v(v)})
    rip_nets = [n for n in nets if n and not is_power(n)]
    keep_nets = [n for n in nets if n and is_power(n)]
    rs = set(rip_nets)
    rt = [t for t in M['tracks'] if t['net'] in rs and in_zone_t(t)]
    rv = [v for v in M['vias'] if v['net'] in rs and in_zone_v(v)]
    # classify: transplant addition or TARGET (base_cur) copper
    add_t = Counter(tkey(t) for t in plan['tracks'])
    add_v = Counter(vkey(v) for v in plan['vias'])
    cur_t = Counter(tkey(t) for t in Bc['tracks'])
    cur_v = Counter(vkey(v) for v in Bc['vias'])
    rm_t = Counter(tkey(t) for t in plan['remove'])
    rm_v = Counter(vkey(v) for v in plan['remove_vias'])
    ra_t, ra_v, rb_t, rb_v = [], [], [], []
    for t in rt:
        k = tkey(t)
        if add_t[k] > 0:
            add_t[k] -= 1
            ra_t.append(t)
        else:
            assert cur_t[k] - rm_t[k] > 0, ('rip of unknown track', t)
            cur_t[k] -= 1
            rb_t.append(t)
    for v in rv:
        k = vkey(v)
        if add_v[k] > 0:
            add_v[k] -= 1
            ra_v.append(v)
        else:
            assert cur_v[k] - rm_v[k] > 0, ('rip of unknown via', v)
            cur_v[k] -= 1
            rb_v.append(v)
    ids_t, ids_v = {id(t) for t in rt}, {id(v) for v in rv}
    Z = dict(M)
    Z['tracks'] = [t for t in M['tracks'] if id(t) not in ids_t]
    Z['vias'] = [dict(v, span=span(v)) for v in M['vias'] if id(v) not in ids_v]
    os.makedirs(os.path.join(CDIR, 'work'), exist_ok=True)
    json.dump(Z, open(os.path.join(CDIR, 'work', 'zone%s.json' % var), 'w'))
    json.dump({'variant': var, 'zone': [X0, X1], 'nets': rip_nets, 'kept_power_nets': keep_nets,
               'ripped_base_tracks': rb_t, 'ripped_base_vias': [dict(v, span=span(v)) for v in rb_v],
               'ripped_add_tracks': ra_t, 'ripped_add_vias': [dict(v, span=span(v)) for v in ra_v]},
              open(os.path.join(CDIR, 'work', 'rip%s.json' % var), 'w'), indent=0)
    oc0 = RC.open_count(RC.islands(M))
    oc = RC.open_count(RC.islands(Z))
    dt, dv, _, _ = PS.analyse(Z)
    out_dt = [t for t in dt if not in_zone_t(t)]
    out_dv = [v for v in dv if not in_zone_v(v)]
    print('variant %r: rip %d nets (%d tracks: %d TARGET + %d added; %d vias: %d TARGET + %d added)' % (
        var, len(rip_nets), len(rt), len(rb_t), len(ra_t), len(rv), len(rb_v), len(ra_v)))
    print('  kept power nets in zone:', keep_nets)
    print('  opens before rip %d, after %d on %d nets' % (sum(oc0.values()), sum(oc.values()), len(oc)))
    print('  dead after rip: %d tracks %d vias (outside the zone %d / %d)' % (len(dt), len(dv), len(out_dt), len(out_dv)))
    print('  open nets:', ' '.join('%s:%d' % kv for kv in sorted(oc.items())))


if __name__ == '__main__':
    main()
