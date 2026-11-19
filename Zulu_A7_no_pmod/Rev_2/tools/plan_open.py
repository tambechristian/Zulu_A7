"""Open connections per net of a plan on top of a model (2026-10-31): the route_check composition, route_conn count.

    python tools/plan_open.py <plan.json> <model.json> [--nets A,B]      (--nets limits the listing)"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import route_conn as C  # noqa: E402
from route_check import span  # noqa: E402


def compose(plan, M):
    rm = plan.get('remove', [])

    def same(t, r):
        return t['net'] == r['net'] and t['layer'] == r['layer'] and \
            {(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))} == \
            {(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))}
    M = dict(M)
    M['tracks'] = [t for t in M['tracks'] if not any(same(t, r) for r in rm)] + plan['tracks']
    rmv = plan.get('remove_vias', [])
    M['vias'] = [v for v in M['vias'] if not any(v['net'] == r['net'] and abs(v['x'] - r['x']) < 0.002 and
                                                 abs(v['y'] - r['y']) < 0.002 and abs(v['hole'] - r['hole']) < 0.002
                                                 for r in rmv)]
    M['vias'] = M['vias'] + [dict(v, span=span(v)) for v in plan['vias']]
    return M


def main():
    plan = json.load(open(sys.argv[1]))
    M = json.load(open(sys.argv[2]))
    only = set(sys.argv[sys.argv.index('--nets') + 1].split(',')) if '--nets' in sys.argv else None
    oc = C.open_count(C.islands(compose(plan, M)))
    print('open connections %d on %d nets' % (sum(oc.values()), len(oc)))
    print(', '.join('%s %d' % kv for kv in sorted(oc.items(), key=lambda kv: (-kv[1], kv[0])) if not only or kv[0] in only))


if __name__ == '__main__':
    main()
