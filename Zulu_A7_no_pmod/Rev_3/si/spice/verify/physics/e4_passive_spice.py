import sys, numpy as np
sys.path.insert(0, '../..')
import ngs, bus_sim as B
from scipy.signal import lsim
from ladder import ladder, measure
d = np.load('wave_SDRAM-CLK_write.npz')
t = np.arange(0, 32e-9, 1e-12); vd = np.interp(t, d['t'], d['ddie'])
# thin the PWL
tt = d['t']; vv = d['ddie']
idx = np.unique(np.concatenate([np.arange(0, len(tt), max(1, len(tt)//20000)), [len(tt)-1]]))
src = B.pwl_source('src', 'ddie', tt[idx], vv[idx])
net = ['Rpd ddie dpk 0.244', 'Lpd dpk p1 3.92n', 'Cpd p1 0 0.53p', 'T1 p1 0 p2 0 Z0=49 TD=130.44p',
       'Cpr p2 0 0.801p', 'Rpr p2 rpk 0.5718', 'Lpr rpk rdie 3.749n', 'Ccr rdie 0 4.39p']
r = ngs.run(['* passive'] + src + net + ['.options reltol=1e-4 method=gear', '.tran 5p 32n 0 5p', '.end'])
ms = measure(r['time'], r['rdie'])
s = ladder(1e-3, 1e-15, 0.244, 3.92e-9, 0.53e-12, 49.0, 130.44e-12, 0.801e-12, 0.5718, 3.749e-9, 4.39e-12)
_, y, _ = lsim(s, vd, t)
ml = measure(t, y[:, 0])
mb = measure(t, np.interp(t, d['t'], d['rdie']))
print('ngspice passive from ddie : ovs %+.3f uns %.3f' % (ms['overshoot'], ms['undershoot']), 't_end', r['time'][-1])
print('numpy ladder from ddie    : ovs %+.3f uns %.3f' % (ml['overshoot'], ml['undershoot']))
print('bus_sim rdie (same run)   : ovs %+.3f uns %.3f' % (mb['overshoot'], mb['undershoot']))
# where are the extremes
for name, tv, v in (('ngspice', r['time'], r['rdie']), ('busim', d['t'], d['rdie']), ('ladder', t, y[:,0])):
    print(name, 'tmax %.3f ns  tmin %.3f ns' % (tv[np.argmax(v)]*1e9, tv[np.argmin(v)]*1e9))
print('ddie range %.3f..%.3f' % (d['ddie'].min(), d['ddie'].max()))
