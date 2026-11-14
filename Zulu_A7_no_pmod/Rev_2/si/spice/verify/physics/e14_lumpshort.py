"""Replace every T-line with TD < TDMIN by a lumped pi (C/2 - L - C/2) and re-run; does the 'Timestep too small'
abort go away, and do the three assigned cases keep their numbers?"""
import sys, re, time
from harness import *
net, scen, corner, tdmin = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
lines, *_ = build(net, scen, corner=corner)
out = []
for l in lines:
    m = re.match(r'^(T\S+) (\S+) 0 (\S+) 0 Z0=(\S+) TD=(\S+)$', l)
    if m and float(m.group(5)) < tdmin:
        n, a, b, z, td = m.group(1), m.group(2), m.group(3), float(m.group(4)), float(m.group(5))
        out += ['L%s %s %s %g' % (n, a, b, z * td), 'C%sa %s 0 %g' % (n, a, td / z / 2), 'C%sb %s 0 %g' % (n, b, td / z / 2)]
    else:
        out.append(l)
t0 = time.time()
r = ngs.run(out)
mm = B.measure(r['time'], r['rdie'], 3.6 if corner == 'max' else 3.3)
print('%-6s %-5s %s lump TD<%gps: %s t_end %.2f ns npts %d (%.0fs)' % (net, scen, corner, tdmin * 1e12, fmt(mm), r['time'][-1] * 1e9, len(r['time']), time.time() - t0))
