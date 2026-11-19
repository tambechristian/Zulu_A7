"""Second checker on the fixed plan: the unchanged ../../judge_check.py via ../../d10/judge/judge_run.py plan_from_json
(both imported read-only, no bytecode written), as d13/combine/judge_final.py did.  -> judge_p15.log / .json here."""
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
r = J.run('plan15.json', JR.plan_from_json(os.path.join(HERE, 'plan15.json')), boxes)
out = dict(errors=r['errors'], violations=r['violations'], worst=r['worst'],
           bad_connectivity={n: c for n, c in r['connectivity'].items() if c['islands'] != 1 or c['antennae']},
           n_nets=len(r['connectivity']), component=r['component'], counts=r['counts'])
print('plan15.json errors', len(r['errors']), 'violations', len(r['violations']), 'bad_conn', len(out['bad_connectivity']), 'nets', out['n_nets'])
json.dump(out, open(os.path.join(HERE, 'judge_p15.json'), 'w'), indent=1, default=str)
open(os.path.join(HERE, 'judge_p15.log'), 'w').write('\n'.join(J.LOG) + '\n')
