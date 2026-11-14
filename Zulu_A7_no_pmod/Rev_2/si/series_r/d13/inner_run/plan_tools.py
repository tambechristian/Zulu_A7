"""Turn inner-run candidates into dq_series_r_plan.json-format deltas and full plans."""
import json, copy, os

HERE = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(HERE, '..', '..', 'board_extract.json')))
REF = {'D13': 'R132', 'D14': 'R133', 'D15': 'R134'}
BIT = {'D13': 13, 'D14': 14, 'D15': 15}
U3PAD = {'D13': '50', 'D14': '51', 'D15': '53'}
LO = {'Top': 'Top Layer', 'Bottom': 'Bottom Layer'}


def lo(L):
    return LO.get(L, L)


def r4(v):
    return round(float(v), 4)


def delta(c):
    """self-contained copper/part delta of one candidate against dq_series_r_plan.json (13-R plan)"""
    net = c['net']
    esc = B['d_escapes'][net]
    st = [e for e in esc['path'] if e['kind'] == 'track' and e['layer'] == 'Bottom'][0]
    fv = esc['first_via']
    sd = 'SDRAM-' + net
    D = dict(remove=[], remove_vias=[], tracks=[], vias=[], microvias=[])
    # rename: U3 stub + first through via
    D['remove'].append(dict(net=net, layer='Bottom Layer', w=st['w'], x1=st['x1'], y1=st['y1'], x2=st['x2'], y2=st['y2'], why='rename'))
    D['tracks'].append(dict(net=sd, layer='Bottom Layer', w=st['w'], x1=st['x1'], y1=st['y1'], x2=st['x2'], y2=st['y2'], why='rename'))
    D['remove_vias'].append(dict(net=net, x=fv['x'], y=fv['y'], hole=fv['hole'], span=['Top', 'Bottom'], why='rename'))
    D['vias'].append(dict(net=sd, x=fv['x'], y=fv['y'], size=fv['size'], hole=fv['hole'], frm='Top Layer', to='Bottom Layer', why='rename'))
    # removed run segments: renamed ones (before the cut) carry why=rename, the cut ones none
    renamed = {(round(a[2], 4), round(a[3], 4), round(a[4], 4), round(a[5], 4)) for a in c['add'] if a[7] == 'rename'}
    for t in c['rm']:
        key = (round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))
        e = dict(net=net, layer=lo(t['layer']), w=t['w'], x1=r4(t['x1']), y1=r4(t['y1']), x2=r4(t['x2']), y2=r4(t['y2']))
        if key in renamed:
            e['why'] = 'rename'
        D['remove'].append(e)
    for (L, nn, x1, y1, x2, y2, w, why) in c['add']:
        e = dict(net=nn, layer=lo(L), w=w, x1=r4(x1), y1=r4(y1), x2=r4(x2), y2=r4(y2))
        if why == 'rename':
            e['why'] = 'rename'
        D['tracks'].append(e)
    for v in c['cols']:
        D['vias'].append(dict(net=v['net'], x=r4(v['x']), y=r4(v['y']), size=v['size'], hole=0.15, frm=lo(v['frm']), to=lo(v['to'])))
        D['microvias'].append(dict(net=v['net'], x=r4(v['x']), y=r4(v['y']), size=v['size'], hole=0.15, frm=lo(v['frm']), to=lo(v['to']),
                                   type=('microvia 0.30/0.15' if v['size'] >= 0.29 else 'buried 0.27/0.15')))
    # emit_copper via format uses 'from'/'to'
    for k in ('vias', 'microvias'):
        for v in D[k]:
            v['from'] = v.pop('frm')
            v['to'] = v.pop('to')
    p1, p2 = c['pad1'], c['pad2']
    part = dict(ref=REF[net], net_bit=BIT[net], side=c['side'], footprint='R0201', comment='22', x=r4((p1[0] + p2[0]) / 2),
                y=r4((p1[1] + p2[1]) / 2), rot=c['rot'], pad1=dict(net=sd, x=r4(p1[0]), y=r4(p1[1])),
                pad2=dict(net=net, x=r4(p2[0]), y=r4(p2[1])), designator_hidden=True)
    D['parts'] = [part]
    D['renet_pads'] = [dict(ref='U3', pad=U3PAD[net], net=sd)]
    D['net_class_add'] = {'SDRAM_DATA': [sd]}
    return D


def merge(base, deltas, note=''):
    P = copy.deepcopy(base)
    for D in deltas:
        for k in ('remove', 'remove_vias', 'tracks', 'vias', 'microvias', 'parts', 'renet_pads'):
            P[k] = P[k] + copy.deepcopy(D[k])
        for cl, nets in D['net_class_add'].items():
            P['net_class_add'].setdefault(cl, [])
            P['net_class_add'][cl] = P['net_class_add'][cl] + [n for n in nets if n not in P['net_class_add'][cl]]
    P['renamed_existing'] = dict(tracks=sum(1 for t in P['tracks'] if t.get('why') == 'rename'),
                                 vias=sum(1 for v in P['vias'] if v.get('why') == 'rename'))
    P['source'] = dict(P['source'])
    P['source']['plan'] = (P['source'].get('plan', '') + ' + ' + note) if note else P['source'].get('plan', '')
    P['source']['generated_by'] = 'si/series_r/d13/inner_run/plan_tools.py'
    return P
