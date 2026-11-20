"""Collect the numbers of every variant into summary.json + opens.json, copy the clean result to model.json (the router
input) and write placement.json (the ECO / placement the Altium step must reproduce, from SOURCE HEAD).

    python scripts/summarize.py
"""
import json
import os
import shutil
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F403

VARIANTS = {'clean': '', 'stubs': '_stubs', 'ripja': '_ripja', 'stubs_ripja': '_stubs_ripja'}
INV = 'C:/Users/tambe/AppData/Local/Temp/claude/4f46ee6af972add9/cb02897e-21a5-48d4-9f87-57145adc4da2/scratchpad/sync/board/json/'
PARTS = ['U2', 'X4', 'U10', 'U4', 'R34', 'C87', 'C88', 'C94', 'C99', 'C106', 'R1'] + ['R%d' % i for i in range(119, 135)]


def main():
    shutil.copyfile(os.path.join(PREP, 'after_transplant.json'), os.path.join(PREP, 'model.json'))
    S, O = {}, {}
    for name, sfx in VARIANTS.items():
        P = json.load(open(os.path.join(PREP, 'transplant%s.json' % sfx)))
        D = json.load(open(os.path.join(PREP, 'dropped%s.json' % sfx)))
        C = json.load(open(os.path.join(PREP, 'check%s.json' % sfx)))
        Lg = json.load(open(os.path.join(PREP, 'transplant_log%s.json' % sfx)))
        drop_net = defaultdict(Counter)
        for d in D:
            if d['what'] == 'addition' and 'obj' in d:
                drop_net[d['obj']['net']][d['reason'].split(' (')[0]] += 1
        S[name] = {
            'plan': {'remove_tracks': len(P['remove']), 'remove_vias': len(P['remove_vias']), 'add_tracks': len(P['tracks']),
                     'add_vias': len(P['vias'])},
            'removals_by_reason': Lg['removals_by_reason'],
            'features_added': P['_meta']['features_added'],
            'dropped_by_reason': dict(Counter('%s | %s | %s' % (d['what'], d['reason'], d.get('zone', '')) for d in D)),
            'dropped_additions_by_net': {n: dict(c) for n, c in sorted(drop_net.items())},
            'emit_problems': C['emit_problems_base_cur'] + C['emit_problems_base_new'],
            'route_check': C['route_check'],
            'dead_copper_after': {k: len(v) for k, v in C['dead_after'].items()},
            'open_total': C['open_total'], 'open_by_net': C['open_by_net'],
            'drc_counts': C['drc_counts'], 'through_via_in_smd_pad': C['through_via_in_smd_pad'],
            'uvia_in_smd_pad_new': len(C['uvia_in_smd_pad_new']), 'new_through_vias': len(C['new_through_vias']),
            'usb': {k: v for k, v in C['usb'].items() if k != 'geom'}, 'counts': C['counts']}
        O[name] = C['open_islands']
    json.dump(S, open(os.path.join(PREP, 'summary.json'), 'w'), indent=1)
    json.dump(O, open(os.path.join(PREP, 'opens.json'), 'w'), indent=1)
    # placement (component records from the inventory's native extract of SOURCE HEAD and TARGET)
    pl = []
    Hn = json.load(open(INV + 'src_427960e.json'))
    Tn = json.load(open(INV + 'tgt.json'))
    hc = {c['ref']: c for c in Hn['comps']}
    tc = {c['ref']: c for c in Tn['comps']}
    keys = ['ref', 'x', 'y', 'rot', 'side', 'footprint', 'lib', 'height']
    for r in PARTS:
        h = hc[r]
        t = tc.get(r)
        pl.append({'ref': r, 'source_head': {k: h.get(k) for k in keys},
                   'target_now': ({k: t.get(k) for k in keys} if t else None)})
    json.dump(pl, open(os.path.join(PREP, 'placement.json'), 'w'), indent=1)
    for name in S:
        s = S[name]
        print('%-12s plan %s open %d %s drc_new %d thruVIP %d dead %s usb mismatch %.4f' % (
            name, s['plan'], s['open_total'], sorted(s['open_by_net']), s['drc_counts']['new_vs_base_cur'],
            len(s['through_via_in_smd_pad']), s['dead_copper_after'], s['usb']['mismatch_mm']))


if __name__ == '__main__':
    main()
