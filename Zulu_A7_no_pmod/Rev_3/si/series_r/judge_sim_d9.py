"""judge_sim_d9.py -- read-direction SI of the judge-added D9 resistor (Bottom 0201 under D9's L4 route near U1).

Re-uses design_top_sim.run_case unchanged except that the R's two pseudo-pads sit on the BOTTOM layer (design_top_sim
puts them on Top), so the L4>L5>Bottom microvia columns land on them.  bus_sim.simulate() itself is untouched.
Writes judge_sim_d9.json in this folder only.   python judge_sim_d9.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PLAN = {'placements': {'D9': {
    'remove_tracks': [{'layer': 'L4-SIG', 'x1': 41.75, 'y1': 13.275, 'x2': 42.425, 'y2': 12.6}],
    'add_tracks': [{'layer': 'L4-SIG', 'w': 0.125, 'x1': 41.75, 'y1': 13.275, 'x2': 41.75, 'y2': 12.95},
                   {'layer': 'L4-SIG', 'w': 0.125, 'x1': 42.35, 'y1': 12.95, 'x2': 42.425, 'y2': 12.6}],
    'add_vias': [{'x': x, 'y': 12.95, 'size': 0.30, 'hole': 0.15, 'span': s}
                 for x in (41.75, 42.35) for s in (['L4-SIG', 'L5-VCC3V3'], ['L5-VCC3V3', 'Bottom'])],
    'pad_A': [41.75, 12.95], 'pad_B': [42.35, 12.95], 'center': [42.05, 12.95]}}}
PLAN_FILE = os.path.join(HERE, 'judge_sim_d9_plan.json')


def run(task):
    import design_top_sim as T

    def model_plan_bottom(M, net, P):
        info = T.__dict__['_orig_model_plan'](M, net, P)
        for p in M['pads']:
            if p['ref'] == 'RSER':
                p['layers'] = ['Bottom Layer']
        return info
    if '_orig_model_plan' not in T.__dict__:
        T._orig_model_plan = T.model_plan
        T.model_plan = model_plan_bottom
    return T.run_case(task)


if __name__ == '__main__':
    import multiprocessing as mp
    json.dump(PLAN, open(PLAN_FILE, 'w'), indent=1)
    tasks = [('plan', 'D9', c, PLAN_FILE, v, sc) for sc in ('read', 'write') for c in ('typ', 'max') for v in ('ideal', '0201')]
    out = []
    with mp.Pool(4, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(run, tasks):
            out.append(r)
            print(json.dumps({k: r.get(k) for k in ('net', 'scenario', 'corner', 'variant', 'connected', 'len_mm', 'vias',
                                                       'ball_vmin', 'ball_vmax', 'ball_budget', 'die_vmin', 'die_budget', 'error')}), flush=True)
    json.dump(out, open(os.path.join(HERE, 'judge_sim_d9.json'), 'w'), indent=1)
