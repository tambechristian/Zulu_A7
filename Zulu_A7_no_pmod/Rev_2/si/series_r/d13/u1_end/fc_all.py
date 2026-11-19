"""run check.py (via fullcheck.run_plan) on every fast-pass candidate of search/search_*.json, 6 workers.
writes fc/results.json : {tag: verdict}"""
import json, os, sys, glob
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def job(a):
    tag, delta = a
    import fullcheck as F
    import build as Bd
    out = os.path.join(F.FC, 'v_%s.json' % tag)
    if os.path.exists(out):
        return tag, json.load(open(out))
    P = Bd.merge_plan(Bd.E.ulib.P13, [delta], note=tag)
    ok, v = F.run_plan(P, tag)
    json.dump(v, open(out, 'w'), default=str)
    for ext in ('json', 'log'):   # keep the disk small: logs of passing tags are kept, json dropped
        pass
    return tag, v


U3B = (17.1749, 6.705, 39.525, 16.995)   # U3 body, datasheet max (board_extract u3.body.max)
U1B = (41.4, 6.9, 51.4, 16.9)


_B = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'board_extract.json')))
_SIDE = {c['ref']: c['side'] for c in _B['components']}
BODIES = [('U3', 'Bottom', U3B), ('U1', 'Top', U1B)] + [(r, _SIDE[r], v['Mech3']) for r, v in _B['component_outlines'].items()
                                                       if 'Mech3' in v and r not in ('U1', 'U3')]
del _B


def body_conflict(side, x, y, r, why=False):
    """R0201 body at its max size (0.63 x 0.33) overlapping a same-side component body (U3: datasheet max;
    U1: 10 x 10 package; others: their Mech3 body outline)"""
    h = r in (0, 180)
    b = (x - 0.315, y - 0.165, x + 0.315, y + 0.165) if h else (x - 0.165, y - 0.315, x + 0.165, y + 0.315)
    for ref, s, box in BODIES:
        if s == side and b[0] < box[2] and b[2] > box[0] and b[1] < box[3] and b[3] > box[1]:
            return ref if why else True
    return None if why else False


def main():
    skipped = []
    todo = []
    for f in sorted(glob.glob(os.path.join(HERE, 'search', 'search_D*.json'))):
        S = json.load(open(f))
        for k, c in enumerate(S['cands']):
            x, y, r = c['pose']
            tag = 'D%d_%s_%s_%s_%d' % (S['net'], S['fam'], ('%.3f' % x).replace('.', 'p'), ('%.3f' % y).replace('.', 'p'), r)
            if body_conflict(S['side'], x, y, r):
                skipped.append(tag)
                continue
            todo.append((tag, c['delta']))
    def pri(t):
        p = t[0].split('_')
        x = float(p[2].replace('p', '.')); y = float(p[3].replace('p', '.'))
        coarse = (round(x * 1000) % 100 == 0) and (round(y * 1000) % 100 == 0)
        return (0 if coarse else 1, t[0])
    todo.sort(key=pri)
    print(len(todo), 'candidates;', len(skipped), 'skipped: R body under U3 (Bottom) / U1 (Top) body', flush=True)
    json.dump(skipped, open(os.path.join(HERE, 'fc', 'skipped_body.json'), 'w'))
    res = {}
    with Pool(int(os.environ.get('FC_WORKERS', '4'))) as p:
        for i, (tag, v) in enumerate(p.imap_unordered(job, todo)):
            res[tag] = v
            if i % 25 == 0:
                print(i, tag, v['ok'], flush=True)
    json.dump(res, open(os.path.join(HERE, 'fc', 'results.json'), 'w'), indent=0, default=str)
    print('pass', sum(v['ok'] for v in res.values()), 'of', len(res))


if __name__ == '__main__':
    main()
