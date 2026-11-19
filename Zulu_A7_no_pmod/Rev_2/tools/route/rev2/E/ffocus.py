"""ffocus.py --model M --seed S --out OUT --net NET --focus x0,y0,x1,y1 [finish.py knobs]
finish.py's partial rip-up finisher (efast via policy) for ONE open connection of NET, with the search windows taken
from a hand-picked focus box (focus +1.2 / +3.0 mm, then the islands' bbox) instead of the whole islands' bbox, which
for a long net is the whole board. Several --net/--focus pairs may be given as NET@x0,y0,x1,y1;NET@... in --jobs."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import efast  # noqa: E402
FN = efast.FN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--seed', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', required=True, help='NET@x0,y0,x1,y1;NET@...')
    ap.add_argument('--clear', type=float, default=0.09)
    ap.add_argument('--slack', type=float, default=0.02)
    ap.add_argument('--laser-small', default='')
    ap.add_argument('--depth', type=int, default=3)
    ap.add_argument('--alts', type=int, default=4)
    ap.add_argument('--rc', type=float, default=0.4)
    ap.add_argument('--maxv', type=int, default=4)
    ap.add_argument('--soft', type=float, default=1.0)
    ap.add_argument('--hw', type=float, default=2.0)
    ap.add_argument('--hpops', type=int, default=600000)
    ap.add_argument('--margin', type=float, default=2.5)
    ap.add_argument('--planes-hard', action='store_true')
    ap.add_argument('--pops', type=int, default=1500000)
    ap.add_argument('--lpops', type=int, default=600000)
    ap.add_argument('--tlimit', type=float, default=1500)
    a = ap.parse_args()
    t0 = time.time()
    F = FN.Fin(a)
    oc = F.opens()
    print('seeded %d vias, %d tracks; open %d: %s' % (len(F.Rt.out_v), len(F.Rt.out_t), sum(oc.values()), oc), flush=True)

    def write():
        json.dump({'vias': F.Rt.out_v, 'tracks': F.Rt.out_t, 'remove': F.removed, 'log': F.log}, open(a.out, 'w'), indent=0)
    for job in [j for j in a.jobs.split(';') if j]:
        net, box = job.split('@')
        focus = tuple(float(v) for v in box.split(','))
        Mn, gs = F.isl(net)
        if len(gs) < 2:
            F.say('== %s already joined' % net)
            continue
        snap = F.snap()
        before = sum(F.opens().values())
        F.deadline = time.time() + a.tlimit
        t1 = time.time()
        F.say('== %s focus %s (%d islands)' % (net, box, len(gs)))
        ok = False
        try:
            ok = F.solve(net, a.depth, set(), focus, len(gs) - 1)
            why = ''
        except FN.Timeout:
            why = ' (time limit)'
        after = sum(F.opens().values())
        if ok and after < before:
            F.say('== %s: open %d -> %d, %.0f s' % (net, before, after, time.time() - t1))
            write()
        else:
            F.restore(snap)
            F.say('== %s: not closed%s (open %d -> %d), %.0f s' % (net, why, before, after, time.time() - t1))
    oc = F.opens()
    write()
    print('ffocus: open %d %s; %d vias %d tracks -> %s (%.0f s)' % (sum(oc.values()), oc, len(F.Rt.out_v), len(F.Rt.out_t), a.out, time.time() - t0))


if __name__ == '__main__':
    main()
