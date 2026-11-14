import sys; sys.path.insert(0, '../..')
import ngs, ctypes as C
net = ['* rc', 'V1 a 0 PULSE(0 1 0 1n 1n 5n 10n)', 'R1 a b 1k', 'C1 b 0 1p', '.tran 1p 20n 0 1p', '.end']
for i in range(4):
    r = ngs.run(net)
    print('run', i, 'curplot', ngs._lib.ngSpice_CurPlot().decode(), 'npts', len(r['time']))
ngs._out.clear(); ngs.cmd('setplot'); print(''.join(ngs._out)[-600:])
