"""make_sim.py -- builds bus_sim_final.py from ../judge/bus_sim_judge.py by exact, asserted string replacements."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, '..', 'judge', 'bus_sim_judge.py'), encoding='utf-8').read()
R = [
 ('"""[d10/judge/bus_sim_judge.py:',
  '"""[d10/sim/bus_sim_final.py: made by make_sim.py from d10/judge/bus_sim_judge.py. Changes, all marked FINAL: plan path '
  'per task (--plan, default ../final_plan.json; md5 recorded per row); outputs sim_final_raw_<tag>.json + wave_final/; '
  'placed mode runs nets WITHOUT an R in the plan on the plan-applied copper (mode tag stays placed, ref None) so the '
  'whole bus is simulated as planned.]\n[was d10/judge/bus_sim_judge.py:'),
 ("WAVE = os.path.join(HERE, 'wave_judge')", "WAVE = os.path.join(HERE, 'wave_final')                       # FINAL"),
 ("PLAN = os.environ.get('ZULU_PLAN', os.path.join(HERE, 'plan.json'))",
  "PLAN = os.environ.get('ZULU_PLAN', os.path.join(os.path.dirname(HERE), 'final_plan.json'))   # FINAL default; per task below"),
 ("""    global STACK
    net, scen""", """    global STACK, PLAN
    if task.get('plan'):                                             # FINAL: plan per task
        PLAN = task['plan']
    net, scen"""),
 ("""            E = final_edits(net)
            if net not in E['parts']:
                raise RuntimeError('%s has no R in the plan' % net)
            part = E['parts'][net]
            PLACED.update(split=True, r=r, pkg=PKG[pkgname], rref=part['ref'])
            key['ref'] = part['ref']
            key['r_side'] = part['side']
            key['r_xy'] = [part['x'], part['y']]
            M = extract_model(E)""",
  """            import hashlib
            E = final_edits(net)
            key['plan'] = os.path.relpath(PLAN, SR).replace(os.sep, '/')            # FINAL
            key['plan_md5'] = hashlib.md5(open(PLAN, 'rb').read()).hexdigest()
            if net in E['parts']:
                part = E['parts'][net]
                PLACED.update(split=True, r=r, pkg=PKG[pkgname], rref=part['ref'])
                key['ref'] = part['ref']
                key['r_side'] = part['side']
                key['r_xy'] = [part['x'], part['y']]
            else:                                                    # FINAL: no R -> plan copper, unsplit
                key['ref'] = None
            M = extract_model(E)"""),
 ("key['wave'] = 'wave_judge/' + wf", "key['wave'] = 'wave_final/' + wf"),
 ("""    tag = opt('--tag', mode)""", """    tag = opt('--tag', mode)
    plan = os.path.abspath(opt('--plan', PLAN))                      # FINAL"""),
 ("""tasks = [dict(net=n, scen=sc, corner=c, stack=st, mode=mode, r=r, pkg=p, src=src)""",
  """tasks = [dict(net=n, scen=sc, corner=c, stack=st, mode=mode, r=r, pkg=p, src=src, plan=plan)"""),
 ("""    wf = '%s_%s_%s_%s_%s_r%g_%s_%s.npz' % (net, scen, corner, stack, mode, r, pkgname, src)""",
  """    wf = '%s_%s_%s_%s_%s_r%g_%s_%s%s.npz' % (net, scen, corner, stack, mode, r, pkgname, src,
                                            ('_' + key['plan_md5'][:8]) if 'plan_md5' in key else '')   # FINAL"""),
 ("'sim_judge_raw_%s.json' % tag", "'sim_final_raw_%s.json' % tag"),
]
for a, b in R:
    assert src.count(a) == 1, a[:60]
    src = src.replace(a, b)
open(os.path.join(HERE, 'bus_sim_final.py'), 'w', encoding='utf-8', newline='\n').write(src)
print('ok')
