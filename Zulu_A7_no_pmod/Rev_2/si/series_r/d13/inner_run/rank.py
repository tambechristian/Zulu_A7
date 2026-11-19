"""Per-candidate margins of the truly new geometry (connectors, columns, R pads; split pieces are sub-segments of
existing copper and inherit its margins) + pairwise D14 x D15 (x D13) compatibility, exact geometry."""
import json, math, itertools, collections, sys
import search as S
from lib import C
NETS = ['D13', 'D14', 'D15']


def objs_of(c):
    news = []
    for (L, nn, x1, y1, x2, y2, w, why) in c['add']:
        if why in ('connector', 'piece'):
            o = S.mk('track', L, nn, ('C', x1, y1, x2, y2, w / 2), w=w); news.append((o, why))
    for v in c['cols']:
        i0, i1 = C.CU.index(v['frm']), C.CU.index(v['to'])
        span = C.CU[min(i0, i1):max(i0, i1) + 1]
        for L in span:
            o = S.mk('via', L, v['net'], ('C', v['x'], v['y'], v['x'], v['y'], v['size'] / 2), span=span, hole=0.15, xy=(v['x'], v['y']))
            news.append((o, 'col'))
    for (x, y), nn, pn in ((c['pad1'], 'SDRAM-' + c['net'], '1'), (c['pad2'], c['net'], '2')):
        o = S.mk('pad', c['side'], nn, ('R', x, y, 0.15, 0.15), xy=(x, y), ref='RNEW', pad=pn); news.append((o, 'pad'))
    return news


def new_margin(c):
    runL, segs, used = RUN[c['net']]
    fam = S.family(c['net'])
    rmids = set()
    for t in c['rm']:
        for o in used:
            if C.same((o.shape[1], o.shape[2]), (t['x1'], t['y1'])) and C.same((o.shape[3], o.shape[4]), (t['x2'], t['y2'])):
                rmids.add(id(o))
    best = (9.0, None)
    for o, why in objs_of(c):
        if why == 'piece':
            continue
        v = S.worst_gap(o, o.layer, fam, rmids)
        if v[0] < best[0]:
            best = (v[0], '%s %s vs %s' % (why, o.layer, v[1]))
    return best


def pair_ok(a, b):
    """exact: new objects of a vs new objects of b (different nets), drills, mask, component boxes"""
    A, Bo = objs_of(a), objs_of(b)
    worst = (9.0, None)
    for o, ow in A:
        for q, qw in Bo:
            if o.layer != q.layer:
                continue
            d = C.dist(o.shape, q.shape)
            g = C.gap_rule(o, q, o.layer)
            if d - g < worst[0]:
                worst = (d - g, 'clearance %s %s/%s' % (o.layer, ow, qw))
    for va in a['cols']:
        for vb in b['cols']:
            sa = set(C.CU[min(C.CU.index(va['frm']), C.CU.index(va['to'])):max(C.CU.index(va['frm']), C.CU.index(va['to'])) + 1])
            sb = set(C.CU[min(C.CU.index(vb['frm']), C.CU.index(vb['to'])):max(C.CU.index(vb['frm']), C.CU.index(vb['to'])) + 1])
            if sa & sb:
                v = math.hypot(va['x'] - vb['x'], va['y'] - vb['y']) - 0.15 - 0.24
                if v < worst[0]:
                    worst = (v, 'hole-to-hole')
    if a['side'] == b['side']:
        for pa in (a['pad1'], a['pad2']):
            for pb in (b['pad1'], b['pad2']):
                d = C.d_rect_rect((pa[0], pa[1], 0.2, 0.2), (pb[0], pb[1], 0.2, 0.2))
                v = d - 0.10 if d > 0 else -1
                if v < worst[0]:
                    worst = (v, 'mask sliver')
        cc = S.rr(a['rbox'], b['rbox']) - 0.254
        if cc < worst[0]:
            worst = (cc, 'component clearance R-R 0.254')
    return worst


RUN = {n: S.run_poly(n) for n in NETS}
if __name__ == '__main__':
    proofs = {}
    import glob
    for fp in glob.glob('proofs/proof_*.jsonl'):
        for l in open(fp):
            r = json.loads(l)
            if 'error' not in r:
                proofs[(r['net'], r['i'])] = r
    C_ = {}
    for n in NETS:
        pf = json.load(open('prefilter_%s.json' % n))
        for i, c in enumerate(pf['candidates']):
            c['i'] = i
            c['new_margin'] = [round(v, 4) if isinstance(v, float) else v for v in new_margin(c)]
            pr = proofs.get((n, i))
            c['proof'] = None if pr is None else pr['PASS']
            c['body_ok'] = c['compclear_body'][0] >= 0.254 - 1e-6 and c['compclear_altium'][0] >= 0.254 - 1e-6
        C_[n] = pf['candidates']
        json.dump(C_[n], open('ranked_%s.json' % n, 'w'))
        ok = [c for c in C_[n] if c['body_ok']]
        print(n, len(C_[n]), 'body/compclear ok', len(ok), 'proved', sum(1 for c in C_[n] if c['proof']), 'proof fail', sum(1 for c in C_[n] if c['proof'] is False))
        for c in sorted(ok, key=lambda c: -c['new_margin'][0])[:5]:
            print('   #%d %s rot%d (%.3f,%.3f) newmargin %s conn %.3f/%.3f cc %s' % (c['i'], c['side'], c['rot'], c['cx'], c['cy'], c['new_margin'], c['conn1'], c['conn2'], c['compclear_altium']))
