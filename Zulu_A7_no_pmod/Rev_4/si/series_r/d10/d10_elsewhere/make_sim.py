"""Builds bus_sim_placed_d10.py from si/series_r/bus_sim_placed.py (not edited) by text substitution: PLACED mode
takes its copper from this folder's plan.json (dq_series_r_plan.json format: every edit of every net, so each net
is simulated on the complete 13-resistor board), D10 joins PLAN_NETS, outputs go to this folder."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.abspath(os.path.join(HERE, '..', '..'))
s = open(os.path.join(SR, 'bus_sim_placed.py')).read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:90]
    s = s.replace(old, new)


rep('"""bus_sim_placed.py -- COPY', '"""bus_sim_placed_d10.py -- built by d10/d10_elsewhere/make_sim.py from bus_sim_placed.py: PLACED mode reads\n'
    'the plan FILE (--plan, default plan.json in this folder) for every net; D10 (R129) is in PLAN_NETS; waves and results\n'
    'go to this folder.  Everything else is bus_sim_placed.py unchanged.\n\nbus_sim_placed.py -- COPY')
rep("HERE = os.path.dirname(os.path.abspath(__file__))\n",
    "OUTDIR = os.path.dirname(os.path.abspath(__file__))\nHERE = os.path.abspath(os.path.join(OUTDIR, '..', '..'))      # si/series_r\n")
rep("WAVE = os.path.join(HERE, 'wave_placed')", "WAVE = os.path.join(OUTDIR, 'wave_d10')")
rep("PLAN_NETS = ['D%d' % i for i in range(10)] + ['D11', 'D12']", "PLAN_NETS = ['D%d' % i for i in range(13)]")
rep('''def final_edits(net):
    """the judge's FINAL edit list (judge_check.py's own plan readers); + D15 only for the optional D15 case"""''',
    '''PLANFILE = os.environ.get('D10_PLAN', os.path.join(OUTDIR, 'plan.json'))
EMIT = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG',
        'L5-VCC3V3': 'L5-VCC3V3', 'Top': 'Top', 'Bottom': 'Bottom'}
CUL = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']


def _span(a, b):
    i, j = CUL.index(EMIT[a]), CUL.index(EMIT[b])
    return CUL[min(i, j):max(i, j) + 1]


def final_edits(net):
    """d10_elsewhere: the whole plan FILE as one edit list (judge_check.apply() order: remove, rename, renet, add)"""
    P = json.load(open(PLANFILE))
    E = dict(remove_tracks=[], add_tracks=[], remove_vias=[], add_vias=[], renet_pads=list(P['renet_pads']), add_pads=[],
             rename_tracks=[], rename_vias=[], parts={})
    for t in P['remove']:
        E['remove_tracks'].append(dict(layer=EMIT[t['layer']], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
    for v in P['remove_vias']:
        E['remove_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], span=_span(v['span'][0], v['span'][-1])))
    for t in P['tracks']:
        E['add_tracks'].append(dict(layer=EMIT[t['layer']], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], w=t['w']))
    for v in P['vias']:
        sp = _span(v['from'], v['to'])
        E['add_vias'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=sp,
                                  kind='through' if len(sp) == 6 else 'micro'))
    for pr in P['parts']:
        for k in ('1', '2'):
            pd = pr['pad' + k]
            E['add_pads'].append(dict(ref=pr['ref'], pad=k, layer=pr['side'], net=pd['net'], x=pd['x'], y=pd['y'], w=0.30,
                                      h=0.30, shape='rect', hole=0.0))
        E['parts']['D%d' % pr['net_bit']] = dict(ref=pr['ref'], side=pr['side'], x=pr['x'], y=pr['y'], rot=pr['rot'],
                                                 p1=(pr['pad1']['x'], pr['pad1']['y']), p2=(pr['pad2']['x'], pr['pad2']['y']))
    return E


def final_edits_judge(net):
    """the judge's FINAL edit list (judge_check.py's own plan readers); + D15 only for the optional D15 case"""''')
rep("json.dump(out, open(os.path.join(HERE, 'sim_placed_raw_%s.json' % tag), 'w'), indent=1)",
    "json.dump(out, open(os.path.join(OUTDIR, 'sim_d10_raw_%s.json' % tag), 'w'), indent=1)")
open(os.path.join(HERE, 'bus_sim_placed_d10.py'), 'w', newline='\n').write(s)
print('bus_sim_placed_d10.py written')
