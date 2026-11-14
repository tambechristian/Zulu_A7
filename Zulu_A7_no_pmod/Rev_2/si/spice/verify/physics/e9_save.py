import sys
from harness import *
net, scen = sys.argv[1], sys.argv[2]
m, r, info = run(net, scen)
assert abs(r['time'][-1] - 32e-9) < 1e-12, r['time'][-1]
np.savez('wave_%s_%s.npz' % (net, scen), t=r['time'], rdie=r['rdie'], ddie=r['ddie'])
print(net, scen, fmt(m))
