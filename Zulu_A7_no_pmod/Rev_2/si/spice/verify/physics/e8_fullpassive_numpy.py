"""Independent numpy solve of bus_sim's FULL passive network (its own el list: T-lines -> LC ladders with <=0.5 ps
sections, via L ladders, lumped C) + packages + receiver C_comp, forced by bus_sim's own driver-die waveform.
Compares with the ngspice receiver die from the same run (validates ngspice's handling of 1-5 ps T-lines at 5 ps step)."""
import sys, numpy as np
from scipy.signal import lsim, StateSpace
from harness import B, M
from ladder import measure
net = sys.argv[1]; scen = sys.argv[2]; wave = sys.argv[3]
dpk, rpk, cr = [tuple(map(float, x.split(','))) for x in sys.argv[4:6]] + [float(sys.argv[6])]
el, n1, n3, rep = B.net_elements(M, net)
dn, rn = (n1, n3) if scen == 'write' else (n3, n1)
caps = {}; inds = []; k = [0]
def cap(n, c): caps[n] = caps.get(n, 0) + c
def newnode():
    k[0] += 1; return '_x%d' % k[0]
for l in el:
    t = l.split()
    if t[0][0] == 'T':
        a, b = t[1], t[3]; Z0 = float(t[5].split('=')[1]); TD = float(t[6].split('=')[1])
        N = max(2, int(np.ceil(TD / 0.5e-12)))
        Ls, Cs = Z0 * TD / N, TD / Z0 / N
        prev = a; cap(a, Cs / 2)
        for i in range(N):
            nxt = b if i == N - 1 else newnode()
            inds.append((prev, nxt, Ls, 0.0)); cap(nxt, Cs if i < N - 1 else Cs / 2); prev = nxt
    elif t[0][0] == 'L':
        inds.append((t[1], t[2], float(t[3]), 0.0))
    elif t[0][0] == 'C':
        cap(t[1], float(t[3]))
    elif t[0][0] == 'R':
        inds.append((t[1], t[2], 1e-13, 1e-3))
# packages: forced die 'D' -> R,L -> dn (C_pkg); rn (C_pkg) -> R,L -> 'rdie' (C_comp)
inds.append(('D', dn, dpk[1], dpk[0])); cap(dn, dpk[2])
inds.append((rn, 'rdie', rpk[1], rpk[0])); cap(rn, rpk[2]); cap('rdie', cr)
nodes = [n for n in caps if n != 'D']
for (a, b, L, R) in inds:
    for n in (a, b):
        if n != 'D' and n not in caps: caps[n] = 1e-18; nodes.append(n)
idx = {n: i for i, n in enumerate(nodes)}
nn, ni = len(nodes), len(inds); n = nn + ni
A = np.zeros((n, n)); Bm = np.zeros((n, 1))
for j, (a, b, L, R) in enumerate(inds):
    s = nn + j
    if a == 'D': Bm[s, 0] += 1 / L
    else: A[idx[a], s] -= 1 / caps[a]; A[s, idx[a]] += 1 / L
    A[idx[b], s] += 1 / caps[b]; A[s, idx[b]] -= 1 / L
    A[s, s] -= R / L
Cm = np.zeros((1, n)); Cm[0, idx['rdie']] = 1
d = np.load(wave); t = np.arange(0, 32e-9, 0.05e-12)
_, y, _ = lsim(StateSpace(A, Bm, Cm, np.zeros((1, 1))), np.interp(t, d['t'], d['ddie']), t)
m = measure(t, y); mb = measure(t, np.interp(t, d['t'], d['rdie']))
print('%s %s: numpy full network forced by ddie: ovs %+.3f uns %.3f 10-90 %.3f | ngspice bus_sim: ovs %+.3f uns %.3f 10-90 %.3f  (%d states)' % (
    net, scen, m['overshoot'], m['undershoot'], m['t10_90'], mb['overshoot'], mb['undershoot'], mb['t10_90'], n))
