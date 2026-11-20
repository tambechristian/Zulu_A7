"""Judge-style full check of a strategy-C plan (relative to TARGET's current copper).

    python scripts/check.py <plan.json> <tag>          writes C/out/<tag>/{result.json, check.json}

  1. emit-readiness on base_cur AND base_new (judge.emit_match: each remove line hits exactly one board object);
  2. result = base_new - removals + additions;
  3. route_check.py <plan> base_new (TARGET's gate, in-process with SDRAM-D0..15 in the SDRAM rule set, via prep/geo);
  4. prune_stubs.analyse (dead copper) + route_conn (open connections) on the result;
  5. full-board exact DRC (judge.drc) of the result vs base_cur: NEW violations only;
  6. through via in any SMD pad (must be 0), microvias in SMD pads new vs base_cur;
  7. USB metrics, counts by via span, added/removed length, Pmod nets touched.
"""
import contextlib
import io
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CDIR = os.path.dirname(HERE)
PREP = os.path.join(os.path.dirname(CDIR), 'prep')
sys.path.insert(0, os.path.join(PREP, 'scripts'))
import geo  # noqa: E402  (TARGET router/route_conn/prune_stubs/judge with SDRAM-D0..15 in the SDRAM set)

J, C, PS, R = geo.J, geo.C, geo.PS, geo.R
STACK = R.STACK
PMOD = {'JA%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)} | {'PMOD-%d' % i for i in (1, 2, 3, 4, 7, 8, 9, 10)}


def tlen(t):
    return math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])


def main():
    plan_path, tag = sys.argv[1], sys.argv[2]
    out_dir = os.path.join(CDIR, 'out', tag)
    os.makedirs(out_dir, exist_ok=True)
    P = json.load(open(plan_path))
    Bc = json.load(open(os.path.join(PREP, 'base_cur.json')))
    Bn = json.load(open(os.path.join(PREP, 'base_new.json')))
    for M in (Bc, Bn):
        for v in M['vias']:
            v['span'] = J.span(v)
    rep = {'plan': plan_path}
    kt0, kv0, probs0 = J.emit_match(Bc, P)
    kt, kv, probs = J.emit_match(Bn, P)
    rep['emit_problems_base_cur'] = probs0
    rep['emit_problems_base_new'] = probs
    newv = [dict(v, span=J.span(v)) for v in P['vias']]
    Res = {'board': Bn['board'], 'planes': Bn['planes'], 'pads': Bn['pads'],
           'tracks': [t for i, t in enumerate(Bn['tracks']) if i not in kt] + [dict(t) for t in P['tracks']],
           'vias': [v for i, v in enumerate(Bn['vias']) if i not in kv] + newv}
    json.dump(Res, open(os.path.join(out_dir, 'result.json'), 'w'))
    import route_check as RC
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv[:] = ['route_check.py', plan_path, os.path.join(PREP, 'base_new.json')]
    with contextlib.redirect_stdout(buf):
        rc = RC.main()
    sys.argv[:] = argv
    rep['route_check'] = buf.getvalue().splitlines()
    rep['route_check_pass'] = rc == 0
    dt, dv, _, _ = PS.analyse(Res)
    rep['dead_after'] = {'tracks': [J.desc('t', t) for t in dt], 'vias': [J.desc('v', v) for v in dv]}
    oc = C.open_count(C.islands(Res))
    rep['open_total'] = sum(oc.values())
    rep['open_by_net'] = dict(sorted(oc.items()))
    v_res = J.drc(Res)
    v_cur = J.drc(Bc)
    new = {k: s for k, s in v_res.items() if k not in v_cur}
    rep['drc_counts'] = {'base_cur': len(v_cur), 'result': len(v_res), 'new_vs_base_cur': len(new)}
    rep['drc_new'] = sorted(new.values())
    smd = [p for p in Res['pads'] if not p['drill']]
    smd0 = [p for p in Bc['pads'] if not p['drill']]
    old_uv = {J.vkey(v) for v in Bc['vias'] if v['span'] != STACK and J.via_pad_hits(v, smd0)}
    th, uv_new, uv_all = [], [], 0
    for v in Res['vias']:
        h = J.via_pad_hits(v, smd)
        if not h:
            continue
        if v['span'] == STACK:
            th.append((J.desc('v', v), h))
        else:
            uv_all += 1
            if J.vkey(v) not in old_uv:
                uv_new.append((J.desc('v', v), h))
    rep['through_via_in_smd_pad'] = th
    rep['uvia_in_smd_pad_total'] = uv_all
    rep['uvia_in_smd_pad_new'] = len(uv_new)
    rep['uvia_in_smd_pad_new_list'] = uv_new
    rep['new_through_vias'] = [J.desc('v', v) for v in newv if v['span'] == STACK]
    rep['usb'] = J.usb_metrics(Res)
    rm_tk = Counter(J.tkey(t) for t in P['remove'])
    rep['counts'] = {
        'remove_tracks': len(P['remove']), 'remove_vias': len(P['remove_vias']), 'add_tracks': len(P['tracks']),
        'add_vias': len(P['vias']),
        'vias_added_by_type': dict(sorted(Counter(J.vkind(v) for v in newv).items())),
        'vias_removed_by_type': dict(sorted(Counter(J.vkind(dict(v, span=J.span(v))) for v in P['remove_vias']).items())),
        'tracks_added_by_layer': dict(sorted(Counter(t['layer'] for t in P['tracks']).items())),
        'tracks_removed_by_layer': dict(sorted(Counter(t['layer'] for t in P['remove']).items())),
        'added_track_mm': round(sum(map(tlen, P['tracks'])), 2),
        'removed_track_mm': round(sum(map(tlen, P['remove'])), 2),
        'board_track_mm_base_cur': round(sum(map(tlen, Bc['tracks'])), 2),
        'board_track_mm_result': round(sum(map(tlen, Res['tracks'])), 2),
        'result_tracks': len(Res['tracks']), 'result_vias': len(Res['vias']), 'result_pads': len(Res['pads'])}
    a = Counter(J.vkind(v) for v in newv)
    r = Counter(J.vkind(dict(v, span=J.span(v))) for v in P['remove_vias'])
    rep['counts']['net_via_change_by_type'] = {k: a[k] - r[k] for k in sorted(set(a) | set(r))}
    touched = sorted({t['net'] for t in P['tracks'] + P['remove']} | {v['net'] for v in P['vias'] + P['remove_vias']})
    rep['pmod_nets_touched'] = {n: {'add_t': sum(1 for t in P['tracks'] if t['net'] == n),
                                    'rm_t': sum(1 for t in P['remove'] if t['net'] == n),
                                    'add_v': sum(1 for v in P['vias'] if v['net'] == n),
                                    'rm_v': sum(1 for v in P['remove_vias'] if v['net'] == n)}
                                for n in touched if n in PMOD}
    rep['nets_touched'] = len(touched)
    json.dump(rep, open(os.path.join(out_dir, 'check.json'), 'w'), indent=1, default=str)
    show = {k: v for k, v in rep.items() if k not in ('usb', 'dead_after', 'uvia_in_smd_pad_new_list')}
    show['dead_after'] = {k: len(v) for k, v in rep['dead_after'].items()}
    show['usb'] = {k: v for k, v in rep['usb'].items() if k != 'geom'}
    print(json.dumps(show, indent=1, default=str))


if __name__ == '__main__':
    main()
