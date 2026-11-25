"""Write the combined plan and prove it with check.py (byte copy of d10/fold/check.py in this folder).

final  = 13-R plan + gnd47 (u3_end unlock) + R132 (u3_end D13_XF-Top_gnd47_38.75_16.3_r180, nudged dy=+0.0035)
         + R133 (u1_end D14_F4_45p600_17p150_0) + R134 (u1_end D15_F4_46p800_16p800_0)
alt0   = the same with R132 exactly as the u3_end candidate (no nudge)
usage: python combine.py   -> ../final_plan.json, plan_alt0.json, check_final.*, check_alt0.*
"""
import json, os, sys, subprocess
import lib
from r132_nudge import nudge

D14_ID = 'D14_F4_45p600_17p150_0'
D15_ID = 'D15_F4_46p800_16p800_0'
D13_ID = 'D13_XF-Top_gnd47_38.75_16.3_r180'
DY = 0.0035


def build(dy):
    pools, unl = lib.load_pools()
    base = lib.load_base()
    r132 = [c for c in pools['D13'] if c['id'].endswith(':' + D13_ID)][0]
    a = [c for c in pools['D14'] if c['id'].endswith(':' + D14_ID)][0]
    b = [c for c in pools['D15'] if c['id'].endswith(':' + D15_ID)][0]
    pr = r132['delta']['parts'][0]
    pts = [(pr['pad1']['x'], pr['pad1']['y']), (pr['pad2']['x'], pr['pad2']['y'])]
    d13 = nudge(lib.polish(r132['delta']), 0.0, dy, pts) if dy else lib.polish(r132['delta'])
    note = ('gnd47 unlock (u3_end) + R132 D13 u3_end %s%s + R133 D14 u1_end %s + R134 D15 u1_end %s; strategy combine'
            % (D13_ID, (' nudged dy=%+.4f' % dy) if dy else '', D14_ID, D15_ID))
    P, errs = lib.merge(base, [unl['gnd47'], d13, lib.polish(a['delta']), lib.polish(b['delta'])], note)
    assert not errs, errs
    P['source']['components'] = dict(gnd47=unl['gnd47'], R132=d13, R133=lib.polish(a['delta']), R134=lib.polish(b['delta']))
    return P


def prove(path, tag):
    r = subprocess.run([sys.executable, os.path.join(lib.HERE, 'check.py'), '--plan', path, '--tag', tag], cwd=lib.HERE,
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    if r.returncode:
        print(r.stderr[-3000:])
    return r.returncode


def main():
    fin = os.path.join(lib.D13, 'final_plan.json')
    alt = os.path.join(lib.HERE, 'plan_alt0.json')
    for P, pth in ((build(DY), fin), (build(0.0), alt)):
        comp = P['source'].pop('components')
        json.dump(P, open(pth, 'w', newline='\n'), indent=1)
        json.dump(comp, open(pth.replace('.json', '_components.json') if pth != fin else os.path.join(lib.HERE, 'final_plan_components.json'), 'w'), indent=1)
        print(pth, lib.md5(pth))
    print('check final', prove(fin, 'final'))
    print('check alt0', prove(alt, 'alt0'))


if __name__ == '__main__':
    main()
