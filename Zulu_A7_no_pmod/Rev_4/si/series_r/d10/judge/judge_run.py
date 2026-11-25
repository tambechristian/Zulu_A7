"""Second, independent checker pass: feed each emit_copper-format plan JSON to ../../judge_check.py (imported
read-only; its own run()/check()/connectivity()/comp_check()/plane_webs() do the work).  Renames are applied as the
plan writes them (remove on Dn + re-add on SDRAM-Dn).

Usage: python judge_run.py   -> judge_run.log / judge_run.json in this folder
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, SR)
sys.argv = [sys.argv[0]]
import judge_check as J  # noqa: E402

CU = J.CU
LN = J.LN


def plan_from_json(path):
    P = json.load(open(path))
    E = dict(remove_tracks=[], add_tracks=[], remove_vias=[], add_vias=[], renet_pads=[], add_pads=[],
             rename_tracks=[], rename_vias=[], parts={})
    for t in P['remove']:
        E['remove_tracks'].append(dict(t, layer=LN[t['layer']]))
    for t in P['tracks']:
        E['add_tracks'].append(dict(t, layer=LN[t['layer']]))
    for v in P['remove_vias']:
        a, b = CU.index(LN[v['span'][0]]), CU.index(LN[v['span'][-1]])
        E['remove_vias'].append(dict(v, span=CU[a:b + 1]))
    for v in P['vias']:
        a, b = sorted((CU.index(LN[v['from']]), CU.index(LN[v['to']])))
        kind = 'through' if b - a == 5 else 'micro'
        E['add_vias'].append(dict(v, span=CU[a:b + 1], kind=kind))
    E['renet_pads'] = [dict(p) for p in P['renet_pads']]
    for pr in P['parts']:
        p1 = (pr['pad1']['x'], pr['pad1']['y'])
        p2 = (pr['pad2']['x'], pr['pad2']['y'])
        E['add_pads'] += J.r0201_pads(pr['ref'], p1, p2, pr['side'], pr['pad1']['net'], pr['pad2']['net'])
        E['parts']['D%d' % pr['net_bit']] = dict(ref=pr['ref'], side=pr['side'], x=pr['x'], y=pr['y'], rot=pr['rot'], p1=p1, p2=p2)
    return E


if __name__ == '__main__':
    boxes = J.comp_boxes()
    plans = [('base12 (dq_series_r_plan.json)', os.path.join(SR, 'dq_series_r_plan.json')),
             ('stagger', os.path.join(SR, 'd10', 'stagger', 'plan.json')),
             ('relocate', os.path.join(SR, 'd10', 'relocate', 'plan.json')),
             ('d10_elsewhere', os.path.join(SR, 'd10', 'd10_elsewhere', 'plan.json'))]
    out = {}
    for name, path in plans:
        r = J.run(name, plan_from_json(path), boxes)
        out[name] = dict(errors=r['errors'], violations=r['violations'], worst=r['worst'],
                         bad_connectivity={n: c for n, c in r['connectivity'].items() if c['islands'] != 1 or c['antennae']},
                         n_nets=len(r['connectivity']), component=r['component'], other_nets=r['other_nets'], counts=r['counts'])
    json.dump(out, open(os.path.join(HERE, 'judge_run.json'), 'w'), indent=1, default=str)
    open(os.path.join(HERE, 'judge_run.log'), 'w').write('\n'.join(J.LOG) + '\n')
