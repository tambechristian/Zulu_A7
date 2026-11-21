"""Linear Thevenin driver (R_s from the IBIS I-V slope near the rail, C_comp at the die, the IBIS package) on the full
board with the IBIS receiver. Source shape: 'lin' = linear ramp from [Ramp] (0-100 = 20-80/0.6); 'ibis' = the IBIS
fixture waveform itself, normalised to 0..1 (rise from the 0 V fixture, fall from the 3.3 V fixture)."""
import sys
from harness import *
net, scen, Rs, shape = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
el, (dib, dpin, dnode), (rib, rpin, rnode), rep = ends(net, scen)
dm = dib.model(dib.pins[dpin][1])
if shape == 'lin':
    lines, *_ = build(net, scen, driver='thev', rs=Rs, edge={'rise': dm.ramp['dv/dt_r'][0][1] / 0.6, 'fall': dm.ramp['dv/dt_f'][0][1] / 0.6})
else:
    lines, *_ = build(net, scen, driver='thev', rs=Rs, edge={'rise': 1e-9, 'fall': 1e-9})
    def norm(edge, vf):
        w = [w for w in dm.waves[edge] if abs(w['v_fixture'] - vf) < 0.01][0]
        t, v = w['t'][:, 0], w['t'][:, 1]
        x = (v - v.min()) / (v.max() - v.min())
        return t, x
    tr, xr = norm('rise', 0.0); tf, xf = norm('fall', 3.3)
    T = np.arange(0, 32e-9, 5e-12); V = np.zeros_like(T)
    for te, kind in B.EDGES:
        s = T >= te
        V[s] = 3.3 * (np.interp(T[s] - te, tr, xr) if kind == 'rise' else np.interp(T[s] - te, tf, xf))
    keep = np.r_[True, np.abs(np.diff(V, 2)) > 1e-6, True]
    src = B.pwl_source('th', 'vth', T[keep], V[keep])
    lines = [l for l in lines if not l.startswith('Vth ')]
    lines = lines[:1] + src + lines[1:]
r = ngs.run(lines)
m = B.measure(r['time'], r['rdie'], 3.3)
print('%-10s %-5s Thevenin Rs %.1f %-4s : %s  t_end %.1f' % (net, scen, Rs, shape, fmt(m), r['time'][-1] * 1e9))
