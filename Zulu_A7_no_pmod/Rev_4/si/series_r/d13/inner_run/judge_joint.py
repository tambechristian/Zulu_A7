"""Second, independent checker: the unchanged ../../judge_check.py via ../../d10/judge/judge_run.py plan_from_json
(both imported read-only) on plan.json and on the 13-R base.  -> judge_joint.log / .json here."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(SR, 'd10', 'judge'))
sys.path.insert(0, SR)
sys.argv = [sys.argv[0]]
sys.dont_write_bytecode = True
import judge_run as JR  # noqa: E402
J = JR.J
boxes = J.comp_boxes()
out = {}
for name, path in [('inner_run plan.json', os.path.join(HERE, 'plan.json')), ('13-R base', os.path.join(HERE, 'base_plan_13.json'))]:
    r = J.run(name, JR.plan_from_json(path), boxes)
    out[name] = dict(errors=r['errors'], violations=r['violations'], worst=r['worst'],
                     bad_connectivity={n: c for n, c in r['connectivity'].items() if c['islands'] != 1 or c['antennae']},
                     n_nets=len(r['connectivity']), component=r['component'], counts=r['counts'])
    print(name, 'errors', len(r['errors']), 'violations', len(r['violations']), 'bad_conn', len(out[name]['bad_connectivity']), 'nets', out[name]['n_nets'])
json.dump(out, open(os.path.join(HERE, 'judge_joint.json'), 'w'), indent=1, default=str)
open(os.path.join(HERE, 'judge_joint.log'), 'w').write('\n'.join(J.LOG) + '\n')
