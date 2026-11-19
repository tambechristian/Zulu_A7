import time
from harness import *
cases = [('SDRAM-CLK','write',130.44e-12),('D0','read',84.6e-12),('D0','write',84.6e-12)]
out = {}
for net, scen, td in cases:
    print('==', net, scen, flush=True)
    for label, kw in [('full board', {}),
                      ('single T 49 ohm', dict(board='tline', Z0=49.0, TD=td)),
                      ('single T 64 ohm', dict(board='tline', Z0=63.6, TD=td)),
                      ('no line (short)', dict(board='none')),
                      ('full board, rx linear (no clamps)', dict(recv='lin')),
                      ('full board, weights clipped 0..1', dict(clipw=True)),
                      ('full board, no packages', dict(nopkg=True))]:
        t0 = time.time()
        m, r, info = run(net, scen, **kw)
        print('  %-36s %s   (%.0fs)' % (label, fmt(m), time.time()-t0), flush=True)
        if label == 'full board':
            np.savez('wave_%s_%s.npz' % (net.replace('#','N'), scen), t=r['time'], rdie=r['rdie'], ddie=r['ddie'])
