"""Second, independent checker: si/series_r/judge_check.py (imported, not edited) run on this folder's plan.json and,
for calibration, on dq_series_r_plan.json.  Writes judge_d10.log/.json here."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, SR)
sys.argv = sys.argv[:1]
import judge_check as J
os.environ['D10_PLAN'] = os.path.join(HERE, 'plan.json')
import bus_sim_placed_d10 as S
boxes = J.comp_boxes()
out = {}
for name, path in (('base12 (dq_series_r_plan.json)', os.path.join(SR, 'dq_series_r_plan.json')), ('d10_elsewhere plan.json', os.path.join(HERE, 'plan.json'))):
    S.PLANFILE = path
    E = S.final_edits(None)
    for t in E['add_tracks']:
        t['layer'] = J.LN[t['layer']]
    for t in E['remove_tracks']:
        t['layer'] = J.LN[t['layer']]
    out[name] = J.run(name, E, boxes)
json.dump(out, open(os.path.join(HERE, 'judge_d10.json'), 'w'), indent=1, default=str)
open(os.path.join(HERE, 'judge_d10.log'), 'w').write('\n'.join(J.LOG) + '\n')
