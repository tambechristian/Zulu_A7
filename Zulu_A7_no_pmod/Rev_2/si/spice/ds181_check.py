"""READ-direction compliance at U1 (Artix-7 HR bank, VCCO = VCC3V3) against DS181 v1.27.1 Table 4
('VIN Maximum Allowed AC Voltage Overshoot and Undershoot for HR I/O Banks', -55..125 C).
Note 2 of the table: the peak voltage, and the duration above VCCO + 0.20 V / below GND - 0.20 V, must not exceed the
table values. Per edge: peak -> allowed % of UI (conservative: the next tabulated level at or beyond the peak);
measured % = time beyond the 0.20 V band / UI. Checked at the die and at the ball, for UI 7.5 ns (133 MHz) and 10 ns.
Also WRITE direction at U3 against the AS4C32M16SB B-die absolute maximum: 4.6 V / -1.0 V for pulse width <= 3 ns."""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OVER = [(0.55, 100), (0.60, 46.6), (0.65, 21.2), (0.70, 9.75), (0.75, 4.55), (0.80, 2.15), (0.85, 1.02), (0.90, 0.49), (0.95, 0.24)]
UNDER = [(0.40, 100), (0.45, 61.7), (0.50, 25.8), (0.55, 11.0), (0.60, 4.77), (0.65, 2.10), (0.70, 0.94), (0.75, 0.43),
         (0.80, 0.20), (0.85, 0.09), (0.90, 0.04), (0.95, 0.02)]
EDGES = [1.0e-9, 8.5e-9, 16.0e-9, 23.5e-9, 32e-9]


def allowed(table, excess):
    if excess <= table[0][0]:
        return 100.0
    for lvl, pct in table:
        if lvl >= excess - 1e-12:
            return pct
    return 0.0


def windows(t, v, rail):
    out = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        s = (t >= a) & (t < b)
        tt, vv = t[s], v[s]
        dt = np.diff(tt, append=tt[-1])
        out.append({'peak_over': float(vv.max() - rail), 't_over_ns': float(np.sum(dt[vv > rail + 0.20]) * 1e9),
                    'peak_under': float(-vv.min()), 't_under_ns': float(np.sum(dt[vv < -0.20]) * 1e9)})
    return out


def main():
    R = [r for r in json.load(open(os.path.join(HERE, 'results_all.json'))) if 'error' not in r]
    rows = []
    for r in R:
        z = np.load(os.path.join(HERE, 'wave', '%s_%s_%s_%s.npz' % (r['net'].replace('#', 'N'), r['scenario'], r['corner'], r['stack'])))
        t = z['t']
        for node in ('rx_die', 'rx_pin'):
            v = z[node]
            if r['scenario'] == 'read':
                for ui in (7.5, 10.0):
                    worst = 0.0
                    detail = None
                    for w in windows(t, v, r['rail']):
                        for kind, peak, dur, tab in (('over', w['peak_over'], w['t_over_ns'], OVER), ('under', w['peak_under'], w['t_under_ns'], UNDER)):
                            if peak <= 0.20:
                                continue
                            used = dur / ui * 100
                            lim = allowed(tab, peak)
                            ratio = used / lim if lim > 0 else float('inf')
                            if ratio > worst:
                                worst, detail = ratio, (kind, peak, dur, used, lim)
                    rows.append({'net': r['net'], 'scenario': 'read', 'corner': r['corner'], 'stack': r['stack'], 'node': node,
                                 'ui_ns': ui, 'usage_ratio': worst, 'detail': detail})
            else:
                vmax, vmin = float(v.max()), float(v.min())
                rows.append({'net': r['net'], 'scenario': 'write', 'corner': r['corner'], 'stack': r['stack'], 'node': node,
                             'vmax': vmax, 'vmin': vmin, 'pass': vmax <= 4.6 and vmin >= -1.0})
    json.dump(rows, open(os.path.join(HERE, 'compliance.json'), 'w'), indent=1)
    for stack in ('fab', 'pcbdoc'):
        for corner in ('typ', 'max'):
            for node in ('rx_die', 'rx_pin'):
                for ui in (7.5, 10.0):
                    g = [x for x in rows if x['scenario'] == 'read' and x['stack'] == stack and x['corner'] == corner and x['node'] == node and x['ui_ns'] == ui]
                    w = max(g, key=lambda x: x['usage_ratio'])
                    fails = [x['net'] for x in g if x['usage_ratio'] > 1]
                    d = w['detail']
                    print('READ  %-6s %-3s %-6s UI %4.1f ns: worst %-4s %s peak %.3f V beyond rail/GND, %.3f ns beyond 0.20 V = %.2f %% of UI vs %.2f %% allowed (%.0f %% of budget)  fails: %s' % (
                        stack, corner, node, ui, w['net'], d[0], d[1], d[2], d[3], d[4], 100 * w['usage_ratio'], ', '.join(fails) or 'none'))
            for node in ('rx_die', 'rx_pin'):
                g = [x for x in rows if x['scenario'] == 'write' and x['stack'] == stack and x['corner'] == corner and x['node'] == node]
                print('WRITE %-6s %-3s %-6s: Vmax %.3f V, Vmin %.3f V (limit 4.6 / -1.0 V for <= 3 ns): %s' % (
                    stack, corner, node, max(x['vmax'] for x in g), min(x['vmin'] for x in g), 'PASS' if all(x['pass'] for x in g) else 'FAIL'))


if __name__ == '__main__':
    main()
