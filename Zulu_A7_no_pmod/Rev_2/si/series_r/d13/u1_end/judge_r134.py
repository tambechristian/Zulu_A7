"""the judge's optional R134 (D15) from design_top.json placements['D15'], re-expressed as a plan delta against the
13-R plan.  Writes judge_r134_delta.json (list with one delta) and runs check.py on it via fullcheck."""
import json, os
import engine as E
import build as Bd
HERE = E.HERE
d = json.load(open(os.path.join(E.ulib.SR, 'design_top.json')))['placements']['D15']
SN, DN = 'SDRAM-D15', 'D15'
delta = dict(remove=[], remove_vias=[], tracks=[], vias=[], parts=[], renet_pads=[], microvias=[])
for t in d['remove_tracks']:
    delta['remove'].append(dict(net=t['net'], layer=E.EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
for t in d['add_tracks']:
    delta['tracks'].append(dict(net=t['net'], layer=E.EMIT[t['layer']], w=t['w'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2']))
for v in d['add_vias']:
    vv = dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], **{'from': E.EMIT[v['span'][0]], 'to': E.EMIT[v['span'][-1]]})
    delta['vias'].append(vv)
    delta['microvias'].append(dict(vv, type='microvia 0.30/0.15' if v['size'] >= 0.29 else 'buried 0.27/0.15'))
for t in d['renamed_to_SDRAM']['tracks']:
    rec = [r for r in E.TRACKS if r['net'] == DN and r['layer'] == t['layer'] and E.same((r['x1'], r['y1']), (t['x1'], t['y1'])) and E.same((r['x2'], r['y2']), (t['x2'], t['y2']))][0]
    delta['remove'].append(dict(net=DN, layer=E.EMIT[rec['layer']], w=rec['w'], x1=rec['x1'], y1=rec['y1'], x2=rec['x2'], y2=rec['y2'], why='rename'))
    delta['tracks'].append(dict(net=SN, layer=E.EMIT[rec['layer']], w=rec['w'], x1=rec['x1'], y1=rec['y1'], x2=rec['x2'], y2=rec['y2'], why='rename'))
for v in d['renamed_to_SDRAM']['vias']:
    rec = [r for r in E.VIAS if r['net'] == DN and E.same((r['x'], r['y']), (v['x'], v['y']))][0]
    delta['remove_vias'].append(dict(net=DN, x=rec['x'], y=rec['y'], hole=rec['hole'], span=['Top', 'Bottom'], why='rename'))
    delta['vias'].append(dict(net=SN, x=rec['x'], y=rec['y'], size=rec['size'], hole=rec['hole'], **{'from': 'Top Layer', 'to': 'Bottom Layer'}, why='rename'))
delta['renet_pads'].append(dict(ref='U3', pad='53', net=SN))
delta['parts'].append(dict(ref='R134', net_bit=15, side='Top', footprint='R0201', comment='22', x=d['x'], y=d['y'], rot=d['rot'],
                           pad1=dict(net=SN, x=round(d['pad_A'][0], 4), y=d['pad_A'][1]), pad2=dict(net=DN, x=round(d['pad_B'][0], 4), y=d['pad_B'][1]),
                           designator_hidden=True))
json.dump([delta], open(os.path.join(HERE, 'judge_r134_delta.json'), 'w'), indent=1)
print(json.dumps(delta, indent=0)[:3000])
