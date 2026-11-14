"""Drive the independent numpy ladder with bus_sim's own driver-die waveform (Rs ~ 0), compare receiver die."""
import numpy as np
from scipy.signal import lsim
from ladder import ladder, measure
u1pk = (0.244, 3.92e-9, 0.53e-12); clkpk = (0.5718, 3.749e-9, 0.801e-12); dq0pk = (0.9883, 6.976e-9, 1.483e-12)
cases = {'SDRAM-CLK_write': (u1pk, 130.44e-12, clkpk, 4.39e-12, 'clamps negligible (Input)'),
         'D0_write': (u1pk, 84.6e-12, dq0pk, 4.71e-12, 'rx DQ clamps'),
         'D0_read': (dq0pk, 84.6e-12, u1pk, 5.23e-12, 'rx U1 clamps')}
for k, (dpk, td, rpk, cr, note) in cases.items():
    try: d = np.load('wave_%s.npz' % k)
    except FileNotFoundError: print(k, 'no wave'); continue
    t = np.arange(0, 32e-9, 1e-12); vd = np.interp(t, d['t'], d['ddie']); vr = np.interp(t, d['t'], d['rdie'])
    m0 = measure(t, vr)
    for Z0 in (49.0, 55.0, 63.6):
        s = ladder(1e-3, 1e-15, dpk[0], dpk[1], dpk[2], Z0, td, rpk[2], rpk[0], rpk[1], cr)
        _, y, _ = lsim(s, vd, t)
        m = measure(t, y[:, 0])
        print('%-16s Z0 %4.1f ladder-from-ddie: ovs %+.3f uns %.3f 10-90 %.3f | bus_sim rdie: ovs %+.3f uns %.3f 10-90 %.3f  (%s)' % (
            k, Z0, m['overshoot'], m['undershoot'], m['t10_90'], m0['overshoot'], m0['undershoot'], m0['t10_90'], note))
