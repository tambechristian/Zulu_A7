"""python score2.py <model> <cfg> <placement> ...: loop lengths + real problems (place_check rules) per placement."""
import json, math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import place_check as PC
M = json.load(open(sys.argv[1])); C = json.load(open(sys.argv[2]))
nets = {(p['ref'], p['pad']): p['net'] for p in M['pads']}
crit = [l for l in C['links'] if l[0] >= 10 and not l[1].startswith('@') and not l[2].startswith('@')]
for f in sys.argv[3:]:
    P = json.load(open(f)); pp = {}; placed = []
    for r, (sd, x, y, rot) in P.items():
        ps = PC.pads_of(r, sd, x, y, rot, nets); placed += ps
        for p in ps: pp[(p['ref'], p['pad'])] = (p['x'], p['y'])
    moved = set(P)
    others = [p for p in M['pads'] if p['ref'] not in moved]
    bad = 0
    for p in placed:
        L = p['layers'][0]
        for q in others + placed:
            if q['ref'] == p['ref']: continue
            if L in q['layers'] or q.get('drill', 0) > 0:
                lim = 0.1 if (q['net'] == p['net'] and q['net'] and q['ref'] in moved) else PC.GAP
                if PC.rect_gap(p, q) < lim - 0.002: bad += 1
    d = {'%s-%s' % (a, b): math.dist(pp[tuple(a.split('.'))], pp[tuple(b.split('.'))]) for w, a, b in crit}
    worst = sorted(d.items(), key=lambda t: -t[1])[:4]
    print('%-16s bad %3d  sum %.1f  worst %s' % (os.path.basename(f), bad, sum(d.values()), ' '.join('%s %.1f' % w for w in worst)))
