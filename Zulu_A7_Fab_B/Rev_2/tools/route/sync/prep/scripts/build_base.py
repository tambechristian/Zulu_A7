"""(a) base_cur.json = TARGET now; (b) base_new.json = TARGET after the ECO + placement, before any copper change.

    python scripts/build_base.py

Pads of the swapped parts (U2 QFN-64 + EP, X4 S2B-PH-SM4-TB, U10 MSOP-8), the moved parts (U4, R34, C87, C88, C94,
C99, C106, R1) and the new DQ series resistors R119-R134 are taken from SOURCE HEAD (427960e) exactly; U3's DQ pads
take their SOURCE HEAD nets (SDRAM-Dn). Every other pad stays TARGET's. Every pad net of base_new is then checked
against the simulated Fab B netlist after the schematic change (scratchpad sync/schematics/net_sim_r.txt).
"""
import json
import os
import shutil
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F403

SWAP = ['U2', 'X4', 'U10']
MOVE = ['U4', 'R34', 'C87', 'C88', 'C94', 'C99', 'C106', 'R1']
NEW = ['R%d' % i for i in range(119, 135)]
NETLIST = os.environ.get('SIM_NETLIST', 'C:/Users/tambe/AppData/Local/Temp/claude/4f46ee6af972add9/'
                         'cb02897e-21a5-48d4-9f87-57145adc4da2/scratchpad/sync/schematics/net_sim_r.txt')


def main():
    T = load('tgt_33023787')
    H = load('src_427960e')
    S = load('src_22ee1dc')
    json.dump(T, open(os.path.join(PREP, 'base_cur.json'), 'w'))
    rep = []
    hp = {(p['ref'], p['pad']): p for p in H['pads']}
    sp = {(p['ref'], p['pad']): p for p in S['pads']}
    tp = {(p['ref'], p['pad']): p for p in T['pads']}
    take = set(SWAP + MOVE + NEW)
    pads = [dict(p) for p in T['pads'] if p['ref'] not in take]
    for p in H['pads']:
        if p['ref'] in take:
            pads.append(dict(p))
    # U3 DQ pads: SOURCE HEAD nets, TARGET geometry (identical: checked)
    for p in pads:
        if p['ref'] == 'U3':
            q = hp[(p['ref'], p['pad'])]
            assert all(abs(p[k] - q[k]) < 1e-4 for k in ('x', 'y', 'w', 'h')), p
            if p['net'] != q['net']:
                rep.append('U3-%s net %s -> %s' % (p['pad'], p['net'], q['net']))
                p['net'] = q['net']
    # checks: moved parts keep footprint and nets (TARGET == SOURCE 22ee1dc), and SOURCE moved them rigidly
    for ref in MOVE:
        ks = sorted(k for k in tp if k[0] == ref)
        assert ks == sorted(k for k in hp if k[0] == ref), ref
        d = None
        for k in ks:
            a, b, s0 = tp[k], hp[k], sp[k]
            assert all(abs(a[f] - s0[f]) < 1e-4 for f in ('x', 'y', 'w', 'h')) and a['net'] == s0['net'], (k, a, s0)
            assert a['net'] == b['net'] and abs(a['w'] - b['w']) < 1e-4 and abs(a['h'] - b['h']) < 1e-4, (k, a, b)
            dd = (r4(b['x'] - a['x']), r4(b['y'] - a['y']))
            assert d is None or (abs(dd[0] - d[0]) < 2e-4 and abs(dd[1] - d[1]) < 2e-4), (k, dd, d)
            d = dd
        rep.append('%s moved rigidly by (%+.4f, %+.4f) mm, %d pads, nets unchanged' % (ref, d[0], d[1], len(ks)))
    for ref in SWAP:
        old = sorted((k[1], tp[k]['net']) for k in tp if k[0] == ref)
        new = sorted((k[1], hp[k]['net']) for k in hp if k[0] == ref)
        rep.append('%s swapped: %d pads -> %d pads; pad/net changes: %s' % (
            ref, len(old), len(new), sorted(set(new) - set(old))))
    # every pad of a taken part matches SOURCE HEAD exactly
    bn = {(p['ref'], p['pad']): p for p in pads}
    for k, q in hp.items():
        if k[0] in take:
            assert bn[k] == q, k
    # nets vs the simulated Fab B netlist after the schematic change
    nl = {}
    for line in open(NETLIST):
        f = line.split()
        if not f:
            continue
        for pin in f[1:]:
            ref, pad = pin.split('-', 1)
            nl[(ref, pad)] = f[0]
    bad = []
    for p in pads:
        exp = nl.get((p['ref'], p['pad']), '')
        got = p['net'] or ''
        if exp.startswith('N$') and not got:
            continue
        if exp != got and not (exp.startswith('N$') or got.startswith('N$') or got.startswith('Net')):
            bad.append('%s-%s board %r netlist %r' % (p['ref'], p['pad'], got, exp))
    missing = sorted('%s-%s' % k for k in nl if k not in bn)
    B = dict(T, pads=pads)
    json.dump(B, open(os.path.join(PREP, 'base_new.json'), 'w'))
    for line in rep:
        print(line)
    print('base_cur: %d pads, %d tracks, %d vias' % (len(T['pads']), len(T['tracks']), len(T['vias'])))
    print('base_new: %d pads (-%d +%d)' % (len(pads), sum(1 for p in T['pads'] if p['ref'] in take),
                                          sum(1 for p in H['pads'] if p['ref'] in take)))
    print('netlist mismatches: %d %s' % (len(bad), bad[:20]))
    print('netlist pins with no board pad: %d %s' % (len(missing), missing[:20]))
    json.dump({'report': rep, 'netlist_mismatch': bad, 'netlist_pins_without_pad': missing},
              open(os.path.join(PREP, 'base_new_check.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
