"""Exhaustive u3_end candidate search on a 0.05 mm R-centre grid, 4 rotations, for one (net, family).
usage: python search.py <net 13|14|15> <family BF|XF-Top|XF-Bottom> <unlock none|gnd47> [box x0,y0,x1,y1] [workers]
writes cands_<net>_<family>_<unlock>.json (every candidate that routes and passes the exact quick check) and
       rejects_<...>.json (per placement: first reason it failed)"""
import sys, json, math, os, time, collections
import multiprocessing as mp
import numpy as np

NET = int(sys.argv[1]); FAM = sys.argv[2]; UNL = sys.argv[3]
BOXES = {('BF', 15): (37.3, 15.6, 41.5, 21.0), ('XF-Bottom', 15): (37.3, 15.6, 41.5, 21.0), ('XF-Top', 15): (37.9, 15.3, 41.0, 18.7),
         ('XF-Top', 14): (35.3, 15.4, 41.0, 21.4), ('XF-Top', 13): (35.3, 15.4, 41.0, 21.4),
         ('BF', 14): (34.5, 15.6, 39.5, 21.0), ('BF', 13): (34.5, 15.6, 39.5, 21.0),
         ('XF-Bottom', 14): (34.5, 15.6, 39.5, 21.0), ('XF-Bottom', 13): (34.5, 15.6, 39.5, 21.0)}
RBOX = tuple(float(v) for v in sys.argv[4].split(',')) if len(sys.argv) > 4 and sys.argv[4] != '-' else BOXES[(FAM, NET)]
WORKERS = min(6, int(sys.argv[5])) if len(sys.argv) > 5 else 6
SITE = (38.22, 17.16)
STEP = 0.05


def route_box(x, y):
    return (min(x, RBOX[0]) - 1.2, min(y, RBOX[1]) - 1.2, max(x, RBOX[2]) + 1.2, max(y, RBOX[3]) + 1.2)


def init():
    global G, W
    import engine as G_
    G = G_
    W = G.World(os.environ.get('U3END_BASE', G.base.PLAN13))


def pre_fn():
    return G.make_gnd47(SITE) if UNL == 'gnd47' else None


def pad_ok(x, y, rot, side):
    """exact pad check (clearance incl. the family's relabels, mask web, body) before routing"""
    n = NET
    c = G.Cand(W, n)
    pre = pre_fn()
    if pre:
        pre(c)
    st, vuid = G.stub_and_via(W, n)
    if FAM == 'BF':
        for o in st:
            c.removed.add(o.uid)
    else:
        for o in st:
            c.relabel[o.uid] = 'SDRAM-D%d' % n
        c.relabel[vuid] = 'SDRAM-D%d' % n
    c.renet_u3()
    c.add_part(G.REF[n], side, x, y, rot)
    v, w = c.verify(margin=G.DESIGN_MARGIN)
    if v:
        return 'pad: %s %s' % (v[0][0], v[0][-1])
    hard, soft, cc = c.body_checks(side, x, y, rot, G.REF[n])
    if hard:
        return 'body: ' + hard[0]
    return None


def work(task):
    x, y, rot = task
    side = 'Bottom' if FAM in ('BF', 'XF-Bottom') else 'Top'
    why = pad_ok(x, y, rot, side)
    if why:
        return dict(x=x, y=y, rot=rot, ok=False, why=why)
    box = route_box(x, y)
    pre = pre_fn()
    out = None
    try:
        if FAM == 'BF':
            for order in (0, 1):
                c, err = G.build_BF(W, NET, x, y, rot, box, order=order, pre=pre)
                if c:
                    break
        else:
            c, err = G.build_XF(W, NET, side, x, y, rot, box, pre=pre)
    except Exception as e:
        return dict(x=x, y=y, rot=rot, ok=False, why='exception %r' % (e,))
    if c is None:
        return dict(x=x, y=y, rot=rot, ok=False, why='route: ' + err)
    v, w = c.verify(margin=G.DESIGN_MARGIN)
    if v:
        return dict(x=x, y=y, rot=rot, ok=False, why='verify: %s' % (v[0],))
    hard, soft, cc = c.body_checks(side, x, y, rot, G.REF[NET])
    m = metrics(c)
    return dict(x=x, y=y, rot=rot, ok=True, side=side, family=c.topology, unlock=UNL, rec=c.rec, notes=c.notes,
                worst={k: v_[0] for k, v_ in w.items()}, worst_detail=w, soft=soft, cc=cc, metrics=m)


def metrics(c):
    n = NET
    sd = 'SDRAM-D%d' % n
    feed = sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in c.rec['tracks'] if t['net'] == sd)
    dn = sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in c.rec['tracks'] if t['net'] == 'D%d' % n)
    rm = sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in c.rec['remove'] if t['net'] == 'D%d' % n and t.get('why') != 'rename')
    nv = len([v for v in c.rec['vias'] if v.get('why') != 'rename' and v['net'] in (sd, 'D%d' % n)])
    return dict(sdram_side_track_mm=round(feed, 3), dn_added_mm=round(dn, 3), dn_removed_mm=round(rm, 3), new_signal_vias=nv,
                net_added_mm=round(feed + dn - rm, 3))


def main():
    rots = (0, 90, 180, 270)
    xs = np.round(np.arange(RBOX[0], RBOX[2] + 1e-6, STEP), 3)
    ys = np.round(np.arange(RBOX[1], RBOX[3] + 1e-6, STEP), 3)
    tasks = [(float(x), float(y), r) for x in xs for y in ys for r in rots]
    t0 = time.time()
    res = []
    with mp.Pool(WORKERS, initializer=init) as pool:
        for r in pool.imap_unordered(work, tasks, chunksize=64):
            res.append(r)
    ok = [r for r in res if r['ok']]
    rej = collections.Counter(r['why'].split(':')[0] + ':' + r['why'].split(':')[1][:60] if ':' in r['why'] else r['why'] for r in res if not r['ok'])
    tag = '%d_%s_%s%s' % (NET, FAM, UNL, os.environ.get('U3END_SUFFIX', ''))
    json.dump(dict(base_plan=os.environ.get('U3END_BASE', G.base.PLAN13) if False else os.environ.get('U3END_BASE', 'dq_series_r_plan.json'), net='D%d' % NET, family=FAM, unlock=UNL, rbox=RBOX, step=STEP, tasks=len(tasks), legal=len(ok), seconds=round(time.time() - t0, 1),
                   cands=ok), open('cands_%s.json' % tag, 'w'), indent=0)
    json.dump(dict(reasons=rej.most_common(), rejects=[r for r in res if not r['ok']]), open('rejects_%s.json' % tag, 'w'))
    print('%s: %d placements tried, %d legal (quick exact check), %.0f s' % (tag, len(tasks), len(ok), time.time() - t0))
    for k, v in rej.most_common(12):
        print('   %6d  %s' % (v, k))


if __name__ == '__main__':
    main()
