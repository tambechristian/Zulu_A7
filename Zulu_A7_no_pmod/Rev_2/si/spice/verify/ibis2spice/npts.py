"""Point count / end time of full-net runs, and whether the tiny steps come from the buffers or the board network."""
import sys, os, json, time
sys.path.insert(0, os.path.abspath('../..'))
import numpy as np, ngs, bus_sim as B, ibis2spice as I
M = json.load(open(B.MODEL)); U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
net, scen, corner, mode = sys.argv[1:5]
el, n1, n3, rep = B.net_elements(M, net)
if mode == 'full':
    t0 = time.time(); tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, scen, corner, U1, U3)
    print(net, scen, corner, mode, 'npts', len(tt), 't_end %.3f ns' % (tt[-1] * 1e9), 'min step %.3g s' % np.diff(tt).min(), '%.0fs' % (time.time() - t0))
else:   # ideal 50-ohm/ramp source instead of IBIS buffers, same board network
    lines = ['* lin', 'Vs s 0 PWL(0 0 1n 0 2n 3.3 8.5n 3.3 9.5n 0 32n 0)', 'Rs s %s 40' % n1, 'Cr %s 0 5p' % n3] + el + \
            ['.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear', '.tran 5p 32n 0 5p', '.end']
    t0 = time.time(); r = ngs.run(lines); tt = r['time']
    print(net, mode, 'npts', len(tt), 't_end %.3f ns' % (tt[-1] * 1e9), 'min step %.3g s' % np.diff(tt).min(), '%.0fs' % (time.time() - t0))
