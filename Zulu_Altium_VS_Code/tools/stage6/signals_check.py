# -*- coding: utf-8 -*-
"""Which nets are still in more than one copper island once these plans are placed?

    python tools/stage4/signals_check.py [--inputs F] [--nets A,B,C] [--all] plan.json [...]

route_emit's "nets joined" counts only the 67 nets route_inputs.json models (power, SDRAM, XADC, charger);
the 109 signal nets of stage 4b live only in the pad lists.  This walks every net that has pads
(block_place.islands: pads, tracks and vias joined end to end, board plus the plans), skips GND/GNDADC
(plane nets), and prints the nets whose pads are not all in one island -- with --nets only those, with
--all every net including the joined ones.  Exit 1 if any listed net is split."""
import io, json, os, sys, collections
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import block_place as BP
import merge as M


def main():
    a = sys.argv[1:]

    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    inp = json.load(io.open(opt('--inputs', os.path.join(TOOLS, 'route_inputs.json')), encoding='utf-8'))
    want = [n for n in opt('--nets', '').split(',') if n]
    skip = set()
    for k in ('--inputs', '--nets'):
        if k in a:
            skip.add(a.index(k)); skip.add(a.index(k) + 1)
    paths = [p for i, p in enumerate(a) if i not in skip and p.endswith('.json')]
    plan = M.merge(paths)[0] if paths else {'vias': [], 'tracks': []}
    if plan.get('remove'):             # stage 4b: the board as the plan leaves it (removals applied first)
        import route_emit as RE
        inp, missing = RE.apply_removals(inp, plan)
        if missing:
            print('REMOVALS DO NOT MATCH THE BOARD: %s' % '; '.join(missing))
            return 2
    npads = collections.Counter(p['net'] for k in ('top_pads', 'bottom_pads', 'th_pads') for p in inp[k] if p.get('net'))
    nets = want or sorted(n for n, c in npads.items() if c >= 2 and n not in ('GND', 'GNDADC'))
    split, joined = [], []
    for n in nets:
        isl = BP.islands(inp, plan, n)
        with_pads = [s for s in isl if any(not str(x).startswith('via@') for x in s)]
        if len(with_pads) > 1:
            split.append((n, len(with_pads), [sorted(str(x) for x in s if not str(x).startswith('via@')) for s in with_pads]))
        else:
            joined.append(n)
    print('%d nets checked (board + %d plan file(s): %d vias, %d tracks): %d joined, %d split' % (
        len(nets), len(paths), len(plan['vias']), len(plan['tracks']), len(joined), len(split)))
    for n, k, isl in split:
        print('  SPLIT %-14s %d islands: %s' % (n, k, ' | '.join(','.join(s)[:60] for s in isl)[:200]))
    if '--all' in a:
        print('joined: ' + ' '.join(joined))
    return 1 if split else 0


if __name__ == '__main__':
    sys.exit(main())
