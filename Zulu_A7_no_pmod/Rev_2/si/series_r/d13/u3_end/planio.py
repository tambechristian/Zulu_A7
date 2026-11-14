import json, copy, os, subprocess, sys
import base
HERE = base.HERE

def merge(recs, base_plan=base.PLAN13, note=''):
    P = json.load(open(base_plan))
    P = copy.deepcopy(P)
    for r in recs:
        for k in ('remove', 'remove_vias', 'tracks', 'vias', 'parts', 'renet_pads', 'microvias'):
            P[k] += copy.deepcopy(r.get(k, []))
        for p in r.get('parts', []):
            nm = 'SDRAM-D%d' % p['net_bit']
            if nm not in P['net_class_add']['SDRAM_DATA']:
                P['net_class_add']['SDRAM_DATA'].append(nm)
    P['source'] = dict(P['source'])
    P['source']['plan'] = (P['source'].get('plan', '') + ' + ' + note) if note else P['source'].get('plan', '')
    P['source']['generated_by'] = 'si/series_r/d13/u3_end'
    return P

def write(P, path):
    json.dump(P, open(path, 'w', newline='\n'), indent=1)

def run_check(plan_path, tag):
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), '--plan', plan_path, '--tag', tag], capture_output=True, text=True, cwd=HERE)
    j = json.load(open(os.path.join(HERE, 'check_%s.json' % tag)))
    return summarize(j)

def summarize(j):
    s = {}
    s['apply_errors'] = len(j['apply_errors'])
    s['split_ok'] = all(v['ok'] for v in j['split'].values())
    s['split_notes'] = {k: v['notes'] for k, v in j['split'].items() if not v['ok']}
    s['new_shorts'] = len(j['shorts']['new'])
    s['planes'] = {L: (v['live_islands_after'], len(v['objects_off_main_after']) - len(v['objects_off_main_before'])) for L, v in j['planes'].items()}
    s['islands_worse'] = j['net_islands']['worse']
    s['sdram_new_islands'] = j['net_islands']['sdram_new']
    s['antennae'] = len(j['antennae'])
    s['clearance_viol'] = len(j['clearance']['violations'])
    s['h2h_viol'] = len(j['hole_to_hole']['violations'])
    s['width_viol'] = len(j['width'])
    s['mask_viol'] = len(j['mask']['violations'])
    s['pass'] = (s['apply_errors'] == 0 and s['split_ok'] and s['new_shorts'] == 0 and not s['islands_worse'] and s['antennae'] == 0
                 and s['clearance_viol'] == 0 and s['h2h_viol'] == 0 and s['width_viol'] == 0 and s['mask_viol'] == 0
                 and all(v[0] == 1 and v[1] <= 0 for v in s['planes'].values()))
    return s
