"""Build the 15-resistor plan (D0-D12 + D14 + D15, D13 left without a resistor).

plan15 = 16-R plan minus every delta item (d13/combine/delta_report.json) that belongs to
D13 / SDRAM-D13 / the gnd47 GND re-tie, minus R132, U3-50's renet, SDRAM-D13's class add,
the U1 designator move and the R132-2 VIPPO entry.  Asserts plan15 == 13-R plan + D14/D15 delta.
"""
import json, hashlib, sys
HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
R = '../..'
p16 = json.load(open(f'{R}/dq_series_r_plan_16.json'))  # archived 16-R plan
p13 = json.load(open(f'{R}/dq_series_r_plan_13.json'))
dl = json.load(open('../combine/delta_report.json'))
assert hashlib.md5(open(f'{R}/dq_series_r_plan_16.json','rb').read()).hexdigest().startswith('7c2b8ae6')
DROP = {'D13', 'SDRAM-D13', 'GND'}
k = lambda x: json.dumps(x, sort_keys=True)
def strip(x):
    return {a: b for a, b in x.items() if a != 'why'}
out = {}
report = {}
for key, val in p16.items():
    if key == 'net_class_add':
        out[key] = {c: [n for n in ns if n != 'SDRAM-D13'] for c, ns in val.items()}; continue
    if key == 'renamed_existing':
        # count renames left: drop the D13 rename track (1) and via (1)
        rt = sum(1 for x in dl['remove'] if x.get('why') == 'rename' and x.get('net') in DROP)
        rv = sum(1 for x in dl['remove_vias'] if x.get('why') == 'rename' and x.get('net') in DROP)
        out[key] = {'tracks': val['tracks'] - rt, 'vias': val['vias'] - rv}; continue
    if not isinstance(val, list):
        out[key] = val; continue
    if key == 'parts':
        out[key] = [x for x in val if x['ref'] != 'R132']
    elif key == 'renet_pads':
        out[key] = [x for x in val if not (x['ref'] == 'U3' and str(x['pad']) == '50')]
    elif key == 'net_class_add':
        out[key] = [x for x in val if 'SDRAM-D13' not in json.dumps(x)] if val and isinstance(val[0], dict) else [x for x in val if x != 'SDRAM-D13']
    elif key == 'designator_moves':
        out[key] = []
    elif key == 'vippo':
        out[key] = [x for x in val if 'R132' not in json.dumps(x)]
    else:
        drop = {k(x) for x in dl.get(key, []) if x.get('net') in DROP}
        drop |= {k(strip(x)) for x in dl.get(key, []) if x.get('net') in DROP}
        out[key] = [x for x in val if k(x) not in drop and k(strip(x)) not in drop]
    report[key] = (len(p13.get(key, [])), len(out[key]), len(val))
out['source'] = 'fallback15: 16-R plan (md5 7c2b8ae6) minus R132/D13/gnd47; D13 has no resistor (user decision 2026-11-13)'
# assertion: plan15 == plan13 + D14/D15 delta
for key, val in out.items():
    if not isinstance(val, list) or key in ('designator_moves',):
        continue
    A = {k(x) for x in val}; B = {k(x) for x in p13.get(key, [])}
    extra = [json.loads(x) for x in A - B]; missing = [json.loads(x) for x in B - A]
    bad = [e for e in extra if 'D13' in json.dumps(e) or ('GND' in json.dumps(e) and key not in ('vippo',))]
    if missing or bad:
        print('ASSERT FAIL', key, 'missing', missing[:3], 'bad', bad[:3]); sys.exit(1)
    report[key] = report[key] + (len(extra),)
s = json.dumps(out, indent=1, sort_keys=True)
open('plan15.json', 'w', newline='\n').write(s + '\n')
print(json.dumps(report))
print('md5', hashlib.md5(open('plan15.json', 'rb').read()).hexdigest())
