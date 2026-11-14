import sys, numpy as np, glob, os, json
sys.path.insert(0, '../..')
import bus_sim as B
for f in sorted(glob.glob('../../wave/*_typ.npz'))[:40]:
    d = np.load(f); t, v, vp, vd = d['t'], d['rx_die'], d['rx_pin'], d['tx_die']
    m = B.measure(t, v, 3.3)
    early = t < 1e-9
    imax, imin = v.argmax(), v.argmin()
    # independent: ringback margin = how close it comes back to the threshold after first crossing (V above VIH / below VIL)
    marg = []
    for (te, k), nx in zip(B.EDGES, [e[0] for e in B.EDGES[1:]] + [B.T_END]):
        s = (t >= te) & (t < nx); w = v[s]
        if k == 'rise':
            i = np.flatnonzero(w >= 2.0); marg.append(w[i[0]:].min() - 2.0 if len(i) else -9)
        else:
            i = np.flatnonzero(w <= 0.8); marg.append(0.8 - w[i[0]:].max() if len(i) else -9)
    # settle check: value at end of each window
    ends = [v[(t >= nx - 0.1e-9) & (t < nx)].mean() for nx in [e[0] for e in B.EDGES[1:]] + [B.T_END]]
    dtmax = np.diff(t).max()
    print('%-22s n=%6d dtmax=%.1fps vmax %.3f @%.2fns vmin %.3f @%.2fns early[%.3f,%.3f] ovs %.3f uns %.3f ring %.3f margins %s ends %s pin-die max %.3f' % (
        os.path.basename(f), len(t), dtmax*1e12, v.max(), t[imax]*1e9, v.min(), t[imin]*1e9, v[early].min(), v[early].max(), m['overshoot'], m['undershoot'],
        m['ringback_into_band'], ['%.2f' % x for x in marg], ['%.2f' % x for x in ends], vp.max()))
