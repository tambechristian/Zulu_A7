"""candidates.json: every u1_end candidate for D13/D14/D15, self-contained so a combiner can test pairwise compatibility.
Each candidate = part + plan delta vs dq_series_r_plan.json (md5 f2949630) + footprint of everything it occupies
(per layer: the exact primitive and a polygon; drills with their spans; part body; pad bbox for ComponentClearance)
+ everything it removes + the check results.  Status:
  legal                 check.py (copy of d10/fold/check.py) on 13-R plan + this candidate: 0 apply errors, split ok,
                        0 new shorts, both pours one island with nothing newly isolated, no net gains islands, 0 dangling
                        ends, 0 clearance / hole-to-hole / width / mask violations; and no physical body conflict
  legal_silk_U1         legal, but a pad opening is < 0.254 mm from (or the body under) U1's visible designator: needs
                        the 'U1' text hidden or moved
  fast_pass_unchecked   passed the exact fast pre-check (clearance, h2h, width, mask, via-in-pad, connectivity) but
                        check.py was not run on it (pours not verified) -- treat as NOT proven
  excluded_body         passes the copper rules but the R body would sit under U3 (Bottom) / U2 or U1 (Top) bodies
Compatibility: build.pair_ok(delta_a, delta_b) (exact clearance / h2h / mask / ComponentClearance between the two
deltas); then run check.py on the merged plan (joint.py)."""
import json, os, glob, math, hashlib
import build as Bd
import fc_all
E = Bd.E
C = E.C
HERE = E.HERE
FCD = os.path.join(HERE, 'fc')
STRAT = {'F1': 'u1_end: Top R between V2 and the ball', 'F2a': 'u1_end: Top R, V2 replaced by a pad-1 column',
         'F2b': 'u1_end: Top R, pad-1 column, V2 kept on the ball side', 'F3T': 'u1_end: Top R over the last inner segment, columns in both pads',
         'F3T2': 'u1_end: as F3T, wider window (x 37.4-41.3, y 15.4-18.6)', 'F3B': 'u1_end: Bottom R over the last inner segment, columns in both pads',
         'F4': 'u1_end: Bottom R at V2, pad-1 column to the inner run, pad 2 to V2 on Bottom',
         'F5': 'U3 end (first via) -- outside u1_end, run only to look for a D15 site clear of the U1 designator',
         'judgeR134': "judge's optional R134 (design_top.json placements D15), re-checked against the 13-R plan"}


def poly(o, n=8):
    S = o.shape
    if S[0] == 'R':
        return [[round(S[1] - S[3], 4), round(S[2] - S[4], 4)], [round(S[1] + S[3], 4), round(S[2] - S[4], 4)],
                [round(S[1] + S[3], 4), round(S[2] + S[4], 4)], [round(S[1] - S[3], 4), round(S[2] + S[4], 4)]]
    x1, y1, x2, y2, r = S[1:6]
    a = math.atan2(y2 - y1, x2 - x1) if (x1, y1) != (x2, y2) else 0.0
    pts = []
    for (cx, cy, a0) in ((x2, y2, a - math.pi / 2), (x1, y1, a + math.pi / 2)):
        for k in range(n + 1):
            t = a0 + math.pi * k / n
            pts.append([round(cx + r * math.cos(t), 4), round(cy + r * math.sin(t), 4)])
    return pts


def footprint(delta, side, x, y, rot):
    occ = {}
    drills = []
    for o in Bd.delta_objs(delta):
        occ.setdefault(o.layer, []).append(dict(kind=o.kind, net=o.net, shape=[o.shape[0]] + [round(v, 4) for v in o.shape[1:]], polygon=poly(o)))
        if o.kind == 'via' and o.layer == o.span[0]:
            drills.append(dict(x=round(o.xy[0], 4), y=round(o.xy[1], 4), hole=o.hole, span=o.span, net=o.net))
    h = rot in (0, 180)
    body = [x - 0.315, y - 0.165, x + 0.315, y + 0.165] if h else [x - 0.165, y - 0.315, x + 0.165, y + 0.315]
    p = delta['parts'][0]
    pb = [min(p['pad1']['x'], p['pad2']['x']) - 0.15, min(p['pad1']['y'], p['pad2']['y']) - 0.15,
          max(p['pad1']['x'], p['pad2']['x']) + 0.15, max(p['pad1']['y'], p['pad2']['y']) + 0.15]
    return dict(occupies=occ, drills=drills, body_max_0201=dict(side=side, rect=[round(v, 4) for v in body]),
                pad_bbox=dict(side=side, rect=[round(v, 4) for v in pb]),
                frees=dict(tracks=[t for t in delta['remove'] if t.get('why') != 'rename'], vias=[v for v in delta['remove_vias'] if v.get('why') != 'rename']))


def main():
    out = dict(source=dict(pcbdoc_md5=E.B['source']['pcbdoc_md5'], base_plan='si/series_r/dq_series_r_plan.json',
                           base_plan_md5=hashlib.md5(open(E.ulib.BASE_PLAN, 'rb').read()).hexdigest(),
                           checker='si/series_r/d13/u1_end/check.py (byte copy of d10/fold/check.py)', strategy='u1_end',
                           grid_mm=0.05, rotations=[0, 90, 180, 270]),
               status_legend=__doc__, families=STRAT, nets={})
    for n in (13, 14, 15):
        rows = []
        for f in sorted(glob.glob(os.path.join(HERE, 'search', 'search_D%d_*.json' % n))):
            S = json.load(open(f))
            for c in S['cands']:
                x, y, r = c['pose']
                tag = 'D%d_%s_%s_%s_%d' % (n, S['fam'], ('%.3f' % x).replace('.', 'p'), ('%.3f' % y).replace('.', 'p'), r)
                bc = fc_all.body_conflict(S['side'], x, y, r, why=True)
                vf = os.path.join(FCD, 'v_%s.json' % tag)
                v = json.load(open(vf)) if os.path.exists(vf) else None
                silk = any(s.startswith('silk') for s in c['fast']['soft'])
                if bc:
                    st = 'excluded_body'
                elif v is None:
                    st = 'fast_pass_unchecked'
                elif not v['ok']:
                    st = 'illegal_check'
                else:
                    st = 'legal_silk_U1' if (silk or any(s.startswith('silk') for s in v['soft'])) else 'legal'
                v2 = E.NETS[n]['v2']
                rows.append(dict(id=tag, net='D%d' % n, ref=E.REF[n], family=S['fam'], status=st, body_conflict=bc,
                                 part=c['delta']['parts'][0], side=S['side'],
                                 dist_to_V2_mm=round(math.hypot(x - v2[0], y - v2[1]), 3),
                                 new_vias=c['n_new_vias'], new_copper_mm=c['added_len'], inner_width=c['w_inner'],
                                 fast_check=dict(soft=c['fast']['soft'], worst=c['fast']['worst']),
                                 check=None if v is None else dict(ok=v['ok'], hard=v['hard'], soft=v['soft'],
                                                                   log='fc/check_%s.log' % tag),
                                 delta=c['delta'], footprint=footprint(c['delta'], S['side'], x, y, r)))
        if n == 15:
            d = json.load(open(os.path.join(HERE, 'judge_r134_delta.json')))[0]
            v = json.load(open(os.path.join(FCD, 'check_judgeR134.json')))
            import fullcheck as F
            vv = F.verdict(v)
            pr = d['parts'][0]
            rows.append(dict(id='D15_judgeR134_39p100_16p750_0', net='D15', ref='R134', family='judgeR134',
                             status='legal_silk_U1' if vv['ok'] else 'illegal_check', body_conflict=None, part=pr, side='Top',
                             dist_to_V2_mm=round(math.hypot(pr['x'] - 48.9, pr['y'] - 16.8), 3), new_vias=3,
                             new_copper_mm=None, inner_width=0.125, fast_check=None,
                             check=dict(ok=vv['ok'], hard=vv['hard'], soft=vv['soft'], log='fc/check_judgeR134.log'),
                             delta=d, footprint=footprint(d, 'Top', pr['x'], pr['y'], pr['rot'])))
        cnt = {}
        for r_ in rows:
            cnt[r_['status']] = cnt.get(r_['status'], 0) + 1
        out['nets']['D%d' % n] = dict(counts=cnt, candidates=rows)
        print('D%d' % n, cnt)
    json.dump(out, open(os.path.join(HERE, 'candidates.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
