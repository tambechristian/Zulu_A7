"""doc15_numbers.py -- the numbers docs/dq_series_resistors.md quotes for the 15-R fallback plan (plan15.json).

Read only.  Sources: d13/sim/sim_final.json (16-R study: per_net rows at 22 ohm and the 15/33 ohm sweep; D0-D12, D14,
D15 waves are bit-identical in fallback15/sim, see report15.log) and fallback15/sim/sim_fb15.json (D13 with no R).
The 15 nets with a resistor are taken from the 16-R rows; D13 is taken from sim_fb15 (no R, today's copper).
Writes doc15_numbers.json + prints a summary.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D13 = os.path.dirname(HERE)
S16 = json.load(open(os.path.join(D13, 'sim', 'sim_final.json')))
FB = json.load(open(os.path.join(HERE, 'sim', 'sim_fb15.json')))
assert FB['plan_md5'] == '187b8703833e9d785fd62c91d044bdf8' and FB['identity_all_zero'] and FB['errors'] == 0
RN = [r for r in S16['per_net'] if r['net'] != 'D13']
D13R = [r for r in FB['rows'] if r['net'] == 'D13']
assert len(RN) == 60 and len(D13R) == 4


def summ(g):
    wb = max(g, key=lambda r: (r['read']['ball_budget_pct'], -r['read']['ball_vmin']))
    wd = max(g, key=lambda r: (r['read']['die_budget_pct'], -r['read']['die_vmin']))
    vm = min(g, key=lambda r: r['read']['ball_vmin'])
    out = dict(n=len(g), ball=wb['read']['ball_budget_pct'], ball_net=wb['net'], die=wd['read']['die_budget_pct'],
               die_net=wd['net'], vmin=vm['read']['ball_vmin'], vmin_net=vm['net'],
               ringback=max(max(r['read']['ringback_ball_v'], r['read']['ringback_die_v']) for r in g),
               w_pin=[min(r['write']['u3pin_vmin'] for r in g), max(r['write']['u3pin_vmax'] for r in g)],
               w_die=[min(r['write']['u3die_vmin'] for r in g), max(r['write']['u3die_vmax'] for r in g)],
               w_pin_vmin_net=min(g, key=lambda r: r['write']['u3pin_vmin'])['net'],
               w_pin_vmax_net=max(g, key=lambda r: r['write']['u3pin_vmax'])['net'],
               w_die_vmin_net=min(g, key=lambda r: r['write']['u3die_vmin'])['net'],
               w_die_vmax_net=max(g, key=lambda r: r['write']['u3die_vmax'])['net'],
               absmax=all(r['write']['absmax_pass'] for r in g),
               rd=[min(r['read']['delay_die_ns'][0] for r in g), max(r['read']['delay_die_ns'][1] for r in g)],
               wd=[min(r['write']['delay_die_ns'][0] for r in g), max(r['write']['delay_die_ns'][1] for r in g)])
    t = [r['read'].get('t10_90_die_ns') for r in g if r['read'].get('t10_90_die_ns') is not None]
    if t:
        out['t10_90'] = [min(t), max(t)]
    return out


OUT = dict(with_R={}, whole_bus={}, d13={})
for st in ('fab', 'pcbdoc'):
    for c in ('typ', 'max'):
        k = '%s|%s' % (st, c)
        g = [r for r in RN if r['stack'] == st and r['corner'] == c]
        OUT['with_R'][k] = summ(g)
        d = [r for r in D13R if r['stack'] == st and r['corner'] == c][0]
        OUT['d13'][k] = dict(ball=d['read']['ball_budget_pct'], die=d['read']['die_budget_pct'],
                             vmin=d['read']['ball_vmin'], detail=d['read']['ball_budget_detail'],
                             w_pin=[d['write']['u3pin_vmin'], d['write']['u3pin_vmax']],
                             w_die=[d['write']['u3die_vmin'], d['write']['u3die_vmax']],
                             t10_90=d['read'].get('t10_90_die_ns'))
        # whole bus: writes and ringback over all 16 nets (D13 without R)
        wb = summ(g + [d])
        OUT['whole_bus'][k] = dict(w_pin=wb['w_pin'], w_die=wb['w_die'], w_pin_vmin_net=wb['w_pin_vmin_net'],
                                   w_pin_vmax_net=wb['w_pin_vmax_net'], w_die_vmin_net=wb['w_die_vmin_net'],
                                   w_die_vmax_net=wb['w_die_vmax_net'], ringback=wb['ringback'], absmax=wb['absmax'])
allr = summ(RN)
OUT['all_with_R'] = dict(rd=allr['rd'], wd=allr['wd'], w_pin=allr['w_pin'], w_die=allr['w_die'],
                         w_pin_net=(allr['w_pin_vmin_net'], allr['w_pin_vmax_net']),
                         w_die_net=(allr['w_die_vmin_net'], allr['w_die_vmax_net']))
per = {}
for r in RN:
    p = per.setdefault(r['net'], dict(rd=[9, -9], wd=[9, -9]))
    p['rd'] = [min(p['rd'][0], r['read']['delay_die_ns'][0]), max(p['rd'][1], r['read']['delay_die_ns'][1])]
    p['wd'] = [min(p['wd'][0], r['write']['delay_die_ns'][0]), max(p['wd'][1], r['write']['delay_die_ns'][1])]
OUT['delay_per_net'] = per
OUT['slowest_read'] = max(per, key=lambda n: per[n]['rd'][1])
OUT['slowest_write'] = max(per, key=lambda n: per[n]['wd'][1])
# sweep on the PcbDoc stack, without D13 (it has no R in plan15)
sw = {}
for rv in (15.0, 22.0, 33.0):
    g = [r for r in S16['sweep'] if r['r_ohm'] == rv and r['net'] != 'D13']
    s = summ(g)
    sw[str(rv)] = dict(nets=sorted({r['net'] for r in g}, key=lambda n: int(n[1:])), n=len(g), ball=s['ball'],
                       ball_net=s['ball_net'], die=s['die'], vmin=s['vmin'], vmin_net=s['vmin_net'],
                       rb_ball=max(r['read']['ringback_ball_v'] for r in g),
                       rb_ball_net=max(g, key=lambda r: r['read']['ringback_ball_v'])['net'],
                       t10_90=s.get('t10_90'), rd=s['rd'], wd=s['wd'])
OUT['sweep_noD13'] = sw
# the 16-R sweep with D13 (to show what changed)
sw16 = {}
for rv in (15.0, 22.0, 33.0):
    g = [r for r in S16['sweep'] if r['r_ohm'] == rv]
    s = summ(g)
    sw16[str(rv)] = dict(n=len(g), ball=s['ball'], die=s['die'], vmin=s['vmin'], t10_90=s.get('t10_90'),
                         rd=s['rd'], wd=s['wd'])
OUT['sweep_16R'] = sw16
json.dump(OUT, open(os.path.join(HERE, 'doc15_numbers.json'), 'w', newline='\n'), indent=1)
print(json.dumps(OUT, indent=1))
