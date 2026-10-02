# -*- coding: utf-8 -*-
"""Which pads of a net are joined to its source once these plans are placed?

    python tools/stage3/islands.py --net VCC3V3 [--source C80-2] [--pads C3-2,C4-2,...] [--inputs F] plan.json [...]

Prints the net's copper islands on the board plus the plans (block_place.islands: pads, vias and tracks
joined end to end), then, for --pads, whether each named pad sits in the island that holds --source
(default: VCC3V3 -> C80-2, FT-VCORE -> U2-12, FT-VPHY -> L4-1, FT-VPLL -> L5-1).  Exit 1 if any
named pad is not joined."""
import io, json, os, sys
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_place as BP
import merge as M

SRC = {'VCC3V3': 'C80-2', 'FT-VCORE': 'U2-12', 'FT-VPHY': 'L4-1', 'FT-VPLL': 'L5-1'}


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    net = opt('--net', 'VCC3V3')
    src = opt('--source', SRC.get(net))
    pads = [p for p in opt('--pads', '').split(',') if p]
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))
    skip = set()
    for k in ('--net', '--source', '--pads', '--inputs'):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    paths = [p for i, p in enumerate(a) if i not in skip and p.endswith('.json')]
    plan = M.merge(paths)[0] if paths else {'vias': [], 'tracks': []}
    isl = BP.islands(inp, plan, net)
    isl = sorted(isl, key=lambda s: -len(s))
    print('%s: %d island(s) with %d plan file(s)' % (net, len(isl), len(paths)))
    home = None
    for s in isl:
        if src in {str(x) for x in s}:
            home = {str(x) for x in s}
    if home is None:
        print('source %s not found on the net' % src)
        return 2
    print('source island (%s): %d members' % (src, len(home)))
    bad = []
    for p in pads:
        ok = p in home
        print('  %-8s %s' % (p, 'joined' if ok else 'NOT joined'))
        if not ok:
            bad.append(p)
    if pads:
        print('%d/%d named pads joined to %s' % (len(pads) - len(bad), len(pads), src))
    else:
        for s in isl:
            if len(s) > 1 or True:
                print('  ' + ' '.join(sorted(str(x) for x in s))[:300])
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
