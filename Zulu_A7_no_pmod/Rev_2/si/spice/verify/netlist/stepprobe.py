"""Why do bus_sim netlists take femtosecond steps? Run the WE# write netlist to 0.9 ns (driver idle) in variants."""
import sys, json, re, time, math
sys.path.insert(0, '../..')
import bus_sim as B, ibis2spice as I, ngs
M = json.load(open(B.MODEL))
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
net = sys.argv[1] if len(sys.argv) > 1 else 'WE#'
tend = float(sys.argv[2]) if len(sys.argv) > 2 else 0.9e-9
el, n1, n3, rep = B.net_elements(M, net)
def ladderize(el, tdmin):
    out = []
    for e in el:
        m = re.match(r'T(\d+) (\S+) 0 (\S+) 0 Z0=(\S+) TD=(\S+)', e)
        if m and float(m.group(5)) < tdmin:
            i, a, b, z0, td = m.group(1), m.group(2), m.group(3), float(m.group(4)), float(m.group(5))
            Lt, Ct = z0 * td, td / z0
            n = max(1, int(math.ceil(td / 0.3e-12)))
            prev = a
            for k in range(n):
                nx = b if k == n - 1 else 'y%s_%d' % (i, k)
                out += ['Cy%s_%da %s 0 %g' % (i, k, prev, Ct / n / 2), 'Ly%s_%d %s %s %g' % (i, k, prev, nx, Lt / n), 'Cy%s_%db %s 0 %g' % (i, k, nx, Ct / n / 2)]
                prev = nx
        else:
            out.append(e)
    return out
pin1 = rep['u1_pin']; pin3 = rep['u3_pin']
dm, rm = U1.model(U1.pins[pin1][1]), U3.model(U3.pins[pin3][1])
for tag, tdmin in (('bus_sim as is', 0), ('TRA with TD<3ps -> ladder', 3e-12), ('all TRA -> ladder', 1)):
    lines = ['* probe']
    t, ku, kd = I.weights_pwl(dm, 'typ', B.EDGES, B.T_END)
    lines += B.pwl_source('ku', 'ku', t, ku) + B.pwl_source('kd', 'kd', t, kd)
    lines += I.buffer_netlist('D', dm, 'typ', 'ddie', n1, I.pkg_for(U1, pin1, 'typ'), 'ku', 'kd')[0]
    lines += I.buffer_netlist('R', rm, 'typ', 'rdie', n3, I.pkg_for(U3, pin3, 'typ'))[0]
    lines += ladderize(el, tdmin)
    lines += ['.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear', '.ic V(ddie)=0 V(rdie)=0', '.tran 5e-12 %g 0 5e-12' % tend, '.end']
    ngs.cmd('destroy all')
    t0 = time.time()
    r = ngs.run(lines)
    tt = r['time']
    print('%-28s tend=%.3f ns points=%d mean step=%.3g ps  %.1fs' % (tag, tt[-1] * 1e9, len(tt), tt[-1] / len(tt) * 1e12, time.time() - t0))
