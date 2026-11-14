"""Build the joint plan: 13-R plan + GND47 unlock + R133 (D14) + R134 (D15), routing with the largest design margin
that still routes; then prove with the checker copy."""
import json, sys, os
import engine as G, planio

def try_build(m, d14xy, d15xy, site=(38.22, 17.16)):
    G.DESIGN_MARGIN = m
    W = G.World()
    box = (35.0, 15.0, 41.6, 21.6)
    c14, e = G.build_XF(W, 14, 'Top', d14xy[0], d14xy[1], d14xy[2], box, pre=G.make_gnd47(site))
    if c14 is None:
        return None, 'D14 ' + e
    v, w = c14.verify(margin=0.0)
    if v:
        return None, 'D14 verify %s' % (v[:2],)
    P1 = planio.merge([c14.rec], note='u3_end D14')
    p1 = os.path.abspath('joint/_tmp_d14.json'); planio.write(P1, p1)
    W2 = G.World(p1)
    c15, e = G.build_XF(W2, 15, 'Top', d15xy[0], d15xy[1], d15xy[2], box)
    if c15 is None:
        return None, 'D15 ' + e
    v, w2 = c15.verify(margin=0.0)
    if v:
        return None, 'D15 verify %s' % (v[:2],)
    return (c14, c15, w, w2), None

if __name__ == '__main__':
    d14 = (39.6, 17.2, 0); d15 = tuple(float(v) for v in sys.argv[1:4]) if len(sys.argv) > 3 else (39.1, 16.6, 0)
    for m in (0.04, 0.03, 0.025, 0.02, 0.015, 0.01, 0.005, 0.0025):
        r, e = try_build(m, d14, d15)
        print('margin %.4f: %s' % (m, e or 'OK'))
        if r:
            break
    c14, c15, w, w2 = r
    print('D14 worst', {k: v[0] for k, v in w.items()}); print('D15 worst', {k: v[0] for k, v in w2.items()})
    tag = sys.argv[4] if len(sys.argv) > 4 else 'final'
    json.dump(dict(margin=m, d14=c14.rec, d15=c15.rec, notes=c14.notes + c15.notes), open('joint/%s_recs.json' % tag, 'w'), indent=1)
