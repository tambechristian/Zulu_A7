"""Driver output impedance of the AS4C32M16SB DQ models from their IBIS I-V tables, and U1's receiver clamp currents.
Run from anywhere: python rout.py.  Reads the vendor IBIS through si/spice/ibis2spice.py (no edits)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SP)
import ibis2spice as I

U3 = I.Ibis(os.path.join(os.path.dirname(HERE), 'ibis', 'as4c32m16sb', 'Alliance-Memory_AS4C32M16SB-7TCN_Ibis.ibs'))
U1 = I.Ibis(os.path.join(os.path.dirname(HERE), 'vivado', 'zulu_a7_no_pmod_u1.ibs'))
COLS = {'typ': 1, 'min': 2, 'max': 3}
print('IBIS corner columns: typ / min (slow) / max (fast); vcc per [Voltage Range]')
for name in ('DQ_100%', 'DQ_72%', 'DQ_39%'):
    m = U3.model(name)
    vr = m.kw['voltage range']
    for c, k in COLS.items():
        vcc = vr[k - 1]
        pd = m.tables['pulldown']; pu = m.tables['pullup']
        x, ipd = pd[:, 0], pd[:, k]
        xu, ipu = pu[:, 0], pu[:, k]   # pullup table: x = Vcc - Vpin, current into pin (negative = sourcing)
        # pulldown clamp-free? IBIS pulldown tables include no clamp (clamps are separate tables)
        def r_small(xx, ii):
            # the tables have no rows between 0.0012 V and ~0.45 V, so a slope fit there is meaningless:
            # use the secant from 0 V to the first row at or above 0.4 V (the linear region)
            k = np.flatnonzero(xx >= 0.4)[0]
            return xx[k] / ii[k]
        def r_at(xx, ii, v):
            return v / np.interp(v, xx, ii)
        # linear-region (small signal, 0.05..0.35 V) and large-signal V/I at 0.5*Vcc
        rpd_s, rpd_h = r_small(x, ipd), r_at(x, ipd, 0.5 * vcc)
        rpu_s, rpu_h = abs(r_small(xu, ipu)), abs(r_at(xu, ipu, 0.5 * vcc))
        # Thevenin as seen by the line at the switching instant: current into a matched 43.4 ohm line from 0 V
        # (rising edge launches V1 = Vcc*Z0/(Z0+Rout)); solve V = Vcc - Vpu_drop, I = V/Z0 on the pullup curve
        z0 = 43.4
        vv = np.linspace(0.01, vcc - 0.01, 2000)
        ip = -np.interp(vcc - vv, xu, ipu)          # current sourced at pin voltage vv
        v1r = vv[np.argmin(abs(ip - vv / z0))]
        ipd2 = np.interp(vv, x, ipd)                # sink current at pin voltage vv (falling edge from Vcc)
        v1f = vv[np.argmin(abs(ipd2 - (vcc - vv) / z0))]
        print('%-8s %-3s Vcc %.2f | pulldown R_lin %5.1f  V/I@Vcc/2 %5.1f | pullup R_lin %5.1f  V/I@Vcc/2 %5.1f ohm | '
              'launch into 43.4: rise %.2f V (Reff %4.1f) fall to %.2f V (Reff %4.1f)' % (
                  name, c, vcc, rpd_s, rpd_h, rpu_s, rpu_h, v1r, z0 * (vcc / v1r - 1), v1f, z0 * (vcc / (vcc - v1f) - 1)))
m = U1.model('LVCMOS33_S_8_HR')
print('\nU1 LVCMOS33_S_8_HR receiver clamps (IBIS from Vivado write_ibis), C_comp', m.kw.get('c_comp'))
gc = m.tables.get('gnd clamp')
pc = m.tables.get('power clamp')
for v in (-0.2, -0.3, -0.4, -0.5, -0.6, -0.8, -1.0, -1.2):
    print('  GND clamp at die %+.1f V: typ %7.2f mA  min %7.2f  max %7.2f' % (v, *(1e3 * np.interp(v, gc[:, 0], gc[:, k]) for k in (1, 2, 3))))
print('  power clamp table rows (x = Vcc - Vpin):')
for v in (-0.2, -0.4, -0.5, -0.6, -0.8):
    print('  Power clamp at Vcc%+.1f V: typ %7.2f mA' % (-v, 1e3 * np.interp(v, pc[:, 0], pc[:, 1])))
print('keys', list(m.tables), list(m.kw)[:20])
