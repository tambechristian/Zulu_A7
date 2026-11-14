"""Read-path timing effect of a series R at U3's DQ pins (premise check, planning only; writes nothing outside this folder).

1. Reference-load delay: the AS4C32M16SB DQ_100% IBIS driver (same behavioural model and package as bus_sim.py) into
   the datasheet/IBIS timing load (Rref 50 ohm to Vref 1.4 V, Cref 30 pF at the pin), measured at the pin at
   Vmeas 1.4 V. tAC/tOH in the datasheet are specified into this load (Table 16 note 6, Figure 18.2).
2. Board delay: the saved si/spice/wave/*.npz read waveforms (R = 0/15/22/33 ohm), measured at U1's die (rx_die) at
   1.65 V = DS181 Table 19 VMEAS for LVCMOS33 (the threshold TIOPI is specified at).
3. Flight-time-compensated delay = board crossing - reference crossing, per net, per edge, per corner.
   Edges used: 8.5 ns fall, 16.0 ns rise, 23.5 ns fall (the 1.0 ns rise starts from the .ic state and is skipped).
   For each edge both the FIRST and the LAST crossing of 1.65 V inside the bit are kept (ringback makes them differ).
Output: timing.json + a printed table.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SP)
import ngs
import ibis2spice as I

U3 = I.Ibis(os.path.join(os.path.dirname(HERE), 'ibis', 'as4c32m16sb', 'Alliance-Memory_AS4C32M16SB-7TCN_Ibis.ibs'))
EDGES = [(1.0e-9, 'rise'), (8.5e-9, 'fall'), (16.0e-9, 'rise'), (23.5e-9, 'fall')]
USE = EDGES[1:]
T_END = 32e-9
UI = 7.5e-9
VRAIL = {'typ': 3.3, 'max': 3.465}
DQPIN = {0: '2', 1: '4', 2: '5', 3: '7', 4: '8', 5: '10', 6: '11', 7: '13',
         8: '42', 9: '44', 10: '45', 11: '47', 12: '48', 13: '50', 14: '51', 15: '53'}


def crossings(t, v, te, kind, vth):
    s = (t >= te) & (t < te + UI)
    tt, vv = t[s], v[s]
    above = vv >= vth
    idx = np.flatnonzero(above[1:] != above[:-1])
    if kind == 'rise':
        idx = [i for i in idx if not above[i] and above[i + 1]]
    else:
        idx = [i for i in idx if above[i] and not above[i + 1]]
    out = []
    for i in idx:   # linear interpolation
        f = (vth - vv[i]) / (vv[i + 1] - vv[i])
        out.append(tt[i] + f * (tt[i + 1] - tt[i]))
    return out


def ref_load(corner, pin, rser=0.0, dt=2e-12):
    m = U3.model('DQ_100%')
    rail = VRAIL[corner]
    t, ku, kd = I.weights_pwl(m, corner, EDGES, T_END)
    from bus_sim import pwl_source
    lines = ['* DQ ref load %s pin %s' % (corner, pin)]
    lines += pwl_source('ku', 'ku', t, ku) + pwl_source('kd', 'kd', t, kd)
    b, _ = I.buffer_netlist('D', m, corner, 'ddie', 'dpin', I.pkg_for(U3, pin, corner), 'ku', 'kd', rail=rail)
    lines += b
    node = 'dpin'
    if rser:
        lines += ['Rser dpin rnode %g' % rser]
        node = 'rnode'
    lines += ['Vref vref 0 1.4', 'Rref %s vref 50' % node, 'Cref %s 0 30p' % node,
              '.options reltol=1e-4 abstol=1e-12 vntol=1e-6 method=gear', '.ic V(ddie)=0',
              '.tran %g %g 0 %g' % (dt, T_END, dt), '.end']
    r = ngs.run(lines)
    tt, v = r['time'], r[node]
    res = {}
    for te, kind in USE:
        c = crossings(tt, v, te, kind, 1.4)
        res['%s@%.1f' % (kind, te * 1e9)] = (c[0] - te) * 1e9
    return res


def main():
    out = {'ref': {}, 'board': {}}
    for corner in ('typ', 'max'):
        for d in range(16):
            out['ref'].setdefault(corner, {})['D%d' % d] = ref_load(corner, DQPIN[d])
    print('Reference-load delay (U3 DQ_100% into 50 ohm/1.4 V + 30 pF, at pin, 1.4 V), ns after the stimulus edge:')
    for corner in ('typ', 'max'):
        v = [x for n in out['ref'][corner].values() for x in n.values()]
        r = [n['rise@16.0'] for n in out['ref'][corner].values()]
        f = [n['fall@8.5'] for n in out['ref'][corner].values()]
        print('  %-3s rise %.3f..%.3f  fall %.3f..%.3f' % (corner, min(r), max(r), min(f), max(f)))
    for tag in ('', '_r15', '_r22', '_r33'):
        R = tag[2:] or '0'
        for corner in ('typ', 'max'):
            rows = {}
            for d in range(16):
                net = 'D%d' % d
                z = np.load(os.path.join(SP, 'wave', '%s_read_%s_fab%s.npz' % (net, corner, tag)))
                t, v = z['t'], z['rx_die']
                e = {}
                for te, kind in USE:
                    c = crossings(t, v, te, kind, 1.65)
                    key = '%s@%.1f' % (kind, te * 1e9)
                    ref = out['ref'][corner][net][key]
                    e[key] = {'first': (c[0] - te) * 1e9 - ref, 'last': (c[-1] - te) * 1e9 - ref, 'n': len(c),
                              'raw_first': (c[0] - te) * 1e9}
                rows[net] = e
            out['board'].setdefault(R, {})[corner] = rows
    json.dump(out, open(os.path.join(HERE, 'timing.json'), 'w'), indent=1)
    print('\nFlight-time-compensated delay at U1 die (1.65 V) minus reference-load delay (1.4 V), ns, fab stack, D0-D15:')
    print('R    corner | rise first min..max | fall first min..max | latest (last crossing) | spread all | multi-crossings')
    base = {}
    for R in ('0', '15', '22', '33'):
        for corner in ('typ', 'max'):
            rows = out['board'][R][corner]
            rf = [e['first'] for n in rows.values() for k, e in n.items() if k.startswith('rise')]
            ff = [e['first'] for n in rows.values() for k, e in n.items() if k.startswith('fall')]
            last = [e['last'] for n in rows.values() for e in n.values()]
            first = [e['first'] for n in rows.values() for e in n.values()]
            multi = sum(e['n'] > 1 for n in rows.values() for e in n.values())
            print('%-4s %-6s | %6.3f..%6.3f | %6.3f..%6.3f | %6.3f | %5.3f | %d' % (
                R, corner, min(rf), max(rf), min(ff), max(ff), max(last), max(last) - min(first), multi))
            if R == '0':
                base[corner] = (min(first), max(last))
            else:
                print('       vs R0: earliest %+.3f ns, latest %+.3f ns, window loss %+.3f ns' % (
                    min(first) - base[corner][0], max(last) - base[corner][1],
                    (max(last) - min(first)) - (base[corner][1] - base[corner][0])))
    # the 22-ohm in the reference load itself (sanity: what the R costs into the datasheet load)
    print('\nSanity: 22 ohm in series with the reference load, D0 pin->load 1.4 V:')
    for corner in ('typ', 'max'):
        a = ref_load(corner, DQPIN[0]); b = ref_load(corner, DQPIN[0], 22.0)
        print('  %s %s' % (corner, {k: round(b[k] - a[k], 3) for k in a}))


if __name__ == '__main__':
    main()
