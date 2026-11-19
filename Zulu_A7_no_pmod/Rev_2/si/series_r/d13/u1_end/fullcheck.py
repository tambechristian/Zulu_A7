"""run this folder's COPY of d10/fold/check.py on (13-R plan + candidate deltas) and judge the result.
usage (module): verdict(tag) ; run_plan(plan_dict, tag) -> (ok, verdict dict)
CLI: python fullcheck.py <deltas.json> <tag>   (deltas.json = list of plan deltas)
check.py writes check_<tag>.json/.log next to itself; they are moved into fc/ afterwards (final proofs stay put).
"""
import json, os, sys, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
FC = os.path.join(HERE, 'fc')
os.makedirs(FC, exist_ok=True)
BASE = json.load(open(os.path.join(HERE, 'check_base13.json')))


def _sl(d):
    return {L: sorted((s['x'], s['y']) for s in r['new_sub_0p10_slivers']) for L, r in d['planes'].items()}


BASE_SL = _sl(BASE)
BASE_REFX = {r['track'] for r in BASE['reference_plane_new_voids']}


def verdict(d):
    hard, soft = [], []
    if d['apply_errors']:
        hard.append('apply errors %d' % len(d['apply_errors']))
    for k, r in d['split'].items():
        if not r['ok']:
            hard.append('split %s: %s' % (k, r['notes']))
    for s in d['self_consistency']:
        if 'missing_from_microvias' in s and s['missing_from_microvias']:
            hard.append('vias missing from microvias list')
        if 'centred' in s and not (s['centred'] and s['nets'] and s['rot_matches_pads']):
            hard.append('part self-consistency %s' % s)
    if d['shorts']['new']:
        hard.append('new shorts %s' % d['shorts']['new'])
    for L, r in d['planes'].items():
        b = BASE['planes'][L]
        if r['live_islands_after'] != 1:
            hard.append('%s live islands %d' % (L, r['live_islands_after']))
        if set(r['objects_off_main_after']) - set(b['objects_off_main_after']):
            hard.append('%s newly isolated %s' % (L, sorted(set(r['objects_off_main_after']) - set(b['objects_off_main_after']))))
        if set(r['off_main_through_necks_lt_0p10_after']) - set(b['off_main_through_necks_lt_0p10_after']):
            hard.append('%s newly neck-attached %s' % (L, sorted(set(r['off_main_through_necks_lt_0p10_after']) - set(b['off_main_through_necks_lt_0p10_after']))))
    if d['net_islands']['worse']:
        hard.append('nets gain islands %s' % d['net_islands']['worse'])
    if d['antennae']:
        hard.append('antennae %s' % d['antennae'][:3])
    if d['clearance']['violations']:
        hard.append('clearance %d: %s' % (len(d['clearance']['violations']), d['clearance']['violations'][:2]))
    if d['hole_to_hole']['violations']:
        hard.append('h2h %s' % d['hole_to_hole']['violations'][:2])
    if d['width']:
        hard.append('width %s' % d['width'][:2])
    if d['mask']['violations']:
        hard.append('mask %s' % d['mask']['violations'][:2])
    sl = _sl(d)
    for L in sl:
        new = [s for s in sl[L] if s not in BASE_SL[L]]
        if new:
            soft.append('%s new <0.10 pour slivers vs 13-R plan: %s' % (L, new))
    refx = [r for r in d['reference_plane_new_voids'] if r['track'] not in BASE_REFX]
    if refx:
        soft.append('tracks over new pour voids: %s' % [(r['plane'], r['track'][:60], r['over_new_void_mm']) for r in refx])
    if d['acid_traps']:
        soft.append('acid traps %d' % len(d['acid_traps']))
    for t in d['tombstone']:
        if t['ref'] in ('R132', 'R133', 'R134') and t['flags']:
            soft.append('%s tombstone flags %s' % (t['ref'], t['flags']))
    for s in d['silk']:
        if not s['ok'] and any(r in s['pad'] for r in ('R132', 'R133', 'R134')):
            soft.append('silk %s %s gap %.3f' % (s['pad'], s['text'], s['gap_to_opening']))
    for a in d['altium_component_clearance']:
        if a['ref'] in ('R132', 'R133', 'R134') and not a['ok']:
            soft.append('ComponentClearance %s %s' % (a['ref'], a['nearest'][:1]))
    w = d['clearance']['worst']
    return dict(ok=not hard, hard=hard, soft=soft, worst=w, h2h_worst=d['hole_to_hole']['worst'], mask_worst=d['mask']['worst'])


def run_plan(P, tag, keep_here=False):
    pth = os.path.join(FC, 'plan_%s.json' % tag)
    json.dump(P, open(pth, 'w'), indent=1)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), '--plan', pth, '--tag', tag], cwd=HERE,
                       capture_output=True, text=True, env=env)
    src = os.path.join(HERE, 'check_%s.json' % tag)
    if not os.path.exists(src):
        return False, dict(ok=False, hard=['check.py crashed: ' + r.stderr[-800:]], soft=[])
    d = json.load(open(src))
    if not keep_here:
        for ext in ('json', 'log'):
            shutil.move(os.path.join(HERE, 'check_%s.%s' % (tag, ext)), os.path.join(FC, 'check_%s.%s' % (tag, ext)))
    v = verdict(d)
    return v['ok'], v


if __name__ == '__main__':
    import build as Bd
    deltas = json.load(open(sys.argv[1]))
    P = Bd.merge_plan(Bd.E.ulib.P13, deltas, note=sys.argv[2])
    ok, v = run_plan(P, sys.argv[2])
    print(json.dumps(v, indent=1, default=str))
