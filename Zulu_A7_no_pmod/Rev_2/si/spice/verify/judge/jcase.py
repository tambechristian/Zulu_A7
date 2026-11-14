"""Judge case runner: indep.py netlist (LC ladders) with optional fab-stack L3/L4 scaling, common rail, per-ball U1 package."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'netlist'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bus_sim as B, ibis2spice as I
import indep
net, scen, corner = sys.argv[1:4]
flags = sys.argv[4:]
opt = {}
if 'fab' in flags:   # reviewer FV numbers, 1080 Dk 4.1: L -16 %, C +9 % on L3/L4
    _line = B.line
    def line(layer, w):
        lp = dict(_line(layer, w))
        if layer in ('L3-SIG', 'L4-SIG'):
            lp['L_nH_per_mm'] *= 0.84; lp['C_pF_per_mm'] *= 1.09
            lp['Z0'] = (lp['L_nH_per_mm'] * 1e-9 / (lp['C_pF_per_mm'] * 1e-12)) ** .5
            lp['td_ps_per_mm'] = (lp['L_nH_per_mm'] * lp['C_pF_per_mm'] * 1e-9) ** .5 * 1e3
        return lp
    B.line = line
if 'pkgball' in flags:
    D = json.load(open(os.path.join(HERE, '..', 'ibis2spice', 'u1_pkg_diag.json')))
    _pk = I.pkg_for
    def pkg_for(ib, pin, corner):
        if ib.pkg['l_pkg'][0] and abs(ib.pkg['l_pkg'][0] - 3.92e-9) < 1e-12 and net in D and D[net][0] == pin:
            return tuple(D[net][1:4])
        return _pk(ib, pin, corner)
    I.pkg_for = pkg_for
    flags = [f for f in flags]
for f in flags:
    if f == 'pkgball': continue
    if '=' in f:
        k, v = f.split('='); opt[k] = float(v)
    elif f != 'fab':
        opt[f] = True
m, lenby, viarep, r, vcc = indep.run(net, scen, corner, opt)
print(json.dumps({'net': net, 'scen': scen, 'corner': corner, 'flags': flags, 'ovs': round(m['overshoot'], 4),
                  'uns': round(m['undershoot'], 4), 't1090': m['t10_90_ns'], 'vcc': vcc, 'tend_ns': float(r['time'][-1] * 1e9),
                  'vmax': round(m['vmax'], 4), 'settle_hi': round(float(r['rdie'][(r['time'] > 7.5e-9) & (r['time'] < 8.4e-9)].mean()), 4)}))
