"""Write candidates.json: every legal inner-run candidate per net, self-contained (part + plan-format copper delta
against dq_series_r_plan.json md5 f2949630 + occupancy shapes per layer + margins + full-check verdict)."""
import json, glob, hashlib, os
import plan_tools as PT
import lib

HERE = os.path.dirname(os.path.abspath(__file__))
CU = lib.CU
proofs = {}
for fp in glob.glob(os.path.join(HERE, 'proofs', 'proof_*.jsonl')):
    for l in open(fp):
        r = json.loads(l)
        if 'error' not in r:
            proofs[(r['net'], r['i'])] = r
base_md5 = hashlib.md5(open(os.path.join(HERE, 'base_plan_13.json'), 'rb').read()).hexdigest()


def occupancy(c):
    occ = []
    for (L, nn, x1, y1, x2, y2, w, why) in c['add']:
        if why in ('connector', 'piece'):
            occ.append(dict(layer=L, net=nn, kind='track-' + why,
                            capsule=[round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4), round(w / 2, 4)]))
    for v in c['cols']:
        i0, i1 = CU.index(v['frm']), CU.index(v['to'])
        for L in CU[min(i0, i1):max(i0, i1) + 1]:
            occ.append(dict(layer=L, net=v['net'], kind='via land %s>%s' % (v['frm'], v['to']), circle=[v['x'], v['y'], v['size'] / 2]))
        occ.append(dict(layer='drill', net=v['net'], kind='drill %s>%s' % (v['frm'], v['to']), circle=[v['x'], v['y'], 0.075],
                        span=[v['frm'], v['to']]))
    for (x, y), nn, pn in ((c['pad1'], 'SDRAM-' + c['net'], '1'), (c['pad2'], c['net'], '2')):
        occ.append(dict(layer=c['side'], net=nn, kind='R pad %s' % pn,
                        rect=[round(x - 0.15, 4), round(y - 0.15, 4), round(x + 0.15, 4), round(y + 0.15, 4)]))
        occ.append(dict(layer=c['side'] + ' mask', net=nn, kind='mask opening pad %s (+0.05)' % pn,
                        rect=[round(x - 0.2, 4), round(y - 0.2, 4), round(x + 0.2, 4), round(y + 0.2, 4)]))
    cx, cy = (c['pad1'][0] + c['pad2'][0]) / 2, (c['pad1'][1] + c['pad2'][1]) / 2
    horiz = abs(c['pad1'][1] - c['pad2'][1]) < 1e-6
    body = [cx - 0.315, cy - 0.165, cx + 0.315, cy + 0.165] if horiz else [cx - 0.165, cy - 0.315, cx + 0.165, cy + 0.315]
    occ.append(dict(layer=c['side'] + ' component', kind='R0201 pad box (ComponentClearance 0.254 applies)', rect=c['rbox']))
    occ.append(dict(layer=c['side'] + ' component', kind='RC0201 max body 0.63 x 0.33', rect=[round(v, 4) for v in body]))
    for t in c['rm']:
        occ.append(dict(layer=t['layer'], net=c['net'], kind='FREED (removed run copper)',
                        capsule=[t['x1'], t['y1'], t['x2'], t['y2'], t['w'] / 2]))
    return occ


out = dict(
    strategy='inner_run',
    base_plan='si/series_r/dq_series_r_plan.json md5 %s (copy: d13/inner_run/base_plan_13.json)' % base_md5,
    pcbdoc_md5='2a616c1c74f8788a4a1c837c7d76c3b0',
    how_to_combine=('apply ONE candidate per net on top of the 13-R plan with plan_tools.merge(base, [delta, ...]). Each delta '
                    'is self-contained: its own renames of the U3-side stub / first through via / run segments (remove + re-add '
                    'with why=rename), the run cut, connectors, via columns, microvias list, part, renet_pad and net_class_add. '
                    'Candidates of different nets are compatible when their occupancy shapes clear each other by the clearance '
                    'rules (0.10 on L3/L4 for SDRAM nets, 0.09 elsewhere), drills by 0.24 on shared spans, pad mask openings '
                    'by 0.10 and R boxes by 0.254. FREED copper of one candidate may be reused by another. '
                    'pairs_D14_D15.json lists the D14 x D15 pairs checked exactly here; plan.json is proven by the full check.py.'),
    legal_definition=('rules-legal on exact geometry (search.py: every land, pad, drill and connector of the candidate against the '
                      '13-R plan applied to the board, SDRAM-Dn / Dn split included) AND the R box >= 0.254 from every same-side '
                      'component box and body (no R under U2 or U3) AND no visible silk within 0.254 of a pad opening. '
                      'full_check = the unchanged d10/fold/check.py (local copy, memoised before-state only) on base + this candidate alone.'),
    nets={})
for net in ('D13', 'D14', 'D15'):
    pf = json.load(open(os.path.join(HERE, 'prefilter_%s.json' % net)))
    rk = {c['i']: c for c in json.load(open(os.path.join(HERE, 'ranked_%s.json' % net)))}
    legal = []
    rejected_body = 0
    for i, c in enumerate(pf['candidates']):
        r = rk[i]
        if not r['body_ok']:
            rejected_body += 1
            continue
        pr = proofs.get((net, i))
        D = PT.delta(c)
        fc = None
        if pr is not None:
            fc = {k: pr[k] for k in ('PASS', 'apply_errors', 'split_ok', 'new_shorts', 'clearance_viol', 'h2h_viol', 'width_viol',
                                     'mask_viol', 'pour_islands', 'pour_off_main_new', 'pour_neck_new', 'worse_islands',
                                     'antennae', 'acid', 'silk_bad', 'compclear', 'tomb_asym', 'u3_side_len')}
        legal.append(dict(id='%s-inner-%d' % (net, i), net=net, ref=PT.REF[net], side=c['side'], rot=c['rot'],
                          x=D['parts'][0]['x'], y=D['parts'][0]['y'], pad1=D['parts'][0]['pad1'], pad2=D['parts'][0]['pad2'],
                          column_per_pad=[[v['from'], v['to'], v['size'], 0.15] for v in D['microvias']][:len(c['cols']) // 2],
                          connector_mm=[c['conn1'], c['conn2']], cut_arc_mm_from_first_via=[c['s1'], c['s2']],
                          margin_new_geometry=r['new_margin'], margin_incl_inherited_pieces=c['cand_clear'],
                          family_split_margin=c['family_clear'], component_clearance=c['compclear_altium'],
                          body_clearance=c['compclear_body'], mech7_courtyard_overlap=c['courtyard_mech7_overlap'],
                          full_check=fc, delta=D, occupancy=occupancy(c)))
    legal.sort(key=lambda e: (-int(bool(e['full_check'] and e['full_check']['PASS'])), -e['margin_new_geometry'][0]))
    out['nets'][net] = dict(run_layer=pf['run_layer'], sites_tested=pf['sites_tested'], sites_rules_legal=pf['sites_legal'],
                            site_pairs=pf['site_pairs'], rules_legal_positions=len(pf['candidates']),
                            rejected_component_body=rejected_body, legal_candidates=len(legal),
                            full_check_pass=sum(1 for e in legal if e['full_check'] and e['full_check']['PASS']),
                            full_check_fail=sum(1 for e in legal if e['full_check'] and not e['full_check']['PASS']),
                            full_check_pending=sum(1 for e in legal if not e['full_check']),
                            search_seconds=pf['seconds'], timed_out=pf['timed_out'], candidates=legal)
out['nets']['D13']['why_zero'] = json.load(open(os.path.join(HERE, 'd13_shortfall.json')))
out['nets']['D13']['why_zero_note'] = (
    'All 504 rules-legal D13 positions (grid 0.025, band 1.0 mm) are Bottom R0201s under U3 (TSOP-II body, standoff '
    '<= 0.15 mm, R height ~0.25 mm): R box to U3 box 0.000 against 0.254. why_zero lists, per 0.5 mm of the L3 run '
    'and per side, the position with the fewest blockers and every rule it fails (margin = distance - rule; -rule '
    'or -1.000 (mask) means touching/overlapping). d13_wide.py: 163 Top + 40 Bottom rules-legal column sites within '
    '2.0 mm of the run lie outside every component box, but no two of them are 0.60 mm apart, so no R position '
    'exists whatever the connector shape. Removing R127 (D8) does not help (D8 Top copper takes its place; 504 again).')
json.dump(out, open(os.path.join(HERE, 'candidates.json'), 'w'), indent=1)
for n, v in out['nets'].items():
    print(n, {k: v[k] for k in ('rules_legal_positions', 'rejected_component_body', 'legal_candidates', 'full_check_pass',
                                'full_check_fail', 'full_check_pending')})
