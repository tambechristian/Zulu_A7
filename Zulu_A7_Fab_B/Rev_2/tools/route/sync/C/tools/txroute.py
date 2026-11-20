"""Strategy C, pass 2: transactional regional rip-up and re-route on top of router.py (C/tools copy).

    python tools/txroute.py --model M.json --seed a.json[,b.json] [--nets N1,N2] --out out.json
                            [--checkpoint cp.json] [--soft 0.3] [--pops 600000] [--vpops 400000] [--rounds 3]
                            [--depth 2] [--order short|name] [--margins 2.5,6.25]

router.py's rip-up is destructive: a torn net that cannot be routed again stays open, so a pass can end with MORE open
connections than it started with (pass 1 seeded with the original zone copper went 10 -> 22). Here every attempt is a
transaction:
  1. route the open net as router.py does (nearest island first, margins 2.5 then 6.25 mm);
  2. if a pair fails, find router.py's minimum-victim path (base=True, --soft cost per cell of rippable copper) and the
     router-copper nets it crosses (Router.blockers tight, + the hole-to-hole neighbours), rip them, route the net, then
     re-route every victim from scratch (shortest first; with --depth > 1 a victim may itself rip once more);
  3. if anything stays open, restore the snapshot (router copper and board raster) - the open count never grows.
The seed plans are router copper (rippable); the model's own copper is fixed. Plane nets (GND / VCC3V3) are never
victims. The output has router.py's format ({tracks, vias, remove: [], log}); every primitive went through
Router.commit, and the plan must still pass route_check.py and the full DRC.
"""
import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import router as R  # noqa: E402
import route_conn as C  # noqa: E402

PLANE = ('GND', 'VCC3V3')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--seed', default='')
    ap.add_argument('--nets', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--checkpoint', default='')
    ap.add_argument('--soft', type=float, default=0.3)
    ap.add_argument('--pops', type=int, default=600000)
    ap.add_argument('--vpops', type=int, default=400000, help='A* budget when re-routing a victim')
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--depth', type=int, default=2)
    ap.add_argument('--maxvict', type=int, default=6, help='skip a rip-up that would tear more nets than this')
    ap.add_argument('--order', default='short', choices=['short', 'name'])
    ap.add_argument('--margins', default='2.5,6.25')
    ap.add_argument('--local', type=float, default=0.0, help='rip only the copper of the victims within this many mm '
                    'of the blocking path (0: the whole net, as router.py)')
    ap.add_argument('--time', type=float, default=0, help='stop starting new attempts after this many minutes')
    ap.add_argument('--slack', type=float, default=R.MARGIN, help='router.py --slack: raster allowance in mm '
                    '(default 0.02); smaller values reach lanes routed at the rule limit -- route_check the result')
    a = ap.parse_args()
    R.MARGIN = a.slack
    t0 = time.time()
    margins = [float(v) for v in a.margins.split(',')]
    M = json.load(open(a.model))
    for v in M['vias']:
        if 'span' not in v:
            v['span'] = R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1]
    B = R.Board(M)
    Rt = R.Router(B, a.pops)
    Rt.soft = a.soft
    if a.seed:
        for f in a.seed.split(','):
            P = json.load(open(f))
            Rt.out_t += P['tracks']
            Rt.out_v += P['vias']
        Rt.rip(set())
    log = []

    def say(m):
        print('%6.1f %s' % ((time.time() - t0) / 60, m), flush=True)
        log.append(m)

    by_net_pads = defaultdict(list)
    for p in M['pads']:
        if p['net']:
            by_net_pads[p['net']].append(p)
    by_net_t = defaultdict(list)
    for t in M['tracks']:
        by_net_t[t['net']].append(t)
    by_net_v = defaultdict(list)
    for v in M['vias']:
        by_net_v[v['net']].append(v)

    def net_model(net):
        """the net alone (model copper + router copper): islands and masks index into THIS model"""
        vs = by_net_v[net] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1])
                              for v in Rt.out_v if v['net'] == net]
        return {'board': M['board'], 'planes': M['planes'], 'pads': by_net_pads[net],
                'tracks': by_net_t[net] + [t for t in Rt.out_t if t['net'] == net], 'vias': vs}

    def groups_of(net):
        Mn = net_model(net)
        return Mn, [dict(g) for g in C.islands(Mn).get(net, [])]

    def opens(net):
        return max(0, len(groups_of(net)[1]) - 1)

    def route_pair(net, Mn, g1, g2, base=False, pops=None):
        Rt.max_pops = pops or a.pops
        mb = R.bbox(Mn, g1)
        for mg in margins:
            win = R.window(B, [mb, R.bbox(Mn, g2)], mg)
            r = Rt.route(net, R.island_mask(B, Mn, g1, win), R.island_mask(B, Mn, g2, win), win, base=base)
            if r:
                return r
        return None

    def tie(net, Mn, g, base=False):
        """a plane net's island to its pour (router.py's plane logic: a tie via anywhere the island reaches)"""
        Rt.max_pops = a.pops
        bx = R.bbox(Mn, g)
        for mg in (0.8, 1.6, 3.0):
            win = R.window(B, [bx], mg)
            r = Rt.route(net, R.island_mask(B, Mn, g, win), None, win, plane=R.PLANE_VIAS[net], base=base)
            if r:
                return r
        return None

    def connect(net, pops=None, fail_fast=True):
        """join all islands of the net (nearest first); returns (ok, failing pair)"""
        Mn, gs = groups_of(net)
        if len(gs) <= 1:
            return True, None
        if net in PLANE:
            for g in gs:
                if g['plane']:
                    continue
                r = tie(net, Mn, g)
                if not r:
                    return False, (Mn, g, None)
                Rt.commit(net, *r)
            return True, None
        main_g, rest = gs[0], gs[1:]
        ok = True
        bad = None
        while rest:
            mb = R.bbox(Mn, main_g)
            rest.sort(key=lambda g: math.hypot((R.bbox(Mn, g)[0] + R.bbox(Mn, g)[2]) / 2 - (mb[0] + mb[2]) / 2,
                                               (R.bbox(Mn, g)[1] + R.bbox(Mn, g)[3]) / 2 - (mb[1] + mb[3]) / 2))
            gi = rest.pop(0)
            r = route_pair(net, Mn, main_g, gi, pops=pops)
            if r:
                Rt.commit(net, *r)
                for k in ('pads', 'tracks', 'vias'):
                    main_g[k] = main_g[k] + gi[k]
                # the commit appended to Rt.out_*: rebuild the net model so later masks see the new copper
                Mn2, gs2 = groups_of(net)
                if len(gs2) <= 1:
                    return True, None
                Mn = Mn2
                # re-derive the main island as the one holding the first pad, the rest stay to do
                pad0 = (Mn['pads'][0]['ref'], Mn['pads'][0]['pad']) if Mn['pads'] else None
                main_g = next((g for g in gs2 if pad0 and any((Mn['pads'][i]['ref'], Mn['pads'][i]['pad']) == pad0
                                                               for i in g['pads'])), gs2[0])
                rest = [g for g in gs2 if g is not main_g]
            else:
                ok = False
                bad = (Mn, main_g, gi)
                if fail_fast:
                    return False, bad
        return ok, bad

    def snapshot():
        return list(Rt.out_t), list(Rt.out_v)

    def restore(s):
        Rt.out_t, Rt.out_v = list(s[0]), list(s[1])
        Rt.rip(set())

    def victims_for(net, bad):
        Mn, g1, g2 = bad
        if g2 is None:
            r = tie(net, Mn, g1, base=True)
            if not r:
                return None
            path, (kind, vx, vy) = r
            path = path + [(path[-1][0], vx, vy, kind)]
        else:
            r = route_pair(net, Mn, g1, g2, base=True)
            if not r:
                return None
            path, endvia = r
        vs = Rt.blockers(net, path, tight=True)
        return {v for v in vs if v not in PLANE and v != net}, path

    def rip_local(vs, path, rad):
        """--local: tear out only the victims' router copper within rad (+ its half width / land) of the blocking
        path, not the whole net; the victim is then re-joined across the short gap"""
        import numpy as np
        P = np.array([(x, y) for _, x, y, _ in path[::2]] + [(path[-1][1], path[-1][2])])

        def near_seg(t):
            ax, ay, bx, by = t['x1'], t['y1'], t['x2'], t['y2']
            vx, vy = bx - ax, by - ay
            L = vx * vx + vy * vy
            k = np.zeros(len(P)) if L == 0 else np.clip(((P[:, 0] - ax) * vx + (P[:, 1] - ay) * vy) / L, 0, 1)
            d = np.hypot(P[:, 0] - ax - k * vx, P[:, 1] - ay - k * vy)
            return float(d.min()) <= rad + t['w'] / 2

        def near_pt(v):
            return float(np.hypot(P[:, 0] - v['x'], P[:, 1] - v['y']).min()) <= rad + v['size'] / 2
        gone_pts = {(v['net'], round(v['x'], 4), round(v['y'], 4)) for v in Rt.out_v if v['net'] in vs and near_pt(v)}
        Rt.out_t = [t for t in Rt.out_t if not (t['net'] in vs and near_seg(t))]
        Rt.out_v = [v for v in Rt.out_v if (v['net'], round(v['x'], 4), round(v['y'], 4)) not in gone_pts]
        Rt.rip(set())

    def attempt(net, depth, frozen):
        """try to close the net; may rip router-copper nets (not frozen) and re-route them; transactional"""
        snap = snapshot()
        ok, bad = connect(net)
        if ok:
            return True
        if depth <= 0:
            restore(snap)
            return False
        tried = 0
        torn = set()
        pre = {}
        while bad is not None and tried < 3:
            tried += 1
            vr = victims_for(net, bad)
            if not vr or not vr[0]:
                break
            vs, vpath = vr
            if vs & frozen or len(torn | vs) > a.maxvict:
                say('  %s: victims %s (frozen or too many) - give up' % (net, ' '.join(sorted(vs))))
                break
            pre.update({v: opens(v) for v in vs if v not in pre})
            if a.local > 0:
                rip_local(vs, vpath, a.local)
            else:
                Rt.rip(vs)
            torn |= vs
            ok, bad = connect(net)
            if not ok:
                # still blocked: one more round of victims on the remaining pair, inside the same transaction
                frozen = frozen | vs
                continue
            # the net is closed; put every victim back (shortest first), victims may rip once more (depth - 1)
            good = True
            vs = torn
            for v in sorted(vs):
                okv, badv = connect(v, pops=a.vpops)
                if not okv and depth > 1:
                    # the inner attempt may tear victims that are already back (not the net itself); the final
                    # check below re-verifies every victim of this transaction
                    okv = attempt(v, depth - 1, frozen | {net})
                if not okv or opens(v) > pre[v]:
                    good = False
                    say('  %s: victim %s not restored' % (net, v))
                    break
            if good and (opens(net) > 0 or any(opens(v) > pre[v] for v in torn)):
                good = False
                say('  %s: a victim was torn again by a nested attempt and not restored' % net)
            if good:
                say('  %s closed, re-routed %s' % (net, ' '.join(sorted(vs))))
                return True
            break
        restore(snap)
        return False

    def all_open():
        Mx = dict(M)
        Mx['tracks'] = M['tracks'] + Rt.out_t
        Mx['vias'] = M['vias'] + [dict(v, span=R.STACK[R.STACK.index(v['from']):R.STACK.index(v['to']) + 1])
                                  for v in Rt.out_v]
        return C.open_count(C.islands(Mx))

    oc = all_open()
    want = set(a.nets.split(',')) if a.nets else None
    say('start: %d open on %d nets: %s' % (sum(oc.values()), len(oc), ' '.join('%s:%d' % kv for kv in sorted(oc.items()))))

    def span_of(n):
        Mn, gs = groups_of(n)
        cs = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in (R.bbox(Mn, g) for g in gs)]
        return max((math.hypot(p[0] - q[0], p[1] - q[1]) for p in cs for q in cs), default=0)

    for rnd in range(a.rounds):
        oc = all_open()
        todo = [n for n in oc if (not want or n in want or rnd > 0)]
        todo.sort(key=span_of if a.order == 'short' else (lambda n: n))
        if not todo:
            break
        closed = 0
        for net in todo:
            if a.time and (time.time() - t0) / 60 > a.time:
                say('time limit')
                break
            if opens(net) == 0:
                continue
            before = sum(all_open().values())
            ok = attempt(net, a.depth, set())
            after = sum(all_open().values())
            assert after <= before, ('open count grew', net, before, after)
            if ok:
                closed += 1
            say('round %d %-14s %s  open %d -> %d' % (rnd + 1, net, 'CLOSED' if ok else 'open', before, after))
            if a.checkpoint:
                json.dump({'vias': Rt.out_v, 'tracks': Rt.out_t, 'remove': [], 'log': log[-50:]},
                          open(a.checkpoint, 'w'), indent=0)
        if closed == 0 or (a.time and (time.time() - t0) / 60 > a.time):
            break
    oc = all_open()
    say('end: %d open on %d nets: %s' % (sum(oc.values()), len(oc), ' '.join('%s:%d' % kv for kv in sorted(oc.items()))))
    json.dump({'vias': Rt.out_v, 'tracks': Rt.out_t, 'remove': [], 'log': log}, open(a.out, 'w'), indent=0)


if __name__ == '__main__':
    main()
