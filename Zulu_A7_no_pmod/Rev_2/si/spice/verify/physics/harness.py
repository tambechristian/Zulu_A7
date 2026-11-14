"""Physics-lens experiments. Never writes outside verify/physics."""
import sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, SP)
import ngs, ibis2spice as I, bus_sim as B

M = json.load(open(B.MODEL))
U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)

def ends(net, scen):
    el, n1, n3, rep = B.net_elements(M, net)
    if scen == 'write':
        return el, (U1, rep['u1_pin'], n1), (U3, rep['u3_pin'], n3), rep
    return el, (U3, rep['u3_pin'], n3), (U1, rep['u1_pin'], n1), rep

def build(net, scen, corner='typ', board='full', driver='ibis', recv='ibis', clipw=False, Z0=None, TD=None,
          rs=None, edge=None, extra=None, nopkg=False):
    el, (dib, dpin, dnode), (rib, rpin, rnode), rep = ends(net, scen)
    dm = dib.model(dib.pins[dpin][1]); rm = rib.model(rib.pins[rpin][1])
    lines = ['* exp']
    if board == 'tline':
        el = ['T1 %s 0 %s 0 Z0=%g TD=%g' % (dnode, rnode, Z0, TD)]
    elif board == 'none':
        el = ['Rshort %s %s 1m' % (dnode, rnode)]
    dpk = I.pkg_for(dib, dpin, corner); rpk = I.pkg_for(rib, rpin, corner)
    if nopkg:
        dpk = (1e-4, 1e-15, 1e-18); rpk = (1e-4, 1e-15, 1e-18)
    if driver == 'ibis':
        t, ku, kd = I.weights_pwl(dm, corner, B.EDGES, B.T_END)
        if clipw:
            ku = np.clip(ku, 0, 1); kd = np.clip(kd, 0, 1)
        lines += B.pwl_source('ku', 'ku', t, ku) + B.pwl_source('kd', 'kd', t, kd)
        b, _ = I.buffer_netlist('D', dm, corner, 'ddie', dnode, dpk, 'ku', 'kd')
        lines += b
    else:   # ideal Thevenin: PWL linear ramp (0-100 % time = edge[kind]) behind rs, plus C_comp at die, plus package
        vcc = 3.3
        pts = [(0, 0.0)]
        lvl = 0.0
        for te, kind in B.EDGES:
            tr = edge[kind]
            pts += [(te, lvl)]
            lvl = vcc if kind == 'rise' else 0.0
            pts += [(te + tr, lvl)]
        pts += [(B.T_END, lvl)]
        lines += ['Vth vth 0 PWL(%s)' % ' '.join('%g %g' % p for p in pts), 'Rth vth ddie %g' % rs]
        cc = dm.kw['c_comp'][I.COL[corner]]
        R, L, C = dpk
        lines += ['CcD ddie 0 %g' % cc, 'RpD ddie D_pk %g' % max(R, 1e-4), 'LpD D_pk %s %g' % (dnode, L), 'CpD %s 0 %g' % (dnode, C)]
    if recv == 'ibis':
        b, _ = I.buffer_netlist('R', rm, corner, 'rdie', rnode, rpk)
        lines += b
    else:   # linear receiver: C_comp + package only (no clamps)
        cc = rm.kw['c_comp'][I.COL[corner]]
        R, L, C = rpk
        lines += ['CcR rdie 0 %g' % cc, 'RpR rdie R_pk %g' % max(R, 1e-4), 'LpR R_pk %s %g' % (rnode, L), 'CpR %s 0 %g' % (rnode, C)]
    lines += el
    if extra: lines += extra
    lines += ['.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear', '.ic V(ddie)=0 V(rdie)=0',
              '.tran 5p %g 0 5p' % B.T_END, '.end']
    return lines, dm, rm, dpk, rpk, rep

def run(*a, **k):
    lines, dm, rm, dpk, rpk, rep = build(*a, **k)
    r = ngs.run(lines)
    m = B.measure(r['time'], r['rdie'], 3.3)
    return m, r, dict(dm=dm.name, rm=rm.name, dpk=dpk, rpk=rpk, rep=rep)

def fmt(m):
    return 'ovs %+.3f  uns %.3f  10-90 %.3f ns  vmax %.3f vmin %.3f' % (m['overshoot'], m['undershoot'], m['t10_90_ns'] or -1, m['vmax'], m['vmin'])
