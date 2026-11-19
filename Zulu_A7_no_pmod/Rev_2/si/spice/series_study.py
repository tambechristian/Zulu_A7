"""Summarise the U3 DQ series-resistor study (R = 0/15/22/33 ohm at the SDRAM pin): DS181 Table 4 budget at the U1
die and ball for reads, SDRAM-input extremes for writes on D0-D15, edge times. Fab stack, typ and max corners."""
import json, numpy as np, ds181_check as D
DN = ['D%d' % i for i in range(16)]
for tag in ('', '_r15', '_r22', '_r33'):
    res = 'results_all.json' if not tag else 'results%s.json' % tag
    R = [r for r in json.load(open(res)) if 'error' not in r and r['stack'] == 'fab' and r['net'] in DN]
    for sc in ('read', 'write'):
        for c in ('typ', 'max'):
            g = [r for r in R if r['corner'] == c and r['scenario'] == sc]
            line = []
            for node in ('rx_die', 'rx_pin'):
                worst = 0; fails = 0; vmin = 9; vmax = -9
                for r in g:
                    z = np.load('wave/%s_%s_%s_fab%s.npz' % (r['net'], sc, c, tag)); t = z['t']; v = z[node]
                    vmin = min(vmin, v.min()); vmax = max(vmax, v.max())
                    if sc == 'read':
                        rr = 0
                        for w in D.windows(t, v, r['rail']):
                            for peak, dur, tab in ((w['peak_over'], w['t_over_ns'], D.OVER), (w['peak_under'], w['t_under_ns'], D.UNDER)):
                                if peak <= 0.2:
                                    continue
                                lim = D.allowed(tab, peak); rr = max(rr, (dur / 7.5 * 100) / lim if lim > 0 else 1e9)
                        worst = max(worst, rr); fails += rr > 1
                line.append('%s Vmin %+.2f Vmax %.2f' % (node[3:], vmin, vmax) + (' budget %5.0f%% fails %2d/16' % (min(100 * worst, 99999), fails) if sc == 'read' else ''))
            t1090 = [r['t10_90_ns'] for r in g]
            print('%-5s %-5s %-3s | %s | %s | t10-90 %.2f-%.2f ns' % (tag[1:] if tag else 'r0', sc, c, line[0], line[1], min(t1090), max(t1090)))
