import sys, re, copy, time
from harness import *
net, scen, var = sys.argv[1], sys.argv[2], sys.argv[3]
el, (dib, dpin, dnode), (rib, rpin, rnode), rep = ends(net, scen)
kw = {}
if var == 'ramp':      # Ku/Kd from [Ramp] (linear weights) instead of the two-waveform extraction
    for ib in (U1, U3):
        for mm in ib.models.values():
            mm.waves = {'rise': [], 'fall': []}
lines, dm, rm, dpk, rpk, rep = build(net, scen, **kw)
if var.startswith('viaL'):
    s = float(var[4:])
    lines = [re.sub(r'^(Lv\S+ \S+ \S+ )(\S+)$', lambda m: m.group(1) + '%.4g' % (float(m.group(2)) * s), l) for l in lines]
if var in ('dt2', 'trap'):
    lines = [l.replace('.tran 5e-12 3.2e-08 0 5e-12', '.tran 2.5e-12 3.2e-08 0 2.5e-12') if var == 'dt2' else l.replace('method=gear', 'method=trap') for l in lines]
    lines = [l.replace('.tran 5p', '.tran 2.5p').replace(' 0 5p', ' 0 2.5p') if var == 'dt2' else l for l in lines]
t0 = time.time()
r = ngs.run(lines)
m = B.measure(r['time'], r['rdie'], 3.3)
mp = B.measure(r['time'], r[rnode], 3.3)
print('%-10s %-5s %-9s DIE %s | PIN ovs %+.3f uns %.3f | t_end %.1f ns (%.0fs) %s' % (net, scen, var, fmt(m), mp['overshoot'], mp['undershoot'],
      r['time'][-1]*1e9, time.time()-t0, [l for l in lines if l.startswith('.tran')]))
