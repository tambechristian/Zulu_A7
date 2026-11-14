"""Re-sample every IBIS V-T table with PCHIP (monotone cubic, passes through every vendor point) at 5 ps before the
Ku/Kd extraction, instead of linear interpolation between the vendor samples. Same everything else."""
import sys
from scipy.interpolate import PchipInterpolator
from harness import *
net, scen, mode = sys.argv[1], sys.argv[2], sys.argv[3]
if mode == 'pchip':
    for ib in (U1, U3):
        for mm in ib.models.values():
            for e in ('rise', 'fall'):
                for w in mm.waves[e]:
                    if 't' not in w: continue
                    a = w['t']; tt = np.arange(a[0, 0], a[-1, 0] + 1e-15, 5e-12)
                    w['t'] = np.column_stack([tt] + [PchipInterpolator(a[:, 0], a[:, c])(tt) for c in (1, 2, 3)])
m, r, info = run(net, scen)
print('%-10s %-5s %-6s %s  t_end %.1f' % (net, scen, mode, fmt(m), r['time'][-1] * 1e9))
