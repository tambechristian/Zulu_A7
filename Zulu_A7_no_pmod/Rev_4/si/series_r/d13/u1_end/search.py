"""enumerate poses for one (net, family) on a grid, pre-filter, build (route), fast exact check.
usage: python search.py <net> <family> [step]   -> search_<net>_<family>.json
"""
import sys, json, math, time, os
import numpy as np
import engine as E
import build as Bd
C = E.C

POSE_WIN = {
    (13, 'F1'): (39.0, 11.6, 41.25, 14.2), (13, 'F2a'): (39.0, 11.6, 41.25, 14.2), (13, 'F2b'): (39.0, 11.6, 41.25, 14.2),
    (13, 'F3T'): (38.2, 12.2, 41.25, 15.6), (13, 'F3B'): (38.2, 12.2, 41.4, 15.6), (13, 'F4'): (39.0, 11.4, 42.8, 14.2),
    (14, 'F1'): (45.6, 16.95, 50.4, 18.7), (14, 'F2a'): (45.6, 16.95, 50.4, 18.7), (14, 'F2b'): (45.6, 16.95, 50.4, 18.7),
    (14, 'F3T'): (37.6, 16.5, 48.3, 18.0), (14, 'F3B'): (37.6, 16.5, 48.3, 18.0), (14, 'F4'): (45.6, 16.4, 50.0, 18.7),
    (15, 'F1'): (46.6, 16.95, 51.0, 18.7), (15, 'F2a'): (46.6, 16.95, 51.0, 18.7), (15, 'F2b'): (46.6, 16.95, 51.0, 18.7),
    (15, 'F3T'): (38.0, 16.1, 49.3, 17.6), (15, 'F3T2'): (37.4, 15.4, 41.3, 18.6),
    (13, 'F5'): (34.6, 15.2, 37.4, 18.0), (14, 'F5'): (35.0, 15.6, 38.6, 18.4), (15, 'F5'): (37.2, 15.6, 40.6, 18.6), (15, 'F3B'): (38.0, 16.1, 49.3, 17.6), (15, 'F4'): (46.6, 16.2, 51.0, 18.7),
}
SIDE = {'F5': 'Top', 'F3T2': 'Top', 'F1': 'Top', 'F2a': 'Top', 'F2b': 'Top', 'F3T': 'Top', 'F3B': 'Bottom', 'F4': 'Bottom'}
COLS = {'F5': (2,), 'F3T2': (1, 2), 'F1': (), 'F2a': (1,), 'F2b': (1,), 'F3T': (1, 2), 'F3B': (1, 2), 'F4': (1,)}


def drill_block(W, span, hole):
    M = np.zeros((W.ny, W.nx), bool)
    X, Y = np.meshgrid(W.xs, W.ys)
    bb = W.bb()
    for d in E.DRILLS:
        if E.is_fam(d[3], NET):
            continue
        if not (bb[0] - 1 < d[0][0] < bb[2] + 1 and bb[1] - 1 < d[0][1] < bb[3] + 1):
            continue
        if not (set(span) & d[2]):
            continue
        r = 0.24 + hole / 2 + d[1] / 2
        M |= np.hypot(X - d[0][0], Y - d[0][1]) < r - 1e-6
    return M


def main():
    global NET
    n = int(sys.argv[1]); fam = sys.argv[2]
    famb = 'F3T' if fam == 'F3T2' else fam
    step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
    NET = n
    N = E.NETS[n]
    side = SIDE[fam]
    pw = POSE_WIN[(n, fam)]
    # routing window: pose window + targets + margin
    zp = N['poly'][:N['first_to'] + 1] + [N['v1']] if fam == 'F5' else N['poly'][N['last_from']:] + [N['v2'], N['ballxy']]
    xs = [pw[0], pw[2]] + [p[0] for p in zp]
    ys = [pw[1], pw[3]] + [p[1] for p in zp]
    rwin = (min(xs) - 0.8, min(ys) - 0.8, max(xs) + 0.8, max(ys) + 0.8)
    ctx = Bd.Ctx(n, famb, rwin)
    W = ctx.W
    SN = 'SDRAM-D%d' % n
    t0 = time.time()
    padok = ~E.static_block(W, side, SN, 0.15, (), exclude=ctx.ign)
    colok = np.ones_like(padok)
    if COLS[fam]:
        for v in E.column(side, N['inner'], (0, 0), SN):
            for L in v['span']:
                colok &= ~E.static_block(W, L, SN, v['size'] / 2, (), exclude=ctx.ign)
            colok &= ~drill_block(W, v['span'], v['hole'])
    poses = []
    nstep = int(round(step / E.RR))
    i0, j0 = W.ij(pw[0], pw[1]); i1, j1 = W.ij(pw[2], pw[3])
    for rot in (0, 90, 180, 270):
        for i in range(i0, i1 + 1, nstep):
            for j in range(j0, j1 + 1, nstep):
                x, y = W.xy(i, j)
                p1, p2 = E.pad_xy(x, y, rot)
                a1 = W.ij(*p1); a2 = W.ij(*p2)
                if not (0 <= a1[0] < W.nx and 0 <= a1[1] < W.ny and 0 <= a2[0] < W.nx and 0 <= a2[1] < W.ny):
                    continue
                if not (padok[a1[1], a1[0]] and padok[a2[1], a2[0]]):
                    continue
                if 1 in COLS[fam] and not colok[a1[1], a1[0]]:
                    continue
                if 2 in COLS[fam] and not colok[a2[1], a2[0]]:
                    continue
                if side == 'Top':
                    horiz = rot in (0, 180)
                    body = [x - 0.315, y - 0.165, x + 0.315, y + 0.165] if horiz else [x - 0.165, y - 0.315, x + 0.165, y + 0.315]
                    if Bd.rr(body, Bd.U1_BODY) <= 0:
                        continue
                poses.append((round(x, 4), round(y, 4), rot))
    print('net D%d %s: %d poses pass the pad/column pre-filter (%.1fs)' % (n, fam, len(poses), time.time() - t0), flush=True)
    res = []
    reasons = {}
    for k, (x, y, rot) in enumerate(poses):
        cand = None
        for wi in ((E.W_INNER, 0.10) if COLS[fam] else (E.W_INNER,)):
            cand, why = Bd.build(ctx, side, x, y, rot, w_inner=wi)
            if cand is None:
                continue
            fc = Bd.fast_check(cand)
            if fc['ok']:
                break
            why = 'fast: ' + fc['hard'][0][:90]
            cand = None
        if cand is None:
            key = why.split(' %')[0][:60]
            reasons[key] = reasons.get(key, 0) + 1
            continue
        res.append(dict(pose=(x, y, rot), fast=fc, delta=Bd.plan_delta(cand),
                        added_len=round(sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in cand['add_t'] if t['why'] == 'new'), 4),
                        n_new_vias=len(cand['add_v']), w_inner=cand['w_inner']))
        if k % 50 == 0:
            print('  %d/%d poses, %d pass (%.0fs)' % (k, len(poses), len(res), time.time() - t0), flush=True)
    out = dict(net=n, fam=fam, side=side, step=step, n_poses=len(poses), n_pass=len(res), reject_reasons=reasons, cands=res)
    json.dump(out, open(os.path.join(E.HERE, 'search', 'search_D%d_%s.json' % (n, fam)), 'w'), indent=0)
    print('D%d %s: %d fast-pass of %d poses; rejects %s (%.0fs)' % (n, fam, len(res), len(poses), reasons, time.time() - t0))


if __name__ == '__main__':
    main()
