import sys, time, json
from harness import *
net, scen, label = sys.argv[1], sys.argv[2], sys.argv[3]
td = 130.44e-12 if net == 'SDRAM-CLK' else 84.6e-12
KW = {'full': {}, 'T49': dict(board='tline', Z0=49.0, TD=td), 'T64': dict(board='tline', Z0=63.6, TD=td),
      'short': dict(board='none'), 'rxlin': dict(recv='lin'), 'clip': dict(clipw=True),
      'smallpkg': dict(nopkg=True)}[label]
t0 = time.time()
m, r, info = run(net, scen, **KW)
lg = ngs.log()
print('%-10s %-5s %-8s %s  t_end %.2f ns  npts %d (%.0fs) %s' % (net, scen, label, fmt(m), r['time'][-1]*1e9, len(r['time']), time.time()-t0,
      ' | '.join(l.strip() for l in lg.splitlines() if 'rror' in l or 'too small' in l or 'abort' in l.lower())[:300]))
