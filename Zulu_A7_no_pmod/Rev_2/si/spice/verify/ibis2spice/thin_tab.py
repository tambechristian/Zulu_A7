"""60-point thinning of the B-source tables vs the full IBIS tables, in the voltage bands the bus actually reaches."""
import sys, os
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, bus_sim as B, ibis2spice as I
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
def thin(tab):
    x, y = tab
    if len(x) > 60:
        keep = np.unique(np.round(np.linspace(0, len(x) - 1, 60)).astype(int)); x, y = x[keep], y[keep]
    return x, y
def ngpwl(x, xs, ys):   # ngspice pwl: linear extrapolation of the end segments
    y = np.interp(x, xs, ys)
    lo, hi = x < xs[0], x > xs[-1]
    y[lo] = ys[0] + (x[lo] - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0])
    y[hi] = ys[-1] + (x[hi] - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
    return y
for ib, name in ((U1, 'LVCMOS33_S_8_HR'), (U3, 'DQ_100%'), (U3, 'INPUT')):
    m = ib.model(name)
    for c in ('typ', 'max'):
        vpu, vpd, vpc, vgc = I._rails(m, c)
        V = np.linspace(-1.0, vpc + 1.0, 4001)
        for key, arg in (('gnd clamp', V - vgc), ('power clamp', vpc - V), ('pullup', vpu - V), ('pulldown', V - vpd)):
            tab = I._table(m, key, c)
            if tab is None: continue
            full = np.interp(arg, *tab); th = ngpwl(arg, *thin(tab))
            band = (V > -0.6) & (V < vpc + 0.6)
            e = np.abs(th - full)
            k = np.argmax(np.where(band, e, 0))
            print('%-16s %-3s %-11s n=%3d worst |thin-full| in -0.6..Vpc+0.6: %.3g A at V=%.3f (full %.4g)  rel %.1f%%' % (
                name, c, key, len(tab[0]), e[k], V[k], full[k], 100 * e[k] / max(abs(full[k]), 1e-6)))
