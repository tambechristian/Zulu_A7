"""(d) apply a transplant plan to base_new and check it.

    python scripts/apply_check.py [transplant.json] [tag]

  1. emit-readiness on base_cur AND base_new (judge.emit_match: every remove line hits exactly one board object, the
     Kill counts equal the list lengths);
  2. after_transplant<tag>.json = base_new - removals + additions (the model the router and route_check start from);
  3. route_check.py <plan> base_new.json (TARGET's gate, in-process with SDRAM-D0..15 in the SDRAM rule set);
  4. prune_stubs.analyse on the result (dead copper; must be 0) and route_conn (open connections);
  5. full-board exact DRC (judge.drc) on the result vs base_cur: NEW violations only - this covers pads that moved or
     appeared (U2/X4/U10/R119-R134/U4/R34/C*/R1) against copper that stays, which route_check never checks;
  6. through via in any SMD pad (must be 0) and microvias in SMD pads that are new;
  7. USB_D_P / USB_D_N metrics (judge.usb_metrics) + per-layer / via facts.
Writes check<tag>.json and prints a summary.
"""
import contextlib
import io
import json
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa: E402,F403
import geo  # noqa: E402

J, C, PS, R = geo.J, geo.C, geo.PS, geo.R


def main():
    plan_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PREP, 'transplant.json')
    tag = sys.argv[2] if len(sys.argv) > 2 else ''
    P = json.load(open(plan_path))
    Bc = json.load(open(os.path.join(PREP, 'base_cur.json')))
    Bn = json.load(open(os.path.join(PREP, 'base_new.json')))
    for M in (Bc, Bn):
        for v in M['vias']:
            v['span'] = J.span(v)
    rep = {'plan': os.path.basename(plan_path)}
    kt0, kv0, probs0 = J.emit_match(Bc, P)
    kt, kv, probs = J.emit_match(Bn, P)
    rep['emit_problems_base_cur'] = probs0
    rep['emit_problems_base_new'] = probs
    newv = [dict(v, span=J.span(v)) for v in P['vias']]
    Res = {'board': Bn['board'], 'planes': Bn['planes'], 'pads': Bn['pads'],
           'tracks': [t for i, t in enumerate(Bn['tracks']) if i not in kt] + [dict(t) for t in P['tracks']],
           'vias': [v for i, v in enumerate(Bn['vias']) if i not in kv] + newv}
    out_model = os.path.join(PREP, 'after_transplant%s.json' % tag)
    json.dump(Res, open(out_model, 'w'))
    # route_check, TARGET's own gate (in-process so the SDRAM-Dn rule patch applies)
    import route_check as RC
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv[:] = ['route_check.py', plan_path, os.path.join(PREP, 'base_new.json')]
    with contextlib.redirect_stdout(buf):
        rc = RC.main()
    sys.argv[:] = argv
    rep['route_check'] = buf.getvalue().splitlines()
    rep['route_check_pass'] = rc == 0
    # dead copper + opens
    dt, dv, nt, nv = PS.analyse(Res)
    rep['dead_after'] = {'tracks': [J.desc('t', t) for t in dt], 'vias': [J.desc('v', v) for v in dv]}
    isl = C.islands(Res)
    oc = C.open_count(isl)
    rep['open_total'] = sum(oc.values())
    rep['open_by_net'] = dict(sorted(oc.items()))
    detail = {}
    for net in sorted(oc):
        gs = []
        for g in isl[net]:
            pads = ['%s-%s' % (Res['pads'][i]['ref'], Res['pads'][i]['pad']) for i in g['pads']]
            xs = [Res['pads'][i]['x'] for i in g['pads']] + [c for i in g['tracks'] for c in (Res['tracks'][i]['x1'], Res['tracks'][i]['x2'])] + [Res['vias'][i]['x'] for i in g['vias']]
            ys = [Res['pads'][i]['y'] for i in g['pads']] + [c for i in g['tracks'] for c in (Res['tracks'][i]['y1'], Res['tracks'][i]['y2'])] + [Res['vias'][i]['y'] for i in g['vias']]
            gs.append({'pads': sorted(pads), 'plane': g['plane'], 'tracks': len(g['tracks']), 'vias': len(g['vias']),
                       'bbox': [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)] if xs else None})
        # planar gap between the islands (any layers): how far the router has to bridge
        objs_ = []
        for g in isl[net]:
            o = [('p', Res['pads'][i]) for i in g['pads']] + [('t', Res['tracks'][i]) for i in g['tracks']] +                 [('v', Res['vias'][i]) for i in g['vias']]
            objs_.append(o)
        if len(objs_) == 2 and objs_[0] and objs_[1]:
            best = min((J.gap(ka, a, kb, b), J.desc(ka, a), J.desc(kb, b)) for ka, a in objs_[0] for kb, b in objs_[1])
            gs.append({'planar_gap_mm': round(best[0], 3), 'between': best[1:]})
        detail[net] = gs
    rep['open_islands'] = detail
    # base_cur / base_new opens for reference
    rep['open_base_cur'] = dict(sorted(C.open_count(C.islands(Bc)).items()))
    rep['open_base_new'] = sum(C.open_count(C.islands(Bn)).values())
    # full-board DRC, NEW vs base_cur
    v_res = J.drc(Res)
    v_cur = J.drc(Bc)
    new = {k: s for k, s in v_res.items() if k not in v_cur}
    rep['drc_counts'] = {'base_cur': len(v_cur), 'result': len(v_res), 'new_vs_base_cur': len(new)}
    rep['drc_new'] = sorted(new.values())
    # via in SMD pad
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
    rep['uvia_in_smd_pad_new'] = uv_new
    rep['new_through_vias'] = [J.desc('v', v) for v in newv if v['span'] == STACK]
    rep['usb'] = J.usb_metrics(Res)
    rep['counts'] = {'remove_tracks': len(P['remove']), 'remove_vias': len(P['remove_vias']), 'add_tracks': len(P['tracks']),
                     'add_vias': len(P['vias']), 'vias_added_by_type': dict(Counter(J.vkind(v) for v in newv)),
                     'vias_removed_by_type': dict(Counter(J.vkind(dict(v, span=J.span(v))) for v in P['remove_vias'])),
                     'result_tracks': len(Res['tracks']), 'result_vias': len(Res['vias']), 'result_pads': len(Res['pads'])}
    json.dump(rep, open(os.path.join(PREP, 'check%s.json' % tag), 'w'), indent=1, default=str)
    show = {k: v for k, v in rep.items() if k not in ('open_islands', 'usb', 'dead_after')}
    show['dead_after'] = {k: len(v) for k, v in rep['dead_after'].items()}
    show['usb'] = {k: v for k, v in rep['usb'].items() if k != 'geom'}
    print(json.dumps(show, indent=1, default=str))


if __name__ == '__main__':
    main()
