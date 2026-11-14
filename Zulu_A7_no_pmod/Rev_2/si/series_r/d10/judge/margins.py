"""Per-object worst copper margin for the Top objects that differ from the 12-R plan near the D8/D10/D11 bundle
(x 38.3-40.5, y 13-15.5), using check.py's own geometry/rules on the applied plan.
Usage: python margins.py <plan.json> <tag>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
plan, tag = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], '--plan', plan, '--tag', tag]
sys.path.insert(0, HERE)
import check as C  # noqa: E402

E = C.load_plan()
pads, tracks, vias, newflags, errors = C.apply(E)
assert not errors, errors
objs = C.build_objs(pads, tracks, vias, newflags)
G = C.Grid(objs, 0.5)
rows = []
for o in objs:
    if not o.new or o.layer != 'Top':
        continue
    x0, y0, x1, y1 = C.bbox(o.shape)
    if not (x1 > 38.3 and x0 < 40.5 and y1 > 13.0 and y0 < 15.5):
        continue
    best = None
    for q in G.near('Top', C.bbox(o.shape), 0.3):
        if q is o or q.uid == o.uid or (q.net == o.net and o.net):
            continue
        m = C.dist(o.shape, q.shape) - C.gap_rule(o, q, 'Top')
        if best is None or m < best[0]:
            best = (m, q.tag)
    rows.append((round(best[0], 4) if best else None, o.tag, best[1] if best else ''))
rows.sort(key=lambda r: (r[0] is None, r[0]))
with open(os.path.join(HERE, 'margins_%s.txt' % tag), 'w') as f:
    for r in rows:
        s = '%+.4f  %-75s vs %s' % r if r[0] is not None else str(r)
        print(s)
        f.write(s + '\n')
