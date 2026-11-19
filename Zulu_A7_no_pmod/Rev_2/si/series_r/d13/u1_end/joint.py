"""build the joint plan: 13-R plan + chosen u1_end candidates (polished), prove it with check.py (copy of
d10/fold/check.py, tag given on the CLI; check_<tag>.json/.log stay in this folder).
usage: python joint.py <tag> <net:fam:x:y:rot> [...]      e.g. joint 14:F4:46.1:17.15:0 15:F4:47.25:16.8:0
writes plan_<tag>.json (and copies to plan.json when tag == 'joint')"""
import json, os, sys, math, shutil, copy
import build as Bd
import fullcheck as F
HERE = os.path.dirname(os.path.abspath(__file__))


def find(n, fam, x, y, rot):
    S = json.load(open(os.path.join(HERE, 'search', 'search_D%d_%s.json' % (n, fam))))
    for c in S['cands']:
        if abs(c['pose'][0] - x) < 1e-6 and abs(c['pose'][1] - y) < 1e-6 and c['pose'][2] == rot:
            return c
    raise KeyError((n, fam, x, y, rot))


def r4(v):
    return round(v + 0.0, 4)


def polish(d):
    """round coordinates to 0.1 um; merge a <0.06 mm attach stub into the kept straight piece it hangs on
    (the piece then ends at the column centre)."""
    d = copy.deepcopy(d)
    for t in d['tracks']:
        for k in ('x1', 'y1', 'x2', 'y2'):
            t[k] = r4(t[k])
    for v in d['vias'] + d['microvias']:
        v['x'], v['y'] = r4(v['x']), r4(v['y'])
    cols = {(v['x'], v['y']) for v in d['vias'] if v.get('why') != 'rename' and v['size'] < 0.34}
    new = [t for t in d['tracks'] if t.get('why') != 'rename']
    for st in list(new):
        L = math.hypot(st['x2'] - st['x1'], st['y2'] - st['y1'])
        if L >= 0.06 or st['layer'] not in ('L3-SIG', 'L4-SIG'):
            continue
        ends = [(st['x1'], st['y1']), (st['x2'], st['y2'])]
        col = [e for e in ends if e in cols]
        if len(col) != 1:
            continue
        other = ends[1] if col[0] == ends[0] else ends[0]
        hosts = [t for t in new if t is not st and t['net'] == st['net'] and t['layer'] == st['layer'] and
                 ((t['x2'], t['y2']) == other or (t['x1'], t['y1']) == other)]
        if len(hosts) != 1:
            continue
        h = hosts[0]
        if (h['x2'], h['y2']) == other:
            h['x2'], h['y2'] = col[0]
        else:
            h['x1'], h['y1'] = col[0]
        d['tracks'].remove(st)
        new.remove(st)
    return d


def main():
    tag = sys.argv[1]
    picks = []
    for s in sys.argv[2:]:
        n, fam, x, y, rot = s.split(':')
        picks.append((int(n), fam, float(x), float(y), int(rot)))
    deltas = []
    for n, fam, x, y, rot in picks:
        if fam == 'judgeR134':
            deltas.append(json.load(open(os.path.join(HERE, 'judge_r134_delta.json')))[0])
        else:
            deltas.append(polish(find(n, fam, x, y, rot)['delta']))
    for i in range(len(deltas)):
        for j in range(i + 1, len(deltas)):
            ok, w = Bd.pair_ok(deltas[i], deltas[j])
            print('pair', picks[i][:2], picks[j][:2], ok, w)
    note = ' + '.join('%s D%d %s (%.4f,%.4f) rot %d' % (Bd.E.REF[n], n, fam, x, y, rot) for n, fam, x, y, rot in picks)
    P = Bd.merge_plan(Bd.E.ulib.P13, deltas, note=note + '; strategy u1_end')
    pth = os.path.join(HERE, 'plan_%s.json' % tag)
    json.dump(P, open(pth, 'w'), indent=1)
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), '--plan', pth, '--tag', tag], cwd=HERE,
                       capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    v = F.verdict(json.load(open(os.path.join(HERE, 'check_%s.json' % tag))))
    ok = v['ok']
    print(json.dumps(dict(ok=ok, hard=v['hard'], soft=v['soft']), indent=1))
    if tag == 'joint' and ok:
        shutil.copy(pth, os.path.join(HERE, 'plan.json'))


if __name__ == '__main__':
    main()
