import time
from harness import *
t0 = time.time()
m, r, info = run('A0', 'write', corner='max')
lg = ngs.log()
print('A0 write max alone:', fmt(m), 't_end %.2f ns npts %d (%.0fs)' % (r['time'][-1] * 1e9, len(r['time']), time.time() - t0))
print([l for l in lg.split('std') if 'rror' in l or 'too small' in l or 'emory' in l][:5])
