"""Same net, swap the U1 driver between LVCMOS33_F_8_HR and LVCMOS33_S_8_HR (identical I-V tables, only the
pre-driver slew differs). Physics: the slow model must not ring more than the fast one. Per-edge extremes."""
import sys
from harness import *
net, scen, model = sys.argv[1], sys.argv[2], sys.argv[3]
el, (dib, dpin, dnode), (rib, rpin, rnode), rep = ends(net, scen)
sig, orig = dib.pins[dpin][0], dib.pins[dpin][1]
dib.pins[dpin] = (sig, model) + tuple(dib.pins[dpin][2:])
m, r, info = run(net, scen)
np.savez("swap_%s_%s.npz" % (net, model), t=r["time"], rdie=r["rdie"], ddie=r["ddie"], ku=r["ku"], kd=r["kd"])
t, v = r['time'], r['rdie']
per = []
for (te, kind), nx in zip(B.EDGES, [e[0] for e in B.EDGES[1:]] + [B.T_END]):
    s = (t >= te) & (t < nx)
    per.append('%s %+.3f' % (kind, (v[s].max() - 3.3) if kind == 'rise' else -v[s].min()))
print('%-10s %-5s driver %-16s %s  t_end %.1f | per-edge ovs/uns: %s' % (net, scen, model, fmt(m), t[-1] * 1e9, ', '.join(per)))
