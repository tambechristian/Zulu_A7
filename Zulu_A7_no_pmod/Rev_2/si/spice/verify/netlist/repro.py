import sys, json, time
sys.path.insert(0, '../..')
import bus_sim as B, ibis2spice as I, ngs
M = json.load(open(B.MODEL))
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
for spec in sys.argv[1:]:
    net, scen, corner = spec.split(':')
    t0 = time.time()
    tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, scen, corner, U1, U3)
    m = B.measure(tt, vr, vcc)
    log = ngs.log()
    errs = [l for l in log.splitlines() if any(k in l.lower() for k in ('error', 'too small', 'abort', 'warning', 'fail'))]
    print(net, scen, corner, 'tend=%.3f ns n=%d ovs %.4f uns %.4f  %.0fs' % (tt[-1] * 1e9, len(tt), m['overshoot'], m['undershoot'], time.time() - t0))
    print('  ngspice msgs:', errs[:8])
