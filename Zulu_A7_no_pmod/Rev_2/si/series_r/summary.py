"""One table over every series-R value simulated for READS (D0-D15, fab stack): DS181 Table 4 budget at U1 die and ball
(same method as si/spice/series_study.py), Vmin/Vmax, 10-90 % edge, and the delay to 1.65 V at the die relative to R = 0.
R 0/15/22/33 come from si/spice/wave (earlier study), R 6/10/47 from series_r/wave (sweep.py)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SP); sys.path.insert(0, HERE)
import ds181_check as D
from timing import crossings, USE

SRC = {0: (SP, ''), 6: (HERE, '_r6'), 10: (HERE, '_r10'), 15: (SP, '_r15'), 22: (SP, '_r22'), 33: (SP, '_r33'), 47: (HERE, '_r47')}
RAIL = {'typ': 3.3, 'max': 3.465}


def t1090(t, v, vcc):
    out = []
    for (te, kind) in USE:
        s = (t >= te) & (t < te + 7.5e-9); w, ts = v[s], t[s]
        if kind == 'rise':
            a, b = np.flatnonzero(w >= 0.1 * vcc), np.flatnonzero(w >= 0.9 * vcc)
        else:
            a, b = np.flatnonzero(w <= 0.9 * vcc), np.flatnonzero(w <= 0.1 * vcc)
        if len(a) and len(b):
            out.append((ts[b[0]] - ts[a[0]]) * 1e9)
    return out


base = {}
print('R   corner | die Vmin  Vmax  budget | ball Vmin  Vmax  budget fails | t10-90 ns   | delay@1.65V vs R0 (ns) min..max')
for R in sorted(SRC):
    d, tag = SRC[R]
    for c in ('typ', 'max'):
        res = {'rx_die': [9, -9, 0, 0], 'rx_pin': [9, -9, 0, 0]}; edges = []; dl = []
        for n in range(16):
            z = np.load(os.path.join(d, 'wave', 'D%d_read_%s_fab%s.npz' % (n, c, tag))); t = z['t']
            for node in res:
                v = z[node]; a = res[node]
                a[0] = min(a[0], v.min()); a[1] = max(a[1], v.max()); rr = 0
                for w in D.windows(t, v, RAIL[c]):
                    for peak, dur, tab in ((w['peak_over'], w['t_over_ns'], D.OVER), (w['peak_under'], w['t_under_ns'], D.UNDER)):
                        if peak > 0.2:
                            lim = D.allowed(tab, peak); rr = max(rr, (dur / 7.5 * 100) / lim if lim > 0 else 1e9)
                a[2] = max(a[2], rr); a[3] += rr > 1
            edges += t1090(t, z['rx_die'], RAIL[c])
            for te, kind in USE:
                x = crossings(t, z['rx_die'], te, kind, 1.65)
                key = (n, c, te)
                if R == 0:
                    base[key] = (x[0], x[-1])
                dl += [(x[0] - base[key][0]) * 1e9, (x[-1] - base[key][1]) * 1e9]
        a, b = res['rx_die'], res['rx_pin']
        print('%-3d %-6s | %+5.2f %5.2f %5.0f%% | %+5.2f %5.2f %6.0f%% %2d/16 | %.2f-%.2f | %+.3f..%+.3f' % (
            R, c, a[0], a[1], min(100 * a[2], 99999), b[0], b[1], min(100 * b[2], 99999), b[3], min(edges), max(edges), min(dl), max(dl)))
