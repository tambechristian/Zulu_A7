# -*- coding: utf-8 -*-
"""Read-direction SI of the PLANNED south-row series Rs (design_arrays.py / plan_south.py) at their real positions.

    python si/series_r/design_arrays_sim.py [--r 22] [--nets D0,...] [--workers 6]

Uses si/spice/bus_sim.simulate() unchanged.  For each net Dn the copper of tools/route/model.json is edited exactly as the
plan says (old Bottom stub removed; new feed U3 pad -> R pad 1 on net SDRAM-Dn; new fold-back return R pad 2 -> first
via on net Dn), then the two halves are netlisted separately by bus_sim.net_elements (R pad 1 stands in as the 'U1'
end of the SDRAM-Dn half, R pad 2 as the 'U3' end of the Dn half), node names are prefixed, and the resistor joins
them with the same 0201 parasitics as parasitic_sim.py (ESL 0.5 nH, 0.05 pF across, 0.08 pF pad-to-plane each end).
Nothing under si/spice is modified.  Writes design_arrays_sim_r<R>.json here.
"""
import copy
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
SPICE = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, HERE)
sys.path.insert(0, SPICE)

LMAP = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG', 'L2-GND': 'L2-GND',
        'L5-VCC3V3': 'L5-VCC3V3'}
PAR = dict(L=0.5e-9, Cpar=0.05e-12, Cpad=0.08e-12)


def plan_for(net):
    import design_arrays as DA
    import plan_south as S
    Rs, ex, notes = S.south(DA.tpl)
    return Rs[net], DA.old_stub(net)


def edited_model(M, net):
    R, stub = plan_for(net)
    sn = 'SDRAM-' + net
    M = copy.deepcopy(M)

    def same(a, b):
        return abs(a - b) < 2e-3
    keep = []
    for t in M['tracks']:
        drop = False
        if t['net'] == net and t['layer'] == 'Bottom Layer':
            for s in stub:
                if (same(t['x1'], s['x1']) and same(t['y1'], s['y1']) and same(t['x2'], s['x2']) and same(t['y2'], s['y2'])) or \
                   (same(t['x1'], s['x2']) and same(t['y1'], s['y2']) and same(t['x2'], s['x1']) and same(t['y2'], s['y1'])):
                    drop = True
        if not drop:
            keep.append(t)
    assert len(keep) == len(M['tracks']) - len(stub), (net, 'stub not found in model.json')
    M['tracks'] = keep
    for t in R['tracks']:
        M['tracks'].append(dict(net=t['net'], layer=LMAP[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for p in M['pads']:
        if p['ref'] == 'U3' and p['net'] == net:
            p['net'] = sn
    p1, p2 = R['pads']
    M['pads'].append(dict(ref='U1', pad='RA', net=sn, x=p1['x'], y=p1['y'], shape='rect', w=0.3, h=0.3,
                          layers=['Bottom Layer'], drill=0.0, plated=False))
    M['pads'].append(dict(ref='U3', pad='RB', net=net, x=p2['x'], y=p2['y'], shape='rect', w=0.3, h=0.3,
                          layers=['Bottom Layer'], drill=0.0, plated=False))
    return M


def _prefix(lines, pre):
    out = []
    for ln in lines:
        tok = ln.split()
        tok[0] = tok[0][0] + pre + tok[0][1:]
        tok = [tok[0]] + [(pre + x if re.fullmatch(r'n\d+', x) else x) for x in tok[1:]]
        out.append(' '.join(tok))
    return out


def run_case(task):
    net, corner, rser = task
    os.environ['ZULU_RSER'] = '0'
    import bus_sim as B
    import ibis2spice as I
    import ds181_check as D
    import parasitic_sim as PS
    B.STACK = 'fab'
    M0 = json.load(open(B.MODEL))
    M = edited_model(M0, net)
    orig = B.net_elements

    def patched(Mx, n, _orig=orig):
        ea, a1, a3, ra = _orig(Mx, 'SDRAM-' + net)     # a1 = R pad 1 (stand-in 'U1'), a3 = real U3 pin
        eb, b1, b3, rb = _orig(Mx, net)                 # b1 = real U1 ball, b3 = R pad 2 (stand-in 'U3')
        el = _prefix(ea, 'a') + _prefix(eb, 'b')
        A, Bn = 'a' + a1, 'b' + b3
        el += ['Rser %s rx %g' % (A, rser), 'Lesl rx %s %g' % (Bn, PAR['L']), 'Cpar %s %s %g' % (A, Bn, PAR['Cpar']),
               'Cpda %s 0 %g' % (A, PAR['Cpad']), 'Cpdb %s 0 %g' % (Bn, PAR['Cpad'])]
        rep = dict(rb)
        rep['u1_pin'], rep['u3_pin'] = rb['u1_pin'], ra['u3_pin']
        rep['len_mm'] = ra['len_mm'] + rb['len_mm']
        rep['delay_ps'] = ra['delay_ps'] + rb['delay_ps']
        rep['feed_mm'], rep['feed_ps'] = ra['len_mm'], ra['delay_ps']
        rep['connected'] = ra['connected'] and rb['connected']
        return el, 'b' + b1, 'a' + a3, rep
    B.net_elements = patched
    U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
    try:
        tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, 'read', corner, U1, U3)
    except Exception as e:
        return dict(net=net, corner=corner, r=rser, error=str(e)[:600])
    rail = B.VRAIL[corner]
    m = B.measure(tt, vr, rail)
    return dict(net=net, corner=corner, r=rser, die_vmin=float(vr.min()), die_vmax=float(vr.max()),
                ball_vmin=float(vrp.min()), ball_vmax=float(vrp.max()),
                die_budget=PS.budget(tt, vr, rail, D), ball_budget=PS.budget(tt, vrp, rail, D),
                t10_90_ns=m['t10_90_ns'], feed_mm=rep['feed_mm'], feed_ps=rep['feed_ps'], len_mm=rep['len_mm'],
                connected=rep['connected'])


def main():
    import multiprocessing as mp
    a = sys.argv[1:]
    r = float(a[a.index('--r') + 1]) if '--r' in a else 22.0
    nets = a[a.index('--nets') + 1].split(',') if '--nets' in a else ['D%d' % i for i in range(8)]
    workers = min(6, int(a[a.index('--workers') + 1]) if '--workers' in a else 6)
    tasks = [(n, c, r) for c in ('typ', 'max') for n in nets]
    out = []
    with mp.Pool(workers, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(run_case, tasks):
            out.append(res)
            print(json.dumps(res), flush=True)
    out.sort(key=lambda x: (x['corner'], int(x['net'][1:])))
    json.dump(out, open(HERE + '/design_arrays_sim_r%g.json' % r, 'w'), indent=1)


if __name__ == '__main__':
    main()
