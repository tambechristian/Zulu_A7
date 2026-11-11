"""Prove the Feather schematic edit did exactly what feather_map.py says, by netlist.

Expected = the original Zulu A7 netlist (the KiCad-proven reports/kicad.net, which sch_netlist.py reproduces
177/177) transformed by feather_map.py: parts removed, X2/U3 pins renumbered, the moved pins re-netted.
Actual = sch_netlist.py run on Asar_feather.PrjPcb. They must match net for net, names included.
    python tools/check_feather_schematic.py [--perm <perm.json> ...]   (each later ball permutation, in the order
                                                                       applied after tools/pin_swap.json)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feather_map as M  # noqa: E402
import sexpr  # noqa: E402
from sch_netlist import build  # noqa: E402

ROOT = os.path.dirname(HERE)
REF = os.path.join(ROOT, '..', 'Zulu_kicad', 'reports', 'kicad.net')
CLEARED = '--before-clear' not in sys.argv     # default: the single-pin net labels have been cleared
_SWAP = os.path.join(HERE, 'pin_swap.json')


def compose(files):
    """original ball -> ball after the permutations in `files`, applied in order (perm[d]: the pin at d moves to perm[d])"""
    perm = {}
    for f in files:
        p = json.load(open(f))['perm']
        perm = {d: p.get(perm.get(d, d), perm.get(d, d)) for d in set(perm) | set(p)}
    return perm


_FILES = [_SWAP] if os.path.exists(_SWAP) and '--before-swap' not in sys.argv else []
_FILES += [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == '--perm']
PERM = compose(_FILES)


def expected():
    nets = {}
    for name, pins in sexpr.netlist(REF).items():
        nets[name] = set(pins)
    moved = {}
    for pad, (fname, old, label) in M.FEATHER.items():
        if label:
            moved[('X2', str(pad))] = label
    for ref in ('U5', 'U6', 'U7'):
        moved[(ref, '3')] = 'EN'
    for ref, (n1, n2, value, mpn) in M.REUSED.items():
        moved[(ref, '1')] = n1
        moved[(ref, '2')] = n2
    for d, (pname, net) in M.X1_PINS.items():
        moved[('X1', d)] = net
    gone = set(M.REMOVED)
    out = {}
    for name, pins in nets.items():
        for ref, d in pins:
            if ref in gone or (ref == 'X1' and d in M.X1_DROPPED_PINS):
                continue
            if ref == 'X2':
                if int(d) in M.X2_DROPPED:
                    continue
                d = str(M.X2_OLD_TO_NEW[int(d)])
            if ref == 'U3':
                d = M.SDRAM_BALL[int(d)]
            if ref == 'U1' and d in PERM:                  # Feather pin swap (tools/pin_swap.json)
                d = PERM[d]
            out.setdefault(moved.get((ref, d), name), set()).add((ref, d))
    for (ref, d), net in getattr(M, 'ADDED_PINS', {}).items():   # parts the Feather adds
        out.setdefault(net, set()).add((ref, d))
    # no-connect pins stay single; nets whose labels clear_single_pin_nets.py removed are gone too, once it has run
    cleared = set(M.CLEARED_NETS) if CLEARED else set()
    return {k: v for k, v in out.items() if not k.startswith('unconnected-') and k not in cleared}


def main():
    exp = expected()
    act = {k: set(v) for k, v in build(os.path.join(ROOT, 'Asar_feather.PrjPcb')).items()}
    # auto-named nets carry a pin-derived name on both sides; compare those by membership only
    def key(nets):
        named = {k: frozenset(v) for k, v in nets.items() if not k.startswith(('N$', 'Net-'))}
        anon = {frozenset(v) for k, v in nets.items() if k.startswith(('N$', 'Net-')) and len(v) > 1}
        return named, anon
    en, ea = key(exp)
    an, aa = key(act)
    bad = 0
    for k in sorted(set(en) | set(an)):
        if en.get(k) != an.get(k):
            bad += 1
            e, a = en.get(k, frozenset()), an.get(k, frozenset())
            print('NET %-14s missing %s  extra %s' % (k, sorted(e - a), sorted(a - e)))
    for s in ea ^ aa:
        bad += 1
        print('UNNAMED', 'expected-only' if s in ea else 'actual-only', sorted(s))
    merges = [k for k in an if '+' in k]
    print('named nets %d, unnamed %d, mismatches %d, merged names %s' % (len(an), len(aa), bad, merges))
    print('PASS' if bad == 0 and not merges else 'FAIL')
    return 0 if bad == 0 and not merges else 1


if __name__ == '__main__':
    sys.exit(main())
