"""Apply tools/pin_swap.json to the U1 symbol (2026-10-23, pre-routing pass).

The swap is done by renaming balls on U1's symbol pins: every pin record whose Designator is in the pool gets the
permuted ball (Designator) and that ball's pin name (Name, e.g. IO_L22P_T3_A05_D21_14), in every placed U1 part.
The net labels and no-ERC marks stay where they are, so each Feather net (CHANn) lands on its new ball and the
freed balls stay marked no-connect. Banks 14 and 16 are both 3.3 V, so mixing them is electrical no-op; the
symbol's bank grouping becomes cosmetic only. Refuses unless every net of the plan's 'swap' table still sits on
its old ball in the schematic netlist (a pool closed under the permutation looks the same after any number of
runs, so the designators alone cannot tell a second run from the first).
    python tools/apply_pin_swap.py <perm.json>     (close the SchDocs in Altium first; tools/pin_swap.json was the
                                                    pre-routing pass, a routing swap set comes from tools/swap_apply.py)
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sch_netlist import build  # noqa: E402
from schdoc import field, join, owner, read_stream, set_field, split, write_stream  # noqa: E402

ROOT = os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb')


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: python tools/apply_pin_swap.py <perm.json>')
    plan = json.load(open(sys.argv[1]))
    perm = plan['perm']
    if any(k == v for k, v in perm.items()) and all(k == v for k, v in perm.items()):
        sys.exit('nothing to do')
    swap = plan.get('swap')
    if not swap:
        sys.exit('REFUSED: the plan has no swap table {net: [old ball, new ball]}, so a second run cannot be told apart')
    at = {}
    for net, pins in build(ROOT).items():
        for ref, d in pins:
            if ref == 'U1':
                at.setdefault(net, []).append(d)
    bad = []
    for net, (old, new) in sorted(swap.items()):
        balls = sorted(at.get(net, []))
        if balls == [new]:
            bad.append('%s is already on %s' % (net, new))
        elif balls != [old]:
            bad.append('%s sits on %s, expected %s' % (net, ','.join(balls) or 'nothing', old))
    if bad:
        sys.exit('REFUSED (already applied, or not the schematic this plan was made for): ' + '; '.join(bad))
    total = 0
    for path in sorted(glob.glob(os.path.join(ROOT, '*.SchDoc'))):
        recs = split(read_stream(path))
        refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
        u1 = {c for c, r in refs.items() if r == 'U1'}
        if not u1:
            continue
        pins = [i for i, (h, b) in enumerate(recs) if field(b, 'RECORD') == '2' and owner(b) in u1
                and field(b, 'Designator') in perm]
        name = {}
        for i in pins:
            d, n = field(recs[i][1], 'Designator'), field(recs[i][1], 'Name')
            if name.setdefault(d, n) != n:
                sys.exit('REFUSED: ball %s has two pin names (%s, %s) -- already swapped?' % (d, name[d], n))
        if sorted(name) != sorted(perm):
            sys.exit('REFUSED: %s: found %d of %d pool balls' % (os.path.basename(path), len(name), len(perm)))
        for i in pins:
            d = field(recs[i][1], 'Designator')
            b = set_field(recs[i][1], 'Designator', perm[d])
            recs[i][1] = set_field(b, 'Name', name[perm[d]])
        write_stream(path, join(recs))
        total += len(pins)
        print('%s: %d U1 pin records renamed over %d balls' % (os.path.basename(path), len(pins), len(perm)))
    if not total:
        sys.exit('REFUSED: no U1 pins found')


if __name__ == '__main__':
    main()
