"""Plan for the 5 Net Antennae of the 2026-11-19 DRC (2026-11-19). READ-ONLY; writes antennae_plan.json.

    python tools/route/drc20/plan.py

Each antenna Altium reported is a SEED. Starting there only, dead objects are peeled off one at a time: a track with an
end that touches nothing else, a track lying wholly inside one via pad (Altium does not count it), a via touching at
most one other object (swallowed stubs excluded). Peeling stops at the first object still joined on both sides.
Joins use walk.py's touches() (0.02 mm). Then every pad of each net must still be one connected group, and no object
left behind may have become dead: a track whose end is freed is reported and handled explicitly.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'walk.py')).read().split('out = {}')[0]
exec(src)                                                                  # M, touches(), name(), segd()

SEEDS = [('USB5V0', lambda o: o[0] == 't' and abs(o[1]['x2'] - 34.325) < 1e-3 and abs(o[1]['x1'] - 32.9) < 1e-3),
         ('PROG#', lambda o: o[0] == 'v' and abs(o[1]['x'] - 50.05) < 1e-3 and abs(o[1]['y'] - 13.75) < 1e-3),
         ('FLASH-D02', lambda o: o[0] == 'v' and abs(o[1]['x'] - 51.05) < 1e-3 and abs(o[1]['y'] - 13.55) < 1e-3 and o[1]['span'][-1] == 'Bottom Layer'),
         ('CLK-12M-FPGA', lambda o: o[0] == 'v' and abs(o[1]['x'] - 53.2) < 1e-3 and abs(o[1]['y'] - 12.7) < 1e-3 and o[1]['span'][0] == 'L4-SIG'),
         ('FLASH-D02', lambda o: o[0] == 'v' and abs(o[1]['x'] - 55.7) < 1e-3 and abs(o[1]['y'] - 13.3) < 1e-3 and o[1]['span'][0] == 'L2-GND')]


def swallowed(t, v):
    """t lies wholly inside v: a via pad, or another track's body on the same layer (Altium does not count it)."""
    if t[0] != 't' or t is v:
        return False
    ends = ((t[1]['x1'], t[1]['y1']), (t[1]['x2'], t[1]['y2']))
    if v[0] == 'v':
        return t[1]['layer'] in v[1]['span'] and all(math.hypot(x - v[1]['x'], y - v[1]['y']) <= v[1]['size'] / 2 for x, y in ends)
    if v[0] == 't':
        return t[1]['layer'] == v[1]['layer'] and all(segd(x, y, v[1]) <= v[1]['w'] / 2 for x, y in ends) and             math.hypot(t[1]['x2'] - t[1]['x1'], t[1]['y2'] - t[1]['y1']) < math.hypot(v[1]['x2'] - v[1]['x1'], v[1]['y2'] - v[1]['y1'])
    return False


def end_free(objs, alive, i):
    k, A = objs[i]
    for (x, y) in ((A['x1'], A['y1']), (A['x2'], A['y2'])):
        pt = ('t', dict(A, x1=x, y1=y, x2=x, y2=y))
        if not any(touches(pt, objs[j]) for j in alive if j != i and not swallowed(objs[j], objs[i])):
            return True
    return False


def is_dead(objs, alive, i):
    k, A = objs[i]
    if k == 'p':
        return False
    if k == 't':
        return end_free(objs, alive, i) or any(swallowed(objs[i], objs[j]) for j in alive if j != i)
    nb = [j for j in alive if j != i and touches(objs[i], objs[j]) and not swallowed(objs[j], objs[i])]
    return len(nb) <= 1


plan = {'remove': [], 'remove_vias': [], 'tracks': [], 'vias': []}
trims = []
removed_by_net = {}
for net, seed in SEEDS:
    objs = removed_by_net.setdefault(net, {'objs': None, 'alive': None, 'gone': []})
    if objs['objs'] is None:
        objs['objs'] = [('t', t) for t in M['tracks'] if t['net'] == net] + [('v', v) for v in M['vias'] if v['net'] == net] + \
                       [('p', p) for p in M['pads'] if p['net'] == net]
        objs['alive'] = set(range(len(objs['objs'])))
    O, alive = objs['objs'], objs['alive']
    s = [i for i in alive if seed(O[i])]
    assert len(s) == 1, (net, len(s))
    assert is_dead(O, alive, s[0]), ('seed not dead', name(O[s[0]]))
    front, gone = [s[0]], []
    while front:
        i = front.pop()
        if i not in alive or not is_dead(O, alive, i):
            continue
        k, A = O[i]
        if k == 't' and not any(swallowed(O[i], O[j]) for j in alive if j != i):
            # a track with one free end: if a live object joins its BODY (a T), only the stretch from the free end to
            # the nearest T point is dead -- trim the track there instead of deleting it
            ends = [(A['x1'], A['y1']), (A['x2'], A['y2'])]
            free = [e for e in ends if not any(touches(('t', dict(A, x1=e[0], y1=e[1], x2=e[0], y2=e[1])), O[j])
                                               for j in alive if j != i and not swallowed(O[j], O[i]))]
            if len(free) == 1:
                fx, fy = free[0]
                keep = [e for e in ends if e != free[0]][0]
                tees = []
                for j in alive:
                    if j == i or O[j][0] != 't' or O[j][1]['layer'] != A['layer']:
                        continue
                    for (x, y) in ((O[j][1]['x1'], O[j][1]['y1']), (O[j][1]['x2'], O[j][1]['y2'])):
                        if segd(x, y, A) <= TOL and math.hypot(x - keep[0], y - keep[1]) > TOL and                                 math.hypot(x - fx, y - fy) > TOL:
                            tees.append((math.hypot(x - fx, y - fy), x, y))
                if tees:
                    _, tx, ty = min(tees)
                    new = dict(A, x1=tx, y1=ty, x2=keep[0], y2=keep[1])
                    trims.append((A, new))
                    O[i] = ('t', new)
                    print('     ~ trim %s to start at (%.4f, %.4f)' % (name(('t', A)), tx, ty))
                    continue
        alive.discard(i)
        gone.append(i)
        front += [j for j in alive if touches(O[i], O[j]) or touches(O[j], O[i])]
    objs['gone'] += gone
    print('%s: seed %s -> %d objects' % (net, name(O[s[0]]), len(gone)))
    for i in gone:
        print('     -', name(O[i]))

for net, d in removed_by_net.items():
    O, alive = d['objs'], d['alive']
    pads = [i for i in alive if O[i][0] == 'p']
    seen, st = set(), pads[:1]
    while st:
        i = st.pop()
        if i in seen:
            continue
        seen.add(i)
        st += [j for j in alive if j not in seen and (touches(O[i], O[j]) or touches(O[j], O[i]))]
    ok = all(p in seen for p in pads)
    left_dead = [name(O[i]) for i in alive if is_dead(O, alive, i)]
    near = [name(O[i]) for i in alive if is_dead(O, alive, i) and any(touches(O[i], O[g]) or touches(O[g], O[i]) for g in d['gone'])]
    print('%-13s pads %d connected after: %s; dead objects bordering the removal: %s' % (net, len(pads), ok, near or 'none'))
    assert ok
    for i in d['gone']:
        k, A = O[i]
        if k == 't':
            plan['remove'].append(A)
        else:
            plan['remove_vias'].append(A)
for old, new in trims:
    plan['remove'].append(old)
    plan['tracks'].append(new)
json.dump(plan, open(os.path.join(HERE, 'antennae_plan.json'), 'w'), indent=1)
print('plan: remove %d tracks, %d vias; re-add %d trimmed tracks' % (len(plan['remove']), len(plan['remove_vias']), len(plan['tracks'])))
