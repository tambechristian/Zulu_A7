import json, engine as G, blockers
W = G.World()
res = []
def bf_cand(n):
    c = G.Cand(W, n)
    st, vuid = G.stub_and_via(W, n)
    for o in st: c.removed.add(o.uid)
    c.renet_u3()
    return c
def xf_cand(n, pre=None):
    c = G.Cand(W, n)
    if pre: pre(c)
    st, vuid = G.stub_and_via(W, n)
    for o in st: c.rename_track(o, 'SDRAM-D%d' % n)
    c.rename_via(vuid, 'SDRAM-D%d' % n); c.removed.add(vuid)
    c.renet_u3()
    return c
box = (33.5, 15.0, 42.0, 22.0)
for n in (13, 14, 15):
    u3 = W.pad_obj('U3', str(G.C.DPIN[n]), 'Bottom').xy
    via = G.FIRST_VIA[n]
    res.append(blockers.report(bf_cand(n), 'Bottom', 'SDRAM-D%d' % n, 0.10, u3, box, 'D%d BF feed: SDRAM-D%d Bottom w0.10 from U3-%d (stub removed)' % (n, n, G.C.DPIN[n]))[0])
    res.append(blockers.report(bf_cand(n), 'Bottom', 'D%d' % n, 0.10, via, box, 'D%d BF return: D%d Bottom w0.10 into the first via (stub removed, U3 pad = SDRAM-D%d)' % (n, n, n))[0])
    res.append(blockers.report(xf_cand(n), 'Bottom', 'SDRAM-D%d' % n, 0.10, via, box, 'D%d XF-Bottom: SDRAM-D%d Bottom w0.10 from the (renamed) first via' % (n, n))[0])
    res.append(blockers.report(xf_cand(n), 'Top', 'SDRAM-D%d' % n, 0.0762, via, box, 'D%d XF-Top: SDRAM-D%d Top w0.0762 from the first via land, no unlock' % (n, n))[0])
    res.append(blockers.report(xf_cand(n, G.make_gnd47((38.22, 17.16))), 'Top', 'SDRAM-D%d' % n, 0.0762, via, box, 'D%d XF-Top: SDRAM-D%d Top w0.0762 from the first via land, GND47 unlocked' % (n, n))[0])
json.dump(res, open('blockers.json', 'w'), indent=1)
for r in res:
    print(r['title']); print('   reach %.3f mm2 bbox %s' % (r['reach_area_mm2'], r['reach_bbox']))
    for k, v in r['boundary_objects'][:8]: print('      %5.2f mm  %s' % (v, k))
