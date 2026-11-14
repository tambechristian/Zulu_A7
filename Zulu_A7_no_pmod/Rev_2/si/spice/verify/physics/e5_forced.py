"""bus_sim's own network (full board, receiver IBIS) driven by a voltage source forced to bus_sim's ddie waveform."""
import sys, numpy as np
from harness import *
d = np.load('wave_SDRAM-CLK_write.npz'); tt, vv = d['t'], d['ddie']
idx = np.unique(np.concatenate([np.arange(0, len(tt), max(1, len(tt)//30000)), [len(tt)-1]]))
mode = sys.argv[1]
lines, dm, rm, dpk, rpk, rep = build('SDRAM-CLK', 'write', board=('tline' if mode == 'T49' else 'full'), Z0=49.0, TD=130.44e-12)
# drop the driver B-source and its C_comp, force ddie
keep = [l for l in lines if not (l.startswith('BD ') or l.startswith('CcD ') or l.startswith('Vku') or l.startswith('Vkd') or l.startswith('+'))]
# the '+' continuation lines belong to long pwl lines (ku/kd sources and B-sources); rebuild receiver B line safely:
lines2 = []
skip = False
for l in lines:
    if l.startswith('BD ') or l.startswith('Vku') or l.startswith('Vkd'):
        skip = True; continue
    if l.startswith('+') and skip:
        continue
    skip = False
    if l.startswith('CcD '):
        continue
    if l.startswith('.ic'):
        l = '.ic V(rdie)=0'
    lines2.append(l)
lines2 = lines2[:1] + B.pwl_source('force', 'ddie', tt[idx], vv[idx]) + lines2[1:]
r = ngs.run(lines2)
m = B.measure(r['time'], r['rdie'], 3.3)
print(mode, 'forced-ddie:', fmt(m), ' t_end', r['time'][-1])
