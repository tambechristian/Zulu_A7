"""design_top_sim.py -- READ-direction SI of the series R at a real position on the route (si/spice/bus_sim.py's own
simulate(), unchanged; only the net's copper and the R element differ).

Two modes:
  --sweep NETS          R (ideal 22 ohm + optional 0201 parasitics) inserted at arc positions along the existing route
                        (track cut, 0.6 mm removed = the R's pad pitch); 'pin' = bus_sim's ZULU_RSER (R at U3's pin)
  --plan design_top.json  the planned copper of every placed resistor (removed / added tracks, new stacked vias,
                        the two R pads) for each net in the plan

The R is an element between the nodes of two pseudo-pads ref 'RSER' pad 'A' (U3 side) and 'B' (U1 side). The 0201
variant adds 0.5 nH ESL, 0.05 pF across and 0.08 pF per pad to ground (parasitic_sim.py's '0201' set).
Writes only into si/series_r: design_top_sim_<tag>.json (no waveforms are saved).
--scenarios read,write (default read): 'write' = U1 drives, U3 receives (die/pin = U3's side then).

    python design_top_sim.py --sweep D8,D3 --positions pin,1.5,3,6,9,12 --corners max --workers 6
    python design_top_sim.py --plan design_top.json --corners typ,max --workers 6
"""
import inspect
import json
import math
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
SPICE = os.path.join(os.path.dirname(HERE), 'spice')
sys.path.insert(0, SPICE)
LMAP = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}
R_OHM = 22.0
PAR = dict(L=0.5e-9, Cpar=0.05e-12, Cpad=0.08e-12)


def lm(L):
    return LMAP.get(L, L)


def patch_bus_sim(B, r_ohm, par):
    """net_elements + an R between the pseudo-pads RSER-A and RSER-B (textual injection into bus_sim's own code)"""
    src = textwrap.dedent(inspect.getsource(B.net_elements))
    hook = "    u1 = [p for p in pads if p['ref'] == 'U1']\n"
    assert hook in src
    inj = ("    _ra = [k for k, p in enumerate(pads) if p['ref'] == 'RSER' and p['pad'] == 'A']\n"
           "    _rb = [k for k, p in enumerate(pads) if p['ref'] == 'RSER' and p['pad'] == 'B']\n"
           "    if _ra and _rb:\n"
           "        _na = node(('p', _ra[0], pads[_ra[0]]['layers'][0]))\n"
           "        _nb = node(('p', _rb[0], pads[_rb[0]]['layers'][0]))\n"
           "        if _PAR:\n"
           "            el.append('Rser %s rx %g' % (_na, _R))\n"
           "            el.append('Lesl rx %s %g' % (_nb, _PAR['L']))\n"
           "            el.append('Cpar %s %s %g' % (_na, _nb, _PAR['Cpar']))\n"
           "            el.append('Cpda %s 0 %g' % (_na, _PAR['Cpad']))\n"
           "            el.append('Cpdb %s 0 %g' % (_nb, _PAR['Cpad']))\n"
           "        else:\n"
           "            el.append('Rser %s %s %g' % (_na, _nb, _R))\n")
    src = src.replace(hook, inj + hook)
    g = dict(B.__dict__)
    g['_R'], g['_PAR'] = r_ohm, par
    exec(compile(src, 'net_elements_patched', 'exec'), g)
    B.net_elements = g['net_elements']


def same_track(t, x1, y1, x2, y2, tol=0.003):
    a = abs(t['x1'] - x1) < tol and abs(t['y1'] - y1) < tol and abs(t['x2'] - x2) < tol and abs(t['y2'] - y2) < tol
    b = abs(t['x1'] - x2) < tol and abs(t['y1'] - y2) < tol and abs(t['x2'] - x1) < tol and abs(t['y2'] - y1) < tol
    return a or b


def rpad(ref_pad, x, y, layer, net):
    return {'ref': 'RSER', 'pad': ref_pad, 'net': net, 'x': x, 'y': y, 'shape': 'rect', 'w': 0.3, 'h': 0.3,
            'layers': [layer], 'drill': 0.0, 'plated': False}


def model_sweep(M, net, s_cut, EX):
    """cut the net's path at arc position s_cut (tracks only), remove 0.6 mm, put RSER-A/B at the two ends"""
    path = EX['d_escapes'][net]['path']
    trk = [o for o in path if o['kind'] == 'track']
    acc = 0.0
    for o in trk:
        L = math.hypot(o['x2'] - o['x1'], o['y2'] - o['y1'])
        if acc + L >= s_cut and L > 0.7:
            u = max(0.0, min(1.0, (s_cut - acc) / L))
            u2 = min(1.0, u + 0.6 / L)
            if u2 - u < 0.6 / L - 1e-9:
                u = 1.0 - 0.6 / L
                u2 = 1.0
            ax, ay = o['x1'] + u * (o['x2'] - o['x1']), o['y1'] + u * (o['y2'] - o['y1'])
            bx, by = o['x1'] + u2 * (o['x2'] - o['x1']), o['y1'] + u2 * (o['y2'] - o['y1'])
            hits = [i for i, t in enumerate(M['tracks']) if t['net'] == net and t['layer'] == lm(o['layer']) and
                    same_track(t, o['x1'], o['y1'], o['x2'], o['y2'])]
            assert len(hits) >= 1, (net, o)
            t0 = M['tracks'][hits[0]]
            M['tracks'] = [t for i, t in enumerate(M['tracks']) if i != hits[0]]
            if u > 1e-6:
                M['tracks'].append(dict(t0, x1=o['x1'], y1=o['y1'], x2=ax, y2=ay))
            if u2 < 1 - 1e-6:
                M['tracks'].append(dict(t0, x1=bx, y1=by, x2=o['x2'], y2=o['y2']))
            M['pads'] = M['pads'] + [rpad('A', ax, ay, lm(o['layer']), net), rpad('B', bx, by, lm(o['layer']), net)]
            return dict(layer=o['layer'], at=(round(ax, 3), round(ay, 3)), s=round(acc + u * L, 3))
        acc += L
    raise ValueError('no track long enough at %s on %s' % (s_cut, net))


def model_plan(M, net, P):
    """apply one net's planned copper (design_top.json 'placements' entry)"""
    for r in P['remove_tracks']:
        hits = [i for i, t in enumerate(M['tracks']) if t['net'] == net and t['layer'] == lm(r['layer']) and
                same_track(t, r['x1'], r['y1'], r['x2'], r['y2'])]
        assert len(hits) == 1, (net, r, hits)
        M['tracks'] = [t for i, t in enumerate(M['tracks']) if i != hits[0]]
    for t in P['add_tracks']:
        M['tracks'].append(dict(net=net, layer=lm(t['layer']), w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in P['add_vias']:
        M['vias'].append(dict(net=net, x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=[lm(L) for L in v['span']]))
    a, b = P['pad_A'], P['pad_B']
    M['pads'] = M['pads'] + [rpad('A', a[0], a[1], 'Top Layer', net), rpad('B', b[0], b[1], 'Top Layer', net)]
    return dict(at=P['center'])


def run_case(task):
    mode, net, corner, arg, variant, scen = task
    import bus_sim as B
    import ibis2spice as I
    import ds181_check as D
    B.STACK = 'fab'
    par = PAR if variant == '0201' else None
    EX = json.load(open(os.path.join(HERE, 'board_extract.json')))
    M = json.load(open(B.MODEL))
    info = {}
    if mode == 'sweep' and arg == 'pin':
        os.environ['ZULU_RSER'] = str(R_OHM)
        if par:
            orig = B.net_elements

            def patched(Mx, n, _orig=orig, _p=par):
                el, n1, n3, rep = _orig(Mx, n)
                el = el + ['Lesl rx %s %g' % (n3, _p['L']), 'Cpar u3pin %s %g' % (n3, _p['Cpar']),
                           'Cpda u3pin 0 %g' % _p['Cpad'], 'Cpdb %s 0 %g' % (n3, _p['Cpad'])]
                return el, n1, 'rx', rep
            B.net_elements = patched
        info = {'s': 0.0, 'layer': 'pin'}
    else:
        os.environ['ZULU_RSER'] = '0'
        patch_bus_sim(B, R_OHM, par)
        if mode == 'sweep':
            try:
                info = model_sweep(M, net, float(arg), EX)
            except ValueError as e:
                return dict(net=net, corner=corner, pos=arg, variant=variant, error=str(e))
        else:
            P = json.load(open(arg))['placements'][net]
            info = model_plan(M, net, P)
    U1, U3 = I.Ibis(B.U1_IBS), I.Ibis(B.U3_IBS)
    try:
        tt, vr, vd, vrp, vcc, rm, dm, rep = B.simulate(M, net, scen, corner, U1, U3)
    except Exception as e:
        return dict(net=net, corner=corner, scenario=scen, pos=arg, variant=variant, error=str(e)[:500])
    rail = B.VRAIL[corner]

    def budget(t, v):
        rr = 0.0
        for w in D.windows(t, v, rail):
            for peak, dur, tab in ((w['peak_over'], w['t_over_ns'], D.OVER), (w['peak_under'], w['t_under_ns'], D.UNDER)):
                if peak <= 0.2:
                    continue
                lim = D.allowed(tab, peak)
                rr = max(rr, (dur / 7.5 * 100) / lim if lim > 0 else 1e9)
        return rr
    m = B.measure(tt, vr, rail)
    return dict(net=net, corner=corner, scenario=scen, pos=arg if mode == 'sweep' else 'plan', variant=variant, info=info,
                connected=rep['connected'], len_mm=round(rep['len_mm'], 3), vias=rep['vias'],
                die_vmin=float(vr.min()), die_vmax=float(vr.max()), ball_vmin=float(vrp.min()), ball_vmax=float(vrp.max()),
                die_budget=budget(tt, vr), ball_budget=budget(tt, vrp), t10_90_ns=m['t10_90_ns'])


def main():
    import multiprocessing as mp
    a = sys.argv[1:]
    corners = a[a.index('--corners') + 1].split(',') if '--corners' in a else ['max']
    workers = min(6, int(a[a.index('--workers') + 1]) if '--workers' in a else 6)
    variants = a[a.index('--variants') + 1].split(',') if '--variants' in a else ['ideal']
    scens = a[a.index('--scenarios') + 1].split(',') if '--scenarios' in a else ['read']
    if '--sweep' in a:
        nets = a[a.index('--sweep') + 1].split(',')
        pos = a[a.index('--positions') + 1].split(',')
        tasks = [('sweep', n, c, p, v, sc) for sc in scens for v in variants for c in corners for n in nets for p in pos]
        tag = a[a.index('--tag') + 1] if '--tag' in a else 'sweep'
    else:
        plan = os.path.join(HERE, a[a.index('--plan') + 1])
        nets = sorted(json.load(open(plan))['placements'], key=lambda n: int(n[1:]))
        if '--nets' in a:
            nets = a[a.index('--nets') + 1].split(',')
        tasks = [('plan', n, c, plan, v, sc) for sc in scens for v in variants for c in corners for n in nets]
        tag = a[a.index('--tag') + 1] if '--tag' in a else 'plan'
    out = []
    with mp.Pool(workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run_case, tasks):
            out.append(r)
            if 'error' in r:
                print('ERROR', r['net'], r['corner'], r['pos'], r['error'][:300], flush=True)
            else:
                print('%-5s ' % r['scenario'] + '%-4s %-3s %-6s %-5s ball %+.3f/%.3f V budget %5.1f%% | die %+.3f budget %4.1f%% | t10-90 %.2f ns conn %s %s' % (
                    r['net'], r['corner'], r['pos'], r['variant'], r['ball_vmin'], r['ball_vmax'], 100 * r['ball_budget'],
                    r['die_vmin'], 100 * r['die_budget'], r['t10_90_ns'] or -1, r['connected'], r['info']), flush=True)
    json.dump(out, open(os.path.join(HERE, 'design_top_sim_%s.json' % tag), 'w'), indent=1)
    print('done %d cases, %d errors' % (len(out), sum('error' in r for r in out)))


if __name__ == '__main__':
    main()
