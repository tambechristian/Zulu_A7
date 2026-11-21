"""Re-simulate the READ case of the DQ nets that design_bottom.py placed, with the R where the plan puts it.

For each placed net Dn the model is si/spice/bus_sim.py's own netlist (tools/route/model.json, fab stack), changed only by:
  * the old Bottom stub U3 pad -> first via is removed,
  * the plan's 'return' track (R pad B -> first via) is added on Bottom at its width,
  * U3's pad is moved to R pad B (so bus_sim's U3 node is the line side of the R),
  * between the SDRAM driver (die+package from IBIS, as before) and that node: the plan's 'neck' as a lumped pi section
    (Z0/td of the Bottom track from fieldsolve), then R, then the 0201 parasitics used by parasitic_sim.py
    (ESL 0.5 nH, 0.05 pF across the body, 0.08 pF pad-to-plane each end).
Reference case 'at_pin' = the ideal R right at U3's pin on the unchanged board (ZULU_RSER), i.e. results_r22.json.
Nothing under si/spice is modified; results go to sim_bottom.json in this folder.

    python sim_bottom.py [--r 22] [--workers 6] [--plan design_bottom.json]
"""
import json, os, sys, math

HERE = os.path.dirname(os.path.abspath(__file__))
SPICE = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SPICE)
PAR = dict(L=0.5e-9, Cpar=0.05e-12, Cpad=0.08e-12)


def budget(t, v, rail, D):
    rr = 0.0
    for w in D.windows(t, v, rail):
        for peak, dur, tab in ((w['peak_over'], w['t_over_ns'], D.OVER), (w['peak_under'], w['t_under_ns'], D.UNDER)):
            if peak <= 0.2:
                continue
            lim = D.allowed(tab, peak)
            rr = max(rr, (dur / 7.5 * 100) / lim if lim > 0 else 1e9)
    return rr


def modify(M, net, pl, stub):
    tr = M['tracks']
    hit = [t for t in tr if t['net'] == net and t['layer'] == 'Bottom Layer' and
           ((abs(t['x1'] - stub['x1']) < 2e-3 and abs(t['y1'] - stub['y1']) < 2e-3 and abs(t['x2'] - stub['x2']) < 2e-3 and abs(t['y2'] - stub['y2']) < 2e-3) or
            (abs(t['x2'] - stub['x1']) < 2e-3 and abs(t['y2'] - stub['y1']) < 2e-3 and abs(t['x1'] - stub['x2']) < 2e-3 and abs(t['y1'] - stub['y2']) < 2e-3))]
    assert len(hit) >= 1, (net, 'stub not in model.json')
    for t in hit:
        tr.remove(t)
    ret = pl['ret']
    for a, b in zip(ret, ret[1:]):
        tr.append(dict(net=net, layer='Bottom Layer', w=pl['w'], x1=a[0], y1=a[1], x2=b[0], y2=b[1]))
    u3 = [p for p in M['pads'] if p['net'] == net and p['ref'] == 'U3']
    assert len(u3) == 1
    u3[0].update(x=ret[0][0], y=ret[0][1], w=0.3, h=0.3, shape='rect')
    return M


def run_case(task):
    net, corner, mode, R, pl, stub = task
    import bus_sim as B
    import ibis2spice as I
    import ds181_check as D
    B.STACK = 'fab'
    M = json.load(open(B.MODEL))
    if mode == 'at_pin':
        os.environ['ZULU_RSER'] = str(R)
    else:
        os.environ['ZULU_RSER'] = '0'
        M = modify(M, net, pl, stub)
        orig = B.net_elements
        neck_len = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pl['neck'], pl['neck'][1:]))
        neck_len += pl['ph'] / 2 - 0.15        # pad centre -> where the neck leaves the pad
        lp = B.line('Bottom Layer', pl['w'])
        td = neck_len * lp['td_ps_per_mm'] * 1e-12

        def patched(M_, n_, _orig=orig):
            el, n1, n3, rep = _orig(M_, n_)
            el = el + ['Lneck u3drv ra %g' % max(lp['Z0'] * td, 1e-15), 'Cneck1 u3drv 0 %g' % (td / lp['Z0'] / 2),
                       'Cneck2 ra 0 %g' % (td / lp['Z0'] / 2), 'Rplan ra rx %g' % R,
                       'Lesl rx %s %g' % (n3, PAR['L']), 'Cpar ra %s %g' % (n3, PAR['Cpar']),
                       'Cpda ra 0 %g' % PAR['Cpad'], 'Cpdb %s 0 %g' % (n3, PAR['Cpad'])]
            return el, n1, 'u3drv', rep
        B.net_elements = patched
    U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
    try:
        tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, 'read', corner, U1, U3)
    except Exception as e:
        return dict(net=net, corner=corner, mode=mode, error=str(e)[:400])
    rail = B.VRAIL[corner]
    m = B.measure(tt, vr, rail)
    return dict(net=net, corner=corner, mode=mode, r=R, die_vmin=float(vr.min()), die_vmax=float(vr.max()),
                ball_vmin=float(vrp.min()), ball_vmax=float(vrp.max()), die_budget=budget(tt, vr, rail, D),
                ball_budget=budget(tt, vrp, rail, D), t10_90_ns=m['t10_90_ns'], connected=rep.get('connected'))


def main():
    import multiprocessing as mp
    a = sys.argv[1:]
    R = float(a[a.index('--r') + 1]) if '--r' in a else 22.0
    workers = min(6, int(a[a.index('--workers') + 1]) if '--workers' in a else 6)
    plan = json.load(open(a[a.index('--plan') + 1] if '--plan' in a else os.path.join(HERE, 'design_bottom.json')))
    ex = json.load(open(os.path.join(HERE, 'board_extract.json')))
    tasks = []
    for p in plan['placements']:
        n = int(p['nets'].split('SDRAM-D')[1].split()[0])
        net = 'D%d' % n
        e = ex['d_escapes'][net]
        pl = dict(neck=[tuple(q) for q in p['neck_pts']], ret=[tuple(q) for q in p['return_pts']], w=p['neck_width'],
                  ph=e['u3_pad']['h'])
        # the neck is stored R pad A -> U3 pad; reverse is irrelevant for its length
        for corner in ('typ', 'max'):
            for mode in ('at_pin', 'placed'):
                tasks.append((net, corner, mode, R, pl, e['bottom_stub'][0]))
    out = []
    with mp.Pool(workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_case, tasks):
            out.append(r)
            print(json.dumps(r), flush=True)
    json.dump(dict(plan=a[a.index('--plan') + 1] if '--plan' in a else 'design_bottom.json', R=R, results=out),
              open(os.path.join(HERE, 'sim_bottom.json'), 'w'), indent=1)
    print('\nnet  corner | at_pin ball Vmin / budget | placed ball Vmin / budget | placed die budget')
    for net in sorted(set(r['net'] for r in out), key=lambda s: int(s[1:])):
        for c in ('typ', 'max'):
            g = {r['mode']: r for r in out if r['net'] == net and r['corner'] == c and 'error' not in r}
            if len(g) == 2:
                print('%-4s %-4s | %+.3f V %5.1f %% | %+.3f V %5.1f %% | %5.1f %%' % (
                    net, c, g['at_pin']['ball_vmin'], 100 * g['at_pin']['ball_budget'], g['placed']['ball_vmin'],
                    100 * g['placed']['ball_budget'], 100 * g['placed']['die_budget']))
    print('errors:', sum('error' in r for r in out))


if __name__ == '__main__':
    main()
