"""repro_cmp.py -- compare d10/sim reproduction runs with si/series_r/sim_placed_raw_*.json (same evaluate(), waveforms)."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.dirname(os.path.dirname(HERE))
ref = json.load(open(os.path.join(SR, 'sim_placed_raw_placed_fab.json'))) + json.load(open(os.path.join(SR, 'sim_placed_raw_base_fab.json')))
out = []
for tag in sys.argv[1:]:
    for m in json.load(open(os.path.join(HERE, 'sim_final_raw_%s.json' % tag))):
        g = [r for r in ref if 'error' not in r and r['net'] == m['net'] and r['scenario'] == m['scenario'] and r['corner'] == m['corner']
             and r['stack'] == m['stack'] and r['mode'] == m['mode'] and r['r'] == m['r'] and r['pkg'] == m['pkg']]
        if len(g) != 1:
            print('no ref', m['net'], m['scenario'], m['corner'], m['mode']); continue
        g = g[0]
        za = np.load(os.path.join(HERE, m['wave'])); zb = np.load(os.path.join(SR, g['wave']))
        same_t = len(za['t']) == len(zb['t']) and np.allclose(za['t'], zb['t'])
        dv = {k: float(np.max(np.abs(za[k] - zb[k]))) if same_t else None for k in ('rx_pin', 'rx_die', 'tx_die')}
        row = dict(tag=tag, net=m['net'], scenario=m['scenario'], corner=m['corner'], mode=m['mode'], plan=m.get('plan'),
                   len_mm=(m['len_mm'], g['len_mm']), vias=(m['vias'], g['vias']), feed_mm=(m.get('feed_mm'), g.get('feed_mm')),
                   pin_vmin=(round(m['pin']['vmin'], 4), round(g['pin']['vmin'], 4)), pin_vmax=(round(m['pin']['vmax'], 4), round(g['pin']['vmax'], 4)),
                   budget=(m['pin'].get('budget'), g['pin'].get('budget')), max_abs_dv=dv, same_timebase=same_t)
        out.append(row)
        print(json.dumps(row))
json.dump(out, open(os.path.join(HERE, 'repro_cmp.json'), 'w'), indent=1)
