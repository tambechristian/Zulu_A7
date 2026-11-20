"""Independent judge of one Fab B Rev 2 sync plan (candidate A/B/C).

    python judge_sync.py <plan.json> <out_dir>

Gates (all re-run here, nothing taken from the candidate's own files):
  G1 emit-readiness on base_cur AND base_new: judge.emit_match (emit_copper's rules) + an independent re-count
     (each remove line hits exactly one object, no object hit by two lines), native 0.1 um keys (native_keys.py CLI)
  G2 route_check.py CLI (TARGET, unpatched) vs base_new; in-process with SDRAM-D0..15 in the SDRAM rule set
  G3 widthcheck.py CLI with TARGET's PcbDoc + prep/extra_classes.json
  G4 result = base_new - emit-matched + plan; prune_stubs.py CLI + route_conn.py CLI on it
  G5 judge.py CLI (official) base_new vs base_cur; plus full exact DRC in-process with the SDRAM-Dn patch: NEW vs base_cur
  G6 through via land overlapping / touching any SMD pad (U1 lands round) -- two independent overlap tests
  G7 planeweb.run on the result (L2 / L5)
  G8 USB metrics + geometry equality with SOURCE HEAD
  G9 SDRAM DQ topology vs SOURCE HEAD (pads per net, one island each, copper geometry)
  plus: Pmod-net disturbance, counts, Altium-step facts (plane-net removals, microvias to mark, transient shorts at
  the moved / new parts between placement and emit, emit guard).
"""
import contextlib
import io
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools'
SYNC = TOOLS + '/route/sync'
PREP = SYNC + '/prep'
PCB = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc'
JUDGE_DIR = TOOLS + '/route/rev2/judge'
sys.path.insert(0, TOOLS)
sys.path.insert(0, JUDGE_DIR)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402
import prune_stubs as PS  # noqa: E402
import judge as J  # noqa: E402

STACK = R.STACK
PMOD = re.compile(r'^(JA\d+|PMOD-\d+)$')
PLANE_NETS = ('GND', 'VCC3V3')
PY = sys.executable


def run(cmd, out_txt, cwd=TOOLS):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    txt = r.stdout + (('\n[stderr]\n' + r.stderr) if r.stderr.strip() else '')
    open(out_txt, 'w').write(txt)
    return r.returncode, txt


def span(v):
    return J.span(v)


def tlen(t):
    return math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])


def k3t(t):
    a = (round(t['x1'], 3), round(t['y1'], 3))
    b = (round(t['x2'], 3), round(t['y2'], 3))
    return (t['net'], t['layer'], round(t['w'], 3)) + tuple(sorted((a, b)))


def k3v(v):
    s = span(v)
    return (v['net'], round(v['x'], 3), round(v['y'], 3), round(v['size'], 3), round(v['hole'], 3), s[0], s[-1])


def indep_emit(B, P):
    """independent re-count of emit_copper's matching: per line hits, per object hits"""
    probs = []
    by = defaultdict(list)
    for j, t in enumerate(B['tracks']):
        by[(t['net'], t['layer'])].append(j)
    obj_hits = Counter()
    for r in P['remove']:
        h = []
        for j in by.get((r['net'], r['layer']), ()):
            t = B['tracks'][j]
            if abs(t['w'] - r['w']) >= 0.002:
                continue
            f = all(abs(a - b) < 0.002 for a, b in zip((t['x1'], t['y1'], t['x2'], t['y2']), (r['x1'], r['y1'], r['x2'], r['y2'])))
            g = all(abs(a - b) < 0.002 for a, b in zip((t['x1'], t['y1'], t['x2'], t['y2']), (r['x2'], r['y2'], r['x1'], r['y1'])))
            if f or g:
                h.append(j)
        if len(h) != 1:
            probs.append('track line hits %d: %s' % (len(h), r))
        obj_hits.update(('t', j) for j in h)
    vb = defaultdict(list)
    for j, v in enumerate(B['vias']):
        vb[v['net']].append(j)
    for r in P['remove_vias']:
        rs = span(r)
        h = [j for j in vb.get(r['net'], ()) if abs(B['vias'][j]['hole'] - r['hole']) < 0.002 and
             abs(B['vias'][j]['x'] - r['x']) < 0.002 and abs(B['vias'][j]['y'] - r['y']) < 0.002 and
             span(B['vias'][j])[0] == rs[0] and span(B['vias'][j])[-1] == rs[-1]]
        if len(h) != 1:
            probs.append('via line hits %d: %s' % (len(h), r))
        obj_hits.update(('v', j) for j in h)
    multi = [k for k, c in obj_hits.items() if c > 1]
    if multi:
        probs.append('%d board objects hit by several lines' % len(multi))
    return probs


def pad_land_overlap(v, p):
    """distance-based overlap of a via land (circle) with pad copper; U1 lands round. returns penetration (>0 overlap)"""
    r = v['size'] / 2
    if C.pad_round(p):
        d = math.hypot(v['x'] - p['x'], v['y'] - p['y']) - min(p['w'], p['h']) / 2
    else:
        d = math.hypot(max(abs(v['x'] - p['x']) - p['w'] / 2, 0), max(abs(v['y'] - p['y']) - p['h'] / 2, 0))
    return r - d


def main():
    plan_path, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    P = json.load(open(plan_path))
    Bc = json.load(open(PREP + '/base_cur.json'))
    Bn = json.load(open(PREP + '/base_new.json'))
    S = json.load(open(PREP + '/models/src_427960e.json'))
    for M in (Bc, Bn, S):
        for v in M['vias']:
            v['span'] = span(v)
    rep = {'plan': plan_path}
    rep['md5'] = subprocess.run(['md5sum', plan_path], capture_output=True, text=True).stdout.split()[0]
    rep['moves'] = len(P.get('moves', []))

    # ---------------- CLIs first (unpatched TARGET tools, separate process; at most 2 python processes alive)
    rc, txt = run([PY, 'route_check.py', plan_path, PREP + '/base_new.json'], out + '/route_check_official.txt')
    rep['G2_route_check_official'] = {'rc': rc, 'tail': txt.strip().splitlines()[-4:]}
    rc, txt = run([PY, 'widthcheck.py', PCB, plan_path, PREP + '/extra_classes.json'], out + '/widthcheck.txt')
    rep['G3_widthcheck'] = {'rc': rc, 'tail': txt.strip().splitlines()[-3:]}
    rc, txt = run([PY, PREP + '/scripts/native_keys.py', plan_path], out + '/native_keys.txt')
    rep['G1_native_keys'] = {'rc': rc, 'out': txt.strip().splitlines()[:5]}

    # ---------------- G1 emit
    kt0, kv0, pr0 = J.emit_match(Bc, P)
    kt, kv, pr = J.emit_match(Bn, P)
    rep['G1_emit'] = {'judge_base_cur': pr0, 'judge_base_new': pr, 'indep_base_cur': indep_emit(Bc, P),
                      'indep_base_new': indep_emit(Bn, P), 'kill_tracks': len(kt), 'kill_vias': len(kv)}
    rep['G1_emit']['same_kill_sets_cur_new'] = (kt0 == kt and kv0 == kv)
    # plan duplicates
    rep['G1_plan_dup'] = {
        'remove_tracks_dup3': len(P['remove']) - len({k3t(t) for t in P['remove']}),
        'remove_vias_dup3': len(P['remove_vias']) - len({k3v(v) for v in P['remove_vias']}),
        'add_tracks_dup3': len(P['tracks']) - len({k3t(t) for t in P['tracks']}),
        'add_vias_dup3': len(P['vias']) - len({k3v(v) for v in P['vias']}),
        'zero_len_add': sum(1 for t in P['tracks'] if tlen(t) < 1e-6),
        'short_add_lt_0.01': sum(1 for t in P['tracks'] if tlen(t) < 0.01)}

    # ---------------- result model
    newv = [dict(v, span=span(v)) for v in P['vias']]
    for v in newv:
        v.pop('from', None)
        v.pop('to', None)
    Res = {'board': Bn['board'], 'planes': Bn['planes'], 'pads': Bn['pads'],
           'tracks': [t for i, t in enumerate(Bn['tracks']) if i not in kt] + [dict(t) for t in P['tracks']],
           'vias': [v for i, v in enumerate(Bn['vias']) if i not in kv] + newv}
    res_path = out + '/result.json'
    json.dump(Res, open(res_path, 'w'))
    rc, txt = run([PY, 'prune_stubs.py', res_path], out + '/prune.txt')
    rep['G4_prune_official'] = txt.strip().splitlines()[-1:]
    rc, txt = run([PY, 'route_conn.py', res_path], out + '/route_conn.txt')
    rep['G4_route_conn_official'] = txt.strip().splitlines()
    rc, txt = run([PY, JUDGE_DIR + '/judge.py', PREP + '/base_new.json', PREP + '/base_cur.json', plan_path, out + '/judge_official'],
                  out + '/judge_official.txt')
    try:
        jo = json.load(open(out + '/judge_official/judge.json'))
        rep['G5_judge_official'] = {'emit_problems': len(jo['emit_problems']), 'open_exact': jo['open_exact'],
                                    'drc_counts': jo['drc_counts'], 'drc_new': jo['drc_new'][:20],
                                    'through_via_in_smd_pad': jo['through_via_in_smd_pad_result'],
                                    'uvia_in_smd_pad_total': jo['uvia_in_smd_pad_result_total'],
                                    'uvia_in_smd_pad_new': len(jo['uvia_in_smd_pad_new']),
                                    'dup_tracks_result': jo['dup_tracks_result'], 'dup_vias_result': jo['dup_vias_result']}
    except Exception as e:  # noqa: BLE001
        rep['G5_judge_official'] = 'FAILED %r' % e

    # ---------------- patched rules from here on (SDRAM-D0..15 in the SDRAM set, as SOURCE)
    R.SDRAM |= {'SDRAM-D%d' % i for i in range(16)}
    import route_check as RC
    buf = io.StringIO()
    argv = sys.argv[:]
    sys.argv[:] = ['route_check.py', plan_path, PREP + '/base_new.json']
    with contextlib.redirect_stdout(buf):
        rcc = RC.main()
    sys.argv[:] = argv
    open(out + '/route_check_sdram.txt', 'w').write(buf.getvalue())
    rep['G2_route_check_sdram'] = {'rc': rcc, 'tail': buf.getvalue().strip().splitlines()[-4:]}

    dt, dv, nt, nv = PS.analyse(Res)
    rep['G4_dead'] = {'tracks': len(dt), 'vias': len(dv)}
    isl = C.islands(Res)
    oc = C.open_count(isl)
    rep['G4_open'] = {'total': sum(oc.values()), 'by_net': oc}

    v_res = J.drc(Res)
    v_cur = J.drc(Bc)
    new = {k: s for k, s in v_res.items() if k not in v_cur}
    rep['G5_drc_sdram'] = {'base_cur': len(v_cur), 'result': len(v_res), 'new': len(new), 'new_list': sorted(new.values())[:30],
                           'fixed': sum(1 for k in v_cur if k not in v_res)}
    # duplicates new vs base_cur
    bt = Counter(k3t(t) for t in Bc['tracks'])
    bv = Counter(k3v(v) for v in Bc['vias'])
    rt_ = Counter(k3t(t) for t in Res['tracks'])
    rv_ = Counter(k3v(v) for v in Res['vias'])
    rep['dup_new_vs_base'] = {'tracks': sum(max(0, c - max(1, bt.get(k, 1))) for k, c in rt_.items() if c > 1),
                              'vias': sum(max(0, c - max(1, bv.get(k, 1))) for k, c in rv_.items() if c > 1)}

    # ---------------- G6 via in SMD pad
    smd = [p for p in Res['pads'] if not p['drill']]
    smd0 = [p for p in Bc['pads'] if not p['drill']]
    th_over, th_touch, uv_all, uv_list = [], [], 0, []
    old_uv = {k3v(v) for v in Bc['vias'] if v['span'] != STACK and J.via_pad_hits(v, smd0)}
    for v in Res['vias']:
        hits = [(p, pad_land_overlap(v, p)) for p in smd if set(p['layers']) & set(v['span'])]
        hits = [(p, d) for p, d in hits if d > -0.001]
        if not hits:
            continue
        if v['span'] == STACK:
            for p, d in hits:
                rec = (J.desc('v', v), '%s-%s(%s)' % (p['ref'], p['pad'], p['net']), round(d, 4))
                (th_over if d > 1e-6 else th_touch).append(rec)
        else:
            if any(d > 1e-4 for p, d in hits):
                uv_all += 1
                if k3v(v) not in old_uv:
                    uv_list.append((J.desc('v', v), ['%s-%s(%s)' % (p['ref'], p['pad'], p['net']) for p, d in hits if d > 1e-4]))
    # second, independent test: judge.via_pad_hits
    th2 = [J.desc('v', v) for v in Res['vias'] if v['span'] == STACK and J.via_pad_hits(v, smd)]
    rep['G6_via_in_pad'] = {'through_overlap': th_over, 'through_touch_within_1um': th_touch, 'through_judge_hits': th2,
                            'uvia_in_smd_total': uv_all, 'uvia_in_smd_new': len(uv_list), 'uvia_in_smd_new_list': uv_list}

    # ---------------- G7 plane web
    import planeweb as PW
    rep['G7_planeweb'] = PW.run(Res, 'result')

    # ---------------- G8 USB
    u = J.usb_metrics(Res)
    us = J.usb_metrics(S)
    rep['G8_usb'] = {k: v for k, v in u.items() if k != 'geom'}
    rep['G8_usb']['geom_equals_source_head'] = u['geom'] == us['geom']

    # ---------------- G9 SDRAM DQ topology vs SOURCE HEAD
    isl_s = C.islands(S)
    dq = {}
    ok = True
    for n in range(16):
        for net in ('D%d' % n, 'SDRAM-D%d' % n):
            pr_ = sorted('%s-%s' % (Res['pads'][i]['ref'], Res['pads'][i]['pad']) for g in isl.get(net, []) for i in g['pads'])
            ps_ = sorted('%s-%s' % (S['pads'][i]['ref'], S['pads'][i]['pad']) for g in isl_s.get(net, []) for i in g['pads'])
            ni = len(isl.get(net, []))
            pos_r = sorted((p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3)) for p in Res['pads'] if p['net'] == net)
            pos_s = sorted((p['ref'], p['pad'], round(p['x'], 3), round(p['y'], 3)) for p in S['pads'] if p['net'] == net)
            cr = Counter([k3t(t) for t in Res['tracks'] if t['net'] == net] + [k3v(v) for v in Res['vias'] if v['net'] == net])
            cs = Counter([k3t(t) for t in S['tracks'] if t['net'] == net] + [k3v(v) for v in S['vias'] if v['net'] == net])
            refs = {x.split('-')[0] for x in pr_}
            if net.startswith('D'):
                shape_ok = len(pr_) == 2 and 'U1' in refs and any(x.startswith('R1') and x.endswith('-2') for x in pr_)
            else:
                shape_ok = len(pr_) == 2 and 'U3' in refs and any(x.startswith('R1') and x.endswith('-1') for x in pr_)
            e = {'pads': pr_, 'islands': ni, 'pads_eq_source': pr_ == ps_, 'pad_pos_eq_source': pos_r == pos_s,
                 'copper_eq_source': cr == cs, 'copper_only_result': sum((cr - cs).values()),
                 'copper_only_source': sum((cs - cr).values()), 'shape_ok': shape_ok}
            if not (ni == 1 and pr_ == ps_ and pos_r == pos_s and shape_ok):
                ok = False
            dq[net] = e
    rep['G9_dq'] = {'ok': ok, 'copper_identical_all': all(e['copper_eq_source'] for e in dq.values()), 'nets': dq}

    # ---------------- Pmod disturbance
    pm_rm_t = [t for t in P['remove'] if PMOD.match(t['net'])]
    pm_rm_v = [v for v in P['remove_vias'] if PMOD.match(v['net'])]
    pm_ad_t = [t for t in P['tracks'] if PMOD.match(t['net'])]
    pm_ad_v = [v for v in P['vias'] if PMOD.match(v['net'])]
    pc = Counter([k3t(t) for t in Bc['tracks'] if PMOD.match(t['net'])] + [k3v(v) for v in Bc['vias'] if PMOD.match(v['net'])])
    pr2 = Counter([k3t(t) for t in Res['tracks'] if PMOD.match(t['net'])] + [k3v(v) for v in Res['vias'] if PMOD.match(v['net'])])
    pmod_pads_same = sorted((p['ref'], p['pad'], p['net'], p['x'], p['y']) for p in Bc['pads'] if p['ref'] == 'J1' or re.match(r'R(2[6-9]|3[0-3])$', p['ref'])) == \
        sorted((p['ref'], p['pad'], p['net'], p['x'], p['y']) for p in Res['pads'] if p['ref'] == 'J1' or re.match(r'R(2[6-9]|3[0-3])$', p['ref']))
    rep['pmod'] = {'nets_touched': sorted({o['net'] for o in pm_rm_t + pm_rm_v + pm_ad_t + pm_ad_v}),
                   'removed_tracks': len(pm_rm_t), 'removed_vias': len(pm_rm_v), 'added_tracks': len(pm_ad_t), 'added_vias': len(pm_ad_v),
                   'result_copper_equals_base_cur': pc == pr2, 'J1_R26_R33_pads_unchanged': pmod_pads_same,
                   'JP3_JP4_pads_unchanged': sorted((p['ref'], p['pad'], p['net'], p['x'], p['y']) for p in Bc['pads'] if p['ref'] in ('JP3', 'JP4')) ==
                   sorted((p['ref'], p['pad'], p['net'], p['x'], p['y']) for p in Res['pads'] if p['ref'] in ('JP3', 'JP4'))}

    # ---------------- counts
    vk = Counter(J.vkind(v) for v in newv)
    rk = Counter(J.vkind(v) for v in P['remove_vias'])
    T0 = json.load(open(PREP + '/transplant.json'))
    t0_rm = Counter(k3t(t) for t in T0['remove']) + Counter(k3v(v) for v in T0['remove_vias'])
    p_rm = Counter(k3t(t) for t in P['remove']) + Counter(k3v(v) for v in P['remove_vias'])
    t0_add = Counter(k3t(t) for t in T0['tracks']) + Counter(k3v(v) for v in T0['vias'])
    p_add = Counter(k3t(t) for t in P['tracks']) + Counter(k3v(v) for v in P['vias'])
    extra_rm = p_rm - t0_rm
    kept = t0_rm - p_rm
    rep['counts'] = {
        'remove_tracks': len(P['remove']), 'remove_vias': len(P['remove_vias']),
        'add_tracks': len(P['tracks']), 'add_vias': len(P['vias']),
        'add_track_mm': round(sum(map(tlen, P['tracks'])), 2), 'remove_track_mm': round(sum(map(tlen, P['remove'])), 2),
        'vias_added_by_type': dict(sorted(vk.items())), 'vias_removed_by_type': dict(sorted(rk.items())),
        'added_tracks_by_layer': dict(Counter(t['layer'] for t in P['tracks'])),
        'removed_tracks_by_layer': dict(Counter(t['layer'] for t in P['remove'])),
        'vs_clean_transplant': {
            'extra_removals_beyond_transplant': sum(extra_rm.values()),
            'extra_removal_track_mm': round(sum(tlen(t) for t in P['remove'] if extra_rm.get(k3t(t))), 2),
            'transplant_removals_kept_on_board': sum(kept.values()),
            'adds_not_in_transplant': sum((p_add - t0_add).values()),
            'transplant_adds_not_in_plan': sum((t0_add - p_add).values()),
            'add_vias_beyond_transplant': len(P['vias']) - len(T0['vias']),
            'add_mm_beyond_transplant': round(sum(map(tlen, P['tracks'])) - sum(map(tlen, T0['tracks'])), 2)},
        'extra_removal_nets': dict(Counter(k[0] for k in extra_rm.elements())),
        'result': {'tracks': len(Res['tracks']), 'vias': len(Res['vias']), 'track_mm': round(sum(map(tlen, Res['tracks'])), 2)},
        'base_cur': {'tracks': len(Bc['tracks']), 'vias': len(Bc['vias']), 'track_mm': round(sum(map(tlen, Bc['tracks'])), 2)}}
    # nets changed vs SOURCE-identical transplant result
    A0 = json.load(open(PREP + '/after_transplant.json'))
    ca = defaultdict(Counter)
    for t in A0['tracks']:
        ca[t['net']][k3t(t)] += 1
    for v in A0['vias']:
        ca[v['net']][k3v(dict(v, span=span(v)))] += 1
    cr = defaultdict(Counter)
    for t in Res['tracks']:
        cr[t['net']][k3t(t)] += 1
    for v in Res['vias']:
        cr[v['net']][k3v(v)] += 1
    rep['nets_differing_from_clean_after_transplant'] = sorted(n for n in set(ca) | set(cr) if ca[n] != cr[n])

    # ---------------- Altium-step facts
    pl_rm_t = Counter((t['net'], t['layer']) for t in P['remove'] if t['net'] in PLANE_NETS)
    pl_rm_v = Counter((v['net'], J.vkind(v)) for v in P['remove_vias'] if v['net'] in PLANE_NETS)
    pl_ad_v = Counter((v['net'], J.vkind(v)) for v in newv if v['net'] in PLANE_NETS)
    l2l5_rm = sum(1 for v in P['remove_vias'] if 'L2-GND' in span(v) or 'L5-VCC3V3' in span(v))
    l2l5_ad = sum(1 for v in newv if 'L2-GND' in v['span'] or 'L5-VCC3V3' in v['span'])
    laser = [v for v in newv if v['span'] != STACK and v['span'] != ['L3-SIG', 'L4-SIG']]
    laser_cls = Counter((round(v['size'], 3), round(v['hole'], 3), v['span'][0], v['span'][-1]) for v in laser)
    buried_cls = Counter((round(v['size'], 3), round(v['hole'], 3)) for v in newv if v['span'] == ['L3-SIG', 'L4-SIG'])
    thr_cls = Counter((round(v['size'], 3), round(v['hole'], 3)) for v in newv if v['span'] == STACK)
    not_markable = [J.desc('v', v) for v in laser if (round(v['size'], 3), round(v['hole'], 3)) not in ((0.3, 0.15), (0.25, 0.1))]
    # new vias at the exact point of a via that stays (stack onto kept copper) and emit_copper's guard via
    kept_vias = [v for i, v in enumerate(Bc['vias']) if i not in kv0]
    kp = defaultdict(list)
    for v in kept_vias:
        kp[(round(v['x'], 3), round(v['y'], 3))].append(v)
    on_kept = [(J.desc('v', v), [J.desc('v', o) for o in kp[(round(v['x'], 3), round(v['y'], 3))]]) for v in newv
               if (round(v['x'], 3), round(v['y'], 3)) in kp]
    free = [v for v in P['vias'] if not any(abs(v['x'] - r['x']) < 0.02 and abs(v['y'] - r['y']) < 0.02 for r in P['remove_vias'])]
    g0 = free[0] if free else None
    guard_block = [J.desc('v', o) for o in Bc['vias'] if g0 and abs(o['x'] - g0['x']) < 0.000762 and abs(o['y'] - g0['y']) < 0.000762]
    rep['altium'] = {'plane_net_track_removals': {'%s %s' % k: c for k, c in sorted(pl_rm_t.items())},
                     'plane_net_via_removals': {'%s %s' % k: c for k, c in sorted(pl_rm_v.items())},
                     'plane_net_via_additions': {'%s %s' % k: c for k, c in sorted(pl_ad_v.items())},
                     'vias_through_L2_or_L5_removed': l2l5_rm, 'vias_through_L2_or_L5_added': l2l5_ad,
                     'laser_vias_added_to_mark': len(laser), 'laser_classes': {'%s/%s %s>%s' % k: c for k, c in sorted(laser_cls.items())},
                     'laser_not_markable_by_mark_microvias': not_markable,
                     'buried_added': {'%s/%s' % k: c for k, c in buried_cls.items()}, 'through_added': {'%s/%s' % k: c for k, c in thr_cls.items()},
                     'new_vias_on_kept_via_points': on_kept, 'emit_copper_guard_via': J.desc('v', dict(g0, span=span(g0))) if g0 else None,
                     'emit_copper_guard_blocked_by': guard_block}
    # transient: base_new (placed parts, old copper) DRC new vs base_cur, by part
    v_bn = J.drc(Bn)
    trans = {k: s for k, s in v_bn.items() if k not in v_cur}
    MOVED = ['U2', 'X4', 'U10', 'U4', 'R34', 'C87', 'C88', 'C94', 'C99', 'C106', 'R1'] + ['R%d' % i for i in range(119, 135)] + ['U3']
    per = Counter()
    for s in trans.values():
        for m in MOVED:
            if re.search(r'(^|[ |])%s-' % re.escape(m), s):
                per[m] += 1
    # are all base_cur objects behind those transient violations removed by the plan?
    rm_ids_t = {k3t(Bc['tracks'][i]) for i in kt0}
    rm_ids_v = {k3v(Bc['vias'][i]) for i in kv0}
    survive = []
    for key, s in trans.items():
        if key[0] != 'clr':
            continue
        for ok_ in key[2]:
            if ok_[0] == 't':
                kk = (ok_[1], ok_[2], round(ok_[3], 3)) + tuple(ok_[4])
                if kk not in rm_ids_t and kk in {k3t(t) for t in Res['tracks']}:
                    survive.append(s)
    # copper of other nets that sits inside a moved / new part's pad hull on its own side, in the RESULT
    inside = {}
    for m in MOVED:
        pads = [p for p in Res['pads'] if p['ref'] == m]
        if not pads:
            continue
        x0 = min(p['x'] - p['w'] / 2 for p in pads)
        x1 = max(p['x'] + p['w'] / 2 for p in pads)
        y0 = min(p['y'] - p['h'] / 2 for p in pads)
        y1 = max(p['y'] + p['h'] / 2 for p in pads)
        side = pads[0]['layers'][0] if pads[0]['layers'] else 'Top Layer'
        kept_t = sum(1 for i, t in enumerate(Bn['tracks']) if i not in kt and t['layer'] == side and
                     min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0)
        add_t = sum(1 for t in P['tracks'] if t['layer'] == side and
                    min(t['x1'], t['x2']) < x1 and max(t['x1'], t['x2']) > x0 and min(t['y1'], t['y2']) < y1 and max(t['y1'], t['y2']) > y0)
        kept_v = sum(1 for i, v in enumerate(Bn['vias']) if i not in kv and side in v['span'] and x0 < v['x'] < x1 and y0 < v['y'] < y1)
        add_v = sum(1 for v in newv if side in v['span'] and x0 < v['x'] < x1 and y0 < v['y'] < y1)
        inside[m] = {'side': side, 'hull': [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
                     'kept_tracks': kept_t, 'kept_vias': kept_v, 'added_tracks': add_t, 'added_vias': add_v,
                     'transient_violations': per.get(m, 0)}
    rep['altium']['transient_violations_after_placement_before_emit'] = len(trans)
    rep['altium']['transient_by_part'] = dict(per)
    rep['altium']['transient_track_objects_not_removed'] = survive[:10]
    rep['altium']['moved_part_hulls'] = inside
    rep['altium']['through_vias_in_result'] = sum(1 for v in Res['vias'] if v['span'] == STACK)

    json.dump(rep, open(out + '/judge_sync.json', 'w'), indent=1, default=str)
    short = {k: v for k, v in rep.items() if k not in ('G7_planeweb', 'G9_dq', 'altium')}
    short['G9_dq'] = {k: v for k, v in rep['G9_dq'].items() if k != 'nets'}
    short['G7_planeweb'] = {l: {m: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in r.items()} for m, r in d.items()}
                            for l, d in rep['G7_planeweb'].items()}
    print(json.dumps(short, indent=1, default=str))


if __name__ == '__main__':
    main()
