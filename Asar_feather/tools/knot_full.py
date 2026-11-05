"""A knot result as a plan for the FULL board model (2026-10-31): the knot's plan plus, in 'remove' and
'remove_vias', the copper net_seed.py moved out of the model (<dir>/dropped.json), so route_check.py, plan_open.py
and emit_copper.py can take it against tools/route/model.json and the board.

    python tools/knot_full.py <knot dir> <plan.json> <out.json>"""
import json
import os
import sys


def main():
    d, plan, out = sys.argv[1:4]
    P = json.load(open(plan))
    D = json.load(open(os.path.join(d, 'dropped.json')))
    Q = {'vias': P['vias'], 'tracks': P['tracks'], 'remove': P.get('remove', []) + D['tracks'],
         'remove_vias': [{k: v[k] for k in ('net', 'x', 'y', 'hole')} for v in D['vias']],
         'log': P.get('log', []) + ['full-model plan: %d dropped tracks and %d dropped vias of %s removed' % (
             len(D['tracks']), len(D['vias']), d)]}
    json.dump(Q, open(out, 'w'), indent=0)
    print('%s: %d vias, %d tracks, remove %d tracks + %d vias' % (out, len(Q['vias']), len(Q['tracks']),
                                                                    len(Q['remove']), len(Q['remove_vias'])))


if __name__ == '__main__':
    main()
