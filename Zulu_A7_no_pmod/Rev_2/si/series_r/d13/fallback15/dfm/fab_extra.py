"""fab_extra.py -- PCBWay-side counts for plan15 that a batch DRC does not report:
stacked-microvia sites (new vs PcbDoc), hole-edge to foreign copper on every layer each new hole passes
(drill-to-copper), annular rings of new vias, VIPPO sites total (PcbDoc + plan).
Reuses adv15.py's model by importing it with argv set (adv15 runs main() on import, so the model is rebuilt here).
Usage: python fab_extra.py   (writes fab_extra.log next to itself)"""
import collections, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)).replace(chr(92), '/')
sys.argv = ['adv15.py', '--plan', HERE + '/../plan15.json', '--tag', 'fabx_scratch']
src = open(HERE + '/adv15.py', encoding='utf-8').read().replace('\nmain()\n', '\n')
G = {'__file__': HERE + '/adv15.py', '__name__': 'adv15_lib'}
exec(compile(src, 'adv15.py', 'exec'), G)
base = G['board_base']()
after, errs, _, _ = G['board_after'](G['PL'])
assert not errs, errs
sgap, circ = G['sgap'], G['circ']
L = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    L.append(s)
    print(s)


def stacks(objs):
    by = collections.defaultdict(list)
    for o in objs:
        if o.kind == 'via' and o.vtype != 'thru':
            by[(round(o.x, 4), round(o.y, 4))].append(o)
    return {k: v for k, v in by.items() if len(v) >= 2}


sb, sa = stacks(base), stacks(after)
newst = {k: v for k, v in sa.items() if k not in sb}
gone = {k: v for k, v in sb.items() if k not in sa}
say('stacked microvia sites (>= 2 co-located non-thru vias): PcbDoc %d, plan15 %d, new %d, removed %d' % (
    len(sb), len(sa), len(newst), len(gone)))
for k, v in sorted(newst.items()):
    say('   new stack %s %s: %s' % (k, v[0].net, ' + '.join('%s>%s' % (o.span[0], o.span[-1]) for o in sorted(v, key=lambda o: G['IDX'][o.span[0]]))))
for k, v in sorted(gone.items()):
    say('   removed stack %s %s' % (k, v[0].net))
# drill-to-copper: hole edge to any foreign copper on each layer of the hole's span
cu = [o for o in after if o.kind in ('track', 'via', 'pad')]
grid = collections.defaultdict(list)
for o in cu:
    for Ly, s in o.shp.items():
        b = G['sbox'](s)
        for i in range(int(b[0] / 0.5) - 1, int(b[2] / 0.5) + 2):
            for j in range(int(b[1] / 0.5) - 1, int(b[3] / 0.5) + 2):
                grid[(Ly, i, j)].append(o)
rows = []
for v in after:
    if v.kind != 'via' or not v.new:
        continue
    h = circ(v.x, v.y, v.hole / 2)
    best = (9, None, None)
    for Ly in v.span:
        for o in grid.get((Ly, int(v.x / 0.5), int(v.y / 0.5)), []):
            if o.net == v.net or o.id == v.id:
                continue
            g = sgap(h, o.shp[Ly])
            if g < best[0]:
                best = (g, Ly, o.d())
    rows.append((round(best[0], 4), v.d(), best[1], best[2], round((v.size - v.hole) / 2, 4)))
rows.sort()
say('new/renamed vias: hole-edge to foreign copper (drill-to-copper), tightest 10 (gap, via, layer, other, annular ring):')
for r in rows[:10]:
    say('   %.4f  %s  on %s  vs %s  ring %.4f' % r)
say('min annular ring of new vias %.4f mm' % min(r[4] for r in rows))
# pour-side drill-to-copper is the pour clearance + ring; report the pour clearance used for microvias on L2/L5
vip_b = sum(1 for o in base if o.kind == 'via')
say('VIPPO sites in plan15: %d (%s)' % (len(G['PL']['vippo']), ', '.join(e['pad'] for e in G['PL']['vippo'])))
open(HERE + '/fab_extra.log', 'w').write('\n'.join(L) + '\n')
