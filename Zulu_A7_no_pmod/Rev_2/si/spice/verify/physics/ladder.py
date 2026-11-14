"""Independent first-principles predictor (no ngspice, no IBIS behavioural model):
Thevenin source (R_s from the IBIS I-V slope, linear ramp from the IBIS [Ramp]) -> C_comp -> R/L_pkg -> C_pkg
-> uniform LC ladder line (Z0, TD; 40 sections) -> C_pkg -> R/L_pkg -> C_comp (receiver). Linear, no clamps.
Solved with scipy lsim. Edges at bus_sim's times; measures like bus_sim.measure."""
import numpy as np
from scipy.signal import lsim, StateSpace

def ladder(Rs, cd, Rpd, Lpd, Cpd, Z0, TD, Cpr, Rpr, Lpr, cr, N=40, Rser_line=0.0):
    Lt, Ct = Z0 * TD, TD / Z0
    # node caps: 0 die_d, 1 pin_d, 2..N line interior (N-1 nodes), N+1 pin_r, N+2 die_r
    C = [cd, Cpd + Ct / N / 2] + [Ct / N] * (N - 1) + [Cpr + Ct / N / 2, cr]
    nn = len(C)
    inds = [(0, 1, Lpd, Rpd)] + [(1 + k, 2 + k, Lt / N, Rser_line / N) for k in range(N)] + [(N + 1, N + 2, Lpr, Rpr)]
    # fix: line sections connect node1 -> node2 ... -> node N+1
    ni = len(inds)
    n = nn + ni
    A = np.zeros((n, n)); Bm = np.zeros((n, 1))
    A[0, 0] = -1 / (Rs * C[0]); Bm[0, 0] = 1 / (Rs * C[0])
    for j, (a, b, L, R) in enumerate(inds):
        s = nn + j
        A[a, s] -= 1 / C[a]; A[b, s] += 1 / C[b]
        A[s, a] += 1 / L; A[s, b] -= 1 / L; A[s, s] -= R / L
    Cm = np.zeros((2, n)); Cm[0, nn - 1] = 1; Cm[1, 0] = 1
    return StateSpace(A, Bm, Cm, np.zeros((2, 1)))

EDGES = [(1.0e-9, 'rise'), (8.5e-9, 'fall'), (16.0e-9, 'rise'), (23.5e-9, 'fall')]

def source(t, tr, tf, vcc=3.3, shape='lin'):
    v = np.zeros_like(t); lvl = 0.0
    for te, kind in EDGES:
        d = tr if kind == 'rise' else tf
        x = np.clip((t - te) / d, 0, 1)
        if shape == 'cos':
            x = 0.5 - 0.5 * np.cos(np.pi * x)
        new = vcc if kind == 'rise' else 0.0
        v = np.where(t >= te, lvl + (new - lvl) * x, v)
        lvl = new
    return v

def measure(t, v, vcc=3.3):
    res = {'overshoot': v.max() - vcc, 'undershoot': -v.min()}
    sl = []
    for (te, kind), nx in zip(EDGES, [e[0] for e in EDGES[1:]] + [32e-9]):
        s = (t >= te) & (t < nx); w, ts = v[s], t[s]
        if kind == 'rise':
            a, b = np.flatnonzero(w >= .33), np.flatnonzero(w >= 2.97)
        else:
            a, b = np.flatnonzero(w <= 2.97), np.flatnonzero(w <= .33)
        if len(a) and len(b): sl.append((ts[b[0]] - ts[a[0]]) * 1e9)
    res['t10_90'] = np.mean(sl)
    # per-edge
    return res

def predict(name, Rs, cd, dpk, line, rpk, cr, tr, tf, shape='lin'):
    t = np.arange(0, 32e-9, 1e-12)
    sys_ = ladder(Rs, cd, dpk[0], dpk[1], dpk[2], line[0], line[1], rpk[2], rpk[0], rpk[1], cr)
    vs = source(t, tr, tf, shape=shape)
    _, y, _ = lsim(sys_, vs, t)
    m = measure(t, y[:, 0])
    print('%-46s ovs %+.3f  uns %.3f  10-90 %.3f ns' % (name, m['overshoot'], m['undershoot'], m['t10_90']))
    return m, t, y

if __name__ == '__main__':
    # U1 package (no per-pin data): R .244 L 3.92n C .53p ; U3 CLK pin 38: .572 3.749n .801p ; U3 DQ0 pin 2: .988 6.976n 1.483p
    u1pk = (0.244, 3.92e-9, 0.53e-12)
    clkpk = (0.5718, 3.749e-9, 0.801e-12)
    dq0pk = (0.9883, 6.976e-9, 1.483e-12)
    print('--- SDRAM-CLK write: LVCMOS33_F_8_HR -> U3 CLK Input (C_comp 4.39 pF), 130 ps flight')
    for Rs in (22.6, 25.0, 30.0):
        for Z0 in (49.0, 55.0):
            for sh in ('lin', 'cos'):
                predict('Rs %.1f Z0 %g ramp %s (tr 1.143 / tf 1.030 ns)' % (Rs, Z0, sh), Rs, 5.23e-12, u1pk, (Z0, 130e-12), clkpk, 4.39e-12,
                        0.6863e-9 / 0.6, 0.6176e-9 / 0.6, sh)
    print('--- D0 read: DQ_100% -> U1 LVCMOS33_S_8_HR (C_comp 5.23 pF), 85 ps flight (linear, NO clamps)')
    for cd in (4.71e-12, 0.0):
        for sh in ('lin', 'cos'):
            for Rs in (36.0,):
                predict('Rs %g cd %.2fp ramp %s (tr .212/tf .132 ns)' % (Rs, cd * 1e12, sh), Rs, cd, dq0pk, (49.0, 85e-12), u1pk, 5.23e-12,
                        0.127368e-9 / 0.6, 0.0792516e-9 / 0.6, sh)
    print('--- D0 write: LVCMOS33_S_8_HR -> U3 DQ0 (C_comp 4.71 pF), 85 ps flight')
    for Rs in (22.6, 25.0):
        for sh in ('lin', 'cos'):
            predict('Rs %.1f ramp %s (tr 5.255 / tf 1.823 ns)' % (Rs, sh), Rs, 5.23e-12, u1pk, (49.0, 85e-12), dq0pk, 4.71e-12,
                    3.1532e-9 / 0.6, 1.0938e-9 / 0.6, sh)
