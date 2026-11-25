"""Point-to-point bench (driver pkg - one T-line - receiver pkg), the same ibis2spice calls bus_sim makes, with one
assumption changed at a time. Usage: python bench.py write|read typ|max variant [Z0 TDps]"""
import sys, os, json, time
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs, bus_sim as B, ibis2spice as I
scen, corner, variant = sys.argv[1:4]
Z0 = float(sys.argv[4]) if len(sys.argv) > 4 else 50.0
TD = float(sys.argv[5]) * 1e-12 if len(sys.argv) > 5 else 85e-12
DIAG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'u1_pkg_diag.json')))
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
u1pin, u3pin = 'V8', '2'                    # D0: U1 V8, U3 DQ0 pin 2
edges, t_end = B.EDGES, B.T_END
pk = I.pkg_for
if variant == 'u1_pkgdiag':
    def pk(ib, pin, c):
        if ib is U1:
            v = [v for v in DIAG.values() if v[0] == pin][0]; return v[1], v[2], v[3]
        return I.pkg_for(ib, pin, c)
if variant.startswith('u1_pin_'):        # put another U1 ball's diagonal on the D0 driver
    net = variant[7:]
    def pk(ib, pin, c):
        if ib is U1:
            v = DIAG[net]; return v[1], v[2], v[3]
        return I.pkg_for(ib, pin, c)
if variant == 'dq_ccomp0': U3.models['DQ_100%'].kw['c_comp'] = [0.0] * 3
if variant == 'dq_ccomp2p': U3.models['DQ_100%'].kw['c_comp'] = [2e-12] * 3
if variant == 'u1_ccomp0':
    for n in ('LVCMOS33_S_8_HR', 'LVCMOS33_F_8_HR'): U1.models[n].kw['c_comp'] = [0.0] * 3
if variant == 'settled':
    edges, t_end = [(1.0e-9, 'rise'), (41.0e-9, 'fall')], 80e-9
if variant == 'nothin':
    I._pwl_expr = lambda var, tab, scale=1.0: 'pwl(%s, %s)' % (var, ', '.join('%.6g, %.6g' % (a, b * scale) for a, b in zip(*tab)))
wfun = I.weights_pwl
if variant == 'nostitch':
    def wfun(m, c, edges, t_end, dt=5e-12):
        tr, tf = I.switching(m, c, 'rise'), I.switching(m, c, 'fall')
        t = np.arange(0, t_end + dt, dt); ku = np.zeros_like(t); kd = np.ones_like(t)
        for te, kind in edges:
            tt, KU, KD, _ = tr if kind == 'rise' else tf
            s = t >= te; k0 = np.flatnonzero(s)[0]; u0, d0 = ku[k0 - 1], kd[k0 - 1]
            fade = np.clip(1 - (t[s] - te) / 3e-9, 0, 1)
            ku[s] = np.interp(t[s] - te, tt, KU) + (u0 - KU[0]) * fade
            kd[s] = np.interp(t[s] - te, tt, KD) + (d0 - KD[0]) * fade
        return t, ku, kd
if scen == 'write':
    dib, dpin, rib, rpin = U1, u1pin, U3, u3pin
else:
    dib, dpin, rib, rpin = U3, u3pin, U1, u1pin
dm, rm = dib.model(dib.pins[dpin][1]), rib.model(rib.pins[rpin][1])
t, ku, kd = wfun(dm, corner, edges, t_end)
lines = ['* bench'] + B.pwl_source('ku', 'ku', t, ku) + B.pwl_source('kd', 'kd', t, kd)
b, _ = I.buffer_netlist('D', dm, corner, 'ddie', 'n1', pk(dib, dpin, corner), 'ku', 'kd'); lines += b
b, (vcc, _) = I.buffer_netlist('R', rm, corner, 'rdie', 'n2', pk(rib, rpin, corner)); lines += b
lines += ['T1 n1 0 n2 0 Z0=%g TD=%g' % (Z0, TD), '.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear',
          '.ic V(ddie)=0 V(rdie)=0', '.tran 5p %g 0 5p' % t_end, '.end']
t0 = time.time(); r = ngs.run(lines)
B.EDGES = edges; B.T_END = t_end
m = B.measure(r['time'], r['rdie'], vcc)
print('%-5s %-3s %-14s Z0 %g TD %gps  ovs %+.4f  uns %.4f  vmax %.4f vmin %+.4f  t10-90 %.3f  (%.1fs, %d pts)' % (
    scen, corner, variant, Z0, TD * 1e12, m['overshoot'], m['undershoot'], m['vmax'], m['vmin'], m['t10_90_ns'] or -1,
    time.time() - t0, len(r['time'])))
