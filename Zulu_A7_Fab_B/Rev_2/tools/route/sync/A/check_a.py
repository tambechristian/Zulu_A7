"""check_a.py <plan.json> <tag>   -- Strategy A full gate of ONE emit-ready plan relative to TARGET's current copper.

The plan = prep/transplant.json merged with the Strategy-A routing (remove / remove_vias / tracks / vias, moves: []).
  1. emit-readiness (judge.emit_match, emit_copper's own matching) on base_cur AND base_new: every remove line hits
     exactly one board object, Kill counts == list lengths;
  2. result = base_new - removals + additions  -> A/result_<tag>.json;
  3. route_check.py <plan> base_new in-process with SDRAM-D0..D15 in the SDRAM rule set (0.10 L3/L4 clearance,
     0.10 width L3/L4/Bottom) AND TARGET's unpatched CLI (subprocess);
  4. prune_stubs (TARGET's CLI on the result) and route_conn (TARGET's CLI on the result);
  5. widthcheck.py <TARGET PcbDoc> <plan> prep/extra_classes.json;
  6. full-board exact DRC (judge.drc with the SDRAM-Dn patch) on the result vs base_cur: NEW violations;
  7. through via whose land overlaps any SMD pad (must be 0); microvias in SMD pads (allowed) new vs base_cur;
  8. USB pair metrics, Pmod (JA*/PMOD*) nets touched, counts by span, added length, plane web (planeweb.run).
Writes A/check_<tag>.json and prints a summary.
"""
import contextlib
import io
import json
import math
import os
import subprocess
import sys
from collections import Counter

A = os.path.dirname(os.path.abspath(__file__))
PREP = os.path.join(os.path.dirname(A), 'prep')
sys.path.insert(0, os.path.join(PREP, 'scripts'))
import geo  # noqa: E402  (patches router.SDRAM with SDRAM-D0..15 for every in-process check)

J, C, PS, R = geo.J, geo.C, geo.PS, geo.R
TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
PCB = TOOLS + '/../Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc'
STACK = J.STACK


def run(cmd):
    p = subprocess.run(cmd, cwd=TOOLS, capture_output=True, text=True)
    return (p.stdout + p.stderr).splitlines(), p.returncode


def main():
    plan_path = os.path.abspath(sys.argv[1])
    tag = sys.argv[2]
    P = json.load(open(plan_path))
    Bc = json.load(open(os.path.join(PREP, 'base_cur.json')))
    Bn = json.load(open(os.path.join(PREP, 'base_new.json')))
    for M in (Bc, Bn):
        for v in M['vias']:
            v['span'] = J.span(v)
    rep = {'plan': plan_path}
    _, _, probs0 = J.emit_match(Bc, P)
    kt, kv, probs = J.emit_match(Bn, P)
    rep['emit_problems_base_cur'] = probs0
    rep['emit_problems_base_new'] = probs
    newv = [dict(v, span=J.span(v)) for v in P['vias']]
    Res = {'board': Bn['board'], 'planes': Bn['planes'], 'pads': Bn['pads'],
           'tracks': [t for i, t in enumerate(Bn['tracks']) if i not in kt] + [dict(t) for t in P['tracks']],
           'vias': [v for i, v in enumerate(Bn['vias']) if i not in kv] + newv}
    res_path = os.path.join(A, 'result_%s.json' % tag)
    json.dump(Res, open(res_path, 'w'))
    # duplicates
    tk = Counter(J.tkey(t) for t in Res['tracks'])
    vk = Counter(J.vkey(v) for v in Res['vias'])
    rep['dup_tracks_result'] = sum(c - 1 for c in tk.values() if c > 1)
    rep['dup_vias_result'] = sum(c - 1 for c in vk.values() if c > 1)
    rep['zero_len_tracks_plan'] = sum(1 for t in P['tracks'] if J.tlen(t) < 1e-6)
    # route_check in-process (patched)
    import route_check as RC
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv[:] = ['route_check.py', plan_path, os.path.join(PREP, 'base_new.json')]
    with contextlib.redirect_stdout(buf):
        rc = RC.main()
    sys.argv[:] = argv
    rep['route_check_sdramdn'] = buf.getvalue().splitlines()
    rep['route_check_sdramdn_pass'] = rc == 0
    out, rc2 = run(['python', 'route_check.py', plan_path, os.path.join(PREP, 'base_new.json')])
    rep['route_check_official'] = out
    out, _ = run(['python', 'prune_stubs.py', res_path])
    rep['prune_stubs'] = out[-3:]
    out, _ = run(['python', 'route_conn.py', res_path])
    rep['route_conn'] = out[-5:]
    out, _ = run(['python', 'widthcheck.py', PCB, plan_path, os.path.join(PREP, 'extra_classes.json')])
    rep['widthcheck'] = out[-12:]
    # in-process dead / opens too
    dt, dv, _, _ = PS.analyse(Res)
    rep['dead_after'] = {'tracks': len(dt), 'vias': len(dv)}
    oc = C.open_count(C.islands(Res))
    rep['open_total'] = sum(oc.values())
    rep['open_by_net'] = dict(sorted(oc.items()))
    # full DRC new vs base_cur
    v_res = J.drc(Res)
    v_cur = J.drc(Bc)
    new = {k: s for k, s in v_res.items() if k not in v_cur}
    rep['drc_counts'] = {'base_cur': len(v_cur), 'result': len(v_res), 'new_vs_base_cur': len(new),
                         'fixed_vs_base_cur': sum(1 for k in v_cur if k not in v_res)}
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
    rep['uvia_in_smd_pad_new_count'] = len(uv_new)
    rep['uvia_in_smd_pad_new'] = uv_new
    rep['new_through_vias'] = [J.desc('v', v) for v in newv if v['span'] == STACK]
    # USB
    u = J.usb_metrics(Res)
    rep['usb'] = {k: v for k, v in u.items() if k != 'geom'}
    src = json.load(open(os.path.join(PREP, 'after_transplant.json')))
    rep['usb']['identical_to_after_transplant'] = u['geom'] == J.usb_metrics(src)['geom']
    # Pmod nets touched
    pm = lambda n: n.startswith('JA') or 'PMOD' in n  # noqa: E731
    rep['pmod_touched'] = {
        'removed_tracks': sorted({t['net'] for t in P['remove'] if pm(t['net'])}),
        'removed_vias': sorted({v['net'] for v in P['remove_vias'] if pm(v['net'])}),
        'added_tracks': sorted({t['net'] for t in P['tracks'] if pm(t['net'])}),
        'added_vias': sorted({v['net'] for v in P['vias'] if pm(v['net'])}),
        'n': sum(1 for t in P['remove'] + P['tracks'] if pm(t['net'])) + sum(1 for v in P['remove_vias'] + P['vias'] if pm(v['net']))}
    # counts
    rm_tk = Counter(J.tkey(t) for t in P['remove'])
    rep['counts'] = {
        'remove_tracks': len(P['remove']), 'remove_vias': len(P['remove_vias']), 'add_tracks': len(P['tracks']),
        'add_vias': len(P['vias']),
        'vias_added_by_type': dict(sorted(Counter(J.vkind(v) for v in newv).items())),
        'vias_removed_by_type': dict(sorted(Counter(J.vkind(dict(v, span=J.span(v))) for v in P['remove_vias']).items())),
        'tracks_added_by_layer': dict(sorted(Counter(t['layer'] for t in P['tracks']).items())),
        'tracks_removed_by_layer': dict(sorted(Counter(t['layer'] for t in P['remove']).items())),
        'added_track_mm': round(sum(map(J.tlen, P['tracks'])), 2),
        'removed_track_mm': round(sum(map(J.tlen, P['remove'])), 2),
        'added_track_mm_excl_readded': round(sum(J.tlen(t) for t in P['tracks'] if J.tkey(t) not in rm_tk), 2),
        'result_tracks': len(Res['tracks']), 'result_vias': len(Res['vias']), 'result_pads': len(Res['pads']),
        'result_via_types': dict(sorted(Counter(J.vkind(v) for v in Res['vias']).items()))}
    if len(sys.argv) > 3 and sys.argv[3] == '--planeweb':
        sys.path.insert(0, os.path.join(TOOLS, 'route', 'rev2', 'judge'))
        import planeweb as PW
        rep['planeweb_result'] = PW.run(Res, tag)
        rep['planeweb_base_cur'] = PW.run(Bc, 'cur')
    json.dump(rep, open(os.path.join(A, 'check_%s.json' % tag), 'w'), indent=1, default=str)
    show = {k: v for k, v in rep.items() if k not in ('uvia_in_smd_pad_new', 'planeweb_result', 'planeweb_base_cur')}
    print(json.dumps(show, indent=1, default=str))
    if 'planeweb_result' in rep:
        for nm in ('planeweb_base_cur', 'planeweb_result'):
            for layer, res in rep[nm].items():
                for mode, r in res.items():
                    print(nm, layer, mode, 'comps', r['components'], 'w/objs', r['components_with_net_objects'],
                          'main mm2', r['main_area_mm2'], 'objs', r['objects'], 'off-main', r['objects_off_main'])


if __name__ == '__main__':
    main()
