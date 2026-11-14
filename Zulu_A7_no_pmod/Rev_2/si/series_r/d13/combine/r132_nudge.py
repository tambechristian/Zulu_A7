"""R132 (u3_end D13 at (38.75,16.30) rot 180) has a Top mask web of exactly 0.100 to R131-1 (margin +0.0000).
Sweep a small north nudge dy of the whole part with its pad-2 column; only the two attach points move (the Top
SDRAM-D13 track's last vertex at pad 1 and the L3 re-join's first vertex at the column).  Every pose is measured
exactly on the full triple (13-R + gnd47 + R132 + chosen R133/R134) with lib.margins.
usage: python r132_nudge.py <d14_id> <d15_id>  -> work/r132_nudge.json"""
import json, os, sys, copy
import lib
from rank import ekey

W = os.path.join(lib.HERE, 'work')


def nudge(delta, dx, dy, pts):
    d = copy.deepcopy(delta)
    def mv(x, y):
        for (px, py) in pts:
            if abs(x - px) < 1e-6 and abs(y - py) < 1e-6:
                return lib.r4(x + dx), lib.r4(y + dy), True
        return x, y, False
    for t in d['tracks']:
        t['x1'], t['y1'], _ = mv(t['x1'], t['y1'])
        t['x2'], t['y2'], _ = mv(t['x2'], t['y2'])
    for v in d['vias'] + d['microvias']:
        v['x'], v['y'], _ = mv(v['x'], v['y'])
    for pr in d['parts']:
        pr['x'], pr['y'] = lib.r4(pr['x'] + dx), lib.r4(pr['y'] + dy)
        for k in ('pad1', 'pad2'):
            pr[k]['x'], pr[k]['y'] = lib.r4(pr[k]['x'] + dx), lib.r4(pr[k]['y'] + dy)
    return d


def main():
    pools, unl = lib.load_pools()
    base = lib.load_base()
    r132 = [c for c in pools['D13'] if c['id'].endswith('38.75_16.3_r180')][0]
    a = [c for c in pools['D14'] if c['id'].endswith(':' + sys.argv[1])][0]
    b = [c for c in pools['D15'] if c['id'].endswith(':' + sys.argv[2])][0]
    pr = r132['delta']['parts'][0]
    pts = [(pr['pad1']['x'], pr['pad1']['y']), (pr['pad2']['x'], pr['pad2']['y'])]
    P0, _ = lib.merge(base, [], 'base')
    p = os.path.join(W, 'n_base.json'); json.dump(P0, open(p, 'w'))
    k13 = {ekey(e) for e in lib.margins(p)['all']}
    out = []
    for dx in (0.0,):
        for dy in (0.0, 0.001, 0.0015, 0.002, 0.0025, 0.003, 0.0035, 0.004):
            d = nudge(lib.polish(r132['delta']), dx, dy, pts)
            P, errs = lib.merge(base, [unl['gnd47'], d, lib.polish(a['delta']), lib.polish(b['delta'])], 'nudge')
            p = os.path.join(W, 'n_%g.json' % dy); json.dump(P, open(p, 'w'))
            m = lib.margins(p)
            own = [e for e in m['all'] if ekey(e) not in k13]
            r132own = [e for e in own if 'R132' in e[2] + e[3] or 'D13' in e[2] + e[3] or 'GND (38.220' in e[2] + e[3]]
            print('dy %+.4f errs %s apply %s own_min %+.4f  R132/gnd47 smallest:' % (dy, errs, m['apply_errors'], own[0][0]))
            for e in r132own[:4]:
                print('      ', e)
            out.append(dict(dx=dx, dy=dy, own_min=own[0][0], r132_smallest=r132own[:8]))
            os.remove(p)
    json.dump(out, open(os.path.join(W, 'r132_nudge.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
